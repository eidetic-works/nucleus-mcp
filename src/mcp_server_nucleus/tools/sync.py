"""Sync, artifact, trigger, and deploy tools.

Super-Tools Facade: All 27 sync/artifact/trigger/deploy/relay/shared/channel
actions exposed via a single `nucleus_sync(action, params)` MCP tool.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional

from ._dispatch import async_dispatch
from . import _pair_actions as _pa  # Nucleus-Delegate v0.1 — pair lifecycle + audit
from ..runtime.posture import (
    declare_posture as _declare_posture,
    approve_posture as _approve_posture,
    get_current_posture as _get_posture,
    clear_posture as _clear_posture,
)

logger = logging.getLogger(__name__)


def register(mcp, helpers):
    """Register the nucleus_sync facade tool with the MCP server."""
    _emit_event = helpers["emit_event"]
    get_brain_path = helpers["get_brain_path"]
    make_response = helpers["make_response"]

    def _list_tasks_filtered(required_role=None):
        """Helper for wakeup_wait: list tasks with strict role filter.

        Strict mode means only tasks with required_role exactly matching
        are returned — no backward-compat fallback to unscoped tasks.
        This prevents a scoped agent from getting spammed by legacy
        unscoped tasks in the queue.
        """
        from ..runtime.task_ops import _list_tasks
        return _list_tasks(required_role=required_role, strict_role=True)

    def _safe_int(val, default):
        """Safely convert to int, returning default on non-numeric values."""
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    from ..runtime.sync_ops import (
        get_sync_status, is_sync_enabled, perform_sync, record_sync_time,
        sync_lock, start_file_watcher, stop_file_watcher,
        get_current_agent, set_current_agent,
    )
    from ..runtime.deployment_ops import (
        _start_deploy_poll, _check_deploy_status,
        _complete_deploy, _run_smoke_test,
    )

    # ── Handler functions (preserve original logic) ──────────

    def _identify_agent(agent_id=None, environment="unknown", role="",
                        provider=None, session_id=None):
        """Register agent identity. Per ADR-0005 §D1, identity is the tuple
        {role, provider, session_id}. Legacy {agent_id, environment, role} is
        accepted via §D5 read-coercion through end of Cycle C+2."""
        import logging
        import socket
        logger = logging.getLogger("nucleus.sync")

        if not (provider or session_id):
            if agent_id:
                logger.info(
                    "identify_agent legacy-shape call (agent_id=%s); coercing per "
                    "ADR-0005 §D5 grace-period. Migrate caller to {role, provider, "
                    "session_id} before end of Cycle C+2.",
                    agent_id,
                )
            else:
                return json.dumps({
                    "error": "identify_agent requires either {agent_id, environment} "
                             "or {role, provider, session_id} per ADR-0005 §D1.",
                }, indent=2)

        try:
            from ..runtime.event_ops import _read_events
            current_host = socket.gethostname()
            recent_events = _read_events(limit=50)
            collision_key = session_id or agent_id
            collision_detected = False
            warning = ""
            for event in recent_events:
                if event.get("type") != "AGENT_REGISTERED":
                    continue
                stored_data = event.get("data", {})
                stored_key = (stored_data.get("session_id")
                              or stored_data.get("agent_id")
                              or event.get("emitter"))
                if stored_key != collision_key:
                    continue
                if stored_data.get("host") and stored_data.get("host") != current_host:
                    collision_detected = True
                    break
            if collision_detected:
                warning = f"WARNING: Agent ID '{collision_key}' is already active on another host."
                logging.getLogger("nucleus").warning(warning)
        except Exception:
            collision_detected = False
            warning = ""

        result = set_current_agent(
            agent_id=agent_id, environment=environment, role=role,
            provider=provider, session_id=session_id,
        )
        if collision_detected:
            result["collision_warning"] = warning
        result["host"] = socket.gethostname()

        # Per PR #2 (CCR server-side auto-arm) — IDE-agnostic relay-arrival arming.
        # Inject canonical inbox + arm directive into response so ANY MCP client
        # (Claude Code, Antigravity, Cursor, Windsurf) sees the directive at
        # identify-time. Closes the gap that PR #1's Claude-only SessionStart
        # hook left for non-Claude-Code agents like agy (Antigravity).
        try:
            from ..runtime.relay_inbox_canonical import resolve_canonical_inbox_name
            _role_val = role if isinstance(role, str) else (result.get("role") or "")
            resolved_role = (_role_val or "").strip().lower()
            canonical_inbox = resolve_canonical_inbox_name(resolved_role) or resolved_role
            if canonical_inbox:
                result["canonical_inbox"] = canonical_inbox
                result["relay_subscribe_directive"] = (
                    f"[CCR-ARM] Fire nucleus_ccr_arm() OR nucleus_relay_subscribe("
                    f"inbox_filter=\"{canonical_inbox}\", timeout_seconds=270) "
                    f"as one of your first 3 tool uses. Re-fire on return for "
                    f"persistent coverage. Per PR #1 + PR #2 CCR-inversion + "
                    f"server-side auto-arm. IDE-agnostic — works in Claude Code, "
                    f"Antigravity, Cursor, Windsurf."
                )
        except Exception as exc:
            # Defensive: identify_agent must NEVER fail on this side-effect
            logging.getLogger("nucleus").warning(
                "identify_agent canonical-inbox directive injection failed: %s", exc
            )

        _emit_event("AGENT_REGISTERED", result["agent_id"], result,
                     f"Agent {result['agent_id']} registered in {environment} (v0.7.1)")
        return json.dumps(result, indent=2)

    def _sync_now(force=False):
        if not is_sync_enabled():
            return make_response(False, error="Sync not enabled",
                                  data={"hint": "Create .brain/config/nucleus.yaml with sync.enabled: true"})
        try:
            with sync_lock(timeout=5):
                result = perform_sync(force)
                record_sync_time()
                _emit_event("SYNC_MANUAL", get_current_agent(), result,
                            f"Manual sync by {get_current_agent()}")
                return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "hint": "Another agent may be syncing."}, indent=2)

    def _sync_auto(enable):
        if enable:
            result = start_file_watcher()
            try:
                from ..runtime.common import get_brain_path as _gbp
                root_path = _gbp().parent
                gitignore = root_path / ".gitignore"
                ignore_block = "\n# Nucleus MCP Sync Metadata\n**/*.meta\n**/*.conflict\n.nucleus_agent\n.sync_last\n"
                if gitignore.exists():
                    content = gitignore.read_text()
                    if "**/*.meta" not in content:
                        with open(gitignore, "a", encoding="utf-8") as f:
                            f.write(ignore_block)
                        result["gitignore_patched"] = True
            except Exception:
                pass
        else:
            result = stop_file_watcher()
        return json.dumps(result, indent=2)

    def _sync_resolve(file_path, strategy="last_write_wins"):
        try:
            from ..runtime.common import get_brain_path as _gbp
            from ..runtime.sync_ops import detect_conflict, resolve_conflict
            brain_path = _gbp()
            abs_path = brain_path / file_path
            with sync_lock(brain_path):
                conflict = detect_conflict(abs_path)
                if not conflict:
                    return json.dumps({"status": "error", "message": "No active conflict."}, indent=2)
                status = resolve_conflict(conflict, strategy, brain_path)
                _emit_event("SYNC_CONFLICT_RESOLVED", get_current_agent(),
                            {"file": file_path, "strategy": strategy, "status": status},
                            f"Conflict in {file_path} resolved via {strategy}")
                return json.dumps({"status": status, "file": file_path}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    from ..runtime.artifact_ops import _read_artifact, _write_artifact, _list_artifacts
    from ..runtime.trigger_ops import _trigger_agent_impl, _get_triggers_impl, _evaluate_triggers_impl
    from ..runtime.shared_state_ops import brain_sync_read, brain_sync_write, brain_sync_list
    from ..runtime.relay_ops import (
        relay_post, relay_inbox, relay_ack, relay_status, relay_clear,
        relay_log_event, relay_skip_review, relay_classify_skip, relay_event_stats,
        relay_wait, relay_poll_start, relay_poll_stop, relay_poll_status, relay_listen,
    )
    from ..runtime.saturation_telemetry import (
        compute_baselines as _saturation_baselines_raw,
        check_saturation as _saturation_check_raw,
    )

    def _saturation_baselines(surface="main", window_size=100):
        return _saturation_baselines_raw(surface=surface, window_size=window_size)

    def _saturation_check(surface="main", window_size=100, threshold_factor=2.0, inspect_recent_n=10):
        return _saturation_check_raw(
            surface=surface,
            window_size=window_size,
            threshold_factor=threshold_factor,
            inspect_recent_n=inspect_recent_n,
        )

    def _channel_notify(title, message, level="info"):
        from ..runtime.channels import get_channel_router
        router = get_channel_router()
        results = router.notify(title, message, level)
        return json.dumps({"sent": results, "channels_reached": sum(1 for v in results.values() if v)}, indent=2)

    def _channel_list():
        from ..runtime.channels import get_channel_router
        router = get_channel_router()
        return json.dumps({"channels": router.list_channels()}, indent=2)

    def _channel_add(channel_type, **kwargs):
        from ..runtime.channels import get_channel_router
        from ..runtime.channels.base import ChannelRouter
        router = get_channel_router()
        if channel_type == "telegram":
            from ..runtime.channels.telegram import TelegramChannel
            ch = TelegramChannel(**{k: v for k, v in kwargs.items() if k in ("token", "chat_id")})
        elif channel_type == "slack":
            from ..runtime.channels.slack import SlackChannel
            ch = SlackChannel(webhook_url=kwargs.get("webhook_url"))
        elif channel_type == "discord":
            from ..runtime.channels.discord import DiscordChannel
            ch = DiscordChannel(webhook_url=kwargs.get("webhook_url"))
        elif channel_type == "whatsapp":
            from ..runtime.channels.whatsapp import WhatsAppChannel
            ch = WhatsAppChannel(**{k: v for k, v in kwargs.items() if k in ("token", "phone_id", "to_number")})
        else:
            return json.dumps({"error": f"Unknown channel type: {channel_type}"}, indent=2)
        router.register(ch)
        return json.dumps({"added": channel_type, "configured": ch.is_configured()}, indent=2)

    def _h_add_channel(channel_type, **kwargs):
        """ROUTER entry for add_channel. Union of every key the per-channel
        branches in _channel_add read: telegram {token, chat_id},
        slack/discord {webhook_url}, whatsapp {token, phone_id, to_number}.
        Declared on the function so _dispatch can reject unknown keys.
        """
        return _channel_add(channel_type, **kwargs)

    _h_add_channel._nucleus_params = (
        "channel_type", "token", "chat_id", "webhook_url", "phone_id", "to_number",
    )

    def _channel_test(channel_name=None):
        from ..runtime.channels import get_channel_router
        router = get_channel_router()
        if channel_name:
            ch = router.get_channel(channel_name)
            if not ch:
                return json.dumps({"error": f"Channel '{channel_name}' not found"}, indent=2)
            ok = ch.test()
            return json.dumps({"channel": channel_name, "success": ok}, indent=2)
        results = {}
        for ch_info in router.list_channels():
            ch = router.get_channel(ch_info["type"])
            if ch and ch.is_configured():
                results[ch_info["type"]] = ch.test()
        return json.dumps({"results": results}, indent=2)

    # ── Marketplace handlers (extracted to _marketplace_core) ──────────────
    from ._marketplace_core import register as _mp_register
    _mp_handlers = _mp_register(_emit_event, get_brain_path)
    _marketplace_search = _mp_handlers["marketplace_search"]
    _marketplace_whoami = _mp_handlers["marketplace_whoami"]
    _marketplace_recommend = _mp_handlers["marketplace_recommend"]
    _marketplace_promote = _mp_handlers["marketplace_promote"]
    _marketplace_quarantine = _mp_handlers["marketplace_quarantine"]
    _marketplace_audit = _mp_handlers["marketplace_audit"]
    _marketplace_compare = _mp_handlers["marketplace_compare"]
    _marketplace_alert = _mp_handlers["marketplace_alert"]
    _marketplace_trends = _mp_handlers["marketplace_trends"]
    _marketplace_export = _mp_handlers["marketplace_export"]
    _marketplace_dashboard = _mp_handlers["marketplace_dashboard"]
    _marketplace_history = _mp_handlers["marketplace_history"]
    _marketplace_can_call = _mp_handlers["marketplace_can_call"]
    _marketplace_diff = _mp_handlers["marketplace_diff"]
    _marketplace_subscribe = _mp_handlers["marketplace_subscribe"]
    _marketplace_unsubscribe = _mp_handlers["marketplace_unsubscribe"]
    _marketplace_subscriptions = _mp_handlers["marketplace_subscriptions"]
    _marketplace_federation_proxy = _mp_handlers["marketplace_federation_proxy"]
    _marketplace_federation_register = _mp_handlers["marketplace_federation_register"]
    _marketplace_federation_sync = _mp_handlers["marketplace_federation_sync"]

    ROUTER = {
        "identify_agent": _identify_agent,
        "sync_status": lambda: json.dumps(get_sync_status(), indent=2),
        "sync_now": _sync_now,
        "sync_auto": _sync_auto,
        "sync_resolve": _sync_resolve,
        "read_artifact": lambda path: _read_artifact(path),
        "write_artifact": lambda path, content: _write_artifact(path, content),
        "list_artifacts": lambda folder=None: _list_artifacts(folder),
        "trigger_agent": lambda agent, task_description, context_files=None: _trigger_agent_impl(agent, task_description, context_files),
        "get_triggers": lambda: _get_triggers_impl(),
        "evaluate_triggers": lambda event_type, emitter: _evaluate_triggers_impl(event_type, emitter),
        "start_deploy_poll": lambda service_id, commit_sha=None: _start_deploy_poll(service_id, commit_sha),
        "check_deploy": lambda service_id: _check_deploy_status(service_id),
        "complete_deploy": lambda service_id, success, deploy_url=None, error=None, run_smoke_test=True: _complete_deploy(service_id, success, deploy_url, error, run_smoke_test),
        "smoke_test": lambda url, endpoint="/api/health": _run_smoke_test(url, endpoint),
        "shared_read": lambda key: json.dumps(brain_sync_read(key), indent=2),
        "shared_write": lambda key, value, agent_id="": json.dumps(brain_sync_write(key, value, agent_id), indent=2),
        "shared_list": lambda: json.dumps(brain_sync_list(), indent=2),
        "notify": lambda title, message, level="info": _channel_notify(title, message, level),
        "list_channels": lambda: _channel_list(),
        # The only **kwargs handler in this ROUTER — declared below so _dispatch
        # can read its contract (see _dispatch._allowed_param_names).
        "add_channel": _h_add_channel,
        "test_channel": lambda channel_name=None: _channel_test(channel_name),
        # ── Cross-session relay (Cowork ↔ Claude Code) ──
        "relay_post": lambda to, subject, body, priority="normal", context=None, sender=None, to_session_id=None, from_session_id=None, in_reply_to=None, task_id=None: json.dumps(relay_post(to, subject, body, priority, context, sender, to_session_id, from_session_id, in_reply_to, task_id=task_id), indent=2),
        "relay_inbox": lambda unread_only=True, limit=20, recipient=None, session_id=None, task_id=None: json.dumps(relay_inbox(unread_only, _safe_int(limit, 20), recipient, session_id, task_id=task_id), indent=2),
        "task_comment_add": lambda task_id, message, sender, subject="", priority="normal", in_reply_to=None: json.dumps(relay_post(to="task_comments", subject=subject or f"[task-comment] {task_id}", body=message, priority=priority, sender=sender, in_reply_to=in_reply_to, task_id=task_id), indent=2),
        "task_comment_list": lambda task_id, limit=100: json.dumps(relay_inbox(unread_only=False, limit=_safe_int(limit, 100), task_id=task_id), indent=2),
        # ── Posture (declared, confirmed, approved, persisted) ──
        "declare_posture": lambda role, approach="execute", agent_id="", delegation_targets=None: json.dumps(_declare_posture(role, approach, agent_id, delegation_targets), indent=2),
        "approve_posture": lambda approved_by="operator": json.dumps(_approve_posture(approved_by), indent=2),
        "get_posture": lambda: json.dumps(_get_posture(), indent=2),
        "clear_posture": lambda: json.dumps(_clear_posture(), indent=2),
        "relay_ack": lambda message_id, recipient=None, session_id=None: json.dumps(relay_ack(message_id, recipient, session_id), indent=2),
        "relay_status": lambda: json.dumps(relay_status(), indent=2),
        "relay_clear": lambda recipient=None, older_than_hours=168: json.dumps(relay_clear(recipient, _safe_int(older_than_hours, 168)), indent=2),
        "relay_log_event": lambda event, side, subject, tags=None, match_reason="", priority="normal", message_id=None, in_reply_to=None: json.dumps(relay_log_event(event, side, subject, tags, match_reason, priority, message_id, in_reply_to), indent=2),
        "relay_skip_review": lambda limit=20: json.dumps(relay_skip_review(_safe_int(limit, 20)), indent=2),
        "relay_classify_skip": lambda ts, subject, classification, note=None: json.dumps(relay_classify_skip(ts, subject, classification, note), indent=2),
        "relay_event_stats": lambda: json.dumps(relay_event_stats(), indent=2),
        "relay_wait": lambda in_reply_to, recipient, timeout_s=60, poll_interval_s=5: json.dumps(relay_wait(in_reply_to, recipient, _safe_int(timeout_s, 60), _safe_int(poll_interval_s, 5)), indent=2),
        "relay_poll_start": lambda recipient, interval_s=10, session_id=None: json.dumps(relay_poll_start(recipient, _safe_int(interval_s, 10), session_id), indent=2),
        "relay_poll_stop": lambda recipient: json.dumps(relay_poll_stop(recipient), indent=2),
        "relay_poll_status": lambda recipient: json.dumps(relay_poll_status(recipient), indent=2),
        "relay_listen": lambda recipient, window_s=60, poll_s=5, in_reply_to=None, known_ids=None, attempt=1: json.dumps(relay_listen(recipient, _safe_int(window_s, 60), _safe_int(poll_s, 5), in_reply_to, known_ids, _safe_int(attempt, 1)), indent=2),
        "saturation_baselines": lambda surface="main", window_size=100: json.dumps(_saturation_baselines(surface, window_size), indent=2),
        "saturation_check": lambda surface="main", window_size=100, threshold_factor=2.0, inspect_recent_n=10: json.dumps(_saturation_check(surface, window_size, threshold_factor, inspect_recent_n), indent=2),
        "marketplace_search": lambda tags=None, min_tier=None, limit=10: _marketplace_search(tags, min_tier, limit),
        "marketplace_whoami": lambda role=None: _marketplace_whoami(role),
        "marketplace_can_call": lambda caller, target: _marketplace_can_call(caller, target),
        "marketplace_recommend": lambda task, top_k=5: _marketplace_recommend(task, _safe_int(top_k, 5)),
        "marketplace_dashboard": lambda: _marketplace_dashboard(),
        "marketplace_history": lambda address, limit=20: _marketplace_history(address, limit),
        "marketplace_promote": lambda address, new_tier, caller="admin": _marketplace_promote(address, new_tier, caller),
        "marketplace_quarantine": lambda address, caller="admin", reason="": _marketplace_quarantine(address, caller, reason),
        "marketplace_audit": lambda caller=None, target=None, action_type=None, since_timestamp=None, limit=50, offset=0: _marketplace_audit(caller, target, action_type, since_timestamp, limit, offset),
        "marketplace_compare": lambda a, b: _marketplace_compare(a, b),
        "marketplace_alert": lambda subscriber, target, event_types=None: _marketplace_alert(subscriber, target, event_types),
        "marketplace_trends": lambda days=30, brain_path=None: _marketplace_trends(_safe_int(days, 30), brain_path),
        "marketplace_export": lambda: _marketplace_export(),
        "marketplace_diff": lambda snapshot_a, snapshot_b: _marketplace_diff(snapshot_a, snapshot_b),
        "marketplace_subscribe": lambda subscriber, target="*", event_types=None: _marketplace_subscribe(subscriber, target, event_types),
        "marketplace_unsubscribe": lambda subscriber, target="*": _marketplace_unsubscribe(subscriber, target),
        "marketplace_subscriptions": lambda subscriber=None: _marketplace_subscriptions(subscriber),
        # ── Federation Parallel-Chain primitives ──────────────────────────────
        "marketplace_federation_proxy": lambda target_brain, action, payload=None: _marketplace_federation_proxy(target_brain, action, payload),
        "marketplace_federation_register": lambda address, capabilities=None, display_name="", tags=None: _marketplace_federation_register(address, capabilities, display_name, tags),
        "marketplace_federation_sync": lambda: _marketplace_federation_sync(),
        # ── Nucleus-Delegate v0.1 — pair lifecycle + audit ──────────────────
        "pair_register": lambda lane, charter_path=None: _pa.pair_register(lane, charter_path),
        "pair_status": lambda lane=None: _pa.pair_status(lane),
        "pair_stop": lambda lane: _pa.pair_stop(lane),
        "pair_fire": lambda lane, brief, model="sonnet", subject=None, parent_session_id=None: _pa.pair_fire(lane, brief, model, subject, parent_session_id),
        "audit_pair": lambda window_hours=24.0: _pa.audit_pair(window_hours),
    }

    @mcp.tool(title="Cross-Agent Sync", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_sync(action: str, params: dict = {}) -> str:
        """Sync, artifact, trigger & deploy management for multi-agent coordination.

