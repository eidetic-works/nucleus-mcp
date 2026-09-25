"""Tests for the `nucleus work` CLI using `python -m mcp_server_nucleus.cli work`."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


_TERMINAL_STATES = frozenset(
    {
        "ready_for_review",
        "completed",
        "failed",
        "cancelled",
        "dismissed",
        "applied",
    }
)


def _init_project_git(project_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=project_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=project_path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=project_path, check=True)
    (project_path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project_path, check=True)


def _make_fake_agy(bin_dir: Path) -> Path:
    agy_path = bin_dir / "agy"
    agy_path.write_text("#!/bin/bash\nset -e\necho 'agy ran'\necho 'agy ran' > agy_ran.txt\n")
    agy_path.chmod(0o755)
    return agy_path


def _run_work(args, cwd, env, timeout=60):
    return subprocess.run(
        [sys.executable, "-m", "mcp_server_nucleus.cli", "work", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def test_nucleus_work_list_exits_zero(tmp_path):
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(tmp_path / ".brain")
    result = _run_work(["list"], tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "No runs found." in result.stdout


def test_nucleus_work_run_executes_queued(tmp_path):
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_agy(bin_dir)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "do work")

    run_result = _run_work(["run", "--run", run_id], tmp_path, env)
    assert run_result.returncode == 0, run_result.stderr

    show_result = _run_work(["show", run_id], tmp_path, env)
    assert show_result.returncode == 0, show_result.stderr
    data = json.loads(show_result.stdout)
    assert data["run"]["state"] in _TERMINAL_STATES

    output_events = [
        ev for ev in data["events"] if ev["type"] == "run.output"
    ]
    assert output_events
    assert any(
        "agy ran" in (ev.get("payload") or {}).get("chunk", "")
        for ev in output_events
    )

    workspace = Path(data["run"]["workspace"])
    assert (workspace / "agy_ran.txt").exists()


def test_nucleus_work_watch(tmp_path):
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_agy(bin_dir)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "do work")

    run_result = _run_work(["run", "--run", run_id], tmp_path, env)
    assert run_result.returncode == 0, run_result.stderr

    watch_result = _run_work(["watch", run_id], tmp_path, env)
    assert watch_result.returncode == 0, watch_result.stderr
    assert "agy ran" in watch_result.stdout


def test_nucleus_work_status_no_daemon(tmp_path):
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(tmp_path / ".brain")
    result = _run_work(["status"], tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "Dispatcher running: False" in result.stdout


def test_nucleus_entrypoint_work_list(tmp_path):
    """The installed `nucleus` binary exposes `work list`."""
    import shutil

    nucleus = shutil.which("nucleus")
    assert nucleus, "nucleus not found on PATH"

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(tmp_path / ".brain")
    result = subprocess.run(
        [nucleus, "work", "list"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "No runs found." in result.stdout


def test_nucleus_work_doctor_reports_checks(tmp_path):
    """doctor prints per-check PASS/FAIL and a dispatcher fix when not running."""
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(tmp_path / ".brain")
    result = _run_work(["doctor"], tmp_path, env)
    assert "PASS python" in result.stdout
    assert "FAIL dispatcher" in result.stdout or "PASS dispatcher" in result.stdout
    assert result.returncode in (0, 1)


def test_nucleus_work_create_queues_run(tmp_path):
    """create with --project-root queues a new run and prints the run id."""
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)

    result = _run_work(
        ["create", f"--project-root={project}", "--prompt=do work"],
        tmp_path,
        env,
    )
    assert result.returncode == 0, result.stderr
    run_id = result.stdout.strip()
    assert run_id

    show = _run_work(["show", run_id], tmp_path, env)
    assert show.returncode == 0, show.stderr
    data = json.loads(show.stdout)
    assert data["run"]["state"] == "queued"


def test_nucleus_work_backup_and_export(tmp_path):
    """create -> backup the DB -> export the run."""
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_agy(bin_dir)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

    create = _run_work(
        ["create", f"--project-root={project}", "--prompt=do work"],
        tmp_path,
        env,
    )
    assert create.returncode == 0, create.stderr
    run_id = create.stdout.strip()
    assert run_id

    backup_dir = tmp_path / "backups"
    backup = _run_work(
        ["backup", f"--output={backup_dir}"],
        tmp_path,
        env,
    )
    assert backup.returncode == 0, backup.stderr
    data = json.loads(backup.stdout)
    assert Path(data["backup_path"]).exists()

    export = _run_work(
        ["export", run_id, f"--output={tmp_path / 'run.json'}"],
        tmp_path,
        env,
    )
    assert export.returncode == 0, export.stderr
    out = json.loads(export.stdout)
    assert Path(out["output"]).exists()
    exported = json.loads(Path(out["output"]).read_text())
    assert exported["run"]["id"] == run_id
    assert "project" in exported
    assert "conversation" in exported


def test_nucleus_work_new_app_smoke_path(tmp_path):
    """Empty git repo + create -> run -> apply ends in a committed file."""
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    agy = bin_dir / "agy"
    agy.write_text("#!/bin/bash\nset -e\necho 'scaffolded' > app.txt\n")
    agy.chmod(0o755)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

    create = _run_work(
        ["create", f"--project-root={project}", "--prompt=scaffold"],
        tmp_path,
        env,
    )
    assert create.returncode == 0, create.stderr
    run_id = create.stdout.strip()

    run = _run_work(["run", "--run", run_id], tmp_path, env)
    assert run.returncode == 0, run.stderr

    show = _run_work(["show", run_id], tmp_path, env)
    data = json.loads(show.stdout)
    assert data["run"]["state"] in _TERMINAL_STATES

    # apply the run
    apply = _run_work(["apply", run_id], tmp_path, env)
    assert apply.returncode == 0, apply.stderr

    assert (project / "app.txt").exists()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project, capture_output=True, text=True)
    assert "app.txt" in status.stdout


def test_work_run_follow_streams_output_events(tmp_path):
    """`work run --run <id> --follow` prints run.output chunks in real time."""
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_agy(bin_dir)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "do work")

    run_result = _run_work(["run", "--run", run_id, "--follow"], tmp_path, env)
    assert run_result.returncode == 0, run_result.stderr
    assert "agy ran" in run_result.stdout

    show = _run_work(["show", run_id], tmp_path, env)
    assert show.returncode == 0, show.stderr
    data = json.loads(show.stdout)
    assert data["run"]["state"] in _TERMINAL_STATES


def test_work_watch_text_mode_prints_chunks(tmp_path):
    """`work watch --text <id>` prints chunks as plain text and stops at terminal state."""
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_fake_agy(bin_dir)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "do work")

    run_result = _run_work(["run", "--run", run_id], tmp_path, env)
    assert run_result.returncode == 0, run_result.stderr

    watch_result = _run_work(["watch", "--text", run_id], tmp_path, env)
    assert watch_result.returncode == 0, watch_result.stderr
    assert "agy ran" in watch_result.stdout
    # No JSON wrappers: the output should not be parseable as a JSON object.
    with pytest.raises(json.JSONDecodeError):
        json.loads(watch_result.stdout)


def test_work_preview_captures_url(tmp_path):
    """Previewing a workspace captures the first URL and the CLI prints it."""
    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "do work")

    resolver = WorkspaceResolver()
    backend = resolver.resolve_backend(project)
    ws = backend.create(project, run_id)
    adapter._store.set_run_workspace(
        run_id,
        workspace=str(ws.target_path),
        base_revision=ws.base_revision,
    )

    store = adapter._store
    store.transition_run(run_id, RunState.PREPARING, "run.preparing")
    store.transition_run(run_id, RunState.RUNNING, "run.running")
    store.transition_run(run_id, RunState.VERIFYING, "run.verifying")
    store.transition_run(run_id, RunState.READY_FOR_REVIEW, "run.ready_for_review")

    artifact = adapter._service.preview_run(run_id, "echo 'http://localhost:3000'")
    assert artifact is not None

    run = store.get_run(run_id)
    assert run.state is RunState.PREVIEWED

    artifacts = store.list_artifacts(run_id)
    preview_artifacts = [a for a in artifacts if a.mime_type == "text/x-preview-url"]
    assert len(preview_artifacts) == 1
    assert preview_artifacts[0].metadata["url"] == "http://localhost:3000"

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    result = _run_work(["preview", f"--run={run_id}"], tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "http://localhost:3000" in result.stdout


def test_nucleus_work_gc_prunes_terminal_workspaces(tmp_path):
    from mcp_server_nucleus.runs.store import RunStore

    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "do work")

    store = RunStore(str(db))
    store.transition_run(run_id, RunState.PREPARING, "run.preparing")
    store.transition_run(run_id, RunState.FAILED, "run.failed")

    ws_root = brain / "runs" / "workspaces"
    ws_root.mkdir(parents=True)
    dead = ws_root / f"nucleus-run-{run_id}"
    dead.mkdir()
    (dead / "payload.bin").write_bytes(b"x" * 1024)
    orphan = ws_root / "nucleus-run-00000000-0000-0000-0000-000000000000"
    orphan.mkdir()

    dry = _run_work(["gc", "--days", "0", "--dry-run"], tmp_path, env)
    assert dry.returncode == 0, dry.stderr
    report = json.loads(dry.stdout)
    assert report["removed"] == [run_id]
    assert report["freed_bytes"] >= 1024
    assert dead.exists() and orphan.exists()

    real = _run_work(["gc", "--days", "0"], tmp_path, env)
    assert real.returncode == 0, real.stderr
    report = json.loads(real.stdout)
    assert report["removed"] == [run_id]
    assert not dead.exists()
    assert orphan.exists()

    store2 = RunStore(str(db))
    assert "run.workspace_gc" in [e.type for e in store2.list_events(run_id)]


def test_nucleus_work_gc_keeps_active_and_fresh_workspaces(tmp_path):
    from mcp_server_nucleus.runs.store import RunStore

    brain = tmp_path / ".brain"
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)

    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    adapter = RunMcpAdapter(db)
    project_id = adapter.create_project(f"file://{project}", "permissive")

    live_conv = adapter.create_conversation(project_id, "live")
    live_run = adapter.create_run(live_conv, "live work")
    old_conv = adapter.create_conversation(project_id, "old")
    old_run = adapter.create_run(old_conv, "old work")
    fresh_conv = adapter.create_conversation(project_id, "fresh")
    fresh_run = adapter.create_run(fresh_conv, "fresh work")

    store = RunStore(str(db))
    # live_run stays QUEUED (non-terminal); old_run and fresh_run go terminal.
    for rid in (old_run, fresh_run):
        store.transition_run(rid, RunState.PREPARING, "run.preparing")
        store.transition_run(rid, RunState.FAILED, "run.failed")

    ws_root = brain / "runs" / "workspaces"
    ws_root.mkdir(parents=True)
    for rid in (live_run, old_run, fresh_run):
        d = ws_root / f"nucleus-run-{rid}"
        d.mkdir()
        (d / "payload.bin").write_bytes(b"x" * 512)

    # Age the live and old workspaces 30 days into the past; fresh stays now.
    import time as _time

    old_mtime = _time.time() - 30 * 86400
    for rid in (live_run, old_run):
        d = ws_root / f"nucleus-run-{rid}"
        os.utime(d, (old_mtime, old_mtime))
        os.utime(d / "payload.bin", (old_mtime, old_mtime))

    report = json.loads(
        _run_work(["gc", "--days", "7"], tmp_path, env).stdout
    )
    # Non-terminal workspace kept even though ancient; fresh terminal kept by age.
    assert report["removed"] == [old_run]
    assert sorted(report["kept"]) == sorted([live_run, fresh_run])
    assert (ws_root / f"nucleus-run-{live_run}").exists()
    assert (ws_root / f"nucleus-run-{fresh_run}").exists()
    assert not (ws_root / f"nucleus-run-{old_run}").exists()
