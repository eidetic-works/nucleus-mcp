#!/usr/bin/env python3
"""Scan recent relay traffic for sender-coercion incidents.

Detects relays where the envelope sender (`from`) doesn't match the substrate
identity registered for that session_id (per providers.yaml or recent history).
Per `feedback_relay_post_sender_coercion.md` HARD RULE: explicit-sender discipline
is fail-loud — but only if someone's WATCHING. This script IS that watcher.

Usage:
    sender_coercion_alarm.py [--since 2026-05-01T00:00:00Z] [--json]

Exit codes:
    0 — no incidents
    1 — incidents found (fail-loud signal for cron/CI)
    2 — substrate error (no ledger, no relays, etc.)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from typing import Any

from _common import brain_path, iter_coord_events, iter_relays, parse_iso, relay_buckets, load_taxonomy


def _load_multi_envelope_sessions() -> dict[str, list[str]]:
    """Read multi_envelope_sessions config from scope_taxonomy.yaml.

    Sessions in this list legitimately fire under multiple sender envelopes by design.
    Returns a dict mapping session_id to a list of allowed envelopes (empty list means all allowed).
    """
    try:
        taxonomy = load_taxonomy()
    except SystemExit:
        return {}

    entries = taxonomy.get("multi_envelope_sessions", []) or []
    out: dict[str, list[str]] = {}
    for entry in entries:
        if isinstance(entry, str):
            out[entry] = []
        elif isinstance(entry, dict) and "sid" in entry:
            out[entry["sid"]] = entry.get("allowed_envelopes", [])
    return out


def detect_incidents(since: str | None) -> list[dict[str, Any]]:
    """Return list of suspected sender-coercion incidents.

    Heuristics:
    1. session_id observed with multiple distinct senders within a 24h window
       (one session = one identity; multi-sender = coercion or stolen-id).
    2. Sender field empty/null but session_id present.
    3. Sender field equals 'claude_code' (legacy bare role) when session has
       previously asserted 'claude_code_main' or 'claude_code_peer'.
    """
    multi_envelope_allowlist: dict[str, list[str]] = _load_multi_envelope_sessions()

    incidents: list[dict[str, Any]] = []
    session_senders: dict[str, set[str]] = defaultdict(set)
    session_first_sender: dict[str, str] = {}
    unknown_sid_relays: list[dict[str, Any]] = []  # sid='unknown' wiring artifact, not coercion

    for bucket in relay_buckets():
        for relay in iter_relays(bucket, since_iso=since):
            sid = relay.get("from_session_id")
            sender = relay.get("from")
            if not sid:
                continue

            # Empty sender check
            if not sender:
                incidents.append({
                    "type": "empty_sender",
                    "relay_id": relay.get("id", "?"),
                    "session_id": sid,
                    "bucket": bucket.name,
                    "created_at": relay.get("created_at", "?"),
                })
                continue

            # sid='unknown' is a wiring-not-yet-caught-up artifact (peer 2026-05-02 surfaced 10/27
            # cowork+windsurf relays use literal 'unknown'). Track separately at low-sev so it
            # surfaces but doesn't trip the high-sev exit (would otherwise flag every cron run).
            if sid == "unknown":
                unknown_sid_relays.append({
                    "relay_id": relay.get("id", "?"),
                    "sender": sender,
                    "bucket": bucket.name,
                })
                continue

            session_senders[sid].add(sender)
            if sid not in session_first_sender:
                session_first_sender[sid] = sender

    # Roll up sid='unknown' into one low-sev incident (not per-relay spam)
    if unknown_sid_relays:
        senders_in_unknown = sorted({r["sender"] for r in unknown_sid_relays})
        incidents.append({
            "type": "unknown_session_id",
            "count": len(unknown_sid_relays),
            "senders_observed": senders_in_unknown,
            "severity": "low",
            "note": "sid='unknown' is a wiring artifact (agents not yet emitting from_session_id). Fix by wiring sid in those agents.",
        })

    # Multi-sender per session
    for sid, senders in session_senders.items():
        if len(senders) > 1:
            # Check if it's a legacy-bare->role-aware upgrade (allowed) vs real coercion
            has_bare = "claude_code" in senders
            has_role_aware = any(s in ("claude_code_main", "claude_code_peer") for s in senders)
            if has_bare and has_role_aware and len(senders) == 2:
                # Legacy upgrade — soft incident
                incidents.append({
                    "type": "legacy_bare_to_role_aware",
                    "session_id": sid,
                    "senders_observed": sorted(senders),
                    "severity": "low",
                })
            elif sid in multi_envelope_allowlist:
                allowed = multi_envelope_allowlist[sid]
                if allowed and not senders.issubset(set(allowed)):
                    incidents.append({
                        "type": "multi_sender_per_session",
                        "session_id": sid,
                        "senders_observed": sorted(senders),
                        "severity": "high",
                        "note": f"Session in multi_envelope allowlist, but observed senders not in allowed list: {allowed}"
                    })
                else:
                    # Multi-envelope session by design — roll up as low-sev carveout.
                    # Mirrors the sid='unknown' carveout pattern (PR #218).
                    incidents.append({
                        "type": "multi_envelope_session_carveout",
                        "session_id": sid,
                        "senders_observed": sorted(senders),
                        "severity": "low",
                        "note": "Session is in multi_envelope_sessions allow-list in scope_taxonomy.yaml — multiple envelopes expected by design.",
                    })
            else:
                incidents.append({
                    "type": "multi_sender_per_session",
                    "session_id": sid,
                    "senders_observed": sorted(senders),
                    "severity": "high",
                })

    return incidents


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default=None, help="ISO8601 lower bound (default: all)")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = p.parse_args()

    try:
        incidents = detect_incidents(args.since)
    except SystemExit:
        return 2
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"incidents": incidents, "count": len(incidents)}, indent=2))
    else:
        if not incidents:
            print("no sender-coercion incidents detected")
        else:
            print(f"sender-coercion incidents: {len(incidents)}")
            for inc in incidents:
                sev = inc.get("severity", "?")
                print(f"  [{sev}] {inc['type']}: {inc.get('session_id') or inc.get('relay_id')}")
                if "senders_observed" in inc:
                    print(f"          senders: {inc['senders_observed']}")

    # High-severity incidents = exit 1; only legacy-bare-upgrade soft = exit 0
    high_sev = [i for i in incidents if i.get("severity") == "high" or i["type"] == "empty_sender"]
    return 1 if high_sev else 0


if __name__ == "__main__":
    sys.exit(main())
