"""Adversarial regression suite for Agent OS claim-extraction scope.

Investigates a specific, live-observed anomaly (2026-08-21, see
docs/AGENT_OS_OAUTH_LIVE_VERIFICATION.md): a 3-cell live loop run showed 2 of
3 turns verdict CONFIRMED/PARTIAL even though the model's own response
appeared to refuse the task. The original hypothesis was that claim
extraction reads the injected intent/context, not just the model's own
outcome text.

**That hypothesis is REFUTED by this suite** (see
test_context_never_leaks_into_the_claim / test_outcome_only_refusal_is_never_
confirmed_even_with_true_claim_in_context below). ``verified_record.label_turn``
builds ``Claim(assertion=outcome, raw={"context": context})`` —
``classify_claim``/``_decompose_anchors`` read only ``claim.assertion``.
``context`` never influences classification or anchor extraction. Confirmed
directly against the real (unmocked) extraction path, not asserted from
reading the code alone.

**The real root cause was different**: ``boot.py``'s
``record_turn_to_flywheel`` truncated the *persisted* ``outcome`` field to
``[:500]`` chars, while ``label_turn`` (called earlier in ``boot_cell``) had
already verified the model's FULL, untruncated text. A turn could legitimately
CONFIRM on content that existed in what was verified but not in what was
stored — an audit-trail integrity gap, not a claim-extraction scope bug. Fixed
in this same commit: ``boot.py`` no longer truncates the stored outcome.
``test_persisted_outcome_is_not_truncated_below_what_was_verified`` is the
permanent regression test for that fix.

A third, separate finding turned up while building this suite: hedged claims
("I believe X may exist") got CONFIRMED with no hedge detection at all —
pure keyword/filename regex, no negation or uncertainty awareness. Originally
tracked as an out-of-scope ``xfail``; fixed 2026-08-21 (Track B2 of the
follow-up brief) via a HEURISTIC, NOT SEMANTIC hedge-phrase blocklist in
``RuleReasoner.adjudicate`` — see ``_HEDGE_PHRASE_RE`` in verifier.py and
``test_hedged_claim_downgrades_to_partial_not_confirmed`` below. Sarcasm,
double-negatives, and hedges outside the fixed phrase list remain undetected
and are a separate, still-open item — not solved by this patch.

A fourth, separate finding also turned up: the FILE-EXISTS path regex
stripped the leading ``/`` off absolute paths, resolving them against the
wrong base directory and REFUTING files that genuinely exist. Also fixed
2026-08-21 (Track B1) — see ``test_absolute_path_claim_for_existing_file_confirms_not_refutes``
below.

No mocking of the extraction step anywhere in this file — every test calls
``label_turn`` (and, for the truncation regression, ``record_turn_to_flywheel``
directly) against hand-constructed, deterministic outcome/intent/context text
or real temp files. This is deliberate: the exchange.py authorization_code
bug (a random UUID sent as the OAuth ``code``) went undetected specifically
because its own tests mocked the network call it needed to exercise for real.
"""
from __future__ import annotations

import json

from mcp_server_nucleus.runtime.agent_os.verified_record import label_turn


# ── Case 1: refusal in outcome, true claim only in injected context ─────────


def test_outcome_only_refusal_is_never_confirmed_even_with_true_claim_in_context(
    tmp_path,
):
    """Model refuses outright; the true, checkable claim exists ONLY in the
    injected context (the intent-equivalent parameter), never in the model's
    own words. Expected: NOT confirmable — context must never leak into the
    claim regardless of how true or checkable it is.
    """
    real_file = tmp_path / "AGENTS.md"
    real_file.write_text("real content\n", encoding="utf-8")

    outcome_refusal = (
        "I cannot confirm this without seeing the filesystem myself. "
        "I decline to state anything about file presence."
    )
    context_with_true_claim = f"{real_file} exists at the repository root (confirmed true)."

    assert "AGENTS.md" not in outcome_refusal
    assert len(outcome_refusal) < 500  # rules out the truncation confound entirely

    result = label_turn(outcome_refusal, context=context_with_true_claim)
    assert result["status"] != "CONFIRMED"
    assert result["status"] == "UNVERIFIABLE"


def test_context_never_leaks_into_the_claim_directly():
    """Direct proof the ``context`` kwarg cannot influence classification: an
    outcome with zero deterministic anchors, paired with a context string
    containing an unambiguous git-SHA-shaped claim, must still be
    UNVERIFIABLE — the SHA in context is never seen by the classifier.
    """
    outcome = "everything is fine, nothing specific to check here"
    context = "commit 0123456789abcdef0123456789abcdef01234567 fixed it"

    result = label_turn(outcome, context=context)
    assert result["status"] == "UNVERIFIABLE"


