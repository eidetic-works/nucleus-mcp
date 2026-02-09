
import os
import json
import time
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Setup basic logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("nucleus")

def get_brain_path() -> Path:
    """Get the brain path from environment or default."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH", ".brain")
    path = Path(brain_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def make_response(success: bool, data=None, error=None, error_code=None):
    """Standardized API response formatter."""
    return json.dumps({
        "success": success,
        "data": data,
        "error": error,
        "error_code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }, indent=2)

def _get_state() -> Dict:
    """Read state from brain."""
    try:
        brain = get_brain_path()
        state_path = brain / "ledger" / "state.json"
        
        if not state_path.exists():
            return {}
            
        with open(state_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading state: {e}")
        return {}

def _update_state(updates: Dict[str, Any]) -> str:
    """Update state in brain."""
    try:
        brain = get_brain_path()
        state_path = brain / "ledger" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        current_state = _get_state()
        current_state.update(updates)
        current_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        with open(state_path, "w") as f:
            json.dump(current_state, f, indent=2)
            
        return "State updated successfully"
    except Exception as e:
        return f"Error updating state: {str(e)}"
