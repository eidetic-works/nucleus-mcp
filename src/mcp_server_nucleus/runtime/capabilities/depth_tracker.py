from typing import List, Dict, Any
import os
from .base import Capability
# Import core logic from top-level package
# Import core logic lazily inside methods to avoid circular dependency
# from ... import _depth_push, _depth_pop, _depth_show, _depth_reset

class DepthTracker(Capability):
    def __init__(self):
        # Determine brain path (fallback for agent runtime if env not set)
        if not os.environ.get("NUCLEAR_BRAIN_PATH"):
            # Default used in verification/dev
            os.environ["NUCLEAR_BRAIN_PATH"] = "/Users/nucleus-os/.gemini/antigravity/brain/7c654df4-b83e-43f9-8620-f15868ec39d1"

    @property
    def name(self) -> str:
        return "depth_tracker"

    @property
    def description(self) -> str:
        return "Tools for tracking conversation depth and preventing rabbit holes."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_depth_push",
                "description": "Go deeper into a subtopic. Tracks position in conversation tree.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "What you're diving into"}
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "brain_depth_pop",
                "description": "Come back up one level in the conversation tree.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "brain_depth_show",
                "description": "Show current depth state with visual indicator and tree.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "brain_depth_reset",
                "description": "Reset depth to root level (0). Clears all levels.",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict) -> str:
        # Lazy import to avoid circular dependency
        from ... import _depth_push, _depth_pop, _depth_show, _depth_reset

        if tool_name == "brain_depth_push":
            result = _depth_push(args.get("topic"))
            if "error" in result:
                return f"Error: {result['error']}"
            return f"Descended to Level {result.get('current_depth')}: '{result.get('topic')}'.\n{result.get('warning', '')}\n{result.get('indicator')}"
            
        elif tool_name == "brain_depth_pop":
            result = _depth_pop()
            if "error" in result:
                return f"Error: {result['error']}"
            return f"{result.get('message')}\n{result.get('indicator')}"

        elif tool_name == "brain_depth_show":
            result = _depth_show()
            if "error" in result:
                return f"Error: {result['error']}"
            return f"{result.get('indicator')}\nStatus: {result.get('status')}\nPath: {result.get('breadcrumbs')}\n\n{result.get('tree')}"

        elif tool_name == "brain_depth_reset":
            result = _depth_reset()
            if "error" in result:
                return f"Error: {result['error']}"
            return result.get('message', 'Reset complete')

        return f"Tool {tool_name} not found in DepthTracker."