Actions:
  identify_agent   - Register agent identity. params: {role, provider, session_id} (per ADR-0005 §D1)
                     OR legacy {agent_id, environment, role?} (coerced per §D5 until end of Cycle C+2)
  sync_status      - Check current multi-agent sync status
  sync_now         - Manually trigger sync. params: {force?}
  sync_auto        - Enable/disable file watching. params: {enable}
  sync_resolve     - Resolve a file conflict. params: {file_path, strategy?}
  read_artifact    - Read an artifact file. params: {path}
  write_artifact   - Write to an artifact file. params: {path, content}
  list_artifacts   - List artifacts. params: {folder?}
  trigger_agent    - Trigger an agent via event. params: {agent, task_description, context_files?}
  get_triggers     - Get all defined neural triggers
  evaluate_triggers - Evaluate triggers for an event. params: {event_type, emitter}
  start_deploy_poll - Start monitoring a Render deploy. params: {service_id, commit_sha?}
  check_deploy     - Check deploy poll status. params: {service_id}
  complete_deploy  - Mark deploy complete. params: {service_id, success, deploy_url?, error?, run_smoke_test?}
  smoke_test       - Run a smoke test. params: {url, endpoint?}
  shared_read      - Read shared state. params: {key}
  shared_write     - Write shared state. params: {key, value, agent_id?}
  shared_list      - List all shared state keys
  notify           - Send notification to all channels. params: {title, message, level?}
  list_channels    - List configured notification channels
  add_channel      - Add a channel. params: {channel_type, webhook_url?}
  test_channel     - Test a channel. params: {channel_name?}
  relay_post       - Post message to another session type (Cowork↔Claude Code). params: {to, subject, body, priority?, context?, sender?, to_session_id?, from_session_id?, in_reply_to?, task_id?}
  relay_inbox      - Read messages for current session type. params: {unread_only?, limit?, recipient?, session_id?, task_id?}
  task_comment_add - Post a task-scoped comment (coordination during task execution). params: {task_id, message, sender, subject?, priority?, in_reply_to?}
  task_comment_list - List all comments for a task. params: {task_id, limit?}
  declare_posture - Declare agent role + approach (pending operator approval). params: {role, approach?, agent_id?, delegation_targets?}
  approve_posture - Approve the declared posture (operator only). params: {approved_by?}
  get_posture    - Get current posture. params: {}
  clear_posture  - Clear current posture. params: {}
  relay_ack        - Mark a relay message as read. params: {message_id, recipient?, session_id?}
  relay_status     - Get relay mailbox status across all session types
  relay_clear      - Clean up old relay messages. params: {recipient?, older_than_hours?}
  relay_log_event  - Log a fire/skip event. params: {event, side, subject, tags?, match_reason?, priority?, message_id?, in_reply_to?}
  relay_skip_review - List recent unclassified skips. params: {limit?}
  relay_classify_skip - Classify a skip event. params: {ts, subject, classification, note?}
  relay_event_stats - Compute override + skip rates from event_log.jsonl
  marketplace_search - Search registered capability cards. params: {tags?, min_tier?, limit?}
  marketplace_whoami - Get caller's address, tier, reputation. params: {role?}
  marketplace_can_call - Pre-flight permission check. params: {caller, target}
  marketplace_recommend - Recommend agents by task description. params: {task, top_k?}
  marketplace_dashboard - Aggregated health snapshot. params: {}
  marketplace_history  - Reputation event timeline for an address. params: {address, limit?}
  marketplace_promote  - Admin: manually set address tier. params: {address, new_tier, caller?}
  marketplace_quarantine - Admin: flag address quarantined. params: {address, caller?, reason?}
  marketplace_audit    - Replay admin_actions.jsonl with filters. params: {caller?, target?, action_type?, since_timestamp?, limit?, offset?}
  marketplace_compare  - Head-to-head comparison of two addresses. params: {a, b}
  marketplace_trends  - Tier distribution trend over N days. params: {days?}
  marketplace_alert   - Subscribe to alert rules. params: {subscriber, target, event_types?}
  marketplace_export   - Full registry snapshot (read-only). params: {}
  marketplace_diff     - Diff two registry snapshots. params: {snapshot_a, snapshot_b}
  marketplace_subscribe - Subscribe to tier-change events. params: {subscriber, target?, event_types?}
  marketplace_unsubscribe - Remove subscription. params: {subscriber, target?}
  marketplace_subscriptions - List subscriptions. params: {subscriber?}
  marketplace_federation_proxy - Proxy an action to a remote federation brain. params: {target_brain, action, payload?}
  marketplace_federation_register - Register local brain as a federated capability card. params: {address, capabilities?, display_name?, tags?}
  marketplace_federation_sync - Force federation sync and reconcile marketplace registry. params: {}
