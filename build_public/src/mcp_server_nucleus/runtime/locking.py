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
import fcntl
import time
import os
import contextlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class BrainLock(abc.ABC):
    """
    Abstract Base Class for Nucleus Locking.
    Enforces the 'LockProvider' interface for Cloud/Local agnosticism.
    """
    
    @abc.abstractmethod
    def acquire(self, timeout: float = 5.0) -> bool:
        """Attempt to acquire the lock. Returns True if successful."""
        pass

    @abc.abstractmethod
    def release(self) -> None:
        """Release the lock."""
        pass

    def check_stale_locks(self, max_age_seconds: float = 3600):
        """Optional: Check for and cleanup stale locks."""
        pass


    @contextlib.contextmanager
    def section(self, timeout: float = 5.0):
        """Context manager for critical sections."""
        acquired = self.acquire(timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock on {self} after {timeout}s")
        try:
            yield
        finally:
            self.release()

class FileBrainLock(BrainLock):
    """
    Local Implementation using UNIX `fcntl`.
    Used for the 'Local First' Sovereign OS.
    """
    
    def __init__(self, lock_path: str):
        self.lock_path = Path(lock_path)
        self.lock_file = None
        # Ensure directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

    def acquire(self, timeout: float = 5.0) -> bool:
        start_time = time.time()
        
        # Open the file if not already open
        if self.lock_file is None:
            self.lock_file = open(self.lock_path, 'w+')

        while True:
            try:
                # specific locking operation: LOCK_EX (Exclusive) | LOCK_NB (Non-Blocking)
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Write PID for debugging (knowing who holds the lock)
                self.lock_file.seek(0)
                self.lock_file.truncate()
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
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
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except ValueError:
                # File might be closed already
                pass
            finally:
                self.lock_file = None

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
