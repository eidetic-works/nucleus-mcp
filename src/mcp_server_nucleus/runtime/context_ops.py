"""
Nucleus Runtime - Context & Prompts
===================================
Core logic for context injection (`brain://context`) and system prompts.
Moves large inline string formatting out of __init__.py.
"""

import json

from .common import get_brain_path, _get_state
from .event_ops import _read_events
from .artifact_ops import _list_artifacts

try:
    from .. import __version__
except ImportError:
    __version__ = "1.8.8"  # Fallback

def _resource_context_impl() -> str:
    """Full context for cold start - auto-visible in sidebar."""
    try:
        brain = get_brain_path()
        state = _get_state()
        sprint = state.get("current_sprint", {})
        agents = state.get("active_agents", [])
        actions = state.get("top_3_leverage_actions", [])
        
        # Format actions
        actions_text = ""
        if actions:
            for i, action in enumerate(actions[:3], 1):
                if isinstance(action, dict):
                    actions_text += f"  {i}. {action.get('action', 'Unknown')}\n"
                else:
                    actions_text += f"  {i}. {action}\n"
        else:
            actions_text = "  (None set)"
        
        # Recent events
        events = _read_events(limit=3)
        events_text = ""
        for evt in events:
            events_text += f"  - {evt.get('type', 'unknown')}: {evt.get('description', '')[:50]}\n"
        if not events_text:
            events_text = "  (No recent events)"
        
        # Check for workflow
        workflow_hint = ""
        workflow_path = brain / "workflows" / "lead_agent_model.md"
        if workflow_path.exists():
            workflow_hint = "📋 Workflow: Read .brain/workflows/lead_agent_model.md for coordination rules"
        
        return f"""# Nucleus Brain Context

## Current Sprint
- Name: {sprint.get('name', 'No active sprint')}
- Focus: {sprint.get('focus', 'Not set')}
- Status: {sprint.get('status', 'Unknown')}

## Active Agents
{', '.join(agents) if agents else 'None'}

## Top Priorities
{actions_text}
## Recent Activity
{events_text}
{workflow_hint}

---
You are the Lead Agent. Use brain_* tools to explore and act."""
    except Exception as e:
        return f"Error loading context: {str(e)}"

def _activate_synthesizer_prompt() -> str:
    """Activate Synthesizer agent to orchestrate the current sprint."""
    state = _get_state()
    sprint = state.get("current_sprint", {})
    return f"""You are the Synthesizer, the orchestrating intelligence of this Nucleus Control Plane.

Current Sprint: {sprint.get('name', 'Unknown')}
Focus: {sprint.get('focus', 'Unknown')}

Your job is to:
1. Review the current state and recent events
2. Determine which agents need to be activated
3. Emit appropriate task_assigned events

Use the available brain_* tools to coordinate the agents."""

def _start_sprint_prompt(goal: str = "MVP Launch") -> str:
    """Initialize a new sprint with the given goal."""
    return f"""Initialize a new sprint with goal: {goal}

Steps:
1. Use brain_update_state to set current_sprint with name, focus, and start date
2. Use brain_emit_event to emit a sprint_started event
3. Identify top 3 leverage actions and emit task_assigned events for each

Goal: {goal}"""

