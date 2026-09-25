"""R5: verify the nucleus_runs MCP facade is registered and functional."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.tools.runs import register


class _FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def test_nucleus_runs_facade_registers(tmp_path):
    mcp = _FakeMcp()
    brain = tmp_path / "brain"
    brain.mkdir()
    register(mcp, {"get_brain_path": lambda: str(brain)})
    assert "nucleus_runs" in mcp.tools


def test_nucleus_runs_create_project_and_run(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    brain = tmp_path / "brain"
    brain.mkdir()
    mcp = _FakeMcp()
    register(mcp, {"get_brain_path": lambda: str(brain)})

    out = mcp.tools["nucleus_runs"]("create_project", {"root_uri": f"file://{project}", "trust_mode": "permissive"})
    data = json.loads(out)
    assert data["success"]
    project_id = data["project_id"]

    out = mcp.tools["nucleus_runs"]("create_conversation", {"project_id": project_id, "title": "c"})
    conv_id = json.loads(out)["conversation_id"]

    out = mcp.tools["nucleus_runs"]("create_run", {"conversation_id": conv_id, "prompt": "write", "idempotency_key": "k1"})
    run_id = json.loads(out)["run_id"]

    out = mcp.tools["nucleus_runs"]("show_run", {"run_id": run_id})
    shown = json.loads(out)
    assert shown["success"]
    assert shown["data"]["run"]["state"] == "queued"


def test_nucleus_runs_adapter_exists(tmp_path):
    db = tmp_path / "nucleus-runs-test.sqlite"
    adapter = RunMcpAdapter(str(db))
    assert adapter is not None
