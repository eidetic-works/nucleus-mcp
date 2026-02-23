import logging
import time
import os
from collections import deque
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .locker import Locker

logger = logging.getLogger(__name__)

class SecurityEventHandler(FileSystemEventHandler):
    """
    Handles file events for the Hypervisor Watchdog.
    Detects attempts to modify locked files.
    """
    def __init__(self, watchdog_instance, locker: Locker):
        self.watchdog = watchdog_instance
        self.locker = locker
        self.revert_timestamps = deque(maxlen=10)

    def on_modified(self, event):
        if event.is_directory:
            return
        
        path = str(Path(event.src_path).resolve())
        is_protected = False
        
        # Access live list from watchdog instance
        for p_path in self.watchdog.protected_paths:
            if path == p_path or path.startswith(p_path + "/"):
                is_protected = True
                break
        
        if is_protected:
            # Breach Detected!
            logger.warning(f"🚨 SECURITY BREACH: Locked file modified: {path}")
            
            # Revert from Shadow Copy (which also re-locks)
            self.revert(path)

    def revert(self, path: str):
        current_time = time.time()
        self.revert_timestamps.append(current_time)
        
        # DDoS Circuit Breaker: 10 edits inside 1 second
        if len(self.revert_timestamps) == self.revert_timestamps.maxlen:
            time_delta = self.revert_timestamps[-1] - self.revert_timestamps[0]
            if time_delta < 1.0:
                logger.error(f"🚨 DDoS CIRCUIT BREAKER TRIPPED! Too many reverts in {time_delta:.2f}s. Dropping connection.")
                os._exit(1)
                
        if path in self.watchdog.shadow_cache:
            try:
                # 1. Unlock to allow writing
                self.locker.unlock(path)
                
                # 2. Write with POSIX flock
                data = self.watchdog.shadow_cache[path]
                with open(path, 'wb') as f:
                    try:
                        import fcntl
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        f.write(data)
                        f.flush()
                        os.fsync(f.fileno())
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except ImportError:
                        f.write(data)
                logger.info(f"✅ Reverted {path} from RAM Shadow Cache.")
            except Exception as e:
                logger.error(f"Failed to revert {path}: {e}")
            finally:
                # 3. Immediately re-lock
                self.locker.lock(path)

class Watchdog:
    """
    The Nucleus Hypervisor Sentinel (Layer 1).
    Monitors critical files and reinforces locks.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.locker = Locker()
        self.observer = Observer()
        self.protected_paths = []
        self.shadow_cache = {}

    def protect(self, path: str):
        """Adds a path to the protected list and starts watching it."""
        abs_path = str((self.workspace_root / path).resolve())
        if abs_path not in self.protected_paths:
            self.protected_paths.append(abs_path)
            
            # Load into RAM Shadow Cache
            try:
                if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                    with open(abs_path, 'rb') as f:
                        self.shadow_cache[abs_path] = f.read()
            except Exception as e:
                logger.warning(f"Watchdog: Could not cache {abs_path}: {e}")
                
            # Ensure it is physically locked
            self.locker.lock(abs_path)
    
    def start(self):
        """Starts the background monitoring thread."""
        if self.observer.is_alive():
            return
            
        try:
            handler = SecurityEventHandler(self, self.locker)
            self.observer.schedule(handler, str(self.workspace_root), recursive=True)
            self.observer.start()
            import sys
            sys.stderr.write(f"[Nucleus] 👁️  Watchdog active: {self.workspace_root}\n"); sys.stderr.flush()
        except (RuntimeError, Exception) as e:
            import sys
            # Only log to stderr, never stdout
            sys.stderr.write(f"[Nucleus] ⚠️  Watchdog Quiet: {e}\n"); sys.stderr.flush()

    def stop(self):
        self.observer.stop()
        self.observer.join()
