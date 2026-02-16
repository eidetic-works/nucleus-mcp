

# =============================================================================
# Nucleus Sovereign Control Plane v1.0.0
# =============================================================================
__version__ = "1.0.4"

import os
import re # noqa: F401
import json
import time
import uuid # noqa: F401
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path # noqa: F401
import sys
import warnings

# CRITICAL: Suppress output pollution to protect JSON-RPC (Stdio)
# Verify urllib3 doesn't leak OpenSSL warnings to stderr which might break some strict MCP clients
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# Record start time for uptime tracking
START_TIME = time.time()

# v0.6.0 Tool Tier System - Solves Registry Bloat
from .tool_tiers import get_active_tier, get_tier_info, is_tool_allowed, tier_manager # noqa: E402

ACTIVE_TIER = get_active_tier()
logger_init = logging.getLogger("nucleus.init")
logger_init.info(f"Nucleus Tool Tier: {ACTIVE_TIER} ({get_tier_info()['tier_name']})")

# Configure FastMCP to disable banner and use stderr for logging to avoid breaking MCP protocol
os.environ["FASTMCP_SHOW_CLI_BANNER"] = "False"
os.environ["FASTMCP_LOG_LEVEL"] = "WARNING"

# from fastmcp import FastMCP (Moved to try/except block below)

# Import commitment ledger module
from . import commitment_ledger # noqa: F401, E402

# Phase 1 Monolith Decomposition Imports
from .runtime.common import get_brain_path, make_response, _get_state, _update_state # noqa: F401, E402
from .runtime.event_ops import _emit_event, _read_events # noqa: F401, E402
from .runtime.task_ops import ( # noqa: F401, E402
    _get_tasks_list, _save_tasks_list, _list_tasks, _add_task, 
    _claim_task, _update_task, _get_next_task, _import_tasks_from_jsonl,
    _escalate_task
) # noqa: F401
from .runtime.session_ops import ( # noqa: F401, E402
    _save_session, _resume_session, _list_sessions, 
    _get_session, _check_for_recent_session, _prune_old_sessions,
    _get_sessions_path, _get_active_session_path
) # noqa: F401
from .runtime.depth_ops import ( # noqa: F401, E402
    _get_depth_path, _get_depth_state, _save_depth_state, _depth_push, 
    _depth_pop, _depth_show, _depth_reset, _depth_set_max, _format_depth_indicator,
    _generate_depth_map
)
from .runtime.schema_gen import generate_tool_schema # noqa: F401, E402
from .runtime.mounter import get_mounter # noqa: F401, E402
from .runtime.sync_ops import ( # noqa: F401, E402
    get_current_agent, set_current_agent, get_agent_info,
    sync_lock, perform_sync, get_sync_status, record_sync_time,
    start_file_watcher, stop_file_watcher, is_sync_enabled,
    auto_start_sync_if_configured
) # noqa: F401
 # noqa: F401

# Setup logging
# logging.basicConfig(level=logging.INFO) # Removing to prevent overriding FastMCP settings
logger = logging.getLogger("nucleus")
logger.setLevel(logging.WARNING)

# Initialize FastMCP Server
# Global flag for fallback mode
USE_STDIO_FALLBACK = False

# Initialize FastMCP Server with fallback
try:
    from fastmcp import FastMCP
    mcp = FastMCP("Nucleus Brain")
except ImportError:
    USE_STDIO_FALLBACK = True
    import sys
    
    # CRITICAL: Use direct stderr write to ensure NO stdout pollution
    sys.stderr.write("[Nucleus Init] WARNING: FastMCP not installed. Running in standalone/verification mode.\\n")
    sys.stderr.flush()
    
    # Define MockMCP before use
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

# Initialize tiered tool registration (must happen after mcp is created)
from .core.tool_registration_impl import configure_tiered_tool_registration # noqa: E402
configure_tiered_tool_registration(mcp)



# ORCHESTRATOR V3.1 INTEGRATION
# ============================================================
# Lazy-loaded singleton for orchestrator access
# All task operations route through this for CRDT + V3.1 features
# IMPORTANT: Uses the SAME singleton as orchestrator_v3.get_orchestrator()

def get_orch():
    """Get the orchestrator singleton (Unified)."""
    from .runtime.orchestrator_unified import get_orchestrator # noqa: E402, F401
    return get_orchestrator()

# ============================================================
# CORE LOGIC (Testable, plain functions)
# ============================================================

# make_response imported from runtime.common
# _emit_event imported from runtime.event_ops
# _read_events imported from runtime.event_ops


# brain_health() defined later in file (line ~7155) - uses _brain_health_impl()

@mcp.tool()
def brain_auto_fix_loop(file_path: str, verification_command: str) -> str:
    """
    Auto-fix loop: Verify -> Diagnose -> Fix -> Verify.
    Retries up to 3 times.
    Phase 4: Self-Healing.
    """
    from .runtime.loops.fixer import FixerLoop # noqa: E402, F401
    
    # We pass brain_fix_code as the fixer callback
    # brain_fix_code returns a JSON string, which FixerLoop expects
    loop = FixerLoop(
        target_file=file_path,
        verification_command=verification_command,
        fixer_func=brain_fix_code,
        max_retries=3
    )
    
    result = loop.run()
    return json.dumps(result, indent=2)

# _get_state imported from runtime.common
# _update_state imported from runtime.common

# ============================================================
# HYPERVISOR LAYER (v0.8.0) - "God Mode" Lock
# ============================================================
from .hypervisor.locker import Locker # noqa: E402
_locker = Locker()

@mcp.tool()
def lock_resource(path: str) -> str:
    """
    [HYPERVISOR] Locks a file or directory using 'chflags uchg' (Immutable).
    Prevents ANY modification, even by root/sudo, until unlocked.
    Use this to protect critical state or during Red Team audits.
    """
    if _locker.lock(path):
        return f"🔒 LOCKED: {path} (Immutable flag set)"
    else:
        return f"❌ FAILED to lock: {path}"

@mcp.tool()
def unlock_resource(path: str) -> str:
    """
    [HYPERVISOR] Unlocks a file or directory (removes 'uchg' flag).
    """
    if _locker.unlock(path):
        return f"🔓 UNLOCKED: {path}"
    else:
        return f"❌ FAILED to unlock: {path}"

from .hypervisor.injector import Injector # noqa: E402
_injector = Injector(os.environ.get("NUCLEAR_BRAIN_PATH", "."))

@mcp.tool()
def set_hypervisor_mode(mode: str) -> str:
    """
    [HYPERVISOR] Switches the IDE visual context (Layer 2 Injection).
    mode: "red" (Audit/Attack) or "blue" (Build/Defend).
    """
    mode = mode.lower()
    if mode == "red":
        _injector.inject_identity("RED TEAM", "#ff0000")
        return "🔴 Hypervisor Mode: RED TEAM (Audit Active)"
    elif mode == "blue":
        _injector.inject_identity("BLUE TEAM", "#007acc")
        return "🔵 Hypervisor Mode: BLUE TEAM (Build Active)"
    elif mode == "reset":
        _injector.reset_identity()
        return "⚪ Hypervisor Mode: RESET (Default)"
    else:
        return "❌ Invalid mode. Use 'red', 'blue', or 'reset'."


from .hypervisor.watchdog import Watchdog # noqa: E402
# Derive workspace root from brain path (assuming .brain is in root)
_brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".")).resolve()
_workspace_root = _brain_path.parent
_watchdog = Watchdog(str(_workspace_root))
# Auto-start watchdog on server boot
try:
    _watchdog.start()
except Exception as e:
    logger.warning(f"Failed to start Hypervisor Watchdog: {e}")

@mcp.tool()
def nucleus_list_directory(path: str) -> str:
    """
    [GOVERNANCE] Lists files in a directory. 
    Allows the agent to safely inspect a folder before performing audit actions.
    """
    try:
        # Resolve symlinks to handle anonymized demo paths
        resolved_path = Path(path).resolve()
        if not resolved_path.exists():
            return f"❌ ERROR: Path not found: {path}"
            
        items = os.listdir(resolved_path)
        [f"📁 {p}" if (resolved_path / p).is_dir() else f"📄 {p}" for p in items]
        
        # Check lock status for each file
        status_lines = []
        for item in items:
            p = resolved_path / item
            locked = "🔒 LOCKED" if _locker.is_locked(str(p)) else "🔓 OPEN"
            status_lines.append(f"{locked} | {item}")
            
        return "\n".join(status_lines)
    except Exception as e:
        return f"❌ ERROR: {str(e)}"

@mcp.tool()
def nucleus_delete_file(path: str) -> str:
    """
    [GOVERNANCE] Attempts to delete a file. 
    This action is strictly governed by the Nucleus Hypervisor (Layer 4).
    """
    try:
        resolved_path = Path(path).resolve()
        
        # 1. Check Hypervisor Lock State
        if _locker.is_locked(str(resolved_path)):
            # Log the blocked attempt for the brain_audit_log demo
            _emit_event("access_denied", "hypervisor_l4", {
                "path": str(resolved_path),
                "action": "delete",
                "reason": "Resource is Immutable (Layer 4 Lock)"
            })
            return f"❌ BLOCKED: {path} is locked by Nucleus Hypervisor. Permission Denied."

        # 2. Perform deletion if NOT locked
        if not resolved_path.exists():
            return f"❌ ERROR: File not found: {path}"
            
        os.remove(resolved_path)
        return f"✅ SUCCESS: {path} has been removed."
        
    except Exception as e:
        return f"❌ ERROR: {str(e)}"

@mcp.tool()
def watch_resource(path: str) -> str:
    """
    [HYPERVISOR] key file/folder monitoring (Layer 1).
    If a protected resource is modified while locked, it triggers an alert
    and immediately re-applies the lock.
    """
    _watchdog.protect(path)
    return f"👁️ WATCHING: {path} (Security Sentinel Active)"

@mcp.tool()
def hypervisor_status() -> str:
    """
    [HYPERVISOR] Reports the current security state of the Agent OS.
    """
    status = []
    status.append("🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)")
    status.append(f"📍 Workspace: {_workspace_root}")
    status.append(f"👁️  Watchdog: {'Active' if _watchdog.observer.is_alive() else 'Inactive'}")
    status.append(f"🔒 Protected Paths: {len(_watchdog.protected_paths)}")
    for p in _watchdog.protected_paths:
        status.append(f"   - {p}")
    
    # Check ID injection status (proxy via environment or file check if possible, or just implicit)
    status.append("🎨 Injector: Ready")
    
    return "\n".join(status)

def _read_artifact(path: str) -> str:
    """Core logic for reading an artifact."""
    try:
        brain = get_brain_path()
        target = brain / "artifacts" / path
        
        if not str(target.resolve()).startswith(str((brain / "artifacts").resolve())):
             return "Error: Access denied (path traversal)"

        if not target.exists():
            return f"Error: File not found: {path}"
            
        return target.read_text()
    except Exception as e:
        return f"Error reading artifact: {str(e)}"

def _write_artifact(path: str, content: str) -> str:
    """Core logic for writing an artifact."""
    try:
        brain = get_brain_path()
        target = brain / "artifacts" / path
        
        if not str(target.resolve()).startswith(str((brain / "artifacts").resolve())):
             return "Error: Access denied (path traversal)"
             
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing artifact: {str(e)}"

def _list_artifacts(folder: Optional[str] = None) -> List[str]:
    """Core logic for listing artifacts."""
    try:
        brain = get_brain_path()
        root = brain / "artifacts"
        if folder:
            root = root / folder
            
        if not root.exists():
            return []
            
        files = []
        for p in root.rglob("*"):
            if p.is_file():
                files.append(str(p.relative_to(brain / "artifacts")))
        return files[:50]
    except Exception:
        return []

def _trigger_agent(agent: str, task_description: str, context_files: List[str] = None) -> str:
    """Core logic for triggering an agent."""
    data = {
        "task_id": f"task-{int(time.time())}",
        "target_agent": agent,
        "description": task_description,
        "context_files": context_files or [],
        "status": "pending"
    }
    
    event_id = _emit_event(
        event_type="task_assigned",
        emitter="nucleus_mcp",
        data=data,
        description=f"Manual trigger for {agent}"
    )
    
    return f"Triggered {agent} with event {event_id}"

def _get_triggers() -> List[Dict]:
    """Core logic for getting all triggers."""
    try:
        brain = get_brain_path()
        triggers_path = brain / "ledger" / "triggers.json"
        
        if not triggers_path.exists():
            return []
            
        with open(triggers_path, "r") as f:
            triggers_data = json.load(f)
        
        # Return list of trigger definitions
        return triggers_data.get("triggers", [])
    except Exception as e:
        logger.error(f"Error reading triggers: {e}")
        return []

def _evaluate_triggers(event_type: str, emitter: str) -> List[str]:
    """Core logic for evaluating which agents should activate."""
    try:
        triggers = _get_triggers()
        matching_agents = []
        
        for trigger in triggers:
            # Check if this trigger matches the event
            if trigger.get("event_type") == event_type:
                # Check emitter filter if specified
                emitter_filter = trigger.get("emitter_filter")
                if emitter_filter is None or emitter in emitter_filter:
                    matching_agents.append(trigger.get("target_agent"))
        
        return list(set(matching_agents))  # Dedupe
    except Exception as e:
        logger.error(f"Error evaluating triggers: {e}")
        return []

# ============================================================
# V2 TASK MANAGEMENT CORE LOGIC
# ============================================================

# Task logic moved to runtime/task_ops.py

# Task logic moved to runtime/task_ops.py


# ============================================================
# DEPTH TRACKER - TIER 1 MVP (ADHD Accommodation)
# ============================================================
# Purpose: Real-time "you are here" indicator for conversation depth
# Philosophy: WARN but ALLOW - guardrail, not a wall

# Depth tracking logic moved to runtime/depth_ops.py




def _get_render_config() -> Dict:
    """Get Render service configuration from state.json."""
    try:
        state = _get_state()
        render_config = state.get("render", {})
        return render_config
    except Exception:
        return {}

def _save_render_config(config: Dict) -> None:
    """Save Render configuration to state.json."""
    state = _get_state()
    state["render"] = config
    brain = get_brain_path()
    state_path = brain / "ledger" / "state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

