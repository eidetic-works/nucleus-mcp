"""Regression test for the target-file-presence check in execution_verifier.

THE DEFECT: the nucleus build --merge pipeline had no target-file-presence
check — a vendor that drops its tasked target files (reports success
without touching the files it was supposed to) could still report PASS,
because the fail-stop predicate only checked ``status == "ok"`` and
``produced_output is True``, neither of which proves the declared target
files were touched.  Tier 0 (diff non-empty) only checks that *something*
changed, not that the *right* files changed.

``verify_target_files_present`` closes that gap: for each declared target
path it checks whether the file was modified (appears in the changed-files
set), exists-but-was-not-modified (hard fail), or is absent-for-reason
(file does not exist — not a failure).

Each test states its failure direction; a check that can only pass is not a
check.
"""

from mcp_server_nucleus.runtime.execution_verifier import (
    verify_target_files_present,
)


# ---------------------------------------------------------------------------
# Positive cases (must not regress)
# ---------------------------------------------------------------------------

def test_modified_target_passes(tmp_path):
    """POSITIVE: a declared target that was modified → passed is True."""
    (tmp_path / "src" / "foo.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "foo.py").write_text("x = 1\n")
    sig = verify_target_files_present(
        {"src/foo.py"}, ["src/foo.py"], tmp_path,
    )
    assert sig["passed"] is True
    assert "src/foo.py" in sig["modified"]
    assert sig["not_modified"] == []


def test_absent_target_is_not_a_failure(tmp_path):
    """ABSENT-FOR-REASON: a declared target that doesn't exist → not a failure.

    The file may have been mentioned as context, was supposed to be deleted,
    or is a path that doesn't resolve.  The absence is confirmed; the reason
    is that the file genuinely does not exist.
    """
    sig = verify_target_files_present(
        {"src/nonexistent.py"}, [], tmp_path,
    )
    assert sig["passed"] is True
    assert "src/nonexistent.py" in sig["absent"]
    assert sig["not_modified"] == []


def test_no_declared_paths_passes(tmp_path):
    """No declared target files → nothing to verify → passed is True."""
    sig = verify_target_files_present(set(), ["src/foo.py"], tmp_path)
    assert sig["passed"] is True
    assert sig["modified"] == []
    assert sig["not_modified"] == []
    assert sig["absent"] == []


def test_none_declared_paths_passes(tmp_path):
    """None/empty declared paths → passed is True (nothing to verify)."""
    sig = verify_target_files_present(None, ["src/foo.py"], tmp_path)
    assert sig["passed"] is True


# ---------------------------------------------------------------------------
# The defect — existing target files not modified
# ---------------------------------------------------------------------------

def test_existing_but_unmodified_target_fails(tmp_path):
    """THE BUG: a declared target that EXISTS but was NOT modified → FAIL.

    This is the exact shape of the defect: the file is there, the vendor was
    supposed to edit it, and didn't — yet without this check the task would
    count as passed because status == "ok" and produced_output is True.
    """
    (tmp_path / "src" / "foo.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "foo.py").write_text("x = 1\n")
    sig = verify_target_files_present(
        {"src/foo.py"}, [], tmp_path,
    )
    assert sig["passed"] is False
    assert "src/foo.py" in sig["not_modified"]


def test_mixed_modified_and_unmodified_fails(tmp_path):
    """One modified + one existing-but-unmodified → FAIL (not all targets met).

    A partial pass must not read as a full pass — that is the exact failure
    mode the defect enabled: one target touched, the other dropped, and the
    task reported PASS.
    """
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    (tmp_path / "src" / "b.py").write_text("x = 2\n")
    sig = verify_target_files_present(
        {"src/a.py", "src/b.py"}, ["src/a.py"], tmp_path,
    )
    assert sig["passed"] is False
    assert "src/a.py" in sig["modified"]
    assert "src/b.py" in sig["not_modified"]


def test_all_modified_passes(tmp_path):
    """All declared targets modified → passed is True."""
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    (tmp_path / "src" / "b.py").write_text("x = 2\n")
    sig = verify_target_files_present(
        {"src/a.py", "src/b.py"},
        ["src/a.py", "src/b.py"],
        tmp_path,
    )
    assert sig["passed"] is True
    assert len(sig["modified"]) == 2
    assert sig["not_modified"] == []


# ---------------------------------------------------------------------------
# Mirror-root tolerance
# ---------------------------------------------------------------------------

def test_mirror_root_changed_path_matches_declared(tmp_path):
    """A declared path matches a changed path under a different mirror root.

    The same package is vendored under ``mcp-server-nucleus/src/`` and
    ``nucleus-mcp/src/``.  A task that declares ``runtime/foo.py`` and a
    vendor that modifies ``mcp-server-nucleus/src/runtime/foo.py`` must be
    recognized as a match, not a false failure.
    """
    (tmp_path / "mcp-server-nucleus" / "src" / "runtime").mkdir(
        parents=True, exist_ok=True)
    (tmp_path / "mcp-server-nucleus" / "src" / "runtime" / "foo.py").write_text(
        "x = 1\n")
    sig = verify_target_files_present(
        {"runtime/foo.py"},
        ["mcp-server-nucleus/src/runtime/foo.py"],
        tmp_path,
    )
    assert sig["passed"] is True
    assert "runtime/foo.py" in sig["modified"]


def test_mirror_root_existing_not_modified_fails(tmp_path):
    """Mirror-root tolerance does NOT weaken the existing-not-modified check.

    A file that exists under a mirror root but was NOT modified still fails
    — the mirror-root logic only helps MATCH changed paths, not excuse
    unmodified ones.
    """
    (tmp_path / "mcp-server-nucleus" / "src" / "runtime").mkdir(
        parents=True, exist_ok=True)
    (tmp_path / "mcp-server-nucleus" / "src" / "runtime" / "foo.py").write_text(
        "x = 1\n")
    sig = verify_target_files_present(
        {"runtime/foo.py"},
        [],  # nothing changed
        tmp_path,
    )
    assert sig["passed"] is False
    assert "runtime/foo.py" in sig["not_modified"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_changed_files_with_existing_target_fails(tmp_path):
    """Empty changed-files set + existing target → FAIL (nothing was touched)."""
    (tmp_path / "config.json").write_text('{"k": 1}')
    sig = verify_target_files_present(
        {"config.json"}, [], tmp_path,
    )
    assert sig["passed"] is False
    assert "config.json" in sig["not_modified"]


def test_declared_path_with_dot_slash_prefix(tmp_path):
    """A declared path with ``./`` prefix is normalized before matching."""
    (tmp_path / "src" / "foo.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "foo.py").write_text("x = 1\n")
    sig = verify_target_files_present(
        {"./src/foo.py"}, ["src/foo.py"], tmp_path,
    )
    assert sig["passed"] is True
    assert "./src/foo.py" in sig["modified"]
