"""
master.py — Central coordinator for the Distributed File System.

Responsibilities:
  • Accept client connections (upload plan, download plan, list, delete)
  • Accept node heartbeats
  • Delegate to MetadataManager, NodeManager, ReplicationManager
"""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

# Ensure project root is on the path when run as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.constants import MASTER_PORT, NODE_BASE_PORT, REPLICATION_FACTOR
from common.utils import send_message, recv_message, get_logger
from master.metadata_manager   import MetadataManager
from master.node_manager       import NodeManager
from master.replication_manager import ReplicationManager

logger = get_logger("master", "logs/master.log")

HEARTBEAT_PORT = MASTER_PORT + 1   # 9001 — lightweight UDP heartbeat listener


class MasterServer:
    def __init__(self, host: str = "0.0.0.0", port: int = MASTER_PORT) -> None:
        self._host = host
        self._port = port

        self._meta  = MetadataManager()
        self._nodes = NodeManager()
        self._repli = ReplicationManager(self._meta, self._nodes)

        # Pre-register the three default nodes
        for node_id in range(1, 4):
            self._nodes.register_node(node_id, "127.0.0.1", NODE_BASE_PORT + node_id - 1)

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((host, port))
        self._server_sock.listen(50)

        # Start heartbeat listener in background
        threading.Thread(target=self._heartbeat_listener, daemon=True,
                         name="HeartbeatListener").start()

    # ---------------------------------------------------------------- #
    #  Main accept loop                                                  #
    # ---------------------------------------------------------------- #

    def serve_forever(self) -> None:
        logger.info(f"Master listening on {self._host}:{self._port}")
        while True:
            try:
                conn, addr = self._server_sock.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True,
                ).start()
            except Exception as exc:
                logger.error(f"Accept error: {exc}")

    # ---------------------------------------------------------------- #
    #  Request dispatcher                                                #
    # ---------------------------------------------------------------- #

    def _handle_client(self, conn: socket.socket, addr: tuple) -> None:
        try:
            with conn:
                msg = recv_message(conn)
                action = msg.get("action", "")
                logger.debug(f"{addr} → {action}")

                handlers = {
                    "UPLOAD_PLAN":     self._handle_upload_plan,
                    "UPLOAD_COMPLETE": self._handle_upload_complete,
                    "DOWNLOAD_PLAN":   self._handle_download_plan,
                    "LIST_FILES":      self._handle_list_files,
                    "DELETE_FILE":     self._handle_delete_file,
                    "HEARTBEAT":       self._handle_heartbeat,
                    "NODE_STATUS":     self._handle_node_status,
                }

                handler = handlers.get(action)
                if handler:
                    response = handler(msg)
                else:
                    response = {"status": "ERROR", "reason": f"Unknown action: {action}"}

                send_message(conn, response)
        except Exception as exc:
            logger.warning(f"Error handling {addr}: {exc}")

    # ---------------------------------------------------------------- #
    #  Handlers                                                          #
    # ---------------------------------------------------------------- #

    def _handle_upload_plan(self, msg: dict) -> dict:
        filename   = msg["filename"]
        chunk_meta = msg["chunk_meta"]     # [{chunk_id, size, hash}, ...]
        file_hash  = msg["file_hash"]
        num_chunks = msg["num_chunks"]

        self._meta.create_file(filename, file_hash, num_chunks, chunk_meta)

        live = self._nodes.live_nodes()
        if not live:
            return {"status": "ERROR", "reason": "No live storage nodes available."}

        assignments = []
        for i, cm in enumerate(chunk_meta):
            nodes = self._nodes.pick_nodes_for_chunk()
            node_addrs = [n.address for n in nodes]
            # Record planned node IDs in metadata
            self._meta.set_chunk_nodes(filename, cm["chunk_id"], [n.node_id for n in nodes])
            assignments.append({"chunk_id": cm["chunk_id"], "nodes": node_addrs})

        logger.info(f"Upload plan for '{filename}': {num_chunks} chunk(s), "
                    f"{len(live)} live node(s)")
        return {"status": "OK", "assignments": assignments}

    def _handle_upload_complete(self, msg: dict) -> dict:
        filename = msg["filename"]
        self._meta.mark_upload_complete(filename)
        logger.info(f"Upload complete: '{filename}'")
        return {"status": "OK", "message": f"'{filename}' is now available."}

    def _handle_download_plan(self, msg: dict) -> dict:
        filename = msg["filename"]
        record   = self._meta.get_file(filename)
        if not record:
            return {"status": "ERROR", "reason": f"File '{filename}' not found."}

        live_ids = {n.node_id for n in self._nodes.live_nodes()}
        chunks_out = []

        for chunk in self._meta.get_chunks_for_file(filename):
            live_nodes = [
                self._nodes.get_node(nid).address
                for nid in chunk["nodes"]
                if nid in live_ids and self._nodes.get_node(nid) is not None
            ]
            if not live_nodes:
                return {
                    "status": "ERROR",
                    "reason": f"Chunk {chunk['chunk_id']} is unavailable (all replicas down).",
                }
            chunks_out.append({
                "chunk_id": chunk["chunk_id"],
                "index":    chunk["index"],
                "hash":     chunk["hash"],
                "nodes":    live_nodes,
            })

        return {
            "status":    "OK",
            "filename":  filename,
            "file_hash": record["file_hash"],
            "chunks":    chunks_out,
        }

    def _handle_list_files(self, _msg: dict) -> dict:
        return {"status": "OK", "files": self._meta.list_files()}

    def _handle_delete_file(self, msg: dict) -> dict:
        filename = msg["filename"]
        record   = self._meta.delete_file(filename)
        if not record:
            return {"status": "ERROR", "reason": f"File '{filename}' not found."}
        # Best-effort deletion from nodes (ignore errors)
        live_ids = {n.node_id for n in self._nodes.live_nodes()}
        for chunk in record["chunks"].values():
            for nid in chunk["nodes"]:
                if nid not in live_ids:
                    continue
                node = self._nodes.get_node(nid)
                if node:
                    try:
                        self._delete_chunk_on_node(node.host, node.port, chunk["chunk_id"])
                    except Exception:
                        pass
        logger.info(f"Deleted '{filename}' from DFS")
        return {"status": "OK", "message": f"'{filename}' deleted."}

    def _handle_heartbeat(self, msg: dict) -> dict:
        node_id = msg.get("node_id")
        host    = msg.get("host", "127.0.0.1")
        port    = msg.get("port")
        if node_id:
            self._nodes.heartbeat(node_id, host, port)
        return {"status": "OK"}

    def _handle_node_status(self, _msg: dict) -> dict:
        return {"status": "OK", "nodes": self._nodes.all_nodes()}

    # ---------------------------------------------------------------- #
    #  UDP heartbeat listener (alternative to TCP)                       #
    # ---------------------------------------------------------------- #

    def _heartbeat_listener(self) -> None:
        import json
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(("0.0.0.0", HEARTBEAT_PORT))
        logger.info(f"UDP heartbeat listener on port {HEARTBEAT_PORT}")
        while True:
            try:
                data, addr = udp.recvfrom(512)
                msg = json.loads(data.decode("utf-8"))
                node_id = msg.get("node_id")
                if node_id:
                    self._nodes.heartbeat(node_id, addr[0], msg.get("port"))
            except Exception:
                pass

    # ---------------------------------------------------------------- #
    #  Helper                                                            #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _delete_chunk_on_node(host: str, port: int, chunk_id: str) -> None:
        from common.constants import SOCKET_TIMEOUT
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as sock:
            send_message(sock, {"action": "DELETE_CHUNK", "chunk_id": chunk_id})
            recv_message(sock)


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    server = MasterServer()
    server.serve_forever()


if __name__ == "__main__":
    main()
