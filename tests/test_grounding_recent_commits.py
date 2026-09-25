"""Tests for recent-commits grounding: `_collect_recent_commits` + `nucleus_ground`.

Covers:
  (a) `_collect_recent_commits` returns valid items on a real git repo
  (b) returns None on a non-git directory
  (c) returns None when `git` is not on PATH (FileNotFoundError)
  (d) returns None on subprocess timeout (TimeoutExpired)
  (e) `nucleus_ground` with include_recent_commits=True -> section present
  (f) `nucleus_ground` with include_recent_commits=False -> section absent

NOTE: the implementation returns items with keys {sha, subject, author, date,
files} — there is no `age` field. Tests assert the real shape.
"""

import subprocess
import sys
import types
from pathlib import Path

import pytest

from mcp_server_nucleus.selfhealer import _collect_recent_commits
from mcp_server_nucleus.tools.grounding import register


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _git(args, cwd):
    """Run a git command, returning the CompletedProcess."""
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False,
    )


@pytest.fixture
def git_repo(tmp_path):
    """A real git repo with one commit, rooted at tmp_path."""
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@t.t"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    (tmp_path / "hello.txt").write_text("hello\n")
    _git(["add", "."], tmp_path)
    _git(["commit", "-q", "-m", "initial commit"], tmp_path)
    return tmp_path


class _FakeMCP:
    """Minimal MCP stand-in: `.tool()` returns an identity decorator.

    Accepts **kwargs because the real `mcp.tool()` takes `title` and
    `annotations`, and most tools in this package pass them. This double
    declared `tool(self)` with no parameters, so the moment nucleus_ground
    gained annotations it raised
    `TypeError: _FakeMCP.tool() got an unexpected keyword argument 'title'` --
    a test failing on the SHAPE of the call rather than on behaviour.

    A double narrower than the interface it stands in for does not protect the
    code; it just breaks whenever the code starts using the real thing
    properly.
    """

    def tool(self, *args, **kwargs):
        def deco(fn):
            return fn
        return deco


def _install_fake_providers(monkeypatch, brain_path):
    """Inject a stub `providers.brain_rag` so `nucleus_ground` can run
    without the real RAG/embedding stack. `search_brain` returns [] so no
    non-recent-commits sections are populated."""
    fake_providers = types.ModuleType("providers")
    fake_brain_rag = types.ModuleType("providers.brain_rag")
    fake_brain_rag.OLLAMA_URL = ""
    fake_brain_rag.BRAIN_PATH = brain_path
    fake_brain_rag._read_brain_owner = lambda bp: "test-project"
    fake_brain_rag.search_brain = lambda *a, **k: []
    fake_providers.brain_rag = fake_brain_rag
    monkeypatch.setitem(sys.modules, "providers", fake_providers)
    monkeypatch.setitem(sys.modules, "providers.brain_rag", fake_brain_rag)


def _build_nucleus_ground(brain_path):
    """Register the grounding tool against fakes and return the callable."""
    helpers = {
        "make_response": lambda ok, data=None, error=None: {
            "ok": ok, "data": data, "error": error,
        },
        "get_brain_path": lambda: str(brain_path),
    }
    tools = register(_FakeMCP(), helpers)
    # register() returns [(name, func)] pairs -- the shape register_all()
    # unpacks at tools/__init__.py:15 (`for name, func in result:`). This
    # helper used to do `return tools[0]`, which worked ONLY while grounding.py
    # returned a bare [func] instead of pairs. That bare list is precisely why
    # grounding was the one module register_all could not load ("cannot unpack
    # non-iterable CallableTool object"). The test that should have caught the
    # bug was written against it, which is why it never surfaced.
    assert tools and isinstance(tools[0], tuple), (
        f"register() must return (name, func) pairs, got {type(tools[0]).__name__}"
    )
    _name, func = tools[0]
    # Name pinned too (from the mirror PR): shape alone would pass for any
    # correctly-shaped pair, and this facade must register as nucleus_ground.
    assert _name == "nucleus_ground", f"expected nucleus_ground, got {_name!r}"
    return func


# ---------------------------------------------------------------------------
# (a) real git repo -> valid items
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_recent_commits_real_repo(git_repo):
    items = _collect_recent_commits(git_repo)
    assert items is not None, "expected items from a real git repo"
    assert isinstance(items, list)
    assert len(items) >= 1
    item = items[0]
    # Real shape: sha, subject, author, date, files
    assert "sha" in item and isinstance(item["sha"], str) and item["sha"]
    assert "subject" in item and item["subject"] == "initial commit"
    assert "files" in item and isinstance(item["files"], list)
    assert "hello.txt" in item["files"]


# ---------------------------------------------------------------------------
# (b) non-git directory -> None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_recent_commits_non_git_dir(tmp_path):
    # tmp_path exists but is not a git repo
    items = _collect_recent_commits(tmp_path)
    assert items is None


# ---------------------------------------------------------------------------
# (c) git not on PATH (FileNotFoundError) -> None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_recent_commits_git_missing(monkeypatch, git_repo):
    def _raise_file_not_found(*a, **k):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("mcp_server_nucleus.selfhealer.subprocess.run",
                        _raise_file_not_found)
    items = _collect_recent_commits(git_repo)
    assert items is None


# ---------------------------------------------------------------------------
# (d) subprocess timeout -> None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_recent_commits_timeout(monkeypatch, git_repo):
    def _raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd=a[0] if a else "git", timeout=5)

    monkeypatch.setattr("mcp_server_nucleus.selfhealer.subprocess.run",
                        _raise_timeout)
    items = _collect_recent_commits(git_repo)
    assert items is None


# ---------------------------------------------------------------------------
# (e) nucleus_ground(include_recent_commits=True) -> section present
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nucleus_ground_includes_recent_commits(git_repo, monkeypatch):
    brain_path = git_repo / ".brain"
    brain_path.mkdir()
    _install_fake_providers(monkeypatch, brain_path)
    nucleus_ground = _build_nucleus_ground(brain_path)

    result = await nucleus_ground(
        task_context="",
        session_id="",
        include_plan=True,
        include_codebase=True,
        include_recent_commits=True,
    )
    assert result["ok"] is True
    sections = result["data"]["sections"]
    assert "recent_commits" in sections
    assert sections["recent_commits"]["count"] >= 1
    assert isinstance(sections["recent_commits"]["items"], list)


# ---------------------------------------------------------------------------
# (f) nucleus_ground(include_recent_commits=False) -> section absent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nucleus_ground_excludes_recent_commits(git_repo, monkeypatch):
    brain_path = git_repo / ".brain"
    brain_path.mkdir()
    _install_fake_providers(monkeypatch, brain_path)
    nucleus_ground = _build_nucleus_ground(brain_path)

    result = await nucleus_ground(
        task_context="",
        session_id="",
        include_plan=True,
        include_codebase=True,
        include_recent_commits=False,
    )
    assert result["ok"] is True
    sections = result["data"]["sections"]
    assert "recent_commits" not in sections
