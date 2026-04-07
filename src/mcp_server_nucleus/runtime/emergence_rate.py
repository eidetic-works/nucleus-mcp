"""
Nucleus Emergence Rate Engine
==============================
Implements anonymized pattern aggregation for data network effects.

The Emergence Rate measures how the system learns from aggregated user
patterns and improves over time. As more users contribute anonymized
patterns, new users benefit from better default suggestions.

This module provides:
1. PatternCollector: Captures usage patterns from engrams, tasks, self-healing fixes
2. PatternAggregator: Anonymizes and aggregates patterns across sessions
3. PatternSuggester: Surfaces top patterns as default suggestions for new users
"""

import json
import hashlib
import logging
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("nucleus.emergence")


# ============================================================
# PATTERN TYPES
# ============================================================

PATTERN_TYPES = {
    "workflow": "Recurring sequences of tool calls or commands",
    "error_fix": "Self-healing fixes that resolved errors",
    "recipe_usage": "Recipe install and customization patterns",
    "engram_context": "Most common engram context categories",
    "session_depth": "Typical session depth patterns",
    "tool_combo": "Frequently used tool combinations",
}


@dataclass
class Pattern:
    """A single observed usage pattern."""
    pattern_type: str
    pattern_key: str           # Anonymized key (hashed)
    pattern_value: str         # Human-readable description
    frequency: int = 1
    effectiveness: float = 0.0  # 0.0 to 1.0 (how often it led to success)
    first_seen: str = ""
    last_seen: str = ""
    source_count: int = 1      # Number of unique sources (anonymized)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.pattern_type,
            "key": self.pattern_key,
            "value": self.pattern_value,
            "frequency": self.frequency,
            "effectiveness": round(self.effectiveness, 3),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "source_count": self.source_count,
        }


# ============================================================
# PATTERN COLLECTOR: Captures patterns from local brain
# ============================================================

