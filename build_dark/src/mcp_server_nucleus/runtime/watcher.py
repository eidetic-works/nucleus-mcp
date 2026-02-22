
"""
Async File Watcher for Nucleus.
Provides event-driven monitoring of Brain changes (directives, tasks).

Strategic Role:
- Moves Daemon from "Sleep Loop" to "Event Driven" (where possible).
- Monitors `directives.md` for policy updates.
- Monitors `task.md` for new commands.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, List, Dict

logger = logging.getLogger(__name__)

class AsyncFileWatcher:
    def __init__(self, watch_paths: List[Path], callback: Callable, polling_interval: float = 2.0):
        self.watch_paths = watch_paths
        self.callback = callback
        self.polling_interval = polling_interval
        self.running = False
        self._last_mtimes: Dict[Path, float] = {}
        
        # Try to import watchdog for native OS events, fallback to polling
        self.use_watchdog = False
        try:
            from watchdog.observers import Observer
            self.use_watchdog = True
            self.observer = Observer()
            self._handler = self._create_handler()
        except ImportError:
            logger.info("Watchdog not installed. Falling back to Polling.")

    def _create_handler(self):
        from watchdog.events import FileSystemEventHandler
        
        class Handler(FileSystemEventHandler):
            def __init__(self, callback):
                self.cb = callback
                
            def on_modified(self, event):
                if not event.is_directory:
                    # Debounce or just fire?
                    # For V1, just fire. simple.
                    asyncio.run_coroutine_threadsafe(self.cb(Path(event.src_path)), asyncio.get_running_loop())
                    
        return Handler(self.callback)

    async def start(self):
        """Start the watcher"""
        self.running = True
        
        if self.use_watchdog:
            logger.info("👀 Starting Native File Watcher (Watchdog)")
            # Re-import to be safe or use what we confirmed
            
            # Watch valid directories
            watched_dirs = set()
            for p in self.watch_paths:
                if p.exists():
                    p_dir = p if p.is_dir() else p.parent
                    if p_dir not in watched_dirs:
                        self.observer.schedule(self._handler, str(p_dir), recursive=False)
                        watched_dirs.add(p_dir)
            
            try:
                self.observer.start()
                # Watchdog runs in thread, we just await nothing or keep loop alive elsewhere
            except Exception as e:
                logger.error(f"Watchdog failed to start: {e}. Fallback to polling.")
                self.use_watchdog = False
                
        if not self.use_watchdog:
            logger.info(f"👀 Starting Polling Watcher ({self.polling_interval}s)")
            asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        """Robust polling loop"""
        # Init mtimes
        for p in self.watch_paths:
            if p.exists():
                self._last_mtimes[p] = p.stat().st_mtime
                
        while self.running:
            for p in self.watch_paths:
                if p.exists():
                    try:
                        current_mtime = p.stat().st_mtime
                        last_mtime = self._last_mtimes.get(p)
                        
                        if last_mtime != current_mtime:
                            self._last_mtimes[p] = current_mtime
                            # Trigger callback
                            logger.debug(f"File changed: {p.name}")
                            if asyncio.iscoroutinefunction(self.callback):
                                await self.callback(p)
                            else:
                                self.callback(p)
                    except OSError:
                        pass # File reading error, skip this tick
            
            await asyncio.sleep(self.polling_interval)

    async def stop(self):
        """Stop watching"""
        self.running = False
        if self.use_watchdog:
            self.observer.stop()
            self.observer.join()
