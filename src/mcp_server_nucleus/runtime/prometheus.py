"""
Nucleus Runtime - Prometheus Metrics (AG-015)
==============================================
Prometheus-compatible metrics endpoint for monitoring Nucleus.

Usage:
    # In your monitoring setup, scrape:
    # GET /metrics (if HTTP server enabled)
    # OR call brain_prometheus_metrics() MCP tool

    # Metrics exported:
    # - nucleus_tool_calls_total{tool="nucleus_engrams"} 
    # - nucleus_tool_errors_total{tool="nucleus_governance"}
    # - nucleus_tool_latency_seconds{tool="nucleus_tasks",quantile="0.5"}
    # - nucleus_dispatch_total{facade="nucleus_tasks",action="add"}
    # - nucleus_tasks_total{status="PENDING"}
    # - nucleus_sessions_total
    # - nucleus_events_total
"""

import time
import threading
from typing import Dict, Any, List
from datetime import datetime, timezone
from collections import defaultdict
import os
import json
from pathlib import Path

# Thread-safe metrics storage
_metrics_lock = threading.Lock()

# Counters
_tool_calls: Dict[str, int] = defaultdict(int)
_tool_errors: Dict[str, int] = defaultdict(int)

# Histograms (simplified - store recent latencies)
_tool_latencies: Dict[str, List[float]] = defaultdict(list)
MAX_LATENCY_SAMPLES = 1000  # Keep last N samples per tool

# Gauges (current values)
_gauges: Dict[str, float] = {}

# Configuration
METRICS_ENABLED = os.environ.get("NUCLEUS_METRICS", "true").lower() == "true"


def inc_counter(name: str, labels: Dict[str, str] = None, value: int = 1):
    """Increment a counter metric."""
    if not METRICS_ENABLED:
        return
    
    key = _make_key(name, labels)
    with _metrics_lock:
        if name.endswith("_errors"):
            _tool_errors[key] += value
        else:
            _tool_calls[key] += value


def observe_latency(tool_name: str, latency_seconds: float):
    """Record a latency observation for a tool."""
    if not METRICS_ENABLED:
        return
    
    with _metrics_lock:
        latencies = _tool_latencies[tool_name]
        latencies.append(latency_seconds)
        # Keep bounded
        if len(latencies) > MAX_LATENCY_SAMPLES:
            _tool_latencies[tool_name] = latencies[-MAX_LATENCY_SAMPLES:]


def set_gauge(name: str, value: float, labels: Dict[str, str] = None):
    """Set a gauge metric to a specific value."""
    if not METRICS_ENABLED:
        return
    
    key = _make_key(name, labels)
    with _metrics_lock:
        _gauges[key] = value


def _make_key(name: str, labels: Dict[str, str] = None) -> str:
    """Create a metric key from name and labels."""
    if not labels:
        return name
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{label_str}}}"


def _calculate_quantiles(values: List[float], quantiles: List[float] = [0.5, 0.9, 0.99]) -> Dict[str, float]:
    """Calculate quantiles from a list of values."""
    if not values:
        return {str(q): 0.0 for q in quantiles}
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    result = {}
    
    for q in quantiles:
        idx = int(q * n)
        if idx >= n:
            idx = n - 1
        result[str(q)] = sorted_values[idx]
    
    return result


