"""Session management, consolidation, events, state, and checkpoint tools.

Super-Tools Facade: All 20 session/event/state/checkpoint/conversation-capture
actions exposed via a single `nucleus_sessions(action, params)` MCP tool.
Layer 0 (shipped 2026-04-08) added 4 conversation-capture actions
(ingest_conversations / search_conversations / list_conversations /
conversation_stats) on top of the original 16.
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
    from ..runtime.conversation_ops import (
        ingest_conversations, search_conversations,
        list_conversations, conversation_stats,
    )
    from ..sessions.registry import (
        detect_splits as _registry_detect_splits,
        heartbeat as _registry_heartbeat,
        list_agents as _registry_list_agents,
        register_session as _registry_register,
        unregister as _registry_unregister,
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

    def _h_register(session_id, agent, role, provider,
                    worktree_path=None, pid=None, heartbeat_interval_s=30):
        try:
            env = _registry_register(
                session_id=session_id, agent=agent, role=role, provider=provider,
                worktree_path=worktree_path, pid=pid,
                heartbeat_interval_s=heartbeat_interval_s,
            )
        except (ValueError, OSError) as exc:
            return make_response(False, error=str(exc))
        return make_response(True, data=env)

    def _h_heartbeat(session_id):
        try:
            env = _registry_heartbeat(session_id)
        except FileNotFoundError as exc:
            return make_response(False, error=str(exc))
        return make_response(True, data=env)

    def _h_unregister(session_id):
        removed = _registry_unregister(session_id)
        return make_response(True, data={"session_id": session_id, "removed": removed})

    def _h_list_agents(worktree_path=None, role=None, alive_only=True):
        return make_response(True, data={
            "agents": _registry_list_agents(
                worktree_path=worktree_path, role=role, alive_only=alive_only,
            ),
        })

    def _h_detect_splits(worktree_path=None):
        return make_response(True, data={
            "splits": _registry_detect_splits(worktree_path=worktree_path),
        })

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
        "ingest_conversations": lambda mode="incremental", session_id="", limit=0, dry_run=False: make_response(True, data=ingest_conversations(mode=mode, session_id=session_id, limit=limit, dry_run=dry_run)),
        "search_conversations": lambda query="", limit=20, session_id="", date_from="", date_to="": make_response(True, data=search_conversations(query=query, limit=limit, session_id=session_id, date_from=date_from, date_to=date_to)),
        "list_conversations": lambda limit=50, offset=0, sort="recent": make_response(True, data=list_conversations(limit=limit, offset=offset, sort=sort)),
        "conversation_stats": lambda: make_response(True, data=conversation_stats()),
        "register": _h_register,
        "heartbeat": _h_heartbeat,
        "unregister": _h_unregister,
        "list_agents": _h_list_agents,
        "detect_splits": _h_detect_splits,
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
  ingest_conversations - Ingest Claude Code JSONL transcripts. params: {mode?: "incremental"|"batch"|"single", session_id?, limit?, dry_run?}
  search_conversations - Search ingested conversations. params: {query, limit?, session_id?, date_from?, date_to?}
  list_conversations   - List ingested sessions. params: {limit?, offset?, sort?: "recent"|"size"|"turns"}
  conversation_stats   - Aggregate conversation corpus statistics
  register         - [T3.11] Register agent session envelope. params: {session_id, agent, role, provider, worktree_path?, pid?, heartbeat_interval_s?}
  heartbeat        - [T3.11] Touch last_heartbeat on an envelope. params: {session_id}
  unregister       - [T3.11] Delete a session envelope. params: {session_id}
  list_agents      - [T3.11] List registered agent envelopes. params: {worktree_path?, role?, alive_only?}
  detect_splits    - [T3.11] Report (worktree, role) buckets with >1 alive session. params: {worktree_path?}
"""
        return dispatch(action, params, ROUTER, "nucleus_sessions")

    return [("nucleus_sessions", nucleus_sessions)]