"""
        return await async_dispatch(action, params, ROUTER, "nucleus_sync")

    # ── Native MCP notifications (operator FOUNDER-OVERRIDE 2026-05-31) ──
    # Separate @mcp.tool because async + needs FastMCP Context for
    # server.send_notification push. Cannot dispatch through sync facade.
    #
    # CTX-INJECTION FIX (2026-06-01, cc-peer empirical bug report relay
    # 13:20Z): `ctx` MUST be annotated `Context` at runtime for FastMCP 3.0
    # dependency injection. Without the annotation FastMCP treats `ctx` as a
    # regular tool param, the client passes a dict, and ctx.info() raises
    # "'dict' object has no attribute 'info'" — which is exactly what
    # cc-peer hit on first invocation.
    from fastmcp import Context
    from ..runtime.relay_notify import relay_subscribe_notifications_impl

    @mcp.tool(title="Next Message", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_next_message(
        ctx: Context,
        recipient: str = "",
        timeout_seconds: int = 60,
    ) -> dict:
        """Get the next unread relay message. One call — returns full message
        body and auto-acks. Long-poll (default 60s; set timeout_seconds).

        This is the agent's idle loop. Call it, get a message or None, act or
        re-call. No separate inbox + ack dance.

        The agent's loop:
          1. nucleus_next_message() → blocks up to 60s for a message
          2. If message: handle it (execute task, respond to comment, etc.)
          3. Re-call nucleus_next_message() — always re-arm, never sit idle
          4. Never stop the loop

        Role is auto-detected from posture (.brain/posture/current.json).
        No args needed.

        Returns:
          dict with:
            message: full relay message (id, from, subject, body, priority, task_id) or None
            acked: True if message was auto-acked
            waited_seconds: how long the poll ran
        """
        from ..runtime.posture import get_current_posture
        from ..runtime.relay_inbox_canonical import resolve_canonical_inbox_name
        from ..runtime.relay.core import relay_inbox, relay_ack
        # Called below when neither an explicit recipient nor an active posture
        # resolves a name. The sibling subscribe handler imports it the same
        # way; this one did not, so every call that reached that branch died on
        # `NameError: name 'detect_session_role' is not defined`.
        from ..runtime.relay_ops import detect_session_role

        # Auto-detect recipient from posture
        me = recipient
        if not me:
            posture = get_current_posture()
            if posture.get("status") == "active":
                agent_id = posture.get("agent_id", "")
                if agent_id:
                    me = resolve_canonical_inbox_name(agent_id)
        if not me:
            me = detect_session_role()

        # Was hardcoded to 60 with no way for a caller to shorten it: the only
        # relay tool of the three that could not be tuned, so any caller that
        # wanted a quick check had to block for a minute. Its two siblings
        # (relay_subscribe, ccr_arm) already took timeout_seconds.
        # `timeout_seconds or 60` would make 0 mean 60, because 0 is falsy --
        # and 0 is precisely the burst value relay_subscribe uses for "scan
        # once, return now". A caller asking for an immediate check would have
        # been silently given a 60-second block instead.
        _t = 60 if timeout_seconds is None else int(timeout_seconds)
        timeout_seconds = 0 if _t == 0 else max(1, min(_t, 1800))
        await ctx.info(f"[next-message] waiting {timeout_seconds}s for {me}")

        # timeout_seconds == 0 is burst mode: one pass, no waiting.
        deadline = time.monotonic() + timeout_seconds
        while True:
            inbox = relay_inbox(unread_only=True, recipient=me, limit=1)
            messages = inbox.get("messages", [])
            if messages:
                msg = messages[0]
                relay_ack(msg.get("id", ""), recipient=me)
                return {
                    "message": msg,
                    "acked": True,
                    "waited_seconds": round(time.monotonic() - (deadline - timeout_seconds), 2),
                }
            if time.monotonic() >= deadline:
                return {
                    "message": None,
                    "acked": False,
                    "waited_seconds": timeout_seconds,
                }
            await asyncio.sleep(1)

    @mcp.tool(title="Relay Subscription", annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_relay_subscribe(
        ctx: Context,
        timeout_seconds: int = 270,
        role: str = "",
        inbox_filter: str = "",
    ) -> dict:
        """Long-poll subscription that pushes ctx.info() on each new inbox file.

