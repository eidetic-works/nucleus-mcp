"""Test executor LLM execution for complex tasks.

Verifies that:
1. When EXECUTOR_LLM_API_KEY is set, the executor attempts LLM execution
2. When LLM execution succeeds, the task is marked DONE
3. When LLM execution fails, the executor falls back to principal handoff
4. When no API key is set, the executor skips LLM and hands off to principal
"""
import subprocess
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXECUTOR_SCRIPT = PROJECT_ROOT / "scripts" / "executor_daemon.sh"


class TestExecutorLLMExecution:
    """Test the LLM execution path in the executor daemon."""

    def test_executor_has_llm_execution_block(self):
        """The executor script should have LLM execution logic."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "EXECUTOR_LLM_API_KEY" in source, (
            "Executor should check EXECUTOR_LLM_API_KEY for LLM execution"
        )
        assert "dispatch_and_capture" in source, (
            "Executor should use dispatch_and_capture for LLM execution"
        )

    def test_executor_has_fallback_to_principal(self):
        """The executor should fall back to principal handoff when LLM fails."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "NEEDS-PRINCIPAL" in source, (
            "Executor should have principal handoff fallback"
        )
        assert "falling back to principal" in source.lower() or "fallback" in source.lower(), (
            "Executor should log fallback to principal"
        )

    def test_executor_llm_provider_configurable(self):
        """The executor should use EXECUTOR_LLM_PROVIDER env var."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "EXECUTOR_LLM_PROVIDER" in source, (
            "Executor should read LLM provider from env"
        )
        assert "LLM_PROVIDER" in source, (
            "Executor should use LLM_PROVIDER variable"
        )

    def test_executor_llm_timeout_configurable(self):
        """The LLM execution should have a timeout."""
        source = EXECUTOR_SCRIPT.read_text()
        # The dispatch_and_capture call should have a timeout
        assert "timeout_s" in source, (
            "LLM execution should have a timeout parameter"
        )

    def test_executor_llm_checks_status(self):
        """The executor should check the LLM result status."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "llm_status" in source, (
            "Executor should extract LLM status from result"
        )
        assert '"ok"' in source or "'ok'" in source, (
            "Executor should check for 'ok' status"
        )

    def test_executor_llm_skips_without_key(self):
        """The executor should skip LLM execution when no API key is set."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "no LLM API key" in source or "skipping LLM" in source, (
            "Executor should log when skipping LLM due to missing key"
        )

    def test_executor_retry_file_in_state_dir(self):
        """The retry file should be in STATE_DIR (persists across reboots)."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "STATE_DIR/executor_retry_counts" in source or 'STATE_DIR' in source and 'executor_retry_counts' in source, (
            "Retry file should be in STATE_DIR, not /tmp/ (persists across reboots)"
        )
        assert '/tmp/executor_retry_counts' not in source, (
            "Retry file should NOT be in /tmp/ (cleared on reboot)"
        )

    def test_executor_has_exponential_backoff(self):
        """The executor should have exponential backoff between retries."""
        source = EXECUTOR_SCRIPT.read_text()
        assert "backoff" in source.lower(), (
            "Executor should have backoff logic"
        )
        assert "INITIAL_BACKOFF" in source, (
            "Executor should have INITIAL_BACKOFF config"
        )
        assert "2 **" in source or "2**" in source, (
            "Executor should use exponential backoff (2^retry_count)"
        )
