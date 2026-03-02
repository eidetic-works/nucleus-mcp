"""Self-Healing SRE God Combo — Diagnosis to Resolution.

Pipeline: search_engrams → performance_metrics → diagnosis → recommendation

This combo automates the SRE triage loop:
1. SEARCH — Find engrams matching a symptom pattern
2. METRICS — Collect performance metrics for correlation
3. DIAGNOSE — Correlate symptoms with metrics to identify root cause
4. RECOMMEND — Generate actionable fix recommendation

Circuit breakers:
- Max execution time: 30 seconds
- Read-only: no destructive actions (diagnosis only)

Usage:
    from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
    result = run_self_healing_sre(symptom="high latency")
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("nucleus.god_combos.self_healing_sre")

MAX_EXECUTION_SECONDS = 30


def run_self_healing_sre(symptom: str, write_engram: bool = True) -> Dict[str, Any]:
    """Execute the Self-Healing SRE pipeline.
    
    Args:
        symptom: Description of the issue to diagnose (e.g. "high latency", "dispatch errors").
        write_engram: Whether to write a diagnosis engram. Default True.
        
    Returns:
        Dict with sections: search, metrics, diagnosis, recommendation, meta.
    """
    start = time.time()
    result = {
        "pipeline": "self_healing_sre",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "symptom": symptom,
        "sections": {},
        "diagnosis": None,
        "recommendation": None,
        "meta": {"steps_completed": 0, "execution_time_ms": 0, "circuit_breaker_hit": False},
    }

    def _check_timeout():
        elapsed = time.time() - start
        if elapsed > MAX_EXECUTION_SECONDS:
            result["meta"]["circuit_breaker_hit"] = True
            return True
        return False

    # ── STEP 1: SEARCH — Find related engrams ────────────────
    try:
        from ..engram_ops import _brain_search_engrams_impl
        search_raw = _brain_search_engrams_impl(query=symptom, limit=10)
        search_data = json.loads(search_raw)
        
        engrams = search_data.get("data", {}).get("engrams", [])
        
        result["sections"]["search"] = {
            "query": symptom,
            "matches": len(engrams),
            "total_available": search_data.get("data", {}).get("total_matching", 0),
            "top_keys": [e.get("key", "?")[:60] for e in engrams[:5]],
            "contexts": list(set(e.get("context", "Unknown") for e in engrams)),
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        logger.warning(f"Search step failed: {e}")
        result["sections"]["search"] = {"error": str(e), "matches": 0}

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 2: METRICS — Collect performance data ────────────
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
        
        result["sections"]["metrics"] = {
            "dispatch_total": dispatch_total,
            "dispatch_errors": dispatch_errors,
            "error_rate_pct": round(error_rate, 2),
            "latency_avg_ms": round(latency_avg, 2),
        }
        result["meta"]["steps_completed"] += 1
    except Exception as e:
        logger.warning(f"Metrics step failed: {e}")
        result["sections"]["metrics"] = {"error": str(e)}

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 3: DIAGNOSE — Correlate symptoms with data ──────
    search_section = result["sections"].get("search", {})
    metrics_section = result["sections"].get("metrics", {})
    
    severity = "LOW"
    findings = []
    
    error_rate = metrics_section.get("error_rate_pct", 0)
    latency = metrics_section.get("latency_avg_ms", 0)
    engram_matches = search_section.get("matches", 0)
    
    if error_rate > 20:
        severity = "CRITICAL"
        findings.append(f"Error rate is {error_rate}% (threshold: 20%)")
    elif error_rate > 5:
        severity = "HIGH"
        findings.append(f"Error rate is {error_rate}% (threshold: 5%)")
    
    if latency > 1000:
        if severity == "LOW":
            severity = "HIGH"
        findings.append(f"Average latency {latency}ms exceeds 1000ms threshold")
    elif latency > 500:
        if severity == "LOW":
            severity = "MEDIUM"
        findings.append(f"Average latency {latency}ms approaching threshold")
    
    if engram_matches > 0:
        findings.append(f"Found {engram_matches} related engrams — prior knowledge exists")
    else:
        findings.append("No prior engrams match this symptom — novel issue")

    if not findings:
        findings.append("No anomalies detected in current metrics")
    
    diagnosis = {
        "severity": severity,
        "findings": findings,
        "symptom": symptom,
        "correlated_contexts": search_section.get("contexts", []),
    }
    result["diagnosis"] = diagnosis
    result["meta"]["steps_completed"] += 1

    if _check_timeout():
        return _finalize(result, start)

    # ── STEP 4: RECOMMEND — Generate action plan ─────────────
    if severity == "CRITICAL":
        action = f"IMMEDIATE: Investigate dispatch errors ({error_rate}%). Check auto_fix_loop or manual review."
    elif severity == "HIGH":
        action = f"URGENT: Review error rate ({error_rate}%) and latency ({latency}ms). Check recent deployments."
    elif severity == "MEDIUM":
        action = f"MONITOR: Latency trending up ({latency}ms). Schedule performance review."
    else:
        action = "ALL CLEAR: No action needed. System operating within normal parameters."

    result["recommendation"] = {
        "action": action,
        "severity": severity,
        "auto_fixable": severity in ("LOW", "MEDIUM"),
    }
    result["meta"]["steps_completed"] += 1

    if write_engram:
        try:
            from ..engram_ops import _brain_write_engram_impl
            engram_value = (
                f"SRE Diagnosis {datetime.now().strftime('%Y-%m-%d %H:%M')}: "
                f"symptom='{symptom}' severity={severity} "
                f"findings={len(findings)} "
                f"action={action[:80]}"
            )
            _brain_write_engram_impl(
                key=f"sre_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M')}",
                value=engram_value,
                context="Architecture",
                intensity=8 if severity in ("CRITICAL", "HIGH") else 5,
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
