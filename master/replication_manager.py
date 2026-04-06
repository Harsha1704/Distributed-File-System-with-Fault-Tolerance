"""
replication_manager.py — Monitors replica health and triggers re-replication.
"""

from __future__ import annotations

import socket
import threading
import time

from common.constants import (
    REPLICATION_FACTOR,
    REPLICATION_CHECK_INTERVAL,
    SOCKET_TIMEOUT,
)
from common.utils import send_message, recv_message, send_bytes, recv_bytes, get_logger

logger = get_logger("replication_manager")


class ReplicationManager:
    def __init__(self, metadata_manager, node_manager) -> None:
        self._meta  = metadata_manager
        self._nodes = node_manager
        self._lock  = threading.Lock()

        self._checker = threading.Thread(
            target=self._periodic_check, daemon=True, name="ReplicationChecker"
        )
        self._checker.start()

        logger.info(
            f"ReplicationManager started "
            f"(interval={REPLICATION_CHECK_INTERVAL}s, factor={REPLICATION_FACTOR})"
        )

    # ---------------------------------------------------------------- #
    #  Node failure handler
    # ---------------------------------------------------------------- #

    def handle_node_failure(self, failed_node_id: int) -> None:
        logger.warning(f"Handling failure of node {failed_node_id}…")

        under = self._meta.remove_node_from_all_chunks(failed_node_id)

        if not under:
            logger.info(f"No affected chunks for node {failed_node_id}")
            return

        logger.info(f"{len(under)} chunk(s) need re-replication")

        for filename, chunk_id in under:
            self._rereplicate(filename, chunk_id)

    # ---------------------------------------------------------------- #
    #  Periodic health check
    # ---------------------------------------------------------------- #

    def _periodic_check(self) -> None:
        while True:
            time.sleep(REPLICATION_CHECK_INTERVAL)
            self._check_all_chunks()

    def _check_all_chunks(self) -> None:
        live_nodes = self._nodes.live_nodes()
        live_ids = {n.node_id for n in live_nodes}
        total_alive = len(live_ids)

        for filename, chunk in self._meta.all_chunks():

            healthy = [nid for nid in chunk["nodes"] if nid in live_ids]

            if len(healthy) < REPLICATION_FACTOR:

                # 🔥 IMPORTANT FIX: skip if replication impossible
                if total_alive <= len(healthy):
                    logger.warning(
                        f"Skipping repair {chunk['chunk_id']} — "
                        f"no extra nodes available "
                        f"(alive={total_alive}, have={len(healthy)})"
                    )
                    continue

                logger.info(
                    f"Under-replicated: {chunk['chunk_id']} "
                    f"({len(healthy)}/{REPLICATION_FACTOR}) → repairing"
                )

                self._rereplicate(filename, chunk["chunk_id"])

    # ---------------------------------------------------------------- #
    #  Core re-replication logic
    # ---------------------------------------------------------------- #

    def _rereplicate(self, filename: str, chunk_id: str) -> None:

        file_record = self._meta.get_file(filename)
        if not file_record:
            return

        chunk = file_record["chunks"].get(chunk_id)
        if not chunk:
            return

        live_nodes = self._nodes.live_nodes()
        live_ids = {n.node_id for n in live_nodes}

        have_ids = [nid for nid in chunk["nodes"] if nid in live_ids]
        need = REPLICATION_FACTOR - len(have_ids)

        if need <= 0:
            return

        # 🔥 FIX: check available nodes BEFORE trying
        available_nodes = [
            n for n in live_nodes
            if n.node_id not in have_ids
        ]

        if not available_nodes:
            logger.warning(
                f"No nodes available to re-replicate {chunk_id} "
                f"(have={have_ids})"
            )
            return

        # ------------------------------------------------------------ #
        # Fetch chunk from existing replica
        # ------------------------------------------------------------ #

        data = None

        for src_id in have_ids:
            src = self._nodes.get_node(src_id)
            if not src:
                continue

            try:
                data = self._fetch_chunk(src.host, src.port, chunk_id)
                break
            except Exception as exc:
                logger.warning(f"Fetch failed from node {src_id}: {exc}")

        if data is None:
            logger.error(f"LOST CHUNK: {chunk_id} — no replicas left!")
            return

        # ------------------------------------------------------------ #
        # Select new nodes safely
        # ------------------------------------------------------------ #

        candidates = self._nodes.pick_nodes_for_chunk(exclude=have_ids)

        if not candidates:
            logger.warning(
                f"Replication failed for {chunk_id} — no eligible nodes"
            )
            return

        new_nodes = candidates[:need]

        # ------------------------------------------------------------ #
        # Store chunk on new nodes
        # ------------------------------------------------------------ #

        for target in new_nodes:
            try:
                self._store_chunk(
                    target.host,
                    target.port,
                    chunk_id,
                    data,
                    chunk["hash"],
                    chunk["index"]
                )

                self._meta.add_chunk_node(
                    filename,
                    chunk_id,
                    target.node_id
                )

                logger.info(
                    f"Re-replicated {chunk_id} → node {target.node_id}"
                )

            except Exception as exc:
                logger.error(
                    f"Replication to node {target.node_id} failed: {exc}"
                )

    # ---------------------------------------------------------------- #
    #  Node communication
    # ---------------------------------------------------------------- #

    @staticmethod
    def _fetch_chunk(host: str, port: int, chunk_id: str) -> bytes:
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as sock:
            send_message(sock, {"action": "FETCH_CHUNK", "chunk_id": chunk_id})
            return recv_bytes(sock)

    @staticmethod
    def _store_chunk(
        host: str, port: int, chunk_id: str, data: bytes, chunk_hash: str, index: int
    ) -> None:
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as sock:
            send_message(sock, {
                "action":   "STORE_CHUNK",
                "chunk_id": chunk_id,
                "hash":     chunk_hash,
                "index":    index,
            })

            send_bytes(sock, data)

            ack = recv_message(sock)

            if ack.get("status") != "OK":
                raise RuntimeError(ack.get("reason"))