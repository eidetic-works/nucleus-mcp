"""Task management, depth tracking, and context switch tools.

Super-Tools Facade: All 16 task/depth/context actions exposed via a single
`nucleus_tasks(action, params)` MCP tool.
"""

import json
from typing import Dict, List, Any, Optional

from ._dispatch import dispatch


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

    def _h_list(status=None, priority=None, skill=None, claimed_by=None):
        return make_response(True, data=_list_tasks(status, priority, skill, claimed_by))

    def _h_get_next(skills):
        task = _get_next_task(skills)
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
        if result.get("success"):
            return make_response(True, data=result)
        return make_response(False, error=result.get("error"))

    def _h_add(description, priority=3, blocked_by=None, required_skills=None,
               source="synthesizer", task_id=None, skip_dep_check=False):
        result = _add_task(description, priority, blocked_by, required_skills, source, task_id, skip_dep_check)
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

    @mcp.tool()
    def nucleus_tasks(action: str, params: dict = {}) -> str:
        """Task management, depth tracking & ADHD context-switch tools.

Actions:
  list              - List tasks. params: {status?, priority?, skill?, claimed_by?}
  get_next          - Get highest-priority unblocked task. params: {skills}
  claim             - Atomically claim a task. params: {task_id, agent_id}
  update            - Update task fields. params: {task_id, updates}
  add               - Create a new task. params: {description, priority?, blocked_by?, required_skills?, source?, task_id?, skip_dep_check?}
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
        return dispatch(action, params, ROUTER, "nucleus_tasks")

    return [("nucleus_tasks", nucleus_tasks)]
