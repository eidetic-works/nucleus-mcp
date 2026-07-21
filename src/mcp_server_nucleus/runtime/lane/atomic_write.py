"""Atomic file write utilities.

Provides atomic_write() which writes to a temp file then renames it,
preventing corruption if the process crashes mid-write.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Union


def atomic_write(path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically.

    Writes to a temp file in the same directory, then renames it to the
    target path. This prevents corruption if the process crashes mid-write
    (the temp file is left behind but the target file is either the old
    content or the new content, never a partial write).

    Args:
        path: Target file path.
        content: Content to write.
        encoding: Text encoding (default: utf-8).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in the same directory (so rename is atomic on same filesystem)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, path)
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: Union[str, Path], content: bytes) -> None:
    """Write bytes to a file atomically (same as atomic_write but for bytes)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
