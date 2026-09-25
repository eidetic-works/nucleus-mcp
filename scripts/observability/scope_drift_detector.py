#!/usr/bin/env python3
"""Detect charter-scope-creep: relays whose tags fall outside the agent's permitted scope.

Source-of-truth: .brain/charters/scope_taxonomy.yaml — agent → permitted_tags + permitted_event_types.
Brittle by design (substring/exact match); cheap to maintain. Upgrade to LLM-judge later if false-positive
rate climbs above ~10%.

Usage:
    scope_drift_detector.py [--since 2026-05-01T00:00:00Z] [--agent claude_code_main] [--json]

Exit codes:
    0 — no drift detected
    1 — drift found (fail-loud signal)
    2 — substrate error (no taxonomy, no relays)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from typing import Any

from _common import brain_path, extract_tags_from_relay, iter_relays, load_taxonomy, relay_buckets


# load_taxonomy + _minimal_yaml_parse moved to _common.py for reuse by
# cross_trio_dashboard.cross_talk_rate (taxonomy-driven lane keywords).


def detect_drift(taxonomy: dict[str, dict[str, Any]], since: str | None,
                 only_agent: str | None = None) -> list[dict[str, Any]]:
    """Return drift incidents per relay."""
    drifts: list[dict[str, Any]] = []
    for bucket in relay_buckets():
        for relay in iter_relays(bucket, since_iso=since):
            sender = relay.get("from")
            if not sender:
                continue
            if only_agent and sender != only_agent:
                continue
            charter = taxonomy.get(sender)
            if not charter:
                drifts.append({
                    "type": "no_charter_for_agent",
                    "agent": sender,
                    "relay_id": relay.get("id", "?"),
                    "severity": "low",
                })
                continue
            permitted = set(charter.get("permitted_tags", []))
            tags = extract_tags_from_relay(relay)
            if not tags:
                continue  # untagged is not drift
            off_charter = []
            for tag in tags:
                # Substring-match against any permitted tag
                if not any(p in tag or tag in p for p in permitted):
                    off_charter.append(tag)
            if off_charter:
                drifts.append({
                    "type": "off_charter_tags",
                    "agent": sender,
                    "relay_id": relay.get("id", "?"),
                    "off_charter_tags": off_charter,
                    "all_tags": tags,
                    "severity": "medium",
                })
    return drifts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default=None)
    p.add_argument("--agent", default=None, help="Filter to single agent")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    try:
        tax = load_taxonomy()
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    drifts = detect_drift(tax, args.since, args.agent)

    if args.json:
        print(json.dumps({"drifts": drifts, "count": len(drifts)}, indent=2))
    else:
        if not drifts:
            print("no scope drift detected")
        else:
            print(f"scope drift incidents: {len(drifts)}")
            by_agent: dict[str, int] = defaultdict(int)
            for d in drifts:
                by_agent[d["agent"]] += 1
            for ag, n in sorted(by_agent.items()):
                print(f"  {ag}: {n}")
            print()
            for d in drifts[:20]:  # cap output
                print(f"  [{d['severity']}] {d['type']}: {d['agent']} — relay {d['relay_id']}")
                if "off_charter_tags" in d:
                    print(f"          off-charter: {d['off_charter_tags']}")

    return 1 if any(d["severity"] in ("medium", "high") for d in drifts) else 0


if __name__ == "__main__":
    sys.exit(main())
