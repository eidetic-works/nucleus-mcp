"""Regression test for git project-root resolution across repository subdirectories."""

import subprocess
from pathlib import Path

from mcp_server_nucleus.runtime.ground import detect_project_root


def test_detect_project_root_from_repo_root_and_subdirectory(tmp_path: Path):
    """Assert detect_project_root returns git top-level from both root and subdirectories."""
    repo_dir = tmp_path / "my_repo"
    repo_dir.mkdir()
    sub_dir = repo_dir / "mcp-server-nucleus"
    sub_dir.mkdir()

    # Create dummy files to test fallback markers inside subdirectory
    (sub_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")

    # Initialize a real git repository at repo_dir
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)

    # 1. From repository root
    root_from_repo = detect_project_root(repo_dir)
    assert root_from_repo.resolve() == repo_dir.resolve()

    # 2. From subdirectory
    root_from_subdir = detect_project_root(sub_dir)
    assert root_from_subdir.resolve() == repo_dir.resolve()


def test_detect_project_root_fallback_without_git(tmp_path: Path):
    """Assert detect_project_root falls back to pyproject.toml / package.json when not in git."""
    non_git_dir = tmp_path / "non_git_repo"
    non_git_dir.mkdir()
    sub_dir = non_git_dir / "sub_pkg"
    sub_dir.mkdir()
    (sub_dir / "pyproject.toml").write_text("[project]\nname = 'sub'\n", encoding="utf-8")

    # In a non-git dir, detect_project_root(sub_dir) should fall back to finding pyproject.toml at sub_dir
    resolved = detect_project_root(sub_dir)
    assert resolved.resolve() == sub_dir.resolve()


def test_detect_project_root_from_file_path(tmp_path: Path):
    """Assert detect_project_root handles file paths as start arguments."""
    repo_dir = tmp_path / "my_repo"
    repo_dir.mkdir()
    sub_dir = repo_dir / "src"
    sub_dir.mkdir()
    file_path = sub_dir / "main.py"
    file_path.write_text("print('hello')", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)

    resolved = detect_project_root(file_path)
    assert resolved.resolve() == repo_dir.resolve()


def test_detect_project_root_git_timeout_fallback(tmp_path: Path, monkeypatch):
    """Assert detect_project_root falls back gracefully if git rev-parse fails or times out."""
    non_git_dir = tmp_path / "fallback_repo"
    non_git_dir.mkdir()
    (non_git_dir / "package.json").write_text("{}", encoding="utf-8")

    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr(subprocess, "run", mock_run)

    resolved = detect_project_root(non_git_dir)
    assert resolved.resolve() == non_git_dir.resolve()

