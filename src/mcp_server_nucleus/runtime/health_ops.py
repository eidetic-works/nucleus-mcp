"""Health / Version / Audit Operations — System health MCP tool implementations.

Extracted from __init__.py (Phase 6B Production Hardening).
Contains:
- _brain_health_impl (JSON health check)
- _brain_health_impl_legacy (formatted health dashboard)
- _brain_version_impl
- _brain_audit_log_impl
"""

import json
import logging
import platform
import sys
import time
from datetime import datetime
from typing import Any, Dict

from .common import get_brain_path

logger = logging.getLogger("mcp_server_nucleus")


# Lazy import helpers (these live in __init__.py)
def _get_version():
    from mcp_server_nucleus import __version__
    return __version__


def _get_mcp():
    from mcp_server_nucleus import mcp
    return mcp


def _get_start_time():
    from mcp_server_nucleus import START_TIME
    return START_TIME


def _make_response(success, data=None, error=None):
    from mcp_server_nucleus import make_response
    return make_response(success, data=data, error=error)


# ── Implementations ──────────────────────────────────────────────

def _brain_health_impl() -> str:
    """Internal implementation of system health check (JSON)."""
    try:
        try:
            brain_path = get_brain_path()
            bp_str = str(brain_path)
        except Exception:
            bp_str = "not_configured"
            
        mcp = _get_mcp()
        tools_count = len(mcp.tools) if hasattr(mcp, 'tools') else "unknown"
        
        return json.dumps({
            "status": "healthy",
            "version": _get_version(),
            "tools_registered": tools_count,
            "brain_path": bp_str,
            "uptime_seconds": int(time.time() - _get_start_time()),
            "python_version": sys.version.split()[0]
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "unhealthy", "error": str(e)})


def _brain_health_impl_legacy() -> str:
    """Internal implementation of system health check."""
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
                with open(tasks_path, "r", encoding="utf-8") as f:
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
                with open(events_path, "r", encoding="utf-8") as f:
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
                with open(slots_path, "r", encoding="utf-8") as f:
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

Please ensure NUCLEUS_BRAIN_PATH is set correctly."""


def _brain_version_impl() -> Dict[str, Any]:
    """Internal implementation of version info."""
    return {
        "nucleus_version": _get_version(),
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "mcp_tools_count": 110,
        "architecture": "Trinity (Orchestration + Choreography + Context)",
        "status": "production-ready"
    }


def _brain_audit_log_impl(limit: int = 20) -> str:
    """Implementation for audit log viewing."""
    try:
        brain = get_brain_path()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        
        if not log_path.exists():
            return _make_response(True, data={
                "entries": [],
                "count": 0,
                "message": "No interaction log found. Enable with V9 Security."
            })
        
        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        # Get most recent entries
        recent = entries[-limit:] if len(entries) > limit else entries
        recent.reverse()  # Most recent first
        
        return _make_response(True, data={
            "entries": recent,
            "count": len(recent),
            "total": len(entries),
            "algorithm": "sha256",
            "message": f"Showing {len(recent)} of {len(entries)} interaction hashes"
        })
    except Exception as e:
        return _make_response(False, error=f"Error reading audit log: {e}")