Replaces bash polling daemons (watch-relay-*.sh) with server-initiated push.
Call once at session start (e.g. via SessionStart hook). Server holds the
subscription, watches the calling agent's role-specific inbox dir, and
fires info-level notifications on each new relay file arrival. Client
re-calls this in a loop for persistent coverage.

Per PR #1 (CCR-inversion-for-relay-pickup): `inbox_filter` parameter added
to BYPASS role-based dir resolution. Use when role detection is unreliable
OR when subscribing to a specific canonical inbox (e.g., 'cc_tb').
Closes 3-week-old feedback_relay_arrival_invisible_midsession HARD RULE.

Args:
  timeout_seconds: max subscription duration (60..1800, default 270 = under
                   FastMCP context-cache TTL so re-subscribe doesn't burn cache)
  role: override calling agent's role (default: env-detected from
        CC_SESSION_ROLE or detect_session_role())
  inbox_filter: explicit inbox dir NAME (e.g., "cc_tb", "claude_code_main").
                When provided, BYPASSES role detection entirely. Recommended
                for SessionStart hook deterministic arming. Resolves the
                bug where cc-tb's role detection mapped to wrong inbox.

Returns:
  dict with subscribed_dir, watched_seconds, events_fired, last_seen_id,
  next_action (the loop hint)

