"""
Nucleus Multi-Agent Sync Operations - Production Ready
Version: 0.7.0

Tier 1: Project-Level Multi-Agent Sync
- Zero-config by default (works without setup)
- Progressive enhancement with .brain/config/nucleus.yaml
- File locking for concurrent access
- Auto-sync with watchdog file watcher
- Conflict detection and resolution

Author: Boss Opus (CORE_SYN)
Date: 2026-02-08
"""

import os
import json
try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None
import time
import hashlib
import logging
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

logger = logging.getLogger("nucleus.sync")

# =============================================================================
# CONFIGURATION LOADER
# =============================================================================

def _load_sync_config(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load .brain/config/nucleus.yaml if it exists.
    Returns empty config if file doesn't exist (Tier 0 behavior).
    """
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    config_file = brain_path / "config" / "nucleus.yaml"
    
    if not config_file.exists():
        return {"sync": {"enabled": False}}
    
    try:
        import yaml
        config = yaml.safe_load(config_file.read_text())
        return config or {"sync": {"enabled": False}}
    except ImportError:
        # Fallback to JSON-style YAML parsing if PyYAML not installed
        try:
            content = config_file.read_text()
            # Simple YAML to dict for basic configs
            config = _parse_simple_yaml(content)
            return config
        except Exception as e:
            logger.warning(f"Could not parse nucleus.yaml: {e}")
            return {"sync": {"enabled": False}}
    except Exception as e:
        logger.warning(f"Error loading sync config: {e}")
        return {"sync": {"enabled": False}}


def _parse_simple_yaml(content: str) -> Dict[str, Any]:
    """Simple YAML parser for basic nucleus.yaml configs."""
    result = {}
    current_section = result
    section_stack = [result]
    indent_stack = [0]
    
    for line in content.split("\n"):
        # Skip comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        
        # Handle key-value pairs
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            
            # Pop sections if we're at a lower indent level
            while indent_stack and indent <= indent_stack[-1] and len(section_stack) > 1:
                section_stack.pop()
                indent_stack.pop()
                current_section = section_stack[-1]
            
            if value:
                # Simple value
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                current_section[key] = value
            else:
                # New section
                current_section[key] = {}
                section_stack.append(current_section[key])
                indent_stack.append(indent)
                current_section = current_section[key]
        
        # Handle list items
        elif stripped.startswith("- "):
            item = stripped[2:].strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            # Find the parent key for this list
            for key in reversed(list(current_section.keys())):
                if isinstance(current_section[key], dict) and not current_section[key]:
                    current_section[key] = [item]
                    break
                elif isinstance(current_section[key], list):
                    current_section[key].append(item)
                    break
    
    return result


def is_sync_enabled(brain_path: Optional[Path] = None) -> bool:
    """Check if sync is enabled for this project."""
    config = _load_sync_config(brain_path)
    return config.get("sync", {}).get("enabled", False)


def get_sync_mode(brain_path: Optional[Path] = None) -> str:
    """Get sync mode: 'auto' or 'manual'."""
    config = _load_sync_config(brain_path)
    return config.get("sync", {}).get("mode", "manual")


def get_watch_files(brain_path: Optional[Path] = None) -> List[str]:
    """Get list of files to watch for sync."""
    config = _load_sync_config(brain_path)
    return config.get("sync", {}).get("watch_files", [
        "ledger/state.json",
        "ledger/decisions.md",
        "task.md"
    ])


def get_sync_interval(brain_path: Optional[Path] = None) -> int:
    """Get sync interval in seconds."""
    config = _load_sync_config(brain_path)
    return config.get("sync", {}).get("interval", 5)


# =============================================================================
# AGENT IDENTIFICATION
# =============================================================================

# Process-local identity cache (Concurrency Hotfix)
_current_identity: Optional[str] = None


def get_current_agent(brain_path: Optional[Path] = None) -> str:
    """
    Get current agent ID, with auto-detection fallback.
    
    Priority:
    1. Process-Local Memory (Sticky & Safe)
    2. Environment variable detection
    3. .brain/.nucleus_agent file (Last Resort / Logging only)
    4. "unknown_agent" fallback
    """
    global _current_identity
    
    # Priority 1: Process-Local Memory (The Golden Source)
    if _current_identity:
        return _current_identity

    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    # Priority 2: Environment detection
    # Check for IDE-specific environment variables
    if os.environ.get("WINDSURF_SESSION"):
        return "windsurf_auto"
    elif os.environ.get("CURSOR_SESSION"):
        return "cursor_auto"
    elif os.environ.get("CLAUDE_DESKTOP"):
        return "claude_desktop_auto"
    elif os.environ.get("VSCODE_PID"):
        return "vscode_auto"
    
    # Check for custom agent ID
    custom_id = os.environ.get("NUCLEUS_AGENT_ID")
    if custom_id:
        return custom_id
        
    # Priority 3: Explicit registration file (Last Resort / Cold Start)
    agent_file = brain_path / ".nucleus_agent"
    if agent_file.exists():
        try:
            agent_info = json.loads(agent_file.read_text())
            # Only trust file if it matches our PID (Session Recovery)
            # Otherwise we risk reading another agent's identity
            if agent_info.get("pid") == os.getpid():
                 return agent_info.get("agent_id", "unknown_agent")
        except Exception:
            pass
    
    # Priority 4: Fallback
    return "unknown_agent"


def set_current_agent(agent_id: str, environment: str, role: str = "", 
                      brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Register current agent identity.
    Updates process-local memory FIRST, then persists to file.
    """
    global _current_identity
    
    # Update memory immediately (Atomic for this process)
    _current_identity = agent_id

    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    agent_file = brain_path / ".nucleus_agent"
    
    agent_info = {
        "agent_id": agent_id,
        "environment": environment,
        "role": role,
        "registered_at": datetime.now().isoformat(),
        "pid": os.getpid()
    }
    
    agent_file.write_text(json.dumps(agent_info, indent=2))
    
    return {
        **agent_info,
        "stored_in": str(agent_file)
    }


def get_agent_info(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get full agent info if registered."""
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    agent_file = brain_path / ".nucleus_agent"
    
    if agent_file.exists():
        try:
            return json.loads(agent_file.read_text())
        except Exception:
            pass
    
    return {
        "agent_id": get_current_agent(brain_path),
        "environment": "unknown",
        "role": "",
        "registered_at": None,
        "auto_detected": True
    }


# =============================================================================
# FILE LOCKING
# =============================================================================

@contextmanager
def sync_lock(brain_path: Optional[Path] = None, timeout: int = 5):
    """
    Acquire exclusive lock for syncing.
    Uses fcntl.flock for cross-process synchronization.
    
    Args:
        brain_path: Path to .brain directory
        timeout: Maximum seconds to wait for lock
    
    Raises:
        Exception if lock cannot be acquired within timeout
    """
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    lock_file_path = brain_path / ".sync.lock"
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open lock file
    lock_fd = open(lock_file_path, 'w')
    
    # Try to acquire lock with timeout
    start_time = time.time()
    
    while True:
        try:
            if fcntl:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif msvcrt:
                lock_fd.seek(0)
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except IOError:
            if time.time() - start_time > timeout:
                lock_fd.close()
                raise Exception(f"Could not acquire sync lock after {timeout}s - another agent may be syncing")
            time.sleep(0.1)
    
    try:
        # Write lock holder info
        lock_info = {
            "agent": get_current_agent(brain_path),
            "acquired_at": datetime.now().isoformat(),
            "pid": os.getpid()
        }
        lock_fd.write(json.dumps(lock_info))
        lock_fd.flush()
        
        yield
    finally:
        # Release lock
        if fcntl:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        elif msvcrt:
            lock_fd.seek(0)
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
        lock_fd.close()
        try:
            lock_file_path.unlink(missing_ok=True)
        except Exception:
            pass


def _verify_brain_path_safety(brain_path: Path):
    """
    Ensure the brain path is technically safe/allowed.
    Requirement from Turning 23/29 Resilience Audit.
    """
    if os.environ.get("NUCLEUS_UNSAFE_SYNC") == "true":
        return
        
    try:
        from .common import get_brain_path
        configured_brain = get_brain_path().resolve()
        
        # Must be exactly the configured brain path or a descendant
        if not str(brain_path.resolve()).startswith(str(configured_brain)):
            raise PermissionError(f"Access denied: Path {brain_path} is outside the configured Nucleus project scope.")
    except Exception as e:
        if isinstance(e, PermissionError):
            raise
        # Fallback for transient resolution errors
        pass


def _calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash in chunks to prevent memory spikes.
    Requirement from Finding 2 (Performance).
    """
    if not file_path.exists():
        return ""
        
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception as e:
        logger.warning(f"Error hashing {file_path}: {e}")
        return ""
# =============================================================================
# SYNC METADATA TRACKING
# =============================================================================

def _get_meta_file(file_path: Path) -> Path:
    """Get the metadata file path for a given file."""
    return file_path.parent / f".{file_path.name}.meta"


def get_last_modifier(file_path: Path) -> str:
    """Get agent that last modified this file."""
    meta_file = _get_meta_file(file_path)
    
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            return meta.get("last_agent", "unknown")
        except Exception:
            pass
    
    return "unknown"


def set_last_modifier(file_path: Path, agent_id: str):
    """Record which agent last modified this file with stat optimization."""
    meta_file = _get_meta_file(file_path)
    
    # Calculate file hash using the new chunked method
    file_hash = _calculate_file_hash(file_path)
    
    # Stat capture for high-speed conflict bypass
    stat = file_path.stat() if file_path.exists() else None
    
    meta = {
        "last_agent": agent_id,
        "last_modified": datetime.now().isoformat(),
        "file": str(file_path.name),
        "expected_hash": file_hash,
        "st_mtime_ns": stat.st_mtime_ns if stat else 0,
        "st_size": stat.st_size if stat else 0
    }
    
    # Atomic write pattern (tmp + replace)
    tmp_meta = meta_file.with_suffix(".tmp")
    try:
        tmp_meta.write_text(json.dumps(meta, indent=2))
        os.replace(tmp_meta, meta_file)
    except Exception as e:
        logger.error(f"Failed to write metadata for {file_path}: {e}")


def _cleanup_stale_conflicts(brain_path: Path):
    """Automatic cleanup of resolved .conflict files (Hygiene)."""
    try:
        from .sync_ops import get_watch_files
        for rel_path in get_watch_files(brain_path):
            file_path = brain_path / rel_path
            conflict_file = file_path.parent / f".{file_path.name}.conflict"
            if conflict_file.exists():
                # If no active conflict detected, remove the stale marker
                if not detect_conflict(file_path):
                    conflict_file.unlink(missing_ok=True)
                    logger.info(f"Cleaned up stale conflict marker for {rel_path}")
    except Exception as e:
        logger.debug(f"Cleanup failed (non-critical): {e}")


def get_file_meta(file_path: Path) -> Dict[str, Any]:
    """Get full metadata for a file."""
    meta_file = _get_meta_file(file_path)
    
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text())
        except Exception:
            pass
    
    return {}


# =============================================================================
# CONFLICT DETECTION
# =============================================================================

def detect_conflict(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Detect if file has conflicting changes with stat optimization.
    
    Returns conflict info if detected, None otherwise.
    """
    meta_file = _get_meta_file(file_path)
    
    if not meta_file.exists() or not file_path.exists():
        return None
    
    try:
        meta = json.loads(meta_file.read_text())
        
        # Fast Check Bypass (Stat Capture)
        if os.environ.get("NUCLEUS_SYNC_FORCE_HASH") != "true":
            stat = file_path.stat()
            if "st_mtime_ns" in meta and meta["st_mtime_ns"] == stat.st_mtime_ns:
                if "st_size" in meta and meta["st_size"] == stat.st_size:
                    # Skip expensive hashing
                    return None
        
        # Fallback to absolute content hash verification
        current_hash = _calculate_file_hash(file_path)
        
        if "expected_hash" in meta and meta["expected_hash"] != current_hash:
            return {
                "file": str(file_path),
                "expected_agent": meta.get("last_agent"),
                "expected_hash": meta["expected_hash"],
                "actual_hash": current_hash,
                "last_modified": meta.get("last_modified"),
                "conflict_type": "unexpected_modification"
            }
    except Exception as e:
        logger.warning(f"Error detecting conflict for {file_path}: {e}")
    
    return None


def resolve_conflict(conflict: Dict[str, Any], strategy: str, 
                     brain_path: Optional[Path] = None) -> str:
    """
    Resolve a detected conflict.
    
    Strategies:
    - "last_write_wins": Accept current state
    - "manual": Create conflict marker file
    """
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    file_path = Path(conflict["file"])
    
    if strategy == "last_write_wins":
        # Accept current state, update metadata
        set_last_modifier(file_path, get_current_agent(brain_path))
        return "resolved_accept_current"
    
    elif strategy == "manual":
        # Create conflict marker file for manual resolution
        conflict_file = file_path.parent / f".{file_path.name}.conflict"
        conflict["detected_at"] = datetime.now().isoformat()
        conflict["detected_by"] = get_current_agent(brain_path)
        conflict_file.write_text(json.dumps(conflict, indent=2))
        return "requires_manual_resolution"
    
    else:
        raise ValueError(f"Unknown conflict strategy: {strategy}")


# =============================================================================
# CORE SYNC LOGIC
# =============================================================================

def perform_sync(force: bool = False, brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Core sync logic with hardened v0.7.1 refinements.
    """
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    # Pillar 1: Path Security Verify
    _verify_brain_path_safety(brain_path)
    
    config = _load_sync_config(brain_path)
    current_agent = get_current_agent(brain_path)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "agent": current_agent,
        "files_synced": [],
        "conflicts": [],
        "sync_duration_ms": 0
    }
    
    start_time = time.time()
    
    # Get files to check
    watch_files = get_watch_files(brain_path)
    conflict_strategy = config.get("sync", {}).get("conflict_resolution", "last_write_wins")
    
    for watch_file in watch_files:
        file_path = brain_path / watch_file
        
        if not file_path.exists():
            continue
        
        # Check for conflicts
        conflict = detect_conflict(file_path)
        if conflict:
            resolution = resolve_conflict(conflict, conflict_strategy, brain_path)
            result["conflicts"].append({
                **conflict,
                "resolution": resolution
            })
        
        # Check if file was modified by another agent
        last_modifier = get_last_modifier(file_path)
        
        if last_modifier != current_agent or force:
            # File was changed by another agent or force sync
            result["files_synced"].append({
                "file": watch_file,
                "action": "reloaded" if last_modifier != current_agent else "refreshed",
                "previous_agent": last_modifier,
                "current_agent": current_agent
            })
            
            # Update metadata to mark current agent
            set_last_modifier(file_path, current_agent)
    
    # Pillar 4: Garbage Collection (Marker Cleanup)
    _cleanup_stale_conflicts(brain_path)
    
    result["sync_duration_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def get_sync_status(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get comprehensive sync status.
    
    Returns current state including:
    - Sync enabled/mode
    - Current agent
    - Detected agents from metadata
    - Pending conflicts
    - Auto-sync status
    """
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    config = _load_sync_config(brain_path)
    sync_config = config.get("sync", {})
    
    # Detect all agents that have modified files
    detected_agents = set()
    pending_conflicts = []
    
    for watch_file in get_watch_files(brain_path):
        file_path = brain_path / watch_file
        if file_path.exists():
            meta = get_file_meta(file_path)
            if meta.get("last_agent"):
                detected_agents.add(meta["last_agent"])
            
            conflict = detect_conflict(file_path)
            if conflict:
                pending_conflicts.append(conflict)
    
    # Get last sync time
    last_sync = None
    sync_log = brain_path / ".sync_last"
    if sync_log.exists():
        try:
            last_sync = sync_log.read_text().strip()
        except Exception:
            pass
    
    return {
        "sync_enabled": sync_config.get("enabled", False),
        "mode": sync_config.get("mode", "manual"),
        "last_sync": last_sync,
        "current_agent": get_current_agent(brain_path),
        "agent_info": get_agent_info(brain_path),
        "detected_agents": list(detected_agents),
        "files_watched": get_watch_files(brain_path),
        "pending_conflicts": pending_conflicts,
        "auto_sync_running": _is_watcher_running(),
        "config_file": str(brain_path / "config" / "nucleus.yaml"),
        "config_exists": (brain_path / "config" / "nucleus.yaml").exists()
    }


def record_sync_time(brain_path: Optional[Path] = None):
    """Record the last sync timestamp."""
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    sync_log = brain_path / ".sync_last"
    sync_log.write_text(datetime.now().isoformat())


# =============================================================================
# AUTO-SYNC FILE WATCHER
# =============================================================================

# Global observer instance
_observer = None
_observer_lock = threading.Lock()


def _is_watcher_running() -> bool:
    """Check if file watcher is running."""
    global _observer
    return _observer is not None and _observer.is_alive()


class BrainSyncHandler:
    """File system event handler for auto-sync with serialized worker (v0.7.1)."""
    
    def __init__(self, brain_path: Path, config: Dict[str, Any]):
        self.brain_path = brain_path
        self.config = config
        self.watch_files = set(config.get("sync", {}).get("watch_files", []))
        self.last_sync: Dict[str, float] = {}
        self.min_interval = config.get("sync", {}).get("interval", 5)
        
        # Serialized Work Queue
        self.work_queue = queue.Queue()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()
    
    def _worker_loop(self):
        """Single worker thread to process sync requests one at a time."""
        while True:
            try:
                rel_path = self.work_queue.get()
                if rel_path is None:
                    break
                self._sync_file(rel_path)
                self.work_queue.task_done()
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(1)

    def on_modified(self, event):
        """Handle file modification events by queuing them."""
        if event.is_directory:
            return
        
        try:
            # Check if this is a watched file
            file_path = Path(event.src_path)
            rel_path = file_path.relative_to(self.brain_path)
            
            if str(rel_path) not in self.watch_files:
                return
            
            # Debounce - don't queue too frequently for the same file
            now = time.time()
            key = str(rel_path)
            if key in self.last_sync:
                if now - self.last_sync[key] < self.min_interval:
                    return
            
            self.last_sync[key] = now
            
            # Queue the work instead of spawning a thread (Finding 3)
            self.work_queue.put(rel_path)
        except Exception as e:
            logger.error(f"Error in file watcher: {e}")
    
    def _sync_file(self, rel_path: Path):
        """Sync a single file."""
        try:
            with sync_lock(self.brain_path, timeout=2):
                logger.info(f"Auto-syncing due to change in {rel_path}")
                result = perform_sync(force=False, brain_path=self.brain_path)
                record_sync_time(self.brain_path)
                
                # Emit event ONLY if something changed or conflict occurred (Finding 3: Noise)
                if result.get("files_synced") or result.get("conflicts"):
                    from .event_ops import _emit_event
                    _emit_event(
                        event_type="SYNC_AUTO",
                        emitter=get_current_agent(self.brain_path),
                        data=result,
                        description=f"Auto-sync detected changes triggered by {rel_path}"
                    )
        except Exception as e:
            logger.error(f"Auto-sync failed: {e}")


def start_file_watcher(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Start watching files for changes.
    
    Uses watchdog library for cross-platform file watching.
    """
    global _observer
    
    if brain_path is None:
        from .common import get_brain_path
        brain_path = get_brain_path()
    
    config = _load_sync_config(brain_path)
    
    if not config.get("sync", {}).get("enabled"):
        return {
            "error": "Sync not enabled",
            "hint": "Add sync.enabled: true to .brain/config/nucleus.yaml"
        }
    
    with _observer_lock:
        # Stop existing watcher if running
        if _observer is not None:
            stop_file_watcher()
        
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            # Create handler
            handler = BrainSyncHandler(brain_path, config)
            
            # Create a watchdog-compatible wrapper
            class WatchdogHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    handler.on_modified(event)
            
            _observer = Observer()
            _observer.schedule(WatchdogHandler(), str(brain_path), recursive=True)
            _observer.start()
            
            logger.info(f"File watcher started for {brain_path}")
            
            return {
                "auto_sync_enabled": True,
                "watching_files": list(handler.watch_files),
                "check_interval": handler.min_interval,
                "status": "watcher_started",
                "brain_path": str(brain_path)
            }
        except ImportError:
            return {
                "error": "watchdog library not installed",
                "hint": "pip install watchdog",
                "status": "watcher_not_available"
            }
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            return {
                "error": str(e),
                "status": "watcher_failed"
            }


def stop_file_watcher() -> Dict[str, Any]:
    """Stop file watcher."""
    global _observer
    
    with _observer_lock:
        if _observer is not None:
            try:
                _observer.stop()
                _observer.join(timeout=5)
                _observer = None
                logger.info("File watcher stopped")
                return {
                    "auto_sync_enabled": False,
                    "status": "watcher_stopped"
                }
            except Exception as e:
                logger.error(f"Error stopping watcher: {e}")
                _observer = None
                return {
                    "auto_sync_enabled": False,
                    "status": "watcher_stopped_with_error",
                    "error": str(e)
                }
        else:
            return {
                "auto_sync_enabled": False,
                "status": "watcher_not_running"
            }


# =============================================================================
# AUTO-START HOOK
# =============================================================================

def auto_start_sync_if_configured(brain_path: Optional[Path] = None):
    """
    Auto-start file watcher if configured for auto mode.
    Called during MCP server initialization.
    """
    if brain_path is None:
        try:
            from .common import get_brain_path
            brain_path = get_brain_path()
        except Exception:
            return
    
    config = _load_sync_config(brain_path)
    
    if config.get("sync", {}).get("enabled") and config.get("sync", {}).get("mode") == "auto":
        logger.info("Auto-starting sync watcher (mode=auto)")
        start_file_watcher(brain_path)
