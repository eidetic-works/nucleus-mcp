"""Agent OS — the gate that decides whether a proposed change is safe to offer.

Track S3 of AGENT_OS_SAFE_FIRST_PR. This is the decision the whole brief exists
for, so it is written to fail closed in every direction.

The rule, stated once: a change is SAFE only when every claim about it is
CONFIRMED. Not "mostly confirmed", not "confirmed except the ones we could not
check". One REFUTED claim blocks. One UNVERIFIABLE claim blocks. Zero claims
blocks — an empty claim set is the absence of evidence, not evidence of safety,
and it is exactly what a bug in the caller produces.

That last case is the one worth stating aloud. `all(x)` over an empty list is
True in Python, so the naive implementation of "all claims confirmed" marks a
change with NO claims as safe. A caller that silently failed to emit claims
would receive a green light. The empty check below is not defensive
programming; it is the difference between this gate working and this gate
being decorative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SafetyVerdict:
    """Why a change was or was not cleared. `safe` is never True by default."""

    safe: bool
    reason: str
    confirmed: List[str] = field(default_factory=list)
    blocking: List[str] = field(default_factory=list)

    def explain(self) -> str:
        """Plain language, per the brief: say WHY, not just no."""
        if self.safe:
            n = len(self.confirmed)
            return (
                f"Safe to propose. All {n} claim(s) about this change were "
                f"verified against the real repository."
            )
        lines = [f"Not safe to propose: {self.reason}"]
        for c in self.blocking:
            lines.append(f"  - unverified: {c}")
        return "\n".join(lines)


def evaluate(
    verified: Dict[str, List[str]],
    *,
    path_allowed: Optional[bool] = None,
    path_reason: str = "",
) -> SafetyVerdict:
    """Decide whether a proposed change may be offered to a human.

    ``verified`` is the dict from explain_changes.verify_claims:
    {"confirmed": [...], "refuted": [...], "unverifiable": [...]}.

    ``path_allowed`` is the S1 refusal gate's answer. Passing None means the
    caller never asked -- which is treated as NOT allowed. A gate that assumes
    permission it was never given is not a gate.
    """
    confirmed = list(verified.get("confirmed") or [])
    refuted = list(verified.get("refuted") or [])
    unverifiable = list(verified.get("unverifiable") or [])

    # The path gate runs first: no amount of confirmed claims makes it
    # acceptable to touch a deploy script. None means "never asked" -> deny.
    if path_allowed is not True:
        return SafetyVerdict(
            False,
            path_reason or (
                "the target path was not cleared by the safe-target gate"
                if path_allowed is False
                else "the safe-target gate was never consulted for this path"
            ),
            confirmed,
            refuted + unverifiable,
        )

    # An empty claim set is not a pass. all([]) is True in Python, so this
    # check is what stops a caller that emitted no claims from being cleared.
    if not confirmed and not refuted and not unverifiable:
        return SafetyVerdict(
            False,
            "no claims were made about this change, so nothing was verified. "
            "An empty claim set is the absence of evidence, not evidence of "
            "safety.",
            [],
            [],
        )

    if refuted:
        return SafetyVerdict(
            False,
            f"{len(refuted)} claim(s) were REFUTED -- checked against the "
            f"repository and found false.",
            confirmed,
            refuted + unverifiable,
        )

    if unverifiable:
        return SafetyVerdict(
            False,
            f"{len(unverifiable)} claim(s) could NOT be verified. That is not "
            f"the same as being false, and it is not the same as being true -- "
            f"it means no deterministic check could settle them, so this "
            f"change is not cleared.",
            confirmed,
            unverifiable,
        )

    return SafetyVerdict(True, "all claims confirmed", confirmed, [])
