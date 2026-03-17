"""
Nucleus Runtime - Health Check (Enterprise Operations)
=======================================================
Provides health status for load balancers and monitoring.

OPERATIONS: This module addresses vulnerability C38 identified in
the exhaustive design thinking analysis (Feb 24, 2026).

Problem: No HTTP health endpoint for load balancer integration
Solution: Health check functions + optional HTTP server

References:
- Evidence: E062
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("nucleus.health_check")


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


def check_brain_path() -> Dict[str, Any]:
    """Check if brain path is accessible."""
    from .common import get_brain_path
    
    try:
        brain = get_brain_path()
        exists = brain.exists()
        writable = os.access(brain, os.W_OK) if exists else False
        
        return {
            "component": "brain_path",
            "status": HealthStatus.HEALTHY if (exists and writable) else HealthStatus.UNHEALTHY,
            "path": str(brain),
            "exists": exists,
            "writable": writable,
        }
    except Exception as e:
        return {
            "component": "brain_path",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def check_engram_ledger() -> Dict[str, Any]:
    """Check engram ledger health."""
    from .common import get_brain_path
    
    try:
        brain = get_brain_path()
        ledger_path = brain / "engrams" / "ledger.jsonl"
        
        if not ledger_path.exists():
            return {
                "component": "engram_ledger",
                "status": HealthStatus.HEALTHY,
                "exists": False,
                "count": 0,
                "message": "Ledger not yet created (normal for new brain)",
            }
        
        # Count engrams
        count = 0
        corrupted = 0
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        json.loads(line)
                        count += 1
                    except json.JSONDecodeError:
                        corrupted += 1
        
        status = HealthStatus.HEALTHY
        if corrupted > 0:
            status = HealthStatus.DEGRADED if corrupted < count * 0.1 else HealthStatus.UNHEALTHY
        
        return {
            "component": "engram_ledger",
            "status": status,
            "exists": True,
            "count": count,
            "corrupted_lines": corrupted,
        }
    except Exception as e:
        return {
            "component": "engram_ledger",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def check_event_log() -> Dict[str, Any]:
    """Check event log health."""
    from .common import get_brain_path
    
    try:
        brain = get_brain_path()
        events_path = brain / "ledger" / "events.jsonl"
        
        if not events_path.exists():
            return {
                "component": "event_log",
                "status": HealthStatus.HEALTHY,
                "exists": False,
                "count": 0,
            }
        
        # Count events and check recency
        count = 0
        last_event_time = None
        
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        count += 1
                        if "timestamp" in event:
                            last_event_time = event["timestamp"]
                    except json.JSONDecodeError:
                        pass
        
        return {
            "component": "event_log",
            "status": HealthStatus.HEALTHY,
            "exists": True,
            "count": count,
            "last_event": last_event_time,
        }
    except Exception as e:
        return {
            "component": "event_log",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def check_hardening() -> Dict[str, Any]:
    """Check hardening module status."""
    try:
        from .hardening import get_hardening_status
        status = get_hardening_status()
        
        return {
            "component": "hardening",
            "status": HealthStatus.HEALTHY,
            "version": status.get("hardening_version", "unknown"),
            "components": status.get("components", {}),
            "enterprise_ready": status.get("enterprise_ready", False),
        }
    except ImportError:
        return {
            "component": "hardening",
            "status": HealthStatus.DEGRADED,
            "message": "Hardening module not available",
        }
    except Exception as e:
        return {
            "component": "hardening",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def check_rate_limiter() -> Dict[str, Any]:
    """Check rate limiter status."""
    try:
        from .rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()
        stats = limiter.get_stats()
        
        return {
            "component": "rate_limiter",
            "status": HealthStatus.HEALTHY,
            "stats": stats,
        }
    except ImportError:
        return {
            "component": "rate_limiter",
            "status": HealthStatus.DEGRADED,
            "message": "Rate limiter not available",
        }
    except Exception as e:
        return {
            "component": "rate_limiter",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def get_health_status(include_details: bool = True) -> Dict[str, Any]:
    """
    Get comprehensive health status.
    
    Args:
        include_details: Include detailed component status
        
    Returns:
        Health status dict suitable for JSON response
    """
    start = time.time()
    
    # Run all checks
    checks = [
        check_brain_path(),
        check_engram_ledger(),
        check_event_log(),
        check_hardening(),
        check_rate_limiter(),
    ]
    
    # Determine overall status
    statuses = [c["status"] for c in checks]
    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED
    
    elapsed_ms = (time.time() - start) * 1000
    
    response = {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "response_time_ms": round(elapsed_ms, 2),
        "version": "1.0.0",
    }
    
    if include_details:
        response["components"] = checks
    
    return response


def get_liveness() -> Dict[str, Any]:
    """
    Simple liveness check for Kubernetes.
    
    Returns minimal response to indicate process is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_readiness() -> Dict[str, Any]:
    """
    Readiness check for Kubernetes.
    
    Checks if service is ready to receive traffic.
    """
    health = get_health_status(include_details=False)
    ready = health["status"] != HealthStatus.UNHEALTHY
    
    return {
        "ready": ready,
        "status": health["status"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# MCP Tool implementation
def _brain_health_impl() -> Dict[str, Any]:
    """Implementation for brain_health MCP tool."""
    return get_health_status(include_details=True)
