"""Sync, artifact, trigger, and deploy tools.

Super-Tools Facade: All 27 sync/artifact/trigger/deploy/relay/shared/channel
actions exposed via a single `nucleus_sync(action, params)` MCP tool.
"""

import json
from typing import Dict, List, Any, Optional

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_sync facade tool with the MCP server."""
    make_response = helpers["make_response"]
    _emit_event = helpers["emit_event"]
    get_brain_path = helpers["get_brain_path"]

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

    def _identify_agent(agent_id, environment, role=""):
        try:
            from ..runtime.event_ops import _read_events
            import socket
            current_host = socket.gethostname()
            recent_events = _read_events(limit=50)
            collision_detected = False
            warning = ""
            for event in recent_events:
                if event.get("emitter") == agent_id and event.get("type") == "AGENT_REGISTERED":
                    stored_data = event.get("data", {})
                    if stored_data.get("host") and stored_data.get("host") != current_host:
                        collision_detected = True
                        break
            if collision_detected:
                import logging
                warning = f"WARNING: Agent ID '{agent_id}' is already active on another host."
                logging.getLogger("nucleus").warning(warning)
        except Exception:
            collision_detected = False
            warning = ""
        result = set_current_agent(agent_id, environment, role)
        if collision_detected:
            result["collision_warning"] = warning
        import socket
        result["host"] = socket.gethostname()
        _emit_event("AGENT_REGISTERED", agent_id, result,
                     f"Agent {agent_id} registered in {environment} (v0.7.1)")
        return json.dumps(result, indent=2)

    def _sync_now(force=False):
        if not is_sync_enabled():
            return json.dumps({"error": "Sync not enabled",
                               "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true"}, indent=2)
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
    from ..runtime.relay_ops import relay_post, relay_inbox, relay_ack, relay_status, relay_clear

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
        "add_channel": lambda channel_type, **kwargs: _channel_add(channel_type, **kwargs),
        "test_channel": lambda channel_name=None: _channel_test(channel_name),
        # ── Cross-session relay (Cowork ↔ Claude Code) ──
        "relay_post": lambda to, subject, body, priority="normal", context=None, sender=None, to_session_id=None, from_session_id=None: json.dumps(relay_post(to, subject, body, priority, context, sender, to_session_id, from_session_id), indent=2),
        "relay_inbox": lambda unread_only=True, limit=20, recipient=None: json.dumps(relay_inbox(unread_only, limit, recipient), indent=2),
        "relay_ack": lambda message_id, recipient=None: json.dumps(relay_ack(message_id, recipient), indent=2),
        "relay_status": lambda: json.dumps(relay_status(), indent=2),
        "relay_clear": lambda recipient=None, older_than_hours=168: json.dumps(relay_clear(recipient, older_than_hours), indent=2),
    }

    @mcp.tool()
    def nucleus_sync(action: str, params: dict = {}) -> str:
        """Sync, artifact, trigger & deploy management for multi-agent coordination.

Actions:
  identify_agent   - Register agent identity. params: {agent_id, environment, role?}
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
  relay_post       - Post message to another session type (Cowork↔Claude Code). params: {to, subject, body, priority?, context?, sender?, to_session_id?, from_session_id?}
  relay_inbox      - Read messages for current session type. params: {unread_only?, limit?, recipient?}
  relay_ack        - Mark a relay message as read. params: {message_id, recipient?}
  relay_status     - Get relay mailbox status across all session types
  relay_clear      - Clean up old relay messages. params: {recipient?, older_than_hours?}
"""
        return dispatch(action, params, ROUTER, "nucleus_sync")

    return [("nucleus_sync", nucleus_sync)]
