import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.agent_os.safe_first_pr import (
    Patch,
    SafeTask,
    apply_patch,
    create_branch_and_commit,
    is_safe_target,
    pr_description,
    propose_patch,
    scan_for_safe_tasks,
)
from mcp_server_nucleus.runtime.agent_os.safe_gate import SafetyVerdict
from mcp_server_nucleus.runtime.verifier import _FILE_EXISTS_RE, _GIT_BRANCH_EXISTS_RE


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), check=True)


def _commit_all(repo: Path, message: str = "init") -> None:
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=str(repo), check=True)


def test_is_safe_target_allows_docs_markdown(tmp_path: Path) -> None:
    allowed, reason = is_safe_target("docs/guide.md", repo_root=str(tmp_path))
    assert allowed is True
    assert reason


def test_is_safe_target_denies_scripts(tmp_path: Path) -> None:
    allowed, reason = is_safe_target("scripts/deploy.sh", repo_root=str(tmp_path))
    assert allowed is False
    assert "scripts" in reason.lower() or "disallowed directory" in reason.lower()


def test_is_safe_target_denies_py(tmp_path: Path) -> None:
    allowed, reason = is_safe_target("src/app.py", repo_root=str(tmp_path))
    assert allowed is False
    assert ".py" in reason or "code/config" in reason


def test_is_safe_target_denies_github(tmp_path: Path) -> None:
    allowed, reason = is_safe_target(".github/workflows/ci.yml", repo_root=str(tmp_path))
    assert allowed is False
    assert ".github" in reason.lower() or "disallowed" in reason.lower()


def test_is_safe_target_denies_traversal(tmp_path: Path) -> None:
    allowed, reason = is_safe_target("docs/../../../etc/passwd", repo_root=str(tmp_path))
    assert allowed is False
    assert "traversal" in reason.lower() or "escapes" in reason.lower()


def test_is_safe_target_denies_secret(tmp_path: Path) -> None:
    allowed, reason = is_safe_target("docs/my_secret_notes.md", repo_root=str(tmp_path))
    assert allowed is False
    assert "secret" in reason.lower()


def test_is_safe_target_denies_unknown_shape(tmp_path: Path) -> None:
    allowed, reason = is_safe_target("weird_thing.xyz", repo_root=str(tmp_path))
    assert allowed is False
    assert "unknown" in reason.lower() or "not under" in reason.lower()


def test_scan_finds_broken_markdown_link(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "intro.md").write_text(
        "See [the missing guide](missing.md) for details.\n"
    )
    (tmp_path / "docs" / "exists.md").write_text("# Exists\n")
    _commit_all(tmp_path)

    tasks = scan_for_safe_tasks(str(tmp_path))
    assert any(
        t.path == "docs/intro.md"
        and t.kind == "broken_link"
        and "missing.md" in t.description
        for t in tasks
    )


def test_scan_ignores_good_markdown_link(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "exists.md").write_text("# Exists\n")
    (tmp_path / "docs" / "intro.md").write_text(
        "See [the good guide](exists.md) for details.\n"
    )
    _commit_all(tmp_path)

    tasks = scan_for_safe_tasks(str(tmp_path))
    assert not tasks


def test_propose_patch_refuses_unsafe_task(tmp_path: Path) -> None:
    task = SafeTask(
        path="scripts/deploy.sh",
        kind="broken_link",
        description="broken link",
        evidence="see [x](y)",
    )
    with pytest.raises(ValueError):
        propose_patch(str(tmp_path), task)


