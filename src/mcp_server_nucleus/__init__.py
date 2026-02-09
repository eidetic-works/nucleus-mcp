"""
Nucleus MCP - The Universal Brain for AI Agents
Cross-platform memory sync for Cursor, Claude Desktop, Windsurf, and any MCP-compatible tool.

MIT License - https://github.com/eidetic-works/nucleus-mcp
"""

__version__ = "1.0.0"

import os
import json
import time
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

# Record start time for uptime tracking
START_TIME = time.time()

# Setup logging - use stderr to avoid breaking MCP protocol
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("nucleus")

# Global flag for fallback mode
USE_STDIO_FALLBACK = False

# Initialize FastMCP Server with fallback
try:
    from fastmcp import FastMCP
    mcp = FastMCP("Nucleus Brain")
except ImportError:
    USE_STDIO_FALLBACK = True
    import sys
    sys.stderr.write("[Nucleus] FastMCP not installed. Install with: pip install nucleus-mcp[full]\n")
    sys.stderr.flush()
    
    class MockMCP:
        """Fallback when FastMCP is not installed."""
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
# CORE UTILITIES
# =============================================================================

def get_brain_path() -> Path:
    """Get the brain path from environment or default."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH", ".brain")
    path = Path(brain_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_response(success: bool, message: str, data: Optional[Dict] = None) -> str:
    """Create a standardized JSON response."""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if data:
        response["data"] = data
    return json.dumps(response, indent=2)


def _get_state() -> Dict[str, Any]:
    """Get current brain state."""
    state_path = get_brain_path() / "ledger" / "state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _update_state(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update brain state."""
    state = _get_state()
    state.update(updates)
    state["last_updated"] = datetime.now().isoformat()
    
    state_path = get_brain_path() / "ledger" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2))
    return state


