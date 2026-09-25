"""Task management, depth tracking, and context switch tools.

Super-Tools Facade: All 16 task/depth/context actions exposed via a single
`nucleus_tasks(action, params)` MCP tool.
"""
import logging
logger = logging.getLogger(__name__)

import json
from typing import Dict, List, Any, Optional

from ._dispatch import async_dispatch


def register(mcp, helpers):
    """Register the nucleus_tasks facade tool with the MCP server."""
    make_response = helpers["make_response"]

    from ..runtime.task_ops import (
        _list_tasks, _get_next_task, _claim_task, _update_task,
        _add_task, _import_tasks_from_jsonl, _escalate_task
    )
    from ..runtime.depth_ops import (
        _depth_push, _depth_pop, _depth_show, _depth_reset,
        _depth_set_max, _generate_depth_map,
        _context_switch, _context_switch_reset, _context_switch_status,
    )

    def _h_list(status=None, priority=None, skill=None, claimed_by=None, required_role=None):
        return make_response(True, data=_list_tasks(status, priority, skill, claimed_by, required_role))

    def _h_get_next(skills, required_role=None):
        task = _get_next_task(skills, required_role=required_role)
        if task:
            return make_response(True, data=task)
        return make_response(True, data=None, error="No matching tasks found")

    def _h_claim(task_id, agent_id):
        result = _claim_task(task_id, agent_id)
        if result.get("success"):
            return make_response(True, data=result)
        return make_response(False, error=result.get("error"))

    def _h_update(task_id, updates):
        result = _update_task(task_id, updates)
        if not result.get("success"):
            return make_response(False, error=result.get("error"))

        # Chain: when marking a task DONE, return the next message from the
        # agent's relay inbox. This eliminates the gap between "task finished"
        # and "what do I do next" — the DONE response IS the next_message call.
        # The agent never goes idle. Each task naturally chains to the next.
        if isinstance(updates, dict) and updates.get("status", "").upper() == "DONE":
            try:
                from ..runtime.posture import get_current_posture
                from ..runtime.relay_inbox_canonical import resolve_canonical_inbox_name
                from ..runtime.relay.core import relay_inbox, relay_ack

                me = None
                posture = get_current_posture()
                if posture.get("status") == "active":
                    agent_id = posture.get("agent_id", "")
                    if agent_id:
                        me = resolve_canonical_inbox_name(agent_id)
                if not me:
                    from ..runtime.relay.session import detect_session_role
                    me = detect_session_role()

                inbox = relay_inbox(unread_only=True, recipient=me, limit=1)
                messages = inbox.get("messages", [])
                if messages:
                    msg = messages[0]
                    relay_ack(msg.get("id", ""), recipient=me)
                    result["next_message"] = msg
                else:
                    result["next_message"] = None
            except Exception as e:
                logger.debug("Swallowed exception in register", exc_info=True)
                result["next_message"] = None
                result["next_message_error"] = str(e)

        return make_response(True, data=result)

    def _h_add(description, priority=3, blocked_by=None, required_skills=None,
               source="synthesizer", task_id=None, skip_dep_check=False,
               required_role=None, plan_ref=None):
        result = _add_task(description, priority, blocked_by, required_skills, source,
                           task_id, skip_dep_check, required_role=required_role, plan_ref=plan_ref)
        if result.get("success"):
            return make_response(True, data=result.get("task"))
        return make_response(False, error=result.get("error"))

    def _h_import(jsonl_path, clear_existing=False, merge_gtm_metadata=True):
        result = _import_tasks_from_jsonl(jsonl_path, clear_existing, merge_gtm_metadata)
        if result.get("success"):
            return make_response(True, data=result)
        return make_response(False, error=result.get("error"))

    ROUTER = {
        "list": _h_list,
        "get_next": _h_get_next,
        "claim": _h_claim,
        "update": _h_update,
        "add": _h_add,
        # Alias: "create" — natural-language synonym for add.
        # Added for ChatGPT App Catalog reviewer ergonomics (test cases use "create").
        "create": _h_add,
        "import_jsonl": _h_import,
        "escalate": lambda task_id, reason: _escalate_task(task_id, reason),
        "depth_push": lambda topic: make_response(True, data=_depth_push(topic)),
        "depth_pop": lambda: make_response(True, data=_depth_pop()),
        "depth_show": lambda: make_response(True, data=_depth_show()),
        "depth_reset": lambda: make_response(True, data=_depth_reset()),
        "depth_set_max": lambda max_depth: make_response(True, data=_depth_set_max(max_depth)),
        "depth_map": lambda: make_response(True, data=_generate_depth_map()),
        "context_switch": lambda new_context: make_response(True, data=_context_switch(new_context)),
        "context_switch_status": lambda: make_response(True, data=_context_switch_status()),
        "context_switch_reset": lambda: make_response(True, data=_context_switch_reset()),
    }

    @mcp.tool(title="Task Management", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_tasks(action: str, params: dict = {}) -> str:
        """Task management, depth tracking & ADHD context-switch tools.

Actions:
  list              - List tasks. params: {status?, priority?, skill?, claimed_by?, required_role?}
  get_next          - Get highest-priority unblocked task. params: {skills, required_role?}
  claim             - Atomically claim a task. params: {task_id, agent_id}
  update            - Update task fields. params: {task_id, updates}
  add               - Create a new task. params: {description, priority?, blocked_by?, required_skills?, source?, task_id?, skip_dep_check?, required_role?, plan_ref?} (alias: "create")
  import_jsonl      - Import tasks from JSONL. params: {jsonl_path, clear_existing?, merge_gtm_metadata?}
  escalate          - Escalate task for human help. params: {task_id, reason}
  depth_push        - Go deeper into subtopic. params: {topic}
  depth_pop         - Come back up one level
  depth_show        - Show current depth state
  depth_reset       - Reset depth to root
  depth_set_max     - Set max safe depth. params: {max_depth}
  depth_map         - Generate exploration map
  context_switch    - Record context switch / ADHD drift check. params: {new_context}
  context_switch_status - Get context switch metrics
  context_switch_reset  - Reset context switch counter
"""
        return await async_dispatch(action, params, ROUTER, "nucleus_tasks")

    return [("nucleus_tasks", nucleus_tasks)]
