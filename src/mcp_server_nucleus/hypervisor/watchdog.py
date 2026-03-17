import logging
import time
import os
from collections import deque, OrderedDict
from pathlib import Path
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    HAS_WATCHDOG = False
try:
    from mcp_server_nucleus.runtime.common import assert_path_in_workspace
except ImportError:
    def assert_path_in_workspace(path: str, workspace_root=None):
        return Path(path).resolve()

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
            # Hash/Diff check to prevent false-positive trigger loops from IDE scanners
            try:
                with open(path, 'rb') as f:
                    current_content = f.read()
                if current_content == self.watchdog.shadow_cache.get(path):
                    # False positive IDE scan, content is identical
                    return
            except Exception:
                pass

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
                logger.error(f"🚨 DDoS CIRCUIT BREAKER TRIPPED! Too many reverts in {time_delta:.2f}s. Ignoring further reverts for 5s.")
                # We do not os._exit(1) anymore to prevent IDEs from violently killing the MCP server.
                # Just sleep briefly to break the infinite feedback loop.
                time.sleep(1)
                return
                
        if path in self.watchdog.shadow_cache:
            try:
                # 1. Unlock to allow writing (with authorization secret)
                self.locker.unlock(path, secret=self.locker._internal_secret)
                
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
    def __init__(self, workspace_root: str, max_cache_size: int = 500):
        if not HAS_WATCHDOG:
            logger.warning("watchdog package not installed — file monitoring disabled")
        self.workspace_root = Path(workspace_root)
        # Ensure workspace_root is safe (Phase 14)
        assert_path_in_workspace(str(self.workspace_root))

        self.locker = Locker()
        self.observer = Observer() if HAS_WATCHDOG else None
        self.protected_paths = []
        # OrderedDict for LRU eviction (Phase 14)
        self.shadow_cache = OrderedDict()
        self.max_cache_size = max_cache_size

    def _cache_file(self, path: str, data: bytes):
        """Add to shadow_cache with LRU eviction (Phase 14)."""
        if path in self.shadow_cache:
            self.shadow_cache.move_to_end(path)
        self.shadow_cache[path] = data
        
        if len(self.shadow_cache) > self.max_cache_size:
            # Evict oldest (at the beginning)
            evicted, _ = self.shadow_cache.popitem(last=False)
            logger.debug(f"Watchdog: Evicted {evicted} from shadow_cache (LRU)")

    def protect(self, path: str):
        """Adds a path to the protected list and starts watching it."""
        # Use common utility for path safety (Phase 14)
        abs_path = str(assert_path_in_workspace(path, workspace_root=str(self.workspace_root)))
        if abs_path not in self.protected_paths:
            self.protected_paths.append(abs_path)
            
            # Load into RAM Shadow Cache
            try:
                if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                    with open(abs_path, 'rb') as f:
                        self._cache_file(abs_path, f.read())
            except Exception as e:
                logger.warning(f"Watchdog: Could not cache {abs_path}: {e}")
                
            # Ensure it is physically locked
            self.locker.lock(abs_path)
    
    def start(self):
        """Starts the background monitoring thread."""
        if not HAS_WATCHDOG or self.observer is None:
            return
        if self.observer.is_alive():
            return

        try:
            handler = SecurityEventHandler(self, self.locker)
            self.observer.schedule(handler, str(self.workspace_root), recursive=True)
            self.observer.daemon = True  # Don't block process exit (fixes pytest hang)
            self.observer.start()
            import sys
            _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json', 'chat']) or any('--format' in arg for arg in sys.argv) or (len(sys.argv) == 1)
            if not _is_quiet:
                sys.stderr.write(f"[Nucleus] 👁️  Watchdog active: {self.workspace_root}\n")
                sys.stderr.flush()
        except (RuntimeError, Exception) as e:
            import sys
            # Only log to stderr, never stdout
            _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json', 'chat']) or any('--format' in arg for arg in sys.argv) or (len(sys.argv) == 1)
            if not _is_quiet:
                sys.stderr.write(f"[Nucleus] ⚠️  Watchdog Quiet: {e}\n")
                sys.stderr.flush()
    def stop(self):
        if self.observer is None:
            return
        self.observer.stop()
        self.observer.join()
