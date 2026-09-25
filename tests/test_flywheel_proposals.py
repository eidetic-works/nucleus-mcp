"""The accept/reject gate — the last third of dreaming.

The talk's loop ends with a human: a batch pass proposes a memory change,
attaches example transcripts and prevalence stats, and a person accepts or
rejects it. Counting and citing shipped already. This is the part that makes it
dreaming rather than better tickets — nothing reaches memory without a decision.

THE CENTRAL REFUSAL: A PROPOSAL WHOSE EVIDENCE IS INSUFFICIENT CANNOT BE
ACCEPTED. Not "is accepted with a warning" — refused. A capped scan produced a
number over a set it could not fully see, and approving a permanent memory
change on that basis is precisely how a partial reading becomes an organisational
fact. This repo has the receipts: 1,021 envelopes, 0 qualifying by construction,
and a gate that read the zero as an answer.

The other three rules follow the shapes that already work here:
  * accept is the ONLY path to memory (two-phase, like goal item closure)
  * a rejection is RECORDED, never deleted (append-only, like store.rollback —
    the record of what was rejected is itself evidence)
  * accepting twice is refused (a write that looks like progress and isn't)
"""
from __future__ import annotations

import json

import pytest

from mcp_server_nucleus.flywheel import prevalence as P
from mcp_server_nucleus.flywheel import proposals as PR
from nucleus_wedge.store import Store


@pytest.fixture()
def brain(tmp_path):
    return tmp_path / ".brain"


