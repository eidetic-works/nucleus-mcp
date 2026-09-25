"""The protected-path firewall must fire on the shape calls actually have (CP-2).

The original guard lived in the pre-facade `CallableTool` wrapper and matched
tool names like `nucleus_delete_file` reading `kwargs["path"]`. The facade
migration made every real call look like
`nucleus_governance(action="delete_file", params={"path": ...})`, so the name
never matched and the path was a level deeper than the hook looked. It could not
fire. These tests pin the replacement to the shape dispatch actually unpacks.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_dispatch = pytest.importorskip("mcp_server_nucleus.tools._dispatch")


class FakeWatchdog:
    def __init__(self, paths):
        self.protected_paths = [str(p) for p in paths]


@pytest.fixture
def protected(tmp_path, monkeypatch):
    """Point the firewall at a real protected directory."""
    guarded = tmp_path / "guarded"
    guarded.mkdir()
    import types
    fake = types.ModuleType("mcp_server_nucleus.runtime.hypervisor_ops")
    fake._watchdog = FakeWatchdog([guarded])
    monkeypatch.setitem(sys.modules, "mcp_server_nucleus.runtime.hypervisor_ops", fake)
    return guarded


def test_write_inside_a_protected_path_is_refused(protected):
    refusal = _dispatch.check_protected_path(
        "nucleus_governance", "delete_file", {"path": str(protected / "secrets.json")}
    )
    assert refusal and "firewall" in refusal.lower()


def test_the_protected_root_itself_is_refused(protected):
    assert _dispatch.check_protected_path(
        "nucleus_governance", "write_file", {"path": str(protected)}
    )


@pytest.mark.parametrize("key", ["path", "file_path", "target_file", "TargetFile", "AbsolutePath"])
def test_every_path_param_spelling_is_checked(protected, key):
    """The pre-facade hook accepted several spellings; so must this one."""
    assert _dispatch.check_protected_path(
        "nucleus_governance", "write_file", {key: str(protected / "x")}
    ), f"a path passed as {key!r} slipped through"


def test_a_path_outside_the_protected_root_is_allowed(protected, tmp_path):
    assert _dispatch.check_protected_path(
        "nucleus_governance", "delete_file", {"path": str(tmp_path / "elsewhere.txt")}
    ) is None


def test_a_sibling_with_the_same_prefix_is_not_treated_as_inside(protected):
    """`/a/guarded-other` must not match `/a/guarded`."""
    sibling = str(protected) + "-other"
    assert _dispatch.check_protected_path(
        "nucleus_governance", "delete_file", {"path": sibling + "/f.txt"}
    ) is None


def test_read_actions_are_not_blocked(protected):
    """Reading a protected path is not the threat the watchdog exists to stop."""
    assert _dispatch.check_protected_path(
        "nucleus_governance", "read_file", {"path": str(protected / "x")}
    ) is None


def test_calls_without_a_path_are_ignored(protected):
    assert _dispatch.check_protected_path("nucleus_tasks", "write_task", {"title": "x"}) is None
    assert _dispatch.check_protected_path("nucleus_tasks", "write_task", None) is None


def test_both_dispatchers_call_the_firewall():
    """Most facades route through async_dispatch; guarding only sync leaves the
    majority of the surface open."""
    import ast

    src = Path(_dispatch.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for name in ("dispatch", "async_dispatch"):
        fn = next(
            (n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name),
            None,
        )
        assert fn is not None, f"_dispatch.py has no {name}()"
        calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "check_protected_path"
        ]
        assert calls, f"{name}() never calls check_protected_path"
