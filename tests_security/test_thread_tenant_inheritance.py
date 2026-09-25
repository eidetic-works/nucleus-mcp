"""Background threads must inherit the request's tenant (TN-4).

`threading.Thread` starts with a fresh `Context`. Both orchestrators launched
mission execution with a plain `Thread(target=...)`, so `_tenant_brain_path` was
unset inside the thread and `get_brain_path()` fell through to `os.environ` or a
cwd walk — resolving whichever brain the process environment happened to name.

The tenant middleware clears those env vars in a `finally` (TN-5), which widens
the window rather than narrowing it: by the time a background thread runs, the
request that started it has usually returned, so the fallback lands on the
process default or a stale value rather than the mission's own tenant.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import ast
import sys
import threading
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

common = pytest.importorskip("mcp_server_nucleus.runtime.common")


@pytest.fixture(autouse=True)
def clear_contextvar():
    common.set_tenant_brain_path(None)
    yield
    common.set_tenant_brain_path(None)


def _capture_in_thread(start) -> object:
    """Run a thread via `start` and report the brain path it observed."""
    seen = {}

    def target():
        seen["path"] = common._tenant_brain_path.get()

    thread = start(target)
    thread.join(timeout=10)
    assert not thread.is_alive(), "the worker thread did not finish"
    return seen.get("path")


def test_a_plain_thread_does_not_see_the_tenant():
    """The behaviour being fixed. If this ever fails, the premise changed."""
    common.set_tenant_brain_path("/brains/tenant-a/.brain")

    def start(target):
        t = threading.Thread(target=target, daemon=True)
        t.start()
        return t

    assert _capture_in_thread(start) is None


def test_start_tenant_thread_carries_the_tenant_in():
    common.set_tenant_brain_path("/brains/tenant-a/.brain")
    observed = _capture_in_thread(
        lambda target: common.start_tenant_thread(target, name="t")
    )
    assert observed == "/brains/tenant-a/.brain", (
        "the background thread resolved a different brain than the request that "
        "started it — a mission started by one tenant could write into another's"
    )


def test_two_tenants_do_not_share_a_context():
    """A single Context cannot be entered twice; each start must copy its own."""
    results = {}
    threads = []
    for tenant in ("tenant-a", "tenant-b"):
        common.set_tenant_brain_path(f"/brains/{tenant}/.brain")
        started = threading.Event()

        def target(t=tenant, ev=started):
            results[t] = common._tenant_brain_path.get()
            ev.set()

        threads.append((common.start_tenant_thread(target, name=tenant), started))
    for thread, started in threads:
        thread.join(timeout=10)
        assert started.is_set()
    assert results == {
        "tenant-a": "/brains/tenant-a/.brain",
        "tenant-b": "/brains/tenant-b/.brain",
    }


def test_an_unset_tenant_stays_unset():
    """CLI and stdio never set the contextvar; the copy must stay empty."""
    assert _capture_in_thread(
        lambda target: common.start_tenant_thread(target, name="t")
    ) is None


def test_the_thread_is_returned_and_daemon_by_default():
    """The old call sites relied on both."""
    done = threading.Event()
    thread = common.start_tenant_thread(done.set, name="t")
    assert isinstance(thread, threading.Thread)
    assert thread.daemon
    thread.join(timeout=10)
    assert done.is_set()


def test_a_raising_target_does_not_take_the_process_down():
    """A mission that raises must not be made worse by the context wrapper."""
    def boom():
        raise RuntimeError("mission failed")

    # The raise is the point of the test, so swallow it at the thread hook
    # rather than letting it surface as an unhandled-thread warning that reads
    # like a real failure in CI output.
    caught = []
    previous = threading.excepthook
    threading.excepthook = caught.append
    try:
        thread = common.start_tenant_thread(boom, name="t")
        thread.join(timeout=10)
    finally:
        threading.excepthook = previous

    assert not thread.is_alive()
    assert caught and caught[0].exc_type is RuntimeError, (
        "the exception was swallowed somewhere inside the wrapper"
    )


# --- the call sites must actually use it ----------------------------------

ORCHESTRATORS = (
    SRC / "mcp_server_nucleus" / "runtime" / "orchestrator_unified.py",
    SRC / "mcp_server_nucleus" / "runtime" / "orchestrator.py",
)


@pytest.mark.parametrize("path", ORCHESTRATORS, ids=lambda p: p.name)
def test_mission_launch_does_not_use_a_raw_thread(path):
    if not path.exists():
        pytest.skip(f"{path.name} not in this export")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    raw = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Thread"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "threading"
    ]
    assert not raw, (
        f"{path.name} still launches a raw threading.Thread at line(s) "
        f"{[n.lineno for n in raw]}; it starts with a fresh Context and will not "
        "see the request's tenant"
    )
    assert "start_tenant_thread" in path.read_text(encoding="utf-8"), (
        f"{path.name} does not use start_tenant_thread"
    )