@pytest.fixture()
def corpus(tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    for n, lines in [
        ("aaaaaaaa-0000-0000-0000-000000000001", ["em dash everywhere"]),
        ("bbbbbbbb-0000-0000-0000-000000000002", ["fine"]),
        ("cccccccc-0000-0000-0000-000000000003", ["em dash everywhere"]),
    ]:
        # Real transcript shape: text lives in message.content, never at the
        # top level. Plain-text fixtures only worked while scan regexed raw
        # JSONL lines, which counted injected boilerplate as behaviour.
        (d / f"{n}.jsonl").write_text("\n".join(
            json.dumps({"type": "assistant",
                        "message": {"content": [{"type": "text", "text": ln}]}})
            for ln in lines) + "\n")
    return d


def _complete(corpus):
    return P.scan("em dash everywhere", roots=[corpus])


def _capped(corpus):
    return P.scan("em dash everywhere", roots=[corpus], max_sessions=1)


# ── proposing ──────────────────────────────────────────────────────────────


def test_a_proposal_starts_pending(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    assert p["status"] == "pending"


def test_a_proposal_carries_its_evidence(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    assert p["evidence"]["sessions_matched"] == 2
    assert p["evidence"]["examples"], "a proposal with no citation is an opinion"


def test_pending_proposals_are_listable(brain, corpus):
    PR.propose(brain, "a", _complete(corpus))
    PR.propose(brain, "b", _complete(corpus))
    assert len(PR.pending(brain)) == 2


def test_a_pending_proposal_writes_nothing_to_memory(brain, corpus):
    PR.propose(brain, "stop using em dashes", _complete(corpus))
    assert Store(brain_path=brain).exists is False, "a proposal touched memory"


# ── THE central refusal ────────────────────────────────────────────────────


def test_an_insufficient_proposal_cannot_be_accepted(brain, corpus):
    """THE control. A count over a set we could not fully see must not become a
    permanent memory."""
    p = PR.propose(brain, "stop using em dashes", _capped(corpus))
    with pytest.raises(ValueError, match="INSUFFICIENT|insufficient"):
        PR.accept(brain, p["proposal_id"], by="operator")


def test_an_insufficient_proposal_writes_nothing_even_on_a_failed_accept(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _capped(corpus))
    try:
        PR.accept(brain, p["proposal_id"], by="operator")
    except ValueError:
        pass
    assert Store(brain_path=brain).exists is False


def test_an_insufficient_proposal_CAN_be_rejected(brain, corpus):
    """Weak evidence is a reason to reject, not a reason to be stuck."""
    p = PR.propose(brain, "stop using em dashes", _capped(corpus))
    out = PR.reject(brain, p["proposal_id"], by="operator", reason="scan was capped")
    assert out["status"] == "rejected"


# ── accepting is the only path to memory ───────────────────────────────────


def test_accept_writes_the_memory(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    PR.accept(brain, p["proposal_id"], by="operator")
    s = Store(brain_path=brain)
    assert any("em dash" in r["snapshot"]["value"] for r in s.rows())


def test_the_written_memory_cites_its_prevalence(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    PR.accept(brain, p["proposal_id"], by="operator")
    vals = [r["snapshot"]["value"] for r in Store(brain_path=brain).rows()]
    assert any("2 of 3" in v for v in vals), "the memory dropped the evidence that justified it"


def test_accepting_twice_is_refused(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    PR.accept(brain, p["proposal_id"], by="operator")
    with pytest.raises(ValueError):
        PR.accept(brain, p["proposal_id"], by="operator")


def test_a_double_accept_does_not_double_write(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    PR.accept(brain, p["proposal_id"], by="operator")
    before = len(list(Store(brain_path=brain).rows()))
    try:
        PR.accept(brain, p["proposal_id"], by="operator")
    except ValueError:
        pass
    assert len(list(Store(brain_path=brain).rows())) == before


def test_rejecting_writes_nothing_to_memory(brain, corpus):
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    PR.reject(brain, p["proposal_id"], by="operator", reason="not a real pattern")
    assert Store(brain_path=brain).exists is False


# ── the record survives the decision ───────────────────────────────────────


def test_a_rejection_is_recorded_not_deleted(brain, corpus):
    """Append-only, like store.rollback. What was rejected, and why, is itself
    evidence — a queue that forgets its rejections re-proposes them forever."""
    p = PR.propose(brain, "stop using em dashes", _complete(corpus))
    PR.reject(brain, p["proposal_id"], by="operator", reason="too narrow")
    all_p = PR.all_proposals(brain)
    assert len(all_p) == 1
    assert all_p[0]["status"] == "rejected" and all_p[0]["reason"] == "too narrow"


def test_a_decision_records_who_and_when(brain, corpus):
    p = PR.propose(brain, "x", _complete(corpus))
    out = PR.accept(brain, p["proposal_id"], by="operator")
    assert out["decided_by"] == "operator" and out["decided_at"]


def test_a_rejection_requires_a_reason(brain, corpus):
    p = PR.propose(brain, "x", _complete(corpus))
    with pytest.raises(ValueError):
        PR.reject(brain, p["proposal_id"], by="operator", reason="")


def test_deciding_an_unknown_proposal_is_refused(brain):
    with pytest.raises(ValueError):
        PR.accept(brain, "no-such-id", by="operator")


def test_pending_excludes_decided(brain, corpus):
    a = PR.propose(brain, "a", _complete(corpus))
    PR.propose(brain, "b", _complete(corpus))
    PR.reject(brain, a["proposal_id"], by="operator", reason="no")
    assert [p["proposed_memory"] for p in PR.pending(brain)] == ["b"]


# --- precision: a count of words is not a count of the failure -------------

def _sampled(brain, n_sample=10, required=True, matched=40):
    from mcp_server_nucleus.flywheel.prevalence import Prevalence
    pv = Prevalence(pattern="p", sessions_matched=matched, sessions_scanned=100, complete=True,
                    sample=[{"session": f"s{i}", "excerpt": f"x{i}", "line": 1} for i in range(n_sample)])
    return PR.propose(brain, "a memory", pv, pattern="p", precision_required=required)


@pytest.fixture
def pbrain(tmp_path):
    b = tmp_path / "b"; b.mkdir(); return b


def test_wilson_lower_is_a_range_not_a_point():
    from mcp_server_nucleus.flywheel.proposals import wilson_lower
    assert wilson_lower(3, 5) < 0.3, "3 of 5 must not read as 60%"
    assert wilson_lower(20, 20) > 0.83
    assert wilson_lower(0, 0) == 0.0
    assert wilson_lower(10, 20) < wilson_lower(20, 40), "more evidence must tighten the bound"


def test_unmeasured_precision_cannot_be_accepted(pbrain):
    row = _sampled(pbrain)
    with pytest.raises(ValueError, match="PRECISION was never measured"):
        PR.accept(pbrain, row["proposal_id"])


def test_low_precision_cannot_be_accepted(pbrain):
    """The 79-session pattern whose matches were ordinary sentences."""
    row = _sampled(pbrain)
    PR.label(pbrain, row["proposal_id"], [True, True] + [False] * 8)
    with pytest.raises(ValueError, match="only 2 of 10"):
        PR.accept(pbrain, row["proposal_id"])


def test_high_precision_is_accepted_and_writes_once(pbrain):
    """The opposed half: the gate must not refuse a pattern that earns it."""
    row = _sampled(pbrain)
    PR.label(pbrain, row["proposal_id"], [True] * 9 + [False])
    out = PR.accept(pbrain, row["proposal_id"])
    assert out["status"] == "accepted"
    hist = pbrain / "engrams" / "history.jsonl"
    assert len(hist.read_text().splitlines()) == 1


def test_unclear_counts_against_the_pattern(pbrain):
    row = _sampled(pbrain)
    out = PR.label(pbrain, row["proposal_id"], [True] * 5 + [None] * 5)
    p = out["evidence"]["precision"]
    assert p["positive"] == 5 and p["unclear"] == 5 and p["rate"] == 0.5
    assert p["wilson_lower"] < 0.5, "an excerpt nobody could read as the failure was counted for it"


def test_labels_must_match_the_recorded_sample(pbrain):
    row = _sampled(pbrain, n_sample=10)
    with pytest.raises(ValueError, match="different set"):
        PR.label(pbrain, row["proposal_id"], [True] * 7)


def test_too_few_labels_cannot_establish_precision(pbrain):
    row = _sampled(pbrain, n_sample=3)
    with pytest.raises(ValueError, match="at least 5"):
        PR.label(pbrain, row["proposal_id"], [True, True, True])


def test_junk_labels_are_refused(pbrain):
    row = _sampled(pbrain)
    with pytest.raises(ValueError, match="true, false, or null"):
        PR.label(pbrain, row["proposal_id"], ["yes"] * 10)


def test_a_proposal_that_does_not_require_precision_is_unaffected(pbrain):
    """Tickets and older callers never asked for it; they must not start being blocked."""
    row = _sampled(pbrain, required=False)
    assert PR.accept(pbrain, row["proposal_id"])["status"] == "accepted"


def test_a_small_lucky_sample_does_not_clear_the_gate(pbrain):
    """3 of 5 is 60% raw -- above the 50% bar -- but its lower bound is ~23%.

    Gating on the raw rate would let five lucky labels accept a pattern that may
    mostly misfire. This is the test that separates the two.
    """
    row = _sampled(pbrain, n_sample=5)
    proposals_row = PR.label(pbrain, row["proposal_id"], [True] * 3 + [False] * 2)
    assert proposals_row["evidence"]["precision"]["rate"] == 0.6
    with pytest.raises(ValueError, match="only 3 of 5"):
        PR.accept(pbrain, row["proposal_id"])


def test_a_larger_sample_at_the_same_rate_does_clear_it(pbrain):
    """The opposed half: 60% over 100 labels has a lower bound above 50%."""
    row = _sampled(pbrain, n_sample=100)
    PR.label(pbrain, row["proposal_id"], [True] * 70 + [False] * 30)
    assert PR.accept(pbrain, row["proposal_id"])["status"] == "accepted"
