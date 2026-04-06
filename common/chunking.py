"""
chunking.py — Split a file into fixed-size chunks and reassemble them.

Each chunk is identified by:
    <original_filename>_chunk_<index>

The module also attaches SHA-256 hashes so the caller can pass them to
hashing.verify_chunk() before writing to disk.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from common.constants import CHUNK_SIZE
from common.hashing import hash_bytes


# ------------------------------------------------------------------ #
#  Splitting                                                           #
# ------------------------------------------------------------------ #

def split_file(
    file_path: str | Path,
    chunk_size: int = CHUNK_SIZE,
) -> list[dict]:
    """
    Split *file_path* into chunks of *chunk_size* bytes.

    Returns a list of chunk descriptors (ordered by index):
    [
        {
            "index":      int,
            "chunk_id":   str,   # "<stem>_chunk_<index>"
            "data":       bytes,
            "size":       int,
            "hash":       str,   # SHA-256 hex of chunk data
        },
        ...
    ]
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    stem = file_path.stem
    chunks: list[dict] = []
    index = 0

    with open(file_path, "rb") as fh:
        while True:
            data = fh.read(chunk_size)
            if not data:
                break
            chunk_id = f"{stem}_chunk_{index}"
            chunks.append(
                {
                    "index":    index,
                    "chunk_id": chunk_id,
                    "data":     data,
                    "size":     len(data),
                    "hash":     hash_bytes(data),
                }
            )
            index += 1

    return chunks


def split_file_lazy(
    file_path: str | Path,
    chunk_size: int = CHUNK_SIZE,
) -> Generator[dict, None, None]:
    """
    Generator version of split_file — yields one chunk descriptor at a time.
    Useful when the file is too large to hold entirely in memory.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    stem = file_path.stem
    index = 0

    with open(file_path, "rb") as fh:
        while True:
            data = fh.read(chunk_size)
            if not data:
                break
            yield {
                "index":    index,
                "chunk_id": f"{stem}_chunk_{index}",
                "data":     data,
                "size":     len(data),
                "hash":     hash_bytes(data),
            }
            index += 1


# ------------------------------------------------------------------ #
#  Merging                                                             #
# ------------------------------------------------------------------ #

def merge_chunks(
    chunks: list[dict],
    output_path: str | Path,
) -> Path:
    """
    Merge an ordered list of chunk descriptors into *output_path*.

    *chunks* must be a list of dicts with at least:
        {"index": int, "data": bytes}

    Returns the resolved output Path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(chunks, key=lambda c: c["index"])
    with open(output_path, "wb") as fh:
        for chunk in ordered:
            fh.write(chunk["data"])

    return output_path


def merge_chunk_files(
    chunk_files: list[str | Path],
    output_path: str | Path,
) -> Path:
    """
    Merge already-saved chunk files (sorted by their embedded index) into
    *output_path*.

    Chunk filenames must contain ``_chunk_<index>`` so they can be ordered.
    """
    def _extract_index(p: Path) -> int:
        # filename pattern: <stem>_chunk_<index>[.ext]
        stem = p.stem
        try:
            return int(stem.rsplit("_chunk_", 1)[-1])
        except ValueError:
            return 0

    paths = sorted([Path(p) for p in chunk_files], key=_extract_index)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as out_fh:
        for cp in paths:
            with open(cp, "rb") as in_fh:
                for block in iter(lambda: in_fh.read(65536), b""):
                    out_fh.write(block)

    return output_path
