"""Trigger — decide whether there is enough NEW work to be worth dreaming over.

A discovery pass costs an agent's attention, so something has to decide when to
run one. The obvious answer is a schedule, and the obvious answer is wrong.

A nightly pass over a day when nothing happened reads the same corpus it read
yesterday, proposes the same things, and teaches the loop to produce output
whether or not there was anything to find. A pass that runs after real work has
accumulated has something new to read by construction. So the gate is the work,
not the clock: *has enough happened since last time?*

This matters more than it sounds. A calendar trigger cannot tell a busy week
from an idle one, so it fires identically for both -- which makes its output
uninformative in exactly the case you most want to trust it. Worse, it
manufactures the appearance of a working flywheel out of an empty corpus.

The watermark is the timestamp of the last pass. "New" means a session with
activity after it. Nothing here consults the current time to decide whether to
fire; the clock is recorded so a human can read the log, and is never an input
to the decision.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .prevalence import _transcripts, default_roots

STATE_FILE = "discovery_trigger.json"
DEFAULT_MIN_NEW_SESSIONS = 20


@dataclass
class Decision:
    """Whether to run a pass, and the measurement behind it."""

    should_run: bool
    reason: str
    new_sessions: int = 0
    threshold: int = DEFAULT_MIN_NEW_SESSIONS
    sessions_total: int = 0
    watermark: Optional[float] = None
    examples: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _state_path(brain_path: Path) -> Path:
    return Path(brain_path) / STATE_FILE


def read_state(brain_path: Path) -> Dict[str, Any]:
    path = _state_path(brain_path)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def record_pass(brain_path: Path, watermark: Optional[float] = None,
                proposals_made: int = 0) -> Dict[str, Any]:
    """Mark a pass as done, advancing the watermark.

    Call this after a pass completes, whatever it found. A pass that found
    nothing still consumed the activity it read, and not advancing would make
    the next call re-read it and reach the same conclusion forever.
    """
    state = {
        "last_pass_at": datetime.now(timezone.utc).isoformat(),
        "watermark": watermark if watermark is not None else datetime.now(timezone.utc).timestamp(),
        "proposals_made": proposals_made,
    }
    path = _state_path(brain_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))
    return state


def should_run(
    brain_path: Path,
    roots: Optional[Sequence[Path]] = None,
    min_new_sessions: int = DEFAULT_MIN_NEW_SESSIONS,
) -> Decision:
    """Has enough new work accumulated since the last pass?

    Note what is absent: no comparison of the current time against the last
    pass. Waiting longer never makes this return True. Only sessions do.
    """
    used = list(roots if roots is not None else default_roots())
    files = _transcripts(used)
    state = read_state(brain_path)
    watermark = state.get("watermark")

    if not files:
        return Decision(
            should_run=False,
            reason=(
                "No transcripts were found under the given roots, so there is "
                "nothing to read. This is not 'no new activity' -- it is no "
                "visible corpus at all."
            ),
            threshold=min_new_sessions,
            watermark=watermark,
        )

    if watermark is None:
        return Decision(
            should_run=True,
            reason=(
                f"No pass has ever run, so the whole corpus of "
                f"{len(files)} session(s) is unread accumulated activity."
            ),
            new_sessions=len(files),
            threshold=min_new_sessions,
            sessions_total=len(files),
        )

    try:
        watermark = float(watermark)
    except (TypeError, ValueError):
        return Decision(
            should_run=False,
            reason=(
                f"The recorded watermark {watermark!r} is not a timestamp, so "
                f"'new since last pass' has no meaning. Refusing rather than "
                f"treating every session as new."
            ),
            threshold=min_new_sessions,
            sessions_total=len(files),
        )

    fresh = []
    for path in files:
        try:
            if path.stat().st_mtime > watermark:
                fresh.append(path.stem)
        except OSError:
            continue

    if len(fresh) >= min_new_sessions:
        return Decision(
            should_run=True,
            reason=(
                f"{len(fresh)} session(s) have had activity since the last "
                f"pass, at or above the floor of {min_new_sessions}."
            ),
            new_sessions=len(fresh),
            threshold=min_new_sessions,
            sessions_total=len(files),
            watermark=watermark,
            examples=fresh[:5],
        )

    return Decision(
        should_run=False,
        reason=(
            f"Only {len(fresh)} session(s) have had activity since the last "
            f"pass, below the floor of {min_new_sessions}. Time passing does "
            f"not change this; work does."
        ),
        new_sessions=len(fresh),
        threshold=min_new_sessions,
        sessions_total=len(files),
        watermark=watermark,
        examples=fresh[:5],
    )
