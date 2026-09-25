"""
Regression + unit tests for ADR-0042 "Project Spine" batch XY-1.

Covers:
  * D2 resolve_project — marker / git-remote / dirname precedence, non-repo,
    invalid marker.
  * D1 precedence inversion in get_brain_path under NUCLEUS_PROJECT_SPINE:
      - Bespoq scenario (a real git repo w/ remote — the actual Bespoq shape):
        env pinned to a foreign brain + cwd inside the project.
        Flag ON  -> project brain wins AND the conflict is logged.
        Flag OFF -> env wins, byte-identical to today, no log.
      - Marker-file variant of the same win-and-log scenario.
      - No project / brain absent -> falls through to env unchanged.
      - No conflict (env == project brain) -> project returned, no log.
  * ContextVar precedence preserved under both flag states.
  * Structural sentinel: flag OFF never calls into runtime.project.

Cooperates with the autouse conftest fixtures (_ensure_brain_path,
_reset_tenant_contextvar): every test that needs a specific env value sets it
via monkeypatch (runs after the autouse default and wins); the flag is toggled
per-test via monkeypatch and belt-cleared by the autouse fixture below. Never
reloads runtime.common (conftest excludes it from module preservation — the
#653 stale-ContextVar cause).
"""

import logging
import subprocess

import pytest

from mcp_server_nucleus.runtime.common import get_brain_path, set_tenant_brain_path
from mcp_server_nucleus.runtime.project import ProjectInfo, resolve_project


@pytest.fixture(autouse=True)
def _clean_project_spine_flag(monkeypatch):
    """Belt: no leaked NUCLEUS_PROJECT_SPINE flips an unrelated test to ON.

    Mirrors _clean_relay_env. Tests that need the flag ON re-set it via
    monkeypatch, which runs after this and wins for the test body.
    """
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)


# ──────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────
def _make_project(base, name="bespoq", *, git=False, brain=True, marker=None):
    """Create a fake project dir under ``base``.

    git=True    -> `git init` a real repo (the git toplevel is a root signal;
                   add a remote with ``_add_remote`` for the git-remote slug).
    brain=True  -> create the owned .brain directory.
    marker=str  -> write a `.nucleus-project` marker with that raw content
                   (the marker file is a root signal regardless of content).
    Returns the project root Path.

    Post the change-1 root restriction, a bare dir (git=False, marker=None) is
    intentionally NOT a detectable project — pyproject.toml / package.json are
    no longer root signals. Pass ``git=True`` or a ``marker`` to make it one.
    """
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    if brain:
        (root / ".brain").mkdir(exist_ok=True)
    if marker is not None:
        (root / ".nucleus-project").write_text(marker, encoding="utf-8")
    return root


def _add_remote(root, url):
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


# ──────────────────────────────────────────────────────────────
# D1 — get_brain_path precedence (the Bespoq regression)
# ──────────────────────────────────────────────────────────────
def test_flag_off_env_wins_byte_identical(tmp_path, monkeypatch, caplog):
    """Flag OFF: env pin wins over a real project brain, exactly as today."""
    proj = _make_project(tmp_path, "bespoq", git=True, brain=True)
    _add_remote(proj, "https://github.com/acme/bespoq.git")
    foreign = tmp_path / "foreign_brain"
    foreign.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(foreign))
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)  # flag OFF

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        result = get_brain_path()

    assert result.resolve() == foreign.resolve()
    assert (proj / ".brain").resolve() != result.resolve()
    assert "overridden by detected project" not in caplog.text


def test_flag_on_project_wins_and_conflict_logged(tmp_path, monkeypatch, caplog):
    """Flag ON: project brain wins over a foreign env pin AND logs the conflict.

    The Bespoq shape is a real git repo with an origin remote — the git-remote
    arm resolves the slug ("bespoq"), and the git toplevel is the root that
    owns ``.brain`` (same root, no monorepo mismatch).
    """
    proj = _make_project(tmp_path, "bespoq", git=True, brain=True)
    _add_remote(proj, "https://github.com/acme/bespoq.git")
    foreign = tmp_path / "foreign_brain"
    foreign.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(foreign))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        result = get_brain_path()

    assert result.resolve() == (proj / ".brain").resolve()
    # conflict log names what lost (env) and what won (slug)
    assert "overridden by detected project" in caplog.text
    assert str(foreign) in caplog.text
    assert "bespoq" in caplog.text


def test_flag_on_marker_variant_project_wins_and_conflict_logged(
    tmp_path, monkeypatch, caplog
):
    """Marker-file variant of the win-and-log scenario (no git repo needed).

    An explicit ``.nucleus-project`` marker makes the dir a root and supplies
    the slug; the same precedence/conflict-log guarantees hold as for the git
    Bespoq shape.
    """
    proj = _make_project(tmp_path, "bespoq", brain=True, marker="bespoq\n")
    foreign = tmp_path / "foreign_brain"
    foreign.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(foreign))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        result = get_brain_path()

    assert result.resolve() == (proj / ".brain").resolve()
    assert "overridden by detected project" in caplog.text
    assert str(foreign) in caplog.text
    assert "bespoq" in caplog.text


def test_flag_on_no_conflict_no_log(tmp_path, monkeypatch, caplog):
    """Flag ON, env pin already == project brain: project returned, no warning."""
    proj = _make_project(tmp_path, "bespoq", brain=True, marker="bespoq\n")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(proj / ".brain"))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        result = get_brain_path()

    assert result.resolve() == (proj / ".brain").resolve()
    assert "overridden by detected project" not in caplog.text


