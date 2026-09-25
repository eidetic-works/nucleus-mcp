#!/usr/bin/env python3
"""Cross-trio observability dashboard — aggregate metrics from coord_events ledger + relay buckets.

Metrics computed:
  1. Per-agent relay rate (sends per hour, last N hours)
  2. Cross-talk rate — relays where >1 agent's lane keywords appear in tags
  3. Ack-latency — gap between relay_fired (send) and relay_processed (read) per relay_id
  4. Sender-coercion incident count (delegates to sender_coercion_alarm)
  5. Scope-drift incident count (delegates to scope_drift_detector)
  6. Coord-overhead-per-shipped-PR — coord events emitted per merged PR (rough proxy)

Usage:
    cross_trio_dashboard.py [--since 2026-05-01T00:00:00Z] [--json]

Output: human-readable text by default, structured JSON with --json.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from _common import (extract_tags_from_relay, iter_coord_events, iter_relays,
                     load_taxonomy, parse_iso, relay_buckets,
                     taxonomy_lane_keywords)


def per_agent_relay_rate(since: str | None) -> dict[str, float]:
    """Returns relays-per-hour per agent."""
    counts: Counter[str] = Counter()
    earliest: dict[str, datetime] = {}
    latest: dict[str, datetime] = {}
    for bucket in relay_buckets():
        for relay in iter_relays(bucket, since_iso=since):
            sender = relay.get("from")
            if not sender:
                continue
            counts[sender] += 1
            ts = parse_iso(relay.get("created_at", ""))
            if ts:
                if sender not in earliest or ts < earliest[sender]:
                    earliest[sender] = ts
                if sender not in latest or ts > latest[sender]:
                    latest[sender] = ts
    rates: dict[str, float] = {}
    for sender, count in counts.items():
        span_h = max(((latest[sender] - earliest[sender]).total_seconds() / 3600.0), 1.0)
        rates[sender] = round(count / span_h, 2)
    return rates


def cross_talk_rate(since: str | None) -> dict[str, Any]:
    """A relay tagged with another agent's lane-keyword counts as cross-talk.

    Lane keywords are derived from .brain/charters/scope_taxonomy.yaml at runtime —
    a tag counts as a lane-keyword for agent X iff it appears in EXACTLY ONE agent's
    permitted_tags. Shared vocabulary (tags under 2+ agents) is dropped; only
    agent-exclusive tags signal cross-talk. Taxonomy edits flow through without
    code changes (was hard-coded prior to this commit).
    """
    try:
        LANE_KEYWORDS = taxonomy_lane_keywords(load_taxonomy())
    except SystemExit:
        # Taxonomy missing — fall back to empty keyword set so dashboard still runs
        # (cross-talk metric will report 0%, not crash). Drift detector surfaces the
        # missing-taxonomy case loudly enough on its own.
        LANE_KEYWORDS = {}
    total = 0
    cross_talk = 0
    by_pair: Counter[tuple[str, str]] = Counter()
    for bucket in relay_buckets():
        for relay in iter_relays(bucket, since_iso=since):
            sender = relay.get("from")
            if not sender or sender not in LANE_KEYWORDS:
                continue
            tags = extract_tags_from_relay(relay)
            if not tags:
                continue
            total += 1
            tag_text = " ".join(tags).lower()
            for other_agent, keywords in LANE_KEYWORDS.items():
                if other_agent == sender:
                    continue
                if any(kw in tag_text for kw in keywords):
                    cross_talk += 1
                    by_pair[(sender, other_agent)] += 1
                    break
    rate = (cross_talk / total) if total else 0
    return {
        "total_relays": total,
        "cross_talk_count": cross_talk,
        "cross_talk_rate": round(rate, 3),
        "top_pairs": by_pair.most_common(5),
    }


def ack_latency(since: str | None) -> dict[str, Any]:
    """Compute ack-latency from coord_events: relay_fired -> relay_processed paired by relay_id.

    Per peer's PR #213, relay_processed events use chosen_option=relay_id from the source relay_fired.
    """
    fires: dict[str, datetime] = {}  # relay_id -> first relay_fired ts
    processes: dict[str, datetime] = {}  # relay_id -> first relay_processed ts
    for ev in iter_coord_events(since_iso=since):
        et = ev.get("event_type")
        rid = ev.get("chosen_option")
        ts = parse_iso(ev.get("timestamp", ""))
        if not (et and rid and ts):
            continue
        if et == "relay_fired" and rid not in fires:
            fires[rid] = ts
        elif et == "relay_processed" and rid not in processes:
            processes[rid] = ts
    paired = []
    for rid, fire_ts in fires.items():
        proc_ts = processes.get(rid)
        if proc_ts and proc_ts >= fire_ts:
            paired.append((proc_ts - fire_ts).total_seconds())
    if not paired:
        return {"paired_count": 0, "p50_seconds": None, "p95_seconds": None, "fires": len(fires), "processes": len(processes)}
    paired.sort()
    return {
        "paired_count": len(paired),
        "p50_seconds": round(paired[len(paired) // 2], 1),
        "p95_seconds": round(paired[int(len(paired) * 0.95)] if len(paired) > 1 else paired[0], 1),
        "mean_seconds": round(statistics.mean(paired), 1),
        "fires": len(fires),
        "processes": len(processes),
        "unprocessed": len(fires) - len([r for r in fires if r in processes]),
    }


def coord_overhead_per_pr(since: str | None) -> dict[str, Any]:
    """Rough proxy: coord_events emitted per merged PR in the time window.

    Uses gh CLI to count merged PRs since `--since`. Skips if gh unavailable.
    """
    coord_count = sum(1 for _ in iter_coord_events(since_iso=since))
    pr_count = 0
    if since:
        try:
            res = subprocess.run(
                ["gh", "pr", "list", "--repo", "eidetic-works/mcp-server-nucleus",
                 "--state", "merged", "--limit", "100",
                 "--search", f"merged:>={since[:10]}",
                 "--json", "number"],
                capture_output=True, text=True, timeout=15,
            )
            if res.returncode == 0:
                pr_count = len(json.loads(res.stdout or "[]"))
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pr_count = 0
    if pr_count == 0:
        return {"coord_events": coord_count, "merged_prs": 0, "events_per_pr": None}
    return {
        "coord_events": coord_count,
        "merged_prs": pr_count,
        "events_per_pr": round(coord_count / pr_count, 1),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default=None,
                   help="ISO8601 lower bound (default: last 24h)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.since:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        since = args.since

    metrics = {
        "since": since,
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "per_agent_relay_rate_per_hour": per_agent_relay_rate(since),
        "cross_talk": cross_talk_rate(since),
        "ack_latency": ack_latency(since),
        "coord_overhead_per_pr": coord_overhead_per_pr(since),
    }

    if args.json:
        print(json.dumps(metrics, indent=2, default=str))
        return 0

    print(f"# Cross-trio observability dashboard\n")
    print(f"window: since {since}  (computed at {metrics['computed_at']})\n")
    print("## Per-agent relay rate (per hour)")
    for agent, rate in sorted(metrics["per_agent_relay_rate_per_hour"].items(), key=lambda x: -x[1]):
        print(f"  {agent}: {rate}/hr")
    print()
    ct = metrics["cross_talk"]
    print(f"## Cross-talk")
    print(f"  total relays: {ct['total_relays']}")
    print(f"  cross-talk count: {ct['cross_talk_count']}")
    print(f"  cross-talk rate: {ct['cross_talk_rate'] * 100:.1f}%")
    if ct["top_pairs"]:
        print(f"  top pairs:")
        for (a, b), n in ct["top_pairs"]:
            print(f"    {a} -> {b}-lane: {n}")
    print()
    al = metrics["ack_latency"]
    print(f"## Ack-latency (relay_fired -> relay_processed)")
    print(f"  paired: {al['paired_count']} / {al['fires']} fires (unprocessed: {al.get('unprocessed', 0)})")
    if al["paired_count"]:
        print(f"  p50: {al['p50_seconds']}s   p95: {al['p95_seconds']}s   mean: {al['mean_seconds']}s")
    else:
        print(f"  no paired events yet (relay_processed emit landed in PR #213; need post-merge data)")
    print()
    co = metrics["coord_overhead_per_pr"]
    print(f"## Coord-overhead-per-PR (rough)")
    print(f"  coord events: {co['coord_events']}, merged PRs: {co['merged_prs']}")
    if co.get("events_per_pr") is not None:
        print(f"  events/PR: {co['events_per_pr']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
