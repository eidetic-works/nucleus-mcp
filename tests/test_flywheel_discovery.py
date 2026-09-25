"""Discovery pass — opposed pairs.

The thing being tested is a refusal, so every test here has a twin: one input
the module must accept and one it must reject. A discovery pass that only ever
proposes is indistinguishable from no verification at all.
"""

import json

import pytest

from mcp_server_nucleus.flywheel import proposals
from mcp_server_nucleus.flywheel.discovery import Candidate, discover, verify


def _corpus(tmp_path, sessions):
    """Write transcripts: {session_id: [line, ...]}."""
    root = tmp_path / "projects" / "proj"
    root.mkdir(parents=True, exist_ok=True)
    for sid, lines in sessions.items():
        # The REAL transcript shape, measured on the live corpus: text lives in
        # message.content as typed blocks, never in a top-level "text" field.
        rows = [
            json.dumps({"type": "assistant",
                        "message": {"content": [{"type": "text", "text": ln}]}})
            for ln in lines
        ]
        (root / f"{sid}.jsonl").write_text("\n".join(rows) + "\n")
    return [tmp_path / "projects"]


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / "brain"
    b.mkdir()
    return b


# --- MUST PROPOSE ----------------------------------------------------------

def test_a_pattern_the_corpus_supports_becomes_a_proposal(tmp_path, brain):
    roots = _corpus(tmp_path, {
        "s1": ["the widget exploded during boot"],
        "s2": ["again: the widget exploded"],
        "s3": ["unrelated chatter"],
    })
    d = verify([Candidate(pattern="widget exploded", memory="widgets explode at boot")],
               brain_path=brain, roots=roots)
    assert len(d.proposed) == 1
    pv = d.proposed[0].prevalence
    assert pv.sessions_matched == 2
    assert pv.complete is True
    assert len(proposals.pending(brain)) == 1


def test_insufficient_evidence_is_still_proposed_and_the_accept_gate_refuses_it(tmp_path, brain):
    """Something noticed but uncheckable must not vanish silently."""
    roots = [tmp_path / "does-not-exist"]
    d = verify([Candidate(pattern="widget exploded", memory="widgets explode")],
               brain_path=brain, roots=roots)
    assert len(d.proposed) == 1, "an unverifiable finding was dropped instead of surfaced"
    assert d.proposed[0].prevalence.complete is False
    pid = d.proposed[0].proposal_id
    with pytest.raises(ValueError, match="INSUFFICIENT"):
        proposals.accept(brain, pid)


# --- MUST REFUSE -----------------------------------------------------------

def test_a_degenerate_pattern_is_refused_before_it_is_ever_counted(tmp_path, brain):
    """``.*`` would report maximum prevalence while meaning nothing."""
    roots = _corpus(tmp_path, {"s1": ["anything"], "s2": ["anything else"]})
    d = verify([Candidate(pattern=".*", memory="everything is broken")],
               brain_path=brain, roots=roots)
    assert d.proposed == []
    assert "empty string" in d.refused[0].refused
    assert proposals.pending(brain) == []


def test_an_invalid_regex_is_refused_not_raised(tmp_path, brain):
    roots = _corpus(tmp_path, {"s1": ["x"]})
    d = verify([Candidate(pattern="[unclosed", memory="m")], brain_path=brain, roots=roots)
    assert d.proposed == []
    assert "not a usable regex" in d.refused[0].refused


def test_a_pattern_the_corpus_does_not_support_is_refused(tmp_path, brain):
    roots = _corpus(tmp_path, {"s1": ["nothing relevant here"]})
    d = verify([Candidate(pattern="zzqx never appears", memory="m")],
               brain_path=brain, roots=roots, min_sessions=1)
    assert d.proposed == []
    assert "below the floor" in d.refused[0].refused


def test_a_pattern_without_a_proposed_memory_is_refused(tmp_path, brain):
    roots = _corpus(tmp_path, {"s1": ["widget exploded"]})
    d = verify([Candidate(pattern="widget exploded", memory="  ")],
               brain_path=brain, roots=roots)
    assert d.proposed == []
    assert "not a finding" in d.refused[0].refused


