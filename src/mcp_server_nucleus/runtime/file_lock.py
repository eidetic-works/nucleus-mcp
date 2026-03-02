"""
Nucleus Runtime - File Locking (Concurrency Hardening)
=======================================================
Cross-platform file locking for concurrent access safety.

CRITICAL DATA: This module addresses vulnerability C25 identified in
the exhaustive design thinking analysis (Feb 24, 2026).

Attack vector: Multiple MCP clients writing to JSONL simultaneously
Defense: Exclusive file locks on all write operations

References:
- Evidence: E038, E039, E041
- Uses filelock library for cross-platform support
"""

import os
import json
import time
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
from contextlib import contextmanager

logger = logging.getLogger("nucleus.file_lock")

# Try to import filelock, fall back to basic locking
try:
    from filelock import FileLock, Timeout
    FILELOCK_AVAILABLE = True
except ImportError:
    FILELOCK_AVAILABLE = False
    logger.warning("filelock not installed - using basic locking (less robust)")


class LockError(Exception):
    """Raised when file lock cannot be acquired."""
    pass


class AtomicWriteError(Exception):
    """Raised when atomic write fails."""
    pass


@contextmanager
def file_lock(path: Union[str, Path], timeout: float = 10.0):
    """
    Context manager for exclusive file locking.
    
    Args:
        path: Path to the file to lock
        timeout: Maximum seconds to wait for lock (default 10)
        
    Yields:
        The path, with lock held
        
    Raises:
        LockError: If lock cannot be acquired within timeout
        
    Example:
        with file_lock("/path/to/file.jsonl"):
            # Safe to read/write file here
            pass
    """
    lock_path = Path(path).with_suffix(Path(path).suffix + ".lock")
    
    if FILELOCK_AVAILABLE:
        lock = FileLock(str(lock_path), timeout=timeout)
        try:
            with lock:
                yield path
        except Timeout:
            raise LockError(f"Could not acquire lock on {path} within {timeout}s")
    else:
        # Fallback: basic lock file (less robust but works)
        acquired = False
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                # Try to create lock file exclusively
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                acquired = True
                break
            except FileExistsError:
                time.sleep(0.1)
        
        if not acquired:
            raise LockError(f"Could not acquire lock on {path} within {timeout}s")
        
        try:
            yield path
        finally:
            try:
                lock_path.unlink()
            except OSError:
                pass


def atomic_write_json(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Atomically write JSON data to a file.
    
    Uses write-to-temp-then-rename pattern for atomicity.
    Includes fsync for durability.
    
    Args:
        path: Destination file path
        data: Data to serialize as JSON
        indent: JSON indentation (default 2)
        
    Raises:
        AtomicWriteError: If write fails
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file in same directory (for atomic rename)
    temp_fd = None
    temp_path = None
    
    try:
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp"
        )
        
        # Write data with explicit encoding
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is on disk
        
        temp_fd = None  # fdopen closed it
        
        # Atomic rename
        os.replace(temp_path, path)
        
        # Sync directory for durability on some filesystems
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(dir_fd)
            os.close(dir_fd)
        except (OSError, AttributeError):
            pass  # O_DIRECTORY not available on all platforms
            
    except Exception as e:
        # Clean up temp file on failure
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise AtomicWriteError(f"Failed to write {path}: {e}") from e


def atomic_append_jsonl(
    path: Union[str, Path],
    record: Dict[str, Any],
    timeout: float = 10.0
) -> None:
    """
    Atomically append a record to a JSONL file with locking.
    
    This is the safe way to append to JSONL files in concurrent environments.
    
    Args:
        path: Path to JSONL file
        record: Dictionary to append as JSON line
        timeout: Lock timeout in seconds
        
    Raises:
        LockError: If lock cannot be acquired
        AtomicWriteError: If write fails
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with file_lock(path, timeout=timeout):
        try:
            with open(path, 'a', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            raise AtomicWriteError(f"Failed to append to {path}: {e}") from e


def safe_read_jsonl(path: Union[str, Path], timeout: float = 10.0) -> List[Dict[str, Any]]:
    """
    Safely read a JSONL file with locking.
    
    Handles:
    - File not existing (returns empty list)
    - Corrupted last line (skips it)
    - Encoding issues (uses UTF-8)
    
    Args:
        path: Path to JSONL file
        timeout: Lock timeout in seconds
        
    Returns:
        List of parsed records
    """
    path = Path(path)
    
    if not path.exists():
        return []
    
    records = []
    
    with file_lock(path, timeout=timeout):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping corrupted line {line_num} in {path}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            raise
    
    return records


def safe_read_json(path: Union[str, Path], default: Any = None) -> Any:
    """
    Safely read a JSON file.
    
    Args:
        path: Path to JSON file
        default: Value to return if file doesn't exist or is invalid
        
    Returns:
        Parsed JSON data or default
    """
    path = Path(path)
    
    if not path.exists():
        return default
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Handle BOM if present
            if content.startswith('\ufeff'):
                content = content[1:]
            return json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Error reading {path}: {e}")
        return default


def repair_jsonl(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Attempt to repair a corrupted JSONL file.
    
    Reads all valid lines and rewrites the file.
    
    Args:
        path: Path to JSONL file
        
    Returns:
        Dict with repair statistics
    """
    path = Path(path)
    
    if not path.exists():
        return {"status": "file_not_found", "repaired": False}
    
    valid_records = []
    corrupted_lines = []
    
    with file_lock(path, timeout=30.0):
        # Read and validate all lines
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    valid_records.append(record)
                except json.JSONDecodeError:
                    corrupted_lines.append(line_num)
        
        if corrupted_lines:
            # Backup original
            backup_path = path.with_suffix('.jsonl.backup')
            path.rename(backup_path)
            
            # Write repaired file
            with open(path, 'w', encoding='utf-8') as f:
                for record in valid_records:
                    json.dump(record, f, ensure_ascii=False)
                    f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            
            return {
                "status": "repaired",
                "repaired": True,
                "valid_records": len(valid_records),
                "corrupted_lines": corrupted_lines,
                "backup": str(backup_path)
            }
        else:
            return {
                "status": "no_corruption",
                "repaired": False,
                "record_count": len(valid_records)
            }
