"""Sandbox escape suite: fake agy executes run.prompt inside the macOS sandbox."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import Run, RunState
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.targets import MacSandboxExecutionTarget, TargetResult
from mcp_server_nucleus.runs.workspace import WorkspaceResolver, _workspace_root


if shutil.which("sandbox-exec") is None:
    pytest.skip("sandbox-exec not available", allow_module_level=True)


def _make_fake_agy(tmp_path: Path) -> Path:
    """Create an ``agy`` executable that parses ``-p`` and exec()s the value."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    script = bindir / "agy"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "\n"
        "code = \"\"\n"
        "i = 1\n"
        "while i < len(sys.argv):\n"
        "    if sys.argv[i] == \"-p\" and i + 1 < len(sys.argv):\n"
        "        code = sys.argv[i + 1]\n"
        "        i += 2\n"
        "    else:\n"
        "        i += 1\n"
        "\n"
        "if not code:\n"
        "    print(\"no -p\", file=sys.stderr)\n"
        "    sys.exit(1)\n"
        "\n"
        "try:\n"
        "    exec(compile(code, \"<prompt>\", \"exec\"))\n"
        "    print(\"ok\", flush=True)\n"
        "except Exception as exc:\n"
        "    print(f\"error: {exc}\", file=sys.stderr)\n"
        "    sys.exit(1)\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bindir


def _make_project_and_run(
    store: RunStore,
    project_root: Path,
    prompt: str,
    idempotency_key: str,
) -> Run:
    """Create a project/conversation/run with the sandbox execution target."""
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    return store.create_run(
        conversation_id=conv.id,
        runner_id="agy",
        model_id="",
        execution_target="mac-sandbox",
        mode="write",
        idempotency_key=idempotency_key,
        prompt=prompt,
    )


def _workspace_target_path(project_root: Path, run_id: str) -> Path:
    """Resolve the workspace target path the same way the worker does."""
    resolver = WorkspaceResolver()
    backend = resolver.resolve_backend(project_root)
    return _workspace_root() / backend._target_name(run_id)


def _run(
    store: RunStore,
    run_id: str,
    fakebin: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile: str | None = None,
) -> TargetResult:
    """Run a single sandbox execution with the given Seatbelt profile."""
    monkeypatch.setenv(
        "PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}"
    )
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # The fake agy exec()s the prompt as Python. The default vendor dispatch
    # preamble is prose (not valid Python), so suppress it for the instrument.
    monkeypatch.setenv("NUCLEUS_VENDOR_PREAMBLE_DISABLED", "1")
    return MacSandboxExecutionTarget(profile=profile).run(
        store, run_id, "owner", lambda: lambda ctx: None
    )


def test_sandbox_blocks_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deny-by-default sandbox must not allow writing above the workspace."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_path = tmp_path / "outside.txt"

    store = RunStore(str(tmp_path / "runs.db"))
    run = _make_project_and_run(
        store,
        project_root,
        'open("../outside.txt", "w").write("x")',
        "k1",
    )

    fakebin = _make_fake_agy(tmp_path)
    monkeypatch.setenv("NUCLEUS_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    result = _run(store, run.id, fakebin, monkeypatch, profile=None)

    assert not outside_path.exists()
    assert result.state not in (RunState.READY_FOR_REVIEW, RunState.COMPLETED)


def test_permissive_profile_allows_workspace_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A permissive (allow default) profile lets the instrument write inside."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    store = RunStore(str(tmp_path / "runs.db"))
    run = _make_project_and_run(
        store,
        project_root,
        'open("inside.txt", "w").write("x")\nprint("ok")',
        "k2",
    )

    fakebin = _make_fake_agy(tmp_path)
    monkeypatch.setenv("NUCLEUS_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    permissive = "(version 1)\n(allow default)\n(deny network*)\n"
    result = _run(store, run.id, fakebin, monkeypatch, profile=permissive)

    target_path = _workspace_target_path(project_root, run.id)
    inside_path = target_path / "inside.txt"
    assert inside_path.exists()
    assert result.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED)
