"""Mining: count what the harness flagged, not what a model imagined."""

import json

import pytest

from mcp_server_nucleus.flywheel.mining import is_dreaming_session, mine, signature


def _err(text, is_error=True):
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t", "content": text,
         **({"is_error": True} if is_error else {})}]}})


def _session(root, name, lines):
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.jsonl").write_text("\n".join(lines) + "\n")


@pytest.fixture
def root(tmp_path):
    return tmp_path / "projects" / "p"


# --- identity of a failure -------------------------------------------------

def test_same_failure_with_different_paths_ids_and_numbers_is_one_signature():
    a = signature("File does not exist: /srv/a/x/foo.py line 12")
    b = signature("File does not exist: /opt/b/y/bar.py line 998")
    assert a == b


def test_different_failures_stay_different():
    assert signature("File does not exist") != signature("Permission denied")


def test_signature_uses_the_first_nonblank_line_only():
    assert signature("\n\nPermission denied\nlots of trailing noise") == signature("Permission denied")


# --- what counts as an error -----------------------------------------------

def test_only_harness_flagged_errors_are_counted(tmp_path, root):
    """A result that merely CONTAINS the word 'error' is not a failure."""
    for i in range(6):
        _session(root, f"s{i}", [_err("all good, 0 errors found", is_error=False)])
    assert mine(roots=[tmp_path / "projects"], min_sessions=2).clusters == []


def test_a_recurring_flagged_error_is_ranked_by_distinct_sessions(tmp_path, root):
    for i in range(6):
        _session(root, f"s{i}", [_err(f"File does not exist: /tmp/f{i}.py")])
    m = mine(roots=[tmp_path / "projects"], min_sessions=5)
    assert len(m.clusters) == 1 and m.clusters[0].sessions == 6


def test_a_retry_loop_in_one_session_is_one_session_not_many(tmp_path, root):
    """200 identical errors in one session is one session's problem."""
    _session(root, "loop", [_err("Exit code 1")] * 200)
    for i in range(4):
        _session(root, f"s{i}", [_err("Exit code 1")])
    c = mine(roots=[tmp_path / "projects"], min_sessions=1).clusters[0]
    assert c.sessions == 5 and c.occurrences == 204


def test_the_floor_excludes_rare_errors(tmp_path, root):
    _session(root, "a", [_err("rare failure")])
    assert mine(roots=[tmp_path / "projects"], min_sessions=3).clusters == []


# --- the feedback loop -----------------------------------------------------

def test_a_dreaming_agents_own_session_is_excluded(tmp_path, root):
    """A pass writes its prompt into a transcript; a later pass must not read it."""
    for i in range(6):
        _session(root, f"real{i}", [_err("Exit code 1")])
    for i in range(6):
        _session(root, f"dream{i}", [
            json.dumps({"type": "user", "message": {"content": "You are the DISCOVERY half of a memory flywheel."}}),
            _err("Exit code 1")])
    m = mine(roots=[tmp_path / "projects"], min_sessions=1)
    assert m.sessions_excluded == 6
    assert m.clusters[0].sessions == 6, "dreaming sessions were counted as evidence"


def test_exclusion_can_be_turned_off(tmp_path, root):
    _session(root, "d", [json.dumps({"message": {"content": "PRECISION half of a memory flywheel"}}), _err("x")])
    assert mine(roots=[tmp_path / "projects"], min_sessions=1, exclude_dreaming=False).sessions_excluded == 0


def test_is_dreaming_session_reads_the_head(tmp_path, root):
    _session(root, "d", [json.dumps({"message": {"content": "DISCOVERY half of a memory flywheel"}})])
    _session(root, "n", [json.dumps({"message": {"content": "ordinary work"}})])
    assert is_dreaming_session(root / "d.jsonl") and not is_dreaming_session(root / "n.jsonl")


def test_a_bare_exit_code_is_told_apart_by_the_next_line():
    """Measured: 'Exit code 1' alone swallowed 293 sessions of unrelated failures."""
    a = signature("Exit code 1\ngrep: no such file or directory")
    b = signature("Exit code 1\npermission denied")
    assert a != b
    assert signature("Exit code 1") == "exit code <n>"  # nothing more to say
