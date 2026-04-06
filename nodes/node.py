"""
node.py — Storage node server for the DFS.

Each node:
  • Stores chunk files on disk
  • Serves STORE_CHUNK / FETCH_CHUNK / DELETE_CHUNK requests over TCP
  • Sends periodic heartbeats to the master (both TCP and UDP)

Run as:
    python -m nodes.node1.node   # NODE_ID resolved from package name
or:
    NODE_ID=2 python node.py
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from common.constants import (
    NODE_BASE_PORT,
    MASTER_PORT,
    HEARTBEAT_INTERVAL,
    SOCKET_TIMEOUT,
    BUFFER_SIZE,
)
from common.hashing import verify_chunk
from common.utils import (
    send_message,
    recv_message,
    send_bytes,
    recv_bytes,
    get_logger,
    ensure_dir,
)

MASTER_HOST = os.environ.get("MASTER_HOST", "127.0.0.1")

# ------------------------------------------------------------------ #
#  Resolve NODE_ID                                                     #
# ------------------------------------------------------------------ #
# Priority: env var NODE_ID > parent directory name > default 1
def _resolve_node_id() -> int:
    env_val = os.environ.get("NODE_ID")
    if env_val:
        return int(env_val)
    # When run as   python -m nodes.node2.node  →  __package__ = "nodes.node2"
    pkg = __package__ or ""
    for part in reversed(pkg.split(".")):
        if part.startswith("node") and part[4:].isdigit():
            return int(part[4:])
    return 1


NODE_ID   = _resolve_node_id()
NODE_PORT = NODE_BASE_PORT + NODE_ID - 1
STORAGE_DIR = Path(f"nodes/storage/node{NODE_ID}")

logger = get_logger(f"node{NODE_ID}", f"logs/node{NODE_ID}.log")


# ------------------------------------------------------------------ #
#  Storage helpers                                                     #
# ------------------------------------------------------------------ #

def _chunk_path(chunk_id: str) -> Path:
    return STORAGE_DIR / f"{chunk_id}.chunk"


def store_chunk(chunk_id: str, data: bytes, expected_hash: str) -> None:
    verify_chunk(data, expected_hash)
    ensure_dir(STORAGE_DIR)
    _chunk_path(chunk_id).write_bytes(data)
    logger.debug(f"Stored chunk {chunk_id} ({len(data)} bytes)")


def fetch_chunk(chunk_id: str) -> bytes:
    p = _chunk_path(chunk_id)
    if not p.exists():
        raise FileNotFoundError(f"Chunk not found: {chunk_id}")
    return p.read_bytes()


def delete_chunk(chunk_id: str) -> None:
    p = _chunk_path(chunk_id)
    if p.exists():
        p.unlink()
        logger.debug(f"Deleted chunk {chunk_id}")


# ------------------------------------------------------------------ #
#  Request handler                                                     #
# ------------------------------------------------------------------ #

def _handle_connection(conn: socket.socket, addr: tuple) -> None:
    try:
        with conn:
            msg    = recv_message(conn)
            action = msg.get("action", "")

            if action == "STORE_CHUNK":
                chunk_id = msg["chunk_id"]
                expected = msg["hash"]
                data     = recv_bytes(conn)
                try:
                    store_chunk(chunk_id, data, expected)
                    send_message(conn, {"status": "OK"})
                except ValueError as exc:
                    logger.error(f"Integrity failure storing {chunk_id}: {exc}")
                    send_message(conn, {"status": "ERROR", "reason": str(exc)})

            elif action == "FETCH_CHUNK":
                chunk_id = msg["chunk_id"]
                try:
                    data = fetch_chunk(chunk_id)
                    send_message(conn, {"status": "OK"})
                    send_bytes(conn, data)
                except FileNotFoundError as exc:
                    send_message(conn, {"status": "ERROR", "reason": str(exc)})

            elif action == "DELETE_CHUNK":
                chunk_id = msg["chunk_id"]
                delete_chunk(chunk_id)
                send_message(conn, {"status": "OK"})

            elif action == "LIST_CHUNKS":
                ensure_dir(STORAGE_DIR)
                chunks = [p.stem for p in STORAGE_DIR.glob("*.chunk")]
                send_message(conn, {"status": "OK", "chunks": chunks})

            elif action == "PING":
                send_message(conn, {"status": "OK", "node_id": NODE_ID})

            else:
                send_message(conn, {"status": "ERROR", "reason": f"Unknown action: {action}"})

    except Exception as exc:
        logger.warning(f"Error handling {addr}: {exc}")


# ------------------------------------------------------------------ #
#  Heartbeat sender                                                    #
# ------------------------------------------------------------------ #

def _send_heartbeats() -> None:
    """Send periodic TCP heartbeats to the master."""
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        try:
            with socket.create_connection((MASTER_HOST, MASTER_PORT), timeout=5) as sock:
                send_message(sock, {
                    "action":  "HEARTBEAT",
                    "node_id": NODE_ID,
                    "host":    "127.0.0.1",
                    "port":    NODE_PORT,
                })
                recv_message(sock)
        except Exception as exc:
            logger.debug(f"Heartbeat to master failed: {exc}")


def _send_udp_heartbeats() -> None:
    """Send periodic UDP heartbeats (faster, lower overhead)."""
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = json.dumps({"node_id": NODE_ID, "port": NODE_PORT}).encode("utf-8")
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        try:
            udp.sendto(payload, (MASTER_HOST, MASTER_PORT + 1))
        except Exception:
            pass


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    ensure_dir(STORAGE_DIR)
    logger.info(f"Node {NODE_ID} starting on port {NODE_PORT} (storage: {STORAGE_DIR})")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", NODE_PORT))
    server.listen(50)

    # Start heartbeat threads
    threading.Thread(target=_send_heartbeats,     daemon=True, name="TCPHeartbeat").start()
    threading.Thread(target=_send_udp_heartbeats, daemon=True, name="UDPHeartbeat").start()

    logger.info(f"Node {NODE_ID} ready — listening on port {NODE_PORT}")

    while True:
        try:
            conn, addr = server.accept()
            conn.settimeout(SOCKET_TIMEOUT)
            threading.Thread(
                target=_handle_connection, args=(conn, addr), daemon=True
            ).start()
        except Exception as exc:
            logger.error(f"Accept error: {exc}")


if __name__ == "__main__":
    main()
