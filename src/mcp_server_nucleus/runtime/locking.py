"""
BrainLock: The Atomic Safety Layer for Nucleus.
This module defines the locking primitives used to ensure data integrity across
multiple Nucleus processes (Daemon, CLI, MCP Server).

Strategic Role:
- Ensures "Atomic State" (The Brain doesn't hallucinate due to race conditions).
- Implements "Leased Locks" (Prevents deadlocks if a process crashes).
- Future-Proofing: Abstract base class allows swapping 'fcntl' for 'Redis' later.
"""

import abc
try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None
import time
import os
import contextlib
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class BrainLock(abc.ABC):
    """
    Abstract Base Class for Nucleus Locking.
    Enforces the 'LockProvider' interface for Cloud/Local agnosticism.
    """
    
    @abc.abstractmethod
    def acquire(self, timeout: float = 5.0, metadata: Optional[Dict[str, str]] = None) -> bool:
        """Attempt to acquire the lock. Returns True if successful."""
        pass

    @abc.abstractmethod
    def release(self) -> None:
        """Release the lock."""
        pass

    @abc.abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Retrieve metadata associated with the lock."""
        pass

    def check_stale_locks(self, max_age_seconds: float = 3600):
        """Optional: Check for and cleanup stale locks."""
        pass


    @contextlib.contextmanager
    def section(self, timeout: float = 5.0, metadata: Optional[Dict[str, str]] = None):
        """Context manager for critical sections."""
        acquired = self.acquire(timeout, metadata=metadata)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock on {self} after {timeout}s")
        try:
            yield
        finally:
            self.release()

class FileBrainLock(BrainLock):
    """
    Local Implementation using UNIX `fcntl` + `xattr` for metadata.
    Used for the 'Local First' Sovereign OS.
    """
    
    def __init__(self, lock_path: str):
        self.lock_path = Path(lock_path)
        self.lock_file = None
        # Ensure directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.xattr_available = shutil.which("xattr") is not None

    def _set_xattr(self, key: str, value: str):
        """Writes extended attribute if xattr is available."""
        if not self.xattr_available:
            return
        
        try:
            subprocess.run(
                ["xattr", "-w", key, str(value), str(self.lock_path)],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to set xattr {key}: {e}")

    def _get_xattr(self, key: str) -> Optional[str]:
        """Reads extended attribute if xattr is available."""
        if not self.xattr_available:
            return None
            
        try:
            result = subprocess.run(
                ["xattr", "-p", key, str(self.lock_path)],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _list_xattrs(self) -> List[str]:
        """Lists all xattrs on the file."""
        if not self.xattr_available:
            return []
            
        try:
            result = subprocess.run(
                ["xattr", str(self.lock_path)],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip().split("\n")
        except subprocess.CalledProcessError:
            return []

    def acquire(self, timeout: float = 5.0, metadata: Optional[Dict[str, str]] = None) -> bool:
        start_time = time.time()
        
        # Open the file if not already open
        if self.lock_file is None:
            self.lock_file = open(self.lock_path, 'w+')

        while True:
            try:
                # specific locking operation: LOCK_EX (Exclusive) | LOCK_NB (Non-Blocking)
                if fcntl:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif msvcrt:
                    self.lock_file.seek(0)
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                
                # Write PID for debugging (knowing who holds the lock)
                self.lock_file.seek(0)
                self.lock_file.truncate()
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
                
                # --- METADATA INJECTION (Phase 28) ---
                if metadata:
                    # Always include timestamp if not present
                    if "timestamp" not in metadata:
                        metadata["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                        
                    for k, v in metadata.items():
                        # Namespace keys with 'nucleus.lock.' if not already
                        key = k if k.startswith("nucleus.lock.") else f"nucleus.lock.{k}"
                        self._set_xattr(key, v)
                
                return True
            except (IOError, OSError):
                # Lock is held by another process
                if time.time() - start_time > timeout:
                    logger.warning(f"Timeout waiting for lock: {self.lock_path}")
                    return False
                time.sleep(0.1)

    def release(self) -> None:
        if self.lock_file:
            try:
                # Unlock
                if fcntl:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                elif msvcrt:
                    self.lock_file.seek(0)
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                self.lock_file.close()
            except ValueError:
                # File might be closed already
                pass
            finally:
                self.lock_file = None

    def get_metadata(self) -> Dict[str, Any]:
        """Retrieves all nucleus.lock.* metadata from the lock file."""
        if not self.lock_path.exists():
            return {}
            
        data = {}
        # Get PID from file content
        try:
            with open(self.lock_path, 'r') as f:
                data["pid"] = f.read().strip()
        except:
            data["pid"] = "unknown"

        # Get xattrs
        if self.xattr_available:
            attrs = self._list_xattrs()
            for attr in attrs:
                if attr.startswith("nucleus.lock."):
                    clean_key = attr.replace("nucleus.lock.", "")
                    data[clean_key] = self._get_xattr(attr)
        
        return data

    def check_stale_locks(self, max_age_seconds: float = 86400):
        """
        Check for stale lock files.
        Note: fcntl locks are released by OS on process death.
        This simply cleans up old files to keep directory tidy.
        """
        try:
            if self.lock_path.exists():
                stat = self.lock_path.stat()
                age = time.time() - stat.st_mtime
                if age > max_age_seconds:
                    # We could try to flock(LOCK_EX | LOCK_NB) to see if anyone holds it
                    # If we can lock it, it was truly stale (or just unused), so we can theoretically delete it.
                    # But dealing with race on deletion is tricky. 
                    # For V1, we simply Log it.
                    logger.info(f"Old lock file detected: {self.lock_path} (Age: {age}s)")
        except Exception:
            pass


    def __repr__(self):
        return f"<FileBrainLock: {self.lock_path}>"

# Factory Function for easy usage
def get_lock(resource_name: str, base_dir: Optional[Path] = None) -> BrainLock:
    """
    Factory to get the appropriate lock for a resource.
    Currently defaults to FileBrainLock.
    """
    if base_dir is None:
        # Default to a .locks directory in the user's home or project root
        # For now, let's use the .brain/.locks directory if possible, or /tmp/nucleus
        base_dir = Path(os.environ.get("NUCLEUS_LOCK_DIR", "/tmp/nucleus_locks"))
    
    lock_path = base_dir / f"{resource_name}.lock"
    return FileBrainLock(str(lock_path))
