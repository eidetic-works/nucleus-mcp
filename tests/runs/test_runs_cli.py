"""R5 `nucleus work` CLI tests."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mcp_server_nucleus.runs.cli import build_parser, main


def test_cli_create_and_list(tmp_path, monkeypatch):
    parser = build_parser()
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=project, check=True)
    (project / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=project, check=True)

    # monkeypatch brain path to live under tmp_path
    from mcp_server_nucleus.runs import cli
    original = cli._brain_path
    cli._brain_path = lambda: tmp_path

    try:
        # create project/conversation directly through adapter using same db path as CLI
        from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
        db = tmp_path / "runs" / "store.sqlite"
        db.parent.mkdir(parents=True, exist_ok=True)
        adapter = RunMcpAdapter(db)
        project_id = adapter.create_project(f"file://{project}", "permissive")
        conv_id = adapter.create_conversation(project_id, "c")

        main(["create", "--conversation", conv_id, "--prompt", "do work", "--idempotency", "k1"])
        # CLI opens its own store; list through the same database via a new adapter
        runs = RunMcpAdapter(db).list_runs(conv_id)
        assert len(runs) == 1
        assert runs[0]["conversation_id"] == conv_id
        assert runs[0]["state"] == "queued"
    finally:
        cli._brain_path = original
