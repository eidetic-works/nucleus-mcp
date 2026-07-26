"""Claim receipts — CLAIMED vs PROVEN, with a real third state.

Every check in this substrate answers one question: *someone asserted X; is X
true?* A receipt records that question and its answer in a form that
accumulates, because the corpus is worth more than any single verdict.

WHY THREE STATES. Ten incidents on 2026-07-26 across three independent agent
sessions were all the same shape — a value that is neither pass nor fail,
coerced into pass:

    SKIPPED      counted as PASSED     (build_runner verify gate)
    UNPARSEABLE  counted as REJECTED   (plan_review_loop heuristic fallback)
    registered   counted as running    (cron dead 102 days; executor daemon
                                        polled ~4,100 times, claimed nothing)
    committed    counted as deployed   (worker running a non-git-synced script)
    stashed      counted as absent     (57 files eaten by `git stash -u`,
                                        `git status` clean, invisible 10 days)
    claimed      counted as proven     (agent reported 113 files/2085 tests;
                                        actual 126/2297)

None were caught by tests, CI, linters, type checkers, or the tool's own
report. All were caught by re-deriving the fact from a primitive. Binary
pass/fail has no room for "I could not determine this", so it rounds to green.
:class:`Verdict.INSUFFICIENT` is that missing room, and it is load-bearing:
it must never be silently folded into either neighbour.

WHY THE FIELDS ARE WIDER THAN v1 NEEDS. A receipt that stores only a boolean
is a verdict; a receipt that stores claim type, primitive, both values, and
the asserting source is a *corpus*. From the corpus you can later derive what
no single check can: which claim types lie most often, which agents
over-report and by how much, the base rate of false-green per language and
framework. Capturing that costs nothing now and cannot be reconstructed
retroactively — hence the shape lands before the consumers do.

Stdlib only. Append-only JSONL. Never raises: a receipt-store failure must
never break the check it is recording.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nucleus.receipt")

RECEIPTS_FILENAME = "receipts.jsonl"


class Verdict(str, Enum):
    """Outcome of re-deriving a claim from a primitive.

    INSUFFICIENT is NOT a soft failure and NOT a soft pass. It means the check
    did not run, could not run, or produced no signal — so nothing was learned.
    Collapsing it into either neighbour is the exact defect this module exists
    to prevent.
    """

    PROVEN = "PROVEN"
    REFUTED = "REFUTED"
    INSUFFICIENT = "INSUFFICIENT"


class ClaimType(str, Enum):
    """What kind of assertion is being checked.

    Deliberately coarse and open — a free-form ``other`` beats forcing a wrong
    label, since the corpus is only useful if the labels are honest.
    """

    TESTS_PASS = "tests_pass"
    FILES_CHANGED = "files_changed"
    JOB_RAN = "job_ran"
    CODE_EXECUTED = "code_executed"
    PLAN_APPROVED = "plan_approved"
    DEPLOYED = "deployed"
    BUILD_VERIFIED = "build_verified"
    OTHER = "other"


@dataclass
class Receipt:
    """One claim, one re-derivation, one verdict.

    ``claimed`` and ``observed`` are free-form strings on purpose: the delta
    between them is the product, and forcing a schema on it now would discard
    exactly the detail that makes the corpus useful later.
    """

    claim_type: str
    claim: str
    verdict: str
    primitive: str
    claimed: str = ""
    observed: str = ""
    source: str = "unknown"
    evidence: str = ""
    reason: str = ""
    tags: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.verdict, Verdict):
            self.verdict = self.verdict.value
        if isinstance(self.claim_type, ClaimType):
            self.claim_type = self.claim_type.value

    @property
    def agrees(self) -> bool:
        """True iff claim and observation match. Only meaningful when PROVEN."""
        return self.verdict == Verdict.PROVEN.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _receipts_path(brain_path: Optional[Path] = None) -> Path:
    """Resolve the receipts JSONL path, creating the directory if needed."""
    if brain_path is None:
        try:
            from .common import get_brain_path

            resolved = get_brain_path()
            brain_path = Path(resolved) if resolved else Path.cwd() / ".brain"
        except Exception:  # noqa: BLE001 — never let path resolution break a check
            brain_path = Path.cwd() / ".brain"
    d = Path(brain_path) / "receipts"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug("receipts dir create failed: %s", exc)
    return d / RECEIPTS_FILENAME


def record(receipt: Receipt, brain_path: Optional[Path] = None) -> bool:
    """Append a receipt. Returns True on success; never raises.

    A failure to record must never fail the check being recorded — an
    observability layer that can break the thing it observes is worse than
    no observability layer.
    """
    try:
        path = _receipts_path(brain_path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("receipt not recorded (%s): %s", receipt.claim_type, exc)
        return False


def read_all(brain_path: Optional[Path] = None) -> List[Receipt]:
    """Read every receipt. Malformed lines are skipped, never fatal."""
    path = _receipts_path(brain_path)
    out: List[Receipt] = []
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Receipt(**json.loads(line)))
            except Exception:  # noqa: BLE001 — one bad row must not lose the corpus
                continue
    except Exception as exc:  # noqa: BLE001
        logger.warning("receipts read failed: %s", exc)
    return out


def summarize(receipts: Optional[List[Receipt]] = None,
              brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Aggregate receipts into the priors the corpus exists to produce.

    Reports per-verdict totals, a disagreement rate per claim type, and a
    per-source breakdown — i.e. which kinds of claim turn out false most often,
    and who asserts them. INSUFFICIENT is excluded from the disagreement rate
    because nothing was learned; counting it either way would restate the very
    error being measured.
    """
    if receipts is None:
        receipts = read_all(brain_path)

    by_verdict: Dict[str, int] = {v.value: 0 for v in Verdict}
    by_claim: Dict[str, Dict[str, int]] = {}
    by_source: Dict[str, Dict[str, int]] = {}

    for r in receipts:
        by_verdict[r.verdict] = by_verdict.get(r.verdict, 0) + 1
        for bucket, key in ((by_claim, r.claim_type), (by_source, r.source)):
            slot = bucket.setdefault(key, {v.value: 0 for v in Verdict})
            slot[r.verdict] = slot.get(r.verdict, 0) + 1

    def _rate(d: Dict[str, int]) -> Optional[float]:
        decided = d.get(Verdict.PROVEN.value, 0) + d.get(Verdict.REFUTED.value, 0)
        if not decided:
            return None  # nothing decided — do NOT report 0.0, that reads as "never wrong"
        return round(d.get(Verdict.REFUTED.value, 0) / decided, 4)

    return {
        "total": len(receipts),
        "by_verdict": by_verdict,
        "disagreement_rate_by_claim": {k: _rate(v) for k, v in by_claim.items()},
        "disagreement_rate_by_source": {k: _rate(v) for k, v in by_source.items()},
        "note": "disagreement_rate excludes INSUFFICIENT; None means nothing decided yet",
    }
