"""
client.py — Command-line interface to the Distributed File System.

Usage:
    python -m client.client upload   <local_file>
    python -m client.client download <remote_filename>
    python -m client.client list
    python -m client.client delete   <remote_filename>
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

from client.config import MASTER_HOST, MASTER_PORT, DOWNLOAD_DIR
from client.client_utils import prepare_upload, assemble_download
from common.utils import send_message, recv_message, send_bytes, recv_bytes, get_logger, ensure_dir
from common.constants import SOCKET_TIMEOUT

logger = get_logger("client", "logs/client.log")


# ------------------------------------------------------------------ #
#  Transport helpers                                                   #
# ------------------------------------------------------------------ #

def _master_conn() -> socket.socket:
    """Open a TCP connection to the master node."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT)
    sock.connect((MASTER_HOST, MASTER_PORT))
    return sock


def _node_conn(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT)
    sock.connect((host, port))
    return sock


# ------------------------------------------------------------------ #
#  DFS operations                                                      #
# ------------------------------------------------------------------ #

def upload(local_path: str) -> None:
    """
    1. Split file into chunks.
    2. Ask master for upload plan (which nodes to use for each chunk).
    3. Push each chunk to its assigned nodes.
    4. Confirm success to master.
    """
    file_path = Path(local_path)
    if not file_path.exists():
        logger.error(f"File not found: {local_path}")
        sys.exit(1)

    chunks, file_hash = prepare_upload(file_path)

    # --- Request upload plan from master ---
    with _master_conn() as sock:
        send_message(sock, {
            "action":     "UPLOAD_PLAN",
            "filename":   file_path.name,
            "num_chunks": len(chunks),
            "file_hash":  file_hash,
            "chunk_meta": [{"chunk_id": c["chunk_id"], "size": c["size"], "hash": c["hash"]}
                           for c in chunks],
        })
        plan = recv_message(sock)

    if plan.get("status") != "OK":
        logger.error(f"Master rejected upload: {plan.get('reason')}")
        sys.exit(1)

    logger.info("Upload plan received. Pushing chunks to storage nodes …")

    # plan["assignments"] = [{"chunk_id": str, "nodes": [{"host": str, "port": int}]}, ...]
    chunk_map = {c["chunk_id"]: c for c in chunks}

    for assignment in plan["assignments"]:
        chunk_id = assignment["chunk_id"]
        chunk    = chunk_map[chunk_id]
        errors   = []

        for node_info in assignment["nodes"]:
            host, port = node_info["host"], node_info["port"]
            try:
                with _node_conn(host, port) as nsock:
                    send_message(nsock, {
                        "action":   "STORE_CHUNK",
                        "chunk_id": chunk_id,
                        "hash":     chunk["hash"],
                        "index":    chunk["index"],
                    })
                    send_bytes(nsock, chunk["data"])
                    ack = recv_message(nsock)
                    if ack.get("status") != "OK":
                        errors.append(f"{host}:{port} → {ack.get('reason')}")
            except Exception as exc:
                errors.append(f"{host}:{port} → {exc}")

        if errors:
            logger.warning(f"Chunk {chunk_id} partial failure: {errors}")
        else:
            logger.info(f"  [OK] {chunk_id} stored on {len(assignment['nodes'])} node(s)")

    # --- Notify master that upload is complete ---
    with _master_conn() as sock:
        send_message(sock, {"action": "UPLOAD_COMPLETE", "filename": file_path.name})
        result = recv_message(sock)

    logger.info(f"Upload complete: {result}")


def download(remote_filename: str) -> None:
    """
    1. Ask master for chunk locations.
    2. Fetch each chunk from a live node.
    3. Verify & reassemble the file locally.
    """
    # --- Get chunk locations from master ---
    with _master_conn() as sock:
        send_message(sock, {"action": "DOWNLOAD_PLAN", "filename": remote_filename})
        plan = recv_message(sock)

    if plan.get("status") != "OK":
        logger.error(f"Master error: {plan.get('reason')}")
        sys.exit(1)

    logger.info(f"Download plan for '{remote_filename}': {len(plan['chunks'])} chunk(s)")

    chunk_descriptors = []

    for chunk_info in plan["chunks"]:
        chunk_id = chunk_info["chunk_id"]
        fetched  = False

        for node_info in chunk_info["nodes"]:
            host, port = node_info["host"], node_info["port"]
            try:
                with _node_conn(host, port) as nsock:
                    send_message(nsock, {"action": "FETCH_CHUNK", "chunk_id": chunk_id})
                    status = recv_message(nsock)
                    if status.get("status") != "OK":
                        raise RuntimeError(status.get("reason", "Node error"))
                    data = recv_bytes(nsock)
                    chunk_descriptors.append({
                        "index": chunk_info["index"],
                        "data":  data,
                        "hash":  chunk_info["hash"],
                    })
                    logger.info(f"  [OK] {chunk_id} <- {host}:{port}")
                    fetched = True
                    break
            except Exception as exc:
                logger.warning(f"  Node {host}:{port} failed for {chunk_id}: {exc}")

        if not fetched:
            logger.error(f"Could not fetch chunk {chunk_id} from any node!")
            sys.exit(1)

    ensure_dir(DOWNLOAD_DIR)
    output = Path(DOWNLOAD_DIR) / remote_filename
    assemble_download(chunk_descriptors, output, plan.get("file_hash"))
    print(f"\n[OK] Downloaded → {output}")


def list_files() -> None:
    """Print all files stored in the DFS."""
    with _master_conn() as sock:
        send_message(sock, {"action": "LIST_FILES"})
        response = recv_message(sock)

    files = response.get("files", [])
    if not files:
        print("(no files stored)")
        return
    print(f"\n{'Filename':<40} {'Chunks':>6}  {'Hash (prefix)':>14}")
    print("-" * 65)
    for f in files:
        print(f"{f['filename']:<40} {f['num_chunks']:>6}  {f['file_hash'][:12]:>14}")


def delete_file(remote_filename: str) -> None:
    """Delete a file from the DFS (all chunks on all nodes)."""
    with _master_conn() as sock:
        send_message(sock, {"action": "DELETE_FILE", "filename": remote_filename})
        response = recv_message(sock)
    print(f"Delete: {response}")


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "upload" and len(sys.argv) == 3:
        upload(sys.argv[2])
    elif cmd == "download" and len(sys.argv) == 3:
        download(sys.argv[2])
    elif cmd == "list":
        list_files()
    elif cmd == "delete" and len(sys.argv) == 3:
        delete_file(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
