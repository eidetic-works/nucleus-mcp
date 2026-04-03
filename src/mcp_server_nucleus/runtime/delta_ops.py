"""Delta Operations — Measures the gap between intent and reality.

The Delta is the fundamental learning primitive of the compounding substrate.
Built on ADUN's Jaccard similarity engine, generalized beyond engrams to ALL
brain operations.

ADUN asks: "Is this new information redundant with what I know?" → Deduplicate.
Delta asks: "Is what happened consistent with what was intended?" → Measure gap.

Same engine. Different question.

Storage: .brain/deltas/deltas.jsonl (JSONL, append-only)
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from .common import get_brain_path

logger = logging.getLogger(__name__)

# Stop words reused from ADUN pipeline (memory_pipeline.py lines 195-200)
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall",
    "for", "and", "but", "or", "nor", "not", "so", "yet",
    "to", "of", "in", "on", "at", "by", "with", "from",
    "this", "that", "it", "its", "we", "our", "their",
})

VALID_FRONTIERS = {"GROUND", "ALIGN", "COMPOUND"}


def _tokenize(text: str) -> set:
    """Tokenize text into word set minus stop words."""
    return set(text.lower().split()) - _STOP_WORDS


def measure_delta(expected: str, actual: str) -> Dict:
    """Measure the gap between expected intent and actual outcome.

    Uses Jaccard similarity (same as ADUN pipeline) but interprets differently:
    - High similarity (>0.8) → positive (ALIGNED)
    - Medium similarity (0.4-0.8) → lateral (DIVERGED)
    - Low similarity (<0.4) → negative (PIVOTED)

    Returns dict with magnitude, direction, similarity, unique words each side.
    """
    expected_words = _tokenize(expected)
    actual_words = _tokenize(actual)

    union = expected_words | actual_words
    if not union:
        return {
            "magnitude": 0.0,
            "direction": "positive",
            "similarity": 1.0,
            "expected_unique": [],
            "actual_unique": [],
        }

    intersection = expected_words & actual_words
    similarity = round(len(intersection) / len(union), 3)
    magnitude = round(1.0 - similarity, 3)

    if similarity >= 0.8:
        direction = "positive"
    elif similarity >= 0.4:
        direction = "lateral"
    else:
        direction = "negative"

    return {
        "magnitude": magnitude,
        "direction": direction,
        "similarity": similarity,
        "expected_unique": sorted(list(expected_words - actual_words))[:5],
        "actual_unique": sorted(list(actual_words - expected_words))[:5],
    }


def record_delta(
    frontier: str,
    expected_source: str,
    expected_intent: str,
    actual_source: str,
    actual_outcome: str,
    insight: str = "",
    corrections: Optional[List[str]] = None,
    brain: Optional[Path] = None,
) -> Optional[str]:
    """Record a Delta — the measured gap between intent and reality.

    Steps:
    1. Validate frontier
    2. Compute magnitude via Jaccard word overlap
    3. Determine direction (positive/lateral/negative)
    4. Write to .brain/deltas/deltas.jsonl
    5. Reinvest: recurring patterns → Strategy engram, negatives → DPO
    6. Emit delta_recorded event
    7. Return delta_id

    Args:
        frontier: "GROUND", "ALIGN", or "COMPOUND"
        expected_source: identifier for the expectation source
        expected_intent: what was expected (free text)
        actual_source: identifier for the actual outcome source
        actual_outcome: what actually happened (free text)
        insight: extracted learning from the gap
        corrections: list of corrective actions taken
        brain: brain path override (uses get_brain_path() if None)

    Returns:
        delta_id string, or None on failure.
    """
    if frontier not in VALID_FRONTIERS:
        logger.warning(f"Invalid frontier '{frontier}', must be one of {VALID_FRONTIERS}")
        return None

    try:
        brain = brain or get_brain_path()
    except Exception:
        logger.warning("Cannot record delta: no brain path available")
        return None

    # Ensure deltas directory exists
    deltas_dir = brain / "deltas"
    deltas_dir.mkdir(parents=True, exist_ok=True)
    deltas_path = deltas_dir / "deltas.jsonl"

    # Measure the gap
    gap = measure_delta(expected_intent, actual_outcome)

    # Build delta record
    delta_id = f"d_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    delta_record = {
        "delta_id": delta_id,
        "timestamp": timestamp,
        "frontier": frontier,
        "expected": {
            "source_type": expected_source.split("_")[0] if "_" in expected_source else "unknown",
            "source_id": expected_source,
            "intent": expected_intent,
        },
        "actual": {
            "source_type": actual_source.split("_")[0] if "_" in actual_source else "unknown",
            "source_id": actual_source,
            "outcome": actual_outcome,
        },
        "delta": {
            "magnitude": gap["magnitude"],
            "direction": gap["direction"],
            "insight": insight,
            "corrections": corrections or [],
        },
        "reinvestment": {
            "engram_written": None,
            "task_created": None,
            "archive_turn_id": None,
            "baseline_updated": False,
        },
    }

    # Write to deltas.jsonl
    try:
        from .hardening import safe_append_jsonl
        safe_append_jsonl(deltas_path, delta_record)
    except Exception as e:
        logger.warning(f"Failed to write delta: {e}")
        return None

    # Reinvest — recurring patterns → engrams, negatives → DPO
    try:
        reinvestment = _reinvest(brain, delta_record, frontier, insight, deltas_path)
        delta_record["reinvestment"] = reinvestment
    except Exception:
        pass  # Reinvestment failure never blocks delta recording

    # Emit event (wires into Artery 4 triggers + Artery 5 hooks)
    try:
        from .event_ops import _emit_event
        _emit_event("delta_recorded", "delta_pipeline", {
            "delta_id": delta_id,
            "frontier": frontier,
            "direction": gap["direction"],
            "magnitude": gap["magnitude"],
            "insight": insight,
        })
    except Exception:
        pass  # Event emission failure never blocks delta recording

    return delta_id


def _reinvest(
    brain: Path,
    delta: Dict,
    frontier: str,
    insight: str,
    deltas_path: Path,
) -> Dict:
    """Reinvestment: recurring patterns → Strategy engrams + DPO pairs.

    Returns updated reinvestment dict.
    """
    reinvestment = {
        "engram_written": None,
        "task_created": None,
        "archive_turn_id": None,
        "baseline_updated": False,
    }

    if not insight:
        return reinvestment

    # Count similar insights in recent deltas (30 days)
    recent = query_deltas(brain=brain, since="30d")
    insight_words = _tokenize(insight)

    similar_count = 0
    for d in recent:
        other_insight = d.get("delta", {}).get("insight", "")
        if not other_insight:
            continue
        other_words = _tokenize(other_insight)
        union = insight_words | other_words
        if not union:
            continue
        similarity = len(insight_words & other_words) / len(union)
        if similarity > 0.6:
            similar_count += 1

    # 3+ recurring pattern → auto-create Strategy engram at intensity 9
    if similar_count >= 3:
        try:
            from .memory_pipeline import MemoryPipeline
            pipeline = MemoryPipeline(brain_path=brain)
            insight_hash = hashlib.md5(insight.encode()).hexdigest()[:8]
            key = f"recurring_{insight_hash}"
            pipeline.process(
                text=f"RECURRING PATTERN ({similar_count}x): {insight}",
                context="Strategy",
                intensity=9,
                source_agent="delta_pipeline",
                key=key,
            )
            reinvestment["engram_written"] = key
        except Exception:
            pass

    # Negative deltas → DPO pair
    if delta["delta"]["direction"] == "negative":
        try:
            from .archive_pipeline import ArchivePipeline
            archive = ArchivePipeline(brain_path=brain)
            archive.record_outcome_preference(
                event_type=f"delta_{frontier.lower()}_negative",
                prompt=f"Intent: {delta['expected']['intent']}",
                response=f"Outcome: {delta['actual']['outcome']}. Insight: {insight}",
                success=False,
                context=f"Frontier: {frontier}. Magnitude: {delta['delta']['magnitude']}",
            )
            reinvestment["archive_turn_id"] = delta["delta_id"]
        except Exception:
            pass

    return reinvestment


def query_deltas(
    brain: Optional[Path] = None,
    frontier: Optional[str] = None,
    direction: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 200,
) -> List[Dict]:
    """Query accumulated deltas with optional filters.

    Args:
        brain: brain path (uses get_brain_path() if None)
        frontier: filter by "GROUND", "ALIGN", or "COMPOUND"
        direction: filter by "positive", "lateral", or "negative"
        since: time filter like "7d", "30d", "90d"
        limit: max results (default 200)

    Returns:
        List of delta dicts, most recent first.
    """
    try:
        brain = brain or get_brain_path()
    except Exception:
        return []

    deltas_path = brain / "deltas" / "deltas.jsonl"
    if not deltas_path.exists():
        return []

    # Parse time filter
    cutoff = None
    if since:
        try:
            days = int(since.rstrip("d"))
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        except (ValueError, AttributeError):
            pass

    # Read and filter
    try:
        from .hardening import safe_read_jsonl
        all_deltas = safe_read_jsonl(deltas_path)
    except Exception:
        return []

    results = []
    for d in all_deltas:
        if cutoff and d.get("timestamp", "") < cutoff:
            continue
        if frontier and d.get("frontier") != frontier:
            continue
        if direction and d.get("delta", {}).get("direction") != direction:
            continue
        results.append(d)

    # Most recent first
    results.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
    return results[:limit]


def extract_patterns(
    brain: Optional[Path] = None,
    since: Optional[str] = None,
    frontier: Optional[str] = None,
) -> Dict:
    """Extract meta-patterns from accumulated deltas.

    Returns:
    {
        "recurring_negatives": [{"pattern": str, "count": int, "examples": [str]}],
        "improving_areas": [],  # Phase 3: track direction changes over time
        "compound_rate": float,  # ratio of positive deltas to total
        "frontier_health": {
            "GROUND": {"total": N, "positive": M, "rate": float},
            ...
        },
        "total_deltas": int,
    }
    """
    deltas = query_deltas(brain=brain, frontier=frontier, since=since or "30d")

    if not deltas:
        return {
            "recurring_negatives": [],
            "improving_areas": [],
            "compound_rate": 0.0,
            "frontier_health": {},
            "total_deltas": 0,
        }

    # Group by frontier
    by_frontier = {}
    for d in deltas:
        f = d.get("frontier", "UNKNOWN")
        by_frontier.setdefault(f, []).append(d)

    # Compute per-frontier health
    frontier_health = {}
    for f, fdeltas in by_frontier.items():
        positive = sum(
            1 for d in fdeltas
            if d.get("delta", {}).get("direction") == "positive"
        )
        frontier_health[f] = {
            "total": len(fdeltas),
            "positive": positive,
            "rate": round(positive / len(fdeltas), 3) if fdeltas else 0.0,
        }

    # Find recurring negative insights
    negative_insights = [
        d.get("delta", {}).get("insight", "")
        for d in deltas
        if d.get("delta", {}).get("direction") == "negative"
        and d.get("delta", {}).get("insight")
    ]

    # Cluster by word similarity (simple: group by first 3 significant words)
    clusters = {}
    for insight in negative_insights:
        words = sorted(_tokenize(insight))[:3]
        cluster_key = " ".join(words) if words else "unclustered"
        clusters.setdefault(cluster_key, []).append(insight)

    recurring = [
        {"pattern": k, "count": len(v), "examples": v[:2]}
        for k, v in clusters.items()
        if len(v) >= 3
    ]
    recurring.sort(key=lambda r: r["count"], reverse=True)

    # Compound rate: positive deltas / total
    total = len(deltas)
    positive_total = sum(
        1 for d in deltas
        if d.get("delta", {}).get("direction") == "positive"
    )

    return {
        "recurring_negatives": recurring,
        "improving_areas": [],  # Phase 3
        "compound_rate": round(positive_total / total, 3) if total else 0.0,
        "frontier_health": frontier_health,
        "total_deltas": total,
    }


# ── Event Hook: Auto-record Deltas from specific event patterns ──────────

def delta_event_hook(event_type: str, emitter: str, data: dict):
    """Auto-record deltas from specific event patterns.

    Registered via register_event_hook() at module load or server startup.
    Called on every event emission. Produces Deltas for:
    - task_completed_with_fence: GROUND delta (was task outcome as expected?)
    - session_ended: COMPOUND delta (session intent vs session outcome)
    - morning_brief_generated: tracked by Artery 1 directly (not here)
    """
    if os.environ.get("NUCLEUS_DISABLE_DELTA_HOOKS"):
        return

    try:
        if event_type == "task_completed_with_fence":
            _auto_delta_from_task_completion(data)
        elif event_type == "session_ended":
            _auto_delta_from_session_end(data)
    except Exception:
        pass  # Never let delta hooks break event emission


def _auto_delta_from_task_completion(data: dict):
    """GROUND Delta: was the task outcome what was expected?"""
    task_title = data.get("task", data.get("title", ""))
    outcome = data.get("outcome", data.get("result", "completed"))
    task_id = data.get("task_id", data.get("id", "unknown"))

    if not task_title:
        return

    record_delta(
        frontier="GROUND",
        expected_source=f"task_{task_id}",
        expected_intent=f"Complete task: {task_title}",
        actual_source=f"event_task_completed_{task_id}",
        actual_outcome=f"Task completed: {outcome}" if outcome else f"Task completed: {task_title}",
        insight="",  # Auto-deltas start without insight; pattern extraction adds it
    )


def _auto_delta_from_session_end(data: dict):
    """COMPOUND Delta: session intent vs session outcome."""
    summary = data.get("summary", "")
    if not summary:
        return

    # Try to find today's brief recommendation as the "intent"
    try:
        brain = get_brain_path()
        ledger_path = brain / "engrams" / "ledger.jsonl"
        if not ledger_path.exists():
            return

        today_key = f"brief_rec_{datetime.now().strftime('%Y%m%d')}"
        intent = None

        from .hardening import safe_read_jsonl
        engrams = safe_read_jsonl(ledger_path)
        for e in engrams:
            if e.get("key") == today_key and not e.get("deleted", False):
                intent = e.get("value", "")

        if not intent:
            return  # No brief rec to compare against

        record_delta(
            frontier="COMPOUND",
            expected_source=today_key,
            expected_intent=intent,
            actual_source=f"session_ended_{datetime.now().strftime('%Y%m%d_%H%M')}",
            actual_outcome=f"Session summary: {summary}",
            insight="",
            brain=brain,
        )
    except Exception:
        pass