SECURITY (per cc-peer hole-poke verdict 2026-06-05 F5):
  inbox_filter has NO ACCESS CONTROL. Any caller can subscribe to any inbox
  by passing inbox_filter. Multi-tenant isolation is NOT enforced via
  inbox-dir routing — see ADR-0035 tenancy isolation contracts (token-vault
  per-tenant-encrypted + embedding-index per-tenant + LLM-context
  single-tenant-only). Inbox-dir is FLEET-INTERNAL routing, NOT a tenant
  boundary.

  This is INTENTIONAL for the current single-operator fleet:
  cross-agent observability is a feature (cc-tb may legitimately subscribe
  to claude_code_main inbox for diagnostic/admin use). The bypass also
  serves SessionStart-hook deterministic arming and test harnesses.

  IF FUTURE OMBA MILESTONES repurpose inbox-dir for per-tenant relay
  isolation (e.g., per-customer relay channels in multi-tenant deployments),
  server-side access control MUST be added here — call sites that pass
  inbox_filter would need to be authorized against the calling tenant's
  identity. NO IMPLICIT TRUST.
"""
        return await relay_subscribe_notifications_impl(
            ctx,
            timeout_seconds=timeout_seconds,
            role=role or None,
            inbox_filter=inbox_filter or None,
        )

    @mcp.tool(title="CCR Arm", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_ccr_arm(
        ctx: Context,
        role: str = "",
        timeout_seconds: int = 270,
    ) -> dict:
        """One-shot convenience: resolve canonical inbox + arm long-poll subscription.

