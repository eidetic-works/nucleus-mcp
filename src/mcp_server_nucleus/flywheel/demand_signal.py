"""Demand Signal Registry — the third-state model applied to "does anyone want
this", not "did we build it correctly".

CSR (csr.py) answers: was a claim about the CODE proven, refuted, or never
checked? This module answers a different question about the same artifact:
was there ever real, external evidence that someone outside this repo wanted
it? The two are orthogonal on purpose — CSR being green says nothing about
demand, and this being green says nothing about correctness. Session
2026-08-16/17/18 found both failure modes in the same corpus: `brain_patterns`
was referenced in three separate strategy docs and built in none (a demand
claim with no code behind it); a ~200-file self-congratulatory doc pile
described dozens of "shipped" features with zero external evidence any of
them were ever used (working code with no demand behind it, or in several
sampled cases, no code at all).

THE THIRD STATE, same shape as csr.py / the receipt gate / the Oracle's own
covenant:
    CONFIRMED  — real, external, checkable evidence exists (an install count,
                 a GitHub star, a support ticket, an operator's direct
                 first-party assertion about their own product).
    NONE       — checked, and no such evidence was found.
    UNKNOWN    — never checked. This is the DEFAULT, deliberately, matching
                 CSR's "absence of a claim is not proof" discipline. A ticket
                 that never asked about demand is not evidence demand exists,
                 the same way an untested claim is not evidence it's true.

UNKNOWN is not a failure state to be ashamed of — most artifacts in a fast-
moving corpus will legitimately sit at UNKNOWN, because nobody has looked yet.
What this registry prevents is the silent slide from UNKNOWN to "assumed
CONFIRMED because it shipped" — the exact failure this session spent hours
finding evidence of.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .csr import _ensure_flywheel_dir

_VALID_VERDICTS = frozenset({"confirmed", "none", "unknown"})

# First-party (the operator asserting a fact about their own product) is a
# different, stronger evidence class than an agent's grep/API-based inference
# -- 2026-08-18: the operator overrode a measured 202-install reading with a
# direct "250+ installs/users, never question again". That is not a source an
# agent can independently verify, and it should not need to be re-verified --
# it is authoritative on its face the way a user's report of their own lived
# experience is, in qualitative research. Recorded as its own source type so
# it is never confused with a scraped/measured number, but also never
# re-litigated the way an agent-inferred CONFIRMED should be.
_VALID_SOURCES = frozenset({
    "operator_assertion",   # first-party, authoritative, not independently reverified
    "analytics",             # GA4, install counts, usage telemetry
    "external_platform",     # GitHub stars/forks/issues, package registry downloads
    "direct_feedback",       # support ticket, user message, review, forum post about it
    "agent_search",          # grep/find across the corpus found no external trace
})


def _demand_ledger_path(brain_path: Path) -> Path:
    return Path(brain_path) / "flywheel" / "demand_signal.jsonl"


def record_signal(
    brain_path: Path,
    *,
    artifact: str,
    verdict: str,
    source: str,
    evidence: str = "",
    phase: str = "unknown",
) -> Dict[str, Any]:
    """Append one demand-signal record. Never raises -- a logging failure
    here must not cost the caller's actual work, same discipline as
    csr.py's _append_survived_log.

    artifact: what this is about (a feature name, a doc claim, a ticket id) --
        free text, not a foreign key into anything, so this stays usable even
        for artifacts that only exist as a sentence in an old strategy doc.
    verdict: one of CONFIRMED / NONE / UNKNOWN (case-insensitive on input,
        stored lowercase).
    source: one of _VALID_SOURCES -- which evidence class this verdict rests
        on. Required even for UNKNOWN (source describes what was tried, even
        if it found nothing) so a future reader can tell "we searched and
        found nothing" apart from "we plan to search but haven't".
    evidence: the actual supporting text/number/quote/path. Required for
        CONFIRMED and NONE (a verdict with no evidence is not a verdict);
        optional for UNKNOWN.
    """
    verdict_norm = (verdict or "").strip().lower()
    if verdict_norm not in _VALID_VERDICTS:
        raise ValueError(
            f"verdict must be one of {sorted(_VALID_VERDICTS)}, got {verdict!r}"
        )
    source_norm = (source or "").strip().lower()
    if source_norm not in _VALID_SOURCES:
        raise ValueError(
            f"source must be one of {sorted(_VALID_SOURCES)}, got {source!r}"
        )
    if verdict_norm in ("confirmed", "none") and not evidence.strip():
        raise ValueError(
            f"verdict={verdict_norm!r} requires non-empty evidence -- "
            f"a verdict with no supporting text is not a verdict, it's a guess"
        )

    rec = {
        "artifact": artifact,
        "verdict": verdict_norm,
        "source": source_norm,
        "evidence": evidence,
        "phase": phase,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        fw_dir = _ensure_flywheel_dir(brain_path)
        with (fw_dir / "demand_signal.jsonl").open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass  # never let the log cost the caller's actual work
    return rec


def read_signal_ledger(brain_path: Path) -> List[Dict[str, Any]]:
    """Read every recorded demand-signal entry, oldest first. Returns []
    if the ledger doesn't exist yet -- an empty ledger is a real, honest
    state (nothing has been checked), not an error."""
    p = _demand_ledger_path(brain_path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().strip().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a corrupt line is skipped, not fatal to the whole read
    return out


def latest_verdict(brain_path: Path, artifact: str) -> Optional[Dict[str, Any]]:
    """The most recent record for a given artifact name, or None if it has
    never been checked at all (the true UNKNOWN state -- distinct from a
    recorded verdict of 'unknown', which means someone explicitly logged
    'checked, could not determine')."""
    matches = [r for r in read_signal_ledger(brain_path) if r["artifact"] == artifact]
    return matches[-1] if matches else None


def summarize(brain_path: Path) -> Dict[str, Any]:
    """Counts by verdict across the whole ledger, for a quick health read --
    the demand-signal equivalent of csr.json's ratio."""
    records = read_signal_ledger(brain_path)
    counts = {"confirmed": 0, "none": 0, "unknown": 0}
    for r in records:
        v = r.get("verdict")
        if v in counts:
            counts[v] += 1
    return {
        "total_artifacts_checked": len(records),
        "confirmed": counts["confirmed"],
        "none": counts["none"],
        "unknown": counts["unknown"],
        "last_updated": records[-1]["ts"] if records else None,
    }