# --- THE CENTRAL REFUSAL: the agent does not get to supply numbers ---------

def test_a_count_the_agent_asserts_cannot_reach_the_proposal(tmp_path, brain):
    """The agent may notice. It may not count.

    A candidate carrying its own confident number must have no effect: the
    proposal's evidence is what this module measured, not what it was told.
    """
    roots = _corpus(tmp_path, {
        "s1": ["the widget exploded"],
        "s2": ["the widget exploded again"],
    })
    liar = Candidate(
        pattern="widget exploded",
        memory="widgets explode",
        rationale="I counted 99 sessions and I am certain",
    )
    d = verify([liar], brain_path=brain, roots=roots)
    row = proposals.pending(brain)[0]
    assert row["evidence"]["sessions_matched"] == 2, "an asserted count reached the record"
    assert "99" not in json.dumps(row["evidence"]), "the agent's number leaked into evidence"


def test_candidate_has_no_field_to_assert_a_count_with():
    """Structural, not behavioural: the door is not there to be left open."""
    assert not any(
        f in Candidate.__dataclass_fields__
        for f in ("count", "sessions", "prevalence", "sessions_matched", "frequency")
    )


# --- the injected discoverer -----------------------------------------------

def test_a_failing_discoverer_damages_nothing(brain):
    def boom():
        raise RuntimeError("vendor lane died at 1800s idle")

    d = discover(boom, brain_path=brain)
    assert d.proposed == []
    assert "the discovering agent failed" in d.refused[0].refused
    assert proposals.pending(brain) == []


def test_a_discoverer_returning_nothing_is_not_an_error(brain):
    d = discover(lambda: [], brain_path=brain)
    assert d.verdicts == []
    assert "proposed nothing" in d.summary()


def test_discovery_runs_over_engrams_too(tmp_path, brain):
    """The lane corpus, now that writes carry a session (item 60)."""
    from nucleus_wedge.store import Store

    st = Store(tmp_path / "b2")
    st.append(value="the widget exploded", key="a", session="s-1")
    st.append(value="the widget exploded", key="b", session="s-2")
    hist = tmp_path / "b2" / "engrams" / "history.jsonl"
    d = verify([Candidate(pattern="widget exploded", memory="widgets explode")],
               brain_path=brain, over_engrams=True, history_path=hist)
    assert len(d.proposed) == 1
    assert d.proposed[0].prevalence.sessions_matched == 2


# --- the reading sample ----------------------------------------------------

def test_gather_batch_reports_when_it_sampled(tmp_path):
    from mcp_server_nucleus.flywheel.discovery import gather_batch

    roots = _corpus(tmp_path, {f"s{i}": [f"line {i}"] for i in range(5)})
    full = gather_batch(roots=roots, max_sessions=10)
    assert full.sessions_available == 5 and full.sampled is False
    part = gather_batch(roots=roots, max_sessions=2)
    assert part.sampled is True, "a capped batch claimed to be the whole corpus"
    assert len(part.excerpts) == 2
    assert part.sessions_available == 5


def test_gather_batch_prompt_names_each_session(tmp_path):
    from mcp_server_nucleus.flywheel.discovery import gather_batch

    roots = _corpus(tmp_path, {"sA": ["the widget exploded"]})
    text = gather_batch(roots=roots).as_prompt()
    assert "session sA" in text and "widget exploded" in text


def test_extractor_handles_every_real_content_shape():
    """The shapes actually present in the live corpus, not the guessed one."""
    from mcp_server_nucleus.flywheel.discovery import _texts_from_row

    assert _texts_from_row({"message": {"content": "plain string body"}}) == ["plain string body"]
    assert _texts_from_row(
        {"message": {"content": [{"type": "text", "text": "block body"}]}}
    ) == ["block body"]
    assert _texts_from_row(
        {"message": {"content": [{"type": "tool_result", "content": "result body"}]}}
    ) == ["result body"]
    # a top-level "text" field does not exist in the corpus and must not be invented
    assert _texts_from_row({"text": "not where text lives"}) == []
    # malformed rows are skipped, never raised
    assert _texts_from_row({"message": {"content": [None, 7]}}) == []
    assert _texts_from_row({}) == []


# --- holes found by the FIRST LIVE RUN, not by a planted test --------------

def test_a_pattern_matching_nearly_every_session_is_refused(tmp_path, brain):
    """The first live run scored a candidate 200 of 200 and proposed it.

    It was not degenerate in the empty-string sense, so the mechanical guard
    let it through, yet it distinguished nothing.
    """
    roots = _corpus(tmp_path, {f"s{i}": ["the status was ok"] for i in range(12)})
    d = verify([Candidate(pattern="status.{0,20}ok", memory="statuses are ok")],
               brain_path=brain, roots=roots)
    assert d.proposed == []
    assert "saturation ceiling" in d.refused[0].refused
    assert proposals.pending(brain) == []


def test_a_pattern_matching_a_minority_is_still_proposed(tmp_path, brain):
    """The opposed half: saturation must not swallow a real finding."""
    sessions = {f"q{i}": ["ordinary unremarkable work"] for i in range(12)}
    sessions["hit1"] = ["the widget exploded"]
    sessions["hit2"] = ["the widget exploded again"]
    roots = _corpus(tmp_path, sessions)
    d = verify([Candidate(pattern="widget exploded", memory="widgets explode")],
               brain_path=brain, roots=roots)
    assert len(d.proposed) == 1
    assert d.proposed[0].prevalence.sessions_matched == 2


def test_saturation_is_not_applied_to_a_tiny_corpus(tmp_path, brain):
    """2 of 2 is 100% but says nothing about saturation."""
    roots = _corpus(tmp_path, {"s1": ["widget exploded"], "s2": ["widget exploded"]})
    d = verify([Candidate(pattern="widget exploded", memory="widgets explode")],
               brain_path=brain, roots=roots)
    assert len(d.proposed) == 1


def test_verify_scans_with_batch_caps_not_the_interactive_defaults(tmp_path, brain):
    """The dead-on-arrival bug: interactive caps made every reading INSUFFICIENT.

    `scan` defaults to 200 sessions / 8 MB against a 4,735-transcript, 3.54 GB
    corpus, so nothing could ever be accepted.
    """
    from mcp_server_nucleus.flywheel import discovery as disc

    seen = {}
    real = disc.scan_many

    def spy(patterns, **kw):
        seen.update(kw)
        seen["calls"] = seen.get("calls", 0) + 1
        seen["patterns"] = list(patterns)
        return real(patterns, **kw)

    disc.scan_many = spy
    try:
        roots = _corpus(tmp_path, {"s1": ["widget exploded gadget melted"],
                                   "s2": ["widget exploded"]})
        verify([Candidate(pattern="widget exploded", memory="m1"),
                Candidate(pattern="gadget melted", memory="m2")],
               brain_path=brain, roots=roots)
    finally:
        disc.scan_many = real

    assert seen["max_sessions"] >= 4735, "would cap below the live corpus"
    assert seen["max_bytes"] > 3.54 * 1e9, "would cap below the live corpus bytes"
    assert seen["calls"] == 1, "the corpus was read more than once"
    assert len(seen["patterns"]) == 2, "patterns were not batched into one pass"


def test_an_unusable_candidate_never_costs_a_corpus_read(tmp_path, brain):
    """Refusals that need no corpus must happen before any scan."""
    from mcp_server_nucleus.flywheel import discovery as disc

    calls = []
    real = disc.scan_many
    disc.scan_many = lambda patterns, **kw: (calls.append(1), real(patterns, **kw))[1]
    try:
        roots = _corpus(tmp_path, {"s1": ["x"]})
        d = verify([Candidate(pattern="[bad", memory="m"),
                    Candidate(pattern=".*", memory="m"),
                    Candidate(pattern="ok", memory="")],
                   brain_path=brain, roots=roots)
    finally:
        disc.scan_many = real

    assert len(d.refused) == 3
    assert calls == [], "the corpus was read for candidates that could not be used"


# --- a repeat pass must not re-propose what was already decided ------------

def _one(tmp_path, brain, pattern="widget exploded", memory="widgets explode"):
    roots = _corpus(tmp_path, {f"s{i}": ["widget exploded"] for i in range(1, 7)})
    return verify([Candidate(pattern=pattern, memory=memory)],
                  brain_path=brain, roots=roots), roots


def test_a_second_pass_does_not_re_propose_a_pending_finding(tmp_path, brain):
    """A pass gated on accumulated activity re-reads sessions an earlier pass saw."""
    _one(tmp_path, brain)
    assert len(proposals.all_proposals(brain)) == 1
    d2, _ = _one(tmp_path, brain)
    assert d2.proposed == []
    assert "already pending" in d2.refused[0].refused
    assert len(proposals.all_proposals(brain)) == 1, "the same finding was recorded twice"


def test_a_second_pass_does_not_re_propose_an_accepted_finding(tmp_path, brain):
    """The decisive one: accepting twice writes the memory twice."""
    d1, _ = _one(tmp_path, brain)
    pid = d1.proposed[0].proposal_id
    n = len(proposals.pending(brain)[0]["evidence"]["sample"])
    proposals.label(brain, pid, [True] * n)
    proposals.accept(brain, pid)
    hist = brain / "engrams" / "history.jsonl"
    after_first = len(hist.read_text().splitlines())

    d2, _ = _one(tmp_path, brain)
    assert d2.proposed == []
    assert "already accepted" in d2.refused[0].refused
    assert len(hist.read_text().splitlines()) == after_first, (
        "a repeat pass wrote the same memory a second time"
    )


def test_a_rejected_finding_is_not_proposed_again_every_pass(tmp_path, brain):
    d1, _ = _one(tmp_path, brain)
    proposals.reject(brain, d1.proposed[0].proposal_id, reason="not useful")
    d2, _ = _one(tmp_path, brain)
    assert d2.proposed == []
    assert "already rejected" in d2.refused[0].refused


def test_a_genuinely_new_finding_still_gets_through(tmp_path, brain):
    """The opposed half: the guard must not freeze the loop."""
    _one(tmp_path, brain)
    roots = _corpus(tmp_path, {"s1": ["widget exploded"], "s2": ["gadget melted"],
                               "s3": ["gadget melted"]})
    d = verify([Candidate(pattern="gadget melted", memory="gadgets melt")],
               brain_path=brain, roots=roots)
    assert len(d.proposed) == 1


def test_gather_batch_can_read_the_oldest_slice(tmp_path):
    import os, time
    from mcp_server_nucleus.flywheel.discovery import gather_batch

    roots = _corpus(tmp_path, {"old": ["from long ago"], "new": ["from today"]})
    base = tmp_path / "projects" / "proj"
    os.utime(base / "old.jsonl", (time.time() - 9e6,) * 2)
    newest = gather_batch(roots=roots, max_sessions=1)
    oldest = gather_batch(roots=roots, max_sessions=1, oldest=True)
    assert newest.excerpts[0]["session"] == "new"
    assert oldest.excerpts[0]["session"] == "old", "oldest=True read the newest slice"


# --- unbounded wildcards ---------------------------------------------------

@pytest.mark.parametrize("pat", [
    "fixture.*skip", "a.+b", "(x|y.*z)w", "abc(?:d.*e)f", "foo.{0,5000}bar",
])
def test_an_unbounded_or_huge_wildcard_gap_is_refused(tmp_path, brain, pat):
    roots = _corpus(tmp_path, {"s1": ["fixture skip"], "s2": ["fixture skip"]})
    d = verify([Candidate(pattern=pat, memory="m")], brain_path=brain, roots=roots)
    assert d.proposed == []
    assert "Bound the gap" in d.refused[0].refused


@pytest.mark.parametrize("pat", [
    "fixture.{0,60}skip", r"literal\.\*dot", "[.*]bracket", "widget exploded",
])
def test_a_bounded_gap_or_an_escaped_dot_is_not_refused(tmp_path, brain, pat):
    """The opposed half: the guard must not swallow legitimate patterns."""
    from mcp_server_nucleus.flywheel.discovery import _unbounded_wildcard
    assert _unbounded_wildcard(pat) is None, pat
