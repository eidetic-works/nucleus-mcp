"""Billing Subsystem — Usage Cost Tracking from Audit Logs.

Computes per-tool, per-session, and aggregate usage costs from:
1. The interaction audit log (ledger/interaction_log.jsonl)
2. The event ledger (ledger/events.jsonl)
3. Token metering data (ledger/token_metering.jsonl)

Cost model:
- Each interaction is assigned a cost unit based on tool tier
- Tier 1 (read-only): 0.1 units (health, version, list, query, search)
- Tier 2 (write): 0.5 units (write_engram, update, claim, add)
- Tier 3 (compute): 1.0 units (auto_fix_loop, spawn_agent, God Combos)
- Tier 4 (destructive): 2.0 units (delete_file, force_assign)

No external billing API — purely local cost tracking for observability.

Usage:
    from mcp_server_nucleus.runtime.billing import compute_usage_summary
    summary = compute_usage_summary()
"""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .common import get_brain_path, make_response


# ── Cost Tiers ────────────────────────────────────────────────
TIER_COSTS = {
    1: 0.1,   # Read-only
    2: 0.5,   # Write
    3: 1.0,   # Compute
    4: 2.0,   # Destructive
}

# Tool → Tier mapping (patterns matched against tool/action names)
TIER_PATTERNS = {
    4: re.compile(r'delete|force_assign|unlock|lock', re.IGNORECASE),
    3: re.compile(r'auto_fix|spawn_agent|pulse_and_polish|self_healing|fusion_reactor|orchestrate_swarm|autopilot', re.IGNORECASE),
    2: re.compile(r'write|update|add|claim|emit|save|close|archive|set_|create|ingest', re.IGNORECASE),
    1: re.compile(r'.*'),  # Default: everything else is read-only
}


def _classify_tier(action: str) -> int:
    """Classify an action/tool name into a cost tier."""
    for tier in [4, 3, 2, 1]:
        if TIER_PATTERNS[tier].search(action):
            return tier
    return 1


def _load_jsonl(path) -> List[Dict]:
    """Load a JSONL file safely."""
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def compute_usage_summary(
    since_hours: Optional[float] = None,
    group_by: str = "tool",
) -> Dict[str, Any]:
    """Compute usage cost summary from audit logs.

    Args:
        since_hours: Only include entries from the last N hours. None = all time.
        group_by: How to group costs — "tool", "tier", or "session".

    Returns:
        Dict with cost breakdown, totals, and metadata.
    """
    brain = get_brain_path()

    # Load all data sources
    audit_entries = _load_jsonl(brain / "ledger" / "interaction_log.jsonl")
    events = _load_jsonl(brain / "ledger" / "events.jsonl")
    metering = _load_jsonl(brain / "ledger" / "token_metering.jsonl")

    # Time filter
    cutoff = None
    if since_hours:
        cutoff = (datetime.now() - timedelta(hours=since_hours)).isoformat()

    # Process audit entries
    tool_costs: Dict[str, float] = defaultdict(float)
    tier_costs: Dict[int, float] = defaultdict(float)
    tier_counts: Dict[int, int] = defaultdict(int)
    tool_counts: Dict[str, int] = defaultdict(int)
    total_cost = 0.0
    total_interactions = 0
    filtered_count = 0

    for entry in audit_entries:
        ts = entry.get("timestamp", "")
        if cutoff and ts < cutoff:
            filtered_count += 1
            continue

        # Extract tool/action name from various audit log formats
        tool_name = (
            entry.get("tool", "") or
            entry.get("action", "") or
            entry.get("event_type", "") or
            "unknown"
        )

        tier = _classify_tier(tool_name)
        cost = TIER_COSTS[tier]

        tool_costs[tool_name] += cost
        tool_counts[tool_name] += 1
        tier_costs[tier] += cost
        tier_counts[tier] += 1
        total_cost += cost
        total_interactions += 1

    # Also count events as interactions
    for event in events:
        ts = event.get("timestamp", "")
        if cutoff and ts < cutoff:
            continue

        event_type = event.get("event_type", "unknown_event")
        tier = _classify_tier(event_type)
        cost = TIER_COSTS[tier]

        tool_costs[event_type] += cost
        tool_counts[event_type] += 1
        tier_costs[tier] += cost
        tier_counts[tier] += 1
        total_cost += cost
        total_interactions += 1

    # Session tracking (group by date bucket: YYYY-MM-DD or hour)
    session_costs: Dict[str, float] = defaultdict(float)
    session_counts: Dict[str, int] = defaultdict(int)

    def _record_session(ts_str: str, cost_val: float):
        if ts_str:
            session_key = ts_str[:10]  # YYYY-MM-DD
            session_costs[session_key] += cost_val
            session_counts[session_key] += 1

    # Re-scan for session data (audit + events already processed above)
    for entry in audit_entries:
        ts = entry.get("timestamp", "")
        if cutoff and ts < cutoff:
            continue
        tool_name = entry.get("tool", "") or entry.get("action", "") or entry.get("event_type", "") or "unknown"
        _record_session(ts, TIER_COSTS[_classify_tier(tool_name)])

    for event in events:
        ts = event.get("timestamp", "")
        if cutoff and ts < cutoff:
            continue
        _record_session(ts, TIER_COSTS[_classify_tier(event.get("event_type", "unknown_event"))])

    # Build breakdown based on group_by
    if group_by == "tier":
        breakdown = {
            f"tier_{t}": {
                "cost": round(tier_costs[t], 2),
                "count": tier_counts[t],
                "unit_cost": TIER_COSTS[t],
                "label": {1: "read-only", 2: "write", 3: "compute", 4: "destructive"}.get(t, "unknown"),
            }
            for t in sorted(tier_costs.keys())
        }
    elif group_by == "session":
        # Sort by date descending, show last 30 days
        sorted_sessions = sorted(session_costs.items(), key=lambda x: x[0], reverse=True)[:30]
        breakdown = {
            date: {
                "cost": round(cost, 2),
                "count": session_counts[date],
            }
            for date, cost in sorted_sessions
        }
    else:  # group_by == "tool"
        # Sort by cost descending, show top 20
        sorted_tools = sorted(tool_costs.items(), key=lambda x: x[1], reverse=True)[:20]
        breakdown = {
            tool: {
                "cost": round(cost, 2),
                "count": tool_counts[tool],
                "tier": _classify_tier(tool),
            }
            for tool, cost in sorted_tools
        }

    # Token metering summary
    token_summary = {
        "total_entries": len(metering),
        "total_units": sum(m.get("units", 0) for m in metering),
    }

    return {
        "total_cost_units": round(total_cost, 2),
        "total_interactions": total_interactions,
        "breakdown": breakdown,
        "group_by": group_by,
        "time_filter": f"last {since_hours}h" if since_hours else "all time",
        "filtered_out": filtered_count,
        "token_metering": token_summary,
        "cost_model": {
            "tier_1_read": TIER_COSTS[1],
            "tier_2_write": TIER_COSTS[2],
            "tier_3_compute": TIER_COSTS[3],
            "tier_4_destructive": TIER_COSTS[4],
            "currency": "nucleus_units",
        },
        "data_sources": {
            "audit_log": len(audit_entries),
            "events": len(events),
            "metering": len(metering),
        },
    }
