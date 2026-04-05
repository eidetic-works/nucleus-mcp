"""
Nucleus Runtime - Common Utilities
==================================
Shared utilities and constants for the Nucleus runtime.
"""

import os
import json
import logging
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# ============================================================
# STRUCTURED LOGGING SYSTEM (AG-010)
# ============================================================

class JSONFormatter(logging.Formatter):
    """Formats log records as JSON objects for machine readability."""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_nucleus_logging(name: str = "nucleus", level: int = logging.INFO):
    """Setup structured logging for a component."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Use JSON if specified via env
        if os.environ.get("NUCLEUS_LOG_JSON", "false").lower() == "true":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        logger.addHandler(handler)
    return logger

# Common logger
logger = setup_nucleus_logging()

def get_nucleus_bin_path() -> str:
    """Return the directory containing the nucleus executable."""
    nucleus_bin = shutil.which("nucleus")
    if nucleus_bin:
        return str(Path(nucleus_bin).resolve().parent)
    # Fallback: same directory as the running Python interpreter
    return str(Path(sys.executable).resolve().parent)


def get_nucleus_mcp_command() -> list:
    """Return the command list for MCP config. Prefers nucleus-mcp binary (full path)."""
    bin_path = shutil.which("nucleus-mcp")
    if bin_path:
        return [str(Path(bin_path).resolve())]
    # Fallback: exact python that has nucleus installed + module
    return [sys.executable, "-m", "mcp_server_nucleus"]


def get_brain_path() -> Path:
    """Get the brain path from environment variable or auto-detect from working directory."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH") or os.environ.get("NUCLEUS_BRAIN_PATH")
    
    if brain_path:
        path = Path(brain_path)
        if not path.exists():
            # Auto-create brain directory structure instead of crashing
            try:
                path.mkdir(parents=True, exist_ok=True)
                for subdir in ["engrams", "ledger", "sessions", "memory",
                              "tasks", "artifacts", "proofs", "strategy",
                              "governance", "channels", "federation"]:
                    (path / subdir).mkdir(exist_ok=True)
                logger.info(f"Auto-created brain directory at {path}")
            except OSError as e:
                raise ValueError(f"Brain path does not exist and could not be created: {brain_path} ({e})")
        return path
    
    # Smart fallback: Find .brain in cwd or parent directories
    cwd = Path.cwd()
    if (cwd / ".brain").exists():
        return cwd / ".brain"
    
    for parent in cwd.parents:
        if (parent / ".brain").exists():
            return parent / ".brain"
            
    # If we get here, no brain was found
    raise ValueError("NUCLEAR_BRAIN_PATH environment variable not set and no .brain directory found in current or parent directories.")

def make_response(success: bool, data=None, error=None, error_code=None):
    """Standardized API response formatter.
    
    Args:
        success: Whether the operation succeeded
        data: Successful payload (dict, list, string)
        error: Error message if failed
        error_code: Optional short code for error (e.g. ERR_NOT_FOUND)
    
    Returns:
        JSON string matching Nucleus Standard Response Schema
    """
    return json.dumps({
        "success": success,
        "data": data,
        "error": error,
        "error_code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }, indent=2)

def _get_state(path: Optional[str] = None) -> Dict:
    """Core logic for getting state."""
    try:
        brain = get_brain_path()
        state_path = brain / "ledger" / "state.json"
        
        if not state_path.exists():
            return {}
            
        from .sync_ops import sync_lock
        with sync_lock(brain, timeout=2):
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
        if path:
            keys = path.split('.')
            val = state
            for k in keys:
                val = val.get(k, {})
            return val
            
        return state
    except Exception as e:
        logger.error(f"Error reading state: {e}")
        return {}

def _update_state(updates: Dict[str, Any]) -> str:
    """Core logic for updating state."""
    try:
        brain = get_brain_path()
        state_path = brain / "ledger" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        from .sync_ops import sync_lock
        with sync_lock(brain, timeout=5):
            current_state = {}
            if state_path.exists():
                with open(state_path, "r", encoding="utf-8") as f:
                    current_state = json.load(f)
            
            current_state.update(updates)
            
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(current_state, f, indent=2, ensure_ascii=False)
            
        return "State updated successfully"
    except Exception as e:
        return f"Error updating state: {str(e)}"
# ============================================================
# MOCK MCP SERVER (For fallback/verification mode)
# ============================================================

class MockMCP:
    """Mock FastMCP server for when the package is not installed."""
    def tool(self, *args, **kwargs):
        def decorator(f): return f
        return decorator
    def resource(self, *args, **kwargs):
        def decorator(f): return f
        return decorator
    def prompt(self, *args, **kwargs):
        def decorator(f): return f
        return decorator
    def run(self):
        pass
