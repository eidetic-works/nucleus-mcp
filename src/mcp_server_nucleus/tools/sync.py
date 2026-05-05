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
        _emit_event("AGENT_REGISTERED", result["agent_id"], result,
                     f"Agent {result['agent_id']} registered in {environment} (v0.7.1)")
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

    def _marketplace_search(tags=None, min_tier=None, limit=10):
        from mcp_server_nucleus.runtime.marketplace import search_by_tags, TrustTier
        cards = search_by_tags(tags or [])
        if min_tier:
            try:
                threshold = TrustTier[min_tier.upper()]
            except KeyError:
                return json.dumps({"error": f"Unknown min_tier '{min_tier}'. Valid: Unverified, Active, Trusted, Verified"}, indent=2)
            cards = [c for c in cards if c.get("tier", TrustTier.UNVERIFIED) >= threshold]
        cards.sort(
            key=lambda c: (c.get("tier", 0), c.get("success_rate", 1.0)),
            reverse=True,
        )
        return json.dumps({"cards": cards[:limit], "count": len(cards[:limit])}, indent=2)

    def _marketplace_whoami(role=None):
        """Return caller's marketplace identity: address, tier, reputation, last_promoted_at."""
        import os
        from mcp_server_nucleus.runtime.marketplace import (
            lookup_by_address,
            ReputationSignals,
            TrustTier,
        )
        # Resolve address from env (CC_SESSION_ROLE) or explicit role param
        raw_role = role or os.environ.get("CC_SESSION_ROLE", "")
        if raw_role:
            address = f"{raw_role.lower().replace('_', '-')}@nucleus"
        else:
            address = ""

        if not address:
            return json.dumps(
                {"registered": False, "reason": "CC_SESSION_ROLE not set and no role param"},
                indent=2,
            )

        card = lookup_by_address(address)
        if card is None:
            return json.dumps({"registered": False, "address": address}, indent=2)

        metrics = ReputationSignals.compute_signals(address)
        tier_int = card.get("tier", TrustTier.UNVERIFIED)
        tier_badge = card.get("tier_badge", TrustTier.get_display_badge(TrustTier.UNVERIFIED))

        return json.dumps(
            {
                "registered": True,
                "address": address,
                "display_name": card.get("display_name"),
                "tier": tier_int,
                "tier_badge": tier_badge,
                "connection_count": metrics.get("connection_count", 0),
                "success_rate": metrics.get("success_rate", 1.0),
                "avg_response_ms": metrics.get("avg_response_ms", 0),
                "last_seen_at": metrics.get("last_seen_at"),
                "last_promoted_at": card.get("last_promoted_at"),
                "inactive": card.get("inactive", False),
            },
            indent=2,
        )

    def _marketplace_recommend(task: str, top_k: int = 5):
        """Recommend top-K addresses by capability match for a given task description.

        Uses bag-of-words overlap between task tokens and card tags/display_name/accepts.
        Returns ranked list with confidence scores (0.0-1.0).
        """
        from mcp_server_nucleus.runtime.marketplace import search_by_tags
        import re

        def _tokenize(text: str):
            return set(re.sub(r"[^a-z0-9]", " ", text.lower()).split())

        task_tokens = _tokenize(task)
        if not task_tokens:
            return json.dumps({"recommendations": [], "task": task}, indent=2)

        all_cards = search_by_tags([])
        scored = []
        for card in all_cards:
            card_tokens: set = set()
            for t in card.get("tags", []):
                card_tokens.update(_tokenize(str(t)))
            for field in ("display_name", "address"):
                card_tokens.update(_tokenize(card.get(field, "")))
            for item in card.get("accepts", []):
                card_tokens.update(_tokenize(str(item)))
            if not card_tokens:
                continue
            overlap = len(task_tokens & card_tokens)
            if overlap == 0:
                continue
            score = round(overlap / len(task_tokens | card_tokens), 4)
            scored.append({
                "address": card.get("address"),
                "display_name": card.get("display_name"),
                "tier": card.get("tier", 0),
                "tier_badge": card.get("tier_badge", ""),
                "confidence": score,
            })

        scored.sort(key=lambda x: (x["confidence"], x["tier"]), reverse=True)
        return json.dumps({"recommendations": scored[:top_k], "task": task}, indent=2)

    def _marketplace_promote(address: str, new_tier: str, caller: str = "admin"):
        """Manually override an address's tier (admin action).

        Requires caller to be at VERIFIED tier (highest) — root-level only.
        Audit-logs to .brain/marketplace/admin_actions.jsonl.
        """
        import time
        from mcp_server_nucleus.runtime.marketplace import (
            lookup_by_address, TrustTier, _get_registry_dir, _get_card_path, get_brain_path,
        )
        card = lookup_by_address(caller)
        if card is None or card.get("tier", TrustTier.UNVERIFIED) < TrustTier.VERIFIED:
            return json.dumps({
                "ok": False, "reason": "caller_not_verified",
                "detail": f"'{caller}' must be VERIFIED tier to promote"
            }, indent=2)

        target_card = lookup_by_address(address)
        if target_card is None:
            return json.dumps({"ok": False, "reason": "unregistered_target"}, indent=2)

        try:
            tier_val = TrustTier[new_tier.upper()]
        except KeyError:
            return json.dumps({"ok": False, "reason": f"unknown_tier '{new_tier}'"}, indent=2)

        old_tier = target_card.get("tier", TrustTier.UNVERIFIED)
        target_card["tier"] = int(tier_val)
        target_card["tier_badge"] = TrustTier.get_display_badge(tier_val)
        target_card["last_promoted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        registry_dir = _get_registry_dir()
        card_path = _get_card_path(address, registry_dir)
        card_path.write_text(json.dumps(target_card, indent=2))

        brain = get_brain_path()
        admin_log = brain / "marketplace" / "admin_actions.jsonl"
        admin_log.parent.mkdir(parents=True, exist_ok=True)
        import time as _t
        entry = {
            "timestamp": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
            "action": "promote",
            "address": address,
            "from_tier": old_tier,
            "to_tier": int(tier_val),
            "caller": caller,
        }
        with open(admin_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return json.dumps({"ok": True, "address": address,
                           "old_tier": old_tier, "new_tier": int(tier_val)}, indent=2)

    def _marketplace_quarantine(address: str, caller: str = "admin", reason: str = ""):
        """Manually flag an address as quarantined.

        Sets quarantined=True on registry card. marketplace_can_call will
        return allowed=false, reason='quarantined' for quarantined addresses.
        Audit-logs to .brain/marketplace/admin_actions.jsonl.
        """
        import time
        from mcp_server_nucleus.runtime.marketplace import (
            lookup_by_address, TrustTier, _get_registry_dir, _get_card_path, get_brain_path,
        )
        caller_card = lookup_by_address(caller)
        if caller_card is None or caller_card.get("tier", TrustTier.UNVERIFIED) < TrustTier.VERIFIED:
            return json.dumps({
                "ok": False, "reason": "caller_not_verified",
                "detail": f"'{caller}' must be VERIFIED tier to quarantine"
            }, indent=2)

        target_card = lookup_by_address(address)
        if target_card is None:
            return json.dumps({"ok": False, "reason": "unregistered_target"}, indent=2)

        target_card["quarantined"] = True
        target_card["quarantine_reason"] = reason or "manual"

        registry_dir = _get_registry_dir()
        card_path = _get_card_path(address, registry_dir)
        card_path.write_text(json.dumps(target_card, indent=2))

        brain = get_brain_path()
        admin_log = brain / "marketplace" / "admin_actions.jsonl"
        admin_log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": "quarantine",
            "address": address,
            "reason": reason or "manual",
            "caller": caller,
        }
        with open(admin_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return json.dumps({"ok": True, "address": address, "quarantined": True}, indent=2)

    def _marketplace_export():
        """Return full registry as a JSON-serializable list.

        Each entry: card fields + live reputation signals. Pure read, no mutation.
        """
        from mcp_server_nucleus.runtime.marketplace import search_by_tags, ReputationSignals

        cards = search_by_tags([])
        snapshot = []
        for card in cards:
            address = card.get("address", "")
            rep = {}
            try:
                rep = ReputationSignals.compute_signals(address)
            except Exception:
                pass
            snapshot.append({**card, "reputation": rep})

        return json.dumps({"snapshot": snapshot, "total": len(snapshot)}, indent=2)

    def _marketplace_dashboard():
        """Aggregated marketplace health snapshot.

        Returns total_registered, by_tier counts, inactive_count, top_10_by_reputation,
        and tier_flips_recorded from the prometheus counter.
        """
        from mcp_server_nucleus.runtime.marketplace import search_by_tags, TrustTier
        from mcp_server_nucleus.runtime.prometheus import get_metrics_json, MARKETPLACE_TIER_CHANGED_TOTAL

        all_cards = search_by_tags([])
        tier_counts = {t.name.lower(): 0 for t in TrustTier}
        inactive_count = 0
        rep_scores = []
        for card in all_cards:
            tier_val = card.get("tier", TrustTier.UNVERIFIED)
            try:
                tier_name = TrustTier(tier_val).name.lower()
            except Exception:
                tier_name = "unverified"
            tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
            if card.get("inactive", False):
                inactive_count += 1
            rep_scores.append({
                "address": card.get("address"),
                "tier": tier_val,
                "success_rate": card.get("success_rate", 1.0),
                "connection_count": card.get("connection_count", 0),
            })
        rep_scores.sort(key=lambda c: (c["success_rate"], c["connection_count"]), reverse=True)
        metrics_json = get_metrics_json()
        tier_flip_count = sum(
            v for k, v in metrics_json.get("tool_calls", {}).items()
            if MARKETPLACE_TIER_CHANGED_TOTAL in k
        )
        return json.dumps({
            "total_registered": len(all_cards),
            "by_tier": tier_counts,
            "inactive_count": inactive_count,
            "top_10_by_reputation": rep_scores[:10],
            "tier_flips_recorded": tier_flip_count,
        }, indent=2)

    def _marketplace_history(address: str, limit: int = 20):
        """Return chronological reputation events for an address.

        Reads .brain/telemetry/relay_metrics.jsonl written by ReputationSignals.
        Returns last N events oldest-first with a running cumulative success count.
        """
        from mcp_server_nucleus.runtime.marketplace import ReputationSignals, lookup_by_address

        card = lookup_by_address(address)
        if card is None:
            return json.dumps({"error": f"address '{address}' not registered"}, indent=2)

        telemetry_file = ReputationSignals._get_telemetry_file()
        events = []
        try:
            if telemetry_file.exists():
                with open(telemetry_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            ev = json.loads(line)
                            if ev.get("to_address") == address:
                                events.append(ev)
                        except Exception:
                            continue
        except Exception as exc:
            return json.dumps({"error": f"failed to read telemetry: {exc}"}, indent=2)

        events.sort(key=lambda e: e.get("timestamp", ""))
        events = events[-limit:]
        cumulative_success = 0
        timeline = []
        for ev in events:
            if ev.get("success"):
                cumulative_success += 1
            timeline.append({
                "timestamp": ev.get("timestamp"),
                "from_address": ev.get("from_address"),
                "latency_ms": ev.get("latency_ms"),
                "success": ev.get("success"),
                "cumulative_successes": cumulative_success,
            })
        return json.dumps({"address": address, "events": timeline,
                           "total_events": len(timeline)}, indent=2)

    def _marketplace_can_call(caller, target):
        """Pre-flight permission check: can caller tier interact with target tier?

        Rule: caller_tier_rank >= target_tier_rank - 1 (one tier gap allowed; two blocked).
        Fails open if lookup raises (marketplace is supplementary).
        """
        import logging
        from mcp_server_nucleus.runtime.marketplace import lookup_by_address, TrustTier
        _log = logging.getLogger("nucleus.marketplace")
        try:
            caller_card = lookup_by_address(caller)
            if caller_card is None:
                return json.dumps({"allowed": False, "caller": caller, "target": target,
                                   "reason": "unregistered_caller"}, indent=2)
            target_card = lookup_by_address(target)
            if target_card is None:
                return json.dumps({"allowed": False, "caller": caller, "target": target,
                                   "reason": "unregistered_target"}, indent=2)
            if caller_card.get("quarantined"):
                return json.dumps({"allowed": False, "caller": caller, "target": target,
                                   "reason": "quarantined"}, indent=2)
            if target_card.get("quarantined"):
                return json.dumps({"allowed": False, "caller": caller, "target": target,
                                   "reason": "quarantined"}, indent=2)
            caller_tier = caller_card.get("tier", TrustTier.UNVERIFIED)
            target_tier = target_card.get("tier", TrustTier.UNVERIFIED)
            allowed = caller_tier >= target_tier - 1
            return json.dumps({
                "allowed": allowed,
                "caller": caller,
                "target": target,
                "caller_tier": TrustTier(caller_tier).name.capitalize(),
                "target_tier": TrustTier(target_tier).name.capitalize(),
                "reason": None if allowed else "tier_too_low",
            }, indent=2)
        except Exception as exc:
            _log.warning(f"marketplace_can_call lookup failed for {caller}->{target}: {exc}")
            return json.dumps({"allowed": True, "caller": caller, "target": target,
                               "reason": "lookup_failed_fail_open"}, indent=2)

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
        "relay_post": lambda to, subject, body, priority="normal", context=None, sender=None, to_session_id=None, from_session_id=None, in_reply_to=None: json.dumps(relay_post(to, subject, body, priority, context, sender, to_session_id, from_session_id, in_reply_to), indent=2),
        "relay_inbox": lambda unread_only=True, limit=20, recipient=None, session_id=None: json.dumps(relay_inbox(unread_only, limit, recipient, session_id), indent=2),
        "relay_ack": lambda message_id, recipient=None, session_id=None: json.dumps(relay_ack(message_id, recipient, session_id), indent=2),
        "relay_status": lambda: json.dumps(relay_status(), indent=2),
        "relay_clear": lambda recipient=None, older_than_hours=168: json.dumps(relay_clear(recipient, older_than_hours), indent=2),
        "relay_log_event": lambda event, side, subject, tags=None, match_reason="", priority="normal", message_id=None, in_reply_to=None: json.dumps(relay_log_event(event, side, subject, tags, match_reason, priority, message_id, in_reply_to), indent=2),
        "relay_skip_review": lambda limit=20: json.dumps(relay_skip_review(limit), indent=2),
        "relay_classify_skip": lambda ts, subject, classification, note=None: json.dumps(relay_classify_skip(ts, subject, classification, note), indent=2),
        "relay_event_stats": lambda: json.dumps(relay_event_stats(), indent=2),
        "relay_wait": lambda in_reply_to, recipient, timeout_s=60, poll_interval_s=5: json.dumps(relay_wait(in_reply_to, recipient, int(timeout_s), int(poll_interval_s)), indent=2),
        "relay_poll_start": lambda recipient, interval_s=10, session_id=None: json.dumps(relay_poll_start(recipient, int(interval_s), session_id), indent=2),
        "relay_poll_stop": lambda recipient: json.dumps(relay_poll_stop(recipient), indent=2),
        "relay_poll_status": lambda recipient: json.dumps(relay_poll_status(recipient), indent=2),
        "relay_listen": lambda recipient, window_s=60, poll_s=5, in_reply_to=None, known_ids=None, attempt=1: json.dumps(relay_listen(recipient, int(window_s), int(poll_s), in_reply_to, known_ids, int(attempt)), indent=2),
        "saturation_baselines": lambda surface="main", window_size=100: json.dumps(_saturation_baselines(surface, window_size), indent=2),
        "saturation_check": lambda surface="main", window_size=100, threshold_factor=2.0, inspect_recent_n=10: json.dumps(_saturation_check(surface, window_size, threshold_factor, inspect_recent_n), indent=2),
        "marketplace_search": lambda tags=None, min_tier=None, limit=10: _marketplace_search(tags, min_tier, limit),
        "marketplace_whoami": lambda role=None: _marketplace_whoami(role),
        "marketplace_can_call": lambda caller, target: _marketplace_can_call(caller, target),
        "marketplace_recommend": lambda task, top_k=5: _marketplace_recommend(task, top_k),
        "marketplace_dashboard": lambda: _marketplace_dashboard(),
        "marketplace_history": lambda address, limit=20: _marketplace_history(address, limit),
        "marketplace_promote": lambda address, new_tier, caller="admin": _marketplace_promote(address, new_tier, caller),
        "marketplace_quarantine": lambda address, caller="admin", reason="": _marketplace_quarantine(address, caller, reason),
        "marketplace_export": lambda: _marketplace_export(),
        "marketplace_diff": lambda snapshot_a, snapshot_b: _marketplace_diff(snapshot_a, snapshot_b),
        "marketplace_subscribe": lambda subscriber, target="*", event_types=None: _marketplace_subscribe(subscriber, target, event_types),
        "marketplace_unsubscribe": lambda subscriber, target="*": _marketplace_unsubscribe(subscriber, target),
        "marketplace_subscriptions": lambda subscriber=None: _marketplace_subscriptions(subscriber),
    }

    def _get_subscriptions_file(brain_path=None):
        from mcp_server_nucleus.runtime.marketplace import get_brain_path as _gbp
        bp = brain_path or _gbp()
        sub_dir = bp / "marketplace"
        sub_dir.mkdir(parents=True, exist_ok=True)
        return sub_dir / "subscriptions.jsonl"

    def _marketplace_subscribe(subscriber: str, target: str = "*", event_types=None):
        """Subscribe subscriber address to tier-change events for target (or '*' for all).

        event_types: list of event names to subscribe to, default ['tier_changed', 'quarantined'].
        Writes a subscription record to .brain/marketplace/subscriptions.jsonl.
        Idempotent — duplicate (subscriber, target) pairs are deduplicated on read.
        """
        import datetime
        events = event_types if isinstance(event_types, list) else ["tier_changed", "quarantined"]
        sub_file = _get_subscriptions_file()
        record = {
            "subscriber": subscriber,
            "target": target,
            "event_types": events,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "active": True,
        }
        with open(sub_file, "a") as fh:
            fh.write(json.dumps(record) + "\n")
        return json.dumps({"subscribed": True, "subscriber": subscriber,
                           "target": target, "event_types": events}, indent=2)

    def _marketplace_unsubscribe(subscriber: str, target: str = "*"):
        """Remove all active subscriptions for (subscriber, target) pair."""
        sub_file = _get_subscriptions_file()
        if not sub_file.exists():
            return json.dumps({"removed": 0, "subscriber": subscriber, "target": target}, indent=2)
        lines = sub_file.read_text().splitlines()
        kept, removed = [], 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                kept.append(line)
                continue
            if rec.get("subscriber") == subscriber and rec.get("target") == target:
                removed += 1
            else:
                kept.append(line)
        sub_file.write_text("\n".join(kept) + ("\n" if kept else ""))
        return json.dumps({"removed": removed, "subscriber": subscriber, "target": target}, indent=2)

    def _marketplace_subscriptions(subscriber=None):
        """List all active subscriptions, optionally filtered by subscriber."""
        sub_file = _get_subscriptions_file()
        if not sub_file.exists():
            return json.dumps({"subscriptions": [], "count": 0}, indent=2)
        subs = []
        seen = set()
        for line in sub_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if subscriber and rec.get("subscriber") != subscriber:
                continue
            key = (rec.get("subscriber"), rec.get("target"))
            if key in seen:
                continue
            seen.add(key)
            if rec.get("active", True):
                subs.append(rec)
        return json.dumps({"subscriptions": subs, "count": len(subs)}, indent=2)

    def _marketplace_diff(snapshot_a, snapshot_b):
        """Diff two registry snapshots produced by marketplace_export.

        Accepts either JSON strings or pre-parsed lists of card dicts.
        Returns added, removed, and changed addresses with tier/quarantine deltas.
        """
        def _parse(s):
            if isinstance(s, str):
                try:
                    parsed = json.loads(s)
                except Exception as exc:
                    return None, str(exc)
                cards = parsed.get("cards") if isinstance(parsed, dict) else parsed
            elif isinstance(s, list):
                cards = s
            elif isinstance(s, dict):
                cards = s.get("cards", [])
            else:
                return None, f"unexpected type {type(s)}"
            return {c["address"]: c for c in cards if "address" in c}, None

        map_a, err_a = _parse(snapshot_a)
        if err_a:
            return json.dumps({"error": f"snapshot_a parse error: {err_a}"}, indent=2)
        map_b, err_b = _parse(snapshot_b)
        if err_b:
            return json.dumps({"error": f"snapshot_b parse error: {err_b}"}, indent=2)

        keys_a, keys_b = set(map_a), set(map_b)
        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        changed = []
        for addr in sorted(keys_a & keys_b):
            ca, cb = map_a[addr], map_b[addr]
            deltas = {}
            for field in ("tier", "quarantined", "inactive", "success_rate", "connection_count"):
                va, vb = ca.get(field), cb.get(field)
                if va != vb:
                    deltas[field] = {"before": va, "after": vb}
            if deltas:
                changed.append({"address": addr, "deltas": deltas})

        return json.dumps({
            "added": added,
            "removed": removed,
            "changed": changed,
            "summary": {
                "added_count": len(added),
                "removed_count": len(removed),
                "changed_count": len(changed),
            },
        }, indent=2)

    @mcp.tool()
    def nucleus_sync(action: str, params: dict = {}) -> str:
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
  relay_post       - Post message to another session type (Cowork↔Claude Code). params: {to, subject, body, priority?, context?, sender?, to_session_id?, from_session_id?, in_reply_to?}
  relay_inbox      - Read messages for current session type. params: {unread_only?, limit?, recipient?, session_id?}
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
  marketplace_export   - Full registry snapshot (read-only). params: {}
  marketplace_diff     - Diff two registry snapshots. params: {snapshot_a, snapshot_b}
  marketplace_subscribe - Subscribe to tier-change events. params: {subscriber, target?, event_types?}
  marketplace_unsubscribe - Remove subscription. params: {subscriber, target?}
  marketplace_subscriptions - List subscriptions. params: {subscriber?}
"""
        return dispatch(action, params, ROUTER, "nucleus_sync")

    return [("nucleus_sync", nucleus_sync)]
