"""A weekly self-test must not repoint the process at its own scratch dir (DS-7).

`seeded_block_instrument` and `cold_start_instrument` both set
`NUCLEUS_BRAIN_PATH` to a `TemporaryDirectory` and never put it back. One also
set `NUCLEUS_PROJECT_SPINE=1` and left it on. They run inside the long-lived
scheduler process, weekly, fifteen minutes apart.

Everything scheduled after them — the briefing, the analytics pass, the
orchestrator, the evening routine, and the weekly backup — then resolved its
brain from a directory that had already been deleted. `get_brain_path` creates
what is missing, so none of those jobs failed. They operated on an empty brain
and reported success, backup included.

This is the same shape as the tenant middleware leak (TN-5): a process-wide
value that outlives the work that set it becomes configuration.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

common = pytest.importorskip("mcp_server_nucleus.runtime.common")

RUNTIME = SRC / "mcp_server_nucleus" / "runtime"
INSTRUMENTS = ["seeded_block_instrument.py", "cold_start_instrument.py"]
LEAKY_VARS = ("NUCLEUS_BRAIN_PATH", "NUCLEUS_PROJECT_SPINE", "NUCLEAR_BRAIN_PATH")


# --- the helper itself ----------------------------------------------------


def test_temporary_env_restores_a_previous_value(monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/real/brain")
    with common.temporary_env(NUCLEUS_BRAIN_PATH="/tmp/scratch"):
        assert os.environ["NUCLEUS_BRAIN_PATH"] == "/tmp/scratch"
    assert os.environ["NUCLEUS_BRAIN_PATH"] == "/real/brain"


def test_temporary_env_unsets_what_was_unset(monkeypatch):
    """The case a naive restore gets wrong by writing back an empty string."""
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    with common.temporary_env(NUCLEUS_BRAIN_PATH="/tmp/scratch"):
        assert os.environ["NUCLEUS_BRAIN_PATH"] == "/tmp/scratch"
    assert "NUCLEUS_BRAIN_PATH" not in os.environ, (
        "an empty NUCLEUS_BRAIN_PATH is not the same as none; the resolver "
        "treats them differently"
    )


def test_temporary_env_restores_after_an_exception(monkeypatch):
    """An instrument that crashes must not leave the process repointed."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/real/brain")
    with pytest.raises(RuntimeError):
        with common.temporary_env(NUCLEUS_BRAIN_PATH="/tmp/scratch"):
            raise RuntimeError("instrument crashed")
    assert os.environ["NUCLEUS_BRAIN_PATH"] == "/real/brain"


def test_temporary_env_can_remove_a_variable(monkeypatch):
    monkeypatch.setenv("NUCLEUS_PROJECT_SPINE", "1")
    with common.temporary_env(NUCLEUS_PROJECT_SPINE=None):
        assert "NUCLEUS_PROJECT_SPINE" not in os.environ
    assert os.environ["NUCLEUS_PROJECT_SPINE"] == "1"


def test_temporary_env_handles_several_at_once(monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/real/brain")
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    with common.temporary_env(NUCLEUS_BRAIN_PATH="/tmp/x", NUCLEUS_PROJECT_SPINE="1"):
        pass
    assert os.environ["NUCLEUS_BRAIN_PATH"] == "/real/brain"
    assert "NUCLEUS_PROJECT_SPINE" not in os.environ


# --- the instruments ------------------------------------------------------


@pytest.mark.parametrize("name", INSTRUMENTS)
def test_the_instrument_restores_every_variable_it_sets(name):
    """Each leaky assignment must be matched by a restore in the same function."""
    path = RUNTIME / name
    if not path.exists():
        pytest.skip(f"{name} not in this export")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assigned = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and "environ" in ast.unparse(target)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value in LEAKY_VARS):
                    assigned.add(target.slice.value)

    if not assigned:
        return  # nothing set directly; temporary_env handles it

    # A bare assignment is only acceptable alongside an explicit restore.
    assert "environ.pop" in source or "temporary_env" in source, (
        f"{name} assigns {sorted(assigned)} into the process environment and "
        "never restores it. It runs inside the long-lived scheduler, so every "
        "job after it — the weekly backup included — inherits the value."
    )


@pytest.mark.parametrize("name", INSTRUMENTS)
def test_the_instrument_does_not_leave_a_temp_path_behind(name):
    """The specific harm: a brain path pointing into a deleted TemporaryDirectory."""
    path = RUNTIME / name
    if not path.exists():
        pytest.skip(f"{name} not in this export")
    source = path.read_text(encoding="utf-8")
    if "TemporaryDirectory" not in source or "NUCLEUS_BRAIN_PATH" not in source:
        return
    assert "temporary_env" in source or "_prev_env" in source, (
        f"{name} points NUCLEUS_BRAIN_PATH at a TemporaryDirectory with no "
        "restore, so after it runs the process resolves its brain from a path "
        "that no longer exists — and get_brain_path recreates it rather than "
        "failing, so nothing reports a problem"
    )


# --- process-wide brain writes outside the instruments (DS-8) -------------


def test_the_depth_tracker_does_not_pin_the_process_to_a_relative_path():
    """It wrote NUCLEUS_BRAIN_PATH=".brain" from a per-request constructor.

    Relative, so it named no particular brain; process-wide, so the first
    request without one pinned every later request; and it short-circuited
    get_brain_path's own contextvar / project / walk-up fallback, which answers
    the same question better.
    """
    path = RUNTIME / "capabilities" / "depth_tracker.py"
    if not path.exists():
        pytest.skip("depth_tracker not in this export")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    writes = [
        n.lineno for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Subscript) and "environ" in ast.unparse(t)
    ]
    assert not writes, (
        f"depth_tracker writes to os.environ at line(s) {writes}. It is built "
        "per request on a long-lived server, and depth_ops resolves its own "
        "brain via get_brain_path, so nothing here needs to."
    )


def test_the_lane_brain_switch_is_documented_where_a_caller_will_see_it():
    """isolate_brain repoints the process on purpose; that must not be a surprise.

    Not asserting it restores — it is meant to outlive the call, and guessing
    otherwise would break the lane workflow. Asserting only that the side effect
    is stated at both ends, which is what was actually missing.
    """
    isolation = RUNTIME / "lane" / "isolation.py"
    tool = SRC / "mcp_server_nucleus" / "tools" / "lane.py"
    for path, needle in ((isolation, "repoints the WHOLE PROCESS"),
                         (tool, "switches the brain for the rest of the session")):
        if not path.exists():
            pytest.skip(f"{path.name} not in this export")
        assert needle in path.read_text(encoding="utf-8"), (
            f"{path.name} no longer warns that initializing a lane changes which "
            "brain the session uses"
        )
