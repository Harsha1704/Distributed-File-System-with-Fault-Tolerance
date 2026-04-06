"""
metadata_manager.py — Persistent file and chunk metadata store.

Schema (saved as JSON):
{
  "<filename>": {
    "filename":    str,
    "file_hash":   str,
    "num_chunks":  int,
    "uploaded_at": str,   # ISO-8601
    "chunks": {
      "<chunk_id>": {
        "chunk_id": str,
        "index":    int,
        "size":     int,
        "hash":     str,
        "nodes":    [node_id, ...]   # 1-based node IDs
      },
      ...
    }
  },
  ...
}
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from common.utils import load_json, save_json, timestamp, get_logger

logger = get_logger("metadata_manager")

_DEFAULT_PATH = "master/metadata.json"


class MetadataManager:
    def __init__(self, store_path: str = _DEFAULT_PATH) -> None:
        self._path = Path(store_path)
        self._lock = threading.RLock()
        self._data: dict[str, Any] = load_json(self._path) or {}
        logger.info(f"MetadataManager loaded {len(self._data)} file record(s) from '{self._path}'")

    # ---------------------------------------------------------------- #
    #  Internal persistence                                              #
    # ---------------------------------------------------------------- #

    def _save(self) -> None:
        save_json(self._path, self._data)

    # ---------------------------------------------------------------- #
    #  File-level operations                                             #
    # ---------------------------------------------------------------- #

    def create_file(
        self,
        filename: str,
        file_hash: str,
        num_chunks: int,
        chunk_meta: list[dict],
    ) -> None:
        """Register a new file entry (before chunks are assigned to nodes)."""
        with self._lock:
            self._data[filename] = {
                "filename":    filename,
                "file_hash":   file_hash,
                "num_chunks":  num_chunks,
                "uploaded_at": timestamp(),
                "status":      "uploading",
                "chunks":      {
                    cm["chunk_id"]: {
                        "chunk_id": cm["chunk_id"],
                        "index":    cm.get("index", i),
                        "size":     cm["size"],
                        "hash":     cm["hash"],
                        "nodes":    [],
                    }
                    for i, cm in enumerate(chunk_meta)
                },
            }
            self._save()

    def mark_upload_complete(self, filename: str) -> None:
        with self._lock:
            if filename in self._data:
                self._data[filename]["status"] = "ready"
                self._save()

    def delete_file(self, filename: str) -> dict | None:
        with self._lock:
            record = self._data.pop(filename, None)
            if record:
                self._save()
            return record

    def get_file(self, filename: str) -> dict | None:
        with self._lock:
            return self._data.get(filename)

    def list_files(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "filename":   v["filename"],
                    "file_hash":  v["file_hash"],
                    "num_chunks": v["num_chunks"],
                    "status":     v.get("status", "unknown"),
                    "uploaded_at": v.get("uploaded_at", ""),
                }
                for v in self._data.values()
            ]

    # ---------------------------------------------------------------- #
    #  Chunk-level operations                                            #
    # ---------------------------------------------------------------- #

    def set_chunk_nodes(self, filename: str, chunk_id: str, node_ids: list[int]) -> None:
        """Record which nodes hold a particular chunk."""
        with self._lock:
            if filename in self._data and chunk_id in self._data[filename]["chunks"]:
                self._data[filename]["chunks"][chunk_id]["nodes"] = node_ids
                self._save()

    def add_chunk_node(self, filename: str, chunk_id: str, node_id: int) -> None:
        """Add a node to a chunk's replica list (used during re-replication)."""
        with self._lock:
            chunk = self._data.get(filename, {}).get("chunks", {}).get(chunk_id)
            if chunk and node_id not in chunk["nodes"]:
                chunk["nodes"].append(node_id)
                self._save()

    def remove_chunk_node(self, chunk_id: str, node_id: int) -> None:
        """Remove *node_id* from every chunk that referenced it."""
        with self._lock:
            changed = False
            for file_record in self._data.values():
                chunk = file_record["chunks"].get(chunk_id)
                if chunk and node_id in chunk["nodes"]:
                    chunk["nodes"].remove(node_id)
                    changed = True
            if changed:
                self._save()

    def remove_node_from_all_chunks(self, node_id: int) -> list[tuple[str, str]]:
        """
        Remove *node_id* from every chunk's node list.

        Returns list of (filename, chunk_id) pairs now under-replicated.
        """
        under_replicated: list[tuple[str, str]] = []
        with self._lock:
            from common.constants import REPLICATION_FACTOR
            for fname, file_record in self._data.items():
                for cid, chunk in file_record["chunks"].items():
                    if node_id in chunk["nodes"]:
                        chunk["nodes"].remove(node_id)
                    if len(chunk["nodes"]) < REPLICATION_FACTOR:
                        under_replicated.append((fname, cid))
            self._save()
        return under_replicated

    def get_chunks_for_file(self, filename: str) -> list[dict]:
        """Return ordered chunk descriptors for *filename*."""
        with self._lock:
            record = self._data.get(filename)
            if not record:
                return []
            return sorted(record["chunks"].values(), key=lambda c: c["index"])

    def all_chunks(self) -> list[tuple[str, dict]]:
        """Yield (filename, chunk_dict) for every chunk in the store."""
        with self._lock:
            result = []
            for fname, rec in self._data.items():
                for chunk in rec["chunks"].values():
                    result.append((fname, chunk))
            return result
