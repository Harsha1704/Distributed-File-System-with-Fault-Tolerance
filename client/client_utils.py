"""
client_utils.py — Higher-level helpers used by the CLI client.

Wraps common.chunking / hashing so client.py stays clean.
"""

from __future__ import annotations

import os
from pathlib import Path

from common.chunking import split_file, merge_chunks
from common.hashing import hash_file, verify_chunk
from common.utils import get_logger

logger = get_logger("client_utils")


def prepare_upload(file_path: str | Path) -> tuple[list[dict], str]:
    """
    Split *file_path* into chunks and compute the whole-file SHA-256.

    Returns:
        (chunks, file_hash)
        chunks  — list of chunk descriptors from split_file()
        file_hash — SHA-256 hex of the original file
    """
    file_path = Path(file_path)
    logger.info(f"Splitting '{file_path.name}' …")
    chunks = split_file(file_path)
    file_hash = hash_file(file_path)
    logger.info(f"  {len(chunks)} chunk(s), file hash = {file_hash[:12]}…")
    return chunks, file_hash


def assemble_download(
    chunk_descriptors: list[dict],   # [{"index": int, "data": bytes, "hash": str}, ...]
    output_path: str | Path,
    expected_file_hash: str | None = None,
) -> Path:
    """
    Verify each chunk's integrity then merge into *output_path*.

    *chunk_descriptors* must contain keys: index, data, hash.
    If *expected_file_hash* is given the reassembled file is also verified.

    Returns the resolved output Path.
    """
    output_path = Path(output_path)

    for cd in chunk_descriptors:
        try:
            verify_chunk(cd["data"], cd["hash"])
        except ValueError as exc:
            raise ValueError(f"Chunk {cd['index']} failed integrity check: {exc}") from exc

    result = merge_chunks(chunk_descriptors, output_path)
    logger.info(f"Assembled {len(chunk_descriptors)} chunk(s) → '{result}'")

    if expected_file_hash:
        from common.hashing import verify_file
        verify_file(result, expected_file_hash)
        logger.info("  Whole-file integrity: ✓")

    return result
