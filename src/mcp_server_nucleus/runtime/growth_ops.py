"""
Nucleus Runtime — Growth Operations
====================================
Event-driven growth automation. Nucleus dogfoods itself.

This module makes growth a FIRST-CLASS runtime capability:
- Metrics capture via GitHub/PyPI APIs → written as engrams
- Growth pulse compound loop → fusion reactor on metrics
- Launch task lifecycle → tracked via Nucleus task system
- Event hooks → growth compounds automatically on trigger events

Architecture:
    _emit_event("morning_brief_generated") → engram_hooks → growth_ops hook
    _emit_event("task_completed_*")        → engram_hooks → growth_ops hook
    cron / CLI                             → growth_pulse() → metrics → engram → compound

This is NOT a script. It's a runtime module that other Nucleus components
can import and call. The growth_engine.py script is a thin CLI wrapper.
"""

import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import get_brain_path, logger as common_logger

logger = logging.getLogger("nucleus.growth_ops")

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

GITHUB_REPO = "eidetic-works/nucleus-mcp"
PYPI_PACKAGE = "nucleus-mcp"
GROWTH_ENGRAM_PREFIX = "growth_"
METRICS_ENGRAM_PREFIX = "growth_metrics_"

# Week 4 decision gates
GATES = {
    "stars": 100,
    "pip_installs_30d": 50,
    "contributors": 3,
    "github_issues": 5,
    "dogfood_streak": 21,
}


# ═══════════════════════════════════════════════════════════════
# METRICS CAPTURE (GitHub + PyPI → engrams)
# ═══════════════════════════════════════════════════════════════

