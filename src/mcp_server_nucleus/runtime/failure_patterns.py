"""Failure Pattern Library — Immune memory for governance.

Every unique Tier 5 failure gets fingerprinted and cataloged.
After 3 occurrences of the same pattern, it's flagged as recurring.

This is the foundation for auto-rule generation and instruction
distillation in future iterations.

Storage: .brain/governance/failure_patterns.jsonl
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("nucleus.failure_patterns")


def _patterns_path(project_root: Path) -> Path:
    """Return path to failure patterns JSONL, creating dir if needed."""
    p = project_root / ".brain" / "governance" / "failure_patterns.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _classify_failure(signal: dict) -> str:
    """Classify a Tier 5 failure into a failure mode.

    Returns: zero_delta, negative_delta, insufficient_delta, file_missing
    """
    if signal.get("check") == "outcome_file":
        return "file_missing"

    actual = signal.get("actual_delta", 0)
    claimed = signal.get("claimed_delta", 0)

    if actual == 0:
        return "zero_delta"
    if actual < 0:
        return "negative_delta"
    if claimed > 0 and actual < claimed * 0.25:
        return "insufficient_delta"
    return "unknown"


def catalog_failure(signal: dict, plan_file: str,
                    project_root: Path = None):
    """Catalog a governance failure for pattern detection.

    Called by goal_tracker when a Tier 5 signal fails.
    Writes to .brain/governance/failure_patterns.jsonl.
    """
    if signal.get("passed", True):
        return  # only catalog failures

    root = project_root or _detect_root()
    metric = signal.get("metric", signal.get("check", "unknown"))
    failure_mode = _classify_failure(signal)
    pattern_key = f"{metric}:{failure_mode}"

    entry = {
        "pattern_key": pattern_key,
        "metric": metric,
        "failure_mode": failure_mode,
        "hit_ratio": signal.get("hit_ratio", 0.0),
        "claimed_delta": signal.get("claimed_delta", 0),
        "actual_delta": signal.get("actual_delta", 0),
        "plan_file": str(plan_file),
        "ts": datetime.now().isoformat(),
    }

    pp = _patterns_path(root)
    try:
        with open(pp, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug(f"Failed to catalog failure pattern: {e}")

    # Check for recurring pattern
    count = _count_pattern(root, pattern_key)
    if count >= 3:
        logger.info(
            f"Recurring failure pattern detected: {pattern_key} "
            f"({count} occurrences)"
        )


def _count_pattern(project_root: Path, pattern_key: str) -> int:
    """Count occurrences of a specific pattern key."""
    pp = _patterns_path(project_root)
    if not pp.exists():
        return 0
    count = 0
    for line in pp.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("pattern_key") == pattern_key:
                count += 1
        except json.JSONDecodeError:
            continue
    return count


def get_recurring_patterns(project_root: Path,
                           min_count: int = 3) -> list[dict]:
    """Return failure patterns that have occurred >= min_count times.

    Returns list of dicts with: pattern_key, count, last_occurrence,
    failure_mode, metric.
    """
    pp = _patterns_path(project_root)
    if not pp.exists():
        return []

    from collections import Counter, defaultdict
    counts: Counter = Counter()
    last_seen: dict[str, dict] = {}

    for line in pp.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            key = entry.get("pattern_key", "")
            counts[key] += 1
            last_seen[key] = entry
        except json.JSONDecodeError:
            continue

    recurring = []
    for key, count in counts.most_common():
        if count >= min_count:
            last = last_seen[key]
            recurring.append({
                "pattern_key": key,
                "count": count,
                "metric": last.get("metric", "?"),
                "failure_mode": last.get("failure_mode", "?"),
                "last_occurrence": last.get("ts", "?"),
            })

    return recurring


def get_all_patterns(project_root: Path) -> list[dict]:
    """Return all failure pattern entries."""
    pp = _patterns_path(project_root)
    if not pp.exists():
        return []
    entries = []
    for line in pp.read_text(errors="ignore").splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _detect_root() -> Path:
    """Detect project root from cwd."""
    p = Path.cwd().resolve()
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return d
    return p
