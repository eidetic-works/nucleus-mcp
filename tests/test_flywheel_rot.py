"""Rot, Phase 0 -- deterministic checks over memory files.

Every fixture is synthetic. The identity terms here are invented; no real string
belongs in a test file, and the real ones are read from the guard at runtime.
"""

import re
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.flywheel import rot


def _git(root, *a):
    subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"; r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.t"); _git(r, "config", "user.name", "t")
    (r / "src").mkdir()
    (r / "src" / "real.py").write_text("a\nb\nc\n")
    (r / "src" / "dup.py").write_text("x\n"); (r / "lib").mkdir(); (r / "lib" / "dup.py").write_text("y\n")
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "c1")
    (r / "untracked.py").write_text("z\n")
    return rot.Checkout(r)


def _sha(repo):
    return subprocess.run(["git", "-C", str(repo.root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def _statuses(text, repo, names=frozenset()):
    cl = rot.extract(text); rot.check(cl, [repo], set(names))
    return {c.text: c.status for c in cl}


# --- extraction ------------------------------------------------------------

def test_extract_finds_paths_lines_shas_and_links():
    kinds = {(c.kind, c.text) for c in rot.extract("see `src/a.py`, `src/b.py:12`, [[other-memory]], and abc1234def")}
    assert ("path", "src/a.py") in kinds and ("line", "src/b.py:12") in kinds
    assert ("link", "other-memory") in kinds and ("sha", "abc1234def") in kinds


def test_extract_ignores_fenced_code_and_non_shas():
    t = "```\n`src/example.py` deadbeef\n```\nplain 1234567 and deadbeef words"
    assert rot.extract(t) == [], "an example command or a plain number/word was read as a claim"


# --- checking: the opposed pairs -------------------------------------------

def test_a_live_path_is_live_and_a_dead_qualified_path_is_dead(repo):
    st = _statuses("`src/real.py` and `src/gone.py`", repo)
    assert st["src/real.py"] == rot.LIVE and st["src/gone.py"] == rot.DEAD


def test_a_bare_filename_absent_from_git_is_unresolved_never_dead(repo):
    """git ls-files cannot see untracked files, so absence there proves nothing."""
    st = _statuses("`untracked.py` and `nothing.py`", repo)
    assert st["nothing.py"] == rot.UNRESOLVED, "a bare name was declared dead from an incomplete set"
    assert st["untracked.py"] in (rot.LIVE, rot.UNRESOLVED)


def test_a_bare_filename_with_two_homes_is_ambiguous(repo):
    assert _statuses("`dup.py`", repo)["dup.py"] == rot.AMBIGUOUS


def test_a_line_reference_beyond_the_file_is_dead(repo):
    st = _statuses("`src/real.py:2` and `src/real.py:99`", repo)
    assert st["src/real.py:2"] == rot.LIVE and st["src/real.py:99"] == rot.DEAD


def test_a_reachable_sha_is_live_and_an_unknown_one_is_dead(repo):
    # A SHA prefix must contain a letter AND a digit to be read as a SHA at all; a real
    # commit's 10-char prefix is all digits about 1% of the time, which made this test flaky.
    full = _sha(repo)
    good = next(full[:n] for n in range(10, 41) if re.search(r"[a-f]", full[:n]) and re.search(r"\d", full[:n]))
    st = _statuses(f"commit {good} and commit 0a1b2c3d4e", repo)
    assert st[good] == rot.LIVE and st["0a1b2c3d4e"] == rot.DEAD


def test_links_resolve_by_stem_or_slug_and_dangling_ones_are_dead(repo):
    st = _statuses("[[exists-slug]] [[file_stem]] [[dangling]]", repo, {"exists-slug", "file_stem"})
    assert st["exists-slug"] == rot.LIVE and st["file_stem"] == rot.LIVE
    # A dangling link is ALLOWED by convention (it marks something worth writing later),
    # so it is not evidence of rot. Measured: 178 of 377 links dangle.
    assert st["dangling"] == rot.UNRESOLVED, "an allowed orphan link was counted as rot"


def test_memory_names_span_sibling_project_memory_dirs(tmp_path):
    """Measured: resolving inside one directory reported 47% of links dead."""
    for proj, stem in (("-A", "alpha_note"), ("-B", "beta_note")):
        d = tmp_path / "projects" / proj / "memory"; d.mkdir(parents=True)
        (d / f"{stem}.md").write_text(f"---\nname: {stem.replace('_', '-')}\n---\nbody")
    names = rot.memory_names(tmp_path / "projects" / "-A" / "memory")
    assert {"alpha_note", "beta-note", "beta_note"} <= names


# --- identity: must fail CLOSED --------------------------------------------

GUARD = '''patterns=(
  # a comment naming "InventedComment" must not become a term
  "Invented Name"
  "invented@example.test"
)
ci_patterns=(
  "invented-entity"
)
ci_regexes=(
  'invented[- ]llc'
)
warn_ci_patterns=(
  "warn-term"
)
'''


@pytest.fixture
def guard(tmp_path):
    g = tmp_path / "guard.sh"; g.write_text(GUARD); return g


def test_terms_are_parsed_and_comments_are_not_terms(guard):
    t = rot.identity_terms(guard)
    assert "Invented Name" in t["patterns"] and "InventedComment" not in " ".join(t["patterns"])
    assert set(t) == {"patterns", "ci_patterns", "ci_regexes", "warn_ci_patterns"}


def test_case_sensitive_terms_are_case_sensitive_and_ci_terms_are_not(guard):
    t = rot.identity_terms(guard)
    assert rot.classify_identity("x.md", "Invented Name", t)
    assert not rot.classify_identity("x.md", "invented name", t), "a case-sensitive term matched loosely"
    assert rot.classify_identity("x.md", "INVENTED-ENTITY here", t)


def test_regex_arrays_are_matched_as_regexes(guard):
    """Measured: treating them as literal text undercounted exclusions, which lets an
    identity-bearing file through to a vendor."""
    t = rot.identity_terms(guard)
    assert rot.classify_identity("x.md", "the Invented-LLC filing", t)


def test_warn_arrays_exclude_too(guard):
    assert rot.classify_identity("x.md", "warn-term", rot.identity_terms(guard))


def test_a_clean_file_is_clean(guard):
    assert rot.classify_identity("notes.md", "nothing sensitive here", rot.identity_terms(guard)) == []


def test_a_file_about_identity_is_excluded_by_name_even_without_a_term(guard):
    assert "name" in rot.classify_identity("feedback_legal_entity_thing.md", "no terms", rot.identity_terms(guard))


def test_a_broken_regex_counts_as_a_hit_not_a_pass():
    assert rot.classify_identity("x.md", "anything", {"ci_regexes": ["[unclosed"]})


def test_an_unreadable_guard_aborts_rather_than_reading_as_clean(tmp_path):
    with pytest.raises(rot.RotError, match="refusing to decide"):
        rot.load_identity_terms(tmp_path / "missing.sh")
    empty = tmp_path / "empty.sh"; empty.write_text("# nothing\n")
    with pytest.raises(rot.RotError):
        rot.load_identity_terms(empty)


# --- the integrity control -------------------------------------------------

def test_phase_zero_leaves_every_memory_file_byte_identical(tmp_path, repo):
    d = tmp_path / "projects" / "-A" / "memory"; d.mkdir(parents=True)
    (d / "one.md").write_text("`src/gone.py` [[nope]] abc1234def")
    (d / "MEMORY.md").write_text("index")
    before = rot.digest_all(d)
    for p in rot.memory_files(d):
        cl = rot.extract(p.read_text()); rot.check(cl, [repo], rot.memory_names(d))
    assert rot.digest_all(d) == before, "the audit modified a memory file"
    assert [p.name for p in rot.memory_files(d)] == ["one.md"], "the index was treated as a memory"


# --- Phase 1: prompts, controls, and the judge -----------------------------

@pytest.fixture
def world(tmp_path):
    """A tracked repo + a memory file OUTSIDE it, sharing distinctive tokens."""
    r = tmp_path / "w"; r.mkdir(); _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.t"); _git(r, "config", "user.name", "t")
    for n, tok in (("a.py", "ALPHA_TOKEN"), ("b.py", "BETA_TOKEN"), ("c.py", "GAMMA_TOKEN")):
        (r / n).write_text(f"{tok} = 1\n")
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "c")
    mem = tmp_path / "mem.md"
    mem.write_text("ALPHA_TOKEN is in a.py. BETA_TOKEN in b.py. GAMMA_TOKEN in c.py. STALE_CLAIM_TOKEN was removed.")
    return r, rot.Task("t1", str(mem), "real")


def _block(verdict, rows, task_id="t1", n=None):
    body = "\n".join(rows)
    return f"noise\nVERDICT: {verdict}\nTASK_ID: {task_id}\nCLAIMS_CHECKED: {n if n is not None else len(rows)}\n{body}\n"


GOOD_CLEAN = ["- alpha exists | TRUE | a.py:1 | ALPHA_TOKEN", "- beta exists | TRUE | b.py:1 | BETA_TOKEN",
              "- gamma exists | TRUE | c.py:1 | GAMMA_TOKEN"]


def test_a_grounded_clean_is_accepted(world):
    r, t = world
    j = rot.judge_audit(_block("CLEAN", GOOD_CLEAN), t, r)
    assert (j.verdict, j.accepted) == ("CLEAN", True), j.reason


def test_a_clean_with_too_few_rows_is_refused(world):
    r, t = world
    assert rot.judge_audit(_block("CLEAN", GOOD_CLEAN[:1], n=3), t, r).verdict == "INSUFFICIENT"


def test_a_clean_citing_a_token_not_in_the_memory_file_is_refused(world):
    """The anti-forgery rule: the symbol must be in BOTH the memory file and the cited file."""
    r, t = world
    forged = [row.replace("ALPHA_TOKEN", "NOT_IN_MEMORY") for row in GOOD_CLEAN[:1]] + GOOD_CLEAN[1:]
    assert rot.judge_audit(_block("CLEAN", forged), t, r).verdict == "INSUFFICIENT"


def test_a_clean_that_cites_a_stale_row_contradicts_itself(world):
    r, t = world
    rows = GOOD_CLEAN + ["- old thing | STALE | a.py | STALE_CLAIM_TOKEN"]
    assert rot.judge_audit(_block("CLEAN", rows), t, r).verdict == "INSUFFICIENT"


def test_a_stale_verdict_quoting_the_memory_file_is_accepted(world):
    r, t = world
    j = rot.judge_audit(_block("STALE", ["- it was removed | STALE | a.py | STALE_CLAIM_TOKEN"]), t, r)
    assert (j.verdict, j.accepted, len(j.stale_rows)) == ("STALE", True, 1), j.reason


def test_a_stale_verdict_inventing_a_claim_is_refused(world):
    """A lane that never read the file cannot quote it."""
    r, t = world
    j = rot.judge_audit(_block("STALE", ["- made up | STALE | a.py | INVENTED_TOKEN"]), t, r)
    assert (j.verdict, j.accepted) == ("INSUFFICIENT", False)


def test_a_stale_verdict_with_no_stale_row_is_refused(world):
    r, t = world
    assert rot.judge_audit(_block("STALE", GOOD_CLEAN), t, r).accepted is False


def test_the_wrong_task_id_is_refused(world):
    r, t = world
    assert rot.judge_audit(_block("CLEAN", GOOD_CLEAN, task_id="other"), t, r).accepted is False


def test_no_verdict_block_is_insufficient_not_clean(world):
    r, t = world
    assert rot.judge_audit("I looked and it seems fine!", t, r).verdict == "INSUFFICIENT"


def test_declared_insufficient_is_an_accepted_result(world):
    r, t = world
    j = rot.judge_audit(_block("INSUFFICIENT", []), t, r)
    assert (j.verdict, j.accepted) == ("INSUFFICIENT", True)


def test_an_unknown_verdict_word_is_insufficient(world):
    r, t = world
    assert rot.judge_audit(_block("PERFECT", GOOD_CLEAN), t, r).verdict == "INSUFFICIENT"


# --- controls --------------------------------------------------------------

def _control_sources(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    for n in rot.CONTROL_EXPECTED: (src / f"{n}.md").write_text(f"synthetic body for {n}")
    return src


def test_controls_cover_all_three_outcomes_and_carry_ground_truth(tmp_path):
    tasks = rot.write_controls(tmp_path / "c", source_dir=_control_sources(tmp_path))
    assert {t.expected for t in tasks} == {"CLEAN", "STALE", "INSUFFICIENT"}
    assert all(Path(t.path).exists() and t.kind == "control" for t in tasks)


def test_missing_control_bodies_abort_rather_than_run_without_controls(tmp_path):
    with pytest.raises(rot.RotError, match="deliberately kept out of the repo"):
        rot.write_controls(tmp_path / "c", source_dir=tmp_path / "nowhere")


def test_no_control_body_is_greppable_in_the_repo(tmp_path):
    """Measured: a lane searched the repo, found a control's body verbatim in this module,
    and said 'this is a planted control, expected STALE'. The answer key must not be in the
    tree the lane audits. Skips where the real bodies are not installed."""
    src = rot.default_controls_dir()
    if not src.is_dir():
        pytest.skip("real control bodies not installed on this machine")
    top = subprocess.run(["git", "-C", str(Path(__file__).parent), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    for f in src.glob("ctl-*.md"):
        lines = [ln.strip() for ln in f.read_text().splitlines() if len(ln.strip()) > 40 and not ln.startswith(("name:", "description:"))]
        for ln in lines[:3]:
            hit = subprocess.run(["git", "-C", top, "grep", "-l", "-F", ln[:60]], capture_output=True, text=True).stdout
            assert not hit.strip(), f"control text from {f.name} is in a tracked file: {hit.strip()[:120]}"


def test_the_planted_controls_ground_truth_still_holds_against_the_real_repo(tmp_path):
    """If a file is renamed, the CLEAN control silently becomes false and a correct
    lane would be marked wrong. Pin the truth the controls depend on."""
    top = Path(subprocess.run(["git", "-C", str(Path(__file__).parent), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True).stdout.strip())
    flywheel = top / "mcp-server-nucleus/src/mcp_server_nucleus/flywheel"
    for f in ("trigger.py", "proposals.py", "dream_cli.py"):
        assert (flywheel / f).exists(), f"the CLEAN control cites {f}, which no longer exists"
    assert "discovery_trigger.json" in (flywheel / "trigger.py").read_text()
    assert "DEFAULT_MIN_NEW_SESSIONS" in (flywheel / "trigger.py").read_text()
    assert "INSUFFICIENT" in (flywheel / "proposals.py").read_text()
    assert not (flywheel / "scheduler_daemon.py").exists(), "the STALE control's dead path came back to life"
    # The STALE control says the floor is 500; the truth must stay something else.
    assert "DEFAULT_MIN_NEW_SESSIONS = 20" in (flywheel / "trigger.py").read_text()


def test_the_prompt_forbids_writes_pins_the_repo_and_names_the_file(tmp_path):
    p = rot.build_prompt("t9", "/abs/mem.md", "/abs/repo")
    assert "READ-ONLY" in p and "git rev-parse --abbrev-ref HEAD" in p
    assert "/abs/mem.md" in p and "TASK_ID: t9" in p and "/abs/repo" in p


def test_the_prompt_accepts_detached_head_at_mains_tip_only():
    """EID-53 opposed pair. ~/nucleus is detached by design (ff-synced to
    origin/main). STEP 0 must proceed for detached-at-main's-tip and still
    refuse every other HEAD. The judge's behaviour is the prompt's text, so
    the test asserts the rule's three arms are encoded in it."""
    p = rot.build_prompt("t", "/m.md", "/r")
    # Arm 1 — the tip-comparison command and the detached accept path.
    assert "git rev-parse main" in p
    assert "detached" in p and "main tip SHA" in p
    # Arm 2 — the no-local-main fallback (the state checkout has none).
    assert "origin/main" in p
    # Arm 3 — refusal survives: other branch OR detached at a stale SHA.
    assert "any other branch" in p and "not main's tip" in p
    assert "STOP and print VERDICT: INSUFFICIENT" in p


def test_the_prompt_frames_dead_paths_as_leads_not_verdicts():
    rep = rot.FileReport("m.md", [rot.Claim("path", "gone.py", rot.DEAD, "no such path")])
    p = rot.build_prompt("t", "/m.md", "/r", rep)
    assert "gone.py" in p and "LEADS" in p and "deleted" in p


def test_a_stale_verdict_for_another_task_is_not_credited_to_this_one(world):
    """judge_clean checks the task id itself, which MASKED this check on the CLEAN path.
    STALE and INSUFFICIENT have no such backstop: a verdict returned for the wrong file
    would be attributed to this one."""
    r, t = world
    rows = ["- it was removed | STALE | a.py | STALE_CLAIM_TOKEN"]
    assert rot.judge_audit(_block("STALE", rows, task_id="someone-else"), t, r).accepted is False


def test_an_insufficient_verdict_for_another_task_is_not_credited_either(world):
    r, t = world
    assert rot.judge_audit(_block("INSUFFICIENT", [], task_id="someone-else"), t, r).accepted is False


def test_a_path_relative_to_a_subdirectory_is_live_not_dead(tmp_path):
    """Found by a lane overturning a mechanical DEAD: memories write `tests/x.py` for
    `pkg/tests/x.py`. 110 paths were reported dead; some were exactly this."""
    r = tmp_path / "sub"; r.mkdir(); _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.t"); _git(r, "config", "user.name", "t")
    (r / "pkg" / "tests").mkdir(parents=True); (r / "pkg" / "tests" / "x.py").write_text("1\n")
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "c")
    st = _statuses("`tests/x.py` and `tests/nope.py`", rot.Checkout(r))
    assert st["tests/x.py"] == rot.LIVE, "a subdirectory-relative path was declared dead"
    assert st["tests/nope.py"] == rot.DEAD, "the fix must not make everything live"


def test_a_suffix_that_only_partly_matches_a_directory_name_is_not_a_hit(tmp_path):
    """`ests/x.py` must not match `pkg/tests/x.py`: the suffix has to align on a `/`."""
    r = tmp_path / "s2"; r.mkdir(); _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.t"); _git(r, "config", "user.name", "t")
    (r / "pkg" / "tests").mkdir(parents=True); (r / "pkg" / "tests" / "x.py").write_text("1\n")
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "c")
    assert _statuses("`ests/x.py`", rot.Checkout(r))["ests/x.py"] == rot.DEAD


# --- bounded work, outages, and the lossy relay ----------------------------

def test_the_prompt_bounds_the_work():
    """Measured: 13 claims took 25 minutes and hit the client's 1800s cap; 6 took 6.5."""
    p = rot.build_prompt("t", "/m.md", "/r")
    assert f"AT MOST {rot.MAX_CLAIMS} claims" in p and "UNCHECKED:" in p


def test_a_vendor_outage_is_retry_not_a_verdict_about_the_file(world):
    r, t = world
    out = 'Step 0: main\\nError: Agent error: Connection error {"cognition.ai/retryable": true}'
    j = rot.judge_audit(out, t, r)
    assert (j.verdict, j.accepted) == (rot.RETRY, False)


def test_an_outage_message_inside_a_real_verdict_is_not_an_outage(world):
    """A lane may legitimately quote an error string; a verdict block means it finished."""
    r, t = world
    out = "note: saw 'Connection error' in a log\\n" + _block("INSUFFICIENT", [])
    assert rot.judge_audit(out, t, r).verdict == "INSUFFICIENT"


def test_a_relay_result_at_the_cap_is_flagged_possibly_truncated(tmp_path):
    import json
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"body": json.dumps({"result": "x" * rot.RELAY_RESULT_CAP})}))
    text, truncated = rot.from_relay(f)
    assert truncated is True and len(text) == rot.RELAY_RESULT_CAP
    f.write_text(json.dumps({"body": {"result": "short"}}))
    assert rot.from_relay(f) == ("short", False)


def test_a_truncated_verdict_block_is_refused_not_guessed(world):
    """The real-1 case: a completed audit cut off after 3 rows must not be judged."""
    r, t = world
    cut = _block("STALE", ["- x | TRUE | a.py:1 | ALPHA_TOKEN"])  # the STALE rows were past the cap
    assert rot.judge_audit(cut, t, r).accepted is False


# --- who may be sent to an external lane -----------------------------------
# Measured (w3-06): a memory with no guard term pointed at a private career document under
# .brain/; the lane followed the pointer and excerpts left the machine.

def _cks(repo):
    return [repo]


def test_a_pointer_into_brain_is_private_even_if_the_file_exists(repo, tmp_path):
    (repo.root / ".brain").mkdir(); (repo.root / ".brain" / "personal.md").write_text("x")
    cl = rot.extract("see `.brain/personal.md`"); rot.check(cl, _cks(repo), set())
    assert rot.private_pointers(cl, _cks(repo)), "a .brain pointer was not treated as private"


def test_an_untracked_file_that_exists_is_private(repo):
    cl = rot.extract("see `untracked.py`"); rot.check(cl, _cks(repo), set())
    assert any("not a tracked repo file" in w for w in rot.private_pointers(cl, _cks(repo)))


def test_a_tracked_file_and_a_dead_path_are_not_private(repo):
    cl = rot.extract("`src/real.py` and `src/gone.py`"); rot.check(cl, _cks(repo), set())
    assert rot.private_pointers(cl, _cks(repo)) == []


def test_personal_subject_matter_is_held_back_without_any_guard_term(repo):
    """The guard's terms are the strings someone already thought of, not the boundary."""
    rep = rot.FileReport("m.md", [], [])
    assert "personal-subject" in rot.lane_allowlist("m.md", "my career and resume draft", rep, _cks(repo))
    assert "personal-subject" in rot.lane_allowlist("project_thrive_profile.md", "neutral", rep, _cks(repo))
    assert rot.lane_allowlist("m.md", "flywheel trigger notes", rep, _cks(repo)) == []


def test_identity_reasons_carry_through_the_allowlist(repo):
    rep = rot.FileReport("m.md", [], ["term:patterns"])
    assert "term:patterns" in rot.lane_allowlist("m.md", "x", rep, _cks(repo))


def test_the_prompt_forbids_reading_outside_the_tracked_repo():
    p = rot.build_prompt("t", "/m.md", "/r")
    assert "READ ONLY git-tracked files" in p and "NEVER open anything under `.brain/`" in p


def test_a_lane_that_cites_an_untracked_private_file_is_refused(world):
    """The behavioural signal that a lane left the fence: it cited a file that exists but is not tracked."""
    r, t = world
    (Path(r) / ".brain").mkdir(exist_ok=True); (Path(r) / ".brain" / "thrive.md").write_text("private")
    rows = GOOD_CLEAN[:2] + ["- private thing | TRUE | .brain/thrive.md:1 | ALPHA_TOKEN"]
    j = rot.judge_audit(_block("CLEAN", rows), t, r)
    assert j.accepted is False and "private path" in j.reason


def test_a_tracked_file_under_a_dot_directory_is_a_legitimate_citation(world):
    """Measured: a lane cited .claude/plugins/.../watch-relay.sh, which this repo TRACKS, and a prefix
    rule refused a correct verdict. What matters is tracked-ness, not the prefix."""
    r, t = world
    d = Path(r) / ".claude" / "plugins"; d.mkdir(parents=True)
    (d / "watch.sh").write_text("ALPHA_TOKEN\n")
    subprocess.run(["git", "-C", str(r), "add", "-A"], check=True); subprocess.run(["git", "-C", str(r), "commit", "-qm", "d"], check=True)
    rows = ["- a | TRUE | a.py:1 | ALPHA_TOKEN", "- b | TRUE | b.py:1 | BETA_TOKEN", "- c | TRUE | .claude/plugins/watch.sh:1 | ALPHA_TOKEN"]
    j = rot.judge_audit(_block("CLEAN", rows), t, r)
    assert "private path" not in j.reason, j.reason


def test_a_path_that_does_not_exist_is_not_a_private_citation(world):
    """Citing the ABSENCE of a file is how a STALE finding is evidenced; nothing was read."""
    r, t = world
    j = rot.judge_audit(_block("STALE", ["- x | STALE | docs/gone.md | STALE_CLAIM_TOKEN"]), t, r)
    assert j.accepted is True, j.reason


def test_a_stale_verdict_citing_a_home_path_is_also_refused(world):
    r, t = world
    j = rot.judge_audit(_block("STALE", ["- x | STALE | ~/.cloudflared/config.yml | STALE_CLAIM_TOKEN"]), t, r)
    assert j.accepted is False and "private path" in j.reason


# --- credentials: never send a memory that holds one ------------------------

def _secret_samples():
    """Built from fragments at runtime: the repo's own secret scanner (rightly) blocks a literal
    secret-shaped string in a committed file, and that includes test fixtures."""
    return [
        "key is " + "sk_" + "live_" + "51Habcdef",
        "token " + "cfu" + "t_" + "abcdefghijklmnop",
        "AK" + "IA" + "ABCDEFGHIJKLMNOP is the id",
        "gh" + "p_" + "a" * 24,
        "-----BEGIN " + "RSA PRIVATE" + " KEY-----",
        "Zk3" + "aB9xQ" * 8,
    ]


@pytest.mark.parametrize("i", range(6))
def test_a_secret_shaped_string_holds_a_memory_back(repo, i):
    text = _secret_samples()[i]
    rep = rot.FileReport("notes.md", [], [])
    assert "credential-shaped" in rot.lane_allowlist("notes.md", text, rep, [repo]), text


def test_credential_named_files_are_held_back_even_without_a_visible_secret(repo):
    rep = rot.FileReport("reference_cloudflare_user_token.md", [], [])
    assert "credential-shaped" in rot.lane_allowlist("reference_cloudflare_user_token.md", "see the dashboard", rep, [repo])


def test_a_git_sha_and_ordinary_prose_are_not_credential_shaped(repo):
    """The opposed half: the screen must not swallow every memory that cites a commit."""
    rep = rot.FileReport("notes.md", [], [])
    sha40 = "4bfd6e2d5524da32ff6996a845eec66936307294"
    assert "credential-shaped" not in rot.lane_allowlist("notes.md", f"fixed in {sha40} and abc1234", rep, [repo])
    assert "credential-shaped" not in rot.lane_allowlist("notes.md", "the flywheel trigger is activity gated", rep, [repo])


def test_a_tracked_directory_is_tracked_and_an_empty_or_unknown_one_is_not(repo):
    """Found by a lane citing `ai_buddy_web/test`: ls-files lists FILES, so a directory always read as
    untracked and a correct verdict was refused as a private citation."""
    assert repo.is_tracked(repo.root / "src"), "a directory holding tracked files must count as tracked"
    (repo.root / "scratch").mkdir()
    assert not repo.is_tracked(repo.root / "scratch"), "an untracked directory must not"
    assert not repo.is_tracked(repo.root / "sr"), "a partial name must not match a directory"
