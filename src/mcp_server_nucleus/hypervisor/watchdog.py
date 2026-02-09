
import logging
import time
import shutil
from pathlib import Path
from typing import List, Optional
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    # Handle environment where watchdog is not installed
    Observer = None
    FileSystemEventHandler = object

from .locker import Locker

logger = logging.getLogger(__name__)

class SecurityEventHandler(FileSystemEventHandler):
    def __init__(self, watchdog_instance, locker: Locker):
        self.watchdog = watchdog_instance
        self.locker = locker

    def on_modified(self, event):
        if not FileSystemEventHandler or event.is_directory:
            return
        
        path = str(Path(event.src_path).resolve())
        is_protected = False
        
        for p_path in self.watchdog.protected_paths:
            if path == p_path or path.startswith(p_path + "/"):
                is_protected = True
                break
        
        if is_protected:
            logger.warning(f"🚨 SECURITY BREACH: Locked file modified: {path}")
            self.locker.lock(path)

class Watchdog:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.locker = Locker()
        self.protected_paths = []
        if Observer:
            self.observer = Observer()
        else:
            self.observer = None

    def protect(self, path: str):
        abs_path = str((self.workspace_root / path).resolve())
        if abs_path not in self.protected_paths:
            self.protected_paths.append(abs_path)
            self.locker.lock(abs_path)
    
    def start(self):
        if not self.observer:
            logger.warning("Watchdog dependency not installed. Monitoring disabled.")
            return
        handler = SecurityEventHandler(self, self.locker)
        self.observer.schedule(handler, str(self.workspace_root), recursive=True)
        self.observer.start()
        logger.info(f"👁️ Hypervisor Watchdog started on {self.workspace_root}")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
