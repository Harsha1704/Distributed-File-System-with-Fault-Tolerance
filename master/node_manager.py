"""
node_manager.py — Tracks live storage nodes via heartbeat.

Each storage node sends a periodic UDP heartbeat to the master.
This module maintains a registry of nodes and their last-seen times,
then exposes helpers to pick live nodes for chunk placement.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any

from common.constants import (
    NODE_TIMEOUT,
    HEARTBEAT_INTERVAL,
    NODE_BASE_PORT,
    REPLICATION_FACTOR,
)
from common.utils import get_logger

logger = get_logger("node_manager")


class NodeInfo:
    def __init__(self, node_id: int, host: str, port: int) -> None:
        self.node_id   = node_id
        self.host      = host
        self.port      = port
        self.last_seen = time.time()
        self.alive     = True

    @property
    def address(self) -> dict:
        return {"host": self.host, "port": self.port, "node_id": self.node_id}

    def __repr__(self) -> str:
        status = "ALIVE" if self.alive else "DEAD"
        return f"Node({self.node_id}, {self.host}:{self.port}, {status})"


class NodeManager:

    def __init__(self) -> None:
        self._nodes: dict[int, NodeInfo] = {}
        self._lock  = threading.RLock()

        self._watchdog_thread = threading.Thread(
            target=self._watchdog, daemon=True, name="NodeWatchdog"
        )
        self._watchdog_thread.start()

        logger.info("NodeManager started (watchdog active)")

    # ---------------------------------------------------------------- #
    #  Registration & heartbeat
    # ---------------------------------------------------------------- #

    def register_node(self, node_id: int, host: str, port: int) -> None:
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = NodeInfo(node_id, host, port)
                logger.info(f"Registered {self._nodes[node_id]}")

    def heartbeat(self, node_id: int, host: str | None = None, port: int | None = None) -> None:
        """Update last-seen timestamp; registers the node if unknown."""
        with self._lock:
            if node_id not in self._nodes:
                h = host or "127.0.0.1"
                p = port or (NODE_BASE_PORT + node_id - 1)
                self._nodes[node_id] = NodeInfo(node_id, h, p)
                logger.info(f"Auto-registered node {node_id} via heartbeat")

            node = self._nodes[node_id]

            # 🔥 CRITICAL FIX: always update heartbeat AND mark alive
            node.last_seen = time.time()

            if not node.alive:
                logger.info(f"Node {node_id} came back ONLINE")

            node.alive = True  # ✅ ENSURE node becomes alive again

            logger.debug(f"Heartbeat received from Node {node_id}")

    # ---------------------------------------------------------------- #
    #  Queries
    # ---------------------------------------------------------------- #

    def live_nodes(self) -> list[NodeInfo]:
        with self._lock:
            alive_nodes = [n for n in self._nodes.values() if n.alive]
            return alive_nodes

    def get_node(self, node_id: int) -> NodeInfo | None:
        with self._lock:
            return self._nodes.get(node_id)

    def pick_nodes_for_chunk(self, exclude: list[int] | None = None) -> list[NodeInfo]:
        """
        Return up to REPLICATION_FACTOR live nodes for chunk placement.
        Nodes in *exclude* are skipped (used during re-replication).
        """
        exclude = exclude or []

        with self._lock:
            candidates = [
                n for n in self._nodes.values()
                if n.alive and n.node_id not in exclude
            ]

        # 🔥 Improved logging clarity
        if len(candidates) < REPLICATION_FACTOR:
            logger.warning(
                f"Only {len(candidates)} live node(s) available "
                f"(replication factor = {REPLICATION_FACTOR})"
            )

        random.shuffle(candidates)
        return candidates[:REPLICATION_FACTOR]

    def all_nodes(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "node_id": n.node_id,
                    "host":    n.host,
                    "port":    n.port,
                    "alive":   n.alive,
                    "last_seen": n.last_seen,
                }
                for n in self._nodes.values()
            ]

    # ---------------------------------------------------------------- #
    #  Watchdog
    # ---------------------------------------------------------------- #

    def _watchdog(self) -> None:
        """Background thread: marks nodes DEAD if heartbeat times out."""
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            now = time.time()

            with self._lock:
                for node in self._nodes.values():
                    if node.alive and (now - node.last_seen) > NODE_TIMEOUT:
                        node.alive = False
                        logger.warning(
                            f"Node {node.node_id} timed out — marked DEAD "
                            f"(last seen {now - node.last_seen:.1f}s ago)"
                        )