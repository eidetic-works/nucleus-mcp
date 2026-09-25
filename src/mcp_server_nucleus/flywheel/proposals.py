"""Proposed memory changes, and the human decision that gates them.

The last third of dreaming. A batch pass observes a pattern, counts how many
sessions it appears in, cites them — and then stops, because the talk's loop
ends with a person accepting or rejecting the change, not with an agent writing
to memory on its own authority.

THE CENTRAL REFUSAL: A PROPOSAL WHOSE EVIDENCE IS INSUFFICIENT CANNOT BE
ACCEPTED. Not accepted-with-a-warning. Refused. A capped scan produced a number
over a set it could not fully see, and approving a permanent memory on that
basis is exactly how a partial reading becomes an organisational fact. The cost
of getting this wrong compounds: a wrong org-wide memory is read by every agent
afterwards, which is the disaster the talk names outright — "if something was
incorrect there, that would scale to all of your agents."

Weak evidence is still a fine reason to REJECT. The gate blocks acceptance, not
progress.

Three supporting rules, each reusing a shape that already works in this repo:
  * accept is the only path to memory — two-phase, like goal item closure, where
    the agent may claim and only the operator closes;
  * a rejection is recorded, never deleted — append-only, like `store.rollback`;
    a queue that forgets its rejections re-proposes them forever;
  * accepting twice is refused — a second write that looks like progress and is
    not, the same class as a `version` field that is always 1.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_FILE = "proposals.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(brain_path: Path) -> Path:
    d = Path(brain_path) / "flywheel"
    d.mkdir(parents=True, exist_ok=True)
    return d / _FILE


def _load(brain_path: Path) -> List[Dict[str, Any]]:
    f = _path(brain_path)
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _save(brain_path: Path, rows: List[Dict[str, Any]]) -> None:
    _path(brain_path).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )


def propose(brain_path: Path, proposed_memory: str, evidence: Any,
            pattern: str = "", precision_required: bool = False) -> Dict[str, Any]:
    """Record a proposed memory change. It touches memory only if accepted."""
    if not (proposed_memory or "").strip():
        raise ValueError("a proposal needs the memory it proposes to write")
    ev = evidence.as_dict() if hasattr(evidence, "as_dict") else dict(evidence or {})
    ev["summary"] = evidence.summary() if hasattr(evidence, "summary") else ev.get("summary", "")
    if precision_required:
        ev["precision_required"] = True
    row = {
        "proposal_id": f"prop_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "at": _now(),
        "pattern": pattern or ev.get("pattern", ""),
        "proposed_memory": proposed_memory.strip(),
        "evidence": ev,
        "status": "pending",
        "decided_at": None,
        "decided_by": None,
        "reason": None,
    }
    rows = _load(brain_path)
    rows.append(row)
    _save(brain_path, rows)
    return row



MIN_PRECISION = 0.5
MIN_LABELS = 5


def wilson_lower(positive: int, total: int, z: float = 1.96) -> float:
    """Lower bound of the 95% Wilson interval for ``positive`` of ``total``.

    Precision from a small sample is a range, not a number: 3 of 5 is not 60%,
    it is anywhere from about 23% up. Gating on the lower bound is what stops
    a lucky handful of labels from clearing a pattern that mostly misfires.
    """
    if total <= 0:
        return 0.0
    ph = positive / total
    denom = 1 + z * z / total
    centre = ph + z * z / (2 * total)
    margin = z * ((ph * (1 - ph) / total + z * z / (4 * total * total)) ** 0.5)
    return max(0.0, (centre - margin) / denom)


def label(brain_path: Path, proposal_id: str, labels: List[Any],
          by: str = "labeler") -> Dict[str, Any]:
    """Record whether each sampled match actually showed the failure.

    ``labels`` is one entry per sampled excerpt, in order: True (it does),
    False (it does not) or None (cannot tell). None counts AGAINST the pattern,
    because an excerpt nobody could read as the failure is not evidence of it.
    The labeller supplies judgements; it never supplies the count.
    """
    rows = _load(brain_path)
    row = _find(rows, proposal_id)
    if row.get("status") != "pending":
        raise ValueError(f"proposal {proposal_id} is already {row.get('status')}")
    ev = row.get("evidence") or {}
    sample = ev.get("sample") or []
    if not sample:
        raise ValueError(f"proposal {proposal_id} has no recorded sample to label")
    if len(labels) != len(sample):
        raise ValueError(
            f"got {len(labels)} label(s) for {len(sample)} sampled excerpt(s); labelling "
            f"a different set than the one recorded proves nothing"
        )
    if any(x not in (True, False, None) for x in labels):
        raise ValueError("labels must each be true, false, or null (cannot tell)")
    if len(labels) < MIN_LABELS:
        raise ValueError(f"need at least {MIN_LABELS} labels; got {len(labels)}")

    positive = sum(1 for x in labels if x is True)
    unclear = sum(1 for x in labels if x is None)
    for entry, lab in zip(sample, labels):
        entry["label"] = lab
    ev["precision"] = {
        "labeled": len(labels),
        "positive": positive,
        "unclear": unclear,
        "rate": positive / len(labels),
        "wilson_lower": wilson_lower(positive, len(labels)),
        "labeled_by": by,
        "at": _now(),
    }
    row["evidence"] = ev
    _save(brain_path, rows)
    return row


def all_proposals(brain_path: Path) -> List[Dict[str, Any]]:
    return _load(brain_path)


def pending(brain_path: Path) -> List[Dict[str, Any]]:
    return [r for r in _load(brain_path) if r.get("status") == "pending"]


def _find(rows: List[Dict[str, Any]], proposal_id: str) -> Dict[str, Any]:
    for r in rows:
        if r.get("proposal_id") == proposal_id:
            return r
    raise ValueError(f"no proposal with id {proposal_id!r}")


def accept(brain_path: Path, proposal_id: str, by: str = "operator",
           min_precision: float = MIN_PRECISION) -> Dict[str, Any]:
    """Approve a proposal and write it to memory. The ONLY path to memory."""
    rows = _load(brain_path)
    row = _find(rows, proposal_id)

    if row.get("status") != "pending":
        raise ValueError(
            f"proposal {proposal_id} is already {row.get('status')}. Re-accepting "
            "would write the memory a second time while looking like progress."
        )

    ev = row.get("evidence") or {}
    if not ev.get("complete", False):
        raise ValueError(
            f"refusing to accept {proposal_id}: its evidence is INSUFFICIENT. "
            f"{ev.get('insufficient_reason') or 'the scan was not complete.'} "
            "A memory accepted on a count over a set nobody could fully see "
            "becomes a fact every later agent reads. Re-run the scan without a "
            "cap, or reject this."
        )

    if ev.get("precision_required"):
        prec = ev.get("precision")
        if not prec:
            raise ValueError(
                f"refusing to accept {proposal_id}: its PRECISION was never measured. "
                f"A count of matches is a count of words co-occurring, not of the "
                f"failure; measured 2026-09-20, a 79-session count was made of "
                f"ordinary sentences. Sample it (nucleus dream --sample) and label it."
            )
        if prec["wilson_lower"] < min_precision:
            raise ValueError(
                f"refusing to accept {proposal_id}: only {prec['positive']} of "
                f"{prec['labeled']} sampled matches showed the failure (lower bound "
                f"{prec['wilson_lower']:.0%}, needs {min_precision:.0%}). The pattern "
                f"mostly matches something else."
            )

    # Written through the same store whose versioning and compare-and-swap gate
    # this goal made real, so an accepted memory is versioned like any other.
    from nucleus_wedge.store import Store

    value = row["proposed_memory"]
    summary = ev.get("summary")
    if summary:
        value = f"{value}\n\nEvidence: {summary}"

    Store(brain_path=brain_path).append(
        value=value,
        kind="dreaming",
        tags=["dreaming", "accepted"],
        source_agent=f"dreaming:accepted-by-{by}",
    )

    row["status"] = "accepted"
    row["decided_at"] = _now()
    row["decided_by"] = by
    _save(brain_path, rows)
    return row


def reject(brain_path: Path, proposal_id: str, by: str = "operator",
           reason: str = "") -> Dict[str, Any]:
    """Decline a proposal. Recorded, never deleted."""
    if not (reason or "").strip():
        raise ValueError(
            "a rejection needs a reason. An unexplained rejection tells the next "
            "pass nothing, so it proposes the same thing again."
        )
    rows = _load(brain_path)
    row = _find(rows, proposal_id)
    if row.get("status") != "pending":
        raise ValueError(f"proposal {proposal_id} is already {row.get('status')}.")
    row["status"] = "rejected"
    row["decided_at"] = _now()
    row["decided_by"] = by
    row["reason"] = reason.strip()
    _save(brain_path, rows)
    return row
