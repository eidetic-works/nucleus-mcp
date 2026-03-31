"""Session management, consolidation, events, state, and checkpoint tools.

Super-Tools Facade: All 16 session/event/state/checkpoint actions exposed via
a single `nucleus_sessions(action, params)` MCP tool.
"""

import json
from typing import Dict, List, Any, Optional

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_sessions facade tool with the MCP server."""
    make_response = helpers["make_response"]
    _emit_event = helpers["emit_event"]
    _read_events = helpers["read_events"]
    _get_state = helpers["get_state"]
    _update_state = helpers["update_state"]
    get_brain_path = helpers["get_brain_path"]

    from ..runtime.session_ops import (
        _save_session, _resume_session, _list_sessions,
        _check_for_recent_session, _brain_session_end_impl,
        _brain_session_start_impl,
    )
    from ..runtime.consolidation_ops import (
        _archive_resolved_files, _generate_merge_proposals, _garbage_collect_tasks
    )
    from ..runtime.checkpoint_ops import (
        _brain_checkpoint_task_impl, _brain_resume_from_checkpoint_impl,
        _brain_generate_handoff_summary_impl
    )

    def _h_save(context, active_task=None, pending_decisions=None,
                breadcrumbs=None, next_steps=None):
        result = _save_session(context, active_task, pending_decisions, breadcrumbs, next_steps)
        if result.get("success"):
            return make_response(True, data=result)
        return make_response(False, error=result.get("error"))

    def _h_resume(session_id=None):
        result = _resume_session(session_id)
        if result:
            return make_response(True, data=result)
        return make_response(False, error="Session not found")

    def _h_end(summary="", learnings="", mood="neutral"):
        result = _brain_session_end_impl(summary, learnings, mood)
        if result.get("success"):
            return make_response(True, data=result)
        return make_response(False, error=result.get("error", "Unknown error"))

    def _h_emit(event_type, emitter, data, description=""):
        result = _emit_event(event_type, emitter, data, description)
        if isinstance(result, str) and result.startswith("Error"):
            return make_response(False, error=result)
        return make_response(True, data={"event_id": result})

    def _wrap_str(result: str) -> str:
        """Wrap a raw string result in make_response for consistent API contract."""
        if isinstance(result, str) and (result.startswith("❌") or result.startswith("Error")):
            return make_response(False, error=result)
        return make_response(True, data={"message": result})

    ROUTER = {
        "save": _h_save,
        "resume": _h_resume,
        "list": lambda: make_response(True, data=_list_sessions()),
        "check_recent": lambda: make_response(True, data=_check_for_recent_session()),
        "end": _h_end,
        "start": lambda: _wrap_str(_brain_session_start_impl()),
        "archive_resolved": lambda: make_response(True, data=_archive_resolved_files()),
        "propose_merges": lambda: make_response(True, data=_generate_merge_proposals()),
        "garbage_collect": lambda max_age_hours=72, dry_run=False: make_response(True, data=_garbage_collect_tasks(max_age_hours=max_age_hours, dry_run=dry_run)),
        "emit_event": _h_emit,
        "read_events": lambda limit=10: make_response(True, data={"events": _read_events(limit)}),
        "get_state": lambda path=None: make_response(True, data=_get_state(path)),
        "update_state": lambda updates: _wrap_str(_update_state(updates)),
        "checkpoint": lambda task_id, step=None, progress_percent=None, context=None, artifacts=None, resumable=True: _wrap_str(_brain_checkpoint_task_impl(task_id, step, progress_percent, context, artifacts, resumable)),
        "resume_checkpoint": lambda task_id: _wrap_str(_brain_resume_from_checkpoint_impl(task_id)),
        "handoff_summary": lambda task_id, summary, key_decisions=None, handoff_notes="": _wrap_str(_brain_generate_handoff_summary_impl(task_id, summary, key_decisions, handoff_notes)),
    }

    @mcp.tool()
    def nucleus_sessions(action: str, params: dict = {}) -> str:
        """Session management, events, state & checkpoint tools.

Actions:
  save             - Save session for later. params: {context, active_task?, pending_decisions?, breadcrumbs?, next_steps?}
  resume           - Resume a saved session. params: {session_id?}
  list             - List all saved sessions
  check_recent     - Check for recent session to resume
  end              - End work session. params: {summary?, learnings?, mood?}
  start            - Mandatory session start protocol
  archive_resolved - Archive .resolved.* backup files
  propose_merges   - Detect redundant artifacts, generate merge proposals
  garbage_collect  - Archive stale tasks. params: {max_age_hours?, dry_run?}
  emit_event       - Emit event to brain ledger. params: {event_type, emitter, data, description?}
  read_events      - Read recent events. params: {limit?}
  get_state        - Get brain state. params: {path?}
  update_state     - Update brain state. params: {updates}
  checkpoint       - Save task checkpoint. params: {task_id, step?, progress_percent?, context?, artifacts?, resumable?}
  resume_checkpoint - Resume from checkpoint. params: {task_id}
  handoff_summary  - Generate handoff summary. params: {task_id, summary, key_decisions?, handoff_notes?}
"""
        return dispatch(action, params, ROUTER, "nucleus_sessions")

    return [("nucleus_sessions", nucleus_sessions)]
