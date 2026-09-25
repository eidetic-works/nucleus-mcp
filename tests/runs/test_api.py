"""Tests for the headless REST API."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from mcp_server_nucleus.runs.api import build_app
from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter


def _init_project_git(path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _adapter(tmp_path: Path) -> RunMcpAdapter:
    brain = tmp_path / "brain"
    db = brain / "runs" / "store.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    return RunMcpAdapter(db)


def test_health_endpoint(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    client = TestClient(build_app(adapter, brain_path=tmp_path / "brain"))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_capabilities_endpoint(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    client = TestClient(build_app(adapter, brain_path=tmp_path / "brain"))
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "runners" in data
    assert "models" in data


def test_create_and_show_run(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    adapter = _adapter(tmp_path)
    client = TestClient(build_app(adapter, brain_path=tmp_path / "brain"))

    response = client.post(
        "/runs",
        json={
            "project_root": str(project),
            "prompt": "add a comment",
            "runner_id": "agy",
            "mode": "write",
            "trust_mode": "permissive",
        },
    )
    assert response.status_code == 200
    data = response.json()
    run_id = data["run_id"]
    assert run_id

    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run"]["id"] == run_id
    assert data["run"]["prompt"] == "add a comment"


def test_artifact_endpoint(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _init_project_git(project)

    adapter = _adapter(tmp_path)
    client = TestClient(build_app(adapter, brain_path=tmp_path / "brain"))

    response = client.post(
        "/runs",
        json={
            "project_root": str(project),
            "prompt": "noop",
            "runner_id": "agy",
            "mode": "write",
            "trust_mode": "permissive",
        },
    )
    run_id = response.json()["run_id"]

    content = b"http://localhost:3000"
    sha = hashlib.sha256(content).hexdigest()
    artifact = adapter._store.record_artifact(
        run_id,
        kind="preview_url",
        sha256=sha,
        mime_type="text/x-preview-url",
        size=len(content),
        metadata={"url": "http://localhost:3000"},
        path=f"artifacts/{sha}.bin",
    )
    artifacts_dir = tmp_path / "brain" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / f"{sha}.bin").write_bytes(content)

    response = client.get(f"/artifacts/{artifact.id}")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "text/x-preview-url"


def test_run_not_found(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    client = TestClient(build_app(adapter, brain_path=tmp_path / "brain"))
    response = client.get("/runs/does-not-exist")
    assert response.status_code == 404
