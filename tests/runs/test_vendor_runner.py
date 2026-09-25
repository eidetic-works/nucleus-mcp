"""R3 vendor runner integration tests for workspace-scoped execution."""
from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.policy import ExecutionPolicy
from mcp_server_nucleus.runs.runners import VendorCliRunner
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


def _install_fake_agy(tmp_path: Path, script: str) -> None:
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    script_path = bindir / "agy"
    script_path.write_text("#!/bin/sh\n" + script)
    script_path.chmod(0o755)
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bindir}{os.pathsep}{current}"


def _seed_workspace(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("# code\n")
    resolver = WorkspaceResolver()
    backend = resolver.resolve_backend(project)
    ws = backend.create(project, "runner-1")
    return ws, backend


def test_vendor_runner_runs_in_workspace_and_captures_diff(tmp_path, monkeypatch):
    _install_fake_agy(
        tmp_path,
        'echo ran > out.txt\n'
        'echo "done"\n'
        'exit 0\n',
    )
    ws, backend = _seed_workspace(tmp_path)
    try:
        runner = VendorCliRunner("agy", mode="write")
        result = runner.run(
            "write a file",
            ws,
            backend,
            ExecutionPolicy.from_trust_mode("permissive"),
            timeout_s=10,
        )

        assert result.status == "ok"
        assert result.rc == 0
        assert "done" in result.output
        assert (ws.target_path / "out.txt").read_text() == "ran\n"
        assert not result.is_clean
        assert result.diff_artifact
    finally:
        backend.dispose(ws)


def test_vendor_runner_policy_denied(tmp_path, monkeypatch):
    _install_fake_agy(
        tmp_path,
        'echo ran > out.txt\n'
        'echo "done"\n'
        'exit 0\n',
    )
    ws, backend = _seed_workspace(tmp_path)
    try:
        runner = VendorCliRunner("agy", mode="write")
        result = runner.run(
            "write a file",
            ws,
            backend,
            ExecutionPolicy.from_trust_mode("strict"),
            timeout_s=10,
        )

        assert result.status == "policy_denied"
        assert not (ws.target_path / "out.txt").exists()
    finally:
        backend.dispose(ws)


def test_vendor_runner_cancellation_captures_partial_output(tmp_path, monkeypatch):
    _install_fake_agy(
        tmp_path,
        'cat > /dev/null\n'
        'for i in $(seq 1 20); do echo "line $i"; sleep 0.2; done\n'
        'echo "done"\n'
        'exit 0\n',
    )
    ws, backend = _seed_workspace(tmp_path)
    try:
        runner = VendorCliRunner("agy")
        cancel = threading.Event()

        def on_stream(s):
            if "line" in s:
                cancel.set()

        result = runner.run(
            "count",
            ws,
            backend,
            ExecutionPolicy.from_trust_mode("permissive"),
            timeout_s=10,
            cancel_event=cancel,
            stream_callback=on_stream,
        )

        assert result.status == "cancelled"
        assert result.rc is None
        assert "line" in result.output
    finally:
        backend.dispose(ws)


def test_vendor_runner_streaming_callback(tmp_path, monkeypatch):
    _install_fake_agy(
        tmp_path,
        'cat > /dev/null\n'
        'for i in 1 2 3; do echo "line $i"; sleep 0.1; done\n'
        'echo "done"\n'
        'exit 0\n',
    )
    ws, backend = _seed_workspace(tmp_path)
    try:
        runner = VendorCliRunner("agy")
        seen = []
        result = runner.run(
            "count",
            ws,
            backend,
            ExecutionPolicy.from_trust_mode("permissive"),
            timeout_s=10,
            stream_callback=lambda s: seen.append(s),
        )

        assert result.status == "ok"
        assert len(seen) >= 4
        assert any("done" in s for s in seen)
    finally:
        backend.dispose(ws)