# ── Case 2: model restates the claim in its own words, true anchor ──────────


def test_model_own_words_matching_true_anchor_confirms():
    """Model states the claim itself, in its own words, matching a real,
    passing fs:file_exists anchor (direct match, not adjacent) → CONFIRMED.

    Bare-relative filename that genuinely exists at repo root (AGENTS.md).
    """
    outcome = "FILE EXISTS: AGENTS.md"
    result = label_turn(outcome)
    assert result["status"] == "CONFIRMED"
    assert result["confidence"] > 0.5


def test_absolute_path_claim_for_existing_file_confirms_not_refutes():
    """Regression test for a real bug found while building this suite
    (2026-08-21): the FILE-EXISTS path regex used to strip the leading ``/``
    off absolute paths at the word boundary (``\\b`` doesn't fire between two
    non-word characters, e.g. a space and a ``/``), silently turning
    ``/abs/path/AGENTS.md`` into a relative ``abs/path/AGENTS.md`` resolved
    against the wrong base directory (``default_repo`` prepended in front of
    an already-absolute-looking remainder) and producing REFUTED for a file
    that genuinely exists. REFUTED there meant "checked the wrong location,"
    not "doesn't exist" — a false-negative on real evidence.

    Fixed by changing the leading ``\\b`` to a negative lookbehind
    ``(?<!\\w)``, which correctly fires before a ``/`` preceded by whitespace
    (space is non-word, so "not preceded by a word char" is true) without
    changing where relative-path matches start (still fires identically
    there, since the character before a bare filename is the same either
    way). Trailing boundary and relative-path behavior both verified
    unchanged before this landed.
    """
    import os

    absolute_path = os.path.abspath("AGENTS.md")
    assert os.path.exists(absolute_path)

    outcome = f"FILE EXISTS: {absolute_path}"
    result = label_turn(outcome)
    assert result["status"] == "CONFIRMED", (
        f"expected CONFIRMED for a genuinely-existing absolute path, got "
        f"{result['status']}: {result['detail']}"
    )


# ── Case 3: model contradicts a true anchor (names a real path, wrong claim) ─


def test_model_claim_of_nonexistent_file_is_refuted():
    """Model asserts a specific file exists; it does not → REFUTED, not
    UNVERIFIABLE. A false claim must be caught, not just withheld.

    Bare relative filename (see the docstring on
    test_model_own_words_matching_true_anchor_confirms for why — an absolute
    tmp_path here would REFUTE for the wrong reason, a separate path-parsing
    bug, not genuine nonexistence).
    """
    missing_relative_name = "this_file_was_never_created_anywhere.md"
    import subprocess
    from pathlib import Path

    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=3,
    ).stdout.strip()
    assert repo_root and not (Path(repo_root) / missing_relative_name).exists()

    outcome = f"FILE EXISTS: {missing_relative_name}"
    result = label_turn(outcome)
    assert result["status"] == "REFUTED"


# ── Case 4: hedged/ambiguous claim — fixed 2026-08-21 (Track B2) ────────────


def test_hedged_claim_downgrades_to_partial_not_confirmed(tmp_path):
    """Was a tracked xfail (KNOWN GAP, found 2026-08-21): classify_claim /
    _decompose_anchors are pure keyword+filename regex with zero
    negation/hedge awareness, so "I believe X may exist" matched FILE-EXISTS
    + a passing fs anchor exactly like an unhedged assertion and CONFIRMED.

    Fixed via a HEURISTIC, NOT SEMANTIC hedge-phrase blocklist
    (``_HEDGE_PHRASE_RE`` in verifier.py, applied in
    ``RuleReasoner.adjudicate``): an otherwise-CONFIRMED verdict downgrades to
    PARTIAL when the assertion text matches one of a fixed set of hedge
    phrases (may/might/possibly/perhaps/probably/I believe/I think/not
    sure/not certain). This is explicitly NOT a semantic fix — sarcasm,
    double-negatives, and hedges phrased outside this exact word list are
    still undetected and are a separate, still-open future item, not solved
    by this patch. See the docstring on ``_HEDGE_PHRASE_RE`` for the full
    scope statement.
    """
    real_file = tmp_path / "AGENTS.md"
    real_file.write_text("x\n", encoding="utf-8")

    outcome = f"I believe {real_file} may exist, though I am not fully certain."
    result = label_turn(outcome)
    assert result["status"] == "PARTIAL", (
        f"expected PARTIAL for a hedged claim even with a passing anchor, "
        f"got {result['status']}: {result['detail']}"
    )
    # Note: the "Hedged assertion..." explanation lives in Verdict.remediation,
    # which label_turn() does not currently surface (only status/confidence/
    # detail=rationale). The status downgrade itself is what this test
    # verifies; the anchor pass/fail rationale in `detail` is unaffected by
    # the hedge check by design (it still reports what was actually probed).


