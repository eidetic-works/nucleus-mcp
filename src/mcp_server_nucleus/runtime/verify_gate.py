"""
verify_gate — the verdict→gate consumption seam (③ + G2 predicate-binding)
==========================================================================
The DSoR Verifier (``runtime/verifier.py``) can adjudicate a claim to
CONFIRMED / REFUTED / UNVERIFIABLE, but an audit found it is wired into
NOTHING — every gate in the substrate consumes raw agent claims ("status is
DONE", "install happened", "I am main") without ever running the referee.

This module is the reusable helper that closes that seam for ONE gate at a
time. It implements the Verification-Game consumption policy (③) *and* the
G2 refinement adjudicated in ``docs/verifier/RATIFICATION.md``:

  * ③ (VERIFICATION_GAME.md §2, Policy B): consume a gating claim ONLY on a
    CONFIRMED verdict. UNVERIFIABLE and REFUTED both yield zero benefit —
    fail **CLOSED**.
  * G2 (RATIFICATION.md §"G2", LOAD-BEARING): tighten ③ to **predicate-
    binding** — consume only when the CONFIRMED verdict's satisfied anchor
    covers *the gate's own load-bearing predicate*. A CONFIRMED verdict for
    an *adjacent* predicate (e.g. ``commit_exists`` when the gate's real
    predicate is ``is_ancestor``) must **NOT** license the gate. Without
    this clause ③ is satisfiable while the substrate is adjacent-consumed.

Design constraints (proof-of-pattern slice):
  * ADDITIVE / dependency-light — stdlib + the sibling ``verifier`` module
    only. No new pip deps.
  * IMPORT-SAFE — importing this module pulls nothing heavy; the ``verifier``
    import is lazy (inside the function) so a caller that never turns the
    gate on never pays for it, and a broken/absent verifier degrades to
    fail-closed rather than an ImportError at module load.
  * The public entry point ``consume_if_confirmed`` returns a plain bool and
    NEVER raises — any internal failure means "could not confirm" → False.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional

logger = logging.getLogger("nucleus.verify_gate")

# git ops whose predicate this helper can bind an evidence-ref anchor to.
# `gate_predicate` is the *op name* of the gate's load-bearing anchor — the
# doctrine-fixed deterministic check that must pass (ANCHOR_DOCTRINE §3).
_GIT_OPS = {
    "is_ancestor",
    "commit_exists",
    "file_exists_at_head",
    "log_grep",
    "branch_contains",
}

# A git commit-ish evidence ref: a 7–40 char lowercase hex SHA.
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _build_anchors(gate_predicate: str, refs: List[str], repo: Optional[str]) -> List[Any]:
    """Build the deterministic anchors that bind ``gate_predicate`` to each
    supplied evidence ref. Returns [] when nothing probeable can be built —
    which the caller treats as fail-closed (no backing evidence ⇒ deny).

    For a git predicate, only SHA-shaped refs produce an anchor; the anchor's
    ``op`` IS ``gate_predicate`` — the gate declares its load-bearing
    predicate and we probe exactly that fact against the claimed evidence.
    """
    try:
        from .verifier import Anchor
    except Exception:  # pragma: no cover - verifier unavailable ⇒ fail closed
        return []

    anchors: List[Any] = []
    if gate_predicate in _GIT_OPS:
        for i, ref in enumerate(refs):
            sha = ref.strip()
            if not _SHA_RE.match(sha.lower()):
                continue
            spec = {"op": gate_predicate, "sha": sha}
            if gate_predicate == "is_ancestor":
                spec["ref"] = "origin/main"
            if repo:
                spec["repo"] = repo
            anchors.append(
                Anchor(
                    anchor_id=f"gate-{gate_predicate}-{sha[:12]}-{i}",
                    kind="git",
                    spec=spec,
                    description=f"{gate_predicate}({sha}) — gate load-bearing predicate",
                    critical=True,
                )
            )
    return anchors


def _verdict_satisfies_predicate(verdict: Any, anchors: List[Any], gate_predicate: str) -> bool:
    """The G2 predicate-binding test, isolated so it can be unit-tested
    directly against a hand-built verdict.

    True iff the verdict is CONFIRMED **and** at least one *passed* anchor
    (``ok is True``) has ``op == gate_predicate``. A CONFIRMED verdict whose
    passing anchors are all *adjacent* (a different op) returns False — that
    is the whole point of G2.
    """
    if verdict is None or getattr(verdict, "status", None) != "CONFIRMED":
        return False
    by_id = {a.anchor_id: a for a in anchors}
    for e in (getattr(verdict, "evidence", None) or []):
        if not isinstance(e, dict) or e.get("ok") is not True:
            continue
        anchor = by_id.get(e.get("anchor_id"))
        if anchor is not None and (anchor.spec or {}).get("op") == gate_predicate:
            return True
    return False


def consume_if_confirmed(
    assertion: str,
    gate_predicate: str,
    evidence_refs: Optional[List[str]],
    *,
    repo: Optional[str] = None,
) -> bool:
    """Should a gate consume ``assertion`` as satisfied?

    Builds a ``Claim``, runs the ``Verifier``, and returns True ONLY if the
    verdict is CONFIRMED *and* the verdict's satisfied anchor set covers
    ``gate_predicate`` (predicate-binding, G2).

    Fails CLOSED — UNVERIFIABLE, REFUTED, no probeable evidence, an
    adjacent-only CONFIRMED, or any internal error all return False.

    Args:
      assertion:      the agent's claim text (for the verdict record).
      gate_predicate: op name of the gate's load-bearing anchor
                      (e.g. ``"is_ancestor"``). This is the fact the gate
                      truly depends on; only a CONFIRMED verdict on THIS
                      predicate licenses consumption.
      evidence_refs:  the claim's backing evidence (commit SHA / ci_run_id).
      repo:           git work-tree to probe (for git predicates).
    """
    refs = [r.strip() for r in (evidence_refs or []) if isinstance(r, str) and r.strip()]

    anchors = _build_anchors(gate_predicate, refs, repo)
    if not anchors:
        # No probeable anchor bound to this predicate (e.g. a raw "DONE" with
        # no backing commit). Fail closed — an unprobed claim is not consumed.
        return False

    try:
        from .verifier import Claim, ProbeEngine, InjectedReasoner, Verifier
    except Exception as exc:  # pragma: no cover - verifier unavailable ⇒ deny
        logger.debug("verify_gate: verifier import failed, failing closed: %s", exc)
        return False

    claim = Claim(
        claim_id="gate-claim",
        source="gate",
        claimant="gate",
        assertion=assertion or "",
        evidence_refs=refs,
    )
    reasoner = InjectedReasoner(anchor_map={claim.claim_id: anchors})
    engine = ProbeEngine(default_repo=repo)
    try:
        verdict = Verifier(reasoner, engine).verify(claim)
    except Exception as exc:  # pragma: no cover - probe/adjudicate blew up ⇒ deny
        logger.debug("verify_gate: verify() raised, failing closed: %s", exc)
        return False

    return _verdict_satisfies_predicate(verdict, anchors, gate_predicate)