def test_propose_patch_does_not_write_to_disk(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    content = "See [the missing guide](missing.md) for details.\n"
    (tmp_path / "docs" / "intro.md").write_text(content)
    (tmp_path / "docs" / "exists.md").write_text("# Exists\n")
    _commit_all(tmp_path)

    tasks = scan_for_safe_tasks(str(tmp_path))
    assert tasks
    task = tasks[0]

    before = (tmp_path / "docs" / "intro.md").read_text()
    patch = propose_patch(str(tmp_path), task)
    after = (tmp_path / "docs" / "intro.md").read_text()

    assert isinstance(patch, Patch)
    assert before == after


def test_propose_patch_claims_match_verifier_regexes(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "intro.md").write_text(
        "See [the missing guide](missing.md) for details.\n"
    )
    _commit_all(tmp_path)

    tasks = scan_for_safe_tasks(str(tmp_path))
    assert tasks
    patch = propose_patch(str(tmp_path), tasks[0])

    for claim in patch.claims:
        assert _FILE_EXISTS_RE.search(claim) or _GIT_BRANCH_EXISTS_RE.search(claim), claim


# --- regressions for a FAIL-OPEN found by the review lane -------------------
# The original rule allowed anything under docs/. Location alone cleared
# docs/.netrc (credentials), docs/Dockerfile, docs/deploy and docs/style.css.
# A path must now be in an allowed PLACE *and* have an allowed SHAPE.

import pytest as _pytest


@_pytest.mark.parametrize("path", [
    "docs/.netrc",        # credentials file
    "docs/.bashrc",       # shell config
    "docs/Dockerfile",    # build definition
    "docs/deploy",        # extensionless, name says it all
    "docs/notes",         # extensionless
    "docs/style.css",     # not documentation
    "docs/page.html",     # not documentation
    "docs/config.conf",   # config
    "docs/data.xml",      # data
])
def test_non_doc_shapes_under_docs_are_denied(path):
    allowed, reason = is_safe_target(path)
    assert not allowed, f"{path} was ALLOWED -- the gate is failing open"
    assert "not a documentation file" in reason or "keyword" in reason


@_pytest.mark.parametrize("path", [
    "docs/guide.md", "docs/deep/nested.md", "examples/demo.txt", "README.md",
])
def test_real_docs_are_still_allowed(path):
    """OPPOSED: tightening must not deny the files the flow exists to edit.
    A gate that denies everything is safe and useless."""
    allowed, reason = is_safe_target(path)
    assert allowed, f"{path} was denied: {reason}"


def test_keyword_matches_tokens_not_substrings():
    """'key' inside 'monkey' is not a secret.

    A deny-list that cries wolf gets switched off, and that costs the rules
    that DO matter -- so the false positive is a real defect, not pedantry.
    """
    allowed, _ = is_safe_target("docs/monkey.md")
    assert allowed, "'monkey.md' denied by substring match on 'key'"

    denied, reason = is_safe_target("docs/api_key.md")
    assert not denied, "a genuine 'key' token must still be denied"
    assert "key" in reason


# ── Track S4: patch application, branch-and-commit, PR body ────────────────

def test_apply_patch_writes_safe_file(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    original = "original content\n"
    (tmp_path / "docs" / "x.md").write_text(original)
    _commit_all(tmp_path)

    patch = Patch(
        path="docs/x.md",
        original_text=original,
        patched_text="patched content\n",
        claims=[],
    )
    bytes_written = apply_patch(str(tmp_path), patch)

    assert (tmp_path / "docs" / "x.md").read_text() == "patched content\n"
    assert bytes_written == len("patched content\n".encode("utf-8"))


def test_apply_patch_refuses_unsafe_path(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "scripts").mkdir()
    content = b"#!/bin/sh\necho hello\n"
    (tmp_path / "scripts" / "deploy.sh").write_bytes(content)
    _commit_all(tmp_path)

    patch = Patch(
        path="scripts/deploy.sh",
        original_text="#!/bin/sh\necho hello\n",
        patched_text="#!/bin/sh\necho world\n",
        claims=[],
    )
    with pytest.raises(PermissionError) as exc:
        apply_patch(str(tmp_path), patch)
    assert "scripts" in str(exc.value).lower() or "disallowed" in str(exc.value).lower()
    assert (tmp_path / "scripts" / "deploy.sh").read_bytes() == content


def test_apply_patch_rechecks_path_at_write_time(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    original = "original content\n"
    (tmp_path / "docs" / "safe.md").write_text(original)
    _commit_all(tmp_path)

    patch = Patch(
        path="docs/safe.md",
        original_text=original,
        patched_text="patched content\n",
        claims=[],
    )
    patch.path = "scripts/deploy.sh"
    with pytest.raises(PermissionError):
        apply_patch(str(tmp_path), patch)
    assert (tmp_path / "docs" / "safe.md").read_text() == original


def test_apply_patch_refuses_if_file_changed(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.md").write_text("original content\n")
    _commit_all(tmp_path)

    patch = Patch(
        path="docs/x.md",
        original_text="original content\n",
        patched_text="patched content\n",
        claims=[],
    )
    (tmp_path / "docs" / "x.md").write_text("changed under us\n")

    with pytest.raises(ValueError):
        apply_patch(str(tmp_path), patch)
    assert (tmp_path / "docs" / "x.md").read_text() == "changed under us\n"


def test_create_branch_and_commit_returns_sha(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    original = "original content\n"
    (tmp_path / "docs" / "x.md").write_text(original)
    _commit_all(tmp_path)

    patch = Patch(
        path="docs/x.md",
        original_text=original,
        patched_text="patched content\n",
        claims=[],
    )
    apply_patch(str(tmp_path), patch)
    sha = create_branch_and_commit(
        str(tmp_path), patch, "patch-branch", message="apply patch"
    )

    assert len(sha) == 40
    result = subprocess.run(
        ["git", "cat-file", "-t", sha],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "commit"


def test_create_branch_and_commit_only_patched_file(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    original = "original content\n"
    (tmp_path / "docs" / "x.md").write_text(original)
    (tmp_path / "other.txt").write_text("other\n")
    _commit_all(tmp_path)

    # Stage an unrelated file so it is in the index when we commit.
    (tmp_path / "other.txt").write_text("modified other\n")
    subprocess.run(["git", "add", "other.txt"], cwd=str(tmp_path), check=True)

    patch = Patch(
        path="docs/x.md",
        original_text=original,
        patched_text="patched content\n",
        claims=[],
    )
    apply_patch(str(tmp_path), patch)
    sha = create_branch_and_commit(
        str(tmp_path), patch, "patch-branch-2", message="apply patch 2"
    )

    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    files = [ln for ln in result.stdout.splitlines() if ln]
    assert "docs/x.md" in files
    assert "other.txt" not in files


def test_create_branch_and_commit_existing_branch_raises(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.md").write_text("original content\n")
    _commit_all(tmp_path)
    subprocess.run(["git", "branch", "existing"], cwd=str(tmp_path), check=True)

    patch = Patch(
        path="docs/x.md",
        original_text="original content\n",
        patched_text="patched content\n",
        claims=[],
    )
    with pytest.raises(ValueError, match="already exists"):
        create_branch_and_commit(str(tmp_path), patch, "existing")


def test_pr_description_refuted_not_stated_as_fact() -> None:
    confirmed = "FILE EXISTS: docs/x.md"
    refuted = "FILE EXISTS: missing.md"
    verified = {
        "confirmed": [confirmed],
        "refuted": [refuted],
        "unverifiable": [],
    }
    verdict = SafetyVerdict(
        safe=False,
        reason="1 claim was refuted",
        confirmed=[confirmed],
        blocking=[refuted],
    )
    patch = Patch(
        path="docs/x.md",
        original_text="",
        patched_text="",
        claims=[confirmed, refuted],
    )
    body = pr_description(patch, verified, verdict)

    assert refuted not in body
    assert "1 claim(s) were not verified" in body


def test_pr_description_leads_with_not_safe_reason() -> None:
    verified = {"confirmed": [], "refuted": [], "unverifiable": []}
    verdict = SafetyVerdict(
        safe=False,
        reason="target path not allowed",
        confirmed=[],
        blocking=[],
    )
    patch = Patch(
        path="docs/x.md",
        original_text="",
        patched_text="",
        claims=[],
    )
    body = pr_description(patch, verified, verdict)

    first_line = body.splitlines()[0]
    assert "not safe" in first_line.lower()
    assert "target path not allowed" in first_line


def test_patch_preserves_a_multiline_document(tmp_path):
    """A Patch must carry the WHOLE file, not the one line that changed.

    propose_patch originally stored `task.evidence` -- a single line -- as
    original_text, while apply_patch writes patched_text as the file's entire
    content and compares original_text against the whole file on disk. On any
    multi-line document that comparison never matched, so apply_patch refused
    every real file. It failed CLOSED, so nothing was destroyed; it also meant
    the feature could never once succeed.

    Every pre-existing fixture was a single-line file, which is exactly why 42
    tests passed over a function that could not work.
    """
    repo = tmp_path / "r"
    (repo / "docs").mkdir(parents=True)
    _init_git_repo(repo)
    doc = repo / "docs" / "guide.md"
    doc.write_text(
        "# Title\n\nIntro paragraph.\n\nSee [gone](missing.md) here.\n\nFinal line.\n",
        encoding="utf-8",
    )
    _commit_all(repo)

    tasks = scan_for_safe_tasks(repo)
    assert tasks, "expected the broken link to be found"
    patch = propose_patch(repo, tasks[0])

    # The patch carries the whole file, both sides.
    assert patch.original_text.count("\n") > 1, "original_text is not whole-file"
    assert "# Title" in patch.patched_text and "Final line." in patch.patched_text

    apply_patch(repo, patch)
    after = doc.read_text(encoding="utf-8")

    assert len(after.splitlines()) == 7, f"document was reshaped: {after!r}"
    assert "# Title" in after and "Intro paragraph." in after and "Final line." in after
    assert "missing.md" not in after, "the broken link survived"
