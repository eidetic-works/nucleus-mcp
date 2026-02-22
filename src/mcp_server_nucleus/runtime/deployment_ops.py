"""
Deployment Operations - Render service configuration, smoke testing, and deploy monitoring.

Extracted from __init__.py monolith (v1.0.7 decomposition).
"""

import json
import time
import uuid
import logging
from typing import Dict

from .common import get_brain_path, _get_state
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.deployment")


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