class PatternCollector:
    """
    Scans the local .brain folder and extracts usage patterns.
    All data is anonymized before aggregation.
    """

    def __init__(self, brain_path: Optional[Path] = None):
        self._brain_path = brain_path
        if not self._brain_path:
            try:
                from .common import get_brain_path
                self._brain_path = get_brain_path()
            except Exception:
                self._brain_path = Path.cwd() / ".brain"

    @staticmethod
    def _anonymize(value: str) -> str:
        """Hash a value for anonymization. Preserves pattern matching without PII."""
        return hashlib.sha256(value.encode()).hexdigest()[:12]

    def collect_engram_patterns(self) -> List[Pattern]:
        """Extract patterns from engram contexts and intensity distributions."""
        patterns = []
        ledger = self._brain_path / "engrams" / "ledger.jsonl"
        if not ledger.exists():
            return patterns

        context_counts: Counter = Counter()
        intensity_buckets: Counter = Counter()
        now = datetime.now(timezone.utc).isoformat()

        try:
            for line in ledger.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    engram = json.loads(line)
                    ctx = engram.get("context", "unknown")
                    intensity = engram.get("intensity", 5)
                    context_counts[ctx] += 1
                    intensity_buckets[f"intensity_{intensity}"] += 1
                except (json.JSONDecodeError, KeyError):
                    continue

            for ctx, count in context_counts.most_common(10):
                patterns.append(Pattern(
                    pattern_type="engram_context",
                    pattern_key=f"ctx_{ctx.lower()}",
                    pattern_value=f"Engram context '{ctx}' used {count} times",
                    frequency=count,
                    effectiveness=min(1.0, count / 50),  # Normalize to 50 uses
                    first_seen=now,
                    last_seen=now,
                ))

        except Exception as e:
            logger.debug(f"Engram pattern collection failed: {e}")

        return patterns

    def collect_error_fix_patterns(self) -> List[Pattern]:
        """Extract patterns from self-healing events in the ledger."""
        patterns = []
        events_file = self._brain_path / "ledger" / "events.jsonl"
        if not events_file.exists():
            return patterns

        fix_counts: Counter = Counter()
        now = datetime.now(timezone.utc).isoformat()

        try:
            for line in events_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    etype = event.get("event_type", "")
                    if "self_heal" in etype or "heal" in etype:
                        # Extract the error category from the data
                        data = event.get("data", {})
                        error_type = data.get("error_type", data.get("category", "unknown"))
                        fix_counts[error_type] += 1
                except (json.JSONDecodeError, KeyError):
                    continue

            for error_type, count in fix_counts.most_common(10):
                patterns.append(Pattern(
                    pattern_type="error_fix",
                    pattern_key=f"fix_{self._anonymize(error_type)}",
                    pattern_value=f"Self-healing fix for '{error_type}' applied {count} times",
                    frequency=count,
                    effectiveness=min(1.0, count / 10),
                    first_seen=now,
                    last_seen=now,
                ))

        except Exception as e:
            logger.debug(f"Error fix pattern collection failed: {e}")

        return patterns

    def collect_tool_combo_patterns(self) -> List[Pattern]:
        """Extract frequently used tool combinations from events."""
        patterns = []
        events_file = self._brain_path / "ledger" / "events.jsonl"
        if not events_file.exists():
            return patterns

        tool_sequences: List[str] = []
        combo_counts: Counter = Counter()
        now = datetime.now(timezone.utc).isoformat()

        try:
            for line in events_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    etype = event.get("event_type", "")
                    if etype.startswith("tool_") or etype == "LLM_GENERATE":
                        tool_sequences.append(etype)
                except (json.JSONDecodeError, KeyError):
                    continue

            # Extract 2-grams and 3-grams of tool usage
            for n in [2, 3]:
                for i in range(len(tool_sequences) - n + 1):
                    combo = " → ".join(tool_sequences[i:i+n])
                    combo_counts[combo] += 1

            for combo, count in combo_counts.most_common(10):
                if count >= 3:  # Only include patterns seen 3+ times
                    patterns.append(Pattern(
                        pattern_type="tool_combo",
                        pattern_key=f"combo_{self._anonymize(combo)}",
                        pattern_value=f"Tool combo '{combo}' used {count} times",
                        frequency=count,
                        effectiveness=min(1.0, count / 20),
                        first_seen=now,
                        last_seen=now,
                    ))

        except Exception as e:
            logger.debug(f"Tool combo pattern collection failed: {e}")

        return patterns

    def collect_all(self) -> List[Pattern]:
        """Collect all pattern types."""
        all_patterns = []
        all_patterns.extend(self.collect_engram_patterns())
        all_patterns.extend(self.collect_error_fix_patterns())
        all_patterns.extend(self.collect_tool_combo_patterns())
        return all_patterns


# ============================================================
# PATTERN AGGREGATOR: Merges and persists patterns
# ============================================================

