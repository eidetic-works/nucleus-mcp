"""Marketplace tool handlers — extracted from sync.py.

Factory: call ``register(emit_event, get_brain_path)`` to obtain a dict
mapping action-name → handler callable suitable for splicing into the
ROUTER in sync.py.
"""
import logging
logger = logging.getLogger(__name__)

import json


def register(emit_event, get_brain_path):
    """Return a dict of marketplace handler callables.

    Parameters
    ----------
    emit_event:
        The ``helpers["emit_event"]`` callable forwarded from
        ``sync.register``.  Reserved for future use by marketplace
        handlers; accepted so callers don't need to change signature
        when a handler starts emitting events.
    get_brain_path:
        The ``helpers["get_brain_path"]`` callable forwarded from
        ``sync.register``.  Used by audit, alert, and subscription
        helpers that need the brain directory.
    """

    # ── internal helper (not exposed in ROUTER) ───────────────────────
    def _get_subscriptions_file(brain_path=None):
        bp = brain_path or get_brain_path()
        sub_dir = bp / "marketplace"
        sub_dir.mkdir(parents=True, exist_ok=True)
        return sub_dir / "subscriptions.jsonl"

    # ── marketplace closures ──────────────────────────────────────────
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
            lookup_by_address, TrustTier, _get_registry_dir, _get_card_path,
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
            lookup_by_address, TrustTier, _get_registry_dir, _get_card_path,
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

    def _marketplace_audit(caller=None, target=None, action_type=None, since_timestamp=None, limit=50, offset=0):
        """Replay admin_actions.jsonl with filters. Pure read, no mutation.

        Filters: caller, target, action_type, since_timestamp.
        Supports pagination with limit/offset.
        """
        from datetime import datetime, timezone

        brain = get_brain_path()
        admin_log = brain / "marketplace" / "admin_actions.jsonl"

        actions = []
        if not admin_log.exists():
            return json.dumps({"actions": [], "total": 0, "offset": offset, "limit": limit}, indent=2)

        with open(admin_log, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    action = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Apply filters
                if caller and action.get("caller") != caller:
                    continue
                if target and action.get("address") != target:
                    continue
                if action_type and action.get("action") != action_type:
                    continue
                if since_timestamp:
                    try:
                        action_time = datetime.fromisoformat(action["timestamp"].replace("Z", "+00:00"))
                        since_time = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                        if action_time < since_time:
                            continue
                    except Exception:
                        logger.debug("Swallowed exception in register", exc_info=True)
                        continue

                actions.append(action)

        total = len(actions)
        paginated = actions[offset:offset + limit]

        return json.dumps({
            "actions": paginated,
            "total": total,
            "offset": offset,
            "limit": limit,
        }, indent=2)

    def _marketplace_compare(a, b):
        """Head-to-head comparison of two addresses.

        Returns side-by-side capability cards, tier history, reputation trajectory, recent interactions.
        """
        from mcp_server_nucleus.runtime.marketplace import lookup_by_address, ReputationSignals

        card_a = lookup_by_address(a)
        card_b = lookup_by_address(b)

        if card_a is None:
            return json.dumps({"error": f"address '{a}' not registered"}, indent=2)
        if card_b is None:
            return json.dumps({"error": f"address '{b}' not registered"}, indent=2)

        rep_a = {}
        rep_b = {}
        try:
            rep_a = ReputationSignals.compute_signals(a)
        except Exception:
            logger.debug("Swallowed exception in register", exc_info=True)
            pass
        try:
            rep_b = ReputationSignals.compute_signals(b)
        except Exception:
            logger.debug("Swallowed exception in register", exc_info=True)
            pass

        return json.dumps({
            "a": {**card_a, "reputation": rep_a},
            "b": {**card_b, "reputation": rep_b},
        }, indent=2)

    def _marketplace_alert(subscriber, target, event_types=None):
        """Subscribe-style alert system. Register alert rule, notify via relay_post when rule matches.

        Alert rules persist to .brain/marketplace/alerts.jsonl.
        """
        from datetime import datetime, timezone

        brain = get_brain_path()
        alerts_file = brain / "marketplace" / "alerts.jsonl"
        alerts_file.parent.mkdir(parents=True, exist_ok=True)

        if event_types is None:
            event_types = ["tier_changed", "quarantined"]

        record = {
            "subscriber": subscriber,
            "target": target,
            "event_types": event_types,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            "active": True,
        }

        with open(alerts_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        return json.dumps({"subscribed": True, "subscriber": subscriber, "target": target, "event_types": event_types}, indent=2)

    def _marketplace_trends(days: int = 30, brain_path=None):
        """Aggregate % of registry at each tier over last N days.

        Computes tier distribution from tier-change events in admin_actions.jsonl.
        Shows whether marketplace is hardening (more Trusted/Verified) or softening.
        Returns timestamp series showing trend.
        """
        from mcp_server_nucleus.runtime.marketplace import TrustTier
        from datetime import datetime, timedelta, timezone
        from pathlib import Path

        brain = brain_path if brain_path is not None else get_brain_path()
        if isinstance(brain, str):
            brain = Path(brain)
        admin_log = brain / "marketplace" / "admin_actions.jsonl"
        registry_dir = brain / "marketplace" / "registry"

        # Read current registry state
        current_cards = []
        if registry_dir.exists():
            for card_file in registry_dir.glob("*.json"):
                try:
                    with open(card_file, "r") as f:
                        card = json.load(f)
                        current_cards.append(card)
                except (json.JSONDecodeError, IOError):
                    pass

        # Build current tier map
        current_tiers = {}
        for card in current_cards:
            address = card.get("address")
            if address:
                current_tiers[address] = card.get("tier", 0)

        # Read ALL tier change history (not filtered by date)
        tier_changes = []
        if admin_log.exists():
            with open(admin_log, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        action = json.loads(line)
                        if action.get("action") == "promote":
                            ts_str = action.get("timestamp", "")
                            if ts_str:
                                try:
                                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                    tier_changes.append({
                                        "timestamp": ts,
                                        "address": action.get("address"),
                                        "from_tier": action.get("from_tier"),
                                        "to_tier": action.get("to_tier"),
                                    })
                                except ValueError:
                                    pass
                    except json.JSONDecodeError:
                        pass

        # Sort changes chronologically
        tier_changes.sort(key=lambda c: c["timestamp"])

        # Compute daily snapshots by walking backwards from current state
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)
        snapshots = []

        # Walk backwards day by day
        for day_offset in range(days, -1, -1):
            snapshot_date = start_date + timedelta(days=day_offset)
            snapshot_date_end = snapshot_date + timedelta(days=1)

            # Reset to current tiers for each day
            working_tiers = dict(current_tiers)

            # Apply tier changes that happened AFTER snapshot_date_end
            # This reverts the state to what it was at the end of snapshot_date
            day_changes = [
                tc for tc in tier_changes
                if tc["timestamp"] > snapshot_date_end
            ]

            # Apply changes in reverse chronological order (undoing from newest to oldest)
            for tc in sorted(day_changes, key=lambda c: c["timestamp"], reverse=True):
                addr = tc["address"]
                if addr in working_tiers:
                    working_tiers[addr] = tc["from_tier"]

            # Compute distribution
            if working_tiers:
                total = len(working_tiers)
                tier_counts = {t.name.lower(): 0 for t in TrustTier}
                for tier_val in working_tiers.values():
                    try:
                        tier_name = TrustTier(tier_val).name.lower()
                    except Exception:
                        logger.debug("Swallowed exception in register", exc_info=True)
                        tier_name = "unverified"
                    tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1

                distribution = {
                    t: float(round(count / total * 100, 2)) if total > 0 else 0.0
                    for t, count in tier_counts.items()
                }
            else:
                total = 0
                distribution = {t.name.lower(): 0.0 for t in TrustTier}

            snapshots.append({
                "date": snapshot_date.strftime("%Y-%m-%d"),
                "total_registered": total,
                "distribution": distribution,
            })

        # Reverse to get chronological order
        snapshots.reverse()

        # Determine trend
        if not current_cards:
            return json.dumps({
                "trend": "insufficient_data",
                "days_analyzed": days,
                "total_changes": len(tier_changes),
                "snapshots": [],
            }, indent=2)
        
        if len(snapshots) < 2:
            trend = "insufficient_data"
        else:
            # Check if all snapshots have zero total (empty registry)
            if all(s["total_registered"] == 0 for s in snapshots):
                trend = "insufficient_data"
            else:
                first_dist = snapshots[0]["distribution"]
                last_dist = snapshots[-1]["distribution"]
                
                high_tier_first = first_dist.get("trusted", 0) + first_dist.get("verified", 0)
                high_tier_last = last_dist.get("trusted", 0) + last_dist.get("verified", 0)
                
                if high_tier_last > high_tier_first + 5:  # 5% threshold
                    trend = "hardening"
                elif high_tier_last < high_tier_first - 5:
                    trend = "softening"
                else:
                    trend = "stable"

        return json.dumps({
            "trend": trend,
            "days_analyzed": days,
            "total_changes": len(tier_changes),
            "snapshots": snapshots,
        }, indent=2)

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
                logger.debug("Swallowed exception in register", exc_info=True)
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
                logger.debug("Swallowed exception in register", exc_info=True)
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
                            logger.debug("Swallowed exception in register", exc_info=True)
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
                                   "reason": "target_quarantined"}, indent=2)
            caller_tier = caller_card.get("tier", TrustTier.UNVERIFIED)
            target_tier = target_card.get("tier", TrustTier.UNVERIFIED)
            allowed = caller_tier >= target_tier - 1
            return json.dumps({
                "allowed": allowed,
                "caller": caller,
                "target": target,
                "caller_tier": caller_tier,
                "target_tier": target_tier,
                "reason": None if allowed else "tier_too_low",
            }, indent=2)
        except Exception as exc:
            _log.warning(f"marketplace_can_call lookup failed for {caller}->{target}: {exc}")
            return json.dumps({"allowed": True, "caller": caller, "target": target,
                               "reason": "lookup_failed_fail_open"}, indent=2)

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
                logger.debug("Swallowed exception in register", exc_info=True)
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
                logger.debug("Swallowed exception in register", exc_info=True)
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

    def _marketplace_federation_proxy(target_brain: str, action: str, payload: dict = None):
        """Proxy a marketplace action to a remote brain in the federation.

        Routes the call via the FederationEngine network layer. The target_brain
        must be a known peer (online or suspect). Returns the remote response
        or an error envelope if the peer is unreachable.

        params: {target_brain, action, payload?}
        """
        import asyncio
        from ..runtime.federation_ops import _get_federation_engine

        engine = _get_federation_engine()
        if engine is None:
            return json.dumps({"ok": False, "error": "FederationEngine not available"}, indent=2)

        peers = engine.get_peers()
        peer = next((p for p in peers if p.peer_id == target_brain), None)
        if peer is None:
            return json.dumps({
                "ok": False,
                "error": f"Unknown peer '{target_brain}'. Known peers: {[p.peer_id for p in peers]}"
            }, indent=2)

        message = {"type": "marketplace_proxy", "action": action, "payload": payload or {}}
        try:
            loop = asyncio.new_event_loop()
            response = loop.run_until_complete(
                engine.network.send_message(peer.address, message, timeout=5.0)
            )
            loop.close()
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, indent=2)

        if response is None:
            return json.dumps({
                "ok": False,
                "error": f"No response from peer '{target_brain}' at {peer.address}"
            }, indent=2)

        return json.dumps({"ok": True, "target_brain": target_brain, "response": response}, indent=2)

    def _marketplace_federation_register(address: str, capabilities: list = None,
                                          display_name: str = "", tags: list = None):
        """Register the local brain as a federated capability card in the marketplace.

        Creates or updates a capability card at the given address and broadcasts
        the registration to all online federation peers via gossip. Peers that
        receive the gossip can later discover this brain via marketplace_search.

        params: {address, capabilities?, display_name?, tags?}
        """
        from ..runtime.marketplace import register_tool
        from ..runtime.federation_ops import _get_federation_engine
        import asyncio

        caps = capabilities or []
        card_data = {
            "address": address,
            "display_name": display_name or address,
            "accepts": caps,
            "emits": ["nucleus.federation.response"],
            "tags": tags or ["federation", "brain"],
            "federation": True,
        }

        try:
            card = register_tool(card_data)
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, indent=2)

        # Best-effort: broadcast to federation peers
        broadcast_count = 0
        engine = _get_federation_engine()
        if engine is not None and engine.running:
            peers = engine.get_online_peers()
            message = {"type": "federation_register", "card": card}
            try:
                loop = asyncio.new_event_loop()
                tasks = [
                    engine.network.send_message(p.address, message, timeout=3.0)
                    for p in peers
                ]
                if tasks:
                    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                broadcast_count = len(peers)
                loop.close()
            except Exception:
                logger.debug("Swallowed exception in register", exc_info=True)
                pass

        return json.dumps({
            "ok": True,
            "address": address,
            "broadcast_peers": broadcast_count,
            "card": card,
        }, indent=2)

    def _marketplace_federation_sync():
        """Force an immediate federation state sync and reconcile marketplace registry.

        Triggers full-mesh synchronization via the FederationEngine, then
        computes a diff between the pre-sync and post-sync registry snapshots.
        Returns sync results per peer plus any registry drift detected.

        params: {} (no required params)
        """
        import asyncio
        from ..runtime.federation_ops import _get_federation_engine
        from ..runtime.marketplace import search_by_tags, ReputationSignals

        engine = _get_federation_engine()
        if engine is None:
            return json.dumps({"ok": False, "error": "FederationEngine not available"}, indent=2)

        if not engine.running:
            return json.dumps({
                "ok": False,
                "error": "Federation engine not running. Use federation join first."
            }, indent=2)

        # Snapshot registry before sync
        pre_cards = search_by_tags([])
        pre_addresses = {c.get("address") for c in pre_cards if c.get("address")}

        # Execute sync
        try:
            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(engine.sync_now())
            loop.close()
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, indent=2)

        # Snapshot registry after sync
        post_cards = search_by_tags([])
        post_addresses = {c.get("address") for c in post_cards if c.get("address")}

        added = sorted(post_addresses - pre_addresses)
        removed = sorted(pre_addresses - post_addresses)

        peer_summaries = []
        if results:
            for r in results:
                peer_summaries.append({
                    "peer_id": r.peer_id,
                    "success": r.success,
                    "items_synced": r.items_synced,
                    "conflicts_resolved": r.conflicts_resolved,
                    "sync_time_ms": round(r.sync_time_ms, 2),
                    "error": r.error,
                })

        return json.dumps({
            "ok": True,
            "peers_synced": len(peer_summaries),
            "peer_results": peer_summaries,
            "registry_drift": {
                "added": added,
                "removed": removed,
                "net_change": len(added) - len(removed),
            },
        }, indent=2)

    return {
        "marketplace_search": _marketplace_search,
        "marketplace_whoami": _marketplace_whoami,
        "marketplace_recommend": _marketplace_recommend,
        "marketplace_promote": _marketplace_promote,
        "marketplace_quarantine": _marketplace_quarantine,
        "marketplace_audit": _marketplace_audit,
        "marketplace_compare": _marketplace_compare,
        "marketplace_alert": _marketplace_alert,
        "marketplace_trends": _marketplace_trends,
        "marketplace_export": _marketplace_export,
        "marketplace_dashboard": _marketplace_dashboard,
        "marketplace_history": _marketplace_history,
        "marketplace_can_call": _marketplace_can_call,
        "marketplace_subscribe": _marketplace_subscribe,
        "marketplace_unsubscribe": _marketplace_unsubscribe,
        "marketplace_subscriptions": _marketplace_subscriptions,
        "marketplace_diff": _marketplace_diff,
        "marketplace_federation_proxy": _marketplace_federation_proxy,
        "marketplace_federation_register": _marketplace_federation_register,
        "marketplace_federation_sync": _marketplace_federation_sync,
    }
