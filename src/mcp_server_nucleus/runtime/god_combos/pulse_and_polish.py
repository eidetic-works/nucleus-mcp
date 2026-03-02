"""Pulse & Polish God Combo — Automated Chief of Staff.

Pipeline: prometheus_metrics → audit_log → morning_brief → engram
    
This combo runs the daily operational health check:
1. PULSE — Collect Prometheus metrics (dispatch counts, errors, latency)
2. AUDIT — Scan recent audit log for anomalies (errors, high-latency)
3. BRIEF — Generate morning brief (memory + tasks + yesterday)
4. POLISH — Write a synthesis engram summarizing the health snapshot

Circuit breakers:
- Max execution time: 30 seconds
- Max engram writes per run: 1

Usage:
    from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
    result = run_pulse_and_polish()
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("nucleus.god_combos.pulse_and_polish")

MAX_EXECUTION_SECONDS = 30


def run_pulse_and_polish(write_engram: bool = True) -> Dict[str, Any]:
    """Execute the Pulse & Polish pipeline.
    
    Args:
        write_engram: Whether to write a synthesis engram at the end. Default True.
        
    Returns:
        Dict with sections: pulse, audit, brief, synthesis, meta.
    """
    start = time.time()
    result = {
        "pipeline": "pulse_and_polish",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "sections": {},
        "synthesis": None,
        "meta": {"steps_completed": 0, "execution_time_ms": 0, "circuit_breaker_hit": False},
    }

    def _check_timeout():
        elapsed = time.time() - start
        if elapsed > MAX_EXECUTION_SECONDS:
            result["meta"]["circuit_breaker_hit"] = True
            return True
        return False

    # ── STEP 1: PULSE — Prometheus Metrics ────────────────────
    try:
        from ..prometheus import get_prometheus_metrics
        raw_metrics = get_prometheus_metrics()
        
        dispatch_total = 0
        dispatch_errors = 0
        latency_avg = 0.0
        
        for line in raw_metrics.split("\n"):
            if line.startswith("nucleus_dispatch_total"):
                try:
                    dispatch_total = int(float(line.split()[-1]))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("nucleus_dispatch_errors_total"):
                try:
                    dispatch_errors = int(float(line.split()[-1]))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("nucleus_dispatch_latency_avg_ms"):
                try:
                    latency_avg = float(line.split()[-1])
                except (ValueError, IndexError):
                    pass

        error_rate = (dispatch_errors / dispatch_total * 100) if dispatch_total > 0 else 0.0
        
        result["sections"]["pulse"] = {
            "dispatch_total": dispatch_total,
            "dispatch_errors": dispatch_errors,
            "error_rate_pct": round(error_rate, 2),
            "latency_avg_ms": round(latency_avg, 2),
            "health": "🟢 HEALTHY" if error_rate < 5 else ("🟡 DEGRADED" if error_rate < 20 else "🔴 CRITICAL"),
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        logger.warning(f"Pulse step failed: {e}")
        result["sections"]["pulse"] = {"error": str(e), "health": "⚪ UNKNOWN"}

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 2: AUDIT — Recent Audit Log ──────────────────────
    try:
        from ..engram_ops import _brain_audit_log_impl
        audit_raw = _brain_audit_log_impl(limit=20)
        audit_data = json.loads(audit_raw)
        
        entries = audit_data.get("data", {}).get("entries", [])
        entry_count = len(entries)
        
        error_entries = [e for e in entries if "error" in str(e).lower()]
        
        result["sections"]["audit"] = {
            "recent_entries": entry_count,
            "error_entries": len(error_entries),
            "health": "🟢 CLEAN" if len(error_entries) == 0 else "🟡 HAS_ERRORS",
            "sample_errors": [str(e)[:100] for e in error_entries[:3]],
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        logger.warning(f"Audit step failed: {e}")
        result["sections"]["audit"] = {"error": str(e), "health": "⚪ UNKNOWN"}

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 3: BRIEF — Morning Brief ────────────────────────
    try:
        from ..morning_brief_ops import _morning_brief_impl
        brief = _morning_brief_impl()
        
        result["sections"]["brief"] = {
            "engram_count": brief.get("sections", {}).get("memory", {}).get("count", 0),
            "task_count": brief.get("sections", {}).get("tasks", {}).get("total_tasks", 0),
            "recommendation": brief.get("recommendation", {}).get("action", "No recommendation"),
            "generation_time_ms": brief.get("meta", {}).get("generation_time_ms", 0),
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        logger.warning(f"Brief step failed: {e}")
        result["sections"]["brief"] = {"error": str(e)}

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 4: POLISH — Synthesize + Write Engram ────────────
    pulse = result["sections"].get("pulse", {})
    audit = result["sections"].get("audit", {})
    brief_section = result["sections"].get("brief", {})

    health_signals = []
    if pulse.get("health", "").startswith("🟢"):
        health_signals.append("dispatch_healthy")
    elif pulse.get("health", "").startswith("🔴"):
        health_signals.append("dispatch_CRITICAL")
    if audit.get("health", "").startswith("🟢"):
        health_signals.append("audit_clean")
    elif audit.get("error_entries", 0) > 0:
        health_signals.append(f"audit_errors:{audit['error_entries']}")

    overall_health = "🟢 OPERATIONAL"
    if any("CRITICAL" in s for s in health_signals):
        overall_health = "🔴 CRITICAL"
    elif any("error" in s for s in health_signals):
        overall_health = "🟡 DEGRADED"

    synthesis = {
        "overall_health": overall_health,
        "health_signals": health_signals,
        "dispatch_total": pulse.get("dispatch_total", 0),
        "error_rate_pct": pulse.get("error_rate_pct", 0),
        "task_count": brief_section.get("task_count", 0),
        "recommendation": brief_section.get("recommendation", ""),
    }
    result["synthesis"] = synthesis
    result["meta"]["steps_completed"] += 1

    if write_engram:
        try:
            from ..engram_ops import _brain_write_engram_impl
            engram_value = (
                f"Pulse&Polish {datetime.now().strftime('%Y-%m-%d %H:%M')}: "
                f"{overall_health} | dispatches={pulse.get('dispatch_total', 0)} "
                f"err_rate={pulse.get('error_rate_pct', 0)}% "
                f"tasks={brief_section.get('task_count', 0)} "
                f"rec={brief_section.get('recommendation', 'none')[:80]}"
            )
            _brain_write_engram_impl(
                key=f"pulse_and_polish_{datetime.now().strftime('%Y%m%d_%H%M')}",
                value=engram_value,
                context="Strategy",
                intensity=7,
            )
            result["meta"]["engram_written"] = True
        except Exception as e:
            logger.warning(f"Engram write failed: {e}")
            result["meta"]["engram_written"] = False

    return _finalize(result, start)


def _finalize(result: Dict, start: float) -> Dict:
    """Add final timing metadata."""
    elapsed = (time.time() - start) * 1000
    result["meta"]["execution_time_ms"] = round(elapsed, 1)
    return result