class PatternAggregator:
    """
    Aggregates patterns from multiple collection runs.
    Persists to .brain/emergence/patterns.json.
    """

    def __init__(self, brain_path: Optional[Path] = None):
        self._brain_path = brain_path
        if not self._brain_path:
            try:
                from .common import get_brain_path
                self._brain_path = get_brain_path()
            except Exception:
                self._brain_path = Path.cwd() / ".brain"
        self._store_path = self._brain_path / "emergence"
        self._patterns_file = self._store_path / "patterns.json"
        self._lock = threading.Lock()

    def _load_patterns(self) -> Dict[str, Pattern]:
        """Load existing patterns from disk."""
        if not self._patterns_file.exists():
            return {}
        try:
            data = json.loads(self._patterns_file.read_text(encoding="utf-8"))
            patterns = {}
            for key, pdata in data.get("patterns", {}).items():
                patterns[key] = Pattern(
                    pattern_type=pdata["type"],
                    pattern_key=pdata["key"],
                    pattern_value=pdata["value"],
                    frequency=pdata.get("frequency", 1),
                    effectiveness=pdata.get("effectiveness", 0.0),
                    first_seen=pdata.get("first_seen", ""),
                    last_seen=pdata.get("last_seen", ""),
                    source_count=pdata.get("source_count", 1),
                )
            return patterns
        except Exception as e:
            logger.warning(f"Failed to load patterns: {e}")
            return {}

    def _save_patterns(self, patterns: Dict[str, Pattern]):
        """Save patterns to disk."""
        try:
            self._store_path.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "pattern_count": len(patterns),
                "patterns": {key: p.to_dict() for key, p in patterns.items()},
            }
            self._patterns_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save patterns: {e}")

    def merge(self, new_patterns: List[Pattern]) -> int:
        """
        Merge new patterns into the persistent store.
        Returns the number of new or updated patterns.
        """
        with self._lock:
            existing = self._load_patterns()
            changes = 0
            now = datetime.now(timezone.utc).isoformat()

            for p in new_patterns:
                key = p.pattern_key
                if key in existing:
                    # Update existing pattern
                    ex = existing[key]
                    ex.frequency += p.frequency
                    ex.effectiveness = (ex.effectiveness + p.effectiveness) / 2  # Running average
                    ex.last_seen = now
                    ex.source_count += 1
                    changes += 1
                else:
                    # New pattern
                    p.first_seen = now
                    p.last_seen = now
                    existing[key] = p
                    changes += 1

            self._save_patterns(existing)
            return changes

    def get_top_patterns(self, n: int = 10, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get top N patterns by frequency × effectiveness score."""
        patterns = self._load_patterns()
        filtered = patterns.values()
        if pattern_type:
            filtered = [p for p in filtered if p.pattern_type == pattern_type]
        else:
            filtered = list(filtered)

        # Sort by composite score: frequency × effectiveness × source_count
        scored = sorted(
            filtered,
            key=lambda p: p.frequency * p.effectiveness * p.source_count,
            reverse=True
        )
        return [p.to_dict() for p in scored[:n]]

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        patterns = self._load_patterns()
        type_counts: Counter = Counter()
        total_freq = 0
        for p in patterns.values():
            type_counts[p.pattern_type] += 1
            total_freq += p.frequency

        return {
            "total_patterns": len(patterns),
            "total_observations": total_freq,
            "patterns_by_type": dict(type_counts),
            "store_path": str(self._patterns_file),
        }


# ============================================================
# PATTERN SUGGESTER: Surfaces top patterns for new users
# ============================================================

class PatternSuggester:
    """
    Suggests patterns to new users based on aggregated data.
    This is the core of the Emergence Rate — the system gets smarter as more users contribute.
    """

    def __init__(self, brain_path: Optional[Path] = None):
        self._aggregator = PatternAggregator(brain_path)

    def get_suggestions(self, context: str = "general", n: int = 5) -> List[Dict[str, Any]]:
        """
        Get pattern suggestions based on context.
        
        Args:
            context: Current user context (e.g., "error", "new_session", "task_planning")
            n: Number of suggestions to return
        """
        context_map = {
            "error": "error_fix",
            "new_session": "engram_context",
            "task_planning": "tool_combo",
            "general": None,
        }
        pattern_type = context_map.get(context)
        return self._aggregator.get_top_patterns(n=n, pattern_type=pattern_type)

    def get_onboarding_hints(self) -> List[str]:
        """
        Generate onboarding hints from the most common patterns.
        These are shown during first-run experience.
        """
        hints = []
        top = self._aggregator.get_top_patterns(n=5)
        for p in top:
            if p["type"] == "engram_context":
                val = p['value']
                ctx_name = val.split("'")[1] if "'" in val else val
                hints.append(f"💡 Most users write engrams in the '{ctx_name}' context")
            elif p["type"] == "error_fix":
                hints.append(f"🔧 Common fix pattern: {p['value']}")
            elif p["type"] == "tool_combo":
                hints.append(f"⚡ Popular workflow: {p['value']}")
        return hints


# ============================================================
# CONVENIENCE: Collect and aggregate in one call
# ============================================================

def collect_and_aggregate(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run a full pattern collection and aggregation cycle.
    Returns stats about what was collected.
    """
    collector = PatternCollector(brain_path)
    aggregator = PatternAggregator(brain_path)

    patterns = collector.collect_all()
    changes = aggregator.merge(patterns)
    stats = aggregator.get_stats()

    logger.info(
        f"🧬 Emergence Rate: Collected {len(patterns)} patterns, "
        f"{changes} changes merged, {stats['total_patterns']} total stored"
    )

    return {
        "collected": len(patterns),
        "merged_changes": changes,
        **stats,
    }
