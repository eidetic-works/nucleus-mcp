"""test_witness_deployment.py — Tests for the deployment witness."""

from __future__ import annotations

import json
import time

import pytest

from mcp_server_nucleus.runtime.agent_os.witness_deployment import (
    log_deployment,
    query_deployment,
    get_deployment_entries,
    _witness_path,
)


@pytest.fixture
def tmp_brain(tmp_path):
    return tmp_path


class TestLogDeployment:
    def test_log_creates_witness_file(self, tmp_brain):
        witness_file = tmp_brain / "witness" / "deployment_log.jsonl"
        assert not witness_file.exists()

        log_deployment(
            url="https://myapp.pages.dev",
            commit_sha="abc123",
            brain_path=str(tmp_brain),
        )
        assert witness_file.exists()

    def test_log_writes_valid_json(self, tmp_brain):
        entry_id = log_deployment(
            url="https://myapp.pages.dev",
            commit_sha="abc123",
            agent_id="cell-1",
            brain_path=str(tmp_brain),
        )
        witness_file = _witness_path(str(tmp_brain))
        with witness_file.open() as f:
            entry = json.loads(f.readline())

        assert entry["witness_id"] == entry_id
        assert entry["url"] == "https://myapp.pages.dev"
        assert entry["commit_sha"] == "abc123"
        assert entry["agent_id"] == "cell-1"
        assert "timestamp" in entry

    def test_log_appends_not_overwrites(self, tmp_brain):
        log_deployment(url="https://a.com", brain_path=str(tmp_brain))
        log_deployment(url="https://b.com", brain_path=str(tmp_brain))
        witness_file = _witness_path(str(tmp_brain))
        with witness_file.open() as f:
            lines = f.readlines()
        assert len(lines) == 2


class TestQueryDeployment:
    def test_query_finds_by_url(self, tmp_brain):
        log_deployment(url="https://myapp.pages.dev", brain_path=str(tmp_brain))
        found = query_deployment(url="myapp.pages.dev", brain_path=str(tmp_brain))
        assert found is True

    def test_query_finds_by_sha(self, tmp_brain):
        log_deployment(url="https://myapp.pages.dev", commit_sha="abc123", brain_path=str(tmp_brain))
        found = query_deployment(commit_sha="abc123", brain_path=str(tmp_brain))
        assert found is True

    def test_query_returns_false_for_no_match(self, tmp_brain):
        log_deployment(url="https://myapp.pages.dev", brain_path=str(tmp_brain))
        found = query_deployment(url="other.com", brain_path=str(tmp_brain))
        assert found is False

    def test_query_filters_by_agent(self, tmp_brain):
        log_deployment(url="https://a.com", agent_id="A", brain_path=str(tmp_brain))
        log_deployment(url="https://b.com", agent_id="B", brain_path=str(tmp_brain))
        found_a = query_deployment(url="a.com", agent_id="A", brain_path=str(tmp_brain))
        found_b = query_deployment(url="a.com", agent_id="B", brain_path=str(tmp_brain))
        assert found_a is True
        assert found_b is False

    def test_query_no_url_or_sha_returns_false(self, tmp_brain):
        found = query_deployment(brain_path=str(tmp_brain))
        assert found is False
