"""
Nucleus Runtime - Depth Tracking Operations
===========================================
Core logic for depth tracking (Rabbit hole protection).
"""

import json
import time
import logging
from typing import Dict, Any
from pathlib import Path

# Relative imports assuming this is in mcp_server_nucleus.runtime
from .common import get_brain_path
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.depth_ops")

def _get_depth_path() -> Path:
    """Get the path to the depth tracking file."""
    brain = get_brain_path()
    session_dir = brain / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / "depth.json"

def _get_depth_state() -> Dict[str, Any]:
    """Get current depth tracking state."""
    try:
        depth_path = _get_depth_path()
        
        if not depth_path.exists():
            # Initialize with default state
            default_state = {
                "session_id": f"session-{time.strftime('%Y%m%d')}",
                "current_depth": 0,
                "max_safe_depth": 5,
                "levels": [],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            }
            with open(depth_path, "w") as f:
                json.dump(default_state, f, indent=2)
            return default_state
        
        with open(depth_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error getting depth state: {e}")
        return {"current_depth": 0, "levels": [], "max_safe_depth": 5}

def _save_depth_state(state: Dict[str, Any]) -> str:
    """Save depth tracking state."""
    try:
        depth_path = _get_depth_path()
        state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with open(depth_path, "w") as f:
            json.dump(state, f, indent=2)
        return "Depth state saved"
    except Exception as e:
        return f"Error saving depth state: {str(e)}"

def _depth_push(topic: str) -> Dict[str, Any]:
    """Go deeper into a subtopic. Returns current state with warnings."""
    try:
        state = _get_depth_state()
        
        new_depth = state.get("current_depth", 0) + 1
        max_safe = state.get("max_safe_depth", 5)
        
        # Create new level entry
        new_level = {
            "depth": new_depth,
            "topic": topic,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "current"
        }
        
        # Update previous level status
        levels = state.get("levels", [])
        for level in levels:
            if level.get("status") == "current":
                level["status"] = "active"
        
        levels.append(new_level)
        
        state["current_depth"] = new_depth
        state["levels"] = levels
        _save_depth_state(state)
        
        # Generate warning based on depth
        warning = None
        warning_level = "safe"
        
        if new_depth >= max_safe:
            warning = f"🔴🔴 RABBIT HOLE! You're at level {new_depth}/{max_safe}. Consider resurfacing."
            warning_level = "danger"
        elif new_depth >= max_safe - 1:
            warning = f"🔴 DEEP DIVE ALERT! Level {new_depth}/{max_safe}. You're in the danger zone."
            warning_level = "danger"
        elif new_depth >= 3:
            warning = f"🟡 CAUTION: Level {new_depth}/{max_safe}. Getting deep - just so you know."
            warning_level = "caution"
        
        # Build breadcrumb path
        breadcrumbs = " → ".join([lv["topic"] for lv in levels])
        
        # Emit event
        _emit_event("depth_increased", "depth_tracker", {
            "new_depth": new_depth,
            "topic": topic,
            "warning_level": warning_level
        })
        
        return {
            "current_depth": new_depth,
            "max_safe_depth": max_safe,
            "topic": topic,
            "breadcrumbs": breadcrumbs,
            "warning": warning,
            "warning_level": warning_level,
            "indicator": _format_depth_indicator(new_depth, max_safe)
        }
    except Exception as e:
        return {"error": str(e)}

def _depth_pop() -> Dict[str, Any]:
    """Come back up one level. Returns new state."""
    try:
        state = _get_depth_state()
        levels = state.get("levels", [])
        
        if not levels:
            return {
                "current_depth": 0,
                "message": "Already at root level (depth 0). Nothing to pop.",
                "indicator": _format_depth_indicator(0, state.get("max_safe_depth", 5))
            }
        
        # Pop the current level
        popped = levels.pop()
        
        # Set new current
        if levels:
            levels[-1]["status"] = "current"
        
        new_depth = len(levels)
        state["current_depth"] = new_depth
        state["levels"] = levels
        _save_depth_state(state)
        
        # Build breadcrumb path
        breadcrumbs = " → ".join([lv["topic"] for lv in levels]) if levels else "(root)"
        returned_to = levels[-1]["topic"] if levels else "root"
        
        # Emit event
        _emit_event("depth_decreased", "depth_tracker", {
            "new_depth": new_depth,
            "returned_to": returned_to,
            "popped_topic": popped["topic"]
        })
        
        return {
            "current_depth": new_depth,
            "returned_to": returned_to,
            "popped_topic": popped["topic"],
            "breadcrumbs": breadcrumbs,
            "message": f"✅ Resurfaced! Now at level {new_depth}: {returned_to}",
            "indicator": _format_depth_indicator(new_depth, state.get("max_safe_depth", 5))
        }
    except Exception as e:
        return {"error": str(e)}

def _depth_show() -> Dict[str, Any]:
    """Show current depth state with visual indicator."""
    try:
        state = _get_depth_state()
        current_depth = state.get("current_depth", 0)
        max_safe = state.get("max_safe_depth", 5)
        levels = state.get("levels", [])
        
        # Build breadcrumb path
        breadcrumbs = " → ".join([lv["topic"] for lv in levels]) if levels else "(root)"
        
        # Build tree visualization
        tree_lines = []
        for i, level in enumerate(levels):
            indent = "  " * i
            prefix = "└─ " if i > 0 else ""
            marker = " ← YOU ARE HERE" if level.get("status") == "current" else ""
            tree_lines.append(f"{indent}{prefix}{i}: {level['topic']}{marker}")
        
        tree = "\n".join(tree_lines) if tree_lines else "(At root level)"
        
        # Generate status
        if current_depth >= max_safe:
            status = "🔴 RABBIT HOLE"
        elif current_depth >= max_safe - 1:
            status = "🔴 DANGER ZONE"
        elif current_depth >= 3:
            status = "🟡 CAUTION"
        else:
            status = "🟢 SAFE"
        
        return {
            "current_depth": current_depth,
            "max_safe_depth": max_safe,
            "status": status,
            "breadcrumbs": breadcrumbs,
            "tree": tree,
            "indicator": _format_depth_indicator(current_depth, max_safe),
            "levels": levels,
            "session_id": state.get("session_id"),
            "help": "Commands: brain_depth_push(topic), brain_depth_pop(), brain_depth_reset(), brain_depth_set_max(n)"
        }
    except Exception as e:
        return {"error": str(e)}

def _depth_reset() -> Dict[str, Any]:
    """Reset depth to 0 (root level). Clears all levels."""
    try:
        state = _get_depth_state()
        state["current_depth"] = 0
        state["levels"] = []
        _save_depth_state(state)
        
        return {
            "current_depth": 0,
            "message": "✅ Depth reset to root level.",
            "indicator": _format_depth_indicator(0, state.get("max_safe_depth", 5))
        }
    except Exception as e:
        return {"error": str(e)}

def _depth_set_max(max_depth: int) -> Dict[str, Any]:
    """Set the maximum safe depth threshold."""
    try:
        # Validate range
        if max_depth < 1 or max_depth > 10:
            return {
                "error": "max_depth must be between 1 and 10",
                "current_max": None
            }
        
        state = _get_depth_state()
        old_max = state.get("max_safe_depth", 5)
        state["max_safe_depth"] = max_depth
        _save_depth_state(state)
        
        current = state.get("current_depth", 0)
        return {
            "old_max": old_max,
            "new_max": max_depth,
            "current_depth": current,
            "indicator": _format_depth_indicator(current, max_depth),
            "message": f"✅ Max depth updated: {old_max} → {max_depth}"
        }
    except Exception as e:
        return {"error": str(e)}

def _format_depth_indicator(current: int, max_safe: int) -> str:
    """Returns a visual progress-style indicator of depth."""
    indicator = "["
    for i in range(max_safe):
        if i < current:
            indicator += "█"
        else:
            indicator += "░"
    indicator += "]"
    
    if current >= max_safe:
        indicator += " ⚠️"
        
    return indicator

def _generate_depth_map() -> Dict[str, Any]:
    """Generate a Mermaid diagram of the current exploration path."""
    try:
        state = _get_depth_state()
        levels = state.get("levels", [])
        max_safe = state.get("max_safe_depth", 5)
        
        if not levels:
            return {
                "mermaid": "```mermaid\ngraph TD\n    ROOT((🏠 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
                "message": "You're at the root level. No exploration path yet.",
                "node_count": 0
            }
        
        # Build Mermaid graph
        lines = ["graph TD"]
        lines.append("    ROOT((🏠 START))")
        
        prev_id = "ROOT"
        for i, level in enumerate(levels):
            node_id = f"L{i}"
            topic = level.get("topic", f"Level {i+1}")
            # Escape quotes and special chars
            topic_safe = topic.replace('"', "'").replace("[", "(").replace("]", ")")
            
            # Determine node style based on depth
            depth = i + 1
            if depth >= max_safe:
                style = "fill:#ffcccc,stroke:#f00"  # Red - rabbit hole
                node_shape = f'{node_id}[["🔴 {topic_safe}"]]'
            elif depth >= max_safe - 1:
                style = "fill:#ffddcc,stroke:#f60"  # Orange - danger
                node_shape = f'{node_id}[["🔴 {topic_safe}"]]'
            elif depth >= 3:
                style = "fill:#ffffcc,stroke:#cc0"  # Yellow - caution
                node_shape = f'{node_id}["🟡 {topic_safe}"]'
            else:
                style = "fill:#ccffcc,stroke:#0a0"  # Green - safe
                node_shape = f'{node_id}["🟢 {topic_safe}"]'
            
            lines.append(f"    {prev_id} --> {node_shape}")
            lines.append(f"    style {node_id} {style}")
            prev_id = node_id
        
        # Mark the last node as current
        if levels:
            lines.append(f"    style {prev_id} stroke-width:3px")
        
        # Wrap in code block
        mermaid_code = "```mermaid\n" + "\n".join(lines) + "\n```"
        
        # Build path summary
        path = " → ".join([lv.get("topic", "?") for lv in levels])
        
        return {
            "mermaid": mermaid_code,
            "path": f"🏠 → {path}",
            "current_depth": len(levels),
            "max_safe_depth": max_safe,
            "node_count": len(levels),
            "message": f"Exploration map with {len(levels)} nodes. Current depth: {len(levels)}/{max_safe}"
        }
    except Exception as e:
        return {"error": str(e)}

