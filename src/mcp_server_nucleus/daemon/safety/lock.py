try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None
import os
import time
import errno
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class BrainLock:
    """
    The Atomic Guard for the Sovereign Brain.
    
    Implements cross-process file locking using fcntl.
    Prevents race conditions between the MCP Server (User Interface)
    and the Daemon (Background Worker).
    
    Principles:
    1. Safety: Never corrupt the Graph.
    2. Liveness: Auto-break stale locks (App crashes).
    3. Atomicity: All or nothing.
    """
    
    def __init__(self, lock_file: str, timeout: int = 5):
        """
        Initialize the BrainLock.
        
        Args:
            lock_file: Path to the lock file (e.g., .brain/lock/state.lock)
            timeout: Seconds to wait for lock acquisition before giving up.
        """
        self.lock_file = lock_file
        self.timeout = timeout
        self.fd = None
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)

    def acquire(self) -> bool:
        """
        Acquire egg-lock. Blocking with timeout.
        """
        start_time = time.time()
        while True:
            try:
                self.fd = open(self.lock_file, 'w')
                # LOCK_EX: Exclusive Lock
                # LOCK_NB: Non-blocking (fail immediately if locked)
                if fcntl:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif msvcrt:
                    self.fd.seek(0)
                    msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
                
                # Write PID for debugging / stale detection
                self.fd.write(str(os.getpid()))
                self.fd.flush()
                return True
                
            except IOError as e:
                if self.fd:
                    self.fd.close()
                    self.fd = None
                    
                if e.errno != errno.EAGAIN:
                    # Unexpected error
                    logger.error(f"BrainLock Error: {e}")
                    raise
                    
                # Locked by another process
                if time.time() - start_time >= self.timeout:
                    # Timeout reached
                    logger.warning(f"BrainLock Acquisition Timeout: {self.lock_file}")
                    return False
                
                # Wait and retry
                time.sleep(0.1)

    def release(self):
        """
        Release the lock.
        """
        if self.fd:
            try:
                # Remove the lock file content (optional, but clean)
                self.fd.truncate(0)
                if fcntl:
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                elif msvcrt:
                    self.fd.seek(0)
                    msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception as e:
                logger.error(f"BrainLock Release Error: {e}")
            finally:
                self.fd.close()
                self.fd = None

    @contextmanager
    def guard(self):
        """
        Context Manager for 'with BrainLock(...):' syntax.
        """
        if not self.acquire():
            raise TimeoutError(f"Could not acquire BrainLock on {self.lock_file}")
        try:
            yield
        finally:
            self.release()

    @staticmethod
    def is_locked(lock_file: str) -> bool:
        """
        Check if a file is currently locked without waiting.
        """
        if not os.path.exists(lock_file):
            return False
            
        try:
            fd = open(lock_file, 'r')
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # If we got here, it wasn't locked. Unlock and close.
                fcntl.flock(fd, fcntl.LOCK_UN)
            elif msvcrt:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
            fd.close()
            return False
        except IOError as e:
            if getattr(e, 'errno', None) in (errno.EAGAIN, errno.EACCES, 13, 33):
                return True
            raise
