
import logging
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
            
            # 1. Immediate Re-Lock (in case it was unlocked)
            self.locker.lock(path)
            
            # 2. (Future) Revert from Shadow Copy
            # self.revert(path)

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

    def protect(self, path: str):
        """Adds a path to the protected list and starts watching it."""
        abs_path = str((self.workspace_root / path).resolve())
        if abs_path not in self.protected_paths:
            self.protected_paths.append(abs_path)
            # Ensure it is physically locked
            self.locker.lock(abs_path)
    
    def start(self):
        """Starts the background monitoring thread."""
        handler = SecurityEventHandler(self, self.locker)
        self.observer.schedule(handler, str(self.workspace_root), recursive=True)
        self.observer.start()
        logger.info(f"👁️ Hypervisor Watchdog started on {self.workspace_root}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
