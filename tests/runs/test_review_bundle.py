"""S3-1 verification bundle artifact manifest tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.runners import RunnerResult
from mcp_server_nucleus.runs.verification import ArtifactRef, VerificationBundle
from mcp_server_nucleus.runs.worker import RunWorker
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


FAKE_OUTPUT = "fake runner output"
FAKE_DIFF = b"fake diff bytes"


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _fake_handler(ctx):
    if ctx.workspace is None or ctx.workspace_backend is None:
        raise RuntimeError("no workspace")
    return RunnerResult(
        vendor="fake",
        model_family="f",
        model_id="m",
        rc=0,
        status="ok",
        output=FAKE_OUTPUT,
        duration=1.23,
        redacted=0,
        diff_artifact=FAKE_DIFF,
        is_clean=False,
    )


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    import mcp_server_nucleus.runtime.common as common

    monkeypatch.setattr(common, "get_brain_path", lambda: tmp_path)
    return tmp_path


def _create_and_run(adapter, tmp_path, worker_store, worker_id):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    project_id = adapter.create_project(f"file://{project}", "permissive")
    conversation_id = adapter.create_conversation(project_id, "test")
    run_id = adapter.create_run(
        conversation_id=conversation_id,
        prompt="do a thing",
        runner_id=worker_id,
        model_id="m",
        execution_target="local",
        mode="write",
    )

    worker = RunWorker(worker_store, run_id, worker_id, workspace_resolver=WorkspaceResolver())
    worker.execute(_fake_handler)
    return run_id


def test_bundle_manifest_has_artifact_refs(brain_path, tmp_path):
    db = tmp_path / "runs.db"
    adapter = RunMcpAdapter(str(db))
    run_id = _create_and_run(adapter, tmp_path, adapter._store, "worker-1")

    data = adapter.show_run(run_id)
    run = data["run"]
    bundle = data["bundle"]

    assert run["state"] == "ready_for_review"
    assert bundle["status"] == "ok"
    assert bundle["patch"]["sha256"]
    assert bundle["stdout_log"]["sha256"]
    assert bundle["work_log"]["sha256"]

    for field in ("patch", "stdout_log", "work_log"):
        ref = bundle[field]
        assert (brain_path / ref["path"]).is_file()
        assert (brain_path / ref["path"]).stat().st_size == ref["size"]

    assert bundle["route"] == {
        "vendor": "fake",
        "model": "m",
        "execution_target": "local",
        "policy": "permissive",
    }
    assert bundle["usage"]["duration"] == pytest.approx(1.23, 0.01)


def test_bundle_read_artifact(brain_path, tmp_path):
    db = tmp_path / "runs.db"
    adapter = RunMcpAdapter(str(db))
    run_id = _create_and_run(adapter, tmp_path, adapter._store, "worker-2")

    data = adapter.show_run(run_id)
    bundle = data["bundle"]
    stdout_ref = ArtifactRef(**bundle["stdout_log"])
    content = VerificationBundle.read_artifact(stdout_ref)

    assert content == FAKE_OUTPUT.encode("utf-8")