def fetch_github_metrics() -> Dict[str, Any]:
    """Fetch current GitHub repo metrics. Returns dict with stars, forks, issues, watchers."""
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}",
            headers={"User-Agent": "nucleus-growth-ops"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "watchers": data.get("subscribers_count", 0),
                "source": "github_api",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.warning(f"GitHub metrics fetch failed: {e}")
        return {"error": str(e), "source": "github_api"}


def fetch_pypi_metrics() -> Dict[str, Any]:
    """Fetch PyPI download stats. Returns dict with last_month installs."""
    try:
        req = urllib.request.Request(
            f"https://pypistats.org/api/packages/{PYPI_PACKAGE}/recent",
            headers={"User-Agent": "nucleus-growth-ops"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return {
                "last_month": data.get("data", {}).get("last_month", 0),
                "last_week": data.get("data", {}).get("last_week", 0),
                "last_day": data.get("data", {}).get("last_day", 0),
                "source": "pypistats_api",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.warning(f"PyPI metrics fetch failed: {e}")
        return {"error": str(e), "source": "pypistats_api"}


def capture_metrics(write_engram: bool = True) -> Dict[str, Any]:
    """
    Capture all growth metrics and optionally write as an engram.

    This is the core metrics function. Called by:
    - growth_pulse() (daily automated)
    - CLI via growth_engine.py
    - MCP via nucleus_infra(action="growth_metrics")

    Returns dict with github, pypi, gates_status, and engram_written.
    """
    github = fetch_github_metrics()
    pypi = fetch_pypi_metrics()

    # Evaluate gates
    gates_status = {}
    if "error" not in github:
        gates_status["stars"] = {
            "current": github["stars"],
            "target": GATES["stars"],
            "passed": github["stars"] >= GATES["stars"],
        }
        gates_status["github_issues"] = {
            "current": github["open_issues"],
            "target": GATES["github_issues"],
            "passed": github["open_issues"] >= GATES["github_issues"],
        }
    if "error" not in pypi:
        gates_status["pip_installs_30d"] = {
            "current": pypi.get("last_month", 0),
            "target": GATES["pip_installs_30d"],
            "passed": pypi.get("last_month", 0) >= GATES["pip_installs_30d"],
        }

    # Dogfood streak (count growth_metrics engrams)
    streak = get_dogfood_streak()
    gates_status["dogfood_streak"] = {
        "current": streak,
        "target": GATES["dogfood_streak"],
        "passed": streak >= GATES["dogfood_streak"],
    }

    gates_passed = sum(1 for g in gates_status.values() if g.get("passed"))
    gates_total = len(gates_status)

    result = {
        "github": github,
        "pypi": pypi,
        "gates": gates_status,
        "gates_summary": f"{gates_passed}/{gates_total} passed",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write as engram (compounds with prior metrics over time)
    if write_engram:
        result["engram_written"] = _write_metrics_engram(github, pypi, gates_passed, gates_total)

    return result


def _write_metrics_engram(
    github: Dict, pypi: Dict, gates_passed: int, gates_total: int
) -> bool:
    """Write a metrics snapshot as an engram."""
    try:
        from .engram_ops import _brain_write_engram_impl

        today = datetime.now().strftime("%Y%m%d")
        stars = github.get("stars", "?")
        forks = github.get("forks", "?")
        issues = github.get("open_issues", "?")
        pip_30d = pypi.get("last_month", "?")

        _brain_write_engram_impl(
            key=f"{METRICS_ENGRAM_PREFIX}{today}",
            value=(
                f"Growth metrics {datetime.now().strftime('%Y-%m-%d')}: "
                f"stars={stars} forks={forks} issues={issues} "
                f"pip_30d={pip_30d} gates={gates_passed}/{gates_total}"
            ),
            context="Strategy",
            intensity=6,
        )
        return True
    except Exception as e:
        logger.warning(f"Metrics engram write failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# DOGFOOD STREAK
# ═══════════════════════════════════════════════════════════════

def get_dogfood_streak() -> int:
    """Count unique days with growth_metrics engrams. This IS the dogfood proof."""
    try:
        from .engram_ops import _brain_search_engrams_impl

        result = json.loads(_brain_search_engrams_impl(query="growth_metrics", limit=100))
        engrams = result.get("data", {}).get("engrams", [])

        # Count unique date suffixes in keys
        dates = set()
        for e in engrams:
            key = e.get("key", "")
            if key.startswith(METRICS_ENGRAM_PREFIX):
                date_part = key[len(METRICS_ENGRAM_PREFIX):]
                if len(date_part) == 8 and date_part.isdigit():
                    dates.add(date_part)

        return len(dates)
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════
# GROWTH PULSE (the compound loop)
# ═══════════════════════════════════════════════════════════════

def growth_pulse(write_engrams: bool = True) -> Dict[str, Any]:
    """
    Execute the full growth pulse pipeline.

    Pipeline:
    1. BRIEF — Load growth context via morning brief
    2. METRICS — Capture GitHub + PyPI stats as engrams
    3. STREAK — Check dogfood consistency
    4. COMPOUND — Synthesize growth insights via fusion reactor

    This is the growth equivalent of pulse_and_polish.
    Designed to run daily (via cron, script, or MCP call).
    """
    start = time.time()
    result = {
        "pipeline": "growth_pulse",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sections": {},
        "meta": {"steps_completed": 0, "execution_time_ms": 0},
    }

    # Step 1: Morning Brief (loads growth context)
    try:
        from .morning_brief_ops import _morning_brief_impl
        brief = _morning_brief_impl()
        result["sections"]["brief"] = {
            "engram_count": brief.get("sections", {}).get("memory", {}).get("count", 0),
            "task_count": brief.get("sections", {}).get("tasks", {}).get("total_tasks", 0),
            "recommendation": brief.get("recommendation", {}).get("action", "none"),
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        result["sections"]["brief"] = {"error": str(e)}

    # Step 2: Metrics capture
    try:
        metrics = capture_metrics(write_engram=write_engrams)
        result["sections"]["metrics"] = {
            "stars": metrics.get("github", {}).get("stars", "?"),
            "forks": metrics.get("github", {}).get("forks", "?"),
            "pip_30d": metrics.get("pypi", {}).get("last_month", "?"),
            "gates_summary": metrics.get("gates_summary", "?"),
            "engram_written": metrics.get("engram_written", False),
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        result["sections"]["metrics"] = {"error": str(e)}

    # Step 3: Streak
    streak = get_dogfood_streak()
    result["sections"]["streak"] = {
        "days": streak,
        "target": GATES["dogfood_streak"],
        "passed": streak >= GATES["dogfood_streak"],
    }
    result["meta"]["steps_completed"] += 1

    # Step 4: Compound via fusion reactor
    if write_engrams:
        try:
            from .god_combos.fusion_reactor import run_fusion_reactor

            stars = result["sections"].get("metrics", {}).get("stars", "?")
            observation = (
                f"Growth pulse {datetime.now().strftime('%Y-%m-%d')}: "
                f"stars={stars}, streak={streak}d, "
                f"gates={result['sections'].get('metrics', {}).get('gates_summary', '?')}"
            )

            fusion = run_fusion_reactor(
                observation=observation,
                context="Strategy",
                intensity=7,
                write_engrams=True,
            )
            result["sections"]["compound"] = {
                "related_engrams": fusion.get("sections", {}).get("recall", {}).get("matches", 0),
                "engrams_written": fusion.get("meta", {}).get("engrams_written", 0),
            }
            result["meta"]["steps_completed"] += 1
        except Exception as e:
            result["sections"]["compound"] = {"error": str(e)}

    result["meta"]["execution_time_ms"] = round((time.time() - start) * 1000)
    return result


# ═══════════════════════════════════════════════════════════════
# GROWTH REPORT (from accumulated engrams)
# ═══════════════════════════════════════════════════════════════

def growth_report() -> Dict[str, Any]:
    """
    Generate a growth report from accumulated engrams.
    Shows metrics timeline, streak, gate status, and compound insights.
    """
    try:
        from .engram_ops import _brain_search_engrams_impl

        # Fetch all growth-related engrams
        raw = json.loads(_brain_search_engrams_impl(query="growth", limit=100))
        engrams = raw.get("data", {}).get("engrams", [])

        metrics_snapshots = []
        compound_insights = []
        other = []

        for e in engrams:
            key = e.get("key", "")
            if key.startswith(METRICS_ENGRAM_PREFIX):
                metrics_snapshots.append(e)
            elif "fusion" in key or "compound" in key:
                compound_insights.append(e)
            else:
                other.append(e)

        # Latest metrics
        latest_metrics = None
        if metrics_snapshots:
            latest = metrics_snapshots[-1]
            latest_metrics = latest.get("value", "")

        # Current gates
        current_gates = capture_metrics(write_engram=False).get("gates", {})

        return {
            "report_date": datetime.now(timezone.utc).isoformat(),
            "total_growth_engrams": len(engrams),
            "metrics_snapshots": len(metrics_snapshots),
            "compound_insights": len(compound_insights),
            "dogfood_streak": get_dogfood_streak(),
            "latest_metrics": latest_metrics,
            "gates": current_gates,
            "recent_insights": [
                {"key": e.get("key"), "value": e.get("value", "")[:150]}
                for e in compound_insights[-5:]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# LAUNCH TASK STATUS
# ═══════════════════════════════════════════════════════════════

def get_launch_tasks() -> Dict[str, Any]:
    """Get status of growth recipe tasks from the brain's task ledger."""
    try:
        brain = get_brain_path()
        tasks_file = brain / "ledger" / "tasks.json"

        if not tasks_file.exists():
            return {"error": "No tasks file — run 'nucleus init --recipe growth'", "tasks": []}

        tasks = json.loads(tasks_file.read_text())
        growth_tasks = [t for t in tasks if t.get("source", "").startswith("recipe:growth")]

        if not growth_tasks:
            return {"message": "No growth tasks — install growth recipe first", "tasks": []}

        done = [t for t in growth_tasks if t.get("status") == "DONE"]
        ready = [t for t in growth_tasks if t.get("status") == "READY"]

        return {
            "total": len(growth_tasks),
            "done": len(done),
            "ready": len(ready),
            "next_actions": [
                {"id": t.get("id"), "description": t.get("description", "")}
                for t in ready[:3]
            ],
            "completed": [
                {"id": t.get("id"), "description": t.get("description", "")}
                for t in done
            ],
        }
    except Exception as e:
        return {"error": str(e), "tasks": []}


# ═══════════════════════════════════════════════════════════════
# COMPOUND OBSERVATION (direct fusion reactor call)
# ═══════════════════════════════════════════════════════════════

def compound_growth_insight(observation: str, context: str = "Strategy") -> Dict[str, Any]:
    """
    Compound a growth observation into the brain via fusion reactor.

    This is the atomic unit of the growth flywheel:
    observe → recall related → synthesize → write higher-intensity engram.
    """
    try:
        from .god_combos.fusion_reactor import run_fusion_reactor

        return run_fusion_reactor(
            observation=observation,
            context=context,
            intensity=7,
            write_engrams=True,
        )
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# GROWTH EVENT HOOKS (reactive layer — the OS signal)
# ═══════════════════════════════════════════════════════════════
#
# Architecture: Wired into _emit_event() alongside engram_hooks.
# When a relevant event fires, growth compounds AUTOMATICALLY.
#
# This is what separates an OS from a toolkit:
#   engram_hooks: event → auto-memory
#   growth_hooks: event → auto-compound growth signal
#
# SAFETY: Same pattern as engram_hooks — try/except pass, never
# blocks event emission. Worst case = metric logged, event proceeds.
#
# THROTTLE: Growth hooks are expensive (API calls, fusion reactor).
# We throttle to max 1 compound per event type per hour to prevent
# runaway costs during high-activity sessions.
# ═══════════════════════════════════════════════════════════════

# Events that trigger growth compounding
GROWTH_TRIGGER_EVENTS = {
    "morning_brief_generated": {
        "action": "compound",
        "template": "Morning brief completed — {engram_count} engrams, {task_count} tasks. Recommendation: {action}",
    },
    "task_completed_with_fence": {
        "action": "compound",
        "template": "Task {task_id} completed ({outcome}). Growth signal: productivity evidence.",
    },
    "deploy_complete": {
        "action": "compound",
        "template": "Deployment complete: {service_id} — {status}. Growth signal: shipping velocity.",
    },
    "sprint_started": {
        "action": "compound",
        "template": "Sprint {sprint_id} started with {tasks_assigned} tasks. Growth signal: execution cadence.",
    },
    "session_ended": {
        "action": "compound",
        "template": "Session ended ({mood}): {summary}. Growth signal: consistency.",
    },
    "outbound_posted": {
        "action": "compound",
        "template": "Posted to {channel}: {title}. Permalink: {permalink}. Growth signal: distribution velocity.",
    },
}

# Throttle state: {event_type: last_fired_timestamp}
_growth_hook_last_fired: Dict[str, float] = {}
GROWTH_HOOK_COOLDOWN_SECONDS = 3600  # 1 hour between fires per event type


def process_event_for_growth(event_type: str, event_data: Dict[str, Any]) -> Optional[Dict]:
    """
    Growth hook entry point — called from _emit_event() for every event.

    Same contract as engram_hooks.process_event_for_engram():
    - Called for EVERY event
    - NEVER blocks event emission (try/except)
    - Returns result dict or None

    Throttled: max 1 compound per event type per hour.
    """
    if event_type not in GROWTH_TRIGGER_EVENTS:
        return None

    # Throttle check
    now = time.time()
    last = _growth_hook_last_fired.get(event_type, 0)
    if (now - last) < GROWTH_HOOK_COOLDOWN_SECONDS:
        return None

    try:
        config = GROWTH_TRIGGER_EVENTS[event_type]

        # Build observation from template
        safe_data = {k: str(v)[:100] for k, v in event_data.items()} if event_data else {}
        try:
            observation = config["template"].format_map(type('SafeDict', (dict,), {'__missing__': lambda s, k: '?'})(safe_data))
        except Exception:
            observation = f"Growth signal from {event_type}"

        # Record throttle
        _growth_hook_last_fired[event_type] = now

        # Write as growth engram (lightweight — no fusion reactor, just engram)
        try:
            from .engram_ops import _brain_write_engram_impl

            ts = int(now) % 100000
            _brain_write_engram_impl(
                key=f"{GROWTH_ENGRAM_PREFIX}hook_{event_type}_{ts}",
                value=observation,
                context="Strategy",
                intensity=5,
            )
            logger.info(f"📈 Growth hook fired: [{event_type}]")
            return {"event_type": event_type, "action": "engram_written", "observation": observation}
        except Exception as e:
            logger.warning(f"Growth hook engram write failed: {e}")
            return None

    except Exception as e:
        logger.warning(f"Growth hook failed (non-fatal): {e}")
        return None


def reset_growth_hook_throttle() -> None:
    """Reset throttle state — useful for testing."""
    _growth_hook_last_fired.clear()
