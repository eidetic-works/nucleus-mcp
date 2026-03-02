"""Dashboard Operations — Enhanced dashboard, snapshots, alerts.

Extracted from __init__.py (Phase 3 Dashboard Tools).
Contains:
- _get_dashboard_engine (singleton)
- _brain_enhanced_dashboard_impl
- _brain_snapshot_dashboard_impl
- _brain_list_snapshots_impl
- _brain_get_alerts_impl
- _brain_set_alert_threshold_impl
"""

import sys
from pathlib import Path

from .common import get_brain_path

_dashboard_engine = None


def _lazy(name):
    import mcp_server_nucleus as m
    return getattr(m, name)


def _get_dashboard_engine():
    """Get or create DashboardEngine singleton."""
    global _dashboard_engine
    if _dashboard_engine is None:
        try:
            # Add nop_v3_refactor to path if needed
            nop_path = Path(__file__).parent.parent.parent.parent.parent / "nop_v3_refactor"
            if str(nop_path) not in sys.path:
                sys.path.insert(0, str(nop_path))
            
            from nop_core.dashboard import DashboardEngine
            get_orch = _lazy("get_orch")
            orch = get_orch()
            _dashboard_engine = DashboardEngine(
                orchestrator=orch,
                brain_path=get_brain_path()
            )
        except ImportError:
            _dashboard_engine = None
    return _dashboard_engine


def _brain_enhanced_dashboard_impl(
    detail_level: str = "standard",
    format: str = "ascii",
    include_alerts: bool = True,
    include_trends: bool = False,
    category: str = None,
) -> str:
    """Internal implementation of enhanced dashboard."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available. Install nop_v3_refactor."
        
        return engine.render(
            detail_level=detail_level,
            format=format,
            include_alerts=include_alerts,
            include_trends=include_trends,
            category=category,
        )
        
    except Exception as e:
        return f"❌ Dashboard error: {str(e)}"


def _brain_snapshot_dashboard_impl(name: str = None) -> str:
    """Internal implementation of snapshot creation."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        snapshot = engine.create_snapshot(name)
        
        return f"""✅ Snapshot Created
   ID: {snapshot.id}
   Name: {snapshot.name}
   Timestamp: {snapshot.timestamp}
   
💡 To compare: brain_compare_dashboards('{snapshot.id}', 'other_snapshot_id')"""
        
    except Exception as e:
        return f"❌ Snapshot error: {str(e)}"


def _brain_list_snapshots_impl(limit: int = 10) -> str:
    """Internal implementation of snapshot listing."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        snapshots = engine.list_snapshots(limit)
        
        if not snapshots:
            return "📸 No snapshots found"
        
        lines = ["📸 Dashboard Snapshots", "=" * 40]
        for s in snapshots:
            lines.append(f"   {s['id']}: {s['name']} ({s['timestamp']})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ List snapshots error: {str(e)}"


def _brain_get_alerts_impl() -> str:
    """Internal implementation of alert retrieval."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        alerts = engine.get_alerts()
        
        if not alerts:
            return "✅ No active alerts - all systems healthy"
        
        lines = ["⚠️ Active Alerts", "=" * 40]
        for alert in alerts:
            icon = "🔴" if alert.level.value == "critical" else "🟡"
            lines.append(f"   {icon} [{alert.level.value.upper()}] {alert.message}")
            lines.append(f"      Metric: {alert.metric}, Value: {alert.value}, Threshold: {alert.threshold}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Alerts error: {str(e)}"


def _brain_set_alert_threshold_impl(metric: str, level: str, value: float) -> str:
    """Internal implementation of threshold setting."""
    try:
        engine = _get_dashboard_engine()
        if engine is None:
            return "❌ DashboardEngine not available."
        
        engine.set_alert_threshold(metric, level, value)
        
        return f"""✅ Threshold Set
   Metric: {metric}
   Level: {level}
   Value: {value}"""
        
    except Exception as e:
        return f"❌ Threshold error: {str(e)}"
