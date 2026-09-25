import subprocess

import pytest
from starlette.testclient import TestClient

from mcp_server_nucleus.runs.api import build_app
from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.service import RunService
from mcp_server_nucleus.runs.store import RunStore


def test_project_root_normalization_matches_service(tmp_path):
    db_path = tmp_path / "runs.db"
    store = RunStore(db_path)
    service = RunService(store)
    adapter = RunMcpAdapter(db_path)

    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    subprocess.run(["git", "init"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
    (project_dir / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=project_dir, check=True)

    # 1. Create a run/project via service.py
    run_id_service, reason = service.submit_run(
        project_root=str(project_dir),
        prompt="Test prompt from service",
    )
    assert run_id_service is not None, f"submit_run failed: {reason}"

    # 2. Create a run via api.py (HTTP POST /runs) using the raw path
    app = build_app(adapter)
    client = TestClient(app)
    response = client.post(
        "/runs",
        json={
            "project_root": str(project_dir),
            "prompt": "Test prompt from api",
        },
    )
    assert response.status_code == 200, response.text

    # Check that both service and api referenced the exact same project ID
    expected_root_uri = f"file://{project_dir.resolve()}"
    project = store.get_project_by_root(expected_root_uri)
    assert project is not None

    run_service = store.get_run(run_id_service)
    run_api_id = response.json()["run_id"]
    run_api = store.get_run(run_api_id)

    conv_service = store.get_conversation(run_service.conversation_id)
    conv_api = store.get_conversation(run_api.conversation_id)

    assert conv_service.project_id == project.id
    assert conv_api.project_id == project.id
