"""Tests for runtime/verify_gate.py — the verdict→gate consumption seam.

Covers the ③ consume-only-on-CONFIRMED policy and, critically, the G2
predicate-binding refinement (RATIFICATION.md): a CONFIRMED verdict for an
*adjacent* predicate must NOT license a gate whose load-bearing predicate is
a different fact. Fail-closed on every non-CONFIRMED / unprobed path.
"""

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.verify_gate import (
    consume_if_confirmed,
    _verdict_satisfies_predicate,
)
from mcp_server_nucleus.runtime.verifier import Anchor, Verdict


# ── G2 predicate-binding (the load-bearing rule) ──────────────────────

class TestPredicateBinding:
    def _confirmed_verdict(self, anchor: Anchor) -> Verdict:
        return Verdict(
            claim_id="c",
            status="CONFIRMED",
            confidence=0.85,
            rationale="",
            anchors=[anchor.to_dict()],
            evidence=[{"anchor_id": anchor.anchor_id, "ok": True, "detail": "", "raw": None}],
        )

    def test_adjacent_confirmed_predicate_does_not_pass(self):
        # G2: verdict CONFIRMED on commit_exists, but the gate's load-bearing
        # predicate is is_ancestor. Adjacent → must NOT license the gate.
        adjacent = Anchor("a1", "git", {"op": "commit_exists", "sha": "abc1234"}, "", critical=True)
        verdict = self._confirmed_verdict(adjacent)
        assert _verdict_satisfies_predicate(verdict, [adjacent], "is_ancestor") is False

    def test_exact_predicate_passes(self):
        # Same CONFIRMED verdict, but the gate's predicate == the passed op.
        matched = Anchor("a1", "git", {"op": "is_ancestor", "sha": "abc1234"}, "", critical=True)
        verdict = self._confirmed_verdict(matched)
        assert _verdict_satisfies_predicate(verdict, [matched], "is_ancestor") is True

    def test_non_confirmed_status_never_passes(self):
        matched = Anchor("a1", "git", {"op": "is_ancestor", "sha": "abc1234"}, "", critical=True)
        for status in ("REFUTED", "UNVERIFIABLE", "PARTIAL"):
            verdict = Verdict(
                claim_id="c", status=status, confidence=0.5, rationale="",
                anchors=[matched.to_dict()],
                evidence=[{"anchor_id": "a1", "ok": True, "detail": "", "raw": None}],
            )
            assert _verdict_satisfies_predicate(verdict, [matched], "is_ancestor") is False

    def test_predicate_op_passed_but_that_anchor_failed(self):
        # The right-op anchor must be the one that PASSED, not merely present.
        matched = Anchor("a1", "git", {"op": "is_ancestor", "sha": "abc1234"}, "", critical=True)
        verdict = Verdict(
            claim_id="c", status="CONFIRMED", confidence=0.85, rationale="",
            anchors=[matched.to_dict()],
            evidence=[{"anchor_id": "a1", "ok": False, "detail": "", "raw": None}],
        )
        assert _verdict_satisfies_predicate(verdict, [matched], "is_ancestor") is False


# ── consume_if_confirmed — fail-closed paths ──────────────────────────

class TestConsumeFailClosed:
    def test_no_evidence_refs_fails_closed(self):
        # Raw claim, no backing commit → no probeable anchor → deny.
        assert consume_if_confirmed("done", "is_ancestor", []) is False
        assert consume_if_confirmed("done", "is_ancestor", None) is False

    def test_non_sha_evidence_fails_closed(self):
        assert consume_if_confirmed("done", "is_ancestor", ["not-a-sha!!"]) is False

    def test_bogus_sha_refuted_fails_closed(self, tmp_path):
        # A valid repo but a SHA that does not exist → REFUTED → deny.
        repo = _init_repo(tmp_path)
        assert consume_if_confirmed("done", "commit_exists", ["deadbeef"], repo=repo) is False

    def test_no_repo_unverifiable_fails_closed(self):
        # SHA-shaped but no repo to probe → UNVERIFIABLE → deny (fail closed).
        assert consume_if_confirmed("done", "commit_exists", ["abc1234"]) is False


# ── consume_if_confirmed — the CONFIRMED path against a real repo ──────

class TestConsumeConfirmed:
    def test_real_commit_confirmed_and_bound(self, tmp_path):
        repo, head = _init_repo(tmp_path, with_commit=True)
        # gate predicate == the op we probe, HEAD really exists → CONFIRMED+bound.
        assert consume_if_confirmed("built commit", "commit_exists", [head], repo=repo) is True

    def test_real_commit_confirmed_but_predicate_unbound(self, tmp_path):
        repo, head = _init_repo(tmp_path, with_commit=True)
        # HEAD exists (commit_exists would CONFIRM), but the gate demands
        # is_ancestor of origin/main — no origin → UNVERIFIABLE → deny.
        assert consume_if_confirmed("shipped", "is_ancestor", [head], repo=repo) is False


# ── helpers ───────────────────────────────────────────────────────────

def _init_repo(tmp_path, with_commit: bool = False):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    if not with_commit:
        return str(repo)
    (repo / "f.txt").write_text("hi")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    head = _git(repo, "rev-parse", "HEAD").strip()
    return str(repo), head


def _git(repo, *args):
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    return r.stdout
