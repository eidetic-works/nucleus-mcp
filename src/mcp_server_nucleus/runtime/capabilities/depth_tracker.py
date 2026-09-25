from typing import List, Dict, Any
import os
from .base import Capability
# Import core logic from top-level package
# Import core logic lazily inside methods to avoid circular dependency
# from ... import _depth_push, _depth_pop, _depth_show, _depth_reset

class DepthTracker(Capability):
    def __init__(self):
        # Deliberately empty. This constructor used to do:
        #
        #     if not os.environ.get("NUCLEUS_BRAIN_PATH"):
        #         os.environ["NUCLEUS_BRAIN_PATH"] = ".brain"
        #
        # Three things wrong with it (ledger DS-8). The value is a *relative*
        # literal, so it resolves against whatever the working directory happens
        # to be at each later use rather than naming one brain. It is
        # process-wide, written from a constructor that ContextFactory builds
        # per request on the long-lived MCP server, so the first request that
        # arrives without a brain set pins every later one. And it short-circuits
        # get_brain_path()'s own fallback — the contextvar, project detection and
        # cwd walk-up — which is strictly better at answering the same question.
        #
        # Nothing here needs the value: depth_ops calls get_brain_path() itself
        # (depth_ops.py:21, :281). Removing it means that in a tree with no
        # .brain anywhere, get_brain_path raises rather than silently creating
        # one in the current directory — which is what every other caller
        # already gets, and the better outcome.
        pass

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
                return f"Error: {result.get('error')}"
            return f"Descended to Level {result.get('current_depth')}: '{result.get('topic')}'.\n{result.get('warning', '')}\n{result.get('indicator')}"
            
        elif tool_name == "brain_depth_pop":
            result = _depth_pop()
            if "error" in result:
                return f"Error: {result.get('error')}"
            return f"{result.get('message')}\n{result.get('indicator')}"

        elif tool_name == "brain_depth_show":
            result = _depth_show()
            if "error" in result:
                return f"Error: {result.get('error')}"
            return f"{result.get('indicator')}\nStatus: {result.get('status')}\nPath: {result.get('breadcrumbs')}\n\n{result.get('tree')}"

        elif tool_name == "brain_depth_reset":
            result = _depth_reset()
            if "error" in result:
                return f"Error: {result.get('error')}"
            return result.get('message', 'Reset complete')

        return f"Tool {tool_name} not found in DepthTracker."
