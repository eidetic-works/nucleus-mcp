"""
Nucleus Runtime - Performance Profiling (AG-014)
=================================================
Timing decorators and performance monitoring for identifying bottlenecks.

Usage:
    from .profiling import timed, get_metrics, reset_metrics

    @timed("task_list")
    def _list_tasks(...):
        ...

    # Get metrics
    metrics = get_metrics()
    print(metrics["task_list"])  # {"calls": 10, "total_ms": 150.5, "avg_ms": 15.05}
"""

import time
import functools
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timezone
import json
import os
from pathlib import Path

# Thread-safe metrics storage
_metrics_lock = threading.Lock()
_metrics: Dict[str, Dict[str, Any]] = {}

# Configuration
PROFILING_ENABLED = os.environ.get("NUCLEUS_PROFILING", "false").lower() == "true"
SLOW_THRESHOLD_MS = float(os.environ.get("NUCLEUS_SLOW_THRESHOLD_MS", "100"))


def timed(operation_name: str, log_slow: bool = True):
    """
    Decorator to time function execution and collect metrics.
    
    Args:
        operation_name: Name for this operation in metrics
        log_slow: Whether to log warning for slow operations
    
    Example:
        @timed("brain_list_tasks")
        def _list_tasks():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not PROFILING_ENABLED:
                return func(*args, **kwargs)
            
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _record_metric(operation_name, elapsed_ms, log_slow)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not PROFILING_ENABLED:
                return await func(*args, **kwargs)
            
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                _record_metric(operation_name, elapsed_ms, log_slow)
        
        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


def asyncio_iscoroutinefunction(func):
    """Check if function is async."""
    import inspect
    return inspect.iscoroutinefunction(func)


def _record_metric(operation_name: str, elapsed_ms: float, log_slow: bool):
    """Record a timing metric (thread-safe)."""
    with _metrics_lock:
        if operation_name not in _metrics:
            _metrics[operation_name] = {
                "calls": 0,
                "total_ms": 0.0,
                "min_ms": float('inf'),
                "max_ms": 0.0,
                "last_call": None,
                "slow_count": 0
            }
        
        m = _metrics[operation_name]
        m["calls"] += 1
        m["total_ms"] += elapsed_ms
        m["min_ms"] = min(m["min_ms"], elapsed_ms)
        m["max_ms"] = max(m["max_ms"], elapsed_ms)
        m["last_call"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        if elapsed_ms > SLOW_THRESHOLD_MS:
            m["slow_count"] += 1
            if log_slow:
                # Use print for now, can integrate with structured logging
                print(f"⚠️ SLOW: {operation_name} took {elapsed_ms:.2f}ms (threshold: {SLOW_THRESHOLD_MS}ms)")


def get_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Get current performance metrics.
    
    Returns:
        Dict with metrics per operation:
        {
            "operation_name": {
                "calls": int,
                "total_ms": float,
                "avg_ms": float,
                "min_ms": float,
                "max_ms": float,
                "slow_count": int,
                "last_call": str (ISO timestamp)
            }
        }
    """
    with _metrics_lock:
        result = {}
        for name, m in _metrics.items():
            result[name] = {
                **m,
                "avg_ms": m["total_ms"] / m["calls"] if m["calls"] > 0 else 0
            }
            # Clean up inf for JSON serialization
            if result[name]["min_ms"] == float('inf'):
                result[name]["min_ms"] = 0
        return result


def reset_metrics():
    """Reset all metrics (useful for testing)."""
    global _metrics
    with _metrics_lock:
        _metrics = {}


def get_metrics_summary() -> str:
    """Get a formatted summary of metrics."""
    metrics = get_metrics()
    if not metrics:
        return "No metrics collected. Set NUCLEUS_PROFILING=true to enable."
    
    lines = ["# Performance Metrics", ""]
    lines.append("| Operation | Calls | Avg (ms) | Min | Max | Slow |")
    lines.append("|-----------|-------|----------|-----|-----|------|")
    
    for name, m in sorted(metrics.items(), key=lambda x: -x[1]["total_ms"]):
        lines.append(
            f"| {name} | {m['calls']} | {m['avg_ms']:.2f} | "
            f"{m['min_ms']:.2f} | {m['max_ms']:.2f} | {m['slow_count']} |"
        )
    
    lines.append("")
    lines.append(f"*Slow threshold: {SLOW_THRESHOLD_MS}ms*")
    return "\n".join(lines)


def export_metrics_to_file(brain_path: Optional[Path] = None) -> str:
    """
    Export metrics to a JSON file in the brain folder.
    
    Args:
        brain_path: Path to brain folder (uses env var if not provided)
    
    Returns:
        Path to exported file
    """
    if brain_path is None:
        brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".brain"))
    
    metrics_dir = brain_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = metrics_dir / f"perf_{timestamp}.json"
    
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "threshold_ms": SLOW_THRESHOLD_MS,
        "metrics": get_metrics()
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return str(filepath)


# Convenience decorators for common operations
def timed_io(func):
    """Decorator for I/O-bound operations (file reads, etc.)."""
    return timed(f"io.{func.__name__}", log_slow=True)(func)


def timed_compute(func):
    """Decorator for compute-bound operations."""
    return timed(f"compute.{func.__name__}", log_slow=True)(func)


def timed_llm(func):
    """Decorator for LLM API calls (expected to be slow)."""
    return timed(f"llm.{func.__name__}", log_slow=False)(func)
