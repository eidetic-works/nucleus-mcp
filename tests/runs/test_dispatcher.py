"""Tests for the real run dispatcher."""
from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.dispatcher import RunDispatcher
from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.models import RunState


TERMINAL_STATES = {
    RunState.READY_FOR_REVIEW,
    RunState.COMPLETED,
    RunState.FAILED,
    RunState.CANCELLED,
    RunState.APPLIED,
    RunState.DISMISSED,
}


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _install_fake_agy(tmp_path: Path, script: str) -> Path:
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    script_path = bindir / "agy"
    script_path.write_text("#!/bin/sh\n" + script)
    script_path.chmod(0o755)
    return bindir


def _setup_env(monkeypatch, fakebin: Path) -> None:
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")


def test_dispatcher_runs_queued_run(tmp_path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _install_fake_agy(
        tmp_path,
        'cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n',
    )
    _setup_env(monkeypatch, fakebin)

    db = tmp_path / "runs.db"
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "test conversation")
    run_id = adapter.create_run(conv_id, "write a file", idempotency_key="k1")

    dispatcher = RunDispatcher(db)
    assert dispatcher.run_once() == 1

    run = dispatcher._store.get_run(run_id)
    assert run.state in TERMINAL_STATES

    bundle = dispatcher._service.get_run_bundle(run_id)
    assert bundle.output.strip() == "done"

    events = dispatcher._store.list_events(run_id)
    assert events
    terminal_events = [e for e in events if e.type in ("run.ready_for_review", "run.completed", "run.failed", "run.cancelled")]
    assert terminal_events


def test_dispatcher_emits_run_output_events(tmp_path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _install_fake_agy(
        tmp_path,
        'printf "line1\\nline2\\nline3\\n"\n',
    )
    _setup_env(monkeypatch, fakebin)

    db = tmp_path / "runs.db"
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "test conversation")
    run_id = adapter.create_run(conv_id, "write lines", idempotency_key="k1")

    dispatcher = RunDispatcher(db)
    assert dispatcher.run_once() == 1

    run = dispatcher._store.get_run(run_id)
    assert run.state in TERMINAL_STATES

    events = dispatcher._store.list_events(run_id)
    output_events = [e for e in events if e.type == "run.output"]
    assert output_events
    assert any("line1" in (e.payload or {}).get("chunk", "") for e in output_events)


def test_dispatcher_concurrency_one_per_workspace(tmp_path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _install_fake_agy(
        tmp_path,
        'cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n',
    )
    _setup_env(monkeypatch, fakebin)

    db = tmp_path / "runs.db"
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "test conversation")
    run1_id = adapter.create_run(conv_id, "first", idempotency_key="k1")
    run2_id = adapter.create_run(conv_id, "second", idempotency_key="k2")

    # Put both runs on the same pre-declared workspace so the dispatcher must
    # gate them per-workspace, not just by global active count.
    shared_workspace = str(tmp_path / "shared-workspace")
    adapter._store.set_run_workspace(run1_id, workspace=shared_workspace)
    adapter._store.set_run_workspace(run2_id, workspace=shared_workspace)

    dispatcher = RunDispatcher(db, max_concurrent=2)
    assert dispatcher.run_once() == 2

    run1 = dispatcher._store.get_run(run1_id)
    run2 = dispatcher._store.get_run(run2_id)
    assert run1.state in TERMINAL_STATES
    assert run2.state in TERMINAL_STATES

    events1 = dispatcher._store.list_events(run1_id)
    events2 = dispatcher._store.list_events(run2_id)

    active_types = {"run.preparing", "run.running", "run.verifying"}
    terminal_types = {"run.ready_for_review", "run.completed", "run.failed", "run.cancelled"}

    run1_terminal_times = [
        e.created_at for e in events1 if e.type in terminal_types
    ]
    run2_active_times = [
        e.created_at for e in events2 if e.type in active_types
    ]

    assert run1_terminal_times
    assert run2_active_times
    # The first run must be terminal before the second one starts active work.
    assert max(run1_terminal_times) <= min(run2_active_times)


def test_dispatcher_cancel(tmp_path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    # A slow vendor so the cancel can land while the run is in-flight.
    fakebin = _install_fake_agy(
        tmp_path,
        'for i in $(seq 1 20); do echo "line $i"; sleep 0.1; done\necho done\nexit 0\n',
    )
    _setup_env(monkeypatch, fakebin)

    db = tmp_path / "runs.db"
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "test conversation")
    run_id = adapter.create_run(conv_id, "count", idempotency_key="k1")

    dispatcher = RunDispatcher(db, poll_interval=0.1)
    stop = threading.Event()
    thread = threading.Thread(target=dispatcher.serve, args=(stop,))
    thread.start()

    try:
        time.sleep(0.05)
        adapter.cancel_run(run_id)

        for _ in range(100):  # wait up to ~10s
            run = dispatcher._store.get_run(run_id)
            if run.state in TERMINAL_STATES:
                break
            time.sleep(0.1)

        run = dispatcher._store.get_run(run_id)
        assert run.state == RunState.CANCELLED
    finally:
        stop.set()
        thread.join(timeout=5.0)
