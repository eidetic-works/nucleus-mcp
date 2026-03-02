"""
File System Resilience Layer
===============================
Phase 73.3: Production-Grade File Operations

Provides:
1. Atomic writes (write to temp, then rename)
2. File locking (fcntl on Unix, msvcrt on Windows)
3. Disk space checks before writes
4. Permission validation
5. Corrupted JSON recovery
6. Cross-platform path handling
7. Concurrent access safety

Target: 99.9% reliability for all file operations.
"""

import json
import logging
import os
import platform
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

logger = logging.getLogger("nucleus.file_resilience")


# ============================================================
# FILE LOCKING (Cross-Platform)
# ============================================================

class FileLock:
    """
    Cross-platform file locking.
    Uses fcntl on Unix, msvcrt on Windows.
    Falls back to .lock file if neither available.
    """

    def __init__(self, path: Union[str, Path], timeout: float = 10.0):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.timeout = timeout
        self._fd = None
        self._acquired = False

    def acquire(self) -> bool:
        """Acquire file lock. Returns True if successful."""
        start = time.monotonic()

        while True:
            try:
                if platform.system() != "Windows":
                    return self._acquire_unix()
                else:
                    return self._acquire_windows()
            except (IOError, OSError):
                if time.monotonic() - start > self.timeout:
                    logger.warning(f"Lock timeout after {self.timeout}s: {self.path}")
                    return False
                time.sleep(0.1)

    def release(self):
        """Release file lock."""
        try:
            if platform.system() != "Windows":
                self._release_unix()
            else:
                self._release_windows()
        except Exception as e:
            logger.warning(f"Lock release error: {e}")

    def _acquire_unix(self) -> bool:
        try:
            import fcntl
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fd = open(self.lock_path, "w")
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._acquired = True
            return True
        except ImportError:
            return self._acquire_fallback()

    def _release_unix(self):
        if self._fd:
            try:
                import fcntl
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass
            finally:
                self._fd.close()
                self._fd = None
                self._cleanup_lock_file()

    def _acquire_windows(self) -> bool:
        try:
            import msvcrt
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fd = open(self.lock_path, "w")
            msvcrt.locking(self._fd.fileno(), msvcrt.LK_NBLCK, 1)
            self._acquired = True
            return True
        except ImportError:
            return self._acquire_fallback()

    def _release_windows(self):
        if self._fd:
            try:
                import msvcrt
                msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
            except ImportError:
                pass
            finally:
                self._fd.close()
                self._fd = None
                self._cleanup_lock_file()

    def _acquire_fallback(self) -> bool:
        """Fallback: use .lock file existence as lock indicator."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        while self.lock_path.exists():
            # Check for stale locks (older than 60s)
            try:
                age = time.time() - self.lock_path.stat().st_mtime
                if age > 60:
                    self.lock_path.unlink(missing_ok=True)
                    break
            except Exception:
                break
            if time.monotonic() - start > self.timeout:
                return False
            time.sleep(0.1)

        try:
            self.lock_path.write_text(str(os.getpid()))
            self._acquired = True
            return True
        except Exception:
            return False

    def _cleanup_lock_file(self):
        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


# ============================================================
# ATOMIC FILE WRITER
# ============================================================

class AtomicWriter:
    """
    Atomic file writes: write to temp file, then rename.
    Prevents corrupted files from partial writes.
    """

    @staticmethod
    def write_text(path: Union[str, Path], content: str, encoding: str = "utf-8") -> bool:
        """Atomically write text content to file."""
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file in same directory (for same-filesystem rename)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent),
                prefix=f".{path.stem}_",
                suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding=encoding) as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic rename (on same filesystem)
                if platform.system() == "Windows":
                    # Windows doesn't support atomic rename over existing file
                    if path.exists():
                        backup = path.with_suffix(path.suffix + ".bak")
                        try:
                            if backup.exists():
                                backup.unlink()
                            path.rename(backup)
                        except Exception:
                            pass
                    os.rename(tmp_path, str(path))
                    # Clean up backup
                    backup = path.with_suffix(path.suffix + ".bak")
                    if backup.exists():
                        try:
                            backup.unlink()
                        except Exception:
                            pass
                else:
                    os.rename(tmp_path, str(path))

                return True
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

        except Exception as e:
            logger.error(f"Atomic write failed for {path}: {e}")
            return False

    @staticmethod
    def write_json(path: Union[str, Path], data: Any, indent: int = 2) -> bool:
        """Atomically write JSON data to file."""
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            return AtomicWriter.write_text(path, content)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed: {e}")
            return False

    @staticmethod
    def append_line(path: Union[str, Path], line: str, encoding: str = "utf-8") -> bool:
        """Thread-safe line append (for JSONL files)."""
        path = Path(path)
        lock = FileLock(path, timeout=5.0)

        try:
            if not lock.acquire():
                logger.warning(f"Could not acquire lock for append: {path}")
                # Fallback: try without lock
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "a", encoding=encoding) as f:
                    f.write(line if line.endswith("\n") else line + "\n")
                return True

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "a", encoding=encoding) as f:
                    f.write(line if line.endswith("\n") else line + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                return True
            finally:
                lock.release()

        except Exception as e:
            logger.error(f"Append failed for {path}: {e}")
            return False


# ============================================================
# RESILIENT JSON READER
# ============================================================

class ResilientJSONReader:
    """
    Reads JSON files with corruption recovery.
    Handles: truncated files, encoding errors, BOM markers.
    """

    @staticmethod
    def read_json(path: Union[str, Path], default: Any = None) -> Any:
        """Read JSON file with fallback to default."""
        path = Path(path)

        if not path.exists():
            return default

        try:
            content = path.read_text(encoding="utf-8-sig")  # Handle BOM
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted JSON in {path}: {e}")
            return ResilientJSONReader._try_recover_json(path, default)
        except UnicodeDecodeError:
            # Try latin-1 as fallback
            try:
                content = path.read_text(encoding="latin-1")
                return json.loads(content)
            except Exception:
                return default
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            return default

    @staticmethod
    def _try_recover_json(path: Path, default: Any) -> Any:
        """Try to recover corrupted JSON file."""
        try:
            content = path.read_text(encoding="utf-8-sig")

            # Try stripping trailing garbage
            for i in range(len(content) - 1, -1, -1):
                if content[i] in ('}', ']'):
                    try:
                        return json.loads(content[:i + 1])
                    except json.JSONDecodeError:
                        continue

            # Try backup file
            backup = path.with_suffix(path.suffix + ".bak")
            if backup.exists():
                try:
                    return json.loads(backup.read_text(encoding="utf-8-sig"))
                except Exception:
                    pass

        except Exception:
            pass

        return default

    @staticmethod
    def read_jsonl(path: Union[str, Path], max_lines: int = 10000) -> list:
        """Read JSONL file, skipping corrupted lines."""
        path = Path(path)
        results = []

        if not path.exists():
            return results

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.debug(f"Skipping corrupted JSONL line {i} in {path}")
                        continue
        except Exception as e:
            logger.error(f"Failed to read JSONL {path}: {e}")

        return results


# ============================================================
# DISK SPACE CHECKER
# ============================================================

class DiskSpaceChecker:
    """Check disk space before writes."""

    MIN_SPACE_MB = 50  # Minimum 50MB free

    @staticmethod
    def has_space(path: Union[str, Path], required_mb: float = 0) -> bool:
        """Check if there's enough disk space."""
        min_required = max(DiskSpaceChecker.MIN_SPACE_MB, required_mb)
        try:
            p = Path(path)
            check = p if p.exists() else p.parent
            while not check.exists() and check != check.parent:
                check = check.parent
            usage = shutil.disk_usage(str(check))
            free_mb = usage.free / (1024 * 1024)
            return free_mb >= min_required
        except Exception:
            return True  # Assume OK if check fails

    @staticmethod
    def get_free_space_mb(path: Union[str, Path]) -> float:
        """Get free space in MB."""
        try:
            p = Path(path)
            check = p if p.exists() else p.parent
            while not check.exists() and check != check.parent:
                check = check.parent
            usage = shutil.disk_usage(str(check))
            return usage.free / (1024 * 1024)
        except Exception:
            return float('inf')


