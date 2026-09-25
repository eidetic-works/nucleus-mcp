"""
Regression + unit tests for ADR-0042 "Project Spine" batch XY-3 (D6 lifecycle).

Covers the entrypoint ContextVar wiring:
  * init_project_context() — the flag-gated setter that _ensure_initialized()
    calls at every entrypoint (stdio main / http build_app+main / cli-schema):
      - Flag ON, cwd inside a project, NO env var  -> the project ContextVar is
        populated; get_current_project() returns the detected ProjectInfo.
      - Flag OFF                                    -> the ContextVar stays at
        its None default (today's behavior, byte-identical).
      - Flag ON, cwd not a project                  -> stays None (env remains
        authoritative).
  * Structural sentinel: flag OFF never imports/calls runtime.project.
  * End-to-end entrypoint proof (fresh subprocess): a real process that runs the
    _ensure_initialized() entry contract in a project cwd with NO NUCLEUS_BRAIN_PATH
    set — flag ON sees the project; flag OFF sees today's behavior (None).

The autouse conftest fixtures reset the flag (_clean_project_spine_flag is local
to test_project_spine.py; here we toggle NUCLEUS_PROJECT_SPINE per-test via
monkeypatch) and the _current_project ContextVar (_reset_project_contextvar).
Unit tests run the set+read inside contextvars.copy_context() so the process
ContextVar is never mutated by the assertion itself (belt over the fixture's
suspenders), matching the #653 stale-reference discipline.
"""

import contextvars
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import mcp_server_nucleus
from mcp_server_nucleus.runtime.common import (
    get_current_project,
    init_project_context,
    set_current_project,
)
from mcp_server_nucleus.runtime.project import ProjectInfo


# ──────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────
def _make_marker_project(base, name="lifecycle-proj", *, brain=True, slug="lifecycle-proj"):
    """Create a detectable project via an explicit .nucleus-project marker.

    Marker-based (no git) keeps detection deterministic and offline. Returns the
    project root Path. The marker's first non-empty line is the resolved slug.
    """
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    (root / ".nucleus-project").write_text(f"{slug}\n", encoding="utf-8")
    if brain:
        (root / ".brain").mkdir(exist_ok=True)
    return root


def _init_and_read():
    """Run init_project_context() then read the accessor — same context."""
    init_project_context()
    return get_current_project()


# ──────────────────────────────────────────────────────────────
# init_project_context() — the seam _ensure_initialized() calls
# ──────────────────────────────────────────────────────────────
def test_flag_on_sets_project_from_cwd_without_env(tmp_path, monkeypatch):
    """Flag ON: a project cwd populates the ContextVar — no env var needed."""
    proj = _make_marker_project(tmp_path, slug="widget")
    monkeypatch.chdir(proj)
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    result = contextvars.copy_context().run(_init_and_read)

    assert isinstance(result, ProjectInfo)
    assert result.slug == "widget"
    assert result.source == "marker"
    assert result.brain_root.resolve() == (proj / ".brain").resolve()


def test_flag_off_leaves_contextvar_none(tmp_path, monkeypatch):
    """Flag OFF: same project cwd, the ContextVar stays None (today's behavior)."""
    proj = _make_marker_project(tmp_path, slug="widget")
    monkeypatch.chdir(proj)
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)  # flag OFF

    result = contextvars.copy_context().run(_init_and_read)

    assert result is None


def test_flag_on_no_project_leaves_none(tmp_path, monkeypatch):
    """Flag ON but cwd is not a detectable project: stays None (env stays boss)."""
    bare = tmp_path / "scratch" / "deep"
    bare.mkdir(parents=True)
    monkeypatch.chdir(bare)
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")

    result = contextvars.copy_context().run(_init_and_read)

    assert result is None


def test_flag_off_never_touches_project_module(tmp_path, monkeypatch):
    """Flag OFF ⇒ init_project_context never imports/calls runtime.project.

    Booby-trap resolve_project to detonate. If init_project_context reached it on
    the flag-OFF path, this would raise; the ContextVar must also remain None.
    Locks the #653-class structural guarantee: the disabled feature's detector
    stays inert on the OFF path.
    """
    import mcp_server_nucleus.runtime.project as project_mod

    def _sentinel(*_args, **_kwargs):
        raise RuntimeError("resolve_project must not run on the flag-OFF path")

    monkeypatch.setattr(project_mod, "resolve_project", _sentinel)
    proj = _make_marker_project(tmp_path, slug="widget")
    monkeypatch.chdir(proj)
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)  # flag OFF

    result = contextvars.copy_context().run(_init_and_read)

    assert result is None


# ──────────────────────────────────────────────────────────────
# accessor / setter round-trip
# ──────────────────────────────────────────────────────────────
def test_set_and_get_current_project_roundtrip(tmp_path):
    """set_current_project / get_current_project are the only reach into the var."""
    info = ProjectInfo(slug="acme", brain_root=tmp_path / ".brain", source="marker")

    def _roundtrip():
        assert get_current_project() is None  # default within a fresh context
        set_current_project(info)
        return get_current_project()

    assert contextvars.copy_context().run(_roundtrip) is info


# ──────────────────────────────────────────────────────────────
# End-to-end: a real entrypoint process (stdio/cli init contract)
# ──────────────────────────────────────────────────────────────
def _run_entrypoint_process(proj: Path, *, flag_on: bool) -> str:
    """Spawn a fresh process that runs the _ensure_initialized() entry contract.

    Proves the ACTUAL D6 wiring (not just the helper): _ensure_initialized() —
    the seam every entrypoint (stdio main / http build_app+main / cli-schema)
    routes through — sets the project ContextVar. Runs with cwd=proj and NO
    NUCLEUS_BRAIN_PATH in the environment. Returns the printed "PROJECT=<slug|NONE>".
    """
    src = str(Path(mcp_server_nucleus.__file__).resolve().parents[1])
    code = textwrap.dedent(
        """
        import sys
        import mcp_server_nucleus as m
        m._ensure_initialized()  # the unified entrypoint contract (D6 seam)
        from mcp_server_nucleus.runtime.common import get_current_project
        p = get_current_project()
        sys.stdout.write("PROJECT=" + (p.slug if p is not None else "NONE") + "\\n")
        """
    )
    env = {k: v for k, v in os.environ.items() if k != "NUCLEUS_BRAIN_PATH"}
    env["PYTHONPATH"] = src
    if flag_on:
        env["NUCLEUS_PROJECT_SPINE"] = "1"
    else:
        env.pop("NUCLEUS_PROJECT_SPINE", None)

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(proj),
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, (
        f"entrypoint process failed (rc={result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    for line in result.stdout.splitlines():
        if line.startswith("PROJECT="):
            return line[len("PROJECT="):]
    raise AssertionError(f"no PROJECT= line in stdout:\n{result.stdout}\n{result.stderr}")


def test_entrypoint_flag_on_process_sees_project_without_env(tmp_path):
    """Flag ON: a fresh CLI/stdio process in a project cwd sees the project
    with NO NUCLEUS_BRAIN_PATH set — the D6 entrypoint wiring in the wild."""
    proj = _make_marker_project(tmp_path, slug="widget")
    assert _run_entrypoint_process(proj, flag_on=True) == "widget"


def test_entrypoint_flag_off_process_matches_today(tmp_path):
    """Flag OFF: the same process leaves the project ContextVar unset (None) —
    byte-identical to pre-spine startup."""
    proj = _make_marker_project(tmp_path, slug="widget")
    assert _run_entrypoint_process(proj, flag_on=False) == "NONE"