def get_prometheus_metrics() -> str:
    """
    Generate Prometheus text format metrics.
    
    Returns:
        Prometheus exposition format string
    """
    lines = []
    
    # Header
    lines.append("# Nucleus MCP Server Metrics")
    lines.append(f"# Generated at {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    
    with _metrics_lock:
        # Tool call counters
        lines.append("# HELP nucleus_tool_calls_total Total number of tool calls")
        lines.append("# TYPE nucleus_tool_calls_total counter")
        for key, value in _tool_calls.items():
            lines.append(f"nucleus_tool_calls_total{{{_extract_labels(key)}}} {value}")
        
        # Tool error counters
        lines.append("")
        lines.append("# HELP nucleus_tool_errors_total Total number of tool errors")
        lines.append("# TYPE nucleus_tool_errors_total counter")
        for key, value in _tool_errors.items():
            lines.append(f"nucleus_tool_errors_total{{{_extract_labels(key)}}} {value}")
        
        # Latency histograms (as summary with quantiles)
        lines.append("")
        lines.append("# HELP nucleus_tool_latency_seconds Tool execution latency")
        lines.append("# TYPE nucleus_tool_latency_seconds summary")
        for tool_name, latencies in _tool_latencies.items():
            if latencies:
                quantiles = _calculate_quantiles(latencies)
                for q, v in quantiles.items():
                    lines.append(f'nucleus_tool_latency_seconds{{tool="{tool_name}",quantile="{q}"}} {v:.6f}')
                lines.append(f'nucleus_tool_latency_seconds_sum{{tool="{tool_name}"}} {sum(latencies):.6f}')
                lines.append(f'nucleus_tool_latency_seconds_count{{tool="{tool_name}"}} {len(latencies)}')
        
        # Gauges
        lines.append("")
        lines.append("# HELP nucleus_gauge Current gauge values")
        lines.append("# TYPE nucleus_gauge gauge")
        for key, value in _gauges.items():
            lines.append(f"nucleus_gauge{{{_extract_labels(key)}}} {value}")
    
    # Add dispatch telemetry metrics (from _dispatch.py)
    try:
        from mcp_server_nucleus.tools._dispatch import get_dispatch_telemetry
        dt = get_dispatch_telemetry().get_metrics()
        if dt["total_dispatches"] > 0:
            lines.append("")
            lines.append("# HELP nucleus_dispatch_total Total facade action dispatches")
            lines.append("# TYPE nucleus_dispatch_total counter")
            for action_key, stats in dt.get("top_10_actions", {}).items():
                parts = action_key.split(".", 1)
                facade = parts[0] if len(parts) > 1 else "unknown"
                action = parts[1] if len(parts) > 1 else parts[0]
                lines.append(f'nucleus_dispatch_total{{facade="{facade}",action="{action}"}} {stats["calls"]}')
            
            lines.append("")
            lines.append("# HELP nucleus_dispatch_errors_total Total facade dispatch errors")
            lines.append("# TYPE nucleus_dispatch_errors_total counter")
            for action_key, stats in dt.get("top_10_actions", {}).items():
                if stats["errors"] > 0:
                    parts = action_key.split(".", 1)
                    facade = parts[0] if len(parts) > 1 else "unknown"
                    action = parts[1] if len(parts) > 1 else parts[0]
                    lines.append(f'nucleus_dispatch_errors_total{{facade="{facade}",action="{action}"}} {stats["errors"]}')
            
            lines.append("")
            lines.append("# HELP nucleus_dispatch_latency_avg_ms Average dispatch latency in ms")
            lines.append("# TYPE nucleus_dispatch_latency_avg_ms gauge")
            for action_key, stats in dt.get("top_10_actions", {}).items():
                parts = action_key.split(".", 1)
                facade = parts[0] if len(parts) > 1 else "unknown"
                action = parts[1] if len(parts) > 1 else parts[0]
                lines.append(f'nucleus_dispatch_latency_avg_ms{{facade="{facade}",action="{action}"}} {stats["avg_ms"]}')
    except Exception:
        pass  # Silently skip dispatch metrics if unavailable

    # Add brain state metrics if available
    try:
        brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".brain"))
        
        # Task counts by status
        tasks_file = brain_path / "ledger" / "tasks.json"
        if tasks_file.exists():
            tasks = json.loads(tasks_file.read_text())
            status_counts = defaultdict(int)
            for task in tasks:
                status_counts[task.get("status", "UNKNOWN")] += 1
            
            lines.append("")
            lines.append("# HELP nucleus_tasks_total Number of tasks by status")
            lines.append("# TYPE nucleus_tasks_total gauge")
            for status, count in status_counts.items():
                lines.append(f'nucleus_tasks_total{{status="{status}"}} {count}')
        
        # Session count
        sessions_dir = brain_path / "sessions"
        if sessions_dir.exists():
            session_count = len(list(sessions_dir.glob("*.json")))
            lines.append("")
            lines.append("# HELP nucleus_sessions_total Total saved sessions")
            lines.append("# TYPE nucleus_sessions_total gauge")
            lines.append(f"nucleus_sessions_total {session_count}")
        
        # Event count
        events_file = brain_path / "ledger" / "events.jsonl"
        if events_file.exists():
            with open(events_file, encoding='utf-8') as f:
                event_count = sum(1 for _ in f)
            lines.append("")
            lines.append("# HELP nucleus_events_total Total events logged")
            lines.append("# TYPE nucleus_events_total gauge")
            lines.append(f"nucleus_events_total {event_count}")
            
    except Exception:
        pass  # Silently skip brain metrics if unavailable
    
    lines.append("")
    return "\n".join(lines)


def _extract_labels(key: str) -> str:
    """Extract labels from a metric key."""
    if "{" in key:
        start = key.index("{")
        end = key.rindex("}")
        return key[start+1:end]
    return f'name="{key}"'


def reset_metrics():
    """Reset all metrics (useful for testing)."""
    global _tool_calls, _tool_errors, _tool_latencies, _gauges
    with _metrics_lock:
        _tool_calls = defaultdict(int)
        _tool_errors = defaultdict(int)
        _tool_latencies = defaultdict(list)
        _gauges = {}


def get_metrics_json() -> Dict[str, Any]:
    """Get metrics as JSON (alternative to Prometheus format)."""
    with _metrics_lock:
        latency_stats = {}
        for tool_name, latencies in _tool_latencies.items():
            if latencies:
                latency_stats[tool_name] = {
                    "count": len(latencies),
                    "sum": sum(latencies),
                    "avg": sum(latencies) / len(latencies),
                    "quantiles": _calculate_quantiles(latencies)
                }
        
        return {
            "tool_calls": dict(_tool_calls),
            "tool_errors": dict(_tool_errors),
            "latencies": latency_stats,
            "gauges": dict(_gauges),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }


# Decorator for automatic metrics collection
def metrics_tracked(tool_name: str):
    """
    Decorator to automatically track tool metrics.
    
    Usage:
        @metrics_tracked("nucleus_engrams.health")
        def nucleus_engrams_health():
            ...
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                inc_counter("tool_calls", {"tool": tool_name})
                return result
            except Exception:
                inc_counter("tool_errors", {"tool": tool_name})
                raise
            finally:
                latency = time.perf_counter() - start
                observe_latency(tool_name, latency)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                inc_counter("tool_calls", {"tool": tool_name})
                return result
            except Exception:
                inc_counter("tool_errors", {"tool": tool_name})
                raise
            finally:
                latency = time.perf_counter() - start
                observe_latency(tool_name, latency)
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator
