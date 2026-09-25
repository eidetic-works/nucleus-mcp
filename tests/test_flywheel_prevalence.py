"""Prevalence: how many SESSIONS a pattern appears in, and which ones.

The flywheel files tickets. 349 of them on disk, each a single-session
assertion: "this broke." None of them can say how often, or in how many
sessions, or point at one. Lamis Mukta's talk names that gap precisely -- a
dreaming pass proposes a memory change together with "examples of transcripts
where it's noticed this pattern has happened and also some stats on how
prevalent this issue is." Evidence, not attestation.

TWO THINGS THIS MODULE REFUSES TO DO, both of which are this repo's own
recurring failure:

  1. IT WILL NOT REPORT A COUNT OVER A SET IT COULD NOT FULLY SEE. There are
     4,728 transcripts on this machine and the largest is 815 MB. Any scan is
     necessarily capped, and a capped scan that returns "2 sessions" reads
     identically to a complete one. So hitting a cap yields INSUFFICIENT, and
     `sessions_matched` is not to be quoted without `complete`. This is the
     crit3 lesson: 1,021 envelopes, 0 qualifying BY CONSTRUCTION, and a gate
     that read the zero as an answer.

  2. IT WILL NOT CONFLATE FREQUENCY WITH PREVALENCE. A pattern appearing fifty
     times in one session is ONE session, not fifty. Frequency in a single
     transcript is how an agent's own repetition gets laundered into evidence
     of a widespread problem.

Session identity is the FILENAME (a uuid), not a parsed field -- free, and
correct even for a truncated or corrupt file.
"""
from __future__ import annotations

import json

import pytest

from mcp_server_nucleus.flywheel import prevalence as P


def _session(root, name, lines):
    f = root / f"{name}.jsonl"
    # The REAL transcript shape. A top-level "text" field does not exist in the
    # corpus; text lives in message.content. Fixtures that invented one only
    # passed because scan used to regex the raw JSONL line, which is the bug
    # these tests now guard against.
    f.write_text("\n".join(
        json.dumps({"type": "assistant",
                    "message": {"content": [{"type": "text", "text": t}]}})
        for t in lines) + "\n")
    return f


@pytest.fixture()
def corpus(tmp_path):
    """5 sessions; the needle is in 3 of them."""
    d = tmp_path / "projects" / "proj"
    d.mkdir(parents=True)
    _session(d, "aaaaaaaa-0000-0000-0000-000000000001", ["boot", "timeout waiting for lock", "done"])
    _session(d, "bbbbbbbb-0000-0000-0000-000000000002", ["boot", "all good"])
    _session(d, "cccccccc-0000-0000-0000-000000000003", ["timeout waiting for lock"])
    _session(d, "dddddddd-0000-0000-0000-000000000004", ["nothing to see"])
    _session(d, "eeeeeeee-0000-0000-0000-000000000005", ["timeout waiting for lock", "again"])
    return d


# ── the number, and what it means ──────────────────────────────────────────


def test_counts_distinct_sessions_not_hits(corpus):
    r = P.scan(r"timeout waiting for lock", roots=[corpus])
    assert r.sessions_matched == 3
    assert r.sessions_scanned == 5


def test_frequency_in_one_session_is_still_one_session(tmp_path):
    """THE control against laundering repetition into prevalence."""
    d = tmp_path / "p"; d.mkdir()
    _session(d, "ffffffff-0000-0000-0000-000000000006", ["boom"] * 50)
    r = P.scan(r"boom", roots=[d])
    assert r.sessions_matched == 1, "50 hits in one session is one session"


def test_examples_cite_a_file_and_a_line(corpus):
    r = P.scan(r"timeout waiting for lock", roots=[corpus])
    assert r.examples, "a prevalence claim with no citable example is an assertion"
    e = r.examples[0]
    assert e["session"].startswith(("aaaa", "cccc", "eeee"))
    assert e["line"] >= 1 and "timeout" in e["excerpt"]


def test_session_id_comes_from_the_filename(corpus):
    r = P.scan(r"timeout waiting for lock", roots=[corpus])
    assert all(len(e["session"]) == 36 for e in r.examples)


def test_no_match_is_a_real_zero_when_the_scan_was_complete(corpus):
    r = P.scan(r"this string appears nowhere", roots=[corpus])
    assert r.sessions_matched == 0 and r.complete is True


def test_absence_names_the_set_it_is_absent_from(corpus):
    """Measured in the wild: scanning one project reported '0 of 5, a real
    absence' for a string that HAD occurred minutes earlier -- a session's
    transcript lives under the project it STARTED in, not where it is working.
    The check was correct over a set that could not contain the evidence."""
    r = P.scan(r"nowhere at all", roots=[corpus])
    s = r.summary()
    assert corpus.name in s, f"absence claim does not name its roots: {s}"
    assert "real absence" not in s, "an unqualified 'real absence' overclaims"


# ── the third state ────────────────────────────────────────────────────────


def test_nothing_to_scan_is_insufficient_not_zero(tmp_path):
    """0 of 0 is not evidence of absence. It is evidence of nothing."""
    empty = tmp_path / "empty"; empty.mkdir()
    r = P.scan(r"anything", roots=[empty])
    assert r.complete is False
    assert r.insufficient_reason and "no transcript" in r.insufficient_reason.lower()


def test_hitting_the_file_cap_is_insufficient(corpus):
    """A capped scan that found matches still cannot report a prevalence."""
    r = P.scan(r"timeout waiting for lock", roots=[corpus], max_sessions=2)
    assert r.sessions_scanned == 2
    assert r.complete is False
    assert "cap" in (r.insufficient_reason or "").lower()


def test_a_complete_scan_says_so(corpus):
    r = P.scan(r"timeout waiting for lock", roots=[corpus], max_sessions=99)
    assert r.complete is True and r.insufficient_reason is None


def test_summary_never_states_a_bare_number_when_incomplete(corpus):
    r = P.scan(r"timeout waiting for lock", roots=[corpus], max_sessions=2)
    s = r.summary()
    assert "INSUFFICIENT" in s
    assert "3 of 5" not in s


def test_summary_states_the_number_when_complete(corpus):
    r = P.scan(r"timeout waiting for lock", roots=[corpus])
    assert "3 of 5" in r.summary()


# ── robustness on a real corpus ────────────────────────────────────────────


def test_an_unreadable_file_does_not_abort_the_scan(corpus):
    bad = corpus / "99999999-0000-0000-0000-000000000009.jsonl"
    bad.write_bytes(b"\xff\xfe not utf-8 \x00")
    r = P.scan(r"timeout waiting for lock", roots=[corpus])
    assert r.sessions_matched == 3
    assert r.sessions_scanned >= 5


def test_a_file_over_the_byte_cap_is_skipped_and_flagged(corpus):
    """815 MB transcripts exist. Reading one to answer a question is the wrong
    trade; skipping it silently is worse."""
    big = corpus / "88888888-0000-0000-0000-000000000008.jsonl"
    big.write_text("x" * 5000 + "\n" + json.dumps(
        {"type": "assistant",
         "message": {"content": [{"type": "text", "text": "timeout waiting for lock"}]}}) + "\n")
    r = P.scan(r"timeout waiting for lock", roots=[corpus], max_bytes=1000)
    assert r.complete is False
    assert "skipped" in (r.insufficient_reason or "").lower()


def test_scan_streams_rather_than_loading(corpus):
    """Guards against a future refactor to read_text(): a 815 MB file must not
    be materialised to answer a regex question."""
    import inspect
    src = inspect.getsource(P)
    assert ".read_text()" not in src, "prevalence must stream, never slurp"


# ── the engram history log: a second kind of source ────────────────────────
#
# `.brain/engrams/history.jsonl` is one file holding cross-vendor agent
# activity (30,749 rows on this machine). It is NOT one session per line:
# only 26 of those rows carry `snapshot.origin.session`. A row counter is not
# a session count and must never be reported as one.


def _engram(value, *, session=None, agent="devin", ts="2026-09-20T00:00:00Z"):
    snap = {"value": value, "source_agent": agent, "timestamp": ts}
    if session is not None:
        # ``session_source`` is what makes the id countable: an env-derived
        # id comes from a process whose env froze at spawn, so prevalence
        # refuses it. See test_wedge_session_attribution.py.
        snap["origin"] = {"session": session, "session_source": "explicit"}
    return {"snapshot": snap, "timestamp": ts}


def _history(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


@pytest.fixture()
def engram_log(tmp_path):
    return tmp_path / "history.jsonl"


def test_engram_rows_with_sessions_count_as_sessions(engram_log):
    """Rows that DO carry origin.session give a real distinct-session count."""
    _history(engram_log, [
        _engram("timeout waiting for lock", session="sess-aaaa"),
        _engram("nothing relevant"),
        _engram("timeout waiting for lock", session="sess-bbbb"),
    ])
    r = P.scan_engrams(r"timeout waiting for lock", history_path=engram_log)
    assert r.sessions_matched == 2
    assert r.unattributed_matches == 0
    assert r.complete is True


def test_engram_matches_without_sessions_are_insufficient(engram_log):
    """A match with no session id cannot be attributed to a session; the log
    does not record one for most rows, so no session count is available."""
    _history(engram_log, [
        _engram("timeout waiting for lock", agent="devin"),
        _engram("timeout waiting for lock", agent="agy"),
    ])
    r = P.scan_engrams(r"timeout waiting for lock", history_path=engram_log)
    assert r.unattributed_matches == 2
    assert r.sessions_matched == 0
    assert r.complete is False
    assert "session" in (r.insufficient_reason or "").lower()
    s = r.summary()
    assert "INSUFFICIENT" in s
    assert "sessions. e.g." not in s, "the complete-branch number must not print"
    # examples cite the lane and the timestamp -- there is no per-session file
    e = r.examples[0]
    assert e["source_agent"] == "devin" and e["timestamp"]


def test_one_unattributed_match_spoils_the_count(engram_log):
    """Two attributed + one unattributed match: the count is still unknowable,
    because the unattributed row may be a third session -- or a repeat."""
    _history(engram_log, [
        _engram("needle", session="sess-aaaa"),
        _engram("needle"),
        _engram("needle", session="sess-bbbb"),
    ])
    r = P.scan_engrams(r"needle", history_path=engram_log)
    assert r.sessions_matched == 2
    assert r.unattributed_matches == 1
    assert r.complete is False


def test_a_malformed_line_does_not_abort_the_engram_scan(engram_log):
    engram_log.write_text(
        json.dumps(_engram("needle", session="sess-aaaa")) + "\n"
        + "this is not json\n"
        + json.dumps(_engram("needle", session="sess-bbbb")) + "\n"
    )
    r = P.scan_engrams(r"needle", history_path=engram_log)
    assert r.sessions_matched == 2
    assert r.skipped, "an unparseable row is recorded, not silently eaten"


def test_a_missing_history_log_is_insufficient_not_zero(tmp_path):
    """Same refusal as an empty roots dir: 0 of 0 is evidence of nothing."""
    r = P.scan_engrams(r"needle", history_path=tmp_path / "nope.jsonl")
    assert r.complete is False
    assert "INSUFFICIENT" in r.summary()


# --- the fast path must agree with the slow one ----------------------------

def _mk_corpus(tmp_path, sessions):
    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True)
    for sid, lines in sessions.items():
        (root / f"{sid}.jsonl").write_text("\n".join(
            json.dumps({"type": "assistant",
                        "message": {"content": [{"type": "text", "text": ln}]}})
            for ln in lines) + "\n")
    return [tmp_path / "projects"]


def test_scan_many_agrees_with_scan_for_every_pattern(tmp_path):
    """A faster path that quietly disagrees is worse than no fast path."""
    from mcp_server_nucleus.flywheel.prevalence import scan, scan_many

    roots = _mk_corpus(tmp_path, {
        "s1": ["widget exploded", "all fine"],
        "s2": ["gadget melted"],
        "s3": ["widget exploded", "gadget melted"],
        "s4": ["nothing of note"],
    })
    pats = ["widget exploded", "gadget melted", "never appears anywhere"]
    many = scan_many(pats, roots=roots)
    for pat in pats:
        one = scan(pat, roots=roots)
        assert many[pat].sessions_matched == one.sessions_matched, pat
        assert many[pat].sessions_scanned == one.sessions_scanned, pat
        assert many[pat].complete == one.complete, pat


def test_scan_many_reports_the_cap_on_every_pattern(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan_many

    roots = _mk_corpus(tmp_path, {f"s{i}": ["widget exploded"] for i in range(6)})
    many = scan_many(["widget exploded", "gadget melted"], roots=roots, max_sessions=2)
    for res in many.values():
        assert res.complete is False
        assert "session cap" in res.insufficient_reason


def test_scan_many_with_no_patterns_is_empty_not_an_error(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan_many

    assert scan_many([], roots=_mk_corpus(tmp_path, {"s1": ["x"]})) == {}


# --- the boilerplate confound ----------------------------------------------
#
# Mutation results for the two protections below, measured after a first
# attempt reported a FALSE pass:
#
#   remove the attachment guard          -> 3 of these tests red
#   restore raw-line matching            -> 1 of these tests red
#
# The first attempt claimed "mutation-verified" from a run in which nothing
# was mutated: the string replacement did not match, so the unchanged file was
# written back and the suite passed for the obvious reason. A mutation script
# must ASSERT that the mutation applied, or it is a green light wired to
# nothing -- the same shape as every other defect this module is about.

def test_a_match_only_in_an_attachment_does_not_count(tmp_path):
    """MEASURED: 80 of 120 sessions matched the raw line, 0 matched real text.

    70 were the `skill_listing` attachment -- the skill catalogue injected into
    nearly every session. A scanner reading raw JSONL measures boilerplate and
    reports it as behaviour.
    """
    from mcp_server_nucleus.flywheel.prevalence import scan

    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True)
    (root / "boiler.jsonl").write_text(json.dumps({
        "type": "user",
        "attachment": {"type": "skill_listing",
                       "content": "- widget-tools: handles widget exploded cases"},
    }) + "\n")
    (root / "real.jsonl").write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "the widget exploded"}]},
    }) + "\n")

    res = scan("widget exploded", roots=[tmp_path / "projects"])
    assert res.sessions_scanned == 2
    assert res.sessions_matched == 1, (
        "an injected skill listing was counted as a session where this happened"
    )
    assert res.examples[0]["session"] == "real"


def test_tool_schema_noise_in_a_non_message_row_does_not_count(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan

    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True)
    (root / "queue.jsonl").write_text(json.dumps({
        "type": "queue-operation", "operation": "enqueue",
        "content": "retry after widget exploded",
    }) + "\n")
    assert scan("widget exploded", roots=[tmp_path / "projects"]).sessions_matched == 0


def test_scan_many_ignores_boilerplate_exactly_as_scan_does(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan, scan_many

    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True)
    (root / "boiler.jsonl").write_text(json.dumps({
        "type": "user",
        "attachment": {"type": "skill_listing", "content": "widget exploded"},
    }) + "\n")
    (root / "real.jsonl").write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "the widget exploded"}]},
    }) + "\n")
    roots = [tmp_path / "projects"]
    assert (scan_many(["widget exploded"], roots=roots)["widget exploded"].sessions_matched
            == scan("widget exploded", roots=roots).sessions_matched == 1)


# --- excerpts must contain the match ---------------------------------------

def _deep_match_corpus(tmp_path):
    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True)
    filler = "unrelated words " * 400  # ~6 KB before the match
    (root / "s1.jsonl").write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text",
                                 "text": filler + "the widget exploded here " + filler}]},
    }) + "\n")
    return [tmp_path / "projects"]


def test_scan_excerpt_contains_a_match_buried_deep_in_a_long_message(tmp_path):
    """The old excerpt was the first 170 chars, so it showed only filler."""
    from mcp_server_nucleus.flywheel.prevalence import scan
    ex = scan("widget exploded", roots=_deep_match_corpus(tmp_path)).examples[0]["excerpt"]
    assert "widget exploded" in ex, f"excerpt does not contain the match: {ex[:80]!r}"


def test_scan_many_excerpt_contains_a_match_buried_deep_in_a_long_message(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan_many
    res = scan_many(["widget exploded"], roots=_deep_match_corpus(tmp_path))
    ex = res["widget exploded"].examples[0]["excerpt"]
    assert "widget exploded" in ex, f"excerpt does not contain the match: {ex[:80]!r}"


# --- an unbiased sample for judging precision ------------------------------

def _many_sessions(tmp_path, n, hit_every=1):
    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        txt = f"session {i} the widget exploded" if i % hit_every == 0 else f"session {i} calm"
        (root / f"s{i:03d}.jsonl").write_text(json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": txt}]}}) + "\n")
    return [tmp_path / "projects"]


def test_sample_is_bounded_and_drawn_from_matching_sessions_only(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan_many
    roots = _many_sessions(tmp_path, 60, hit_every=2)
    r = scan_many(["widget exploded"], roots=roots, sample_size=10)["widget exploded"]
    assert r.sessions_matched == 30 and len(r.sample) == 10
    assert all("widget exploded" in e["excerpt"] for e in r.sample), "a non-match was sampled"
    assert len({e["session"] for e in r.sample}) == 10, "a session was sampled twice"


def test_sample_is_not_just_the_first_matches(tmp_path):
    """`examples` takes the first few in file order; a sample must not."""
    from mcp_server_nucleus.flywheel.prevalence import scan_many
    roots = _many_sessions(tmp_path, 200)
    r = scan_many(["widget exploded"], roots=roots, sample_size=10)["widget exploded"]
    first_ten = {f"s{i:03d}" for i in range(10)}
    assert {e["session"] for e in r.sample} != first_ten, "sample is the head of the corpus"
    assert max(e["session"] for e in r.sample) > "s050", "sample never reached the later sessions"


def test_sample_is_deterministic_for_a_seed(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan_many
    roots = _many_sessions(tmp_path, 100)
    a = scan_many(["widget exploded"], roots=roots, sample_size=8, sample_seed=7)["widget exploded"]
    b = scan_many(["widget exploded"], roots=roots, sample_size=8, sample_seed=7)["widget exploded"]
    assert [e["session"] for e in a.sample] == [e["session"] for e in b.sample]


def test_no_sample_by_default(tmp_path):
    from mcp_server_nucleus.flywheel.prevalence import scan_many
    r = scan_many(["widget exploded"], roots=_many_sessions(tmp_path, 20))["widget exploded"]
    assert r.sample == []
