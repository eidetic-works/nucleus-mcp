"""Tests for usage recording in the run store and MCP adapter."""
from __future__ import annotations

import pytest

from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.runners import RunnerResult
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.verifiers import NoopVerifier
from mcp_server_nucleus.runs.worker import RunWorker


def _fake_runner_result(vendor: str = "fake-vendor") -> RunnerResult:
    return RunnerResult(
        vendor=vendor,
        model_family="fake-family",
        model_id="fake-model",
        rc=0,
        status="ok",
        output="fake output",
        duration=2.5,
        diff_artifact=b"",
        is_clean=False,
    )


def test_usage_recorded_after_run(tmp_path):
    db = tmp_path / "test_usage.db"
    store = RunStore(str(db))
    project = store.create_project(root_uri=f"file://{tmp_path}", trust_mode="default")
    conversation = store.create_conversation(project.id, "test-conversation")
    run = store.create_run(
        conversation_id=conversation.id,
        runner_id="test-runner",
        model_id="fake-model",
        execution_target="local",
        mode="write",
        idempotency_key="key-1",
        prompt="test prompt",
    )

    def handler(ctx):
        return _fake_runner_result()

    worker = RunWorker(store, run.id, owner_id="test-owner", workspace_resolver=None)
    worker.execute(handler, verifiers=[NoopVerifier()])

    usage = store.get_usage(run.id)
    assert usage is not None
    assert usage.vendor == "fake-vendor"
    assert usage.model_family == "fake-family"
    assert usage.model_id == "fake-model"
    assert usage.duration == 2.5
    assert usage.source == "unknown"
    assert usage.confidence == "low"
    assert usage.quota_class == "free"
    assert usage.tokens is None
    assert usage.cost is None


def test_show_run_includes_usage(tmp_path):
    db = tmp_path / "test_show_usage.db"
    adapter = RunMcpAdapter(str(db))
    project_id = adapter.create_project(root_uri=f"file://{tmp_path}", trust_mode="default")
    conversation_id = adapter.create_conversation(project_id, "test-conversation")
    run_id = adapter.create_run(
        conversation_id=conversation_id,
        prompt="test prompt",
        runner_id="test-runner",
        model_id="fake-model",
        execution_target="local",
        mode="write",
    )

    def handler(ctx):
        return _fake_runner_result(vendor="adapter-vendor")

    worker = RunWorker(adapter._store, run_id, owner_id="test-owner", workspace_resolver=None)
    worker.execute(handler, verifiers=[NoopVerifier()])

    response = adapter.show_run(run_id)
    assert "usage" in response
    assert response["usage"]["source"] == "unknown"
    assert response["usage"]["vendor"] == "adapter-vendor"
    assert response["usage"]["model_family"] == "fake-family"
    assert response["usage"]["model_id"] == "fake-model"
    assert response["usage"]["duration"] == 2.5
    assert "bundle" in response
    assert response["bundle"]["usage"]["source"] == "unknown"
