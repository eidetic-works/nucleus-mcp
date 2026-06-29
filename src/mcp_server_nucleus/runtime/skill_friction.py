"""Paste-friction metric for the macro-seed loop — the kill-gate signal.

friction = repeated manual pastes a macro would absorb = sum(size - 1) over
qualifying macro clusters. Recorded each extraction run to
<brain>/skills/friction_history.jsonl so the loop self-evaluates: if friction
doesn't drop by the target within the window, flag for kill (no orphan loop).

A "macro cluster" is command-like (imperative / short directives) AND backed by
real work (mean quality grade above a floor) — this filters out conversational
filler that the raw frequency-scorer over-rewards.
"""
import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nucleus.skill_friction")

_GRADE_W = {"copper": 0.2, "silver": 0.5, "gold": 0.8, "platinum": 1.0}
_IMPERATIVE = re.compile(
    r"^\s*(check|run|continue|report|fix|do|update|send|deploy|verify|extract|"
    r"generate|install|review|complete|push|merge|draft|start|stop|sync|relay|"
    r"ship|make|create|add|status|list|free|build|test)\b",
    re.I,
)


def is_macro_cluster(cluster: Dict, min_quality: float = 0.4) -> bool:
    """Command-like + backed by real work. The friction gate (distinct from the
    install allowlist gate)."""
    intents = cluster.get("intents", [])
    if len(intents) < 3:
        return False
    imp = sum(1 for it in intents if _IMPERATIVE.search(str(it)))
    short = sum(1 for it in intents if len(str(it).split()) <= 12)
    cmd_like = (imp / len(intents) >= 0.4) or (short / len(intents) >= 0.7)
    turns = cluster.get("turns", [])
    if turns:
        qual = sum(_GRADE_W.get(t.get("quality_grade", "copper"), 0.2) for t in turns) / len(turns)
    else:
        qual = 0.0
    return cmd_like and qual >= min_quality


def compute_friction(clusters: List[Dict], total_turns: int = 0) -> Dict:
    """Compute the paste-friction metric over a set of clusters."""
    macros = [c for c in clusters if is_macro_cluster(c)]
    addressable = sum(max(0, c.get("size", 0) - 1) for c in macros)
    metric = {
        "macro_clusters": len(macros),
        "total_clusters": len(clusters),
        "addressable_pastes": addressable,
        "total_turns": total_turns,
    }
    # Only record a percentage when we have a real denominator — otherwise it
    # would be a misleading 0.0.
    if total_turns:
        metric["friction_pct"] = round(100.0 * addressable / total_turns, 2)
    return metric


def record_friction(brain_path: Path, metric: Dict, ts: Optional[str] = None) -> None:
    """Append a friction snapshot to the history log (kill-gate input)."""
    p = brain_path / "skills" / "friction_history.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    row = dict(metric)
    row["ts"] = ts or dt.datetime.now(dt.timezone.utc).isoformat()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    logger.info(
        "friction recorded: %s addressable pastes across %s macro clusters",
        metric.get("addressable_pastes"),
        metric.get("macro_clusters"),
    )


def check_kill_gate(
    brain_path: Path, window_days: int = 14, drop_target: float = 0.30
) -> Optional[Dict]:
    """If >= window_days of history exist and friction hasn't dropped at least
    drop_target from the first recorded baseline, return a kill-flag dict.
    Otherwise None. Prevents an orphan loop that never proves its value."""
    p = brain_path / "skills" / "friction_history.jsonl"
    if not p.exists():
        return None
    rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) < 2:
        return None
    first, last = rows[0], rows[-1]
    try:
        t0 = dt.datetime.fromisoformat(first["ts"])
        t1 = dt.datetime.fromisoformat(last["ts"])
    except (KeyError, ValueError):
        return None
    if (t1 - t0).days < window_days:
        return None
    base = first.get("addressable_pastes", 0)
    now = last.get("addressable_pastes", 0)
    if not base:
        # No baseline friction to reduce — the loop is still ramping, not failing.
        return None
    drop = (base - now) / base
    if drop < drop_target:
        return {
            "kill_recommended": True,
            "baseline": base,
            "current": now,
            "drop": round(drop, 3),
            "target": drop_target,
            "window_days": window_days,
        }
    return None
