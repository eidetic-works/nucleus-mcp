"""A ticket should carry evidence, not an assertion.

349 tickets on disk say some version of "this broke." None says in how many
sessions, or points at one. `prevalence.scan` can now answer that; this wires it
into the filing path so the answer travels with the ticket.

FOUR THINGS THIS MUST NOT DO:

  1. NOT SCAN BY DEFAULT. There are 4,728 transcripts here. A scan on every
     ticket would make filing cost minutes. Evidence is opt-in via a pattern.

  2. NOT BLOCK FILING. The whole file_ticket contract is "all actions are
     best-effort; one failing does not block the others." A scan that throws
     must lose the evidence, never the ticket.

  3. NOT PRESENT A CAPPED COUNT AS A FACT. If the scan hit a cap, the ticket
     must carry INSUFFICIENT rather than a bare number — otherwise the ticket
     launders a partial reading into a statistic, which is the exact failure
     the prevalence module refuses to commit.

  4. NOT LEAK THE OPERATOR'S HOME PATH. Citations carry absolute transcript
     paths. Every other field in this record goes through `_scrub_home_paths`;
     evidence must too, or attaching evidence would quietly defeat a guard the
     repo already has.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server_nucleus.flywheel.core import Flywheel


def _tickets(brain):
    f = brain / "flywheel" / "pending_issues.jsonl"
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


@pytest.fixture()
def corpus(tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    for name, lines in [
        ("aaaaaaaa-0000-0000-0000-000000000001", ["lock timeout hit"]),
        ("bbbbbbbb-0000-0000-0000-000000000002", ["all fine"]),
        ("cccccccc-0000-0000-0000-000000000003", ["lock timeout hit"]),
    ]:
        # Real transcript shape (message.content). Plain-text fixtures only
        # worked while scan regexed raw JSONL and counted boilerplate.
        (d / f"{name}.jsonl").write_text("\n".join(
            json.dumps({"type": "assistant",
                        "message": {"content": [{"type": "text", "text": ln}]}})
            for ln in lines) + "\n")
    return d


@pytest.fixture()
def fw(tmp_path):
    return Flywheel(brain_path=tmp_path / ".brain")


# ── backward compatibility: the default path must not change ───────────────


def test_a_ticket_without_a_pattern_carries_no_evidence(fw, tmp_path):
    """CONTROL. 349 existing callers pass no pattern and must be untouched."""
    fw.file_ticket(step="s", error="boom")
    t = _tickets(tmp_path / ".brain")[0]
    assert "evidence" not in t


def test_filing_without_a_pattern_does_not_scan(fw, tmp_path, monkeypatch):
    """Scanning 4,728 transcripts on every ticket would make filing cost
    minutes. Proven by making a scan fatal if it happens at all."""
    from mcp_server_nucleus.flywheel import prevalence
    monkeypatch.setattr(prevalence, "scan",
                        lambda *a, **k: pytest.fail("scanned without a pattern"))
    fw.file_ticket(step="s", error="boom")


# ── evidence travels with the ticket ───────────────────────────────────────


def test_a_pattern_attaches_a_prevalence_reading(fw, tmp_path, corpus):
    fw.file_ticket(step="s", error="lock timeout",
                   evidence_pattern="lock timeout hit", evidence_roots=[corpus])
    e = _tickets(tmp_path / ".brain")[0]["evidence"]
    assert e["sessions_matched"] == 2 and e["sessions_scanned"] == 3
    assert e["complete"] is True


def test_evidence_carries_citations(fw, tmp_path, corpus):
    fw.file_ticket(step="s", error="lock timeout",
                   evidence_pattern="lock timeout hit", evidence_roots=[corpus])
    ex = _tickets(tmp_path / ".brain")[0]["evidence"]["examples"]
    assert ex and ex[0]["session"] and ex[0]["line"] >= 1


def test_evidence_summary_states_the_number_when_complete(fw, tmp_path, corpus):
    fw.file_ticket(step="s", error="lock timeout",
                   evidence_pattern="lock timeout hit", evidence_roots=[corpus])
    assert "2 of 3" in _tickets(tmp_path / ".brain")[0]["evidence"]["summary"]


# ── the refusals ───────────────────────────────────────────────────────────


def test_a_capped_scan_is_recorded_as_insufficient(fw, tmp_path, corpus):
    """THE control. A partial reading must not reach the ticket as a statistic."""
    fw.file_ticket(step="s", error="lock timeout", evidence_pattern="lock timeout hit",
                   evidence_roots=[corpus], evidence_max_sessions=1)
    e = _tickets(tmp_path / ".brain")[0]["evidence"]
    assert e["complete"] is False
    assert "INSUFFICIENT" in e["summary"]
    assert "2 of 3" not in e["summary"]


def test_a_failing_scan_loses_the_evidence_not_the_ticket(fw, tmp_path, monkeypatch):
    from mcp_server_nucleus.flywheel import prevalence

    def boom(*a, **k):
        raise RuntimeError("transcript store unreachable")

    monkeypatch.setattr(prevalence, "scan", boom)
    fw.file_ticket(step="s", error="boom", evidence_pattern="anything")
    t = _tickets(tmp_path / ".brain")[0]
    assert t["error"], "the ticket itself must survive"
    assert t.get("evidence", {}).get("complete") is not True


def test_citations_do_not_leak_the_home_path(fw, tmp_path):
    """Every other field goes through _scrub_home_paths. Attaching evidence must
    not quietly defeat a guard this repo already has.

    THE CORPUS MUST LIVE UNDER THE REAL $HOME. The first version of this test
    used the `corpus` fixture under pytest's tmp_path (/private/var/...), which
    contains no home prefix — so `_scrub_home_paths` had nothing to remove and
    the assertion could not fail. Deleting the scrub left it green. A correct
    check over a set that cannot contain the evidence, inside the control meant
    to catch exactly that.
    """
    import shutil, uuid

    home_corpus = Path.home() / ".cache" / f"nucleus-evidence-test-{uuid.uuid4().hex[:8]}"
    home_corpus.mkdir(parents=True)
    try:
        (home_corpus / "aaaaaaaa-0000-0000-0000-000000000001.jsonl").write_text(
            json.dumps({"type": "assistant",
                        "message": {"content": [{"type": "text",
                                                 "text": "lock timeout hit"}]}}) + "\n"
        )
        fw.file_ticket(step="s", error="lock timeout",
                       evidence_pattern="lock timeout hit", evidence_roots=[home_corpus])
        blob = json.dumps(_tickets(tmp_path / ".brain")[0])
        assert str(Path.home()) not in blob, "an absolute home path reached the ticket"
        assert "~/" in blob, "the scrub did not run at all — this test would be vacuous"
    finally:
        shutil.rmtree(home_corpus, ignore_errors=True)


# ── the wiring: a signature only when one can be trusted ───────────────────
# `evidence_pattern` existed with 0 callers, so tickets still asserted. Wiring
# it up means deciding WHAT pattern a ticket should carry, and that is the whole
# difficulty: an auto-derived regex over free prose either over-matches every
# ticket or matches nothing, and both produce a confident wrong prevalence —
# the exact failure this evidence machinery exists to prevent.
#
# So `error_signature` returns None for anything it cannot pin down, and a
# ticket with no signature simply carries no evidence. No signature is a fine
# outcome; a junk one is not.

from mcp_server_nucleus.flywheel.core import error_signature, file_ticket as file_ticket_fn


def test_signature_of_an_exception_keeps_type_and_message():
    sig = error_signature("TypeError: '<' not supported between instances of 'str' and 'int'")
    assert sig and "TypeError" in sig


def test_signature_drops_the_variable_tail():
    """Two occurrences of the same bug differ after the em dash."""
    a = error_signature("TypeError: bad compare — status_dashboard fails on dispatch")
    b = error_signature("TypeError: bad compare — slots view fails on dispatch")
    assert a == b, "the signature must survive a differing tail"


def test_signature_normalises_digits_and_hex():
    a = error_signature("ValueError: no loop with id 41")
    b = error_signature("ValueError: no loop with id 907")
    assert a == b


def test_free_prose_gets_no_signature():
    """THE control. Prose has no stable head, so there is nothing safe to match."""
    assert error_signature(
        "Antigravity did not receive automatic relay push notifications for relays sent by cc"
    ) is None


def test_empty_error_gets_no_signature():
    assert error_signature("") is None and error_signature(None) is None


def test_a_signature_is_a_usable_regex():
    import re
    sig = error_signature("KeyError: 'session' missing from snapshot 12")
    re.compile(sig)  # must not raise
    assert re.search(sig, "KeyError: 'session' missing from snapshot 99")


# ── the silent param drop ──────────────────────────────────────────────────


def test_the_module_level_wrapper_forwards_evidence_pattern(tmp_path, corpus, monkeypatch):
    """core.file_ticket() listed evidence_pattern nowhere in the kwargs it
    forwarded, so any caller using the convenience wrapper had its argument
    silently discarded — the shape that makes a feature look wired when it is
    not."""
    seen = {}
    from mcp_server_nucleus.flywheel import core as core_mod

    real = core_mod.Flywheel.file_ticket

    def spy(self, **kw):
        seen.update(kw)
        return real(self, **kw)

    monkeypatch.setattr(core_mod.Flywheel, "file_ticket", spy)
    file_ticket_fn(step="s", error="boom", brain_path=tmp_path / ".brain",
                   evidence_pattern="lock timeout hit", evidence_roots=[corpus])
    assert seen.get("evidence_pattern") == "lock timeout hit", (
        f"the wrapper dropped it; forwarded kwargs were {sorted(seen)}"
    )