def _cold_start_prompt() -> str:
    """Get instant context when starting a new session."""
    try:
        brain = get_brain_path()
        state = _get_state()
        sprint = state.get("current_sprint", {})
        agents = state.get("active_agents", [])
        actions = state.get("top_3_leverage_actions", [])
        
        # Format top actions
        actions_text = ""
        if actions:
            for i, action in enumerate(actions[:3], 1):
                if isinstance(action, dict):
                    actions_text += f"{i}. {action.get('action', 'Unknown')}\n"
                else:
                    actions_text += f"{i}. {action}\n"
        else:
            actions_text = "None set - check state.json"
        
        # Recent events
        events = _read_events(limit=5)
        events_text = ""
        for evt in events[-3:]:  # Show last 3
            evt_type = evt.get('type', 'unknown')
            evt_desc = evt.get('description', '')[:40]
            events_text += f"- {evt_type}: {evt_desc}\n"
        if not events_text:
            events_text = "(No recent events)"
        
        # Check for workflow
        workflow_hint = ""
        workflow_path = brain / "workflows" / "lead_agent_model.md"
        if workflow_path.exists():
            workflow_hint = "\n📋 **Coordination:** Read `.brain/workflows/lead_agent_model.md` for multi-tool rules."
        
        # Recent artifacts
        artifacts = _list_artifacts()[:5]
        artifacts_text = ", ".join([a.split("/")[-1] for a in artifacts]) if artifacts else "None"
        
        # ─── BRAIN CARD: Engrams ───
        engram_section = ""
        try:
            engram_path = brain / "memory" / "engrams.json"
            if engram_path.exists():
                with open(engram_path, "r", encoding="utf-8") as f:
                    engrams = json.load(f)
                total_engrams = len(engrams) if isinstance(engrams, list) else 0
                
                # Show last 3 engrams (most recent first)
                recent = engrams[-3:] if isinstance(engrams, list) else []
                recent.reverse()
                
                engram_lines = ""
                for eng in recent:
                    key = eng.get("key", "?")[:30]
                    ctx = eng.get("context", "?")
                    intensity = eng.get("intensity", 0)
                    bar = "█" * min(intensity, 10)
                    val_preview = eng.get("value", "")[:60]
                    engram_lines += f"  - **{key}** [{ctx}] {bar} ({intensity}/10)\n    _{val_preview}..._\n"
                
                if not engram_lines:
                    engram_lines = "  _(No engrams stored yet)_\n"
                
                engram_section = f"""
## 🧠 Memory ({total_engrams} engrams stored)
{engram_lines}"""
            else:
                engram_section = "\n## 🧠 Memory\n  _(No engrams file found — run `brain_write_engram` to start building memory)_\n"
        except Exception:
            engram_section = "\n## 🧠 Memory\n  _(Could not read engrams)_\n"
        
        # ─── BRAIN CARD: Tasks ───
        task_section = ""
        try:
            task_path = brain / "ledger" / "tasks.json"
            if task_path.exists():
                with open(task_path, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                total = len(tasks) if isinstance(tasks, list) else 0
                
                # Filter for actionable tasks
                actionable = [t for t in tasks if isinstance(t, dict) and t.get("status") in ("READY", "IN_PROGRESS")]
                # Sort by priority (1 is highest)
                actionable.sort(key=lambda x: x.get("priority", 99))
                
                top_tasks = actionable[:3]
                task_lines = ""
                for t in top_tasks:
                   status_icon = "🔄" if t.get("status") == "IN_PROGRESS" else "⏳"
                   task_lines += f"  - {status_icon} **[{t.get('id')}]** {t.get('description', '')}\n"
                
                if not task_lines and total > 0:
                    task_lines = "  _(No high-priority tasks pending)_\n"
                elif not task_lines:
                    task_lines = "  _(No tasks found)_\n"

                task_section = f"\n## 📋 Top Tasks ({len(actionable)} actionable / {total} total)\n{task_lines}"
            else:
                task_section = "\n## 📋 Tasks\n  _(No tasks found)_\n"
        except Exception:
            task_section = "\n## 📋 Tasks\n  _(Could not read tasks)_\n"
        
        # ─── BRAIN CARD: Mounts ───
        mount_section = ""
        try:
            mounts_path = brain / "mounts.json"
            if mounts_path.exists():
                with open(mounts_path, "r", encoding="utf-8") as f:
                    mounts = json.load(f)
                mount_count = len(mounts) if isinstance(mounts, (list, dict)) else 0
                if isinstance(mounts, dict):
                    mount_names = list(mounts.keys())[:5]
                    mount_section = f"\n## 🔌 Mounts ({mount_count} connected)\n  {', '.join(mount_names)}\n"
                elif mount_count > 0:
                    mount_section = f"\n## 🔌 Mounts ({mount_count} connected)\n"
                else:
                    mount_section = "\n## 🔌 Mounts\n  _(No external servers mounted)_\n"
            else:
                mount_section = "\n## 🔌 Mounts\n  _(No mounts configured — use `brain_mount_server` to connect external MCP servers)_\n"
        except Exception:
            mount_section = "\n## 🔌 Mounts\n  _(Could not read mounts)_\n"
        
        # ─── BRAIN CARD: Session Arc ───
        arc_section = ""
        try:
            from .session_ops import _load_session_arc
            arc = _load_session_arc(brain)
            if arc.get("recent_sessions"):
                arc_lines = ""
                for s in arc["recent_sessions"]:
                    ts = s.get("timestamp", "")[:10]
                    val = s.get("value", "")[:60]
                    arc_lines += f"  - [{ts}] {val}\n"
                focus = arc.get("todays_focus")
                focus_line = f"  - **Today's focus:** {focus}\n" if focus else ""
                arc_section = f"\n## 📋 Session Arc\n{arc_lines}{focus_line}"
        except Exception:
            arc_section = ""

        # ─── BRAIN CARD: Compounding Pulse ───
        pulse_section = ""
        try:
            from datetime import datetime
            cycle_path = brain / "meta" / "compounding_cycle.json"
            if cycle_path.exists():
                cycle = json.loads(cycle_path.read_text())
                cid = cycle.get("cycle_id", "?")
                ws = cycle.get("weekly_score_start")
                today_str = datetime.now().strftime("%Y-%m-%d")
                today_data = cycle.get("days", {}).get(today_str, {})
                action = today_data.get("action", "?")
                completed = sum(1 for d in cycle.get("days", {}).values() if d.get("completed"))
                score_text = f"Score: {ws}" if ws is not None else "Score: pending"
                pulse_section = f"\n## 📈 Compounding Pulse\n  Week {cid} | Day {completed}/7 | {score_text} | Today: {action}\n"
        except Exception:
            pulse_section = ""

        return f"""# 🧠 Nucleus Brain Card
<v{__version__}> · Local-first AI Memory · Everything stays on your machine.

## Current State
- **Sprint:** {sprint.get('name', 'No active sprint')}
- **Focus:** {sprint.get('focus', 'Not set')}
- **Status:** {sprint.get('status', 'Unknown')}
- **Active Agents:** {', '.join(a.get('codename', str(a)) if isinstance(a, dict) else str(a) for a in agents) if agents else 'None'}

## Top Priorities
{actions_text}
## Recent Activity
{events_text}
## Recent Artifacts
{artifacts_text}
{engram_section}{task_section}{mount_section}{arc_section}{pulse_section}{workflow_hint}

---

## Your Role
You are now the **Lead Agent** for this session.
- No strict role restrictions — you can do code, strategy, research
- Use `brain_*` tools to read/write state and artifacts
- Emit events to coordinate with other agents

What would you like to work on?"""
    except Exception as e:
        return f"""# 🧠 Nucleus Brain Card

⚠️ Could not load brain state: {str(e)}

Make sure NUCLEAR_BRAIN_PATH is set correctly.

You can still use brain_* tools to explore the brain manually."""
