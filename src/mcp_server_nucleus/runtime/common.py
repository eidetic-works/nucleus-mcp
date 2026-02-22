"""
Nucleus Runtime - Common Utilities
==================================
Shared utilities and constants for the Nucleus runtime.
"""

import os
import json
import logging
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

def get_brain_path() -> Path:
    """Get the brain path from environment variable (read dynamically for testing)."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
    if not brain_path:
        raise ValueError("NUCLEAR_BRAIN_PATH environment variable not set")
    path = Path(brain_path)
    if not path.exists():
         raise ValueError(f"Brain path does not exist: {brain_path}")
    return path

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
            with open(state_path, "r") as f:
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
                with open(state_path, "r") as f:
                    current_state = json.load(f)
            
            current_state.update(updates)
            
            with open(state_path, "w") as f:
                json.dump(current_state, f, indent=2)
            
        return "State updated successfully"
    except Exception as e:
        return f"Error updating state: {str(e)}"
