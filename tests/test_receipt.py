"""Tests for the claim-receipt corpus.

The load-bearing property is that INSUFFICIENT survives every round trip and
every aggregation. Every incident this module was written for was a third
state being quietly folded into a neighbour, so these tests assert that it
never is.
"""

import json

import pytest

from mcp_server_nucleus.runtime.receipt import (
    ClaimType,
    Receipt,
    Verdict,
    read_all,
    record,
    summarize,
)


def _mk(verdict, claim_type=ClaimType.TESTS_PASS, source="agent_a", **kw):
    return Receipt(
        claim_type=claim_type,
        claim="tests pass",
        verdict=verdict,
        primitive="pytest",
        source=source,
        **kw,
    )


def test_roundtrip_preserves_all_three_verdicts(tmp_path):
    for v in (Verdict.PROVEN, Verdict.REFUTED, Verdict.INSUFFICIENT):
        assert record(_mk(v), brain_path=tmp_path)
    got = read_all(brain_path=tmp_path)
    assert [r.verdict for r in got] == ["PROVEN", "REFUTED", "INSUFFICIENT"]


def test_insufficient_is_not_proven_and_not_refuted(tmp_path):
    """The whole point: INSUFFICIENT must never read as either neighbour."""
    r = _mk(Verdict.INSUFFICIENT)
    assert r.verdict == "INSUFFICIENT"
    assert r.agrees is False           # not a pass
    assert r.verdict != Verdict.REFUTED.value  # and not a failure


def test_insufficient_excluded_from_disagreement_rate(tmp_path):
    """A run that decided nothing must not read as 'never wrong'."""
    for _ in range(3):
        record(_mk(Verdict.INSUFFICIENT), brain_path=tmp_path)
    s = summarize(brain_path=tmp_path)
    assert s["by_verdict"]["INSUFFICIENT"] == 3
    # None, NOT 0.0 — 0.0 would claim a perfect record from zero evidence.
    assert s["disagreement_rate_by_claim"]["tests_pass"] is None


def test_disagreement_rate_computed_over_decided_only(tmp_path):
    record(_mk(Verdict.PROVEN), brain_path=tmp_path)
    record(_mk(Verdict.REFUTED), brain_path=tmp_path)
    record(_mk(Verdict.INSUFFICIENT), brain_path=tmp_path)
    s = summarize(brain_path=tmp_path)
    assert s["disagreement_rate_by_claim"]["tests_pass"] == 0.5  # 1 of 2 decided
    assert s["total"] == 3


def test_per_source_priors_separate_agents(tmp_path):
    """The corpus must be able to say WHICH source over-reports."""
    for _ in range(3):
        record(_mk(Verdict.REFUTED, source="over_reporter"), brain_path=tmp_path)
    record(_mk(Verdict.PROVEN, source="honest"), brain_path=tmp_path)
    s = summarize(brain_path=tmp_path)
    assert s["disagreement_rate_by_source"]["over_reporter"] == 1.0
    assert s["disagreement_rate_by_source"]["honest"] == 0.0


def test_claimed_observed_delta_is_preserved(tmp_path):
    """The delta between claim and observation is the product; keep it verbatim."""
    record(_mk(Verdict.REFUTED, claimed="113 files / 2085 tests",
               observed="126 files / 2297 tests"), brain_path=tmp_path)
    r = read_all(brain_path=tmp_path)[0]
    assert r.claimed == "113 files / 2085 tests"
    assert r.observed == "126 files / 2297 tests"


def test_malformed_line_does_not_lose_the_corpus(tmp_path):
    record(_mk(Verdict.PROVEN), brain_path=tmp_path)
    path = tmp_path / "receipts" / "receipts.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write("{not json at all\n")
    record(_mk(Verdict.REFUTED), brain_path=tmp_path)
    got = read_all(brain_path=tmp_path)
    assert len(got) == 2  # bad row skipped, good rows survive


def test_record_never_raises_on_unwritable_path(tmp_path):
    """A receipt-store failure must never break the check being recorded."""
    blocked = tmp_path / "blocked"
    blocked.write_text("i am a file, not a directory")
    assert record(_mk(Verdict.PROVEN), brain_path=blocked) is False


def test_enum_inputs_are_normalized_to_strings(tmp_path):
    record(_mk(Verdict.PROVEN, claim_type=ClaimType.DEPLOYED), brain_path=tmp_path)
    raw = (tmp_path / "receipts" / "receipts.jsonl").read_text().strip()
    d = json.loads(raw)
    assert d["verdict"] == "PROVEN"
    assert d["claim_type"] == "deployed"


def test_empty_corpus_summarizes_without_error(tmp_path):
    s = summarize(brain_path=tmp_path)
    assert s["total"] == 0
    assert s["by_verdict"]["INSUFFICIENT"] == 0
