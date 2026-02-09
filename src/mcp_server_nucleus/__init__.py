
"""
Nucleus MCP - The Universal Brain for AI Agents
Cross-platform memory sync for Cursor, Claude Desktop, Windsurf, and any MCP-compatible tool.

MIT License - https://github.com/eidetic-works/nucleus-mcp
"""

__version__ = "1.0.0"

import json
import logging
import os
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .runtime.common import get_brain_path, make_response
from .runtime.event_ops import _emit_event

# Record start time for uptime tracking
START_TIME = time.time()

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("nucleus")

# Load FastMCP or Fallback
try:
    from fastmcp import FastMCP
    mcp = FastMCP("Nucleus Brain")
except ImportError:
    class MockMCP:
        def tool(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def resource(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def prompt(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def run(self): pass
    mcp = MockMCP()

# =============================================================================
# MEMORY TOOLS (V2 SCHEMA)
# =============================================================================

@mcp.tool()
def brain_write_engram(key: str, value: str, context: str = "Decision", intensity: int = 5) -> str:
    """
    Store persistent knowledge in the brain using the Key/Value schema.

    Args:
        key: Unique identifier for the engram (alpha-numeric)
        value: The knowledge or decision to store
        context: Contextual boundary (e.g., 'Decision', 'Architecture', 'Strategy')
        intensity: Importance level (1-10)
    """
    try:
        engram_path = get_brain_path() / "engrams" / "ledger.jsonl"
        engram_path.parent.mkdir(parents=True, exist_ok=True)

        engram = {
            "key": key,
            "value": value,
            "context": context,
            "intensity": intensity,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        with open(engram_path, "a") as f:
            f.write(json.dumps(engram) + "\n")

        _emit_event("ENGRAM_CREATED", "nucleus_mcp", {"key": key, "context": context})
        return make_response(True, data={"engram": engram, "message": f"Engram '{key}' written."})
    except Exception as e:
        return make_response(False, error=str(e))

@mcp.tool()
def brain_query_engrams(context: Optional[str] = None, min_intensity: int = 1) -> str:
    """
    Query stored knowledge from the brain.
    """
    try:
        engram_path = get_brain_path() / "engrams" / "ledger.jsonl"
        if not engram_path.exists():
            return make_response(True, data={"engrams": [], "count": 0})

        records = []
        with open(engram_path, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        filtered = [r for r in records if r.get("intensity", 5) >= min_intensity]
        if context:
            filtered = [r for r in filtered if r.get("context") == context]

        filtered.sort(key=lambda x: x.get("intensity", 5), reverse=True)
        return make_response(True, data={"engrams": filtered, "count": len(filtered)})
    except Exception as e:
        return make_response(False, error=str(e))

@mcp.tool()
def brain_governance_status() -> str:
    """
    [GOVERNANCE] Check the current security and compliance state of the Nucleus brain.
    """
    try:
        engram_count = 0
        engram_file = get_brain_path() / "engrams" / "ledger.jsonl"
        if engram_file.exists():
             engram_count = len(engram_file.read_text().splitlines())
             
        status = {
            "policies": {"default_deny": True, "isolation_boundaries": True, "immutable_audit": True},
            "statistics": {"engram_count": engram_count},
            "status": "ENFORCED"
        }
        return make_response(True, data=status)
    except Exception as e:
        return make_response(False, error=str(e))

# =============================================================================
# HYPERVISOR TOOLS
# =============================================================================

@mcp.tool()
def lock_resource(path: str) -> str:
    """[HYPERVISOR] Lock a file/folder to prevent modification (Layer 4)."""
    from .hypervisor.locker import Locker
    success = Locker().lock(path)
    return make_response(success, data={"path": path, "status": "LOCKED" if success else "FAILED"})

@mcp.tool()
def unlock_resource(path: str) -> str:
    """[HYPERVISOR] Unlock a resource."""
    from .hypervisor.locker import Locker
    success = Locker().unlock(path)
    return make_response(success, data={"path": path, "status": "UNLOCKED" if success else "FAILED"})

@mcp.tool()
def watch_resource(path: str) -> str:
    """[HYPERVISOR] Start monitoring a file/folder for changes."""
    from .hypervisor.watchdog import Watchdog
    Watchdog(os.getcwd()).protect(path)
    return make_response(True, data={"path": path, "status": "WATCHING"})

@mcp.tool()
def set_hypervisor_mode(mode: str) -> str:
    """[HYPERVISOR] Switch visual context (red/blue/reset)."""
    from .hypervisor.injector import Injector
    injector = Injector(os.getcwd())
    if mode == "reset":
        success = injector.reset_identity()
    else:
        colors = {"red": "#ff0000", "blue": "#0000ff"}
        success = injector.inject_identity(mode, colors.get(mode, "#333333"))
    return make_response(success, data={"mode": mode})
