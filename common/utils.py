"""
utils.py — Shared helper functions used across client, master, and nodes.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import struct
import time
from pathlib import Path
from typing import Any

from common.constants import BUFFER_SIZE, ENCODING, LOG_FORMAT, DATE_FORMAT


# ------------------------------------------------------------------ #
#  Logging                                                             #
# ------------------------------------------------------------------ #

def get_logger(name: str, log_file: str | None = None, level=logging.DEBUG) -> logging.Logger:
    """
    Return a configured Logger.
    If *log_file* is given, logs are written there **and** to stdout.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


# ------------------------------------------------------------------ #
#  JSON message framing over raw TCP                                   #
# ------------------------------------------------------------------ #
# Protocol: 4-byte big-endian length prefix  +  UTF-8 JSON payload

def send_message(sock: socket.socket, payload: dict) -> None:
    """Serialize *payload* to JSON and send over *sock* with a length prefix."""
    data = json.dumps(payload).encode(ENCODING)
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)


def recv_message(sock: socket.socket) -> dict:
    """
    Receive a length-prefixed JSON message from *sock*.
    Raises ConnectionError if the socket closes unexpectedly.
    """
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        raise ConnectionError("Socket closed while reading message length.")
    (length,) = struct.unpack(">I", raw_len)
    raw_data = _recv_exact(sock, length)
    if not raw_data:
        raise ConnectionError("Socket closed while reading message body.")
    return json.loads(raw_data.decode(ENCODING))


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes from *sock*."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""
        buf += chunk
    return buf


# ------------------------------------------------------------------ #
#  Raw binary framing (for chunk data)                                 #
# ------------------------------------------------------------------ #

def send_bytes(sock: socket.socket, data: bytes) -> None:
    """Send raw bytes with a 4-byte length prefix."""
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)


def recv_bytes(sock: socket.socket) -> bytes:
    """Receive raw bytes that were sent with send_bytes()."""
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        raise ConnectionError("Socket closed while reading byte length.")
    (length,) = struct.unpack(">I", raw_len)
    return _recv_exact(sock, length)


# ------------------------------------------------------------------ #
#  Misc                                                                #
# ------------------------------------------------------------------ #

def node_address(node_id: int, base_port: int = 9100) -> tuple[str, int]:
    """Return (host, port) for a node given its 1-based *node_id*."""
    return ("127.0.0.1", base_port + node_id - 1)


def timestamp() -> str:
    """Return current UTC time as ISO-8601 string."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Return the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path: str | Path) -> Any:
    """Load and return JSON from *path*; return {} if file missing."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p) as fh:
        return json.load(fh)


def save_json(path: str | Path, data: Any) -> None:
    """Atomically write *data* as JSON to *path*."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(p)