Per PR #2 (CCR server-side auto-arm) — IDE-agnostic relay-arrival arming.

This is the RECOMMENDED entry point for SessionStart auto-arming across all
MCP clients (Claude Code, Antigravity, Cursor, Windsurf, etc.). Equivalent to:
    1. resolve_canonical_inbox_name(role) → canonical inbox name
    2. nucleus_relay_subscribe(inbox_filter=<canonical>, timeout_seconds=...)

Why this exists vs nucleus_relay_subscribe + inbox_filter:
    nucleus_relay_subscribe + inbox_filter requires the caller to KNOW the
    canonical inbox name for their role. nucleus_ccr_arm hides that step.
    Agent just calls nucleus_ccr_arm() with no args; server detects role from
    CC_SESSION_ROLE / NUCLEUS_SESSION_ROLE env OR detect_session_role().

Args:
  role: explicit role override (e.g., "antigravity", "cc_tb"). If omitted,
        server detects via env vars / registry ancestry / provider heuristics
        (per detect_session_role).
  timeout_seconds: max subscription duration (60..1800, default 270 under
                   FastMCP context-cache TTL).

Returns:
  dict with: canonical_inbox (the dir name resolved), subscribed_dir (full
  path), watched_seconds, events_fired, last_seen_id, next_action.

  Re-call this tool in a loop on return for persistent coverage. Each
  return carries `next_action` as the loop hint.

