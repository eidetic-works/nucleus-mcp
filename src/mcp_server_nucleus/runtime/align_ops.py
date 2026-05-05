"""
ALIGN — Human correction frontier.

Users correct AI output. Each correction:
1. Writes a verdict to human_verdicts.jsonl
2. Records an ALIGN Delta (gap between what AI did and what was right)
3. Creates a DPO preference pair (for training)
4. Emits align_reviewed event (feeds substrate)

This closes the loop: GROUND verifies → ALIGN corrects → COMPOUND learns.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .common import get_brain_path, logger


def record_correction(context: str, correction: str,
                      expected: str = "", severity: str = "medium",
                      extra_metadata: Optional[Dict[str, Any]] = None
                      ) -> Dict[str, Any]:
    """Record a human correction of AI output.

    Args:
        context: What the AI produced (the wrong output)
        correction: What it should have been (the right output)
        expected: Optional — what was originally asked for
        severity: low/medium/high — how bad the mistake was
        extra_metadata: Optional dict merged into the DPO pair's metadata
            and the verdict record. Used by callers that want to tag a
            correction with mode/sovereignty/surface/source — enables
            retroactive corpus filtering at training time without
            changing schema. Caller-provided keys win over defaults
            (verdict_id, severity).
    """
    brain = get_brain_path()
    verdict_id = f"v-{int(datetime.now().timestamp())}-{str(uuid.uuid4())[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    extra_metadata = dict(extra_metadata or {})

    # 1. Write verdict
    verdict = {
        "verdict_id": verdict_id,
        "verdict": "corrected",
        "timestamp": timestamp,
        "context": context[:500],
        "correction": correction[:500],
        "expected": expected[:500] if expected else "",
        "severity": severity,
    }
    if extra_metadata:
        verdict["metadata"] = extra_metadata

    verdicts_path = brain / "driver" / "human_verdicts.jsonl"
    verdicts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(verdicts_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(verdict, ensure_ascii=False) + "\n")

    # 2. Record ALIGN Delta
    delta_id = None
    try:
        from .delta_ops import record_delta
        delta_id = record_delta(
            frontier="ALIGN",
            expected_source="user",
            expected_intent=expected or f"Correct output for: {context[:100]}",
            actual_source="ai",
            actual_outcome=context[:200],
            insight=correction[:200],
            corrections=correction[:200],
        )
    except Exception as e:
        logger.warning(f"ALIGN delta recording failed: {e}")

    # 3. Create DPO preference pair
    pref_id = None
    try:
        from .archive_pipeline import ArchivePipeline
        archive = ArchivePipeline()
        prompt = expected if expected else f"Task context: {context[:200]}"
        pref_metadata = {"verdict_id": verdict_id, "severity": severity}
        # extra_metadata wins on collision (caller knows their context better
        # than this default — e.g., they may want to override severity).
        pref_metadata.update(extra_metadata)
        pref = archive.record_preference(
            prompt=prompt,
            chosen=correction,
            rejected=context,
            source="align_correction",
            metadata=pref_metadata,
        )
        if pref:
            pref_id = pref.get("pref_id")
    except Exception as e:
        logger.warning(f"ALIGN DPO recording failed: {e}")

    # 4. Emit align_reviewed event
    try:
        from .event_ops import _emit_event
        _emit_event("align_reviewed", "nucleus_align", {
            "verdict_id": verdict_id,
            "verdict": "corrected",
            "severity": severity,
            "delta_id": delta_id,
            "pref_id": pref_id,
        })
    except Exception:
        pass

    # Coord-event capture (§5.3 completion): emit correction event for router corpus.
    # Best-effort; never breaks the alignment flow. correction events are the
    # high-signal training data — wait-and-see means corpus stays half-blind
    # for §5.5 validation gates.
    try:
        from . import coord_events as _ce
        _ce.emit(
            event_type="correction",
            agent="nucleus_align",
            session_id=verdict_id,
            context_summary=f"correction: {context[:120]}",
            chosen_option=correction[:120],
            reasoning_summary=f"severity={severity} pref_id={pref_id}",
            tags=[severity] if severity else [],
        )
    except Exception:
        pass

    return {
        "verdict_id": verdict_id,
        "verdict": "corrected",
        "delta_id": delta_id,
        "pref_id": pref_id,
        "message": f"Correction recorded. Delta: {delta_id}, DPO: {pref_id}",
    }


def record_rejection(context: str, reason: str = "",
                     severity: str = "medium",
                     extra_metadata: Optional[Dict[str, Any]] = None
                     ) -> Dict[str, Any]:
    """Record a thumbs-down WITHOUT a correction text.

    Verdict-only negative signal — no DPO pair gets written. Use when
    the user wants to flag "this was bad" but doesn't have time or a
    better answer. Distinguishes intent ("model was wrong") from data
    ("here's what it should have said") so we don't pollute the DPO
    archive with low-quality chosen text just to capture a thumbs-down.

    Args:
        context: What the AI produced (the rejected output)
        reason: Optional one-line reason for rejection
        severity: low/medium/high
        extra_metadata: Optional dict merged into the verdict record
            (mode/sovereignty/surface tagging — same shape as
            record_correction's extra_metadata).
    """
    brain = get_brain_path()
    verdict_id = f"v-{int(datetime.now().timestamp())}-{str(uuid.uuid4())[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    extra_metadata = dict(extra_metadata or {})

    verdict = {
        "verdict_id": verdict_id,
        "verdict": "rejected",
        "timestamp": timestamp,
        "context": context[:500],
        "reason": reason[:200] if reason else "",
        "severity": severity,
    }
    if extra_metadata:
        verdict["metadata"] = extra_metadata

    verdicts_path = brain / "driver" / "human_verdicts.jsonl"
    verdicts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(verdicts_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(verdict, ensure_ascii=False) + "\n")

    try:
        from .event_ops import _emit_event
        _emit_event("align_reviewed", "nucleus_align", {
            "verdict_id": verdict_id,
            "verdict": "rejected",
            "severity": severity,
        })
    except Exception:
        pass

    return {
        "verdict_id": verdict_id,
        "verdict": "rejected",
        "message": "Rejection recorded (verdict-only, no DPO pair).",
    }


def record_approval(context: str, notes: str = "") -> Dict[str, Any]:
    """Record approval of AI output (positive signal)."""
    brain = get_brain_path()
    verdict_id = f"v-{int(datetime.now().timestamp())}-{str(uuid.uuid4())[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    verdict = {
        "verdict_id": verdict_id,
        "verdict": "accepted",
        "timestamp": timestamp,
        "context": context[:500],
        "notes": notes[:200] if notes else "",
    }

    verdicts_path = brain / "driver" / "human_verdicts.jsonl"
    verdicts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(verdicts_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(verdict, ensure_ascii=False) + "\n")

    # Emit event
    try:
        from .event_ops import _emit_event
        _emit_event("align_reviewed", "nucleus_align", {
            "verdict_id": verdict_id,
            "verdict": "accepted",
        })
    except Exception:
        pass

    # Coord-event capture (§5.3 completion): emit founder_verdict event.
    # Approval is the founder's positive verdict on AI output. Pairs with
    # correction events to form the chosen/rejected signal for router training.
    try:
        from . import coord_events as _ce
        _ce.emit(
            event_type="founder_verdict",
            agent="nucleus_align",
            session_id=verdict_id,
            context_summary=f"approval: {context[:120]}",
            chosen_option="accepted",
            reasoning_summary=notes[:120] if notes else "",
            tags=["approval"],
        )
    except Exception:
        pass

    return {
        "verdict_id": verdict_id,
        "verdict": "accepted",
        "message": "Approval recorded.",
    }


def get_align_stats() -> Dict[str, Any]:
    """Get alignment statistics from human verdicts."""
    brain = get_brain_path()
    verdicts_path = brain / "driver" / "human_verdicts.jsonl"

    if not verdicts_path.exists():
        return {"total": 0, "message": "No alignment data yet. Use correct/approve to start."}

    try:
        from .hardening import safe_read_jsonl
        verdicts = safe_read_jsonl(verdicts_path)
    except Exception:
        verdicts = []
        with open(verdicts_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        verdicts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    if not verdicts:
        return {"total": 0, "message": "No alignment data yet."}

    corrected = sum(1 for v in verdicts if v.get("verdict") == "corrected")
    accepted = sum(1 for v in verdicts if v.get("verdict") == "accepted")
    total = corrected + accepted

    return {
        "total": total,
        "corrected": corrected,
        "accepted": accepted,
        "approval_rate": round(accepted / total, 3) if total > 0 else 0,
        "severity_breakdown": {
            s: sum(1 for v in verdicts if v.get("severity") == s)
            for s in ["low", "medium", "high"]
        },
    }
