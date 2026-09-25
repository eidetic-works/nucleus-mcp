"""Opposed contract tests for the R2 workspace backend."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.workspace import (
    CopyWorkspaceBackend,
    GitWorkspaceBackend,
    WorkspaceEscape,
    WorkspaceNotClean,
    WorkspaceResolver,
)


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')\n")
    (root / "README.md").write_text("# Project\n")
    return root


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@nucleus"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True)


def _make_workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_copy_backend_creates_isolated_target(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-1")

    assert ws.target_path.is_dir()
    assert ws.target_path != root
    assert ws.target_path == workspace_root / "nucleus-copy-run-1"
    assert (ws.target_path / "src" / "main.py").read_text() == "print('hello')\n"

    resolved = backend.resolve(ws, "src/main.py")
    assert resolved.is_relative_to(ws.target_path)

    backend.dispose(ws)


def test_copy_backend_resolves_absolute_and_relative_paths(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-1")

    rel = backend.resolve(ws, "README.md")
    abs_resolved = backend.resolve(ws, str(ws.target_path / "src" / "main.py"))
    assert rel == ws.target_path / "README.md"
    assert abs_resolved == ws.target_path / "src" / "main.py"

    backend.dispose(ws)


def test_copy_backend_rejects_escape_attempts(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-1")

    with pytest.raises(WorkspaceEscape):
        backend.resolve(ws, "../outside")

    with pytest.raises(WorkspaceEscape):
        backend.resolve(ws, "/etc/passwd")

    backend.dispose(ws)


def test_copy_backend_dispose_removes_target(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-1")
    assert ws.target_path.exists()
    backend.dispose(ws)
    assert not ws.target_path.exists()


def test_copy_backend_captures_diff_and_is_clean_check(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-1")

    assert backend.is_clean(ws)
    (ws.target_path / "src" / "main.py").write_text("print('world')\n")
    diff = backend.diff(ws)
    assert b"world" in diff
    assert not backend.is_clean(ws)

    backend.dispose(ws)


def test_copy_backend_rejects_existing_target(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    (workspace_root / "nucleus-copy-run-2").mkdir()
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    with pytest.raises(WorkspaceNotClean):
        backend.create(root, "run-2")


def test_git_backend_creates_worktree_and_resolves_paths(tmp_path):
    root = _make_project(tmp_path)
    _init_git_repo(root)
    workspace_root = _make_workspace_root(tmp_path)
    backend = GitWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-git-1")

    assert ws.target_path.is_dir()
    assert ws.target_path == workspace_root / "nucleus-run-run-git-1"
    assert (ws.target_path / "src" / "main.py").read_text() == "print('hello')\n"
    assert ws.base_revision is not None
    assert len(ws.base_revision) == 40

    resolved = backend.resolve(ws, "README.md")
    assert resolved.is_relative_to(ws.target_path)

    backend.dispose(ws)
    assert not ws.target_path.exists()


def test_git_backend_rejects_escape_attempts(tmp_path):
    root = _make_project(tmp_path)
    _init_git_repo(root)
    workspace_root = _make_workspace_root(tmp_path)
    backend = GitWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-git-2")

    with pytest.raises(WorkspaceEscape):
        backend.resolve(ws, "../../etc")

    backend.dispose(ws)


def test_workspace_resolver_prefers_git_backend(tmp_path):
    root = _make_project(tmp_path)
    _init_git_repo(root)
    workspace_root = _make_workspace_root(tmp_path)
    resolver = WorkspaceResolver(workspace_root=workspace_root)
    backend = resolver.resolve_backend(root)
    assert backend.name == "git"


def test_workspace_resolver_falls_back_to_copy_for_non_git(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    resolver = WorkspaceResolver(workspace_root=workspace_root)
    backend = resolver.resolve_backend(root)
    assert backend.name == "copy"


def test_copy_backend_ignores_dot_next_and_large_files(tmp_path):
    root = _make_project(tmp_path)
    (root / ".next").mkdir()
    (root / ".next" / "build.json").write_text("{}")
    (root / "huge.txt").write_bytes(b"0" * (2 * 1024 * 1024))

    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-ignore")

    assert (ws.target_path / "src" / "main.py").read_text() == "print('hello')\n"
    assert not (ws.target_path / ".next").exists()
    assert not (ws.target_path / "huge.txt").exists()

    backend.dispose(ws)


def test_diff_does_not_report_only_in_base_for_skipped_files(tmp_path):
    root = _make_project(tmp_path)
    (root / ".next").mkdir()
    (root / ".next" / "build.json").write_text("{}")
    (root / "huge.txt").write_bytes(b"0" * (2 * 1024 * 1024))

    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-diff")
    (ws.target_path / "src" / "main.py").write_text("print('world')\n")

    diff = backend.diff(ws)
    assert b"Only in base" not in diff
    assert b"world" in diff

    backend.dispose(ws)


def test_copy_backend_ignores_public_media_image(tmp_path):
    root = _make_project(tmp_path)
    (root / "public").mkdir()
    (root / "public" / "media").mkdir()
    (root / "public" / "media" / "logo.png").write_bytes(b"fake png data")

    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-media")

    assert (ws.target_path / "src" / "main.py").read_text() == "print('hello')\n"
    assert not (ws.target_path / "public" / "media").exists()

    diff = backend.diff(ws)
    assert b"Only in base" not in diff
    assert b"logo.png" not in diff

    backend.dispose(ws)


def test_diff_ignores_runner_build_artifacts(tmp_path):
    root = _make_project(tmp_path)
    workspace_root = _make_workspace_root(tmp_path)
    backend = CopyWorkspaceBackend(workspace_root=workspace_root)
    ws = backend.create(root, "run-artifacts")

    (ws.target_path / "tsconfig.tsbuildinfo").write_text("{}")
    diff = backend.diff(ws)
    assert b"tsconfig.tsbuildinfo" not in diff
    assert b"Only in target" not in diff

    backend.dispose(ws)
