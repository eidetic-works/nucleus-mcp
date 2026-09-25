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

# Capture process start time for staleness detection (fw-1786072975).
# time.monotonic() at import gives a reference point to compute wall-clock
# process start via time.time() - (time.monotonic() - _PROC_START_MONOTONIC).
_PROC_START_MONOTONIC = time.monotonic()


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
            logger.debug("Swallowed exception in _brain_health_impl", exc_info=True)
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
                logger.debug("Swallowed exception in _brain_health_impl_legacy", exc_info=True)
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
                logger.debug("Swallowed exception in _brain_health_impl_legacy", exc_info=True)
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
                logger.debug("Swallowed exception in _brain_health_impl_legacy", exc_info=True)
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
    """Internal implementation of version info.

    Includes module staleness info (fw-1786072975): the git SHA and mtime
    of the loaded mcp_server_nucleus package, so a running server can
    report whether it holds stale code relative to the repo on disk.
    """
    staleness = _module_staleness()
    return {
        "nucleus_version": _get_version(),
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "mcp_tools_count": 110,
        "architecture": "Trinity (Orchestration + Choreography + Context)",
        "status": "production-ready",
        "module_staleness": staleness,
    }


def _module_staleness() -> Dict[str, Any]:
    """Report whether the running process holds stale code (fw-1786072975).

    Compares the loaded module's ``__file__`` mtime against the file on
    disk, and reports the git SHA of the repo at the module's location.
    A running process holds whatever ``sys.modules`` cached at first
    import; lazy in-function imports may or may not have been exercised.
    This makes staleness a MEASURED value instead of an assumption.

    Returns a dict with:
    - ``loaded_module_mtime``: mtime of the loaded package ``__init__.py``
    - ``disk_module_mtime``: current mtime of that file on disk
    - ``stale``: True if disk mtime > loaded mtime (file changed after import)
    - ``repo_git_sha``: short git SHA at the module's repo, or None
    - ``loaded_package_path``: the path the running process imported from
    """
    import os
    import subprocess
    try:
        import mcp_server_nucleus as _pkg
        pkg_path = getattr(_pkg, "__file__", None)
        if not pkg_path:
            return {"error": "cannot determine package path"}
        loaded_mtime = os.path.getmtime(pkg_path)
        disk_mtime = os.path.getmtime(pkg_path)  # same file, but check
        # The loaded mtime IS the disk mtime — we need to compare against
        # the mtime at import time. Since we can't know that, we check
        # whether any .py file in the package dir is newer than the
        # process start time.
        proc_start = time.time() - (time.monotonic() - _PROC_START_MONOTONIC)
        pkg_dir = os.path.dirname(pkg_path)
        newest_py = 0.0
        newest_file = ""
        for root, dirs, files in os.walk(pkg_dir):
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    try:
                        m = os.path.getmtime(fp)
                        if m > newest_py:
                            newest_py = m
                            newest_file = os.path.relpath(fp, pkg_dir)
                    except OSError:
                        pass
        stale = newest_py > proc_start
        # Git SHA
        git_sha = None
        try:
            repo_root = os.path.dirname(os.path.dirname(pkg_dir))
            r = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=3,
                cwd=repo_root,
            )
            if r.returncode == 0:
                git_sha = r.stdout.strip()
        except Exception:
            logger.debug("Swallowed exception in _module_staleness", exc_info=True)
            pass
        return {
            "loaded_package_path": pkg_path,
            "process_start_ts": datetime.fromtimestamp(proc_start).isoformat(),
            "newest_py_mtime": datetime.fromtimestamp(newest_py).isoformat(),
            "newest_py_file": newest_file,
            "stale": stale,
            "repo_git_sha": git_sha,
        }
    except Exception as e:
        return {"error": str(e)[:200]}


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