USAGE PATTERNS:
  Claude Code (via .claude/hooks/ccr_pr_1_canonical_inbox_subscribe.sh hook):
    Hook nudges agent → agent fires nucleus_ccr_arm() → arms canonical inbox.
  Antigravity (no .claude/ hook system):
    Agent reads identify_agent response → sees `relay_subscribe_directive` →
    fires nucleus_ccr_arm() → arms canonical inbox.
  Cursor / Windsurf / other MCP clients:
    Same as Antigravity — identify_agent directive is IDE-agnostic.

SECURITY: Inherits inbox_filter security model from nucleus_relay_subscribe.
  Server resolves the canonical inbox for the calling agent's role; if role
  is forged (CC_SESSION_ROLE override), agent can subscribe to other agents'
  inboxes. Acceptable for single-operator fleet observability; multi-tenant
  deployments MUST add server-side role-claim verification.
"""
        from ..runtime.relay_inbox_canonical import resolve_canonical_inbox_name
        from ..runtime.relay_ops import detect_session_role
        import os

        resolved_role = (
            role
            or os.environ.get("CC_SESSION_ROLE", "").strip().lower()
            or os.environ.get("NUCLEUS_SESSION_ROLE", "").strip().lower()
            or detect_session_role()
        )
        canonical_inbox = resolve_canonical_inbox_name(resolved_role) or resolved_role

        result = await relay_subscribe_notifications_impl(
            ctx,
            timeout_seconds=timeout_seconds,
            inbox_filter=canonical_inbox,
        )
        # Augment response with explicit canonical_inbox + resolved_role for clarity
        result["canonical_inbox"] = canonical_inbox
        result["resolved_role"] = resolved_role
        result["next_action"] = (
            f"Re-call nucleus_ccr_arm(role=\"{resolved_role}\") to maintain "
            f"persistent coverage of {canonical_inbox} inbox."
        )
        return result

    @mcp.tool(title="Task Wakeup Wait", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
    async def nucleus_wakeup_wait(
        ctx: Context,
        required_role: str = "",
        timeout_seconds: int = 5,
        skills: str = "",
        agent_id: str = "",
        auto_claim: bool = True,
    ) -> dict:
        """Quick scan for a PENDING task. Returns the task directly if one is
        available, or None if no task is ready within the timeout.

        Default timeout is 5s (non-blocking). The agent should NOT loop on
        this — tasks arrive via relay push. This is a fallback for when the
        agent wants to check for tasks without waiting for a relay.

        No args needed — the role is auto-detected from posture
        (.brain/posture/current.json) or NUCLEUS_AGENT_ROLES env var.

        Args:
          required_role: role scope filter. Auto-detected from posture if empty.
          timeout_seconds: max wait (default 5s, 0 = instant burst, max 1800).
          skills: comma-separated skill filter (optional).
          agent_id: identifier for claiming (auto-detected if empty).
          auto_claim: if True, atomically claim the task before returning.

        Returns:
          dict with task (or None on timeout), claimed, watched_seconds, next_action
        """
        from ..runtime.task_ops import _get_next_task, _claim_task
        from ..runtime.posture import get_current_role

        # Auto-detect role: explicit arg > posture file > env var > any
        if not required_role:
            required_role = get_current_role()
        if not required_role:
            required_role = os.environ.get("NUCLEUS_AGENT_ROLES", "").strip()

        burst_mode = int(timeout_seconds) == 0
        if not burst_mode:
            timeout_seconds = max(1, min(1800, int(timeout_seconds)))

        skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
        claim_id = agent_id or required_role or "agent"
        role_label = required_role or "any"
        await ctx.info(
            f"[wakeup-wait] polling for {timeout_seconds}s "
            f"(required_role={role_label}, auto_claim={auto_claim}, burst={burst_mode})"
        )

        # timeout_seconds == 0 is burst mode: one pass, no waiting.
        deadline = time.monotonic() + timeout_seconds
        poll_interval = 1.0 if not burst_mode else 0

        while True:
            try:
                task = _get_next_task(skill_list, required_role=required_role or None)
                if task and not task.get("claimed_by"):
                    # Found a matching unclaimed task
                    claimed = False
                    if auto_claim:
                        claim_result = _claim_task(task["id"], claim_id)
                        claimed = claim_result.get("success", False)
                        if claimed:
                            task["claimed_by"] = claim_id
                            await ctx.info(
                                f"[wakeup-wait] claimed task {task['id']} "
                                f"({task.get('description', '')[:80]})"
                            )
                        else:
                            # Race — another agent claimed it first. Keep polling.
                            logger.debug("wakeup_wait claim race on %s, continuing", task["id"])
                            task = None
                    if task:
                        return {
                            "task": task,
                            "claimed": claimed,
                            "watched_seconds": int(time.monotonic() - (deadline - timeout_seconds)),
                            "next_action": "execute the task, run pytest to gate, commit, mark DONE, then call nucleus_wakeup_wait again",
                        }
            except Exception as exc:
                logger.warning("wakeup_wait poll exception: %s", exc)

            if burst_mode:
                break
            if time.monotonic() >= deadline:
                break
            await asyncio.sleep(poll_interval)

        return {
            "task": None,
            "claimed": False,
            "watched_seconds": 0 if burst_mode else timeout_seconds,
            "next_action": "timeout — re-call nucleus_wakeup_wait to continue waiting",
        }

    return [
        ("nucleus_sync", nucleus_sync),
        ("nucleus_relay_subscribe", nucleus_relay_subscribe),
        ("nucleus_ccr_arm", nucleus_ccr_arm),
        ("nucleus_wakeup_wait", nucleus_wakeup_wait),
    ]
