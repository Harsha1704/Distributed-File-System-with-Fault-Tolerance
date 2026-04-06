"""
hashing.py — SHA-256 integrity helpers for DFS chunks.
"""

import hashlib
from pathlib import Path


def hash_bytes(data: bytes) -> str:
    """Return hex-encoded SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str | Path) -> str:
    """
    Return hex-encoded SHA-256 digest of the file at *path*.
    Reads in 64 KB blocks to stay memory-efficient for large files.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def verify_chunk(data: bytes, expected_hash: str) -> bool:
    """
    Return True if SHA-256(data) matches *expected_hash*.
    Raises ValueError with detail if they differ.
    """
    actual = hash_bytes(data)
    if actual != expected_hash:
        raise ValueError(
            f"Integrity check FAILED.\n"
            f"  expected : {expected_hash}\n"
            f"  actual   : {actual}"
        )
    return True


def verify_file(path: str | Path, expected_hash: str) -> bool:
    """
    Return True if SHA-256 of file at *path* matches *expected_hash*.
    Raises ValueError on mismatch.
    """
    actual = hash_file(path)
    if actual != expected_hash:
        raise ValueError(
            f"File integrity check FAILED for '{path}'.\n"
            f"  expected : {expected_hash}\n"
            f"  actual   : {actual}"
        )
    return True