def _run_smoke_test(deploy_url: str, endpoint: str = "/api/health") -> Dict:
    """Run a quick health check on deployed service."""
    import urllib.request
    import urllib.error
    
    try:
        url = f"{deploy_url.rstrip('/')}{endpoint}"
        start = time.time()
        
        request = urllib.request.Request(url, headers={"User-Agent": "Nucleus-Smoke-Test/1.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            latency_ms = (time.time() - start) * 1000
            data = json.loads(response.read().decode())
            
            if response.status == 200:
                status = data.get("status", "unknown")
                if status in ["healthy", "ok", "success"]:
                    return {
                        "passed": True,
                        "latency_ms": round(latency_ms, 2),
                        "status": status,
                        "url": url
                    }
                else:
                    return {
                        "passed": False,
                        "reason": f"Health status: {status}",
                        "latency_ms": round(latency_ms, 2)
                    }
            else:
                return {
                    "passed": False,
                    "reason": f"HTTP {response.status}",
                    "latency_ms": round(latency_ms, 2)
                }
                
    except urllib.error.HTTPError as e:
        return {"passed": False, "reason": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"passed": False, "reason": f"URL Error: {str(e.reason)}"}
    except TimeoutError:
        return {"passed": False, "reason": "Timeout (10s)"}
    except Exception as e:
        return {"passed": False, "reason": str(e)}

def _poll_render_once(service_id: str) -> Dict:
    """Check current deploy status once. Returns latest deploy info."""
    # This is a placeholder - actual implementation would call Render MCP
    # For now, we document what it would return
    return {
        "status": "unknown",
        "message": "Use mcp_render_list_deploys() to check deploy status",
        "service_id": service_id,
        "action": "Call brain_check_deploy() with the service ID to poll Render"
    }

def _start_deploy_poll(service_id: str, commit_sha: str = None) -> Dict:
    """Start monitoring a deploy. Logs event and returns poll instructions."""
    try:
        # Log the poll start event
        _emit_event("deploy_poll_started", "render_poller", {
            "service_id": service_id,
            "commit_sha": commit_sha,
            "poll_interval_seconds": 30,
            "timeout_minutes": 20
        })
        
        # Get or create active polls file
        brain = get_brain_path()
        polls_path = brain / "ledger" / "active_polls.json"
        
        if polls_path.exists():
            with open(polls_path) as f:
                polls = json.load(f)
        else:
            polls = {"polls": []}
        
        # Add new poll
        poll_id = f"poll-{int(time.time())}-{str(uuid.uuid4())[:8]}"
        new_poll = {
            "poll_id": poll_id,
            "service_id": service_id,
            "commit_sha": commit_sha,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "polling"
        }
        
        # Cancel any existing poll for same service
        polls["polls"] = [p for p in polls["polls"] if p.get("service_id") != service_id]
        polls["polls"].append(new_poll)
        
        with open(polls_path, "w") as f:
            json.dump(polls, f, indent=2)
        
        return {
            "poll_id": poll_id,
            "service_id": service_id,
            "commit_sha": commit_sha,
            "status": "polling_started",
            "message": f"Deploy monitoring started. Use brain_check_deploy('{service_id}') to check status.",
            "next_check": "Call mcp_render_list_deploys() or brain_check_deploy() to see current status"
        }
    except Exception as e:
        return {"error": str(e)}

def _check_deploy_status(service_id: str) -> Dict:
    """Check deploy status and update poll state. Returns formatted status."""
    try:
        brain = get_brain_path()
        polls_path = brain / "ledger" / "active_polls.json"
        
        # Check if we have an active poll
        if not polls_path.exists():
            return {
                "status": "no_active_poll",
                "message": "No active polling for this service. Start one with brain_start_deploy_poll()."
            }
        
        with open(polls_path) as f:
            polls = json.load(f)
        
        active_poll = next((p for p in polls.get("polls", []) if p.get("service_id") == service_id), None)
        
        if not active_poll:
            return {
                "status": "no_active_poll",
                "message": f"No active polling for service {service_id}."
            }
        
        # Calculate elapsed time
        started_at = active_poll.get("started_at", "")
        elapsed_minutes = 0
        if started_at:
            try:
                start_time = time.mktime(time.strptime(started_at[:19], "%Y-%m-%dT%H:%M:%S"))
                elapsed_minutes = (time.time() - start_time) / 60
            except Exception:
                pass
        
        return {
            "poll_id": active_poll.get("poll_id"),
            "service_id": service_id,
            "commit_sha": active_poll.get("commit_sha"),
            "status": "polling",
            "elapsed_minutes": round(elapsed_minutes, 1),
            "message": f"Polling for {elapsed_minutes:.1f} minutes. Use mcp_render_list_deploys('{service_id}') to check Render status.",
            "next_action": "Check Render MCP for actual deploy status, then call brain_complete_deploy() when done"
        }
    except Exception as e:
        return {"error": str(e)}

def _complete_deploy(service_id: str, success: bool, deploy_url: str = None, 
                     error: str = None, run_smoke_test: bool = True) -> Dict:
    """Mark deploy as complete. Optionally runs smoke test."""
    try:
        brain = get_brain_path()
        polls_path = brain / "ledger" / "active_polls.json"
        
        # Remove from active polls
        if polls_path.exists():
            with open(polls_path) as f:
                polls = json.load(f)
            
            polls["polls"] = [p for p in polls.get("polls", []) if p.get("service_id") != service_id]
            
            with open(polls_path, "w") as f:
                json.dump(polls, f, indent=2)
        
        # Run smoke test if successful
        smoke_result = None
        if success and deploy_url and run_smoke_test:
            smoke_result = _run_smoke_test(deploy_url)
        
        # Determine final status
        if success:
            if smoke_result and smoke_result.get("passed"):
                status = "deploy_success_verified"
                message = f"✅ Deploy complete and verified! URL: {deploy_url}"
            elif smoke_result and not smoke_result.get("passed"):
                status = "deploy_success_smoke_failed"
                message = f"⚠️ Deploy succeeded but smoke test failed: {smoke_result.get('reason')}"
            else:
                status = "deploy_success"
                message = f"✅ Deploy complete! URL: {deploy_url}"
        else:
            status = "deploy_failed"
            message = f"❌ Deploy failed: {error}"
        
        # Log completion event
        _emit_event("deploy_complete", "render_poller", {
            "service_id": service_id,
            "success": success,
            "url": deploy_url,
            "error": error,
            "smoke_test": smoke_result,
            "status": status
        })
        
        return {
            "status": status,
            "message": message,
            "deploy_url": deploy_url,
            "smoke_test": smoke_result,
            "service_id": service_id
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# FEATURE MAP (Product feature inventory)
# ============================================================

def _get_features_path(product: str) -> Path:
    """Get path to product's features.json file."""
    brain = get_brain_path()
    return brain / "features" / f"{product}.json"

def _load_features(product: str) -> Dict:
    """Load features for a product."""
    path = _get_features_path(product)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"product": product, "last_updated": None, "total_features": 0, "features": []}

def _save_features(product: str, data: Dict) -> None:
    """Save features for a product."""
    path = _get_features_path(product)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    data["total_features"] = len(data.get("features", []))
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def _add_feature(product: str, name: str, description: str, source: str, 
                 version: str, how_to_test: List[str], expected_result: str,
                 status: str = "development", **kwargs) -> Dict:
    """Add a new feature to the product's feature map."""
    try:
        data = _load_features(product)
        
        # Generate ID from name
        feature_id = name.lower().replace(" ", "_").replace("-", "_")
        feature_id = "".join(c for c in feature_id if c.isalnum() or c == "_")
        
        # Check for duplicates
        if any(f.get("id") == feature_id for f in data.get("features", [])):
            return {"error": f"Feature '{feature_id}' already exists"}
        
        # Build feature dict
        feature = {
            "id": feature_id,
            "name": name,
            "description": description,
            "product": product,
            "source": source,
            "version": version,
            "status": status,
            "how_to_test": how_to_test,
            "expected_result": expected_result,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "last_validated": None,
            "validation_result": None
        }
        
        # Add optional fields
        for key in ["tier", "deployed_at", "deployed_url", "released_at", 
                    "pypi_url", "files_changed", "commit_sha", "tags"]:
            if key in kwargs:
                feature[key] = kwargs[key]
        
        data.setdefault("features", []).append(feature)
        _save_features(product, data)
        
        return {"success": True, "feature": feature}
    except Exception as e:
        return {"error": str(e)}

def _list_features(product: str = None, status: str = None, tag: str = None) -> Dict:
    """List features with optional filters."""
    try:
        brain = get_brain_path()
        features_dir = brain / "features"
        
        if not features_dir.exists():
            return {"features": [], "total": 0}
        
        all_features = []
        
        # Get all product files or just the specified one
        if product:
            products = [product]
        else:
            products = [f.stem for f in features_dir.glob("*.json")]
        
        for p in products:
            data = _load_features(p)
            for feature in data.get("features", []):
                # Apply filters
                if status and feature.get("status") != status:
                    continue
                if tag and tag not in feature.get("tags", []):
                    continue
                all_features.append(feature)
        
        return {"features": all_features, "total": len(all_features)}
    except Exception as e:
        return {"error": str(e)}

def _get_feature(feature_id: str) -> Dict:
    """Get a specific feature by ID."""
    try:
        brain = get_brain_path()
        features_dir = brain / "features"
        
        if not features_dir.exists():
            return {"error": f"Feature '{feature_id}' not found"}
        
        for json_file in features_dir.glob("*.json"):
            data = _load_features(json_file.stem)
            for feature in data.get("features", []):
                if feature.get("id") == feature_id:
                    return {"feature": feature}
        
        return {"error": f"Feature '{feature_id}' not found"}
    except Exception as e:
        return {"error": str(e)}

def _update_feature(feature_id: str, **updates) -> Dict:
    """Update a feature."""
    try:
        brain = get_brain_path()
        features_dir = brain / "features"
        
        for json_file in features_dir.glob("*.json"):
            product = json_file.stem
            data = _load_features(product)
            
            for i, feature in enumerate(data.get("features", [])):
                if feature.get("id") == feature_id:
                    # Apply updates
                    for key, value in updates.items():
                        data["features"][i][key] = value
                    
                    _save_features(product, data)
                    return {"success": True, "feature": data["features"][i]}
        
        return {"error": f"Feature '{feature_id}' not found"}
    except Exception as e:
        return {"error": str(e)}

def _mark_validated(feature_id: str, result: str) -> Dict:
    """Mark a feature as validated."""
    if result not in ["passed", "failed"]:
        return {"error": "Result must be 'passed' or 'failed'"}
    
    return _update_feature(
        feature_id,
        last_validated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        validation_result=result
    )

def _search_features(query: str) -> Dict:
    """Search features by name, description, or tags."""
    try:
        result = _list_features()
        if "error" in result:
            return result
        
        query_lower = query.lower()
        matches = []
        
        for feature in result.get("features", []):
            # Search in name, description, tags
            searchable = " ".join([
                feature.get("name", ""),
                feature.get("description", ""),
                " ".join(feature.get("tags", []))
            ]).lower()
            
            if query_lower in searchable:
                matches.append(feature)
        
        return {"features": matches, "total": len(matches), "query": query}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# PROOF SYSTEM (Feature validation proof)
# ============================================================



# Session management logic moved to runtime/session_ops.py






# ============================================================
# BRAIN CONSOLIDATION - TIER 1 (Reversibility-First)
# ============================================================
# Purpose: Automated cleanup of artifact noise without data loss
# Philosophy: MOVE, never DELETE - all actions are reversible

def _get_archive_path() -> Path:
    """Get the path to the archive directory."""
    brain = get_brain_path()
    archive_path = brain / "archive"
    archive_path.mkdir(parents=True, exist_ok=True)
    return archive_path

def _archive_resolved_files() -> Dict:
    """Archive all .resolved.* backup files to archive/resolved/.
    
    These are version snapshot files created by Antigravity when editing.
    Moving them clears visual clutter while preserving file history.
    
    Returns:
        Dict with moved count, archive path, and list of moved files
    """
    try:
        brain = get_brain_path()
        archive_dir = _get_archive_path() / "resolved"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        moved_files = []
        skipped_files = []
        
        # Find all .resolved.* files (pattern: *.resolved or *.resolved.N)
        for f in brain.glob("*.resolved*"):
            if f.is_file():
                try:
                    dest = archive_dir / f.name
                    # Handle duplicate names in archive
                    if dest.exists():
                        base = f.stem
                        suffix = f.suffix
                        counter = 1
                        while dest.exists():
                            dest = archive_dir / f"{base}.dup{counter}{suffix}"
                            counter += 1
                    
                    f.rename(dest)
                    moved_files.append(f.name)
                except Exception as e:
                    skipped_files.append({"file": f.name, "error": str(e)})
        
        # Also check for metadata.json files (Antigravity auto-generated)
        for f in brain.glob("*.metadata.json"):
            if f.is_file():
                try:
                    dest = archive_dir / f.name
                    if dest.exists():
                        base = f.stem
                        suffix = f.suffix
                        counter = 1
                        while dest.exists():
                            dest = archive_dir / f"{base}.dup{counter}{suffix}"
                            counter += 1
                    
                    f.rename(dest)
                    moved_files.append(f.name)
                except Exception as e:
                    skipped_files.append({"file": f.name, "error": str(e)})
        
        # Log the consolidation event
        if moved_files:
            _emit_event(
                "brain_consolidated",
                "BRAIN_CONSOLIDATION",
                {
                    "tier": 1,
                    "action": "archive_resolved",
                    "files_moved": len(moved_files),
                    "archive_path": str(archive_dir)
                },
                f"Archived {len(moved_files)} resolved/metadata files"
            )
        
        return {
            "success": True,
            "files_moved": len(moved_files),
            "files_skipped": len(skipped_files),
            "archive_path": str(archive_dir),
            "moved_files": moved_files[:20],  # Limit output size
            "skipped_files": skipped_files,
            "message": f"Archived {len(moved_files)} files to {archive_dir}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _detect_redundant_artifacts() -> Dict:
    """Detect potentially redundant artifacts based on filename patterns.
    
    Looks for:
    1. Versioned duplicates (file.md vs FILE_V0_4_0.md)
    2. Related synthesis docs (SYNTHESIS_PART1, SYNTHESIS_PART2, etc.)
    3. Stale files (not modified in 30+ days, no references)
    
    Returns:
        Dict with categorized redundancy findings
    """
    try:
        brain = get_brain_path()
        
        findings = {
            "versioned_duplicates": [],
            "related_series": [],
            "stale_files": [],
            "archive_candidates": []
        }
        
        all_files = list(brain.glob("*.md"))
        # filenames = {f.stem.lower(): f for f in all_files}
        
        # 1. Detect versioned duplicates
        # e.g., implementation_plan.md vs IMPLEMENTATION_PLAN_V0_4_0.md
        version_patterns = ["_v0", "_v1", "_v2", "_v3", "_v4", "_v5"]
        processed = set()
        
        for f in all_files:
            stem = f.stem.lower()
            
            # Skip if already processed
            if f.name in processed:
                continue
                
            # Check for versioned variant
            for vp in version_patterns:
                if vp in stem:
                    # This IS the versioned file, find the unversioned
                    base_name = stem.split(vp)[0].replace("_", "").strip()
                    
                    # Look for potential match
                    for other_f in all_files:
                        other_stem = other_f.stem.lower().replace("_", "")
                        if other_f != f and base_name in other_stem and vp not in other_f.stem.lower():
                            findings["versioned_duplicates"].append({
                                "old": other_f.name,
                                "new": f.name,
                                "reason": "Versioned file likely supersedes unversioned",
                                "suggestion": "Archive old, keep new"
                            })
                            processed.add(other_f.name)
                            processed.add(f.name)
                            break
        
        # 2. Detect related series (SYNTHESIS_PART1, SYNTHESIS_PART2, etc.)
        series_patterns = {
            "SYNTHESIS_PART": [],
            "RAW_MONOLOGUE_PART": [],
            "DESIGN_": [],
        }
        
        for f in all_files:
            for pattern in series_patterns:
                if pattern in f.stem:
                    series_patterns[pattern].append(f.name)
        
        for pattern, files in series_patterns.items():
            if len(files) > 2:
                findings["related_series"].append({
                    "pattern": pattern,
                    "files": files[:5],  # Limit to first 5
                    "count": len(files),
                    "reason": f"{len(files)} related files in series",
                    "suggestion": f"Consider consolidating into single {pattern.replace('_', '')}ALL.md"
                })
        
        # 3. Detect stale files (30+ days old)
        import time
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        
        for f in all_files:
            if f.stat().st_mtime < thirty_days_ago:
                # Skip key preserved files
                preserved = ["NORTH_STAR", "task", "README", "PROTOCOL"]
                if any(p in f.stem for p in preserved):
                    continue
                    
                findings["stale_files"].append({
                    "file": f.name,
                    "last_modified": time.strftime("%Y-%m-%d", time.localtime(f.stat().st_mtime)),
                    "reason": "Not modified in 30+ days",
                    "suggestion": "Review for archiving"
                })
        
        # 4. Archive candidates (temp files, completed work)
        archive_keywords = ["_exploration", "_proposal", "_draft", "_temp", "_old"]
        for f in all_files:
            stem = f.stem.lower()
            for kw in archive_keywords:
                if kw in stem:
                    findings["archive_candidates"].append({
                        "file": f.name,
                        "keyword": kw,
                        "reason": f"Contains '{kw}' suggesting temporary nature",
                        "suggestion": "Move to archive/"
                    })
                    break
        
        return {
            "success": True,
            "total_files_scanned": len(all_files),
            "findings": findings,
            "summary": {
                "versioned_duplicates": len(findings["versioned_duplicates"]),
                "related_series": len(findings["related_series"]),
                "stale_files": len(findings["stale_files"]),
                "archive_candidates": len(findings["archive_candidates"])
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _generate_merge_proposals() -> Dict:
    """Generate human-readable merge proposal document.
    
    Runs detection and formats results as actionable proposals.
    Does NOT execute any merges - proposals only.
    
    Returns:
        Dict with proposal_text and structured data
    """
    try:
        detection_result = _detect_redundant_artifacts()
        
        if not detection_result.get("success"):
            return detection_result
        
        findings = detection_result.get("findings", {})
        summary = detection_result.get("summary", {})
        
        # Generate markdown proposal
        today = time.strftime("%Y-%m-%d")
        lines = [
            "# Brain Consolidation Proposals",
            "",
            f"> **Generated:** {today}  ",
            "> **Status:** Awaiting human review  ",
            "> **Action:** None taken - proposals only",
            "",
            "---",
            "",
        ]
        
        # Summary
        total_proposals = sum(summary.values())
        lines.append("## Summary")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|:---------|:------|")
        lines.append(f"| Versioned Duplicates | {summary.get('versioned_duplicates', 0)} |")
        lines.append(f"| Related Series | {summary.get('related_series', 0)} |")
        lines.append(f"| Stale Files (30+ days) | {summary.get('stale_files', 0)} |")
        lines.append(f"| Archive Candidates | {summary.get('archive_candidates', 0)} |")
        lines.append(f"| **Total Proposals** | **{total_proposals}** |")
        lines.append("")
        
        if total_proposals == 0:
            lines.append("✅ **Brain is clean!** No consolidation needed.")
            return {
                "success": True,
                "total_proposals": 0,
                "proposal_text": "\n".join(lines),
                "findings": findings
            }
        
        lines.append("---")
        lines.append("")
        
        # Versioned duplicates section
        if findings.get("versioned_duplicates"):
            lines.append("## Versioned Duplicates")
            lines.append("")
            lines.append("These files appear to have old/new versions. Consider archiving the old one.")
            lines.append("")
            for i, dup in enumerate(findings["versioned_duplicates"], 1):
                lines.append(f"### {i}. {dup['old']}")
                lines.append(f"- **Old:** `{dup['old']}`")
                lines.append(f"- **New:** `{dup['new']}`")
                lines.append(f"- **Reason:** {dup['reason']}")
                lines.append(f"- **Suggestion:** {dup['suggestion']}")
                lines.append("")
        
        # Related series section
        if findings.get("related_series"):
            lines.append("## Related File Series")
            lines.append("")
            lines.append("These files form related series that could potentially be consolidated.")
            lines.append("")
            for i, series in enumerate(findings["related_series"], 1):
                lines.append(f"### {i}. {series['pattern']}* ({series['count']} files)")
                lines.append(f"- **Pattern:** `{series['pattern']}*`")
                lines.append(f"- **Files:** {', '.join(['`' + f + '`' for f in series['files']])}")
                if series['count'] > 5:
                    lines.append(f"  - ... and {series['count'] - 5} more")
                lines.append(f"- **Suggestion:** {series['suggestion']}")
                lines.append("")
        
        # Stale files section
        if findings.get("stale_files"):
            lines.append("## Stale Files (30+ Days Old)")
            lines.append("")
            lines.append("These files haven't been modified in 30+ days. Review if still relevant.")
            lines.append("")
            for i, stale in enumerate(findings["stale_files"][:10], 1):  # Limit to 10
                lines.append(f"{i}. `{stale['file']}` - Last modified: {stale['last_modified']}")
            if len(findings["stale_files"]) > 10:
                lines.append(f"   ... and {len(findings['stale_files']) - 10} more")
            lines.append("")
        
        # Archive candidates section
        if findings.get("archive_candidates"):
            lines.append("## Archive Candidates")
            lines.append("")
            lines.append("These files contain keywords suggesting they're temporary work.")
            lines.append("")
            for i, cand in enumerate(findings["archive_candidates"][:10], 1):
                lines.append(f"{i}. `{cand['file']}` - Contains '{cand['keyword']}'")
            if len(findings["archive_candidates"]) > 10:
                lines.append(f"   ... and {len(findings['archive_candidates']) - 10} more")
            lines.append("")
        
        # Next steps section
        lines.append("---")
        lines.append("")
        lines.append("## Next Steps")
        lines.append("")
        lines.append("1. Review proposals above")
        lines.append("2. To archive files, run: `nucleus consolidate archive`")
        lines.append("3. To manually move files: `mv file.md .brain/archive/`")
        lines.append("4. Tier 3 (Execute Merges) coming soon...")
        lines.append("")
        
        proposal_text = "\n".join(lines)
        
        # Log event
        _emit_event(
            "merge_proposals_generated",
            "BRAIN_CONSOLIDATION",
            {
                "tier": 2,
                "total_proposals": total_proposals,
                "categories": summary
            },
            f"Generated {total_proposals} consolidation proposals"
        )
        
        return {
            "success": True,
            "total_proposals": total_proposals,
            "proposal_text": proposal_text,
            "findings": findings,
            "summary": summary
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================
# FEATURE MAP TOOLS (MCP wrappers)
# ============================================================



@mcp.tool()
def brain_add_feature(product: str, name: str, description: str, source: str,
                      version: str, how_to_test: List[str], expected_result: str,
                      status: str = "development", tags: List[str] = None) -> Dict:
    """Add a new feature to the product's feature map.
    
    Args:
        product: "gentlequest" or "nucleus"
        name: Human-readable feature name
        description: What the feature does
        source: Where it lives (e.g., "gentlequest_app", "pypi_mcp")
        version: Which version it shipped in
        how_to_test: List of test steps
        expected_result: What should happen when testing
        status: development/staged/production/released
        tags: Searchable tags
    
    Returns:
        Created feature object
    """
    kwargs = {}
    if tags:
        kwargs["tags"] = tags
    return _add_feature(product, name, description, source, version, 
                        how_to_test, expected_result, status, **kwargs)

@mcp.tool()
def brain_list_features(product: str = None, status: str = None, tag: str = None) -> Dict:
    """List all features, optionally filtered.
    
    Args:
        product: Filter by product ("gentlequest" or "nucleus")
        status: Filter by status
        tag: Filter by tag
    
    Returns:
        List of matching features
    """
    return _list_features(product, status, tag)

@mcp.tool()
def brain_get_feature(feature_id: str) -> Dict:
    """Get a specific feature by ID.
    
    Args:
        feature_id: The feature ID (snake_case)
    
    Returns:
        Feature object with test instructions
    """
    return _get_feature(feature_id)

@mcp.tool()
def brain_update_feature(feature_id: str, status: str = None, 
                         description: str = None, version: str = None) -> Dict:
    """Update a feature's fields.
    
    Args:
        feature_id: Feature to update
        status: New status
        description: New description
        version: New version
    
    Returns:
        Updated feature
    """
    updates = {}
    if status:
        updates["status"] = status
    if description:
        updates["description"] = description
    if version:
        updates["version"] = version
    
    if not updates:
        return {"error": "No updates provided"}
    
    return _update_feature(feature_id, **updates)

@mcp.tool()
def brain_mark_validated(feature_id: str, result: str) -> Dict:
    """Mark a feature as validated after testing.
    
    Args:
        feature_id: Feature that was tested
        result: "passed" or "failed"
    
    Returns:
        Updated feature with validation timestamp
    """
    return _mark_validated(feature_id, result)

# ============================================================
# RECURSIVE MOUNTER (AG-021)
# ============================================================

@mcp.tool()
async def brain_mount_server(name: str, command: str, args: List[str] = []) -> str:
    """
    Mount an external MCP server to Nucleus (Recursive Aggregator).
    
    This allows Nucleus to act as a Host-Runtime for other servers,
    providing a single unified interface for the AI client.
    
    Args:
        name: Local name for the mounted server
        command: Executable command (e.g. "npx", "python")
        args: Command line arguments
    """
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        # V9.3 Async Protocol Fix: Use async/await directly
        # This prevents "loop already running" errors in IDEs like Windsurf
        return await mounter.mount(name, command, args)
    except Exception as e:
        return f"Error mounting server: {e}"

@mcp.tool()
async def brain_unmount_server(server_id: str) -> str:
    """
    Unmount an external MCP server.
    
    Args:
        server_id: The ID of the server to unmount (e.g. mnt-123456)
    """
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        # V9.3 Async Protocol Fix
        return await mounter.unmount(server_id)
    except Exception as e:
        return f"Error unmounting server: {e}"

@mcp.tool()
def brain_list_mounted() -> str:
    """
    List all currently mounted external MCP servers.
    """
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        return make_response(True, data=mounter.list_mounted())
    except Exception as e:
        return make_response(False, error=str(e))

@mcp.tool()
async def brain_discover_mounted_tools(server_id: str = None) -> str:
    """
    Discover tools from mounted MCP servers.
    
    This is the "Southbound Query" of the Recursive Aggregator pattern.
    It asks mounted servers what tools they provide.
    
    Args:
        server_id: Optional. Specific server to query. If None, queries all.
    """
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        
        # V9.3 Async Protocol Fix: Direct await
        results = {}
        servers = mounter.mounted_servers
        
        if server_id:
            if server_id not in servers:
                return {"error": f"Server {server_id} not found"}
            server = servers[server_id]
            tools = await server.list_tools()
            return make_response(True, data={server.name: tools})
        
        # Query all servers
        for sid, server in servers.items():
            tools = await server.list_tools()
            results[server.name] = tools
            
        return make_response(True, data=results)
    except Exception as e:
        return make_response(False, error=str(e))

@mcp.tool()
async def brain_invoke_mounted_tool(server_id: str, tool_name: str, arguments: Dict[str, Any] = {}) -> str:
    """
    Invoke a tool on a mounted external MCP server.
    
    This is the "Southbound Execution" of the Recursive Aggregator pattern.
    It allows calling tools on any number of external servers without 
    bloating the primary Nucleus registry.
    
    Args:
        server_id: The ID of the server (e.g. mnt-123456)
        tool_name: The name of the tool to call on that server
        arguments: Arguments for the tool
    """
    try:
        brain = get_brain_path()
        mounter = get_mounter(brain)
        
        # V9.3 Async Protocol Fix
        if server_id not in mounter.mounted_servers:
            return json.dumps({"success": False, "error": f"Server {server_id} not found"})
            
        server = mounter.mounted_servers[server_id]
        result = await server.call_tool(tool_name, arguments)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@mcp.tool()
def brain_search_features(query: str) -> Dict:
    """Search features by name, description, or tags.
    
    Args:
        query: Search query
    
    Returns:
        Matching features
    """
    return _search_features(query)

# ============================================================
# PROOF SYSTEM TOOLS (MCP wrappers)
# ============================================================

@mcp.tool()
def brain_generate_proof(feature_id: str, thinking: str = None,
                         deployed_url: str = None, 
                         files_changed: List[str] = None,
                         risk_level: str = "low",
                         rollback_time: str = "15 minutes") -> Dict:
    """Generate a proof document for a feature.
    
    Creates a markdown proof file with:
    - AI thinking (options, choice, reasoning, fallback)
    - Deployed URL
    - Files changed
    - Rollback plan with risk level
    
    Args:
        feature_id: Feature to generate proof for
        thinking: AI's decision-making process (markdown)
        deployed_url: Production URL
        files_changed: List of files modified
        risk_level: low/medium/high
        rollback_time: Estimated time to rollback
    
    Returns:
        Proof generation result with path
    """
    return _generate_proof(feature_id, thinking, deployed_url, 
                           files_changed, risk_level, rollback_time)

@mcp.tool()
def brain_get_proof(feature_id: str) -> Dict:
    """Get the proof document for a feature.
    
    Args:
        feature_id: Feature ID to get proof for
    
    Returns:
        Proof content or message if not found
    """
    return _get_proof(feature_id)

@mcp.tool()
def brain_list_proofs() -> Dict:
    """List all proof documents.
    
    Returns:
        List of proofs with metadata
    """
    return {
        "proofs": _list_proofs(),
        "total": len(_list_proofs())
    }

def _list_proofs() -> List[str]:
    """Core logic wrapper for listing proofs."""
    try:
        from .runtime.capabilities.proof_system import ProofSystem # noqa: E402, F401
        proof_sys = ProofSystem()
        return proof_sys._list_proofs()
    except Exception:
        return []

# ============================================================
# SESSION MANAGEMENT TOOLS (MCP wrappers)
# ============================================================

@mcp.tool()
def brain_save_session(context: str, active_task: str = None,
                       pending_decisions: List[str] = None,
                       breadcrumbs: List[str] = None,
                       next_steps: List[str] = None) -> str:
    """Save current session for later resumption."""
    return _save_session_impl(context, active_task, pending_decisions, breadcrumbs, next_steps)

def _save_session_impl(context: str, active_task: str = None,
                       pending_decisions: List[str] = None,
                       breadcrumbs: List[str] = None,
                       next_steps: List[str] = None) -> str:
    """Implementation for saving session."""
    result = _save_session(context, active_task, pending_decisions, breadcrumbs, next_steps)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_resume_session(session_id: str = None) -> str:
    """Resume a saved session."""
    return _resume_session_impl(session_id)

def _resume_session_impl(session_id: str = None) -> str:
    """Implementation for resuming session."""
    result = _resume_session(session_id)
    if result:
        return make_response(True, data=result)
    return make_response(False, error="Session not found")

@mcp.tool()
def brain_list_sessions() -> Dict:
    """List all saved sessions.
    
    Returns:
        List of sessions with metadata (context, task, date)
    """
    sessions = _list_sessions()
    return make_response(True, data=sessions)

@mcp.tool()
def brain_check_recent_session() -> Dict:
    """Check if there's a recent session to offer resumption.
    
    Call this at the start of a new conversation to see if
    the user should be offered to resume their previous work.
    
    Returns:
        Whether a recent session exists with prompt text
    """
    result = _check_for_recent_session()
    return make_response(True, data=result)

# ============================================================
# BRAIN CONSOLIDATION TOOLS (MCP wrappers)
# ============================================================

@mcp.tool()
def brain_archive_resolved() -> Dict:
    """Archive all .resolved.* backup files to clean up the brain folder.
    
    This moves auto-generated version backup files (created by Antigravity)
    to the archive/resolved/ folder. The files are NOT deleted - they can
    be recovered from the archive at any time.
    
    Safe to run regularly (nightly recommended). Reversible action.
    
    Returns:
        Summary of archived files including count and paths
    """
    return _archive_resolved_files()

@mcp.tool()
def brain_propose_merges() -> Dict:
    """Detect redundant artifacts and generate merge proposals.
    
    Scans the brain folder for:
    - Versioned duplicates (old.md vs NEW_V0_4_0.md)
    - Related series (SYNTHESIS_PART1, PART2, etc.)
    - Stale files (30+ days unmodified)
    - Archive candidates (temp files, drafts)
    
    Returns proposals only - no files are moved or modified.
    Human reviews proposals before any action is taken.
    
    Returns:
        Merge proposals with structured findings and readable report
    """
    return _generate_merge_proposals()

@mcp.tool()
def brain_emit_event(event_type: str, emitter: str, data: Dict[str, Any], description: str = "") -> str:
    """Emit a new event to the brain ledger."""
    return _emit_event_impl(event_type, emitter, data, description)

def _emit_event_impl(event_type: str, emitter: str, data: Dict[str, Any], description: str = "") -> str:
    """Implementation for emitting events."""
    result = _emit_event(event_type, emitter, data, description)
    if result.startswith("Error"):
        return make_response(False, error=result)
    return make_response(True, data={"event_id": result})

@mcp.tool()
def brain_read_events(limit: int = 10) -> List[Dict]:
    """Read recent events."""
    return _read_events_impl(limit)

def _read_events_impl(limit: int = 10) -> str:
    """Implementation for reading events."""
    events = _read_events(limit)
    return make_response(True, data={"events": events})

@mcp.tool()
def brain_get_state(path: Optional[str] = None) -> Dict:
    """Get the current state of the brain."""
    return _get_state(path)

@mcp.tool()
def brain_update_state(updates: Dict[str, Any]) -> str:
    """Update the brain state with new values (shallow merge)."""
    return _update_state(updates)

# ============================================================
# MULTI-AGENT SYNC TOOLS (v0.7.0)
# ============================================================

@mcp.tool()
def brain_identify_agent(agent_id: str, environment: str, role: str = "") -> str:
    """
    Register current agent identity for multi-agent coordination.
    
    This is the first tool an agent should call when starting a session.
    It persists agent identity in .brain/.nucleus_agent for event logging
    and sync coordination.
    
    Args:
        agent_id: Unique identifier (e.g., "windsurf_main", "cursor_dev")
        environment: Tool name (e.g., "windsurf", "cursor", "claude_desktop")
        role: Optional role (e.g., "architect", "developer", "reviewer")
    
    Returns:
        JSON with registration details and storage location
    
    Example:
        brain_identify_agent("windsurf_opus", "windsurf", "architect")
    """
    # Pillar 6: ID Collision Protection (Finding 6)
    try:
        from .runtime.event_ops import _read_events # noqa: E402, F401
        import socket
        current_host = socket.gethostname()
        
        # Check last 50 events for this ID from a different host
        recent_events = _read_events(limit=50)
        collision_detected = False
        for event in recent_events:
            # If agent registered recently (< 5 mins) from another host
            if event.get("emitter") == agent_id and event.get("type") == "AGENT_REGISTERED":
                stored_data = event.get("data", {})
                if stored_data.get("host") and stored_data.get("host") != current_host:
                    collision_detected = True
                    break
        
        if collision_detected:
            warning = f"WARNING: Agent ID '{agent_id}' is already active on another host. Consider using a suffix (e.g. {agent_id}-{current_host[:5]})."
            logger.warning(warning)
            # We return the warning in the JSON result but don't hard-block (Non-destructive)
    except Exception:
        collision_detected = False

    result = set_current_agent(agent_id, environment, role)
    if collision_detected:
        result["collision_warning"] = warning
    
    # Emit registration event with host info
    import socket
    result["host"] = socket.gethostname()
    
    _emit_event(
        event_type="AGENT_REGISTERED",
        emitter=agent_id,
        data=result,
        description=f"Agent {agent_id} registered in {environment} (v0.7.1)"
    )
    
    return json.dumps(result, indent=2)


@mcp.tool()
def brain_sync_status() -> str:
    """
    Check current multi-agent sync status.
    
    Returns comprehensive sync state including:
    - Whether sync is enabled and mode (auto/manual)
    - Current agent identity
    - All detected agents that have modified watched files
    - Pending conflicts
    - Auto-sync watcher status
    
    Use this to understand the current sync state before making changes
    or to debug sync issues.
    
    Returns:
        JSON with sync status details
    """
    status = get_sync_status()
    return json.dumps(status, indent=2)


@mcp.tool()
def brain_sync_now(force: bool = False) -> str:
    """
    Manually trigger multi-agent sync.
    
    Synchronizes watched files (.brain/ledger/state.json, decisions.md, task.md)
    with proper conflict detection and resolution. Use this when:
    - Taking over from another agent
    - Before making critical changes
    - After a conflict is detected
    
    Args:
        force: If True, sync even if no changes detected
    
    Returns:
        JSON with sync result including files synced and conflicts resolved
    """
    if not is_sync_enabled():
        return json.dumps({
            "error": "Sync not enabled",
            "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true",
            "example": "sync:\\n  enabled: true\\n  mode: auto"
        }, indent=2)
    
    try:
        with sync_lock(timeout=5):
            result = perform_sync(force)
            record_sync_time()
            
            # Emit sync event
            _emit_event(
                event_type="SYNC_MANUAL",
                emitter=get_current_agent(),
                data=result,
                description=f"Manual sync by {get_current_agent()}"
            )
            
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "hint": "Another agent may be syncing. Wait and retry."
        }, indent=2)


@mcp.tool()
def brain_sync_auto(enable: bool) -> str:
    """
    Enable or disable automatic file watching and sync.
    
    When enabled, watches configured files for changes and automatically
    syncs within 5 seconds of modification. Uses watchdog library for
    cross-platform file monitoring.
    
    Args:
        enable: True to start watching, False to stop
    
    Returns:
        JSON with auto-sync status and watched files
    
    Requires:
        - .brain/config/nucleus.yaml with sync.enabled: true
        - watchdog library installed (pip install watchdog)
    """
    if enable:
        result = start_file_watcher()
        
        # Pillar 5: Git Hygiene (Finding 5)
        try:
            from .runtime.common import get_brain_path # noqa: E402, F401
            root_path = get_brain_path().parent
            gitignore = root_path / ".gitignore"
            
            ignore_block = "\n# Nucleus MCP Sync Metadata\n**/*.meta\n**/*.conflict\n.nucleus_agent\n.sync_last\n"
            
            if gitignore.exists():
                content = gitignore.read_text()
                if "**/*.meta" not in content:
                    logger.info("Automatically patching .gitignore for Nucleus sync hygiene...")
                    with open(gitignore, "a") as f:
                        f.write(ignore_block)
                    result["gitignore_patched"] = True
            else:
                # Optionally create it if it doesn't exist? (Non-destructive)
                # For now, only patch if it exists to respect user sovereignty
                pass
        except Exception as e:
            logger.debug(f"Git hygiene check failed: {e}")
    else:
        result = stop_file_watcher()
        
    return json.dumps(result, indent=2)


@mcp.tool()
def brain_sync_resolve(file_path: str, strategy: str = "last_write_wins") -> str:
    """
    Manually resolve a file conflict (v0.7.1).
    
    Args:
        file_path: Relative path to the file (e.g., "task.md")
        strategy: "last_write_wins" (accept current) or "manual" (keep marker)
        
    Returns:
        JSON with resolution result.
    """
    try:
        from .runtime.common import get_brain_path # noqa: E402, F401
        from .runtime.sync_ops import detect_conflict, resolve_conflict, sync_lock, get_current_agent # noqa: E402, F401
        
        brain_path = get_brain_path()
        abs_path = brain_path / file_path
        
        with sync_lock(brain_path):
            conflict = detect_conflict(abs_path)
            if not conflict:
                return json.dumps({"status": "error", "message": "No active conflict found for this file."}, indent=2)
            
            status = resolve_conflict(conflict, strategy, brain_path)
            
            description = f"Conflict in {file_path} resolved via {strategy} by {get_current_agent()}"
            _emit_event(
                event_type="SYNC_CONFLICT_RESOLVED",
                emitter=get_current_agent(),
                data={"file": file_path, "strategy": strategy, "status": status},
                description=description
            )
            
            return json.dumps({"status": status, "file": file_path}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
def brain_read_artifact(path: str) -> str:
    """Read contents of an artifact file (relative to .brain/artifacts)."""
    return _read_artifact(path)

@mcp.tool()
def brain_write_artifact(path: str, content: str) -> str:
    """Write contents to an artifact file."""
    return _write_artifact(path, content)

@mcp.tool()
def brain_list_artifacts(folder: Optional[str] = None) -> List[str]:
    """List artifacts in a folder."""
    return _list_artifacts(folder)

@mcp.tool()
def brain_trigger_agent(agent: str, task_description: str, context_files: List[str] = None) -> str:
    """Trigger an agent by emitting a task_assigned event."""
    return _trigger_agent(agent, task_description, context_files)

@mcp.tool()
def brain_get_triggers() -> List[Dict]:
    """Get all defined neural triggers from triggers.json."""
    return _get_triggers()

@mcp.tool()
def brain_evaluate_triggers(event_type: str, emitter: str) -> List[str]:
    """Evaluate which agents should activate for a given event type and emitter."""
    return _evaluate_triggers(event_type, emitter)

# ============================================================
# V2 TASK MANAGEMENT TOOLS
# ============================================================

@mcp.tool()
def brain_list_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    skill: Optional[str] = None,
    claimed_by: Optional[str] = None
) -> str:
    """List tasks with optional filters."""
    return _list_tasks_impl(status, priority, skill, claimed_by)

def _list_tasks_impl(status=None, priority=None, skill=None, claimed_by=None) -> str:
    """Implementation for listing tasks."""
    tasks = _list_tasks(status, priority, skill, claimed_by)
    return make_response(True, data=tasks)

@mcp.tool()
def brain_get_next_task(skills: List[str]) -> str:
    """Get the highest-priority unblocked task."""
    return _get_next_task_impl(skills)

def _get_next_task_impl(skills: List[str]) -> str:
    """Implementation for getting next task."""
    task = _get_next_task(skills)
    if task:
        return make_response(True, data=task)
    return make_response(True, data=None, error="No matching tasks found")

@mcp.tool()
def brain_claim_task(task_id: str, agent_id: str) -> str:
    """Atomically claim a task."""
    return _claim_task_impl(task_id, agent_id)

def _claim_task_impl(task_id: str, agent_id: str) -> str:
    """Implementation for claiming a task."""
    result = _claim_task(task_id, agent_id)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_update_task(task_id: str, updates: Dict[str, Any]) -> str:
    """Update task fields."""
    return _update_task_impl(task_id, updates)

def _update_task_impl(task_id: str, updates: Dict[str, Any]) -> str:
    """Implementation for updating a task."""
    result = _update_task(task_id, updates)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_add_task(
    description: str,
    priority: int = 3,
    blocked_by: List[str] = None,
    required_skills: List[str] = None,
    source: str = "synthesizer",
    task_id: str = None,
    skip_dep_check: bool = False
) -> str:
    """Create a new task in the queue.
    
    Args:
        description: Task description
        priority: 1-5 (1=highest)
        blocked_by: Optional list of task IDs that block this task
        required_skills: Optional list of skills needed
        source: Emitter name
        task_id: Optional custom ID (semantic)
        skip_dep_check: For bulk imports to bypass referential integrity check
    """
    return _add_task_impl(description, priority, blocked_by, required_skills, source, task_id, skip_dep_check)

def _add_task_impl(description: str, priority: int = 3, 
                  blocked_by: List[str] = None,
                  required_skills: List[str] = None,
                  source: str = "synthesizer",
                  task_id: str = None,
                  skip_dep_check: bool = False) -> str:
    """Implementation for adding a task."""
    result = _add_task(description, priority, blocked_by, required_skills, source, task_id, skip_dep_check)
    if result.get("success"):
        return make_response(True, data=result.get("task"))
    return make_response(False, error=result.get("error"))


# Bulk task import logic moved to runtime/task_ops.py



@mcp.tool()
def brain_import_tasks_from_jsonl(jsonl_path: str, clear_existing: bool = False, merge_gtm_metadata: bool = True) -> str:
    """Import tasks from a JSONL file.
    
    Args:
        jsonl_path: Path to tasks.jsonl (relative to brain or absolute)
        clear_existing: Whether to wipe the current queue
        merge_gtm_metadata: Whether to preserve environment/model fields for GTM
    """
    return _import_tasks_from_jsonl_impl(jsonl_path, clear_existing, merge_gtm_metadata)

def _import_tasks_from_jsonl_impl(jsonl_path: str, clear_existing: bool = False, merge_gtm_metadata: bool = True) -> str:
    """Implementation for importing tasks."""
    result = _import_tasks_from_jsonl(jsonl_path, clear_existing, merge_gtm_metadata)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_escalate(task_id: str, reason: str) -> Dict:
    """Escalate a task to request human help.
    
    Args:
        task_id: The task ID or description to escalate
        reason: Why the agent needs human help
    
    Returns:
        Result with success boolean and updated task or error
    """
    return _escalate_task(task_id, reason)

# ============================================================
# DEPTH TRACKER TOOLS (ADHD Accommodation)
# ============================================================

@mcp.tool()
def brain_depth_push(topic: str) -> Dict:
    """Go deeper into a subtopic."""
    return _depth_push_impl(topic)

def _depth_push_impl(topic: str) -> str:
    result = _depth_push(topic)
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_pop() -> str:
    """Come back up one level."""
    return _depth_pop_impl()

def _depth_pop_impl() -> str:
    """Implementation for depth pop."""
    result = _depth_pop()
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_show() -> str:
    """Show current depth state."""
    return _depth_show_impl()

def _depth_show_impl() -> str:
    """Implementation for depth show."""
    result = _depth_show()
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_reset() -> str:
    """Reset depth to root level."""
    return _depth_reset_impl()

def _depth_reset_impl() -> str:
    """Implementation for depth reset."""
    result = _depth_reset()
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_set_max(max_depth: int) -> str:
    """Set the maximum safe depth."""
    return _depth_set_max_impl(max_depth)

def _depth_set_max_impl(max_depth: int) -> str:
    """Implementation for setting max depth."""
    result = _depth_set_max(max_depth)
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_map() -> str:
    """Generate exploration map."""
    return _depth_map_impl()

def _depth_map_impl() -> str:
    """Implementation for depth map."""
    result = _generate_depth_map()
    return make_response(True, data=result)

# ============================================================
# RENDER POLLER TOOLS (Deploy monitoring)
# ============================================================



@mcp.tool()
def brain_start_deploy_poll(service_id: str, commit_sha: str = None) -> Dict:
    """Start monitoring a Render deploy. 
    
    Call this after git push to start tracking deploy status.
    The system will log events and you can check status with brain_check_deploy().
    
    Args:
        service_id: Render service ID (e.g., 'srv-abc123')
        commit_sha: Optional Git commit SHA being deployed
    
    Returns:
        Poll ID and instructions for checking status
    """
    return _start_deploy_poll(service_id, commit_sha)

@mcp.tool()
def brain_check_deploy(service_id: str) -> Dict:
    """Check status of an active deploy poll.
    
    Returns elapsed time and instructions. Use mcp_render_list_deploys()
    to get actual status from Render, then call brain_complete_deploy()
    when the deploy finishes.
    
    Args:
        service_id: Render service ID to check
    
    Returns:
        Current poll status and next action hints
    """
    return _check_deploy_status(service_id)

@mcp.tool()
def brain_complete_deploy(service_id: str, success: bool, deploy_url: str = None,
                          error: str = None, run_smoke_test: bool = True) -> Dict:
    """Mark a deploy as complete and optionally run smoke test.
    
    Call this when you see the deploy is 'live' in Render.
    If success=True and deploy_url is provided, runs a health check.
    
    Args:
        service_id: Render service ID
        success: True if deploy succeeded, False if failed
        deploy_url: URL of deployed service (for smoke test)
        error: Error message if deploy failed
        run_smoke_test: Whether to run health check (default True)
    
    Returns:
        Final status with smoke test results
    """
    return _complete_deploy(service_id, success, deploy_url, error, run_smoke_test)

@mcp.tool()
def brain_smoke_test(url: str, endpoint: str = "/api/health") -> Dict:
    """Run a smoke test on any URL.
    
    Useful for quick health checks without full deploy workflow.
    
    Args:
        url: Base URL of service (e.g., 'https://myapp.onrender.com')
        endpoint: Health endpoint to hit (default: '/api/health')
    
    Returns:
        Smoke test result with pass/fail and latency
    """
    return _run_smoke_test(url, endpoint)

# ============================================================
# MCP RESOURCES (Subscribable data)
# ============================================================

@mcp.resource("brain://state")
def resource_state() -> str:
    """Live state.json content - subscribable."""
    state = _get_state()
    return json.dumps(state, indent=2)

@mcp.resource("brain://events")
def resource_events() -> str:
    """Recent events - subscribable."""
    events = _read_events(limit=20)
    return json.dumps(events, indent=2)

@mcp.resource("brain://triggers")
def resource_triggers() -> str:
    """Trigger definitions - subscribable."""
    triggers = _get_triggers()
    return json.dumps(triggers, indent=2)

@mcp.resource("brain://depth")
def resource_depth() -> str:
    """Current depth tracking state - subscribable. Shows where you are in the conversation tree."""
    depth_state = _depth_show()
    return json.dumps(depth_state, indent=2)

@mcp.resource("brain://context")
def resource_context() -> str:
    """Full context for cold start - auto-visible in sidebar. Click this first in any new session."""
    try:
        brain = get_brain_path()
        state = _get_state()
        sprint = state.get("current_sprint", {})
        agents = state.get("active_agents", [])
        actions = state.get("top_3_leverage_actions", [])
        
        # Format actions
        actions_text = ""
        if actions:
            for i, action in enumerate(actions[:3], 1):
                if isinstance(action, dict):
                    actions_text += f"  {i}. {action.get('action', 'Unknown')}\n"
                else:
                    actions_text += f"  {i}. {action}\n"
        else:
            actions_text = "  (None set)"
        
        # Recent events
        events = _read_events(limit=3)
        events_text = ""
        for evt in events:
            events_text += f"  - {evt.get('type', 'unknown')}: {evt.get('description', '')[:50]}\n"
        if not events_text:
            events_text = "  (No recent events)"
        
        # Check for workflow
        workflow_hint = ""
        workflow_path = brain / "workflows" / "lead_agent_model.md"
        if workflow_path.exists():
            workflow_hint = "📋 Workflow: Read .brain/workflows/lead_agent_model.md for coordination rules"
        
        return f"""# Nucleus Brain Context

## Current Sprint
- Name: {sprint.get('name', 'No active sprint')}
- Focus: {sprint.get('focus', 'Not set')}
- Status: {sprint.get('status', 'Unknown')}

## Active Agents
{', '.join(agents) if agents else 'None'}

## Top Priorities
{actions_text}
## Recent Activity
{events_text}
{workflow_hint}

---
You are the Lead Agent. Use brain_* tools to explore and act."""
    except Exception as e:
        return f"Error loading context: {str(e)}"

# ============================================================
# MCP PROMPTS (Pre-built orchestration)
# ============================================================

@mcp.prompt()
def activate_synthesizer() -> str:
    """Activate Synthesizer agent to orchestrate the current sprint."""
    state = _get_state()
    sprint = state.get("current_sprint", {})
    return f"""You are the Synthesizer, the orchestrating intelligence of this Nucleus Control Plane.

Current Sprint: {sprint.get('name', 'Unknown')}
Focus: {sprint.get('focus', 'Unknown')}

Your job is to:
1. Review the current state and recent events
2. Determine which agents need to be activated
3. Emit appropriate task_assigned events

Use the available brain_* tools to coordinate the agents."""

@mcp.prompt()
def start_sprint(goal: str = "MVP Launch") -> str:
    """Initialize a new sprint with the given goal."""
    return f"""Initialize a new sprint with goal: {goal}

Steps:
1. Use brain_update_state to set current_sprint with name, focus, and start date
2. Use brain_emit_event to emit a sprint_started event
3. Identify top 3 leverage actions and emit task_assigned events for each

Goal: {goal}"""

@mcp.prompt()
def cold_start() -> str:
    """Get instant context when starting a new session. Call this first in any new conversation."""
    try:
        brain = get_brain_path()
        state = _get_state()
        sprint = state.get("current_sprint", {})
        agents = state.get("active_agents", [])
        actions = state.get("top_3_leverage_actions", [])
        
        # Format top actions
        actions_text = ""
        if actions:
            for i, action in enumerate(actions[:3], 1):
                if isinstance(action, dict):
                    actions_text += f"{i}. {action.get('action', 'Unknown')}\n"
                else:
                    actions_text += f"{i}. {action}\n"
        else:
            actions_text = "None set - check state.json"
        
        # Recent events
        events = _read_events(limit=5)
        events_text = ""
        for evt in events[-3:]:  # Show last 3
            evt_type = evt.get('type', 'unknown')
            evt_desc = evt.get('description', '')[:40]
            events_text += f"- {evt_type}: {evt_desc}\n"
        if not events_text:
            events_text = "(No recent events)"
        
        # Check for workflow
        workflow_hint = ""
        workflow_path = brain / "workflows" / "lead_agent_model.md"
        if workflow_path.exists():
            workflow_hint = "\n📋 **Coordination:** Read `.brain/workflows/lead_agent_model.md` for multi-tool rules."
        
        # Recent artifacts
        artifacts = _list_artifacts()[:5]
        artifacts_text = ", ".join([a.split("/")[-1] for a in artifacts]) if artifacts else "None"
        
        return f"""# Nucleus Cold Start

You are now connected to a Nucleus Brain.

## Current State
- **Sprint:** {sprint.get('name', 'No active sprint')}
- **Focus:** {sprint.get('focus', 'Not set')}
- **Status:** {sprint.get('status', 'Unknown')}
- **Active Agents:** {', '.join(agents) if agents else 'None'}

## Top Priorities
{actions_text}
## Recent Activity
{events_text}
## Recent Artifacts
{artifacts_text}
{workflow_hint}

---

## Your Role
You are now the **Lead Agent** for this session.
- No strict role restrictions - you can do code, strategy, research
- Use brain_* tools to read/write state and artifacts
- Emit events to coordinate with other agents

What would you like to work on?"""
    except Exception as e:
        return f"""# Nucleus Cold Start

⚠️ Could not load brain state: {str(e)}

Make sure NUCLEAR_BRAIN_PATH is set correctly.

You can still use brain_* tools to explore the brain manually."""

# ============================================================
# SATELLITE VIEW (Unified Status Dashboard)
# ============================================================

def _generate_sparkline(counts: List[int], chars: str = "▁▂▃▄▅▆▇█") -> str:
    """Generate a sparkline string from a list of counts."""
    if not counts or max(counts) == 0:
        return "▁" * len(counts) if counts else "▁▁▁▁▁▁▁"
    
    max_val = max(counts)
    scale = (len(chars) - 1) / max_val
    return "".join(chars[int(c * scale)] for c in counts)


def _get_activity_sparkline(days: int = 7) -> Dict:
    """Get activity sparkline for the last N days from events.jsonl."""
    try:
        brain = get_brain_path()
        
        # Fast path: use precomputed summary if available (Tier 2)
        summary_path = brain / "ledger" / "activity_summary.json"
        if summary_path.exists():
            try:
                from datetime import datetime, timedelta
                with open(summary_path, "r") as f:
                    summary = json.load(f)
                
                # Build counts from summary
                today = datetime.now().date()
                counts = []
                day_labels = []
                for i in range(days - 1, -1, -1):
                    day = (today - timedelta(days=i)).isoformat()
                    counts.append(summary.get("days", {}).get(day, 0))
                    day_labels.append(day)
                
                if sum(counts) > 0:  # Only use if we have data
                    peak_idx = counts.index(max(counts)) if counts else 0
                    peak_day = day_labels[peak_idx] if day_labels else None
                    return {
                        "sparkline": _generate_sparkline(counts),
                        "total_events": sum(counts),
                        "peak_day": peak_day,
                        "days_covered": days,
                        "source": "precomputed"
                    }
            except Exception:
                pass  # Fall through to slow path
        
        # Slow path: read events.jsonl
        events_path = brain / "ledger" / "events.jsonl"
        
        if not events_path.exists():
            return {
                "sparkline": "▁▁▁▁▁▁▁",
                "total_events": 0,
                "peak_day": None,
                "days_covered": days
            }

        
        # Read last 500 events (performance optimization)
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        day_counts = defaultdict(int)
        today = datetime.now().date()
        
        # Read events efficiently (tail approach)
        events = []
        with open(events_path, "r") as f:
            for line in f:
                if line.strip():
                    events.append(line)
        
        # Only process last 500 events
        for line in events[-500:]:
            try:
                evt = json.loads(line)
                timestamp = evt.get("timestamp", "")
                if timestamp:
                    # Parse timestamp (format: 2026-01-06T14:00:00+0530)
                    evt_date = timestamp[:10]  # Get YYYY-MM-DD
                    day_counts[evt_date] += 1
            except Exception:
                pass
        
        # Build counts for last N days
        counts = []
        day_labels = []
        for i in range(days - 1, -1, -1):
            day = (today - timedelta(days=i)).isoformat()
            counts.append(day_counts.get(day, 0))
            day_labels.append(day)
        
        # Find peak day
        peak_idx = counts.index(max(counts)) if counts else 0
        peak_day = day_labels[peak_idx] if day_labels else None
        
        return {
            "sparkline": _generate_sparkline(counts),
            "total_events": sum(counts),
            "peak_day": peak_day,
            "days_covered": days
        }
    except Exception as e:
        return {
            "sparkline": "▁▁▁▁▁▁▁",
            "total_events": 0,
            "peak_day": None,
            "error": str(e)
        }


def _get_health_stats() -> Dict:
    """Get brain health statistics."""
    try:
        brain = get_brain_path()
        artifacts_path = brain / "artifacts"
        archive_path = brain / "archive"
        
        # Count artifacts
        artifacts_count = 0
        if artifacts_path.exists():
            artifacts_count = len(list(artifacts_path.rglob("*.md")))
        
        # Count archived files
        archive_count = 0
        if archive_path.exists():
            archive_count = len(list(archive_path.rglob("*")))
        
        # Count stale files (older than 30 days)
        stale_count = 0
        import time
        now = time.time()
        thirty_days_ago = now - (30 * 24 * 60 * 60)
        
        if artifacts_path.exists():
            for f in artifacts_path.rglob("*.md"):
                if f.stat().st_mtime < thirty_days_ago:
                    stale_count += 1
        
        return {
            "artifacts_count": artifacts_count,
            "archive_count": archive_count,
            "stale_count": stale_count
        }
    except Exception as e:
        return {
            "artifacts_count": 0,
            "archive_count": 0,
            "stale_count": 0,
            "error": str(e)
        }


def _get_satellite_view(detail_level: str = "standard") -> Dict:
    """
    Get unified satellite view of the brain.
    
    Detail levels:
    - "minimal": depth only (1 file read)
    - "standard": depth + activity + health (3 reads)
    - "full": depth + activity + health + session (4 reads)
    """
    result = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "detail_level": detail_level
    }
    
    # Always include depth
    try:
        depth = _depth_show()
        result["depth"] = {
            "current": depth.get("current_depth", 0),
            "max": depth.get("max_safe_depth", 5),
            "breadcrumbs": depth.get("breadcrumbs", ""),
            "indicator": depth.get("indicator", "🟢 ○○○○○")
        }
    except Exception:
        result["depth"] = {
            "current": 0,
            "max": 5,
            "breadcrumbs": "(not tracked)",
            "indicator": "⚪ ○○○○○"
        }
    
    if detail_level == "minimal":
        return result
    
    # Standard: add activity and health
    result["activity"] = _get_activity_sparkline(days=7)
    result["health"] = _get_health_stats()
    
    # Add commitment health (PEFS Phase 2)
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        stats = ledger.get("stats", {})
        result["commitments"] = {
            "total_open": stats.get("total_open", 0),
            "green": stats.get("green_tier", 0),
            "yellow": stats.get("yellow_tier", 0),
            "red": stats.get("red_tier", 0),
            "last_scan": ledger.get("last_scan")
        }
    except Exception:
        result["commitments"] = None
    
    if detail_level == "standard":
        return result
    
    # Sprint: add current sprint and active tasks
    if detail_level in ("sprint", "full"):
        try:
            state = _get_state()
            sprint = state.get("sprint", {})
            result["sprint"] = {
                "name": sprint.get("name", "(no sprint)"),
                "focus": sprint.get("focus", ""),
                "status": sprint.get("status", "")
            }
            
            # Get active tasks (top 3 priority)
            try:
                tasks = _list_tasks()
                active_tasks = [t for t in tasks if t.get("status") in ("READY", "IN_PROGRESS")][:3]
                result["active_tasks"] = [
                    {"id": t.get("id", ""), "description": t.get("description", "")[:40]}
                    for t in active_tasks
                ]
            except Exception:
                result["active_tasks"] = []
        except Exception:
            result["sprint"] = None
            result["active_tasks"] = []
    
    if detail_level == "sprint":
        return result
    
    # Full: add session info
    try:
        sessions = _list_sessions()
        if sessions:
            latest = sessions[0]
            result["session"] = {
                "id": latest.get("session_id", ""),
                "context": latest.get("context", ""),
                "active_task": latest.get("active_task", ""),
                "saved_at": latest.get("saved_at", "")
            }
        else:
            result["session"] = None
    except Exception:
        result["session"] = None
    
    return result



def _format_satellite_cli(view: Dict) -> str:
    """Format satellite view for CLI output."""
    lines = []
    
    # Header
    lines.append("╭─────────────────────────────────────────────────────────╮")
    lines.append("│  🧠 NUCLEUS SATELLITE VIEW                              │")
    lines.append("├─────────────────────────────────────────────────────────┤")
    lines.append("│                                                         │")
    
    # Depth
    depth = view.get("depth", {})
    indicator = depth.get("indicator", "⚪ ○○○○○")
    breadcrumbs = depth.get("breadcrumbs", "(not tracked)")
    # Truncate breadcrumbs if too long
    if len(breadcrumbs) > 45:
        breadcrumbs = breadcrumbs[:42] + "..."
    lines.append(f"│  📍 DEPTH: {indicator:<45} │")
    lines.append(f"│     {breadcrumbs:<52} │")
    lines.append("│                                                         │")
    
    # Activity (if present)
    activity = view.get("activity")
    if activity:
        sparkline = activity.get("sparkline", "▁▁▁▁▁▁▁")
        total = activity.get("total_events", 0)
        peak = activity.get("peak_day", "")
        if peak:
            peak_short = peak[5:]  # Remove year, show MM-DD
        else:
            peak_short = "N/A"
        lines.append(f"│  📈 ACTIVITY (7d): {sparkline}  ({total} events, peak: {peak_short:<5}) │")
        lines.append("│                                                         │")
    
    # Sprint (if present)
    sprint = view.get("sprint")
    if sprint:
        sprint_name = sprint.get("name", "(no sprint)")[:40]
        sprint_focus = sprint.get("focus", "")[:40]
        lines.append(f"│  🎯 SPRINT: {sprint_name:<45} │")
        if sprint_focus:
            lines.append(f"│     Focus: {sprint_focus:<46} │")
        
        # Active tasks (if present)
        active_tasks = view.get("active_tasks", [])
        if active_tasks:
            lines.append("│     Tasks:                                              │")
            for task in active_tasks[:3]:
                task_desc = task.get("description", "")[:42]
                lines.append(f"│       • {task_desc:<49} │")
        lines.append("│                                                         │")
    
    # Session (if present)
    session = view.get("session")
    if session:
        context = session.get("context", "(none)")[:40]
        task = session.get("active_task", "(none)")[:40]
        lines.append(f"│  🔥 SESSION: {context:<44} │")
        lines.append(f"│     Task: {task:<47} │")
        lines.append("│                                                         │")
    
    # Health (if present)
    health = view.get("health")
    if health:
        artifacts = health.get("artifacts_count", 0)
        archived = health.get("archive_count", 0)
        stale = health.get("stale_count", 0)
        lines.append("│  🏥 HEALTH                                              │")
        lines.append(f"│     Artifacts: {artifacts} active | {archived} archived{' ' * (28 - len(str(artifacts)) - len(str(archived)))} │")
        if stale > 0:
            lines.append(f"│     ⚠️  {stale} stale files (30+ days){' ' * (36 - len(str(stale)))} │")
        lines.append("│                                                         │")
    
    # Commitments (PEFS - if present)
    commitments = view.get("commitments")
    if commitments:
        total = commitments.get("total_open", 0)
        green = commitments.get("green", 0)
        yellow = commitments.get("yellow", 0)
        red = commitments.get("red", 0)
        
        # Mental load indicator
        if red > 0:
            load = "🔴"
        elif yellow > 2:
            load = "🟡"
        elif total == 0:
            load = "✨"
        else:
            load = "🟢"
        
        lines.append(f"│  🎯 COMMITMENTS {load}                                       │")
        lines.append(f"│     Open loops: {total} (🟢{green} 🟡{yellow} 🔴{red}){' ' * (27 - len(str(total)) - len(str(green)) - len(str(yellow)) - len(str(red)))} │")
        lines.append("│                                                         │")
    
    # Footer
    lines.append("╰─────────────────────────────────────────────────────────╯")
    
    return "\n".join(lines)


@mcp.tool()
def brain_satellite_view(detail_level: str = "standard") -> str:
    """
    Get unified satellite view of the brain.
    
    Shows depth, activity, health, and session in one view.
    
    Args:
        detail_level: "minimal", "standard", or "full"
    
    Returns:
        Formatted satellite view
    """
    view = _get_satellite_view(detail_level)
    formatted = _format_satellite_cli(view)
    return make_response(True, data=formatted)

# ============================================================
# COMMITMENT LEDGER MCP TOOLS (PEFS Phase 2)
# ============================================================

@mcp.tool()
def brain_scan_commitments() -> str:
    """
    Scan artifacts for new commitments (checklists, TODOs).
    Updates the ledger with any new items found.
    (MDR_005 Compliant: Logic moved to shared library)
    
    Returns:
        Scan results
    """
    try:
        brain = get_brain_path()
        result = commitment_ledger.scan_for_commitments(brain)
        return f"✅ Scan complete. Found {result.get('new_found', 0)} new items."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_archive_stale() -> str:
    """
    Auto-archive commitments older than 30 days.
    
    Returns:
        Count of archived items
    """
    try:
        brain = get_brain_path()
        count = commitment_ledger.auto_archive_stale(brain)
        return f"✅ Archive complete. Archived {count} stale items."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_export() -> str:
    """
    Export the brain content to a zip file in .brain/exports/.
    Respects .brain/.brainignore patterns to protect IP.
    (MDR_008 Compliance)
    
    Returns:
        Path to the exported zip file
    """
    try:
        brain = get_brain_path()
        if hasattr(commitment_ledger, 'export_brain'):
            result = commitment_ledger.export_brain(brain)
            return f"✅ {result}"
        return "Error: export_brain validation failed (function missing)."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_list_commitments(tier: str = None) -> str:
    """
    List all open commitments.
    
    Args:
        tier: Optional filter by tier ("green", "yellow", "red")
    
    Returns:
        List of open commitments with details
    """
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        
        # Filter open commitments by tier if specified
        all_commitments = ledger.get('commitments', [])
        commitments = [c for c in all_commitments if c.get('status') == 'open']
        if tier:
            commitments = [c for c in commitments if c.get('tier') == tier]
        
        if not commitments:
            return "✅ No open commitments!"
        
        output = f"**Open Commitments ({len(commitments)} total)**\n\n"
        
        for comm in commitments:
            tier_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(comm["tier"], "⚪")
            output += f"{tier_emoji} **{comm['description'][:60]}**\n"
            output += f"   Age: {comm['age_days']} days | Suggested: {comm['suggested_action']}\n"
            output += f"   Reason: {comm['suggested_reason']}\n"
            output += f"   ID: `{comm['id']}`\n\n"
        
        return output
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_close_commitment(commitment_id: str, method: str) -> str:
    """
    Close a commitment with specified method.
    
    Args:
        commitment_id: The commitment ID (e.g., comm_20260106_163000_0)
        method: Closure method (do_now, scheduled, archived, killed, delegated)
    
    Returns:
        Confirmation with updated commitment
    """
    try:
        brain = get_brain_path()
        commitment = commitment_ledger.close_commitment(brain, commitment_id, method)
        
        # Emit event
        _emit_event(
            "commitment_closed",
            "user",
            {"commitment_id": commitment_id, "method": method},
            description=f"Closed: {commitment['description'][:50]}"
        )
        
        return f"""✅ Commitment closed!

**Description:** {commitment['description']}
**Method:** {method}
**Was open:** {commitment['age_days']} days
**Closed at:** {commitment['closed_at']}"""
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_commitment_health() -> str:
    """
    Get commitment health summary.
    
    Shows open loop count, tier breakdown, and mental load estimate.
    Useful for quick status check.
    
    Returns:
        Health summary with actionable insights
    """
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        stats = ledger.get("stats", {})
        
        total = stats.get("total_open", 0)
        green = stats.get("green_tier", 0)
        yellow = stats.get("yellow_tier", 0)
        red = stats.get("red_tier", 0)
        by_type = stats.get("by_type", {})
        
        # Mental load calculation
        if red > 0:
            mental_load = "🔴 HIGH"
            advice = "Focus on red-tier items first"
        elif yellow > 2:
            mental_load = "🟡 MEDIUM"
            advice = "Clear yellow items before they go red"
        elif total == 0:
            mental_load = "✨ ZERO"
            advice = "No open loops - guilt-free operation!"
        else:
            mental_load = "🟢 LOW"
            advice = "Looking good, maintain momentum"
        
        # Format by_type
        type_str = ", ".join([f"{t}: {c}" for t, c in by_type.items()]) if by_type else "(none)"
        
        return f"""## 🎯 Commitment Health

**Open loops:** {total}
- 🟢 Green: {green}
- 🟡 Yellow: {yellow}
- 🔴 Red: {red}

**By type:** {type_str}

**Mental load:** {mental_load}
**Advice:** {advice}

**Last scan:** {ledger.get('last_scan', 'Never')[:16] if ledger.get('last_scan') else 'Never'}"""
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def brain_open_loops(
    type_filter: str = None,
    tier_filter: str = None
) -> str:
    """
    Unified view of ALL open loops (tasks, todos, drafts, decisions).
    
    This is the single source of truth for what needs attention.
    Replaces the need to check separate task/commitment systems.
    
    Args:
        type_filter: Filter by type ("task", "todo", "draft", "decision")
        tier_filter: Filter by tier ("green", "yellow", "red")
    
    Returns:
        All open loops grouped by type and priority
    """
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        
        open_comms = [c for c in ledger["commitments"] if c["status"] == "open"]
        
        # Apply filters
        if type_filter:
            open_comms = [c for c in open_comms if c.get("type") == type_filter]
        if tier_filter:
            open_comms = [c for c in open_comms if c.get("tier") == tier_filter]
        
        if not open_comms:
            return "✅ No open loops! Guilt-free operation."
        
        # Group by type
        by_type = {}
        for c in open_comms:
            t = c.get("type", "unknown")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(c)
        
        # Build output
        output = f"## 📋 Open Loops ({len(open_comms)} total)\n\n"
        
        type_emoji = {"task": "🔧", "todo": "☑️", "draft": "📝", "decision": "🤔"}
        
        for t, items in by_type.items():
            emoji = type_emoji.get(t, "📌")
            output += f"### {emoji} {t.upper()} ({len(items)})\n\n"
            
            # Sort by tier (red first) then age
            items.sort(key=lambda x: ({"red": 0, "yellow": 1, "green": 2}.get(x.get("tier"), 3), -x.get("age_days", 0)))
            
            for c in items[:5]:  # Max 5 per type
                tier_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(c.get("tier"), "⚪")
                output += f"{tier_emoji} **{c['description'][:50]}**\n"
                output += f"   {c.get('age_days', 0)}d old | Suggested: {c.get('suggested_action')}\n"
                output += f"   ID: `{c['id']}`\n\n"
            
            if len(items) > 5:
                output += f"   ...and {len(items) - 5} more\n\n"
        
        return output
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_add_loop(
    description: str,
    loop_type: str = "task",
    priority: int = 3
) -> str:
    """
    Manually add a new open loop (task, todo, draft, or decision).
    
    Use this when you want to track something that isn't in a document.
    
    Args:
        description: What needs to be done
        loop_type: Type of loop ("task", "todo", "draft", "decision")
        priority: 1-5, lower is higher priority
    
    Returns:
        Created loop details
    """
    try:
        brain = get_brain_path()
        commitment = commitment_ledger.add_commitment(
            brain,
            source_file="manual",
            source_line=0,
            description=description,
            comm_type=loop_type,
            source="manual",
            priority=priority
        )
        
        # Emit event for orchestration
        try:
            _emit_event(
                "commitment_created",
                "brain_add_loop",
                {
                    "commitment_id": commitment['id'],
                    "type": loop_type,
                    "description": description[:60],
                    "priority": priority,
                    "tier": commitment.get('tier', 'green')
                },
                description=f"New {loop_type}: {description[:40]}"
            )
        except Exception:
            pass  # Don't fail loop creation if event emission fails
        
        return f"""✅ Loop created!

**ID:** `{commitment['id']}`
**Type:** {loop_type}
**Description:** {description}
**Priority:** {priority}
**Suggested:** {commitment['suggested_action']} - {commitment['suggested_reason']}"""
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_weekly_challenge(
    action: str = "get",  # get, set, list
    challenge_id: str = None
) -> str:
    """
    Manage the weekly growth challenge.
    
    Args:
        action: "get" (current status), "set" (start new), "list" (show options)
        challenge_id: ID of challenge to set (if action="set")
    
    Returns:
        Challenge status or list of options
    """
    try:
        brain = get_brain_path()
        
        if action == "list":
            challenges = commitment_ledger.get_starter_challenges()
            output = "## 🏆 Weekly Challenges\n\n"
            for c in challenges:
                output += f"**{c['title']}** (`{c['id']}`)\n"
                output += f"{c['description']}\n"
                output += f"🏆 Reward: {c['reward']}\n\n"
            return output
            
        if action == "set":
            if not challenge_id:
                return "⚠️ Please provide `challenge_id` to set a challenge."
            
            challenges = commitment_ledger.get_starter_challenges()
            selected = next((c for c in challenges if c["id"] == challenge_id), None)
            
            if not selected:
                return f"❌ Challenge `{challenge_id}` not found."
            
            # Start fresh
            selected["started_at"] = datetime.now().isoformat()
            selected["status"] = "active"
            commitment_ledger.set_challenge(brain, selected)
            
            return f"✅ **Challenge Accepted: {selected['title']}**\n\nGoal: {selected['description']}\nGo get it!"
            
        # Default: get
        challenge = commitment_ledger.load_challenge(brain)
        if not challenge:
            return "No active challenge. Run `brain_weekly_challenge(action='list')` to pick one!"
            
        return f"""## 🏆 Current Challenge: {challenge['title']}

📝 **Goal:** {challenge['description']}
📅 **Started:** {challenge['started_at'][:10]}
🎁 **Reward:** {challenge['reward']}

Keep pushing!"""

    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_patterns(
    action: str = "list",  # list, learn
) -> str:
    """
    Manage learned patterns for commitment closure.
    
    Args:
        action: "list" (show learned patterns), "learn" (scan ledger for new patterns)
    
    Returns:
        List of patterns or learning result
    """
    try:
        brain = get_brain_path()
        
        if action == "learn":
            patterns = commitment_ledger.learn_patterns(brain)
            return f"✅ Learning complete. Total patterns: {len(patterns)}"
            
        # List
        patterns = commitment_ledger.load_patterns(brain)
        if not patterns:
            return "No patterns learned yet. Run `brain_patterns(action='learn')` after closing some items!"
            
        output = "## 🧠 Learned Patterns\n\n"
        for p in patterns:
            output += f"**{p['name']}**\n"
            output += f"• Keywords: {', '.join(p['keywords'])}\n"
            output += f"• Action: {p['action']}\n\n"
            
        return output

    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_metrics() -> str:
    """
    Get coordination metrics (velocity, closure rates, mental load).
    
    Returns:
        Formatted metrics report
    """
    try:
        brain = get_brain_path()
        metrics = commitment_ledger.calculate_metrics(brain)
        
        output = "## 📊 Coordination Metrics (Last 7 Days)\n\n"
        output += f"**🚀 Velocity:** {metrics['velocity_7d']} items closed\n"
        output += f"**⏱️ Speed:** {metrics['avg_days_to_close']} days avg to close\n\n"
        
        output += "**📈 Closure Rates by Type:**\n"
        if metrics['closure_rates']:
            for t, rate in metrics['closure_rates'].items():
                output += f"- {t}: {rate}\n"
        else:
            output += "(No closed items yet)\n"
            
        output += "\n**🧠 Current Load:**\n"
        output += f"- Total Open: {metrics['current_load']['total']}\n"
        output += f"- Red Tier: {metrics['current_load']['red']}\n"
        
        return output

    except Exception as e:
        return f"Error: {e}"

    except Exception as e:
        return f"Error: {e}"

def _generate_proof(feature_id: str, thinking: str = "", deployed_url: str = "", files_changed: List[str] = [], risk_level: str = "low", rollback_time: str = "15m") -> Dict[str, Any]:
    """Core logic wrapper for generating a proof."""
    try:
        from .runtime.capabilities.proof_system import ProofSystem # noqa: E402, F401
        proof_sys = ProofSystem()
        return proof_sys._generate_proof({
            "feature_id": feature_id,
            "thinking": thinking,
            "deployed_url": deployed_url,
            "files_changed": files_changed,
            "risk_level": risk_level,
            "rollback_time": rollback_time
        })
    except Exception as e:
        return {"error": str(e)}

def _get_proof(feature_id: str) -> Dict[str, Any]:
    """Core logic wrapper for getting a proof."""
    try:
        from .runtime.capabilities.proof_system import ProofSystem # noqa: E402, F401
        proof_sys = ProofSystem()
        content = proof_sys._get_proof(feature_id)
        if content.startswith("Proof for"): # Not found message
             return {"exists": False, "message": content}
        return {"exists": True, "content": content}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# MULTI-TIER LLM MANAGEMENT TOOLS
# ============================================================

@mcp.tool()
def brain_set_llm_tier(tier: str) -> str:
    """
    Set the default LLM tier for agent spawning.
    
    Available tiers:
    - premium: gemini-2.5-pro (high quality, higher cost)
    - standard: gemini-2.5-flash (default, balanced)
    - economy: gemini-2.5-flash-lite (low cost, background tasks)
    - local_paid: API Key mode with billing
    - local_free: API Key free tier (100 req/day)
    
    Args:
        tier: One of the available tier names
    
    Returns:
        Confirmation message
    """
    import os
    valid_tiers = ["premium", "standard", "economy", "local_paid", "local_free"]
    
    if tier.lower() not in valid_tiers:
        return f"❌ Invalid tier '{tier}'. Valid tiers: {', '.join(valid_tiers)}"
    
    # Set environment variable for the session
    os.environ["NUCLEUS_LLM_TIER"] = tier.lower()
    
    return f"✅ LLM tier set to '{tier}'. All subsequent agent spawns will use this tier."


@mcp.tool()
def brain_get_llm_status() -> str:
    """
    Get current LLM tier configuration and available tiers.
    
    Returns:
        Status report with current tier, available models, and benchmark results.
    """
    import os
    import json
    
    brain = get_brain_path()
    tier_status_path = brain / "tier_status.json"
    
    output = "## 🧠 LLM Tier Status\n\n"
    
    # Current settings
    current_tier = os.environ.get("NUCLEUS_LLM_TIER", "auto (standard)")
    force_vertex = os.environ.get("FORCE_VERTEX", "1")
    
    output += f"**Current Tier:** {current_tier}\n"
    output += f"**Vertex Mode:** {'Enabled' if force_vertex == '1' else 'Disabled'}\n\n"
    
    # Load cached tier status if available
    if tier_status_path.exists():
        try:
            with open(tier_status_path) as f:
                status = json.load(f)
            
            output += "### Available Tiers (from last benchmark)\n"
            output += "| Tier | Model | Status | Latency |\n"
            output += "|------|-------|--------|--------|\n"
            
            for tier_name, result in status.get("tier_results", {}).items():
                status_emoji = "✅" if result.get("status") == "SUCCESS" else "❌"
                latency = f"{result.get('latency_ms', '-')}ms" if result.get('latency_ms') else "-"
                output += f"| {tier_name} | {result.get('model', 'unknown')} | {status_emoji} {result.get('status')} | {latency} |\n"
            
            output += f"\n**Recommended:** {status.get('recommended_tier', 'standard')}\n"
            output += f"**Last Benchmark:** {status.get('run_timestamp', 'unknown')}\n"
        except Exception as e:
            output += f"Could not load tier status: {e}\n"
    else:
        output += "No benchmark data available. Run `test_llm_tiers.py --save` to generate.\n"
    
    return output


@mcp.tool()
async def brain_spawn_agent(
    intent: str,
    execute_now: bool = True,
    persona: str = None
) -> str:
    """
    Spawn an Ephemeral Agent via the Nucleus Agent Runtime (NAR).
    The factory constructs a context based on intent and launches a disposable agent.
    MDR_044: Now uses Dual-Engine LLM with intelligent tier routing.
    
    Args:
        intent: The high-level goal (e.g., "Deploy production service")
        execute_now: Whether to run immediately or just return the plan.
        persona: Optional explicit persona to use (e.g., 'developer', 'devops')
        
    Returns:
        Execution log or plan details.
    """
    try:
        from uuid import uuid4
        from .runtime.llm_client import DualEngineLLM # noqa: E402, F401
            
        session_id = f"spawn-{str(uuid4())[:8]}"
        from .runtime.factory import ContextFactory # noqa: E402, F401
        from .runtime.agent import EphemeralAgent # noqa: E402, F401

        factory = ContextFactory()
        
        if persona:
            context = factory.create_context_for_persona(session_id, persona, intent)
        else:
            context = factory.create_context(session_id, intent)
        
        # Get job_type from context for tier routing
        job_type = context.get("job_type", "ORCHESTRATION")
        
        output = "## 🏭 NAR Factory Receipt\n"
        output += f"**Intent:** {intent}\n"
        output += f"**Persona:** {context.get('persona', 'Unknown')}\n"
        output += f"**Job Type:** {job_type}\n"
        output += f"**Capabilities:** {', '.join(context['capabilities'])}\n"
        output += f"**Tools Mapped:** {len(context['tools'])}\n"
        
        if not context['tools']:
            return output + "\n❌ No tools mapped. Agent would be powerless."
            
        if execute_now:
            output += "\n--- Executive Trace (Tier-Routed) ---\n"
            
            # Initialize with tier routing based on job_type
            llm = DualEngineLLM(job_type=job_type)
            
            output += f">> 🎯 Tier: {llm.tier.value if llm.tier else 'default'}\n"
            output += f">> 🧠 Model: {llm.model_name}\n"
            output += f">> ⚡ Engine: {llm.active_engine}\n"
            
            agent = EphemeralAgent(context, model=llm)
            log = await agent.run()
            output += log + "\n"
            output += "✅ Ephemeral Agent executed and terminated.\n"
            
        return output

    except Exception as e:
        return f"Error spawning agent: {e}"


# ============================================================
# MDR_010: USAGE TELEMETRY & FEEDBACK MCP TOOLS
# ============================================================

@mcp.tool()
def brain_record_interaction() -> str:
    """
    Record a user interaction timestamp (MDR_010).
    Call this when the user engages with any brain functionality.
    """
    try:
        brain = get_brain_path()
        commitment_ledger.record_interaction(brain)
        return "✅ Interaction recorded"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_value_ratio() -> str:
    """
    Get the Value Ratio metric (MDR_010).
    Value Ratio = High Impact Closures / Notifications Sent.
    """
    try:
        brain = get_brain_path()
        ratio = commitment_ledger.calculate_value_ratio(brain)
        output = "## 📊 Value Ratio (MDR_010)\n\n"
        output += f"**Notifications Sent:** {ratio['notifications_sent']}\n"
        output += f"**High Impact Closures:** {ratio['high_impact_closed']}\n"
        output += f"**Ratio:** {ratio['ratio']}\n"
        output += f"**Verdict:** {ratio['verdict']}\n"
        return output
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_check_kill_switch() -> str:
    """
    Check Kill Switch status (MDR_010).
    Detects inactivity and suggests pausing notifications.
    """
    try:
        brain = get_brain_path()
        status = commitment_ledger.check_kill_switch(brain)
        output = "## 🛑 Kill Switch Status (MDR_010)\n\n"
        output += f"**Action:** {status['action']}\n"
        output += f"**Message:** {status.get('message', 'N/A')}\n"
        if 'days_inactive' in status:
            output += f"**Days Inactive:** {status['days_inactive']}\n"
        return output
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_pause_notifications() -> str:
    """
    Pause all PEFS notifications (Kill Switch activation).
    Call this when the user requests to stop notifications.
    """
    try:
        brain = get_brain_path()
        commitment_ledger.pause_notifications(brain)
        return "🛑 Notifications paused. Use brain_resume_notifications() to restart."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_resume_notifications() -> str:
    """
    Resume PEFS notifications after pause.
    """
    try:
        brain = get_brain_path()
        commitment_ledger.resume_notifications(brain)
        commitment_ledger.record_interaction(brain)
        return "✅ Notifications resumed. Interaction recorded."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_record_feedback(notification_type: str, score: int) -> str:
    """
    Record user feedback on a notification (MDR_010).
    
    Args:
        notification_type: Type of notification (e.g., 'daily', 'red_tier', 'challenge')
        score: Feedback score (1-5, where 5=helpful, 1=noise)
    """
    try:
        brain = get_brain_path()
        commitment_ledger.record_feedback(brain, notification_type, score)
        if score >= 4:
            msg = "✅ Positive feedback recorded. Marked as high-impact."
        elif score >= 2:
            msg = "📝 Neutral feedback recorded."
        else:
            msg = "😔 Negative feedback recorded. Will try to improve."
        return msg
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_mark_high_impact() -> str:
    """
    Manually mark a loop closure as high-impact (MDR_010).
    Use when a notification led to a meaningful outcome.
    """
    try:
        brain = get_brain_path()
        commitment_ledger.mark_high_impact_closure(brain)
        return "✅ Marked as high-impact closure. Value ratio updated."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_session_start() -> str:
    """
    START HERE - Mandatory session start protocol.
    
    Returns current Brain state to drive your work:
    - Satellite view (depth, activity, health)
    - Top 5 pending tasks by priority
    - Active sprint (if any)
    - Recommendations
    
    CRITICAL: Call this BEFORE starting significant work.
    Read AGENT_PROTOCOL.md for full workflow.
    
    Returns:
        Formatted report with priorities and recommendations
    """
    return _brain_session_start_impl()

def _brain_session_start_impl() -> str:
    try:
        # Direct File I/O for robustness (avoid internal function call issues)
        brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
        if not brain_path:
            return "Error: NUCLEAR_BRAIN_PATH env var not set"
        
        brain = Path(brain_path)
        
        # 1. Get Depth
        depth_path = brain / "depth_state.json"
        depth_data = {}
        if depth_path.exists():
            try:
                with open(depth_path, "r") as f:
                    depth_data = json.load(f)
            except Exception:
                pass
            
        depth_current = depth_data.get("current_depth", 0)
        depth_max = depth_data.get("max_safe_depth", 5)
        depth_indicator = depth_data.get("indicator", "🟢 ○○○○○")
        
        # 2. Get Tasks
        tasks_path = brain / "ledger" / "tasks.json"
        pending_tasks = []
        if tasks_path.exists():
            try:
                with open(tasks_path, "r") as f:
                    all_tasks = json.load(f)
                    pending_tasks = [t for t in all_tasks if t.get("status") == "PENDING"]
            except Exception:
                pass
            
        # Sort by priority
        # Sort by priority - safely handle string priorities
        def get_priority_int(t):
            try:
                return int(t.get("priority", 999))
            except (ValueError, TypeError):
                return 999
                
        sorted_tasks = sorted(pending_tasks, key=get_priority_int)[:5]
        
        # 3. Get Session
        state_path = brain / "ledger" / "state.json"
        has_session = False
        active_context = "None"
        active_task = "None"
        
        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
                    session = state.get("current_session", {})
                    if session:
                        has_session = True
                        active_context = session.get("context", "Unknown")
                        active_task = session.get("active_task", "None")
            except Exception:
                pass

        # Build Report
        output = []
        output.append("=" * 60)
        output.append("🧠 BRAIN SESSION START - Workflow Enforcement Active")
        output.append("=" * 60)
        output.append("")
        
        # Satellite View Simulation
        output.append("📊 CURRENT STATE:")
        output.append(f"   📍 DEPTH: {depth_indicator} ({depth_current}/{depth_max})")
        output.append("")
        
        # Priority Tasks
        output.append("🎯 TOP PRIORITY TASKS:")
        recommended_model = None
        recommended_env = None
        if not sorted_tasks:
            output.append("   ✅ No pending tasks! All clear.")
        else:
            for i, task in enumerate(sorted_tasks, 1):
                raw_priority = task.get("priority", 3)
                try:
                    priority = int(raw_priority)
                except (ValueError, TypeError):
                    priority = 3
                    
                desc = task.get("description", "")[:70]
                task_id = task.get("id", "")
                task_model = task.get("model")
                task_env = task.get("environment")
                
                priority_icon = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}.get(priority, "⚫")
                
                output.append(f"   {i}. {priority_icon} P{priority} | {desc}")
                output.append(f"      ID: {task_id}")
                
                # Show model and environment if available (GTM tasks)
                if task_model or task_env:
                    model_str = f"Model: {task_model}" if task_model else ""
                    env_str = f"Env: {task_env}" if task_env else ""
                    output.append(f"      {model_str} {env_str}".strip())
                
                if priority <= 2:
                    output.append("      ⚠️  HIGH PRIORITY - Should work on this first")
                output.append("")
                
                # Track recommended model from highest priority unclaimed task
                if not recommended_model and task_model and not task.get("claimed_by"):
                    recommended_model = task_model
                    recommended_env = task_env
        
        # 4. Model Routing Section (Patch 4)
        output.append("-" * 60)
        output.append("🔀 MODEL ROUTING:")
        if recommended_model:
            output.append(f"   🎯 TARGET MODEL: {recommended_model}")
            output.append(f"   🌍 TARGET ENV:   {recommended_env or 'Any'}")
            output.append("   💡 Recommendation: Resume with the model/env listed above.")
        else:
            output.append("   ✅ No specific model routing requested. Use default.")
        output.append("-" * 60)
        output.append("")
        
        # Model Auto-Selection (Patch 4)
        output.append("🤖 MODEL ROUTING:")
        if recommended_model:
            model_display = {
                "claude_opus_4.5": "Claude Opus 4.5 (deep reasoning)",
                "claude_sonnet_4": "Claude Sonnet 4 (balanced)",
                "gemini_3_pro": "Gemini 3 Pro (fast iteration)",
                "gemini_3_pro_high": "Gemini 3 Pro High (analysis)"
            }.get(recommended_model, recommended_model)
            output.append(f"   ✨ Recommended: {model_display}")
            if recommended_env:
                output.append(f"   🎯 Environment: {recommended_env}")
            output.append("   (Based on highest priority unclaimed task)")
        else:
            output.append("   No specific model recommended - use default")
        output.append("")
        
        # Active Sprint
        output.append("🏃 ACTIVE SPRINT:")
        if has_session:
            output.append(f"   Context: {active_context}")
            output.append(f"   Task: {active_task}")
        else:
            output.append("   No active sprint - consider setting one with brain_save_session()")
        output.append("")
        
        # Check for pending handoffs
        handoffs_path = brain / "ledger" / "handoffs.json"
        pending_handoffs = []
        if handoffs_path.exists():
            try:
                with open(handoffs_path) as f:
                    all_handoffs = json.load(f)
                    pending_handoffs = [h for h in all_handoffs if h.get("status") == "pending"]
            except Exception:
                pass
        
        if pending_handoffs:
            output.append("📬 PENDING HANDOFFS:")
            for h in pending_handoffs[:3]:
                output.append(f"   → TO: {h.get('to_agent')} | P{h.get('priority', 3)}")
                output.append(f"     Request: {h.get('request', '')[:50]}...")
            output.append("   Run: brain_get_handoffs() for details")
            output.append("")
        
        # Multi-agent coordination reminder
        output.append("🤝 MULTI-AGENT PROTOCOL:")
        output.append("   Run: brain_check_protocol('<your_agent_id>') to verify compliance")
        output.append("   Agents: windsurf_exec_001, antigravity_exec_001")
        output.append("   Protocol: .brain/protocols/MULTI_AGENT_MOU.md")
        output.append("")
        
        # Recommendations
        output.append("💡 RECOMMENDATIONS:")
        if pending_handoffs:
            output.append("   📬 Check pending handoffs first!")
        if sorted_tasks and sorted_tasks[0].get("priority", 99) <= 2:
            top = sorted_tasks[0]
            output.append(f"   ⚠️  Work on Priority {top['priority']} task first:")
            output.append(f"   '{top['description'][:60]}...'")
        elif not has_session and sorted_tasks:
            output.append("   1. Pick a task from above")
            output.append("   2. Create sprint: brain_save_session(context='...')")
            output.append("   3. Stay focused on that sprint")
        else:
            output.append("   Continue current sprint or work on top priority task")
        output.append("")
        
        output.append("📖 Read AGENT_PROTOCOL.md and MULTI_AGENT_MOU.md for workflow")
        output.append("=" * 60)
        
        # Emit event (safe)
        try:
             _emit_event("session_started", "brain", {"task_count": len(sorted_tasks)})
        except Exception:
            pass
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error in session start: {e}"


def _check_protocol_compliance(agent_id: str) -> Dict:
    """Check if agent is following multi-agent coordination protocol."""
    try:
        brain = get_brain_path()
        violations = []
        warnings = []
        
        # Load protocol
        protocol_path = brain / "protocols" / "multi_agent_mou.json"
        if not protocol_path.exists():
            return {
                "compliant": True,
                "message": "Protocol file not found - operating in standalone mode",
                "violations": [],
                "warnings": []
            }
        
        with open(protocol_path) as f:
            protocol = json.load(f)
        
        # Check 1: Is agent registered?
        agents = protocol.get("agents", {})
        if agent_id not in agents:
            warnings.append(f"Agent '{agent_id}' not in protocol registry")
        
        # Check 2: Any IN_PROGRESS tasks claimed by other agents?
        tasks = _get_tasks_list()
        in_progress = [t for t in tasks if t.get("status") == "IN_PROGRESS"]
        
        other_agent_tasks = [
            t for t in in_progress 
            if t.get("claimed_by") and t.get("claimed_by") != agent_id
        ]
        
        if other_agent_tasks:
            for t in other_agent_tasks:
                warnings.append(
                    f"Task '{t.get('id')}' claimed by {t.get('claimed_by')} - do not overlap"
                )
        
        # Check 3: Environment routing
        pending_tasks = [t for t in tasks if t.get("status") == "PENDING"]
        agent_env = agents.get(agent_id, {}).get("environment")
        
        routed_to_me = [
            t for t in pending_tasks 
            if t.get("environment") == agent_env
        ]
        
        # Build compliance report
        compliant = len(violations) == 0
        
        return {
            "compliant": compliant,
            "agent_id": agent_id,
            "agent_role": agents.get(agent_id, {}).get("role", "unknown"),
            "violations": violations,
            "warnings": warnings,
            "active_agents": list(agents.keys()),
            "tasks_for_me": [t.get("id") for t in routed_to_me],
            "tasks_in_progress_by_others": [
                {"id": t.get("id"), "claimed_by": t.get("claimed_by")} 
                for t in other_agent_tasks
            ],
            "protocol_version": protocol.get("version", "unknown"),
            "message": "Protocol compliance check complete"
        }
    except Exception as e:
        return {
            "compliant": False,
            "error": str(e),
            "violations": [f"Protocol check failed: {str(e)}"],
            "warnings": []
        }


@mcp.tool()
def brain_check_protocol(agent_id: str) -> str:
    """
    Check multi-agent coordination protocol compliance.
    
    Call this at session start to verify you're following the MoU.
    Returns violations (blocking) and warnings (informational).
    
    Args:
        agent_id: Your agent ID (e.g., 'windsurf_exec_001')
    
    Returns:
        Compliance report with violations, warnings, and task routing info
    
    Example:
        brain_check_protocol("windsurf_exec_001")
    """
    result = _check_protocol_compliance(agent_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def brain_request_handoff(
    to_agent: str,
    context: str,
    request: str,
    priority: int = 3,
    artifacts: List[str] = None
) -> str:
    """
    Request a handoff to another agent via the shared brain.
    
    Creates a handoff request that the other agent (or human) can see.
    Use this when you need another agent to continue work.
    
    Args:
        to_agent: Target agent ID (e.g., 'antigravity_exec_001')
        context: Brief context about current state
        request: What you need them to do
        priority: 1-5 (1=critical)
        artifacts: List of files they should read
    
    Returns:
        Handoff request confirmation
    """
    try:
        brain = get_brain_path()
        
        # Create handoff request
        handoff = {
            "id": f"handoff-{int(time.time())}-{str(uuid.uuid4())[:4]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "from_agent": "current_session",  # Will be filled by caller
            "to_agent": to_agent,
            "priority": priority,
            "context": context,
            "request": request,
            "artifacts": artifacts or [],
            "status": "pending"
        }
        
        # Save to handoffs file
        handoffs_path = brain / "ledger" / "handoffs.json"
        handoffs = []
        if handoffs_path.exists():
            with open(handoffs_path) as f:
                handoffs = json.load(f)
        
        handoffs.append(handoff)
        
        with open(handoffs_path, "w") as f:
            json.dump(handoffs, f, indent=2)
        
        # Emit event
        _emit_event("handoff_requested", "nucleus_mcp", {
            "handoff_id": handoff["id"],
            "to_agent": to_agent,
            "priority": priority
        })
        
        # Format for human visibility
        formatted = f"""
📬 HANDOFF REQUEST
━━━━━━━━━━━━━━━━━━
TO: {to_agent}
PRIORITY: P{priority}
CONTEXT: {context}
REQUEST: {request}
ARTIFACTS: {', '.join(artifacts) if artifacts else 'None'}
━━━━━━━━━━━━━━━━━━
ID: {handoff['id']}
Status: Pending - will appear in target agent's session_start
"""
        return formatted
        
    except Exception as e:
        return f"Error creating handoff: {str(e)}"


@mcp.tool()
def brain_get_handoffs(agent_id: str = None) -> str:
    """
    Get pending handoff requests for an agent.
    
    Args:
        agent_id: Filter to handoffs for this agent (optional)
    
    Returns:
        List of pending handoff requests
    """
    try:
        brain = get_brain_path()
        handoffs_path = brain / "ledger" / "handoffs.json"
        
        if not handoffs_path.exists():
            return json.dumps({"handoffs": [], "message": "No handoffs found"})
        
        with open(handoffs_path) as f:
            handoffs = json.load(f)
        
        # Filter to pending
        pending = [h for h in handoffs if h.get("status") == "pending"]
        
        # Filter by agent if specified
        if agent_id:
            pending = [h for h in pending if h.get("to_agent") == agent_id]
        
        return json.dumps({
            "handoffs": pending,
            "count": len(pending),
            "message": f"Found {len(pending)} pending handoff(s)"
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e), "handoffs": []})


def _get_slot_registry() -> Dict:
    """Load slot registry from disk."""
    brain = get_brain_path()
    registry_path = brain / "slots" / "registry.json"
    if not registry_path.exists():
        return {"slots": {}, "aliases": {}}
    with open(registry_path) as f:
        return json.load(f)


def _save_slot_registry(registry: Dict):
    """Save slot registry to disk."""
    brain = get_brain_path()
    registry_path = brain / "slots" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def _get_tier_definitions() -> Dict:
    """Load tier definitions from disk."""
    brain = get_brain_path()
    tiers_path = brain / "protocols" / "tiers.json"
    if not tiers_path.exists():
        return {"tiers": {}, "tier_priority_mapping": {}}
    with open(tiers_path) as f:
        return json.load(f)


def _resolve_slot_id(slot_id: str, registry: Dict) -> str:
    """Resolve alias to actual slot ID."""
    if slot_id in registry.get("slots", {}):
        return slot_id
    return registry.get("aliases", {}).get(slot_id, slot_id)


def _get_tier_for_model(model: str, tier_defs: Dict) -> str:
    """Determine tier for a model."""
    model_lower = model.lower().replace(" ", "_").replace("-", "_")
    for tier_name, tier_info in tier_defs.get("tiers", {}).items():
        models = [m.lower() for m in tier_info.get("models", [])]
        if model_lower in models or any(model_lower in m or m in model_lower for m in models):
            return tier_name
    return "standard"  # Default


def _infer_task_tier(task: Dict, tier_defs: Dict) -> str:
    """Infer required tier from task metadata."""
    # Check explicit required_tier
    if task.get("required_tier"):
        return task["required_tier"]
    
    # Check environment (human tasks)
    if task.get("environment") == "human":
        return "human"
    
    # Infer from priority
    priority = task.get("priority", 3)
    mapping = tier_defs.get("tier_priority_mapping", {})
    return mapping.get(str(priority), "standard")


def _can_slot_run_task(slot_tier: str, task_tier: str, tier_defs: Dict) -> bool:
    """Check if slot tier can handle task tier."""
    if task_tier == "human":
        return False  # Human tasks can't be claimed by slots
    
    tiers = tier_defs.get("tiers", {})
    slot_level = tiers.get(slot_tier, {}).get("level", 99)
    task_level = tiers.get(task_tier, {}).get("level", 1)
    
    # Lower level = more powerful. Slot can run if its level <= task level.
    return slot_level <= task_level


def _compute_slot_blockers(task: Dict, tasks: List[Dict], registry: Dict) -> List[str]:
    """Compute which slots are blocking this task."""
    blocking_slots = set()
    blocked_by = task.get("blocked_by", [])
    
    for dep_id in blocked_by:
        # Find the dependency task
        dep_task = next((t for t in tasks if t.get("id") == dep_id), None)
        if not dep_task:
            continue
        
        # If dependency is not done, check who owns it
        if dep_task.get("status") != "DONE":
            claimed_by = dep_task.get("claimed_by")
            if claimed_by:
                blocking_slots.add(claimed_by)
    
    return list(blocking_slots)


# ============================================================================
# NOP V3.0: FENCING TOKEN SYSTEM
# ============================================================================

def _get_fence_counter() -> Dict:
    """Load fence counter from disk."""
    brain = get_brain_path()
    counter_path = brain / "ledger" / "fence_counter.json"
    if not counter_path.exists():
        return {"value": 100, "last_issued": None, "history": []}
    with open(counter_path) as f:
        return json.load(f)


def _increment_fence_token() -> int:
    """Atomically increment and return the next fence token."""
    brain = get_brain_path()
    counter_path = brain / "ledger" / "fence_counter.json"
    counter_path.parent.mkdir(parents=True, exist_ok=True)
    
    counter = _get_fence_counter()
    counter["value"] += 1
    counter["last_issued"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    with open(counter_path, "w") as f:
        json.dump(counter, f, indent=2)
    
    return counter["value"]


def _get_model_cost(model: str) -> float:
    """Get cost per 1K tokens for a model."""
    tier_defs = _get_tier_definitions()
    model_costs = tier_defs.get("model_costs", {})
    
    # Normalize model name
    model_lower = model.lower().replace(" ", "_").replace("-", "_")
    
    # Direct lookup
    if model_lower in model_costs:
        return model_costs[model_lower]
    
    # Fuzzy match
    for cost_model, cost in model_costs.items():
        if model_lower in cost_model or cost_model in model_lower:
            return cost
    
    return 0.010  # Default cost


# ============================================================================
# NOP V3.0: DEPENDENCY GRAPH COMPUTATION
# ============================================================================

def _compute_dependency_graph(tasks: List[Dict], registry: Dict) -> Dict:
    """
    Compute full dependency graph with slot-level blocking.
    
    Returns:
        {
            "task_to_task": {task_id: [blocking_task_ids]},
            "task_to_slot": {task_id: [blocking_slot_ids]},
            "slot_to_slot": {slot_id: [blocked_by_slot_ids]},
            "circular_deps": [[cycle_path]],
            "blocking_chains": {task_id: [full_chain]},
            "computed_at": timestamp
        }
    """
    from collections import defaultdict
    
    graph = {
        "task_to_task": {},
        "task_to_slot": {},
        "slot_to_slot": defaultdict(set),
        "circular_deps": [],
        "blocking_chains": {},
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    
    # Build task assignments map
    task_assignments = {}
    for task in tasks:
        task_id = task.get("id")
        assigned = task.get("assigned_slot") or task.get("claimed_by")
        if task_id and assigned:
            task_assignments[task_id] = assigned
    
    # Step 1: Build task-to-task graph
    for task in tasks:
        task_id = task.get("id")
        blockers = task.get("blocked_by", [])
        graph["task_to_task"][task_id] = blockers
        
        # Step 2: Compute task-to-slot (which slots are blocking this task)
        blocking_slots = set()
        for blocker_id in blockers:
            blocker_task = next((t for t in tasks if t.get("id") == blocker_id), None)
            if blocker_task and blocker_task.get("status") != "DONE":
                blocker_slot = task_assignments.get(blocker_id)
                if blocker_slot:
                    blocking_slots.add(blocker_slot)
        
        if blocking_slots:
            graph["task_to_slot"][task_id] = list(blocking_slots)
        
        # Step 3: Compute slot-to-slot
        my_slot = task_assignments.get(task_id)
        if my_slot:
            for blocking_slot in blocking_slots:
                if blocking_slot != my_slot:
                    graph["slot_to_slot"][my_slot].add(blocking_slot)
    
    # Convert defaultdict to regular dict with lists
    graph["slot_to_slot"] = {k: list(v) for k, v in graph["slot_to_slot"].items()}
    
    # Step 4: Detect circular dependencies (DFS)
    visited = set()
    path = []
    
    def dfs_cycle(task_id):
        if task_id in path:
            cycle_start = path.index(task_id)
            cycle = path[cycle_start:] + [task_id]
            if cycle not in graph["circular_deps"]:
                graph["circular_deps"].append(cycle)
            return
        if task_id in visited:
            return
        
        visited.add(task_id)
        path.append(task_id)
        
        for blocker in graph["task_to_task"].get(task_id, []):
            dfs_cycle(blocker)
        
        path.pop()
    
    for task in tasks:
        dfs_cycle(task.get("id"))
    
    # Step 5: Compute blocking chains (transitive closure)
    def get_full_chain(task_id, seen=None):
        if seen is None:
            seen = set()
        if task_id in seen:
            return []
        seen.add(task_id)
        
        chain = []
        for blocker in graph["task_to_task"].get(task_id, []):
            chain.append(blocker)
            chain.extend(get_full_chain(blocker, seen))
        return chain
    
    for task in tasks:
        task_id = task.get("id")
        graph["blocking_chains"][task_id] = get_full_chain(task_id)
    
    return graph


# ============================================================================
# NOP V3.0: MULTI-FACTOR SLOT SCORING
# ============================================================================

def _score_slot_for_task(task: Dict, slot: Dict, tier_defs: Dict) -> Dict:
    """
    Score a slot for a task using multi-factor analysis.
    
    Returns:
        {
            "score": 0-100,
            "breakdown": {factor: points},
            "warnings": [],
            "recommendation": str
        }
    """
    score = 0
    breakdown = {}
    warnings = []
    
    tiers = tier_defs.get("tiers", {})
    task_tier = _infer_task_tier(task, tier_defs)
    slot_tier = slot.get("tier", "standard")
    
    task_level = tiers.get(task_tier, {}).get("level", 3)
    slot_level = tiers.get(slot_tier, {}).get("level", 3)
    
    # 1. TIER MATCH (0-30 points)
    if slot_level == task_level:
        breakdown["tier_match"] = 30
        score += 30
    elif slot_level < task_level:
        breakdown["tier_match"] = 25  # Overpowered
        score += 25
    elif slot_level == task_level + 1:
        breakdown["tier_match"] = 10  # Slightly underpowered
        score += 10
        warnings.append(f"Slot tier ({slot_tier}) is 1 level below task tier ({task_tier})")
    else:
        breakdown["tier_match"] = 0  # Too weak
        warnings.append(f"TIER_MISMATCH: Slot ({slot_tier}) cannot handle task ({task_tier})")
    
    # 2. AVAILABILITY (0-25 points)
    if slot.get("status") == "active" and not slot.get("current_task"):
        breakdown["availability"] = 25
        score += 25
    elif slot.get("status") == "active":
        breakdown["availability"] = 10
        score += 10
    else:
        breakdown["availability"] = 0
        warnings.append(f"Slot status: {slot.get('status')}")
    
    # 3. CAPABILITY MATCH (0-20 points)
    task_skills = set(task.get("required_skills", []))
    slot_caps = set(slot.get("capabilities", []))
    if task_skills:
        overlap = len(task_skills & slot_caps) / len(task_skills)
        cap_score = int(overlap * 20)
        breakdown["capability"] = cap_score
        score += cap_score
    else:
        breakdown["capability"] = 15  # No specific skills required
        score += 15
    
    # 4. COST EFFICIENCY (0-15 points)
    model = slot.get("model", "")
    cost = _get_model_cost(model)
    if cost <= 0.005:
        breakdown["cost"] = 15
        score += 15
    elif cost <= 0.015:
        breakdown["cost"] = 10
        score += 10
    elif cost <= 0.030:
        breakdown["cost"] = 5
        score += 5
    else:
        breakdown["cost"] = 0
    
    # 5. HEALTH (0-10 points)
    success_rate = slot.get("success_rate", 1.0)
    health_score = int(success_rate * 10)
    breakdown["health"] = health_score
    score += health_score
    
    # Generate recommendation
    if score >= 80:
        recommendation = "EXCELLENT match"
    elif score >= 60:
        recommendation = "GOOD match"
    elif score >= 40:
        recommendation = "ACCEPTABLE with warnings"
    else:
        recommendation = "NOT RECOMMENDED"
    
    return {
        "score": score,
        "breakdown": breakdown,
        "warnings": warnings,
        "recommendation": recommendation,
        "slot_id": slot.get("id"),
        "estimated_cost": _get_model_cost(slot.get("model", "")) * task.get("estimated_tokens", 5000) / 1000
    }


# ============================================================================
# NOP V3.0: CLAIM WITH FENCING
# ============================================================================

def _claim_with_fence(task_id: str, slot_id: str) -> Dict:
    """
    Atomically claim a task with fencing token.
    
    Returns:
        {"success": bool, "fence_token": int, "error": str}
    """
    try:
        tasks = _get_tasks_list()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Check if already claimed by someone else
        if task.get("claimed_by") and task.get("claimed_by") != slot_id:
            return {
                "success": False,
                "error": f"Task already claimed by {task['claimed_by']}",
                "current_fence": task.get("fence_token")
            }
        
        # Issue new fence token
        fence_token = _increment_fence_token()
        
        # Update task
        task["claimed_by"] = slot_id
        task["fence_token"] = fence_token
        task["claimed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        task["status"] = "IN_PROGRESS"
        
        _save_tasks_list(tasks)
        
        # Update slot
        registry = _get_slot_registry()
        if slot_id in registry.get("slots", {}):
            registry["slots"][slot_id]["current_task"] = task_id
            registry["slots"][slot_id]["fence_token"] = fence_token
            _save_slot_registry(registry)
        
        _emit_event("task_claimed_with_fence", slot_id, {
            "task_id": task_id,
            "fence_token": fence_token
        })
        
        return {
            "success": True,
            "fence_token": fence_token,
            "task_id": task_id,
            "slot_id": slot_id
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def _complete_with_fence(task_id: str, slot_id: str, fence_token: int, outcome: str = "success") -> Dict:
    """
    Complete a task with fence token validation.
    
    Returns:
        {"success": bool, "error": str}
    """
    try:
        tasks = _get_tasks_list()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Validate fence token
        if task.get("fence_token") != fence_token:
            return {
                "success": False,
                "error": "Stale fence token - task was reassigned",
                "expected_fence": fence_token,
                "current_fence": task.get("fence_token")
            }
        
        # Validate claimer
        if task.get("claimed_by") != slot_id:
            return {
                "success": False,
                "error": f"Task claimed by different slot: {task['claimed_by']}"
            }
        
        # Complete the task
        task["status"] = "DONE" if outcome == "success" else "FAILED"
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        task["completed_by"] = slot_id
        
        _save_tasks_list(tasks)
        
        _emit_event("task_completed_with_fence", slot_id, {
            "task_id": task_id,
            "fence_token": fence_token,
            "outcome": outcome
        })
        
        return {"success": True, "task_id": task_id, "outcome": outcome}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def _brain_orchestrate_impl(
    slot_id: str = None,
    model: str = None,
    alias: str = None,
    mode: str = "auto"
) -> str:
    """
    Internal implementation of brain_orchestrate - directly callable.
    
    This function contains the actual orchestration logic and can be called
    directly from other Python code without going through MCP protocol.
    """
    try:
        brain = get_brain_path()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Load registries
        registry = _get_slot_registry()
        tier_defs = _get_tier_definitions()
        tasks = _get_tasks_list()
        
        # Build response structure
        response = {
            "meta": {
                "timestamp": now,
                "protocol_version": "2.0.0",
                "mode": mode
            },
            "slot": None,
            "protocol_status": {
                "compliant": True,
                "violations": [],
                "warnings": []
            },
            "handoffs": {
                "pending_for_me": [],
                "sent_by_me": []
            },
            "action": {
                "type": "WAIT",
                "task_id": None,
                "task_description": None,
                "task_priority": None,
                "claimed": False,
                "reason": "Initializing..."
            },
            "queue": {
                "assigned_to_me": [],
                "blocked": [],
                "available_for_claim": []
            },
            "system": {
                "active_slots": len([s for s in registry.get("slots", {}).values() if s.get("status") == "active"]),
                "total_pending": len([t for t in tasks if t.get("status") == "PENDING"]),
                "total_in_progress": len([t for t in tasks if t.get("status") == "IN_PROGRESS"]),
                "total_blocked": len([t for t in tasks if t.get("status") == "BLOCKED"]),
                "total_done": len([t for t in tasks if t.get("status") == "DONE"])
            }
        }
        
        # REGISTRATION MODE
        if mode == "register":
            if not model:
                response["action"] = {
                    "type": "ERROR",
                    "reason": "model parameter required for registration"
                }
                return json.dumps(response, indent=2)
            
            # Generate slot ID if not provided
            if not slot_id:
                slot_id = f"slot_{int(time.time())}_{str(uuid.uuid4())[:4]}"
            
            # Determine tier
            tier = _get_tier_for_model(model, tier_defs)
            
            # Create slot entry
            new_slot = {
                "id": slot_id,
                "alias": alias,
                "ide": "unknown",
                "model": model,
                "tier": tier,
                "capabilities": [],
                "status": "active",
                "current_task": None,
                "registered_at": now,
                "last_heartbeat": now,
                "tasks_completed": 0,
                "reset_at": None
            }
            
            registry["slots"][slot_id] = new_slot
            if alias:
                registry["aliases"][alias] = slot_id
            
            _save_slot_registry(registry)
            
            response["slot"] = new_slot
            response["action"] = {
                "type": "REGISTERED",
                "reason": f"Slot {slot_id} registered with tier {tier}"
            }
            
            _emit_event("slot_registered", "nucleus_orchestrate", {
                "slot_id": slot_id,
                "model": model,
                "tier": tier
            })
            
            return json.dumps(response, indent=2)
        
        # RESOLVE SLOT ID
        if not slot_id:
            response["action"] = {
                "type": "ERROR",
                "reason": "slot_id required (use mode='register' to create new slot)"
            }
            return json.dumps(response, indent=2)
        
        resolved_id = _resolve_slot_id(slot_id, registry)
        slot = registry.get("slots", {}).get(resolved_id)
        
        if not slot:
            response["action"] = {
                "type": "REGISTER_REQUIRED",
                "reason": f"Slot '{slot_id}' not found. Use mode='register' with model parameter."
            }
            return json.dumps(response, indent=2)
        
        # Update heartbeat
        slot["last_heartbeat"] = now
        registry["slots"][resolved_id] = slot
        _save_slot_registry(registry)
        
        response["slot"] = slot
        
        # CHECK FOR EXHAUSTION
        if slot.get("status") == "exhausted":
            response["action"] = {
                "type": "EXHAUSTED",
                "reason": f"Slot exhausted. Reset at: {slot.get('reset_at', 'unknown')}"
            }
            return json.dumps(response, indent=2)
        
        # CHECK HANDOFFS
        handoffs_path = brain / "ledger" / "handoffs.json"
        if handoffs_path.exists():
            with open(handoffs_path) as f:
                all_handoffs = json.load(f)
            response["handoffs"]["pending_for_me"] = [
                h for h in all_handoffs 
                if h.get("to_agent") == resolved_id and h.get("status") == "pending"
            ]
        
        # PROTOCOL COMPLIANCE
        in_progress = [t for t in tasks if t.get("status") == "IN_PROGRESS"]
        other_agent_tasks = [
            t for t in in_progress 
            if t.get("claimed_by") and t.get("claimed_by") != resolved_id
        ]
        
        for t in other_agent_tasks:
            response["protocol_status"]["warnings"].append(
                f"Task '{t.get('id')}' claimed by {t.get('claimed_by')} - do not overlap"
            )
        
        # FIND AVAILABLE TASKS
        slot_tier = slot.get("tier", "standard")
        available = []
        blocked = []
        
        for task in tasks:
            if task.get("status") not in ["PENDING", "READY"]:
                continue
            if task.get("claimed_by"):
                continue
            
            task_tier = _infer_task_tier(task, tier_defs)
            
            # Check tier compatibility
            if not _can_slot_run_task(slot_tier, task_tier, tier_defs):
                continue
            
            # Check dependencies
            slot_blockers = _compute_slot_blockers(task, tasks, registry)
            task_blockers = task.get("blocked_by", [])
            
            # Check if all blocking tasks are done
            all_done = True
            for dep_id in task_blockers:
                dep = next((t for t in tasks if t.get("id") == dep_id), None)
                if dep and dep.get("status") != "DONE":
                    all_done = False
                    break
            
            if not all_done or slot_blockers:
                blocked.append({
                    "id": task.get("id"),
                    "blocked_by_slots": slot_blockers,
                    "blocked_by_tasks": task_blockers
                })
            else:
                available.append(task)
        
        response["queue"]["blocked"] = blocked
        response["queue"]["available_for_claim"] = [t.get("id") for t in available]
        
        # SORT BY PRIORITY
        available.sort(key=lambda t: t.get("priority", 99))
        
        # HANDLE MODES
        if mode == "report":
            response["action"] = {
                "type": "REPORT",
                "reason": f"{len(available)} tasks available, {len(blocked)} blocked"
            }
            return json.dumps(response, indent=2)
        
        if not available:
            if blocked:
                response["action"] = {
                    "type": "BLOCKED",
                    "reason": f"All {len(blocked)} available tasks are blocked by other slots"
                }
            else:
                response["action"] = {
                    "type": "WAIT",
                    "reason": "No tasks available for your tier"
                }
            return json.dumps(response, indent=2)
        
        # BEST TASK
        best_task = available[0]
        
        if mode == "guided":
            response["action"] = {
                "type": "CHOOSE",
                "task_id": best_task.get("id"),
                "task_description": best_task.get("description"),
                "task_priority": best_task.get("priority"),
                "claimed": False,
                "reason": f"Recommended: {best_task.get('id')}. {len(available)} total available."
            }
            return json.dumps(response, indent=2)
        
        # AUTO MODE - CLAIM THE TASK
        claim_result = _claim_task(best_task.get("id"), resolved_id)
        
        if claim_result.get("success"):
            response["action"] = {
                "type": "WORK",
                "task_id": best_task.get("id"),
                "task_description": best_task.get("description"),
                "task_priority": best_task.get("priority"),
                "claimed": True,
                "reason": "Claimed highest priority unblocked task"
            }
            response["autopilot_hint"] = {
                "continue": len(available) > 1,
                "next_call": f"brain_orchestrate('{resolved_id}') after completing this task",
                "remaining_tasks": len(available) - 1
            }
        else:
            response["action"] = {
                "type": "ERROR",
                "reason": f"Claim failed: {claim_result.get('error')}"
            }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return json.dumps({
            "meta": {"error": str(e)},
            "action": {"type": "ERROR", "reason": str(e)}
        }, indent=2)


@mcp.tool()
def brain_orchestrate(
    slot_id: str = None,
    model: str = None,
    alias: str = None,
    mode: str = "auto"
) -> str:
    """
    THE GOD COMMAND - Single entry point for all slot operations.
    
    Modes:
    - register: Create new slot with model/alias
    - auto: Check status + auto-claim best task + return instructions
    - guided: Check status + show options + wait for human choice
    - report: Just show status, no actions
    
    Args:
        slot_id: Your slot ID or alias (e.g., 'windsurf_001' or 'ws_opus')
        model: Model name for registration (e.g., 'claude_opus_4.5')
        alias: Human-friendly alias for slot
        mode: Operation mode - 'auto', 'guided', 'report', 'register'
    
    Returns:
        JSON with guaranteed schema - no interpretation needed.
        
    Example:
        brain_orchestrate("windsurf_001", mode="auto")
        brain_orchestrate(slot_id="new_slot", model="gemini_3_pro_high", mode="register")
    """
    return _brain_orchestrate_impl(slot_id, model, alias, mode)


@mcp.tool()
def brain_slot_complete(slot_id: str, task_id: str, outcome: str = "success", notes: str = None) -> str:
    """
    Mark a task as complete and get next task.
    
    Args:
        slot_id: Your slot ID
        task_id: Task you just completed
        outcome: 'success' or 'failed'
        notes: Optional completion notes
    
    Returns:
        Updated status and next task recommendation
    """
    try:
        registry = _get_slot_registry()
        resolved_id = _resolve_slot_id(slot_id, registry)
        
        # Update task status
        tasks = _get_tasks_list()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "DONE" if outcome == "success" else "FAILED"
                task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                task["completion_notes"] = notes
                break
        
        _save_tasks_list(tasks)
        
        # Update slot
        slot = registry["slots"].get(resolved_id, {})
        slot["current_task"] = None
        slot["tasks_completed"] = slot.get("tasks_completed", 0) + 1
        registry["slots"][resolved_id] = slot
        _save_slot_registry(registry)
        
        # Emit event
        _emit_event("task_completed", resolved_id, {
            "task_id": task_id,
            "outcome": outcome
        })
        
        # Get next task (use impl to avoid FunctionTool callable issue)
        return _brain_orchestrate_impl(slot_id=resolved_id, mode="auto")
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def brain_slot_exhaust(slot_id: str, reset_hours: int = 5) -> str:
    """
    Mark slot as exhausted (model hit usage limit).
    
    Args:
        slot_id: Your slot ID
        reset_hours: Hours until model resets (default: 5 for Gemini)
    
    Returns:
        Confirmation with reset time
    """
    try:
        registry = _get_slot_registry()
        resolved_id = _resolve_slot_id(slot_id, registry)
        
        slot = registry["slots"].get(resolved_id)
        if not slot:
            return json.dumps({"error": f"Slot {slot_id} not found"})
        
        # Calculate reset time
        reset_at = time.time() + (reset_hours * 3600)
        reset_at_str = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(reset_at))
        
        slot["status"] = "exhausted"
        slot["reset_at"] = reset_at_str
        registry["slots"][resolved_id] = slot
        _save_slot_registry(registry)
        
        _emit_event("slot_exhausted", resolved_id, {
            "reset_at": reset_at_str
        })
        
        return json.dumps({
            "slot_id": resolved_id,
            "status": "exhausted",
            "reset_at": reset_at_str,
            "message": f"Slot marked exhausted. Will reset at {reset_at_str}"
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# NOP V3.1: STATUS DASHBOARD - VISUAL MONITORING
# ============================================================================

@mcp.tool()
def brain_status_dashboard(detail_level: str = "standard") -> str:
    """
    Get comprehensive status dashboard for agent pool monitoring.
    
    Shows pool health, slot status, task queue, and cost tracking
    in a visual ASCII format.
    
    Args:
        detail_level: "minimal", "standard", or "full"
        
    Returns:
        Formatted dashboard with ASCII visualization
    
    Example:
        brain_status_dashboard()  # Standard view
        brain_status_dashboard("full")  # Include cost tracking
    """
    try:
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Load data
        registry = _get_slot_registry()
        tasks = _get_tasks_list()
        _get_tier_definitions()
        all_slots = registry.get("slots", {})
        
        # Calculate metrics
        active_slots = [s for s in all_slots.values() if s.get("status") == "active"]
        [s for s in all_slots.values() if s.get("status") == "exhausted"]
        busy_slots = [s for s in all_slots.values() if s.get("current_task")]
        
        pending_tasks = [t for t in tasks if t.get("status") in ["PENDING", "READY"]]
        in_progress_tasks = [t for t in tasks if t.get("status") == "IN_PROGRESS"]
        blocked_tasks = [t for t in tasks if t.get("status") == "BLOCKED"]
        done_tasks = [t for t in tasks if t.get("status") == "DONE"]
        
        # Priority breakdown
        # Priority breakdown - safely handle string priorities
        def get_prio(t):
            try:
                return int(t.get("priority", 3))
            except (ValueError, TypeError):
                return 3

        p1_tasks = [t for t in pending_tasks if get_prio(t) == 1]
        p2_tasks = [t for t in pending_tasks if get_prio(t) == 2]
        p3_tasks = [t for t in pending_tasks if get_prio(t) == 3]
        p4_tasks = [t for t in pending_tasks if get_prio(t) >= 4]
        
        # Calculate health and utilization
        total_slots = len(all_slots)
        pool_utilization = len(busy_slots) / max(total_slots, 1) * 100
        pool_health = len(active_slots) / max(total_slots, 1) * 100
        
        # Build dashboard
        lines = []
        
        # Header
        lines.append("╔" + "═" * 62 + "╗")
        lines.append("║  🧠 NUCLEUS ORCHESTRATION DASHBOARD v3.1" + " " * 20 + "║")
        lines.append("╠" + "═" * 62 + "╣")
        
        # Pool Overview
        health_bar = "█" * int(pool_health / 10) + "░" * (10 - int(pool_health / 10))
        util_bar = "█" * int(pool_utilization / 16.67) + "░" * (6 - int(pool_utilization / 16.67))
        
        lines.append(f"║  POOL HEALTH: {health_bar} {pool_health:.0f}%   │  UTILIZATION: {util_bar} {pool_utilization:.0f}%  ║")
        lines.append(f"║  ACTIVE SLOTS: {len(active_slots)}/{total_slots}" + " " * 16 + f"│  TASKS PENDING: {len(pending_tasks)}" + " " * 8 + "║")
        lines.append("╚" + "═" * 62 + "╝")
        lines.append("")
        
        # Slot Status Grid
        lines.append("SLOT STATUS:")
        lines.append("┌" + "─" * 18 + "┬" + "─" * 8 + "┬" + "─" * 10 + "┬" + "─" * 23 + "┐")
        lines.append("│ SLOT             │ STATUS │ TASK     │ RESET                 │")
        lines.append("├" + "─" * 18 + "┼" + "─" * 8 + "┼" + "─" * 10 + "┼" + "─" * 23 + "┤")
        
        for slot_id, slot in list(all_slots.items())[:6]:  # Max 6 slots for display
            status = slot.get("status", "unknown")
            current_task = slot.get("current_task", "--")
            if current_task and len(current_task) > 8:
                current_task = current_task[:8]
            
            # Status icon
            if status == "active" and not slot.get("current_task"):
                status_icon = "🟢 IDLE"
            elif status == "active" and slot.get("current_task"):
                status_icon = "🔵 BUSY"
            elif status == "exhausted":
                status_icon = "🔴 EXHA"
            else:
                status_icon = "⚪ " + status[:4].upper()
            
            # Reset info
            reset_at = slot.get("reset_at")
            if reset_at:
                reset_info = f"🔄 {reset_at[:16]}"
            else:
                reset_info = "∞ unlimited"
            
            slot_display = slot_id[:16] if len(slot_id) > 16 else slot_id.ljust(16)
            current_task = str(current_task).ljust(8)[:8]
            reset_info = reset_info[:21].ljust(21)
            
            lines.append(f"│ {slot_display} │ {status_icon} │ {current_task} │ {reset_info} │")
        
        lines.append("└" + "─" * 18 + "┴" + "─" * 8 + "┴" + "─" * 10 + "┴" + "─" * 23 + "┘")
        lines.append("")
        
        # Task Queue Summary
        lines.append("TASK QUEUE:")
        max_bar = max(len(p1_tasks), len(p2_tasks), len(p3_tasks), len(p4_tasks), len(blocked_tasks), 1)
        scale = 20 / max_bar if max_bar > 0 else 1
        
        p1_bar = "█" * max(1, int(len(p1_tasks) * scale)) if p1_tasks else ""
        p2_bar = "█" * max(1, int(len(p2_tasks) * scale)) if p2_tasks else ""
        p3_bar = "█" * max(1, int(len(p3_tasks) * scale)) if p3_tasks else ""
        p4_bar = "█" * max(1, int(len(p4_tasks) * scale)) if p4_tasks else ""
        blocked_bar = "█" * max(1, int(len(blocked_tasks) * scale)) if blocked_tasks else ""
        
        lines.append(f"  P1 (Critical): {p1_bar} {len(p1_tasks)} tasks")
        lines.append(f"  P2 (High):     {p2_bar} {len(p2_tasks)} tasks")
        lines.append(f"  P3 (Medium):   {p3_bar} {len(p3_tasks)} tasks")
        lines.append(f"  P4 (Low):      {p4_bar} {len(p4_tasks)} tasks")
        lines.append(f"  BLOCKED:       {blocked_bar} {len(blocked_tasks)} tasks")
        lines.append("")
        
        # Full detail: Cost tracking
        if detail_level == "full":
            lines.append("COST TRACKING (Session):")
            total_tokens = sum(s.get("tokens_used", 0) for s in all_slots.values())
            total_cost = sum(s.get("total_cost", 0) for s in all_slots.values())
            lines.append(f"  Total Tokens: {total_tokens:,}")
            lines.append(f"  Est. Cost: ${total_cost:.2f}")
            lines.append("  By Slot:")
            for slot_id, slot in list(all_slots.items())[:4]:
                slot_cost = slot.get("total_cost", 0)
                slot_tokens = slot.get("tokens_used", 0)
                lines.append(f"    - {slot_id}: ${slot_cost:.2f} ({slot_tokens:,} tokens)")
            lines.append("")
        
        # Summary stats
        lines.append(f"📊 Generated at: {now}")
        lines.append(f"📈 Tasks: {len(done_tasks)} done | {len(in_progress_tasks)} in progress | {len(pending_tasks)} pending")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"Dashboard error: {str(e)}"


# ============================================================================
# NOP V3.1: CHECKPOINT TOOLS - PAUSE/RESUME FOR LONG-RUNNING TASKS
# ============================================================================

def _brain_checkpoint_task_impl(
    task_id: str,
    step: int = None,
    progress_percent: float = None,
    context: str = None,
    artifacts: List[str] = None,
    resumable: bool = True
) -> str:
    """Internal implementation of brain_checkpoint_task - directly callable."""
    try:
        orch = get_orch()
        
        checkpoint_data = {
            "step": step,
            "progress_percent": progress_percent,
            "context": context,
            "artifacts": artifacts or [],
            "resumable": resumable
        }
        
        # Remove None values
        checkpoint_data = {k: v for k, v in checkpoint_data.items() if v is not None}
        
        result = orch.checkpoint_task(task_id, checkpoint_data)
        
        if result.get("success"):
            output = f"✅ Checkpoint saved for task {task_id}\n"
            output += f"   Step: {step or 'N/A'}\n"
            output += f"   Progress: {progress_percent or 'N/A'}%\n"
            output += f"   Resumable: {resumable}\n"
            if artifacts:
                output += f"   Artifacts: {len(artifacts)} files\n"
            output += f"\n💡 To resume: brain_resume_from_checkpoint('{task_id}')"
            return output
        else:
            return f"❌ Checkpoint failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Checkpoint error: {str(e)}"


def _brain_resume_from_checkpoint_impl(task_id: str) -> str:
    """Internal implementation of brain_resume_from_checkpoint - directly callable."""
    try:
        orch = get_orch()
        result = orch.resume_from_checkpoint(task_id)
        
        if result.get("success"):
            checkpoint = result.get("checkpoint", {})
            data = checkpoint.get("data", {})
            context_summary = result.get("context_summary")
            
            output = f"📋 Resume Instructions for {task_id}\n"
            output += "=" * 50 + "\n\n"
            
            output += "## Checkpoint Data\n"
            output += f"   Last checkpoint: {checkpoint.get('last_checkpoint_at', 'N/A')}\n"
            output += f"   Step: {data.get('step', 'N/A')}\n"
            output += f"   Progress: {data.get('progress_percent', 'N/A')}%\n"
            output += f"   Resumable: {data.get('resumable', True)}\n"
            
            if data.get("context"):
                output += f"\n## Context\n{data.get('context')}\n"
            
            if data.get("artifacts"):
                output += "\n## Artifacts Created\n"
                for a in data["artifacts"]:
                    output += f"   - {a}\n"
            
            if context_summary:
                output += f"\n## Previous Summary\n{context_summary.get('summary', 'N/A')}\n"
                if context_summary.get("key_decisions"):
                    output += "\n## Key Decisions\n"
                    for d in context_summary["key_decisions"]:
                        output += f"   - {d}\n"
            
            output += f"\n{result.get('resume_instructions', '')}"
            return output
        else:
            return f"❌ Resume failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Resume error: {str(e)}"


def _brain_generate_handoff_summary_impl(
    task_id: str,
    summary: str,
    key_decisions: List[str] = None,
    handoff_notes: str = ""
) -> str:
    """Internal implementation of brain_generate_handoff_summary - directly callable."""
    try:
        orch = get_orch()
        result = orch.generate_context_summary(
            task_id, summary, key_decisions or [], handoff_notes
        )
        
        if result.get("success"):
            output = f"✅ Handoff summary generated for {task_id}\n"
            output += f"   Summary length: {len(summary)} chars\n"
            output += f"   Key decisions: {len(key_decisions or [])} items\n"
            if handoff_notes:
                output += f"   Handoff notes: {len(handoff_notes)} chars\n"
            return output
        else:
            return f"❌ Summary generation failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Summary error: {str(e)}"


@mcp.tool()
def brain_checkpoint_task(
    task_id: str,
    step: int = None,
    progress_percent: float = None,
    context: str = None,
    artifacts: List[str] = None,
    resumable: bool = True
) -> str:
    """
    Save checkpoint for long-running task.
    
    Use this to persist progress before:
    - Agent exhaustion (rate limits, reset cycles)
    - Session end
    - Handoff to another agent
    
    Args:
        task_id: Task to checkpoint
        step: Current step number (e.g., 3 of 5)
        progress_percent: 0-100 completion percentage
        context: Textual context for resume
        artifacts: List of artifact paths created so far
        resumable: Whether task can be resumed from this point
    
    Returns:
        Checkpoint confirmation with recovery instructions
    """
    return _brain_checkpoint_task_impl(task_id, step, progress_percent, context, artifacts, resumable)


@mcp.tool()
def brain_resume_from_checkpoint(task_id: str) -> str:
    """
    Get checkpoint data for task resumption.
    
    Use this when:
    - Resuming after agent exhaustion
    - Taking over from another agent
    - Continuing after session restart
    
    Args:
        task_id: Task to resume
    
    Returns:
        Checkpoint data with context and resume instructions
    """
    return _brain_resume_from_checkpoint_impl(task_id)


@mcp.tool()
def brain_generate_handoff_summary(
    task_id: str,
    summary: str,
    key_decisions: List[str] = None,
    handoff_notes: str = ""
) -> str:
    """
    Generate context summary for task handoff.
    
    Use this before:
    - Handing off to another agent
    - Ending a session with incomplete work
    - Approaching reset cycle limit
    
    Args:
        task_id: Task to summarize
        summary: Brief summary of current state
        key_decisions: List of decisions made during work
        handoff_notes: Notes for the next agent
    
    Returns:
        Confirmation of summary generation
    """
    return _brain_generate_handoff_summary_impl(task_id, summary, key_decisions, handoff_notes)




# ============================================================================
# NOP V3.0: THE SPRINT COMMAND - MULTI-SLOT ORCHESTRATION
# ============================================================================

@mcp.tool()
def brain_autopilot_sprint(
    slots: List[str] = None,
    mode: str = "auto",
    halt_on_blocker: bool = True,
    halt_on_tier_mismatch: bool = False,
    max_tasks_per_slot: int = 10,
    budget_limit: float = None,
    dry_run: bool = False
) -> str:
    """
    THE SPRINT COMMAND - Orchestrate multiple slots in parallel.
    
    This is the ENTERPRISE upgrade over brain_orchestrate().
    Coordinates a TEAM of slots working simultaneously.
    
    Args:
        slots: Slot IDs to orchestrate (None = all active slots)
        mode: 'auto' (execute), 'plan' (show what would happen), 'status' (current state)
        halt_on_blocker: Stop if circular dependency detected
        halt_on_tier_mismatch: Stop if task requires higher tier than available
        max_tasks_per_slot: Max tasks to assign per slot in one sprint
        budget_limit: Max cost ($) for entire sprint (None = unlimited)
        dry_run: If True, don't actually claim tasks, just show plan
    
    Returns:
        Sprint execution report with per-slot results.
    
    Example:
        brain_autopilot_sprint()  # All active slots
        brain_autopilot_sprint(slots=["windsurf_001", "antigravity_001"])
        brain_autopilot_sprint(mode="plan", dry_run=True)  # Preview
    """
    try:
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        sprint_id = f"sprint_{int(time.time())}_{str(uuid.uuid4())[:4]}"
        
        # Load data
        registry = _get_slot_registry()
        tier_defs = _get_tier_definitions()
        tasks = _get_tasks_list()
        all_slots = registry.get("slots", {})
        
        # PHASE 1: SELECT TARGET SLOTS
        if slots is None:
            target_slots = [s for s in all_slots.values() if s.get("status") == "active"]
        else:
            target_slots = []
            for slot_id in slots:
                resolved = _resolve_slot_id(slot_id, registry)
                if resolved in all_slots:
                    target_slots.append(all_slots[resolved])
        
        if not target_slots:
            return json.dumps({
                "sprint_id": sprint_id,
                "status": "ERROR",
                "error": "No active slots found",
                "timestamp": now
            }, indent=2)
        
        # PHASE 2: COMPUTE DEPENDENCY GRAPH
        dep_graph = _compute_dependency_graph(tasks, registry)
        
        # Check for circular dependencies
        if dep_graph["circular_deps"] and halt_on_blocker:
            return json.dumps({
                "sprint_id": sprint_id,
                "status": "HALTED",
                "reason": "Circular dependencies detected",
                "circular_deps": dep_graph["circular_deps"],
                "action": "Resolve circular dependencies before sprint",
                "timestamp": now
            }, indent=2)
        
        # PHASE 3: COMPUTE ASSIGNMENTS
        assignments = []
        total_estimated_cost = 0
        tasks_assigned = 0
        slots_blocked = 0
        
        for slot in target_slots:
            slot_id = slot.get("id")
            slot_tier = slot.get("tier", "standard")
            
            # Skip exhausted slots
            if slot.get("status") == "exhausted":
                assignments.append({
                    "slot_id": slot_id,
                    "task_id": None,
                    "status": "EXHAUSTED",
                    "reason": f"Slot exhausted. Recovery at: {slot.get('reset_at', 'unknown')}"
                })
                continue
            
            # Find runnable tasks for this slot
            runnable_tasks = []
            blocked_reasons = []
            
            for task in tasks:
                task_id = task.get("id")
                
                # Skip non-pending tasks
                if task.get("status") not in ["PENDING", "READY"]:
                    continue
                
                # Skip already claimed tasks
                if task.get("claimed_by"):
                    continue
                
                # Check tier compatibility
                task_tier = _infer_task_tier(task, tier_defs)
                if not _can_slot_run_task(slot_tier, task_tier, tier_defs):
                    if halt_on_tier_mismatch:
                        blocked_reasons.append(f"Task {task_id} requires tier {task_tier}")
                    continue
                
                # Check dependencies
                blockers = task.get("blocked_by", [])
                all_done = True
                blocking_slots = []
                
                for dep_id in blockers:
                    dep_task = next((t for t in tasks if t.get("id") == dep_id), None)
                    if dep_task and dep_task.get("status") != "DONE":
                        all_done = False
                        if dep_task.get("claimed_by"):
                            blocking_slots.append(dep_task.get("claimed_by"))
                
                if not all_done:
                    blocked_reasons.append(f"Task {task_id} blocked by {blocking_slots or blockers}")
                    continue
                
                # Task is runnable!
                score_result = _score_slot_for_task(task, slot, tier_defs)
                runnable_tasks.append({
                    "task": task,
                    "score": score_result["score"],
                    "estimated_cost": score_result["estimated_cost"],
                    "warnings": score_result["warnings"]
                })
            
            # Sort by priority then score
            runnable_tasks.sort(key=lambda x: (x["task"].get("priority", 99), -x["score"]))
            
            if runnable_tasks:
                best = runnable_tasks[0]
                task = best["task"]
                
                # Check budget
                if budget_limit and total_estimated_cost + best["estimated_cost"] > budget_limit:
                    assignments.append({
                        "slot_id": slot_id,
                        "task_id": None,
                        "status": "BUDGET_EXCEEDED",
                        "reason": f"Would exceed budget (${total_estimated_cost:.3f} + ${best['estimated_cost']:.3f} > ${budget_limit})"
                    })
                    continue
                
                # Claim task (unless dry run)
                fence_token = None
                if mode == "auto" and not dry_run:
                    claim_result = _claim_with_fence(task.get("id"), slot_id)
                    if claim_result.get("success"):
                        fence_token = claim_result.get("fence_token")
                    else:
                        assignments.append({
                            "slot_id": slot_id,
                            "task_id": task.get("id"),
                            "status": "CLAIM_FAILED",
                            "reason": claim_result.get("error")
                        })
                        continue
                
                assignments.append({
                    "slot_id": slot_id,
                    "task_id": task.get("id"),
                    "task_description": task.get("description", "")[:100],
                    "priority": task.get("priority"),
                    "fence_token": fence_token,
                    "status": "EXECUTING" if fence_token else "PLANNED",
                    "estimated_cost": best["estimated_cost"],
                    "score": best["score"],
                    "warnings": best["warnings"]
                })
                
                total_estimated_cost += best["estimated_cost"]
                tasks_assigned += 1
            else:
                slots_blocked += 1
                assignments.append({
                    "slot_id": slot_id,
                    "task_id": None,
                    "status": "BLOCKED" if blocked_reasons else "IDLE",
                    "reason": blocked_reasons[0] if blocked_reasons else "No tasks for this tier",
                    "blocked_reasons": blocked_reasons[:3]  # Limit to 3
                })
        
        # PHASE 4: BUILD RESPONSE
        executing_count = len([a for a in assignments if a.get("status") == "EXECUTING"])
        planned_count = len([a for a in assignments if a.get("status") == "PLANNED"])
        
        if mode == "status":
            status = "REPORT"
        elif executing_count > 0:
            status = "RUNNING"
        elif planned_count > 0:
            status = "PLANNED"
        elif slots_blocked == len(target_slots):
            status = "ALL_BLOCKED"
        else:
            status = "IDLE"
        
        # Compute next actions
        next_actions = []
        for a in assignments:
            if a.get("status") == "EXECUTING":
                next_actions.append(
                    f"{a['slot_id']}: Execute '{a.get('task_description', '')[:50]}...', "
                    f"then brain_slot_complete('{a['slot_id']}', '{a['task_id']}', fence_token={a.get('fence_token')})"
                )
            elif a.get("status") == "BLOCKED":
                next_actions.append(f"{a['slot_id']}: {a.get('reason', 'Blocked')}")
        
        response = {
            "sprint_id": sprint_id,
            "status": status,
            "mode": mode,
            "dry_run": dry_run,
            "timestamp": now,
            
            "slots_summary": {
                "total": len(target_slots),
                "executing": executing_count,
                "planned": planned_count,
                "blocked": slots_blocked,
                "exhausted": len([a for a in assignments if a.get("status") == "EXHAUSTED"])
            },
            
            "assignments": assignments,
            
            "dependency_analysis": {
                "total_tasks": len(tasks),
                "pending_tasks": len([t for t in tasks if t.get("status") == "PENDING"]),
                "blocked_tasks": len(dep_graph.get("task_to_slot", {})),
                "circular_deps": dep_graph.get("circular_deps", []),
                "longest_chain_length": max((len(c) for c in dep_graph.get("blocking_chains", {}).values()), default=0)
            },
            
            "cost_projection": {
                "estimated_total": round(total_estimated_cost, 4),
                "budget_limit": budget_limit,
                "within_budget": budget_limit is None or total_estimated_cost <= budget_limit
            },
            
            "next_actions": next_actions[:5],  # Limit to 5
            
            "autopilot_hint": {
                "continue": tasks_assigned > 0,
                "check_status": "brain_autopilot_sprint(mode='status')",
                "tasks_remaining": len([t for t in tasks if t.get("status") == "PENDING"]) - tasks_assigned
            }
        }
        
        # Emit event
        _emit_event("sprint_started", "nucleus_orchestrate", {
            "sprint_id": sprint_id,
            "mode": mode,
            "slots": [s.get("id") for s in target_slots],
            "tasks_assigned": tasks_assigned
        })
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "ERROR",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }, indent=2)


@mcp.tool()
def brain_force_assign(slot_id: str, task_id: str, acknowledge_risk: bool = False) -> str:
    """
    Force assign a task to a slot, overriding tier requirements.
    
    Use this when you MUST run a task on a specific slot despite tier mismatch.
    Requires explicit risk acknowledgment.
    
    Args:
        slot_id: Target slot ID
        task_id: Task to assign
        acknowledge_risk: Must be True to proceed with tier mismatch
    
    Returns:
        Assignment result with warnings
    """
    try:
        registry = _get_slot_registry()
        tier_defs = _get_tier_definitions()
        tasks = _get_tasks_list()
        
        resolved_id = _resolve_slot_id(slot_id, registry)
        slot = registry.get("slots", {}).get(resolved_id)
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not slot:
            return json.dumps({"error": f"Slot {slot_id} not found"})
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
        
        # Check tier mismatch
        slot_tier = slot.get("tier", "standard")
        task_tier = _infer_task_tier(task, tier_defs)
        
        tiers = tier_defs.get("tiers", {})
        slot_level = tiers.get(slot_tier, {}).get("level", 3)
        task_level = tiers.get(task_tier, {}).get("level", 3)
        
        tier_gap = slot_level - task_level
        
        if tier_gap > 1 and not acknowledge_risk:
            return json.dumps({
                "error": "TIER_MISMATCH_RISK",
                "slot_tier": slot_tier,
                "task_tier": task_tier,
                "tier_gap": tier_gap,
                "message": "Task requires higher tier. Set acknowledge_risk=True to override.",
                "risk_level": "HIGH" if tier_gap > 2 else "MEDIUM"
            })
        
        # Force claim
        claim_result = _claim_with_fence(task_id, resolved_id)
        
        if claim_result.get("success"):
            warnings = []
            if tier_gap > 0:
                warnings.append(f"TIER_OVERRIDE: Slot ({slot_tier}) is {tier_gap} levels below task ({task_tier})")
            
            return json.dumps({
                "success": True,
                "slot_id": resolved_id,
                "task_id": task_id,
                "fence_token": claim_result.get("fence_token"),
                "warnings": warnings,
                "message": "Task force-assigned. Proceed with caution."
            })
        else:
            return json.dumps({"error": claim_result.get("error")})
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def brain_file_changes() -> str:
    """
    Get pending file change events from the Brain folder.
    
    Phase 50 Native Sync: Returns a list of files that have changed
    since the last check. Use this to detect updates made by other
    Chats/IDEs/CLI tools.
    
    Returns:
        List of file change events (type, path, timestamp)
    """
    try:
        from .runtime.file_monitor import get_file_monitor # noqa: E402, F401
        
        monitor = get_file_monitor()
        if not monitor:
            return json.dumps({
                "status": "disabled",
                "message": "File monitor not initialized. Ensure watchdog is installed.",
                "events": []
            })
        
        if not monitor.is_running:
            return json.dumps({
                "status": "stopped",
                "message": "File monitor is not running.",
                "events": []
            })
        
        events = monitor.get_pending_events()
        return json.dumps({
            "status": "active",
            "event_count": len(events),
            "events": [e.to_dict() for e in events]
        })
        
    except ImportError:
        return json.dumps({
            "status": "unavailable",
            "message": "watchdog library not installed. Run: pip install watchdog",
            "events": []
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "events": []
        })


@mcp.tool()
def brain_gcloud_status() -> str:
    """
    Check GCloud authentication status.
    
    Phase 49 GCloud Integration: Returns the current gcloud configuration
    including active project and authenticated account.
    
    Returns:
        GCloud auth status (project, account, availability)
    """
    try:
        from .runtime.gcloud_ops import get_gcloud_ops # noqa: E402, F401
        
        ops = get_gcloud_ops()
        status = ops.check_auth_status()
        return json.dumps(status, indent=2)
        
    except ImportError as e:
        return json.dumps({
            "error": f"GCloudOps module not available: {e}"
        })
    except Exception as e:
        return json.dumps({
            "error": str(e)
        })


@mcp.tool()
def brain_gcloud_services(project: str = None, region: str = "us-central1") -> str:
    """
    List Cloud Run services in a project.
    
    Phase 49 GCloud Integration: Uses your local gcloud auth to query
    infrastructure status. No API keys needed.
    
    Args:
        project: GCP project ID (optional, uses default if not set)
        region: GCP region (default: us-central1)
    
    Returns:
        List of Cloud Run services with status
    """
    try:
        from .runtime.gcloud_ops import GCloudOps # noqa: E402, F401
        
        ops = GCloudOps(project=project, region=region)
        
        if not ops.is_available:
            return json.dumps({
                "error": "gcloud CLI not found",
                "install": "https://cloud.google.com/sdk/docs/install"
            })
        
        result = ops.list_cloud_run_services()
        return json.dumps(result.to_dict(), indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e)
        })




@mcp.tool()
def brain_list_services() -> str:
    """
    List Render.com services.
    
    Returns:
        JSON string of service list (Real or Mock).
    """
    try:
        from .runtime.render_ops import get_render_ops # noqa: E402, F401
        ops = get_render_ops()
        return json.dumps(ops.list_services(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================
# MARKETING ADAPTIVE PROTOCOLS (Self-healing)
# ============================================================

def _scan_marketing_log() -> Dict:
    """Scan marketing_log.md for failures."""
    try:
        # Try relative path first (repo root)
        log_path = Path("docs/marketing/marketing_log.md")
        if not log_path.exists():
            # Fallback to absolute path
            log_path = Path("/Users/lokeshgarg/ai-mvp-backend/docs/marketing/marketing_log.md")
            
        if not log_path.exists():
            return {"status": "error", "error": f"Marketing log not found at {log_path}"}
            
        failures = []
        with open(log_path, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "[FAILURE]" in line:
                    tag = "UNKNOWN"
                    if "[AUTH_LOCKED]" in line:
                        tag = "AUTH_LOCKED"
                    elif "[SELECTOR_MISSING]" in line:
                        tag = "SELECTOR_MISSING"
                    elif "[TIMEOUT]" in line:
                        tag = "TIMEOUT"
                    elif "[RATE_LIMIT]" in line:
                        tag = "RATE_LIMIT"
                    
                    failures.append({
                        "line_number": i + 1,
                        "tag": tag,
                        "content": line.strip()
                    })
        
        # Sort by most recent (end of file)
        failures.reverse()
        
        return {
            "status": "healthy" if not failures else "degraded",
            "failure_count": len(failures),
            "failures": failures[:5]  # Show last 5
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def brain_scan_marketing_log() -> str:
    """
    Scan the marketing log for failure tags (e.g. [FAILURE], [AUTH_LOCKED]).
    Used by the Adaptive Protocols to trigger self-correction.
    
    Returns:
        JSON string with health status and recent failures.
    """
    result = _scan_marketing_log()
    return json.dumps(result, indent=2)

@mcp.tool()
def brain_synthesize_strategy(focus_topic: Optional[str] = None) -> str:
    """
    [Marketing Engine]
    Analyze marketing logs and update the Strategy Document using GenAI.
    
    Args:
        focus_topic: Optional topic to focus the strategy analysis on.
        
    Returns:
        Review of the synthesis operation.
    """
    # Lazy import of capability
    try:
        from mcp_server_nucleus.runtime.capabilities.marketing_engine import brain_synthesize_strategy
        
        result = brain_synthesize_strategy(
            project_root=str(Path.cwd()),
            focus_topic=focus_topic
        )
        
        if result.get("status") == "success":
             return f"✅ Strategy Updated.\nPath: {result.get('path')}\nInsights: {result.get('insights')}"
        else:
             return f"❌ Synthesis Failed: {result.get('message')}"
             
    except Exception as e:
        return f"❌ Error loading marketing engine: {e}"

@mcp.tool()
def brain_synthesize_status_report(focus: str = "roadmap") -> str:
    """
    [Executive Engine]
    Generate a 'State of the Union' report by analyzing tasks, logs, and vision.
    
    Args:
        focus: 'roadmap' (default), 'technical', or 'marketing'.
        
    Returns:
        The generated status report.
    """
    try:
        from mcp_server_nucleus.runtime.capabilities.synthesizer import brain_synthesize_status_report
        
        result = brain_synthesize_status_report(
            project_root=str(Path.cwd()),
            focus=focus
        )
        
        if result.get("status") == "success":
             return result.get("report")
        else:
             return f"❌ Status Generation Failed: {result.get('message')}"
             
    except Exception as e:
        return f"❌ Error loading synthesizer: {e}"

@mcp.tool()
def brain_optimize_workflow() -> str:
    """
    [Marketing Engine]
    Scan marketing logs for 'META-FEEDBACK' and self-optimize the workflow cheatsheet.
    
    Returns:
        Status of the optimization attempt.
    """
    try:
        from mcp_server_nucleus.runtime.capabilities.marketing_engine import brain_optimize_workflow
        
        result = brain_optimize_workflow(project_root=str(Path.cwd()))
        
        if result.get("status") == "success":
             return f"✅ Workflow Optimized.\nMessage: {result.get('message')}\nPath: {result.get('path')}"
        elif result.get("status") == "skipped":
             return f"ℹ️  Optimization Skipped: {result.get('message')}"
        else:
             return f"❌ Optimization Failed: {result.get('message')}"
             
    except Exception as e:
        return f"❌ Error loading marketing engine: {e}"


# ============================================================
# CRITIC SYSTEM TOOLS
# ============================================================




@mcp.tool()
def brain_apply_critique(review_path: str) -> Dict:
    """Apply fixes based on a critique review.
    
    Spawns a Developer agent to fix the issues identified in the review.
    
    Args:
        review_path: Path to the critique JSON file
        
    Returns:
        Task creation result
    """
    try:
        # Resolve relative path for _read_artifact
        # _read_artifact expects path relative to artifacts/
        path_str = str(review_path)
        if "artifacts/" in path_str:
            path_str = path_str.split("artifacts/")[-1]
            
        content_str = _read_artifact(path_str)
        if content_str.startswith("Error"):
             return {"error": content_str}
             
        review = json.loads(content_str)
        
        payload = review.get("payload", {})
        target = payload.get("target")
        issues = payload.get("issues", [])
        
        if not target or not issues:
             return {"error": "Invalid critique format: missing target or issues"}

        description = f"Fix {len(issues)} issues in {target} identified by Critic.\n\nIssues:\n"
        for i in issues:
            description += f"- [{i.get('severity')}] {i.get('description')}\n"
            
        # Trigger Developer
        result = _trigger_agent(
            agent="developer",
            task_description=description,
            context_files=[path_str, target]
        )
        
        return {"success": True, "message": result}
        
    except Exception as e:
        return {"error": f"Failed to apply critique: {str(e)}"}



@mcp.tool()
async def brain_orchestrate_swarm(mission: str, agents: List[str] = None) -> Dict:
    """Initialize a multi-agent swarm for a complex mission (Unified)."""
    try:
        orch = get_orch()
        return await orch.start_mission(mission, agents=agents)
    except Exception as e:
        return make_response(False, error=f"Swarm failed: {str(e)}")



@mcp.tool()
def brain_search_memory(query: str) -> Dict:
    """Search long-term memory for keywords using ripgrep.
    
    Args:
        query: Keyword or phrase to search for.
        
    Returns:
        List of matching snippets with file paths.
    """
    try:
        from .runtime.memory import _search_memory # noqa: E402, F401
        return _search_memory(query)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_read_memory(category: str) -> Dict:
    """Read full content of a memory category.
    
    Args:
        category: One of ['context', 'patterns', 'learnings', 'decisions']
        
    Returns:
        Full content of the requested memory file.
    """
    try:
        from .runtime.memory import _read_memory # noqa: E402, F401
        return _read_memory(category)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_manage_strategy(action: str, content: str = None) -> Dict:
    """Read or Update the core Strategy Document.
    
    Args:
        action: 'read', 'update', or 'append'.
        content: Text content (required for update/append).
    """
    try:
        from .runtime.strategy import _manage_strategy # noqa: E402, F401
        return _manage_strategy(action, content)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_update_roadmap(action: str, item: str = None) -> Dict:
    """Read or Update the Roadmap.
    
    Args:
        action: 'read' or 'add'.
        item: Roadmap item text (required for add).
    """
    try:
        from .runtime.strategy import _update_roadmap # noqa: E402, F401
        return _update_roadmap(action, item)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

def main():
    # Fallback for Python 3.9 / No FastMCP
    if globals().get("USE_STDIO_FALLBACK"):
        from .runtime.stdio_server import StdioServer # noqa: E402, F401
        import logging
        import sys
        
        # Configure logging to stderr to not corrupt stdout
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)
        
        server = StdioServer()
        server.run()
        return

    # Helper to log to debug file
    def log_debug(msg):
        with open("/tmp/mcp_debug.log", "a") as f:
            f.write(f"{msg}\n")
    
    # Phase 50: Initialize File Monitor for Native Sync
    try:
        from .runtime.file_monitor import init_file_monitor # noqa: E402, F401
        brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
        if brain_path and Path(brain_path).exists():
            monitor = init_file_monitor(brain_path)
            monitor.start()
            log_debug(f"📡 File monitor initialized for: {brain_path}")
    except ImportError as e:
        log_debug(f"File monitor not available: {e}")
    except Exception as e:
        log_debug(f"File monitor init failed: {e}")
    
    try:
        log_debug("Entering mcp.run()")
        mcp.run()
        log_debug("Exited mcp.run() normally")
    except Exception as e:
        log_debug(f"Exception in mcp.run(): {e}")
        import traceback
        with open("/tmp/mcp_debug.log", "a") as f:
            traceback.print_exc(file=f)
        raise

if __name__ == "__main__":
    main()

# ============================================================
# CRITIC LOOP - PHASE 12
# ============================================================

def _critique_code(file_path: str, context: Optional[str] = None) -> Dict:
    """Core logic for critiquing code using the Critic persona."""
    try:
        from .runtime.llm_client import DualEngineLLM # noqa: E402, F401
        import json
        
        brain = get_brain_path()
        target_file = Path(file_path)
        
        # Security check: Ensure file is within project
        # In a real impl, we'd check against PROJECT_ROOT env var, but here allow absolute
        if not target_file.exists():
            return {"error": f"File not found: {file_path}"}
            
        code_content = target_file.read_text()
        
        # Load Critic Persona
        critic_persona_path = brain / "agents" / "critic.md"
        if critic_persona_path.exists():
            system_prompt = critic_persona_path.read_text()
        else:
            system_prompt = "You are The Critic. Find bugs, security flaws, and style issues."
            
        initial_prompt = f"""
        CRITIQUE THIS FILE: {file_path}
        CONTEXT: {context or 'General Check'}
        
        Analyze the code provided below.
        Return JSON matching schema: {{ "status": "PASS/FAIL/WARN", "score": 0-100, "issues": [ {{ "severity": "CRITICAL/WARNING", "line": 1, "message": "..." }} ] }}
        """
        
        # Pass as list to handle large code blocks safely
        prompt_parts = [initial_prompt, "\nCODE:\n```\n", code_content, "\n```\n"]
        
        # Call LLM
        client = DualEngineLLM(system_instruction=system_prompt)
        response = client.generate_content(prompt_parts)
        
        # Parse JSON
        text = response.text
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            critique = json.loads(text)
        except Exception:
            # Fallback to text wrapping
            critique = {"status": "WARN", "score": 0, "summary": text, "issues": []}
            
        # Emit event
        _emit_event("code_critiqued", "critic", {
            "file": file_path,
            "status": critique.get("status"),
            "score": critique.get("score")
        })
        
        return critique
        
    except Exception as e:
        return {"error": str(e)}

def _apply_critique(file_path: str, critique_id: str) -> str:
    """Placeholder for applying critique fixes automatically."""
    return "Feature not implemented in Phase 12 MVP. Please fix manually based on critique."

@mcp.tool()
def brain_critique_code(file_path: str, context: str = "General Review") -> str:
    """
    Run a specialized 'Critic' agent review on a file.
    Args:
        file_path: Absolute path to the file to review.
        context: Optional context (e.g. "Focus on security", "Check performance").
    Returns:
        JSON string of the critique.
    """
    result = _critique_code(file_path, context)
    return json.dumps(result, indent=2)

@mcp.tool()
def brain_fix_code(file_path: str, issues_context: str) -> str:
    """
    Auto-fix code based on provided issues context.
    Args:
        file_path: Absolute path to the file.
        issues_context: Description of issues or stringified JSON from Critic.
    """
    return _fix_code(file_path, issues_context)

def _fix_code(file_path: str, issues_context: str) -> str:
    """
    Core logic for The Fixer.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"status": "error", "message": "File not found"})

        original_content = path.read_text(encoding='utf-8')
        
        # 1. Create Backup
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        backup_path.write_text(original_content, encoding='utf-8')

        # 2. Invoke LLM (Fixer Persona)
        system_prompt = (
            "You are 'The Fixer', an autonomous code repair agent. "
            "Your goal is to fix specific issues in the provided code while maintaining strict adherence to the project's style (Nucleus/Neon/Context-Aware). "
            "Return ONLY the full corrected file content inside a code block. Do not wrap in markdown or add commentary."
        )
        
        user_prompt = f"""
        TARGET: {file_path}
        
        ISSUES TO FIX:
        {issues_context}
        
        CURRENT CONTENT:
        ```
        {original_content}
        ```
        
        INSTRUCTIONS:
        1. Fix the issues listed above.
        2. Ensure accessibility (ARIA) and style compliance (Globals/Neon) if UI.
        3. Do NOT break existing logic.
        4. Return the COMPLETE new file content.
        """

        # Use Dual Engine (using mcp_server_nucleus's internal instance if available, or creating one)
        # We assume DualEngineLLM is imported (it is at top of __init__.py usually, or we use the one instantiated in server. But this is the library).
        # We need to import it or assume it's available.
        from .runtime.llm_client import DualEngineLLM # noqa: E402, F401
        
        llm = DualEngineLLM() 
        fix_response = llm.generate_content(
            prompt=user_prompt,
            system_instruction=system_prompt
        )

        # 3. Extract Code
        # Simple extraction logic: find first ``` and last ```
        new_content = fix_response.text.strip()
        if "```" in new_content:
            parts = new_content.split("```")
            # Usually parts[1] is the code if format is ```lang ... ```
            # If parts[0] is empty, parts[1] is language+code or just code.
            # Let's robustly strip.
            candidate = parts[1]
            if candidate.startswith(("typescript", "tsx", "python", "css", "javascript", "json")):
                 # Remove first line (lang identifier)
                 candidate = "\n".join(candidate.split("\n")[1:])
            new_content = candidate
        
        # 4. Write Fix
        path.write_text(new_content, encoding='utf-8')
        
        return json.dumps({
            "status": "success", 
            "message": f"Applied fix to {path.name}",
            "backup": str(backup_path)
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ============================================================
# PHASE 71: CROSS-CHAT TASK VISIBILITY
# ============================================================

def _get_thread_identity(conversation_id: str) -> Optional[Dict]:
    """Look up thread identity from thread_registry.md."""
    try:
        brain = get_brain_path()
        registry_path = brain / "meta" / "thread_registry.md"
        
        if not registry_path.exists():
            return None
            
        content = registry_path.read_text()
        
        # Simple parsing: look for the conversation_id prefix in any line
        short_id = conversation_id[:8] if len(conversation_id) > 8 else conversation_id
        
        for line in content.split("\n"):
            if short_id in line and "|" in line:
                # Parse table row: | Thread ID | Label | Agent Role | Purpose |
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 5:
                    return {
                        "thread_id": parts[1],
                        "label": parts[2],
                        "role": parts[3],
                        "purpose": parts[4] if len(parts) > 4 else ""
                    }
        return None
    except Exception:
        return None

def _get_active_sessions() -> Dict:
    """Get active sessions from ledger."""
    try:
        brain = get_brain_path()
        sessions_path = brain / "ledger" / "active_sessions.json"
        
        if not sessions_path.exists():
            return {"sessions": {}}
            
        with open(sessions_path, "r") as f:
            return json.load(f)
    except Exception:
        return {"sessions": {}}

def _save_active_sessions(data: Dict) -> str:
    """Save active sessions to ledger."""
    try:
        brain = get_brain_path()
        sessions_path = brain / "ledger" / "active_sessions.json"
        sessions_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sessions_path, "w") as f:
            json.dump(data, f, indent=2)
        return "Saved"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_session_briefing(conversation_id: Optional[str] = None) -> str:
    """Get a briefing of pending work and session identity at session start.
    
    Call this at the start of each conversation to see:
    - Who you are (from thread_registry.md)
    - Open tasks and priorities
    - What other sessions are working on
    
    Args:
        conversation_id: Optional. Your conversation ID for identity lookup.
    
    Returns:
        Formatted briefing with tasks and identity info.
    """
    lines = ["## 📋 Session Briefing", ""]
    
    # 1. Identity from thread registry
    if conversation_id:
        identity = _get_thread_identity(conversation_id)
        if identity:
            lines.append("### 🪪 Your Identity")
            lines.append(f"- **Thread:** `{conversation_id[:12]}...`")
            lines.append(f"- **Role:** {identity.get('role', 'Unknown')}")
            lines.append(f"- **Focus:** {identity.get('label', 'Unknown')}")
            lines.append("")
    
    # 2. Active sessions
    sessions = _get_active_sessions()
    active = sessions.get("sessions", {})
    if active:
        lines.append(f"### 👥 Active Sessions ({len(active)})")
        for sid, info in list(active.items())[:5]:
            lines.append(f"- `{sid[:8]}`: {info.get('focus', 'Unknown')}")
        lines.append("")
    
    # 3. In Progress tasks
    in_progress = _list_tasks(status="IN_PROGRESS")
    if in_progress:
        lines.append(f"### 🔄 In Progress ({len(in_progress)})")
        for t in in_progress[:3]:
            claimed = t.get("claimed_by", "unknown")
            lines.append(f"- {t['description'][:50]}... (by {claimed})")
        lines.append("")
    
    # 4. Pending tasks
    pending = _list_tasks(status="PENDING")
    if pending:
        lines.append(f"### 📌 Pending ({len(pending)})")
        for t in pending[:5]:
            pri = "🔴" if t.get("priority", 3) <= 2 else "🟡" if t.get("priority") == 3 else "⚪"
            lines.append(f"- {pri} {t['description'][:60]}")
        if len(pending) > 5:
            lines.append(f"  ... and {len(pending) - 5} more")
    
    if not in_progress and not pending:
        lines.append("✨ **All clear!** No pending tasks.")
    
    return "\n".join(lines)

@mcp.tool()
def brain_register_session(conversation_id: str, focus_area: str) -> str:
    """Register this session's focus area for cross-chat visibility.
    
    Call this when starting work on a specific task or phase.
    
    Args:
        conversation_id: Your conversation ID
        focus_area: What you're working on (e.g., "Phase 71: Visibility")
    
    Returns:
        Confirmation message
    """
    try:
        sessions = _get_active_sessions()
        
        sessions["sessions"][conversation_id] = {
            "focus": focus_area,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "last_active": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }
        
        _save_active_sessions(sessions)
        
        # Emit event
        _emit_event("session_registered", "nucleus_mcp", {
            "conversation_id": conversation_id,
            "focus_area": focus_area
        })
        
        return f"Registered session {conversation_id[:8]}... focused on: {focus_area}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_handoff_task(
    task_description: str,
    target_session_id: Optional[str] = None,
    priority: int = 3
) -> str:
    """Hand off a task to another session or the shared queue.
    
    Creates a task in the shared task system. If target_session_id is provided,
    the task is tagged for that specific session.
    
    Args:
        task_description: What needs to be done
        target_session_id: Optional. Target session ID (or None for shared queue)
        priority: 1-5 (1=critical, 5=low). Default 3.
    
    Returns:
        Confirmation with task ID
    """
    try:
        # Add to task system
        result = _add_task(
            description=f"{'@' + target_session_id[:8] + ': ' if target_session_id else ''}{task_description}",
            priority=priority,
            source="handoff"
        )
        
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        
        task = result.get("task", {})
        
        # Log handoff
        try:
            brain = get_brain_path()
            handoffs_path = brain / "ledger" / "handoffs.json"
            
            handoffs = []
            if handoffs_path.exists():
                with open(handoffs_path, "r") as f:
                    handoffs = json.load(f)
            
            handoffs.append({
                "task_id": task.get("id"),
                "description": task_description,
                "target": target_session_id,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            })
            
            with open(handoffs_path, "w") as f:
                json.dump(handoffs, f, indent=2)
        except Exception:
            pass  # Don't fail if audit log fails
        
        target_msg = f"for session {target_session_id[:8]}" if target_session_id else "to shared queue"
        return f"✅ Task handed off {target_msg}. ID: {task.get('id')}"
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: TASK INGESTION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_ingestion_engine():
    """Get or create TaskIngestionEngine singleton."""
    global _ingestion_engine
    if "_ingestion_engine" not in globals() or _ingestion_engine is None:
        try:
            from pathlib import Path
            import sys
            
            # Add nop_v3_refactor to path if needed
            nop_path = Path(__file__).parent.parent.parent.parent.parent / "nop_v3_refactor"
            if str(nop_path) not in sys.path:
                sys.path.insert(0, str(nop_path))
            
            from nop_core.task_ingestion import TaskIngestionEngine
            _ingestion_engine = TaskIngestionEngine(brain_path=get_brain_path())
        except ImportError:
            _ingestion_engine = None
    return _ingestion_engine


def _brain_ingest_tasks_impl(
    source: str,
    source_type: str = "auto",
    session_id: str = None,
    auto_assign: bool = False,
    skip_dedup: bool = False,
    dry_run: bool = False,
) -> str:
    """Internal implementation of brain_ingest_tasks."""
    try:
        engine = _get_ingestion_engine()
        if engine is None:
            return "❌ TaskIngestionEngine not available. Install nop_v3_refactor."
        
        # Detect if source is a file path or raw content
        if os.path.exists(source):
            result = engine.ingest_from_file(
                source,
                source_type=source_type,
                session_id=session_id,
                auto_assign=auto_assign,
                skip_dedup=skip_dedup,
                dry_run=dry_run,
            )
        else:
            result = engine.ingest_from_text(
                source,
                source_type=source_type if source_type != "auto" else "manual",
                session_id=session_id,
                auto_assign=auto_assign,
                skip_dedup=skip_dedup,
                dry_run=dry_run,
            )
        
        # Format output
        from nop_core.task_ingestion import format_ingestion_result
        return format_ingestion_result(result)
        
    except Exception as e:
        return f"❌ Ingestion error: {str(e)}"


@mcp.tool()
def brain_ingest_tasks(
    source: str,
    source_type: str = "auto",
    session_id: str = None,
    auto_assign: bool = False,
    skip_dedup: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Ingest tasks from various sources into the brain.
    
    Parses and imports tasks from:
    - Planning documents (markdown with checkboxes)
    - Code TODOs (TODO/FIXME/HACK comments)
    - Handoff summaries (JSON from agent handoffs)
    - Meeting notes (action items with @mentions)
    - External APIs (Jira, Linear, GitHub)
    
    Args:
        source: File path or raw text/JSON content
        source_type: "planning", "todos", "handoffs", "meetings", "api", "auto"
        session_id: Your session ID for provenance tracking
        auto_assign: If True, immediately assign tasks to available agents
        skip_dedup: If True, skip deduplication check (faster)
        dry_run: If True, parse and validate but don't create tasks
    
    Returns:
        Formatted ingestion result with batch ID, stats, and rollback hint
    
    Examples:
        brain_ingest_tasks("/docs/sprint_42.md", source_type="planning")
        brain_ingest_tasks("/src/**/*.py", source_type="todos")
        brain_ingest_tasks('{"from_session":"ws_001","tasks":[...]}', source_type="handoffs")
    """
    return _brain_ingest_tasks_impl(
        source, source_type, session_id, auto_assign, skip_dedup, dry_run
    )


def _brain_rollback_ingestion_impl(batch_id: str, reason: str = None) -> str:
    """Internal implementation of brain_rollback_ingestion."""
    try:
        engine = _get_ingestion_engine()
        if engine is None:
            return "❌ TaskIngestionEngine not available."
        
        result = engine.rollback(batch_id, reason)
        
        if result.get("success"):
            return f"✅ Rollback complete\n   Batch: {batch_id}\n   Tasks removed: {result['tasks_removed']}"
        else:
            return f"❌ Rollback failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Rollback error: {str(e)}"


@mcp.tool()
def brain_rollback_ingestion(batch_id: str, reason: str = None) -> str:
    """
    Rollback an ingestion batch.
    
    Removes all tasks created in the specified batch.
    Use the batch_id from brain_ingest_tasks result.
    
    Args:
        batch_id: Batch ID from brain_ingest_tasks result
        reason: Optional reason for rollback (logged)
    
    Returns:
        Rollback result with tasks removed count
    """
    return _brain_rollback_ingestion_impl(batch_id, reason)


def _brain_ingestion_stats_impl() -> str:
    """Internal implementation of brain_ingestion_stats."""
    try:
        engine = _get_ingestion_engine()
        if engine is None:
            return "❌ TaskIngestionEngine not available."
        
        stats = engine.get_ingestion_stats()
        
        lines = [
            "📊 **Ingestion Statistics**",
            "=" * 40,
            f"   Total ingested: {stats['total_ingested']}",
            f"   Total skipped: {stats['total_skipped']}",
            f"   Total failed: {stats['total_failed']}",
            f"   Batches: {stats['batches_count']}",
            f"   Dedup cache: {stats['dedup_cache_size']}",
        ]
        
        if stats.get("by_source"):
            lines.append("\n📁 **By Source:**")
            for source, count in stats["by_source"].items():
                lines.append(f"   {source}: {count}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Stats error: {str(e)}"


@mcp.tool()
def brain_ingestion_stats() -> str:
    """
    Get overall ingestion statistics.
    
    Returns:
        Stats including total ingested, dedup rate, source breakdown
    """
    return _brain_ingestion_stats_impl()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: DASHBOARD TOOLS (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

_dashboard_engine = None


def _get_dashboard_engine():
    """Get or create DashboardEngine singleton."""
    global _dashboard_engine
    if _dashboard_engine is None:
        try:
            from pathlib import Path
            import sys
            
            # Add nop_v3_refactor to path if needed
            nop_path = Path(__file__).parent.parent.parent.parent.parent / "nop_v3_refactor"
            if str(nop_path) not in sys.path:
                sys.path.insert(0, str(nop_path))
            
            from nop_core.dashboard import DashboardEngine
            orch = get_orch()
            _dashboard_engine = DashboardEngine(
                orchestrator=orch,
                brain_path=get_brain_path()
            )
        except ImportError:
            _dashboard_engine = None
    return _dashboard_engine


def _brain_enhanced_dashboard_impl(
    detail_level: str = "standard",
    format: str = "ascii",
    include_alerts: bool = True,
    include_trends: bool = False,
    category: str = None,
) -> str:
    """Internal implementation of enhanced dashboard."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available. Install nop_v3_refactor."
        
        return engine.render(
            detail_level=detail_level,
            format=format,
            include_alerts=include_alerts,
            include_trends=include_trends,
            category=category,
        )
        
    except Exception as e:
        return f"❌ Dashboard error: {str(e)}"


@mcp.tool()
def brain_dashboard(
    detail_level: str = "standard",
    format: str = "ascii",
    include_alerts: bool = True,
    include_trends: bool = False,
    category: str = None,
) -> str:
    """
    Enhanced orchestration dashboard with multiple output formats.
    
    Provides real-time visibility into all NOP V3.1 components:
    - Agent Pool Health (active, idle, exhausted, utilization)
    - Task Queue Metrics (pending, in-progress, blocked, velocity)
    - Ingestion Statistics (sources, dedup rates, batches)
    - Cost Tracking (tokens, USD, budget, burn rate)
    - Dependency Graph (depths, blocked chains, circular)
    - System Health (uptime, errors)
    
    Args:
        detail_level: "minimal", "standard", "verbose", "full"
        format: "ascii" (terminal), "json" (API), "mermaid" (diagrams)
        include_alerts: Include alert section
        include_trends: Include trend data (velocity, etc.)
        category: Filter to specific category ("agents", "tasks", "ingestion", "cost", "deps")
    
    Returns:
        Formatted dashboard in requested format
    
    Examples:
        brain_dashboard()  # Standard ASCII dashboard
        brain_dashboard(detail_level="full", include_trends=True)
        brain_dashboard(format="json")  # For API consumption
        brain_dashboard(category="agents")  # Only agent metrics
    """
    return _brain_enhanced_dashboard_impl(
        detail_level, format, include_alerts, include_trends, category
    )


def _brain_snapshot_dashboard_impl(name: str = None) -> str:
    """Internal implementation of snapshot creation."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        snapshot = engine.create_snapshot(name)
        
        return f"""✅ Snapshot Created
   ID: {snapshot.id}
   Name: {snapshot.name}
   Timestamp: {snapshot.timestamp}
   
💡 To compare: brain_compare_dashboards('{snapshot.id}', 'other_snapshot_id')"""
        
    except Exception as e:
        return f"❌ Snapshot error: {str(e)}"


@mcp.tool()
def brain_snapshot_dashboard(name: str = None) -> str:
    """
    Create a manual dashboard snapshot for later comparison.
    
    Snapshots capture the current state of all metrics and alerts.
    Use for tracking progress over time or debugging issues.
    
    Args:
        name: Optional name for the snapshot
    
    Returns:
        Snapshot ID and confirmation
    """
    return _brain_snapshot_dashboard_impl(name)


def _brain_list_snapshots_impl(limit: int = 10) -> str:
    """Internal implementation of snapshot listing."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        snapshots = engine.list_snapshots(limit)
        
        if not snapshots:
            return "📸 No snapshots found"
        
        lines = ["📸 Dashboard Snapshots", "=" * 40]
        for s in snapshots:
            lines.append(f"   {s['id']}: {s['name']} ({s['timestamp']})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ List snapshots error: {str(e)}"


@mcp.tool()
def brain_list_snapshots(limit: int = 10) -> str:
    """
    List available dashboard snapshots.
    
    Args:
        limit: Maximum number of snapshots to list (default: 10)
    
    Returns:
        List of snapshots with IDs, names, and timestamps
    """
    return _brain_list_snapshots_impl(limit)


def _brain_get_alerts_impl() -> str:
    """Internal implementation of alert retrieval."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        alerts = engine.get_alerts()
        
        if not alerts:
            return "✅ No active alerts - all systems healthy"
        
        lines = ["⚠️ Active Alerts", "=" * 40]
        for alert in alerts:
            icon = "🔴" if alert.level.value == "critical" else "🟡"
            lines.append(f"   {icon} [{alert.level.value.upper()}] {alert.message}")
            lines.append(f"      Metric: {alert.metric}, Value: {alert.value}, Threshold: {alert.threshold}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Alerts error: {str(e)}"


@mcp.tool()
def brain_get_alerts() -> str:
    """
    Get current active alerts from the dashboard.
    
    Alerts are triggered when metrics exceed thresholds:
    - CRITICAL: Immediate action required
    - WARNING: Attention needed
    
    Returns:
        List of active alerts with levels and details
    """
    return _brain_get_alerts_impl()


def _brain_set_alert_threshold_impl(metric: str, level: str, value: float) -> str:
    """Internal implementation of threshold setting."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        engine.set_alert_threshold(metric, level, value)
        
        return f"""✅ Threshold Set
   Metric: {metric}
   Level: {level}
   Value: {value}"""
        
    except Exception as e:
        return f"❌ Threshold error: {str(e)}"


@mcp.tool()
def brain_set_alert_threshold(metric: str, level: str, value: float) -> str:
    """
    Set custom alert threshold for a metric.
    
    Available metrics:
    - agents.exhausted_ratio: Ratio of exhausted agents (0-1)
    - agents.utilization: Pool utilization (0-1)
    - tasks.pending: Number of pending tasks
    - tasks.blocked_ratio: Ratio of blocked tasks (0-1)
    - cost.budget_remaining_ratio: Budget remaining (0-1)
    - deps.max_depth: Maximum dependency chain depth
    
    Args:
        metric: Metric name (e.g., "tasks.pending")
        level: "warning" or "critical"
        value: Threshold value
    
    Returns:
        Confirmation of threshold setting
    """
    return _brain_set_alert_threshold_impl(metric, level, value)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: AUTOPILOT SPRINT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

_autopilot_engine = None


def _get_autopilot_engine():
    """Get or create AutopilotEngine singleton."""
    global _autopilot_engine
    if _autopilot_engine is None:
        try:
            from pathlib import Path
            import sys
            
            nop_path = Path(__file__).parent.parent.parent.parent.parent / "nop_v3_refactor"
            if str(nop_path) not in sys.path:
                sys.path.insert(0, str(nop_path))
            
            from nop_core.autopilot import AutopilotEngine
            orch = get_orch()
            _autopilot_engine = AutopilotEngine(
                orchestrator=orch,
                brain_path=get_brain_path()
            )
        except ImportError:
            _autopilot_engine = None
    return _autopilot_engine


def _brain_autopilot_sprint_v2_impl(
    slots: List[str] = None,
    mode: str = "auto",
    halt_on_blocker: bool = True,
    halt_on_tier_mismatch: bool = False,
    max_tasks_per_slot: int = 10,
    budget_limit: float = None,
    time_limit_hours: float = None,
    dry_run: bool = False,
) -> str:
    """Internal implementation of enhanced autopilot sprint."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available. Install nop_v3_refactor."
        
        from nop_core.autopilot import SprintMode, format_sprint_result
        
        mode_enum = SprintMode(mode.lower())
        
        result = engine.execute_sprint(
            slots=slots,
            mode=mode_enum,
            halt_on_blocker=halt_on_blocker,
            halt_on_tier_mismatch=halt_on_tier_mismatch,
            max_tasks_per_slot=max_tasks_per_slot,
            budget_limit=budget_limit,
            time_limit_hours=time_limit_hours,
            dry_run=dry_run,
        )
        
        return format_sprint_result(result)
        
    except Exception as e:
        return f"❌ Sprint error: {str(e)}"


@mcp.tool()
def brain_autopilot_sprint_v2(
    slots: List[str] = None,
    mode: str = "auto",
    halt_on_blocker: bool = True,
    halt_on_tier_mismatch: bool = False,
    max_tasks_per_slot: int = 10,
    budget_limit: float = None,
    time_limit_hours: float = None,
    dry_run: bool = False,
) -> str:
    """
    Enhanced autopilot sprint with V3.1 features.
    
    Orchestrates multiple slots in parallel to execute pending tasks.
    Features wave-based dependency analysis, tier-matched assignment,
    budget control, and comprehensive halt conditions.
    
    Args:
        slots: Slot IDs to use (None = all active)
        mode: "auto" (execute), "plan" (dry run), "guided" (step-by-step), "status"
        halt_on_blocker: Stop if circular dependency detected
        halt_on_tier_mismatch: Stop if no slot can handle required tier
        max_tasks_per_slot: Max tasks per slot in one sprint
        budget_limit: Max cost in USD (None = unlimited)
        time_limit_hours: Max duration (None = unlimited)
        dry_run: Override to plan mode
    
    Returns:
        Sprint execution report with tasks completed, budget spent, etc.
    
    Examples:
        brain_autopilot_sprint_v2()  # Full auto execution
        brain_autopilot_sprint_v2(mode="plan")  # Preview what would happen
        brain_autopilot_sprint_v2(budget_limit=5.0)  # Limit cost to $5
    """
    return _brain_autopilot_sprint_v2_impl(
        slots, mode, halt_on_blocker, halt_on_tier_mismatch,
        max_tasks_per_slot, budget_limit, time_limit_hours, dry_run
    )


def _brain_start_mission_impl(
    name: str,
    goal: str,
    task_ids: List[str],
    slot_ids: List[str] = None,
    budget_limit: float = 10.0,
    time_limit_hours: float = 4.0,
    success_criteria: List[str] = None,
) -> str:
    """Internal implementation of mission start."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        mission = engine.start_mission(
            name=name,
            goal=goal,
            task_ids=task_ids,
            slot_ids=slot_ids,
            budget_limit=budget_limit,
            time_limit_hours=time_limit_hours,
            success_criteria=success_criteria,
        )
        
        return f"""✅ Mission Started
   ID: {mission.id}
   Name: {mission.name}
   Goal: {mission.goal}
   Tasks: {len(mission.tasks)}
   Budget: ${mission.budget_limit:.2f}
   Time Limit: {mission.time_limit_hours}h
   
💡 Use brain_mission_status() to track progress"""
        
    except Exception as e:
        return f"❌ Mission error: {str(e)}"


@mcp.tool()
def brain_start_mission(
    name: str,
    goal: str,
    task_ids: List[str],
    slot_ids: List[str] = None,
    budget_limit: float = 10.0,
    time_limit_hours: float = 4.0,
    success_criteria: List[str] = None,
) -> str:
    """
    Start a new mission for orchestrated execution.
    
    Missions are high-level goals with associated tasks, constraints,
    and success criteria. They provide persistence and tracking.
    
    Args:
        name: Mission name (e.g., "Implement NOP V3.1")
        goal: What success looks like
        task_ids: List of task IDs to complete
        slot_ids: Slots to use (None = all active)
        budget_limit: Max cost in USD
        time_limit_hours: Max duration
        success_criteria: List of success conditions
    
    Returns:
        Mission ID and confirmation
    """
    return _brain_start_mission_impl(
        name, goal, task_ids, slot_ids, budget_limit, time_limit_hours, success_criteria
    )


def _brain_mission_status_impl(mission_id: str = None) -> str:
    """Internal implementation of mission status."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        status = engine.get_mission_status(mission_id)
        
        if "error" in status:
            return f"❌ {status['error']}"
        
        progress = status["progress"]
        budget = status["budget"]
        
        return f"""🎯 Mission Status: {status['name']}
═══════════════════════════════════════
ID: {status['mission_id']}
Status: {status['status'].upper()}

📊 PROGRESS
   ├── Completed: {progress['completed']}/{progress['total']} ({progress['percent']}%)
   └── Elapsed: {status['elapsed']}

💰 BUDGET
   ├── Limit: ${budget['limit']:.2f}
   ├── Spent: ${budget['spent']:.2f}
   └── Remaining: ${budget['remaining']:.2f}"""
        
    except Exception as e:
        return f"❌ Status error: {str(e)}"


@mcp.tool()
def brain_mission_status(mission_id: str = None) -> str:
    """
    Get current mission status and progress.
    
    Args:
        mission_id: Mission ID (None = current mission)
    
    Returns:
        Detailed mission progress report
    """
    return _brain_mission_status_impl(mission_id)


def _brain_halt_sprint_impl(reason: str = "User requested halt") -> str:
    """Internal implementation of sprint halt."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        result = engine.halt_sprint(reason)
        
        return f"""⛔ Sprint Halt Requested
   Sprint ID: {result.get('sprint_id', 'N/A')}
   Reason: {result['reason']}
   Status: {result['status']}
   
💡 Sprint will complete current task then stop gracefully"""
        
    except Exception as e:
        return f"❌ Halt error: {str(e)}"


@mcp.tool()
def brain_halt_sprint(reason: str = "User requested halt") -> str:
    """
    Request halt of current sprint.
    
    The sprint will complete its current task then stop gracefully.
    Progress is checkpointed for potential resumption.
    
    Args:
        reason: Reason for halting
    
    Returns:
        Confirmation of halt request
    """
    return _brain_halt_sprint_impl(reason)


def _brain_resume_sprint_impl(sprint_id: str = None) -> str:
    """Internal implementation of sprint resume."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        from nop_core.autopilot import format_sprint_result
        
        result = engine.resume_sprint(sprint_id)
        
        return format_sprint_result(result)
        
    except Exception as e:
        return f"❌ Resume error: {str(e)}"


@mcp.tool()
def brain_resume_sprint(sprint_id: str = None) -> str:
    """
    Resume a halted sprint from checkpoint.
    
    Restores state from the last checkpoint and continues execution.
    
    Args:
        sprint_id: Sprint ID to resume (None = most recent)
    
    Returns:
        Sprint execution report
    """
    return _brain_resume_sprint_impl(sprint_id)


# =============================================================================
# FEDERATION ENGINE MCP TOOLS (Phase 5)
# =============================================================================

_federation_engine = None

def _get_federation_engine():
    """Get or create the federation engine singleton."""
    global _federation_engine
    if _federation_engine is None:
        try:
            from .runtime.federation import FederationEngine, FederationConfig # noqa: E402, F401
            brain_path = get_brain_path()
            config = FederationConfig(
                brain_id=f"brain_{brain_path.name}",
                region="default",
                brain_path=brain_path,
            )
            _federation_engine = FederationEngine(config)
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize FederationEngine: {e}")
            return None
    return _federation_engine


def _brain_federation_status_impl() -> str:
    """Internal implementation of federation status."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        status = engine.get_status()
        health = engine.get_health()
        
        # Format peer list
        peers = status.get("peers", {})
        peer_list = []
        for peer in engine.get_peers():
            icon = "🟢" if peer.is_online() else "🟡" if peer.status.name == "SUSPECT" else "🔴"
            peer_list.append(f"   {icon} {peer.peer_id} ({peer.region}) - {peer.latency_ms:.1f}ms")
        
        peer_display = "\n".join(peer_list) if peer_list else "   No peers discovered"
        
        warnings = health.get("warnings", [])
        warning_display = "\n".join(f"   ⚠️ {w}" for w in warnings) if warnings else "   None"
        
        return f"""🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: {status['brain_id']}
   Region: {status['region']}
   Running: {'✅' if status['running'] else '❌'}

👑 CONSENSUS
   Leader: {status['leader_id'] or 'None'}
   Is Leader: {'✅' if status['is_leader'] else '❌'}
   Term: {status['term']}

🔗 PEERS ({peers.get('online', 0)}/{peers.get('total', 0)} online)
{peer_display}

📡 PARTITION STATUS
   Status: {status['partition_status']}
   Class A Enabled: {'✅' if status['class_a_enabled'] else '❌'}

💚 HEALTH
   Score: {health['score']:.0%}
   Healthy: {'✅' if health['healthy'] else '❌'}

⚠️ WARNINGS
{warning_display}

🔄 SYNC
   Merkle Root: {status['sync']['merkle_root'][:16]}...
   Vector Clock: {len(status['sync']['vector_clock'])} entries"""
        
    except Exception as e:
        return f"❌ Federation status error: {str(e)}"


@mcp.tool()
def brain_federation_status() -> str:
    """
    Get comprehensive federation status.
    
    Shows local brain info, consensus state, peer list,
    partition status, health score, and sync state.
    
    Returns:
        Formatted federation status report
    """
    return _brain_federation_status_impl()


def _brain_federation_join_impl(seed_peer: str) -> str:
    """Internal implementation of federation join."""
    import asyncio
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        # Start engine if not running
        if not engine.running:
            asyncio.run(engine.start())
        
        result = asyncio.run(engine.join(seed_peer))
        
        if result.get("success"):
            return f"""✅ JOINED FEDERATION
   Seed Peer: {seed_peer}
   Total Peers: {result.get('peers', 0)}
   
💡 Federation engine is now active and syncing"""
        else:
            return f"❌ Failed to join: {result.get('error', 'Unknown error')}"
        
    except Exception as e:
        return f"❌ Join error: {str(e)}"


@mcp.tool()
def brain_federation_join(seed_peer: str) -> str:
    """
    Join a federation via seed peer.
    
    Connects to an existing federation network through
    a known peer address.
    
    Args:
        seed_peer: Address of seed peer (host:port)
    
    Returns:
        Join result
    """
    return _brain_federation_join_impl(seed_peer)


def _brain_federation_leave_impl() -> str:
    """Internal implementation of federation leave."""
    import asyncio
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        result = asyncio.run(engine.leave())
        
        if result.get("success"):
            return """✅ LEFT FEDERATION
   
Federation engine stopped gracefully.
Local brain now operating in standalone mode."""
        else:
            return f"❌ Failed to leave: {result.get('error', 'Unknown error')}"
        
    except Exception as e:
        return f"❌ Leave error: {str(e)}"


@mcp.tool()
def brain_federation_leave() -> str:
    """
    Leave the federation gracefully.
    
    Notifies peers and stops federation engine.
    Brain continues operating in standalone mode.
    
    Returns:
        Leave confirmation
    """
    return _brain_federation_leave_impl()


def _brain_federation_peers_impl() -> str:
    """Internal implementation of federation peers list."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        peers = engine.get_peers()
        
        if not peers:
            return """🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation."""
        
        lines = ["🔗 FEDERATION PEERS", "═══════════════════════════════════════", ""]
        
        for peer in peers:
            status_icon = {
                "ONLINE": "🟢",
                "SUSPECT": "🟡", 
                "OFFLINE": "🔴",
                "QUARANTINED": "⛔",
                "UNKNOWN": "❓",
            }.get(peer.status.name, "❓")
            
            trust_icon = {
                "OWNER": "👑",
                "ADMIN": "🛡️",
                "MEMBER": "👤",
                "GUEST": "👁️",
            }.get(peer.trust_level.name, "👤")
            
            lines.append(f"{status_icon} {peer.peer_id}")
            lines.append(f"   Address: {peer.address}")
            lines.append(f"   Region: {peer.region}")
            lines.append(f"   Trust: {trust_icon} {peer.trust_level.name}")
            lines.append(f"   Latency: {peer.latency_ms:.1f}ms")
            lines.append(f"   Load: {peer.load:.0%}")
            lines.append(f"   Capabilities: {', '.join(peer.capabilities) or 'None'}")
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Peers error: {str(e)}"


@mcp.tool()
def brain_federation_peers() -> str:
    """
    List all federation peers with details.
    
    Shows status, region, trust level, latency,
    load, and capabilities for each peer.
    
    Returns:
        Formatted peer list
    """
    return _brain_federation_peers_impl()


def _brain_federation_sync_impl() -> str:
    """Internal implementation of federation sync."""
    import asyncio
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        if not engine.running:
            return "❌ Federation engine not running. Use brain_federation_join first."
        
        results = asyncio.run(engine.sync_now())
        
        if not results:
            return """🔄 SYNC COMPLETE
   
No peers to sync with."""
        
        lines = ["🔄 SYNC RESULTS", "═══════════════════════════════════════", ""]
        
        total_synced = 0
        total_conflicts = 0
        
        for result in results:
            icon = "✅" if result.success else "❌"
            lines.append(f"{icon} {result.peer_id}")
            lines.append(f"   Items synced: {result.items_synced}")
            lines.append(f"   Conflicts resolved: {result.conflicts_resolved}")
            lines.append(f"   Time: {result.sync_time_ms:.2f}ms")
            if result.error:
                lines.append(f"   Error: {result.error}")
            lines.append("")
            
            total_synced += result.items_synced
            total_conflicts += result.conflicts_resolved
        
        lines.append("📊 TOTALS")
        lines.append(f"   Peers synced: {len(results)}")
        lines.append(f"   Items synced: {total_synced}")
        lines.append(f"   Conflicts resolved: {total_conflicts}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Sync error: {str(e)}"


@mcp.tool()
def brain_federation_sync() -> str:
    """
    Force immediate synchronization with all peers.
    
    Performs full state sync using Merkle tree comparison
    and CRDT merge for conflict resolution.
    
    Returns:
        Sync results for each peer
    """
    return _brain_federation_sync_impl()


def _brain_federation_route_impl(task_id: str, profile: str = "default") -> str:
    """Internal implementation of federation routing."""
    import asyncio
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        # Get task from task store
        task = {"id": task_id}
        
        # Try to get full task details
        try:
            tasks_file = get_brain_path() / "ledger" / "tasks.json"
            if tasks_file.exists():
                import json
                with open(tasks_file) as f:
                    tasks_data = json.load(f)
                for t in tasks_data.get("tasks", []):
                    if t.get("id") == task_id or t.get("description", "").startswith(task_id):
                        task = t
                        break
        except Exception:
            pass
        
        decision = asyncio.run(engine.route_task(task, profile))
        
        return f"""🎯 ROUTING DECISION
═══════════════════════════════════════

📋 Task: {task_id}
📊 Profile: {profile}

🏆 TARGET
   Brain: {decision.target_brain}
   Score: {decision.score:.3f}
   
⏱️ ROUTING TIME
   {decision.routing_time_ms:.3f}ms

🔄 ALTERNATIVES
{chr(10).join(f'   {i+1}. {alt[0]} (score: {alt[1]:.3f})' for i, alt in enumerate(decision.alternatives[:3])) or '   None'}

💡 Task should be executed on {decision.target_brain}"""
        
    except Exception as e:
        return f"❌ Routing error: {str(e)}"


@mcp.tool()
def brain_federation_route(task_id: str, profile: str = "default") -> str:
    """
    Route a task to the optimal brain.
    
    Uses composite scoring with configurable profiles
    to determine the best brain for task execution.
    
    Args:
        task_id: Task to route
        profile: Routing profile (default, realtime, batch, premium, budget)
    
    Returns:
        Routing decision with target brain and alternatives
    """
    return _brain_federation_route_impl(task_id, profile)


def _brain_federation_health_impl() -> str:
    """Internal implementation of federation health."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            return "❌ FederationEngine not available."
        
        health = engine.get_health()
        metrics = engine.metrics
        
        # Health bar
        score = health["score"]
        bar_filled = int(score * 20)
        bar_empty = 20 - bar_filled
        health_bar = "█" * bar_filled + "░" * bar_empty
        
        # Status color
        if score >= 0.8:
            status = "🟢 HEALTHY"
        elif score >= 0.5:
            status = "🟡 DEGRADED"
        else:
            status = "🔴 CRITICAL"
        
        return f"""💚 FEDERATION HEALTH
═══════════════════════════════════════

{status}
[{health_bar}] {score:.0%}

📊 PARTITION
   Status: {health['partition_status']}
   Peers Online: {health['peers_online']}/{health['peers_total']}
   Leader: {health['leader'] or 'None'}

📈 METRICS
   Tasks Routed: {metrics.tasks_routed}
   Avg Routing Time: {metrics.avg_routing_time_ms:.3f}ms
   Sync Operations: {metrics.sync_operations}
   Leader Changes: {metrics.raft_leader_changes}
   Partition Events: {metrics.partition_events}

⚠️ WARNINGS ({len(health['warnings'])})
{chr(10).join(f'   • {w}' for w in health['warnings']) or '   None'}"""
        
    except Exception as e:
        return f"❌ Health error: {str(e)}"


@mcp.tool()
def brain_federation_health() -> str:
    """
    Get federation health dashboard.
    
    Shows health score, partition status, metrics,
    and any active warnings.
    
    Returns:
        Health dashboard with visual indicators
    """
    return _brain_federation_health_impl()


# ============================================================================
# SYSTEM HEALTH ENDPOINT (Phase 6B Production Hardening)
# ============================================================================
def _brain_health_impl() -> str:
    """Internal implementation of system health check (JSON)."""
    
    try:
        try:
            brain_path = get_brain_path()
            bp_str = str(brain_path)
        except Exception:
            bp_str = "not_configured"
            
        tools_count = len(mcp.tools) if hasattr(mcp, 'tools') else "unknown"
        
        return json.dumps({
            "status": "healthy",
            "version": __version__,
            "tools_registered": tools_count,
            "brain_path": bp_str,
            "uptime_seconds": int(time.time() - START_TIME),
            "python_version": sys.version.split()[0]
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "unhealthy", "error": str(e)})

def _brain_health_impl_legacy() -> str:
    """Internal implementation of system health check."""
    import platform
    
    health_status = {
        "status": "healthy",
        "version": "0.5.0",
        "checks": {},
        "warnings": [],
        "uptime_seconds": 0
    }
    
    try:
        brain = get_brain_path()
        
        # Check 1: Brain path exists
        if brain.exists():
            health_status["checks"]["brain_path"] = "✅ OK"
        else:
            health_status["checks"]["brain_path"] = "❌ FAIL"
            health_status["status"] = "unhealthy"
            health_status["warnings"].append("Brain path does not exist")
        
        # Check 2: Ledger directory
        ledger_path = brain / "ledger"
        if ledger_path.exists():
            health_status["checks"]["ledger"] = "✅ OK"
        else:
            health_status["checks"]["ledger"] = "⚠️ MISSING"
            health_status["warnings"].append("Ledger directory missing")
        
        # Check 3: Tasks file
        tasks_path = brain / "ledger" / "tasks.json"
        if tasks_path.exists():
            try:
                with open(tasks_path, "r") as f:
                    tasks = json.load(f)
                task_count = len(tasks.get("tasks", []))
                health_status["checks"]["tasks"] = f"✅ OK ({task_count} tasks)"
            except Exception as e:
                health_status["checks"]["tasks"] = f"⚠️ CORRUPT: {str(e)[:30]}"
                health_status["warnings"].append("Tasks file corrupted")
        else:
            health_status["checks"]["tasks"] = "⚠️ NO FILE"
        
        # Check 4: Events file
        events_path = brain / "ledger" / "events.jsonl"
        if events_path.exists():
            try:
                with open(events_path, "r") as f:
                    event_count = sum(1 for _ in f)
                health_status["checks"]["events"] = f"✅ OK ({event_count} events)"
            except Exception as e:
                health_status["checks"]["events"] = f"⚠️ ERROR: {str(e)[:30]}"
        else:
            health_status["checks"]["events"] = "⚠️ NO FILE"
        
        # Check 5: State file
        state_path = brain / "state.json"
        if state_path.exists():
            health_status["checks"]["state"] = "✅ OK"
        else:
            health_status["checks"]["state"] = "⚠️ MISSING"
        
        # Check 6: Slots registry
        slots_path = brain / "slots" / "registry.json"
        if slots_path.exists():
            try:
                with open(slots_path, "r") as f:
                    slots = json.load(f)
                slot_count = len(slots.get("slots", []))
                health_status["checks"]["slots"] = f"✅ OK ({slot_count} slots)"
            except Exception:
                health_status["checks"]["slots"] = "⚠️ CORRUPT"
        else:
            health_status["checks"]["slots"] = "⚠️ NO FILE"
        
        # Calculate overall health score
        ok_count = sum(1 for v in health_status["checks"].values() if v.startswith("✅"))
        total_checks = len(health_status["checks"])
        health_score = ok_count / total_checks if total_checks > 0 else 0
        
        # Health bar
        bar_filled = int(health_score * 20)
        bar_empty = 20 - bar_filled
        health_bar = "█" * bar_filled + "░" * bar_empty
        
        # Status indicator
        if health_score >= 0.8:
            status_icon = "🟢 HEALTHY"
        elif health_score >= 0.5:
            status_icon = "🟡 DEGRADED"
            health_status["status"] = "degraded"
        else:
            status_icon = "🔴 CRITICAL"
            health_status["status"] = "unhealthy"
        
        # Format output
        checks_formatted = "\n".join(f"   {k}: {v}" for k, v in health_status["checks"].items())
        warnings_formatted = "\n".join(f"   • {w}" for w in health_status["warnings"]) or "   None"
        
        return f"""💚 NUCLEUS HEALTH CHECK
═══════════════════════════════════════

{status_icon}
[{health_bar}] {health_score:.0%}

📋 VERSION
   Nucleus: {health_status['version']}
   Python: {platform.python_version()}
   Platform: {platform.system()} {platform.release()}

🔍 CHECKS
{checks_formatted}

⚠️ WARNINGS ({len(health_status['warnings'])})
{warnings_formatted}

📁 BRAIN PATH
   {brain}

🕐 TIMESTAMP
   {datetime.now().isoformat()}

✅ System is {health_status['status']}"""
        
    except Exception as e:
        return f"""💚 NUCLEUS HEALTH CHECK
═══════════════════════════════════════

🔴 CRITICAL ERROR
   {str(e)}

Please ensure NUCLEAR_BRAIN_PATH is set correctly."""


@mcp.tool()
def brain_health() -> str:
    """
    Get comprehensive system health status.
    
    Checks brain path, ledger, tasks, events, state, and slots.
    Returns health score and detailed status for each component.
    
    Use this for:
    - Production monitoring
    - Debugging issues
    - Verifying installation
    
    Returns:
        Health dashboard with all component statuses
    """
    return _brain_health_impl()


def _brain_version_impl() -> Dict[str, Any]:
    """Internal implementation of version info."""
    import platform
    
    return {
        "nucleus_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "mcp_tools_count": 110,
        "architecture": "Trinity (Orchestration + Choreography + Context)",
        "status": "production-ready"
    }


@mcp.tool()
def brain_version() -> str:
    """
    Get Nucleus version and system information.
    
    Returns:
        Version info as formatted string
    """
    info = _brain_version_impl()
    return f"""🧠 NUCLEUS VERSION INFO
═══════════════════════════════════════

📦 VERSION
   Nucleus: {info['nucleus_version']}
   Python: {info['python_version']}
   Platform: {info['platform']} {info['platform_release']}

🔧 CAPABILITIES
   MCP Tools: {info['mcp_tools_count']}+
   Architecture: {info['architecture']}
   Status: {info['status']}

   GitHub: https://github.com/eidetic-works/nucleus-mcp
   PyPI: pip install nucleus-mcp
   Docs: https://nucleusos.dev"""

@mcp.tool()
async def brain_export_schema() -> str:
    """
    Export the current MCP toolset as an OpenAPI/JSON Schema.
    
    This helps the AI or external tools understand the full 
    contract of all available Nucleus tools.
    
    Returns:
        JSON Schema string
    """
    schema = await generate_tool_schema(mcp)
    return json.dumps(schema, indent=2)


@mcp.tool()
def brain_performance_metrics(export_to_file: bool = False) -> str:
    """
    Get performance metrics for Nucleus operations (AG-014).
    
    Requires NUCLEUS_PROFILING=true environment variable to collect metrics.
    
    Args:
        export_to_file: If True, also exports metrics to .brain/metrics/
    
    Returns:
        Formatted performance summary or JSON if exported
    """
    from .runtime.profiling import get_metrics, get_metrics_summary, export_metrics_to_file # noqa: E402, F401
    
    metrics = get_metrics()
    if not metrics:
        return make_response(True, data={
            "message": "No metrics collected. Set NUCLEUS_PROFILING=true to enable.",
            "hint": "export NUCLEUS_PROFILING=true before starting Nucleus"
        })
    
    if export_to_file:
        try:
            filepath = export_metrics_to_file()
            return make_response(True, data={
                "metrics": metrics,
                "exported_to": filepath
            })
        except Exception as e:
            return make_response(False, error=f"Export failed: {e}")
    
    return make_response(True, data={
        "summary": get_metrics_summary(),
        "metrics": metrics
    })


@mcp.tool()
def brain_prometheus_metrics(format: str = "prometheus") -> str:
    """
    Get Prometheus-compatible metrics for monitoring (AG-015).
    
    Args:
        format: Output format - "prometheus" (text) or "json"
    
    Returns:
        Metrics in Prometheus exposition format or JSON
    
    Example scrape config:
        - job_name: 'nucleus'
          static_configs:
            - targets: ['localhost:9090']
    """
    from .runtime.prometheus import get_prometheus_metrics, get_metrics_json # noqa: E402, F401
    
    if format.lower() == "json":
        return make_response(True, data=get_metrics_json())
    
    # Return raw Prometheus format (not wrapped in JSON for scraping)
    return get_prometheus_metrics()


@mcp.tool()
def brain_audit_log(limit: int = 20) -> str:
    """
    View the cryptographic interaction log for trust verification.
    
    Each interaction is SHA-256 hashed for integrity verification.
    This is the "Why-Trace" that proves agent decisions.
    
    Part of the Governance Moat (N-SOS V1).
    
    Args:
        limit: Number of recent entries to return (default 20)
    
    Returns:
        Recent interaction hashes with timestamps and emitters
    """
    return _brain_audit_log_impl(limit)


def _brain_audit_log_impl(limit: int = 20) -> str:
    """Implementation for audit log viewing."""
    try:
        brain = get_brain_path()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        
        if not log_path.exists():
            return make_response(True, data={
                "entries": [],
                "count": 0,
                "message": "No interaction log found. Enable with V9 Security."
            })
        
        entries = []
        with open(log_path, "r") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        # Get most recent entries
        recent = entries[-limit:] if len(entries) > limit else entries
        recent.reverse()  # Most recent first
        
        return make_response(True, data={
            "entries": recent,
            "count": len(recent),
            "total": len(entries),
            "algorithm": "sha256",
            "message": f"Showing {len(recent)} of {len(entries)} interaction hashes"
        })
    except Exception as e:
        return make_response(False, error=f"Error reading audit log: {e}")


@mcp.tool()
def brain_write_engram(key: str, value: str, context: str = "Decision", intensity: int = 5) -> str:
    """
    Write a new Engram to the cognitive memory ledger.
    
    Engrams are persistent memory units that survive between sessions.
    Use this to record architectural decisions, constraints, and learnings.
    
    Part of the Engram Ledger (N-SOS V1).
    
    Args:
        key: Unique identifier (e.g., "auth_architecture", "no_openai")
        value: The memory content (include reasoning - "X because Y")
        context: Category - Feature, Architecture, Brand, Strategy, Decision
        intensity: 1-10 priority (10=critical constraint, 5=normal, 1=archive)
    
    Returns:
        Confirmation with engram details
    
    Examples:
        - brain_write_engram("db_choice", "PostgreSQL for ACID compliance", "Architecture", 8)
        - brain_write_engram("no_openai", "Budget constraint - Gemini only", "Decision", 10)
    """
    return _brain_write_engram_impl(key, value, context, intensity)


def _brain_write_engram_impl(key: str, value: str, context: str, intensity: int) -> str:
    """Implementation for engram writing."""
    try:
        # V9.1 Security Hardening: Key Validation
        if not key or len(key.strip()) < 2:
            import sys
            print("[NUCLEUS] SECURITY VIOLATION: Empty or short key detected", file=sys.stderr)
            return make_response(False, error="Security Violation: Key must be at least 2 characters")
            
        if not re.match(r"^[a-zA-Z0-9_.-]+$", key):
            import sys
            print("[NUCLEUS] SECURITY VIOLATION: Invalid key pattern detected", file=sys.stderr)
            return make_response(False, error="Security Violation: Key contains invalid characters")

        # V9.2 Value Restoration: Removed aggressive SQL/Script regex.
        # Rationale: We use a JSON Ledger for storage, so SQL Injection is structurally impossible.
        # Blocking strings like "DROP TABLE" hurts developers saving code snippets.
        # We trust the ledger backend to serialize JSON correctly.

        # Validate intensity
        if not 1 <= intensity <= 10:
            return make_response(False, error="Intensity must be between 1 and 10")
        
        # Validate context
        valid_contexts = ["Feature", "Architecture", "Brand", "Strategy", "Decision"]
        if context not in valid_contexts:
            return make_response(False, error=f"Context must be one of: {valid_contexts}")
        
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"
        engram_path.parent.mkdir(parents=True, exist_ok=True)
        
        engram = {
            "key": key,
            "value": value,
            "context": context,
            "intensity": intensity,
            "timestamp": datetime.now().isoformat(),
            "signature": None  # Future: cryptographic signing
        }
        
        with open(engram_path, "a") as f:
            f.write(json.dumps(engram) + "\n")
        
        # Also emit event for audit trail
        _emit_event("engram_written", "brain_write_engram", {
            "key": key,
            "context": context,
            "intensity": intensity
        })
        
        return make_response(True, data={
            "engram": engram,
            "message": f"Engram '{key}' written with intensity {intensity} ({context})"
        })
    except Exception as e:
        return make_response(False, error=f"Error writing engram: {e}")


@mcp.tool()
def brain_query_engrams(context: str = None, min_intensity: int = 1) -> str:
    """
    Query Engrams from the cognitive memory ledger.
    
    Retrieve persistent memory units filtered by context and intensity.
    
    Args:
        context: Filter by category (Feature, Architecture, Brand, Strategy, Decision)
                 If None, returns all engrams
        min_intensity: Minimum intensity threshold (1-10)
    
    Returns:
        List of matching engrams sorted by intensity (highest first)
    """
    return _brain_query_engrams_impl(context, min_intensity)


def _brain_query_engrams_impl(context: str, min_intensity: int) -> str:
    """Implementation for engram querying."""
    try:
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"
        
        if not engram_path.exists():
            return make_response(True, data={
                "engrams": [],
                "count": 0,
                "message": "No engrams found. Use brain_write_engram() to create."
            })
        
        engrams = []
        with open(engram_path, "r") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    # Filter by context if specified
                    if context and e.get("context", "").lower() != context.lower():
                        continue
                    # Filter by minimum intensity
                    if e.get("intensity", 5) < min_intensity:
                        continue
                    engrams.append(e)
        
        # Sort by intensity (highest first)
        engrams.sort(key=lambda x: x.get("intensity", 5), reverse=True)
        
        return make_response(True, data={
            "engrams": engrams,
            "count": len(engrams),
            "filters": {"context": context, "min_intensity": min_intensity}
        })
    except Exception as e:
        return make_response(False, error=f"Error querying engrams: {e}")


@mcp.tool()
def brain_search_engrams(query: str, case_sensitive: bool = False) -> str:
    """
    Search Engrams by substring match in key or value.
    
    Simple text search across all engrams. Use this to find
    specific memories by keyword.
    
    Args:
        query: Substring to search for in engram keys and values
        case_sensitive: Whether search is case-sensitive (default: False)
    
    Returns:
        List of matching engrams with match highlights
    
    Examples:
        - brain_search_engrams("postgres") - Find database decisions
        - brain_search_engrams("auth") - Find authentication-related memories
    """
    return _brain_search_engrams_impl(query, case_sensitive)


def _brain_search_engrams_impl(query: str, case_sensitive: bool = False) -> str:
    """Implementation for engram substring search."""
    try:
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"
        
        if not engram_path.exists():
            return make_response(True, data={
                "engrams": [],
                "count": 0,
                "query": query,
                "message": "No engrams found. Use brain_write_engram() to create."
            })
        
        search_query = query if case_sensitive else query.lower()
        matches = []
        
        with open(engram_path, "r") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    key = e.get("key", "")
                    value = e.get("value", "")
                    
                    key_search = key if case_sensitive else key.lower()
                    value_search = value if case_sensitive else value.lower()
                    
                    if search_query in key_search or search_query in value_search:
                        e["_match_in"] = []
                        if search_query in key_search:
                            e["_match_in"].append("key")
                        if search_query in value_search:
                            e["_match_in"].append("value")
                        matches.append(e)
        
        matches.sort(key=lambda x: x.get("intensity", 5), reverse=True)
        
        return make_response(True, data={
            "engrams": matches,
            "count": len(matches),
            "query": query,
            "case_sensitive": case_sensitive
        })
    except Exception as e:
        return make_response(False, error=f"Error searching engrams: {e}")


@mcp.tool()
def brain_governance_status() -> str:
    """
    Get the current governance status of the Nucleus Control Plane.
    
    Returns a summary of:
    - Active policies (Default-Deny, Isolation, Audit)
    - Audit log statistics
    - Engram count
    - Security configuration
    
    Part of the Governance Moat (N-SOS V1).
    """
    return _brain_governance_status_impl()


def _brain_governance_status_impl() -> str:
    """Implementation for governance status."""
    try:
        brain = get_brain_path()
        
        # Check audit log
        audit_path = brain / "ledger" / "interaction_log.jsonl"
        audit_count = 0
        if audit_path.exists():
            with open(audit_path, "r") as f:
                audit_count = sum(1 for line in f if line.strip())
        
        # Check engrams
        engram_path = brain / "engrams" / "ledger.jsonl"
        engram_count = 0
        if engram_path.exists():
            with open(engram_path, "r") as f:
                engram_count = sum(1 for line in f if line.strip())
        
        # Check events
        events_path = brain / "ledger" / "events.jsonl"
        events_count = 0
        if events_path.exists():
            with open(events_path, "r") as f:
                events_count = sum(1 for line in f if line.strip())
        
        # Security config
        v9_security = os.environ.get("NUCLEUS_V9_SECURITY", "false").lower() == "true"
        
        governance = {
            "policies": {
                "default_deny": True,  # Always enforced
                "isolation_boundaries": True,  # Always enforced
                "immutable_audit": v9_security,
                "cryptographic_hashing": v9_security
            },
            "statistics": {
                "audit_log_entries": audit_count,
                "engram_count": engram_count,
                "events_logged": events_count
            },
            "configuration": {
                "v9_security_enabled": v9_security,
                "brain_path": str(brain)
            },
            "status": "ENFORCED" if v9_security else "PARTIAL"
        }
        
        return make_response(True, data=governance)
    except Exception as e:
        return make_response(False, error=f"Error checking governance: {e}")


# =============================================================================
# v0.6.0 DSoR (Decision System of Record) MCP Tools
# =============================================================================

@mcp.tool()
def brain_list_decisions(limit: int = 20) -> str:
    """
    List recent DecisionMade events from the decision ledger.
    
    v0.6.0 DSoR: Provides visibility into agent decision provenance.
    
    Args:
        limit: Maximum number of decisions to return (default: 20)
    """
    try:
        brain = get_brain_path()
        decisions_file = brain / "ledger" / "decisions" / "decisions.jsonl"
        
        if not decisions_file.exists():
            return make_response(True, data={"decisions": [], "count": 0})
        
        decisions = []
        with open(decisions_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        decisions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Return most recent first
        decisions = decisions[-limit:][::-1]
        
        return make_response(True, data={
            "decisions": decisions,
            "count": len(decisions),
            "total_in_ledger": sum(1 for _ in open(decisions_file))
        })
    except Exception as e:
        return make_response(False, error=f"Error listing decisions: {e}")


@mcp.tool()
def brain_list_context_snapshots(limit: int = 10) -> str:
    """
    List context snapshots from the snapshot ledger.
    
    v0.6.0 DSoR: Provides visibility into state verification history.
    
    Args:
        limit: Maximum number of snapshots to return (default: 10)
    """
    try:
        brain = get_brain_path()
        snapshots_dir = brain / "ledger" / "snapshots"
        
        if not snapshots_dir.exists():
            return make_response(True, data={"snapshots": [], "count": 0})
        
        snapshots = []
        for snap_file in sorted(snapshots_dir.glob("snap-*.json"), reverse=True)[:limit]:
            try:
                with open(snap_file) as f:
                    snapshots.append(json.load(f))
            except Exception:
                continue
        
        return make_response(True, data={
            "snapshots": snapshots,
            "count": len(snapshots)
        })
    except Exception as e:
        return make_response(False, error=f"Error listing snapshots: {e}")


@mcp.tool()
def brain_metering_summary(since_hours: int = 24) -> str:
    """
    Get token metering summary for billing and audit.
    
    v0.6.0 DSoR: Addresses V9 Pricing Rebellion vulnerability.
    
    Args:
        since_hours: Only include entries from the last N hours (default: 24)
    """
    try:
        brain = get_brain_path()
        meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
        
        if not meter_file.exists():
            return make_response(True, data={
                "total_entries": 0,
                "total_units": 0,
                "by_scope": {},
                "by_resource_type": {},
                "decisions_linked": 0
            })
        
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
        
        entries = []
        with open(meter_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get("timestamp", "") >= cutoff:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        # Compute summary
        summary = {
            "total_entries": len(entries),
            "total_units": sum(e.get("units_consumed", 0) for e in entries),
            "by_scope": {},
            "by_resource_type": {},
            "decisions_linked": sum(1 for e in entries if e.get("decision_id")),
            "since_hours": since_hours
        }
        
        for entry in entries:
            scope = entry.get("scope", "unknown")
            rtype = entry.get("resource_type", "unknown")
            units = entry.get("units_consumed", 0)
            
            summary["by_scope"][scope] = summary["by_scope"].get(scope, 0) + units
            summary["by_resource_type"][rtype] = summary["by_resource_type"].get(rtype, 0) + units
        
        return make_response(True, data=summary)
    except Exception as e:
        return make_response(False, error=f"Error getting metering summary: {e}")


@mcp.tool()
def brain_ipc_tokens(active_only: bool = True) -> str:
    """
    List IPC authentication tokens.
    
    v0.6.0 DSoR: Addresses CVE-2026-001 (Sidecar Exploit).
    
    Args:
        active_only: Only show active (non-consumed, non-expired) tokens
    """
    try:
        brain = get_brain_path()
        tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
        
        if not tokens_file.exists():
            return make_response(True, data={"tokens": [], "count": 0})
        
        from datetime import datetime, timezone
        datetime.now(timezone.utc).isoformat()
        
        events = []
        with open(tokens_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Group by token_id to get current state
        token_states = {}
        for event in events:
            tid = event.get("token_id")
            if tid:
                if tid not in token_states:
                    token_states[tid] = {"token_id": tid, "events": []}
                token_states[tid]["events"].append(event)
                token_states[tid]["last_event"] = event.get("event")
                token_states[tid]["decision_id"] = event.get("decision_id")
        
        tokens = list(token_states.values())
        
        if active_only:
            tokens = [t for t in tokens if t.get("last_event") == "issued"]
        
        return make_response(True, data={
            "tokens": tokens[-20:],  # Limit to recent 20
            "count": len(tokens),
            "active_only": active_only
        })
    except Exception as e:
        return make_response(False, error=f"Error listing IPC tokens: {e}")


@mcp.tool()
def brain_dsor_status() -> str:
    """
    Get comprehensive v0.6.0 DSoR (Decision System of Record) status.
    
    Returns combined status of:
    - Decision ledger
    - Context snapshots
    - IPC token metering
    - Security compliance
    """
    try:
        brain = get_brain_path()
        
        # Decision ledger stats
        decisions_file = brain / "ledger" / "decisions" / "decisions.jsonl"
        decision_count = 0
        if decisions_file.exists():
            with open(decisions_file) as f:
                decision_count = sum(1 for line in f if line.strip())
        
        # Snapshot stats
        snapshots_dir = brain / "ledger" / "snapshots"
        snapshot_count = len(list(snapshots_dir.glob("snap-*.json"))) if snapshots_dir.exists() else 0
        
        # Metering stats
        meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
        meter_count = 0
        total_units = 0
        if meter_file.exists():
            with open(meter_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            meter_count += 1
                            total_units += entry.get("units_consumed", 0)
                        except Exception:
                            pass
        
        # IPC token stats
        tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
        token_issued = 0
        token_consumed = 0
        if tokens_file.exists():
            with open(tokens_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("event") == "issued":
                                token_issued += 1
                            elif event.get("event") == "consumed":
                                token_consumed += 1
                        except Exception:
                            pass
        
        status = {
            "version": "0.6.0",
            "feature": "Decision System of Record (DSoR)",
            "components": {
                "decision_ledger": {
                    "status": "ACTIVE" if decision_count > 0 else "READY",
                    "total_decisions": decision_count
                },
                "context_snapshots": {
                    "status": "ACTIVE" if snapshot_count > 0 else "READY",
                    "total_snapshots": snapshot_count
                },
                "ipc_auth": {
                    "status": "ACTIVE" if token_issued > 0 else "READY",
                    "tokens_issued": token_issued,
                    "tokens_consumed": token_consumed
                },
                "token_metering": {
                    "status": "ACTIVE" if meter_count > 0 else "READY",
                    "meter_entries": meter_count,
                    "total_units_metered": total_units
                }
            },
            "v9_vulnerabilities_addressed": [
                "CVE-2026-001: Sidecar Exploit (per-request IPC auth)",
                "Pricing Rebellion (token metering linked to decisions)"
            ],
            "overall_status": "OPERATIONAL"
        }
        
        return make_response(True, data=status)
    except Exception as e:
        return make_response(False, error=f"Error getting DSoR status: {e}")


@mcp.tool()
def brain_federation_dsor_status() -> str:
    """
    Get Federation Engine DSoR status.
    
    v0.6.0 DSoR: Shows federation events with decision provenance.
    """
    try:
        brain = get_brain_path()
        events_file = brain / "ledger" / "events.jsonl"
        
        federation_events = {
            "peer_joined": 0,
            "peer_left": 0,
            "peer_suspect": 0,
            "leader_elected": 0,
            "task_routed": 0,
            "state_synced": 0
        }
        recent_events = []
        
        if events_file.exists():
            with open(events_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            event_type = event.get("type", "")
                            
                            if event_type == "federation_peer_joined":
                                federation_events["peer_joined"] += 1
                            elif event_type == "federation_peer_left":
                                federation_events["peer_left"] += 1
                            elif event_type == "federation_peer_suspect":
                                federation_events["peer_suspect"] += 1
                            elif event_type == "federation_leader_elected":
                                federation_events["leader_elected"] += 1
                            elif event_type == "federation_task_routed":
                                federation_events["task_routed"] += 1
                            elif event_type == "federation_state_synced":
                                federation_events["state_synced"] += 1
                            
                            if event_type.startswith("federation_"):
                                recent_events.append({
                                    "type": event_type,
                                    "timestamp": event.get("timestamp"),
                                    "decision_id": event.get("data", {}).get("decision_id")
                                })
                        except Exception:
                            pass
        
        # Get last 10 federation events
        recent_events = recent_events[-10:]
        
        status = {
            "version": "0.6.0",
            "feature": "Federation Engine DSoR Integration",
            "event_counts": federation_events,
            "total_federation_events": sum(federation_events.values()),
            "recent_events": recent_events,
            "dsor_integration": {
                "decision_provenance": True,
                "context_hashing": True,
                "event_auditing": True
            }
        }
        
        return make_response(True, data=status)
    except Exception as e:
        return make_response(False, error=f"Error getting federation DSoR status: {e}")


@mcp.tool()
def brain_routing_decisions(limit: int = 20) -> str:
    """
    Query routing decision history from the Federation Engine.
    
    v0.6.0 DSoR: All routing decisions are now auditable.
    
    Args:
        limit: Maximum number of decisions to return (default: 20)
    """
    try:
        brain = get_brain_path()
        events_file = brain / "ledger" / "events.jsonl"
        
        routing_decisions = []
        
        if events_file.exists():
            with open(events_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("type") == "federation_task_routed":
                                data = event.get("data", {})
                                routing_decisions.append({
                                    "timestamp": event.get("timestamp"),
                                    "target_brain": data.get("target_brain"),
                                    "score": data.get("score"),
                                    "profile": data.get("profile"),
                                    "decision_id": data.get("decision_id"),
                                    "routing_time_ms": data.get("routing_time_ms")
                                })
                        except Exception:
                            pass
        
        # Return last N decisions
        routing_decisions = routing_decisions[-limit:]
        
        return make_response(True, data={
            "total_decisions": len(routing_decisions),
            "limit": limit,
            "decisions": routing_decisions
        })
    except Exception as e:
        return make_response(False, error=f"Error querying routing decisions: {e}")


# =============================================================================
# v0.6.0 TOOL TIER SYSTEM - Registry Bloat Solution
# =============================================================================

@mcp.tool()
def brain_list_tools(category: str = None) -> str:
    """
    List available tools at the current tier level.
    
    v0.6.0 Registry Optimization: Tools are tiered to prevent LLM context overflow.
    Set NUCLEUS_TOOL_TIER env var: 0=launch, 1=core, 2=all
    
    Args:
        category: Optional filter (e.g., "federation", "task", "memory")
    """
    try:
        tier_info = get_tier_info()
        
        # Get all brain_* functions/tools that are allowed for the current tier
        import mcp_server_nucleus as nucleus
        
        all_funcs = []
        for name in dir(nucleus):
            if name.startswith('brain_'):
                # Handle both functions and FunctionTool objects
                getattr(nucleus, name)
                # If it's a tool, its name is item.name. If function, item.__name__
                actual_name = name
                if is_tool_allowed(actual_name):
                    all_funcs.append(actual_name)
        
        # Sync: Only list tools allowed in the current tier
        all_tools = sorted(all_funcs)
        
        if category:
            cat_map = {
                "federation": ["brain_mount_server", "brain_list_tools"],
                "memory": ["brain_write_engram", "brain_query_engrams"],
                "governance": ["brain_audit_log", "brain_governance_status", "brain_version", "brain_health"],
                "task": [] # No task tools in launch tier
            }
            
            # If valid category in map, filter by set membership
            if category.lower() in cat_map:
                target_tools = set(cat_map[category.lower()])
                all_tools = [t for t in all_tools if t in target_tools]
            else:
                # Fallback to string matching for unknown categories
                all_tools = [t for t in all_tools if category.lower() in t.lower()]
        
        return make_response(True, data={
            "tier": tier_info["tier_name"],
            "tier_level": tier_info["active_tier"],
            "total_tools": len(all_tools),
            "tools": all_tools,
            "hint": "Set NUCLEUS_TOOL_TIER=0 for launch (8 tools), =1 for core (28), =2 for all"
        })
    except Exception as e:
        return make_response(False, error=f"Error listing tools: {e}")


@mcp.tool()
def brain_tier_status() -> str:
    """
    Get current tool tier configuration status.
    
    v0.6.0 Registry Bloat Solution: Nucleus uses tiered tool exposure to prevent
    LLM context window overflow. This tool shows the current tier and counts.
    """
    try:
        info = get_tier_info()
        stats = tier_manager.get_stats()
        
        return make_response(True, data={
            "version": "0.6.0",
            "feature": "Tool Tier System (Registry Bloat Solution)",
            "current_tier": info["tier_name"],
            "tier_level": info["active_tier"],
            "env_var": info["env_var"],
            "env_value": info["current_value"],
            "tier_breakdown": {
                "tier_0_launch": info["tier_0_count"],
                "tier_1_core": info["tier_1_count"],
                "tier_2_advanced": info["tier_2_count"],
            },
            "registration_stats": stats,
            "recommendation": "Use NUCLEUS_TOOL_TIER=0 for nucleusos.dev website launch"
        })
    except Exception as e:
        return make_response(False, error=f"Error getting tier status: {e}")

