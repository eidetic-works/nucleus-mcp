"""Project Management View Operations — High-level HUD and Gantt rendering."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
from .common import get_brain_path
from .task_ops import _list_tasks
from .health_ops import _brain_health_impl
from .federation_ops import _brain_federation_status_json_impl

def _brain_pm_summary_impl() -> str:
    """Consolidated Project Management Summary HUD."""
    try:
        # 1. Task Statistics
        tasks = _list_tasks()
        total = len(tasks)
        pending = len([t for t in tasks if t.get("status") in ["PENDING", "TODO", "READY"]])
        in_progress = len([t for t in tasks if t.get("status") == "IN_PROGRESS"])
        done = len([t for t in tasks if t.get("status") in ["DONE", "COMPLETE"]])
        blocked = len([t for t in tasks if t.get("status") == "BLOCKED"])
        escalated = len([t for t in tasks if t.get("status") == "ESCALATED"])
        
        # 2. Health & DSoR
        try:
            health_json = _brain_health_impl()
            health_data = json.loads(health_json)
        except Exception:
            health_data = {"status": "DEGRADED", "version": "0.5.x"}
            
        health_status = health_data.get("status", "unknown").upper()
        version = health_data.get("version", "unknown")
        
        # 3. Federation info
        try:
            fed_status_json = _brain_federation_status_json_impl()
            fed_data = json.loads(fed_status_json)
        except Exception:
            fed_data = {"peers": {}, "sovereign_mode": False}
            
        peers_info = fed_data.get("peers", {})
        peers_count = peers_info.get("total", 0) if isinstance(peers_info, dict) else 0
        is_sovereign = fed_data.get("sovereign_mode", False)
        
        # Format HUD
        lines = [
            "🚀 NUCLEUS PROJECT MANAGEMENT HUD",
            "═" * 50,
            f"STARDATE: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%f')[:23]} UTC",
            f"VERSION: {version} | HEALTH: {health_status}",
            "",
            "📊 TASK PIPELINE",
            f"   • Total Tasks:   {total}",
            f"   • Pending:       {pending} ⏳",
            f"   • In Progress:   {in_progress} ⚡",
            f"   • Blocked:       {blocked} 🛑",
            f"   • Escalated:     {escalated} ⚠️",
            f"   • Completed:     {done} ✅",
            "",
            "🔗 FEDERATION & GOVERNANCE",
            f"   • Peers Online:  {peers_count}",
            f"   • Sovereign Mode: {'ACTIVE' if is_sovereign else 'INACTIVE'} (Majority Consensus Required)" if is_sovereign else f"   • Sovereign Mode: {'INACTIVE'} (Standalone Mode)",
            "",
            "🎯 ROADMAP ALIGNMENT",
            "   [PHASE 9]  Consensus-Based Governance       [COMPLETE]",
            "   [PHASE 10] Project Management View          [/] IN PROGRESS",
            "",
            "═" * 50,
            "💡 Use nucleus_pm_view:gantt for dependency visualization."
        ]
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ PM View Error: {str(e)}"

def _brain_pm_gantt_impl() -> str:
    """ASCII Gantt Chart of active tasks and dependencies."""
    try:
        tasks = _list_tasks()
        if not tasks:
            return "📭 No tasks in pipeline."
            
        # Only show Pending, In Progress, Blocked, Escalated
        active = [t for t in tasks if t.get("status") not in ["DONE", "COMPLETE"]]
        if not active:
            return "✅ All tasks completed. Pipeline clear."
            
        lines = [
            "📅 TASK GANTT & DEPENDENCIES",
            "═" * 65,
            f"{'STATUS':10} | {'TASK ID':10} | {'DESCRIPTION':30} | {'BLOCKERS'}",
            "─" * 65
        ]
        
        for t in active:
            tid = t.get("id", "??")
            desc = t.get("description", "")
            if len(desc) > 27: desc = desc[:27] + "..."
            
            status = t.get("status", "PENDING")
            
            # Icon
            icon = "⚪"
            if status == "IN_PROGRESS": icon = "⚡"
            elif status == "BLOCKED": icon = "🛑"
            elif status == "ESCALATED": icon = "⚠️"
            elif status in ["PENDING", "TODO", "READY"]: icon = "⏳"
            
            blockers = t.get("blocked_by", [])
            blocker_str = ", ".join(blockers) if blockers else "-"
            
            lines.append(f"{icon} {status:8} | {tid:10} | {desc:30} | {blocker_str}")
            
        lines.append("═" * 65)
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Gantt Error: {str(e)}"
