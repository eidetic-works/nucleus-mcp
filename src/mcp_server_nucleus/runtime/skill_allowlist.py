"""Allowlist gate for autonomous skill install/apply.

The blind frequency-scorer mis-ranks conversational filler as high-value
(empirically, on real operator data: "what do you recommend" scored 0.65,
"but what about tb work" 0.65). Until a trustworthy success-oracle exists,
autonomous INSTALL is gated on an operator-approved allowlist of recurring-
macro patterns — NOT on the raw score. Everything else is still registered
and surfaced (evening card), but never auto-installed/auto-applied.

This is the honest reconciliation of "run without me" with the unsolved
oracle problem: trust a tiny human-approved allowlist, not a blind scorer.
As the success-signal proves out, the allowlist widens — earned, not assumed.

Allowlist file: <brain>/skills/allowlist.json
    {
      "version": 1,
      "patterns": [
        {"id": "relays", "match": "check relays", "note": "recurring ops macro"}
      ]
    }
A pattern matches when its (case-insensitive) "match" substring appears in the
cluster's domain or any of its intents.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nucleus.skill_allowlist")

ALLOWLIST_FILE = "allowlist.json"
# A match auto-installs into ~/.claude/skills, so guard against over-broad
# needles substring-matching unintended clusters.
MIN_NEEDLE_LEN = 4


def allowlist_path(brain_path: Path) -> Path:
    return brain_path / "skills" / ALLOWLIST_FILE


def load_allowlist(brain_path: Path) -> List[Dict]:
    """Load allowlist patterns. Missing/unreadable file => empty list, which
    means surface-only (no autonomous install). Fails safe, logs why."""
    p = allowlist_path(brain_path)
    if not p.exists():
        logger.info(
            "No skill allowlist at %s — autonomous install disabled (surface-only).", p
        )
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Allowlist unreadable (%s): %s — treating as empty (surface-only).", p, e
        )
        return []
    patterns = data.get("patterns", [])
    if not isinstance(patterns, list):
        logger.warning("Allowlist 'patterns' is not a list — treating as empty.")
        return []
    return patterns


def match_allowlist(cluster: Dict, patterns: List[Dict]) -> Optional[str]:
    """Return the matching pattern id if the cluster matches any allowlist
    pattern, else None.

    The needle is tested (case-insensitive substring) against each field
    INDIVIDUALLY — the domain and each intent separately — never a concatenated
    haystack, so a needle cannot match across a domain/intent boundary. Patterns
    with a needle shorter than MIN_NEEDLE_LEN or a missing id are skipped (and
    logged): both would risk false-positive auto-install."""
    if not patterns:
        return None
    fields = [str(cluster.get("domain", "")).lower()]
    fields += [str(i).lower() for i in cluster.get("intents", [])]
    for pat in patterns:
        needle = str(pat.get("match", "")).strip().lower()
        pid = str(pat.get("id", "")).strip()
        if len(needle) < MIN_NEEDLE_LEN:
            logger.warning(
                "allowlist pattern needle %r too short (<%d chars) — skipped.",
                needle, MIN_NEEDLE_LEN,
            )
            continue
        if not pid:
            logger.warning("allowlist pattern (match=%r) has no id — skipped.", needle)
            continue
        if any(needle in f for f in fields):
            return pid
    return None