# ── Case 5: default free-form prompt — no spurious CONFIRMED ────────────────


def test_freeform_reflection_with_business_state_trigger_words_never_spuriously_confirms():
    """Reproduces the shape of the 20-cell default-prompt run (see the
    reference doc): free-form reflection mentioning '/Users/...'-shaped text
    (spurious BUSINESS-STATE join via the bare \\busers?\\b pattern) but with
    NO real deterministic anchor (no filename, no git SHA, no URL) present.
    Must never spuriously CONFIRM from an unknown/manual-only class.
    """
    outcome = (
        "The current users of this system include the operator's local "
        "workspace as an active session, and the architecture is scoped "
        "around multiple active merchants and subscribers reasoning about "
        "the platform's business state in the abstract."
    )
    result = label_turn(outcome)
    assert result["status"] != "CONFIRMED"
    assert result["status"] == "UNVERIFIABLE"


def test_freeform_reflection_20cell_default_prompt_pattern_empirical_baseline():
    """Not a strict business-logic assertion — a frozen empirical baseline.
    The actual 20-cell live run against the loop's default prompt ("Run the
    loop: observe, recall, think, record...") produced CONFIRMED: 0 across
    every real turn. This test locks that shape in with representative real
    turn outcome text pulled from that run, so a future change to the
    doctrine that starts spuriously confirming free-form reflection is
    caught here, not discovered live again.
    """
    real_turn_outcome = (
        "# Nucleus Agent OS — Turn 2 Observation & Recall\n\n"
        "## Observed State\nI am booted INSIDE Nucleus. The memory injected "
        "above is comprehensive: 11 commits across STAGE-1 build wave "
        "(feat/dsor-verifier branch), the keystone inversion (gateway "
        "mediates cognition, not MCP), first cell proof (boot.py + membrane "
        "seams REAL), two-walls on keyless (auth proven, quota bounded), and "
        "the complete FABLE THEORY."
    )
    result = label_turn(real_turn_outcome)
    assert result["status"] != "CONFIRMED"


# ── Case 6: the actual root cause found here — persisted-outcome truncation ─


def test_persisted_outcome_is_not_truncated_below_what_was_verified(tmp_path):
    """Regression test for the REAL bug this investigation found: boot.py's
    record_turn_to_flywheel used to persist outcome[:500], silently
    truncating the on-disk evidence for a verdict that had already been
    computed against the full, untruncated text. A CONFIRMED turn's stored
    record could omit the very substring that earned it — an audit-trail
    integrity gap. Minimal deterministic repro, no live model call needed:
    build a >500-char outcome whose only checkable claim sits past char 500,
    verify it directly (as boot_cell does), then persist it and assert the
    stored record still contains the evidence.
    """
    # Bare relative filename genuinely present at repo root (AGENTS.md) — a
    # tmp_path absolute path would trip the separate leading-slash bug
    # documented on test_model_own_words_matching_true_anchor_confirms.
    real_filename = "AGENTS.md"

    padding = "I am thinking carefully about this refusal. " * 12
    full_outcome = padding + f"In conclusion, after all that padding, FILE EXISTS: {real_filename}"
    assert len(full_outcome) > 500
    assert real_filename not in full_outcome[:500], (
        "test setup sanity check: the claim must genuinely sit past the old "
        "truncation point, or this test doesn't exercise the bug at all"
    )

    # This is what boot_cell does: verify the FULL text first.
    verdict = label_turn(full_outcome)
    assert verdict["status"] == "CONFIRMED"

    # This is what record_turn_to_flywheel does with that same full text.
    from mcp_server_nucleus.runtime.agent_os.boot import (
        GatewayResult,
        record_turn_to_flywheel,
    )

    gres = GatewayResult(
        text=full_outcome,
        engine="STUB",
        mediated=True,
        event_id="evt-test",
        model="stub-deterministic-v0",
        stubbed=True,
    )
    brain = tmp_path / "brain"
    record_turn_to_flywheel(
        intent="test intent",
        recalled_rows=[],
        gateway_result=gres,
        brain_path=str(brain),
        verified_label=verdict,
    )

    turns_path = brain / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert rows, "record_turn_to_flywheel must write at least one turn"
    stored_outcome = rows[-1]["outcome"]

    assert stored_outcome == full_outcome, (
        "the persisted outcome must be the FULL text that was actually "
        "verified -- a truncated stored record that omits the evidence for "
        "its own verdict is the exact bug this test exists to catch"
    )
    assert real_filename in stored_outcome