def test_flag_on_no_project_falls_through_to_env(tmp_path, monkeypatch, caplog):
    """Flag ON but cwd is not a project (no signal, no brain): env wins, no log."""
    bare = tmp_path / "scratch" / "deep"
    bare.mkdir(parents=True)
    foreign = tmp_path / "foreign_brain"
    foreign.mkdir()
    monkeypatch.chdir(bare)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(foreign))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        result = get_brain_path()

    assert result.resolve() == foreign.resolve()
    assert "overridden by detected project" not in caplog.text


def test_flag_on_project_without_brain_falls_through_to_env(tmp_path, monkeypatch):
    """Flag ON, project root exists but has no .brain: env wins (no divergence)."""
    proj = _make_project(tmp_path, "bespoq", brain=False, marker="bespoq\n")
    foreign = tmp_path / "foreign_brain"
    foreign.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(foreign))
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    assert get_brain_path().resolve() == foreign.resolve()


# ──────────────────────────────────────────────────────────────
# ContextVar precedence preserved under BOTH flag states
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("flag", [None, "1"])
def test_contextvar_still_wins_over_project(tmp_path, monkeypatch, flag):
    """Branch A (ContextVar) beats project detection and env, flag ON or OFF."""
    proj = _make_project(tmp_path, "bespoq", brain=True, marker="bespoq\n")
    ctx_brain = tmp_path / "ctx_brain"
    ctx_brain.mkdir()
    monkeypatch.chdir(proj)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(proj / ".brain"))
    if flag is None:
        monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    else:
        monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", flag)

    set_tenant_brain_path(str(ctx_brain))
    try:
        result = get_brain_path()
    finally:
        set_tenant_brain_path(None)

    assert result.resolve() == ctx_brain.resolve()


# ──────────────────────────────────────────────────────────────
# Structural sentinel — the flag-OFF path never enters runtime.project
# ──────────────────────────────────────────────────────────────
def test_flag_off_never_touches_project_module(tmp_path, monkeypatch):
    """Flag OFF ⇒ resolve_project is never called, under env AND ContextVar.

    Booby-trap ``runtime.project.resolve_project`` to raise. If get_brain_path
    ever imported/called it on the default (flag-unset) path, these calls would
    detonate. Both the env-set and ContextVar-set resolutions must still
    succeed — locking the structural guarantee (the #653-class contract) that
    the disabled feature's module stays inert on the OFF path.
    """
    import mcp_server_nucleus.runtime.project as project_mod

    def _sentinel(*_args, **_kwargs):
        raise RuntimeError("resolve_project must not run on the flag-OFF path")

    monkeypatch.setattr(project_mod, "resolve_project", _sentinel)
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)  # flag OFF

    # (a) env-set resolution (ContextVar cleared by autouse fixture)
    env_brain = tmp_path / "env_brain"
    env_brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(env_brain))
    assert get_brain_path().resolve() == env_brain.resolve()

    # (b) ContextVar-set resolution (short-circuits before the flag guard)
    ctx_brain = tmp_path / "ctx_brain"
    ctx_brain.mkdir()
    set_tenant_brain_path(str(ctx_brain))
    try:
        assert get_brain_path().resolve() == ctx_brain.resolve()
    finally:
        set_tenant_brain_path(None)


# ──────────────────────────────────────────────────────────────
# D2 — resolve_project unit coverage
# ──────────────────────────────────────────────────────────────
def test_detect_marker_beats_git_remote(tmp_path):
    """Explicit .nucleus-project marker wins, even inside a git repo w/ remote."""
    proj = _make_project(tmp_path, "dirname_ignored", git=True, marker="custom-slug\n")
    _add_remote(proj, "git@github.com:acme/widget.git")

    info = resolve_project(proj)
    assert isinstance(info, ProjectInfo)
    assert info.source == "marker"
    assert info.slug == "custom-slug"
    assert info.brain_root.resolve() == (proj / ".brain").resolve()


def test_detect_git_remote_beats_dirname(tmp_path):
    """No marker: git remote slug (repo name) beats the directory name."""
    proj = _make_project(tmp_path, "some-random-dir", git=True)
    _add_remote(proj, "git@github.com:acme/widget.git")

    info = resolve_project(proj)
    assert info is not None
    assert info.source == "git-remote"
    assert info.slug == "widget"


def test_detect_dirname_fallback(tmp_path):
    """Git repo with no remote: root is the git toplevel, slug falls back to
    the slugified directory name (marker absent, git-remote absent)."""
    proj = _make_project(tmp_path, "My Cool Project", git=True)  # git toplevel, no remote
    info = resolve_project(proj)
    assert info is not None
    assert info.source == "dirname"
    assert info.slug == "my-cool-project"


def test_detect_non_repo_returns_none(tmp_path):
    """A bare dir with no project signal returns None (caller falls through)."""
    bare = tmp_path / "nothing_here"
    bare.mkdir()
    assert resolve_project(bare) is None


def test_detect_invalid_marker_falls_through(tmp_path):
    """Empty/whitespace marker content is ignored → next arm (dirname) resolves."""
    proj = _make_project(tmp_path, "fallthrough-proj", git=False, marker="   \n\n")
    info = resolve_project(proj)
    assert info is not None
    assert info.source == "dirname"
    assert info.slug == "fallthrough-proj"