# ============================================================
# PERMISSION CHECKER
# ============================================================

class PermissionChecker:
    """Cross-platform permission checking."""

    @staticmethod
    def can_read(path: Union[str, Path]) -> bool:
        path = Path(path)
        if not path.exists():
            return False
        return os.access(str(path), os.R_OK)

    @staticmethod
    def can_write(path: Union[str, Path]) -> bool:
        path = Path(path)
        if path.exists():
            return os.access(str(path), os.W_OK)
        # Check parent
        parent = path.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        return os.access(str(parent), os.W_OK)

    @staticmethod
    def ensure_writable(path: Union[str, Path]) -> bool:
        """Ensure path is writable, creating directories if needed."""
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            return PermissionChecker.can_write(path)
        except PermissionError:
            return False
        except Exception:
            return False


# ============================================================
# RESILIENT FILE OPS (Unified Interface)
# ============================================================

class ResilientFileOps:
    """
    Unified interface for resilient file operations.
    Combines: atomic writes, locking, disk checks, permission checks.
    """

    def __init__(self):
        self._write_count = 0
        self._read_count = 0
        self._error_count = 0

    def write_json(self, path: Union[str, Path], data: Any, indent: int = 2) -> bool:
        """Write JSON with full resilience stack."""
        path = Path(path)
        self._write_count += 1

        # Pre-flight checks
        if not DiskSpaceChecker.has_space(path):
            logger.error(f"Insufficient disk space for write: {path}")
            self._error_count += 1
            return False

        if path.exists() and not PermissionChecker.can_write(path):
            logger.error(f"No write permission: {path}")
            self._error_count += 1
            return False

        if not PermissionChecker.ensure_writable(path):
            logger.error(f"Cannot create parent dirs: {path}")
            self._error_count += 1
            return False

        return AtomicWriter.write_json(path, data, indent)

    def write_text(self, path: Union[str, Path], content: str) -> bool:
        """Write text with full resilience stack."""
        path = Path(path)
        self._write_count += 1

        if not DiskSpaceChecker.has_space(path):
            self._error_count += 1
            return False
        if not PermissionChecker.ensure_writable(path):
            self._error_count += 1
            return False

        return AtomicWriter.write_text(path, content)

    def append_jsonl(self, path: Union[str, Path], record: Dict[str, Any]) -> bool:
        """Append a JSON record to a JSONL file with locking."""
        try:
            line = json.dumps(record, ensure_ascii=False)
            return AtomicWriter.append_line(path, line)
        except Exception as e:
            logger.error(f"JSONL append failed: {e}")
            self._error_count += 1
            return False

    def read_json(self, path: Union[str, Path], default: Any = None) -> Any:
        """Read JSON with corruption recovery."""
        self._read_count += 1
        return ResilientJSONReader.read_json(path, default)

    def read_jsonl(self, path: Union[str, Path], max_lines: int = 10000) -> list:
        """Read JSONL with line-level error recovery."""
        self._read_count += 1
        return ResilientJSONReader.read_jsonl(path, max_lines)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "write_count": self._write_count,
            "read_count": self._read_count,
            "error_count": self._error_count,
        }


# ============================================================
# SINGLETON
# ============================================================

_file_ops_instance: Optional[ResilientFileOps] = None

def get_resilient_file_ops() -> ResilientFileOps:
    """Get singleton resilient file ops instance."""
    global _file_ops_instance
    if _file_ops_instance is None:
        _file_ops_instance = ResilientFileOps()
    return _file_ops_instance
