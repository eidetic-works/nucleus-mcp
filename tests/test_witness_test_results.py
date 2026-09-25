"""test_witness_test_results.py — Tests for the test-result witness."""

from __future__ import annotations

import json
import os

import pytest

from mcp_server_nucleus.runtime.agent_os.witness_test_results import (
    log_test_result,
    query_test_result,
    verify_signature,
    get_test_result_entries,
    _witness_path,
)


@pytest.fixture
def tmp_brain(tmp_path, monkeypatch):
    """Isolated brain WITH a signing key.

    witness_test_results refuses to sign without NUCLEUS_WITNESS_SIGN_KEY --
    correctly, since signing with a hardcoded fallback would make every
    signature worthless. This fixture simply never set it, so 7 tests failed
    with "NUCLEUS_WITNESS_SIGN_KEY is not set" and looked like an environment
    fault. It is a fixture gap: test_merge_gate.py has set this the same way
    since it was written.

    The refusal path is deliberately NOT weakened here -- it is covered by
    test_merge_gate_authorize.py, which DELETES the variable on purpose to
    prove the refusal still fires.
    """
    monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-signing-key")
    return tmp_path


class TestLogTestResult:
    def test_log_creates_witness_file(self, tmp_brain):
        witness_file = tmp_brain / "witness" / "test_results.jsonl"
        assert not witness_file.exists()

        log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
        assert witness_file.exists()

    def test_log_writes_valid_json_with_signature(self, tmp_brain):
        entry_id = log_test_result(
            "run-001", passed=10, failed=0, skipped=0, brain_path=str(tmp_brain)
        )
        witness_file = _witness_path(str(tmp_brain))
        with witness_file.open() as f:
            entry = json.loads(f.readline())

        assert entry["witness_id"] == entry_id
        assert entry["test_run_id"] == "run-001"
        assert entry["passed"] == 10
        assert entry["failed"] == 0
        assert entry["all_passed"] is True
        assert "signature" in entry
        assert len(entry["signature"]) == 64  # HMAC-SHA256 hex

    def test_all_passed_false_when_failed(self, tmp_brain):
        log_test_result("run-002", passed=8, failed=2, brain_path=str(tmp_brain))
        witness_file = _witness_path(str(tmp_brain))
        with witness_file.open() as f:
            entry = json.loads(f.readline())
        assert entry["all_passed"] is False


class TestQueryTestResult:
    def test_query_finds_by_run_id(self, tmp_brain):
        log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
        found = query_test_result("run-001", brain_path=str(tmp_brain))
        assert found is True

    def test_query_substring_match(self, tmp_brain):
        log_test_result("pytest-run-abc", passed=5, failed=0, brain_path=str(tmp_brain))
        found = query_test_result("pytest", brain_path=str(tmp_brain))
        assert found is True

    def test_query_require_all_passed(self, tmp_brain):
        log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
        log_test_result("run-002", passed=8, failed=2, brain_path=str(tmp_brain))

        found_all = query_test_result("run-001", require_all_passed=True, brain_path=str(tmp_brain))
        found_failed = query_test_result("run-002", require_all_passed=True, brain_path=str(tmp_brain))

        assert found_all is True
        assert found_failed is False

    def test_query_returns_false_for_no_match(self, tmp_brain):
        log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
        found = query_test_result("other", brain_path=str(tmp_brain))
        assert found is False


class TestVerifySignature:
    def test_valid_signature_verifies(self, tmp_brain):
        os.environ["NUCLEUS_WITNESS_SIGN_KEY"] = "test-key"
        try:
            log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
            witness_file = _witness_path(str(tmp_brain))
            with witness_file.open() as f:
                entry = json.loads(f.readline())
            assert verify_signature(entry, key="test-key") is True
        finally:
            del os.environ["NUCLEUS_WITNESS_SIGN_KEY"]

    def test_tampered_entry_fails_verification(self, tmp_brain):
        os.environ["NUCLEUS_WITNESS_SIGN_KEY"] = "test-key"
        try:
            log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
            witness_file = _witness_path(str(tmp_brain))
            with witness_file.open() as f:
                entry = json.loads(f.readline())
            # Tamper with the passed count
            entry["passed"] = 999
            assert verify_signature(entry, key="test-key") is False
        finally:
            del os.environ["NUCLEUS_WITNESS_SIGN_KEY"]

    def test_wrong_key_fails_verification(self, tmp_brain):
        os.environ["NUCLEUS_WITNESS_SIGN_KEY"] = "correct-key"
        try:
            log_test_result("run-001", passed=10, failed=0, brain_path=str(tmp_brain))
            witness_file = _witness_path(str(tmp_brain))
            with witness_file.open() as f:
                entry = json.loads(f.readline())
            assert verify_signature(entry, key="wrong-key") is False
        finally:
            del os.environ["NUCLEUS_WITNESS_SIGN_KEY"]