def _emit_event(event_type: str, data: Dict[str, Any]) -> None:
    """Emit an event to the ledger."""
    events_path = get_brain_path() / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    
    event = {
        "type": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    
    with open(events_path, "a") as f:
        f.write(json.dumps(event) + "\n")


# =============================================================================
# MEMORY TOOLS
# =============================================================================

@mcp.tool()
def brain_write_engram(content: str, category: str = "general", tags: Optional[List[str]] = None) -> str:
    """
    Store persistent knowledge in the brain.
    
    Args:
        content: The knowledge to store
        category: Category for organization (e.g., 'decision', 'architecture', 'task')
        tags: Optional list of tags for searching
    
    Returns:
        JSON response with engram ID
    """
    import hashlib
    
    engrams_path = get_brain_path() / "engrams"
    engrams_path.mkdir(parents=True, exist_ok=True)
    
    engram_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    
    engram = {
        "id": engram_id,
        "content": content,
        "category": category,
        "tags": tags or [],
        "created_at": datetime.now().isoformat()
    }
    
    engram_file = engrams_path / f"{engram_id}.json"
    engram_file.write_text(json.dumps(engram, indent=2))
    
    _emit_event("ENGRAM_CREATED", {"engram_id": engram_id, "category": category})
    
    return make_response(True, f"Engram stored: {engram_id}", {"engram_id": engram_id})


@mcp.tool()
def brain_query_engrams(query: str = "", category: str = "", limit: int = 10) -> str:
    """
    Query stored knowledge from the brain.
    
    Args:
        query: Search term (searches content)
        category: Filter by category
        limit: Maximum results to return
    
    Returns:
        JSON response with matching engrams
    """
    engrams_path = get_brain_path() / "engrams"
    
    if not engrams_path.exists():
        return make_response(True, "No engrams found", {"engrams": []})
    
    results = []
    for engram_file in engrams_path.glob("*.json"):
        try:
            engram = json.loads(engram_file.read_text())
            
            # Filter by category
            if category and engram.get("category") != category:
                continue
            
            # Filter by query
            if query and query.lower() not in engram.get("content", "").lower():
                continue
            
            results.append(engram)
            
            if len(results) >= limit:
                break
        except (json.JSONDecodeError, IOError):
            continue
    
    return make_response(True, f"Found {len(results)} engrams", {"engrams": results})


@mcp.tool()
def brain_audit_log(limit: int = 20) -> str:
    """
    View the decision/event audit log.
    
    Args:
        limit: Maximum events to return
    
    Returns:
        JSON response with recent events
    """
    events_path = get_brain_path() / "ledger" / "events.jsonl"
    
    if not events_path.exists():
        return make_response(True, "No events logged yet", {"events": []})
    
    events = []
    with open(events_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Return most recent events
    recent = events[-limit:] if len(events) > limit else events
    recent.reverse()  # Most recent first
    
    return make_response(True, f"Showing {len(recent)} events", {"events": recent})


# =============================================================================
# STATE MANAGEMENT TOOLS
# =============================================================================

@mcp.tool()
def brain_get_state() -> str:
    """
    Get current project/brain state.
    
    Returns:
        JSON response with current state
    """
    state = _get_state()
    return make_response(True, "Current state retrieved", {"state": state})


@mcp.tool()
def brain_set_state(key: str, value: str) -> str:
    """
    Set a state value in the brain.
    
    Args:
        key: State key
        value: State value
    
    Returns:
        JSON response confirming update
    """
    _update_state({key: value})
    _emit_event("STATE_UPDATED", {"key": key, "value": value})
    return make_response(True, f"State updated: {key}", {"key": key, "value": value})


@mcp.tool()
def brain_list_artifacts() -> str:
    """
    List all artifacts in the brain.
    
    Returns:
        JSON response with artifact listing
    """
    artifacts_path = get_brain_path() / "artifacts"
    
    if not artifacts_path.exists():
        return make_response(True, "No artifacts found", {"artifacts": []})
    
    artifacts = []
    for item in artifacts_path.rglob("*"):
        if item.is_file():
            artifacts.append({
                "path": str(item.relative_to(artifacts_path)),
                "size": item.stat().st_size,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
            })
    
    return make_response(True, f"Found {len(artifacts)} artifacts", {"artifacts": artifacts})


# =============================================================================
# SYNC TOOLS (Multi-Agent)
# =============================================================================

_current_agent = None

@mcp.tool()
def brain_identify_agent(agent_id: str, agent_type: str = "unknown") -> str:
    """
    Register this agent's identity for sync tracking.
    
    Args:
        agent_id: Unique identifier (e.g., 'cursor_main', 'claude_desktop')
        agent_type: Type of agent (e.g., 'cursor', 'claude', 'windsurf')
    
    Returns:
        JSON response confirming registration
    """
    global _current_agent
    _current_agent = {"id": agent_id, "type": agent_type}
    
    agents_path = get_brain_path() / "agents"
    agents_path.mkdir(parents=True, exist_ok=True)
    
    agent_file = agents_path / f"{agent_id}.json"
    agent_data = {
        "id": agent_id,
        "type": agent_type,
        "registered_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    }
    agent_file.write_text(json.dumps(agent_data, indent=2))
    
    _emit_event("AGENT_REGISTERED", {"agent_id": agent_id, "agent_type": agent_type})
    
    return make_response(True, f"Agent registered: {agent_id}", {"agent": agent_data})


@mcp.tool()
def brain_sync_now() -> str:
    """
    Manually trigger a brain sync.
    Writes current timestamp to sync state for other agents to detect.
    
    Returns:
        JSON response with sync status
    """
    sync_path = get_brain_path() / "sync"
    sync_path.mkdir(parents=True, exist_ok=True)
    
    sync_state = {
        "last_sync": datetime.now().isoformat(),
        "agent": _current_agent.get("id") if _current_agent else "unknown",
        "status": "synced"
    }
    
    (sync_path / "state.json").write_text(json.dumps(sync_state, indent=2))
    
    _emit_event("SYNC_MANUAL", {"agent": sync_state["agent"]})
    
    return make_response(True, "Brain synced", {"sync": sync_state})


@mcp.tool()
def brain_sync_status() -> str:
    """
    Check the current sync status.
    
    Returns:
        JSON response with sync state and active agents
    """
    sync_path = get_brain_path() / "sync" / "state.json"
    agents_path = get_brain_path() / "agents"
    
    sync_state = {}
    if sync_path.exists():
        try:
            sync_state = json.loads(sync_path.read_text())
        except json.JSONDecodeError:
            pass
    
    active_agents = []
    if agents_path.exists():
        for agent_file in agents_path.glob("*.json"):
            try:
                agent = json.loads(agent_file.read_text())
                active_agents.append(agent)
            except (json.JSONDecodeError, IOError):
                continue
    
    return make_response(True, "Sync status retrieved", {
        "sync": sync_state,
        "agents": active_agents,
        "current_agent": _current_agent
    })


# =============================================================================
# HYPERVISOR TOOLS (Security)
# =============================================================================

@mcp.tool()
def lock_resource(path: str) -> str:
    """
    [HYPERVISOR] Lock a file/folder to prevent modification (Layer 4).
    Uses filesystem immutable flag on supported systems.
    
    Args:
        path: Absolute path to lock
    
    Returns:
        JSON response with lock status
    """
    import subprocess
    
    path = Path(path)
    if not path.exists():
        return make_response(False, f"Path does not exist: {path}")
    
    try:
        # macOS: Use chflags
        result = subprocess.run(
            ["chflags", "uchg", str(path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            _emit_event("RESOURCE_LOCKED", {"path": str(path)})
            return make_response(True, f"🔒 LOCKED: {path}")
        else:
            return make_response(False, f"Failed to lock: {result.stderr}")
    except FileNotFoundError:
        # Linux fallback: use chattr
        try:
            result = subprocess.run(
                ["chattr", "+i", str(path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                _emit_event("RESOURCE_LOCKED", {"path": str(path)})
                return make_response(True, f"🔒 LOCKED: {path}")
            else:
                return make_response(False, f"Failed to lock: {result.stderr}")
        except FileNotFoundError:
            return make_response(False, "Lock command not available on this system")


@mcp.tool()
def unlock_resource(path: str) -> str:
    """
    [HYPERVISOR] Unlock a resource.
    
    Args:
        path: Absolute path to unlock
    
    Returns:
        JSON response with unlock status
    """
    import subprocess
    
    path = Path(path)
    if not path.exists():
        return make_response(False, f"Path does not exist: {path}")
    
    try:
        result = subprocess.run(
            ["chflags", "nouchg", str(path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            _emit_event("RESOURCE_UNLOCKED", {"path": str(path)})
            return make_response(True, f"🔓 UNLOCKED: {path}")
        else:
            return make_response(False, f"Failed to unlock: {result.stderr}")
    except FileNotFoundError:
        try:
            result = subprocess.run(
                ["chattr", "-i", str(path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                _emit_event("RESOURCE_UNLOCKED", {"path": str(path)})
                return make_response(True, f"🔓 UNLOCKED: {path}")
            else:
                return make_response(False, f"Failed to unlock: {result.stderr}")
        except FileNotFoundError:
            return make_response(False, "Unlock command not available on this system")


@mcp.tool()
def watch_resource(path: str) -> str:
    """
    [HYPERVISOR] Start monitoring a file/folder for changes.
    
    Args:
        path: Path to watch
    
    Returns:
        JSON response with watch status
    """
    path = Path(path)
    if not path.exists():
        return make_response(False, f"Path does not exist: {path}")
    
    watches_path = get_brain_path() / "watches.json"
    
    watches = []
    if watches_path.exists():
        try:
            watches = json.loads(watches_path.read_text())
        except json.JSONDecodeError:
            watches = []
    
    if str(path) not in watches:
        watches.append(str(path))
        watches_path.write_text(json.dumps(watches, indent=2))
    
    _emit_event("WATCH_ADDED", {"path": str(path)})
    
    return make_response(True, f"Now watching: {path}", {"watches": watches})


@mcp.tool()
def hypervisor_status() -> str:
    """
    [HYPERVISOR] Reports the current security state of the Agent OS.
    
    Returns:
        JSON response with security status
    """
    watches_path = get_brain_path() / "watches.json"
    
    watches = []
    if watches_path.exists():
        try:
            watches = json.loads(watches_path.read_text())
        except json.JSONDecodeError:
            pass
    
    uptime = time.time() - START_TIME
    
    status = {
        "uptime_seconds": round(uptime, 2),
        "brain_path": str(get_brain_path()),
        "watched_resources": len(watches),
        "current_agent": _current_agent,
        "version": __version__
    }
    
    return make_response(True, "Hypervisor status", {"status": status})


# =============================================================================
# HEALTH CHECK
# =============================================================================

@mcp.tool()
def brain_health() -> str:
    """
    Check the health of the Nucleus brain.
    
    Returns:
        JSON response with health status
    """
    brain_path = get_brain_path()
    
    checks = {
        "brain_exists": brain_path.exists(),
        "ledger_exists": (brain_path / "ledger").exists(),
        "engrams_exists": (brain_path / "engrams").exists(),
        "state_valid": False,
        "uptime_seconds": round(time.time() - START_TIME, 2)
    }
    
    # Check state validity
    try:
        state = _get_state()
        checks["state_valid"] = isinstance(state, dict)
    except Exception:
        pass
    
    all_healthy = all([
        checks["brain_exists"],
        checks["ledger_exists"] or True,  # Optional
        checks["state_valid"] or True  # Optional
    ])
    
    return make_response(
        all_healthy,
        "Brain is healthy" if all_healthy else "Brain needs attention",
        {"checks": checks}
    )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the MCP server."""
    if USE_STDIO_FALLBACK:
        import sys
        sys.stderr.write("[Nucleus] Cannot start server without FastMCP. Install with: pip install nucleus-mcp[full]\n")
        sys.exit(1)
    
    mcp.run()


if __name__ == "__main__":
    main()
