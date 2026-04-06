"""
master.py — Central coordinator for the Distributed File System.
"""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

# Fix encoding (optional but safe)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.constants import MASTER_PORT, NODE_BASE_PORT
from common.utils import send_message, recv_message, get_logger
from master.metadata_manager import MetadataManager
from master.node_manager import NodeManager
from master.replication_manager import ReplicationManager

logger = get_logger("master", "logs/master.log")

HEARTBEAT_PORT = MASTER_PORT + 1


class MasterServer:

    def __init__(self, host: str = "0.0.0.0", port: int = MASTER_PORT):
        self._host = host
        self._port = port

        self._meta = MetadataManager()
        self._nodes = NodeManager()
        self._repli = ReplicationManager(self._meta, self._nodes)

        # Register default nodes
        for node_id in range(1, 4):
            self._nodes.register_node(
                node_id, "127.0.0.1", NODE_BASE_PORT + node_id - 1
            )

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((host, port))
        self._server_sock.listen(50)

        threading.Thread(
            target=self._heartbeat_listener,
            daemon=True
        ).start()

    # ---------------- MAIN LOOP ---------------- #

    def serve_forever(self):
        logger.info(f"Master listening on {self._host}:{self._port}")
        while True:
            try:
                conn, addr = self._server_sock.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
            except Exception as e:
                logger.exception(f"Accept error: {e}")

    # ---------------- CLIENT HANDLER ---------------- #

    def _handle_client(self, conn, addr):
        try:
            with conn:
                msg = recv_message(conn)
                action = msg.get("action", "")

                # ✅ FIXED (no Unicode)
                logger.debug(f"{addr} -> {action}")

                handlers = {
                    "UPLOAD_PLAN": self._handle_upload_plan,
                    "UPLOAD_COMPLETE": self._handle_upload_complete,
                    "DOWNLOAD_PLAN": self._handle_download_plan,
                    "LIST_FILES": self._handle_list_files,
                    "DELETE_FILE": self._handle_delete_file,
                    "HEARTBEAT": self._handle_heartbeat,
                    "NODE_STATUS": self._handle_node_status,
                }

                handler = handlers.get(action)

                if handler:
                    response = handler(msg)
                else:
                    response = {"status": "ERROR", "reason": "Unknown action"}

                send_message(conn, response)

        except Exception as e:
            logger.exception(f"Client error {addr}: {e}")

    # ---------------- HANDLERS ---------------- #

    def _handle_upload_plan(self, msg):
        filename = msg["filename"]
        chunk_meta = msg["chunk_meta"]
        file_hash = msg["file_hash"]
        num_chunks = msg["num_chunks"]

        self._meta.create_file(filename, file_hash, num_chunks, chunk_meta)

        live = self._nodes.live_nodes()
        if not live:
            return {"status": "ERROR", "reason": "No nodes available"}

        assignments = []

        for cm in chunk_meta:
            nodes = self._nodes.pick_nodes_for_chunk()

            self._meta.set_chunk_nodes(
                filename,
                cm["chunk_id"],
                [n.node_id for n in nodes]
            )

            assignments.append({
                "chunk_id": cm["chunk_id"],
                "nodes": [n.address for n in nodes]
            })

        return {"status": "OK", "assignments": assignments}

    def _handle_upload_complete(self, msg):
        self._meta.mark_upload_complete(msg["filename"])
        return {"status": "OK"}

    def _handle_download_plan(self, msg):
        filename = msg["filename"]
        record = self._meta.get_file(filename)

        if not record:
            return {"status": "ERROR", "reason": "File not found"}

        live_ids = {n.node_id for n in self._nodes.live_nodes()}
        chunks = []

        for chunk in self._meta.get_chunks_for_file(filename):
            nodes = [
                self._nodes.get_node(nid).address
                for nid in chunk["nodes"]
                if nid in live_ids
            ]

            if not nodes:
                return {"status": "ERROR", "reason": "Chunk unavailable"}

            chunks.append({
                "chunk_id": chunk["chunk_id"],
                "index": chunk["index"],
                "hash": chunk["hash"],
                "nodes": nodes
            })

        return {
            "status": "OK",
            "filename": filename,
            "file_hash": record["file_hash"],
            "chunks": chunks
        }

    def _handle_list_files(self, _):
        return {"status": "OK", "files": self._meta.list_files()}

    def _handle_delete_file(self, msg):
        record = self._meta.delete_file(msg["filename"])
        if not record:
            return {"status": "ERROR", "reason": "File not found"}
        return {"status": "OK"}

    def _handle_heartbeat(self, msg):
        node_id = msg.get("node_id")
        if node_id:
            self._nodes.heartbeat(node_id, msg.get("host"), msg.get("port"))
        return {"status": "OK"}

    def _handle_node_status(self, _):
        return {"status": "OK", "nodes": self._nodes.all_nodes()}

    # ---------------- HEARTBEAT ---------------- #

    def _heartbeat_listener(self):
        import json

        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(("0.0.0.0", HEARTBEAT_PORT))

        while True:
            try:
                data, addr = udp.recvfrom(512)
                msg = json.loads(data.decode())

                if msg.get("node_id"):
                    self._nodes.heartbeat(msg["node_id"], addr[0], msg.get("port"))

            except Exception:
                pass


# ---------------- ENTRY ---------------- #

def main():
    server = MasterServer()
    server.serve_forever()


if __name__ == "__main__":
    main()