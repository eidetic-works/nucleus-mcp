"""
Nucleus Runtime - Founder Absence Readiness (Atom B)
=====================================================
Manages quiescent-mode / founder-offline states to ensure
the platform maintains basic autonomy (C6 §8).
"""

import time
import logging
from typing import Dict, Any, List

from .health_check import get_health_status, HealthStatus
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.founder_absence")

def can_discover_tools() -> bool:
    """Check if tool discovery registry is operational."""
    try:
        from .marketplace import CapabilityRegistry
        from .common import get_brain_path
        registry = CapabilityRegistry(get_brain_path())
        # Try to read the registry
        _ = registry.find_tools(query="test")
        return True
    except Exception:
        return False

def can_route_messages() -> bool:
    """Check if relay queue partition scheme is functional."""
    try:
        from .relay_ops import list_inbox
        _ = list_inbox("cowork", limit=1)
        return True
    except Exception:
        return False

def can_rebuild_memory_index() -> bool:
    """Check if engram cache/ledger is accessible."""
    from .health_check import check_engram_ledger
    status = check_engram_ledger()
    return status.get("status") in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

def can_triage_alerts() -> bool:
    """Check if task ops are operational for alert creation."""
    try:
        from .task_ops import _list_tasks
        _ = _list_tasks(limit=1)
        return True
    except Exception:
        return False

def are_endpoints_monitored() -> bool:
    """Check if circuit breakers and health endpoints are up."""
    from .health_check import check_circuit_breakers
    status = check_circuit_breakers()
    return status.get("status") in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

def can_generate_reports() -> bool:
    """Check if reporting/ledger access is up."""
    from .health_check import check_event_log
    status = check_event_log()
    return status.get("status") in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

def readiness_score() -> float:
    """
    Calculate autonomous readiness score (0.0 to 1.0) based on critical capabilities.
    1.0 = fully autonomous.
    """
    checks = [
        can_discover_tools(),
        can_route_messages(),
        can_rebuild_memory_index(),
        can_triage_alerts(),
        are_endpoints_monitored(),
        can_generate_reports()
    ]
    passed = sum(1 for c in checks if c)
    return passed / len(checks) if checks else 0.0

def enter_quiescent_mode(duration_hours: int = 12) -> Dict[str, Any]:
    """
    Enable founder offline mode. Triggers autonomous maintenance loops.
    """
    score = readiness_score()
    
    if score < 0.5:
        logger.warning(f"Refusing quiescent mode: readiness score {score:.2f} is too low.")
        return {"success": False, "error": "Readiness too low", "score": score}
        
    _emit_event("founder_absence_started", "nucleus_absence", {
        "duration_hours": duration_hours,
        "readiness_score": score
    })
    
    # Auto-run maintenance tasks that usually require founder oversight
    maintenance_results = run_autonomous_maintenance()
    
    return {
        "success": True,
        "mode": "quiescent",
        "duration_hours": duration_hours,
        "readiness_score": score,
        "maintenance_results": maintenance_results
    }

def run_autonomous_maintenance() -> Dict[str, Any]:
    """
    Auto-execute background tasks during founder offline window.
    """
    results = {}
    
    # 1. Stale Registry Prune (from Atom 3)
    try:
        from .marketplace import CapabilityRegistry
        from .common import get_brain_path
        registry = CapabilityRegistry(get_brain_path())
        stale_count = registry.mark_stale()
        results["registry_stale_prune"] = {"status": "success", "count": stale_count}
    except Exception as e:
        results["registry_stale_prune"] = {"status": "error", "error": str(e)}
        
    # 2. Apply Reputation Decay (from Atom 2)
    try:
        from .marketplace import ReputationSignals
        from .common import get_brain_path
        signals = ReputationSignals(get_brain_path())
        signals.apply_decay()
        results["reputation_decay"] = {"status": "success"}
    except Exception as e:
        results["reputation_decay"] = {"status": "error", "error": str(e)}
        
    # More maintenance can be added here (dedup, alert triage, etc.)
    
    _emit_event("autonomous_maintenance_completed", "nucleus_absence", {
        "results": results
    })
    
    return results
