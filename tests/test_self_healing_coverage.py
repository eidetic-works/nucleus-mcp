"""
Coverage tests for runtime/capabilities/self_healing.py
"""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities.self_healing import SelfHealingOps


@pytest.fixture
def self_healing(monkeypatch):
    monkeypatch.setenv("NUCLEUS_HEALTH_CMD", "echo 'healthy'")
    return SelfHealingOps()


@pytest.fixture
def self_healing_default(monkeypatch):
    monkeypatch.delenv("NUCLEUS_HEALTH_CMD", raising=False)
    return SelfHealingOps()


# ---------------------------------------------------------------------------
# Properties & Init
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, self_healing):
        assert self_healing.name == "self_healing_ops"

    def test_description(self, self_healing):
        assert "Diagnose" in self_healing.description or "repair" in self_healing.description

    def test_init_with_custom_cmd(self, self_healing):
        assert self_healing.health_cmd == "echo 'healthy'"

    def test_init_default_cmd(self, self_healing_default):
        assert "No health check configured" in self_healing_default.health_cmd


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_two_tools(self, self_healing):
        tools = self_healing.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_scan_health" in names
        assert "brain_generate_fix_plan" in names

    def test_generate_fix_plan_required(self, self_healing):
        tools = self_healing.get_tools()
        tool = [t for t in tools if t["name"] == "brain_generate_fix_plan"][0]
        assert tool["parameters"]["required"] == ["error_log"]


# ---------------------------------------------------------------------------
# _scan_health
# ---------------------------------------------------------------------------
class TestScanHealth:
    def test_scan_success(self, self_healing):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "All tests passed"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            result = self_healing._scan_health()
            assert result["success"] is True
            assert result["output"] == "All tests passed"
            assert result["errors"] == ""
            assert result["command"] == "echo 'healthy'"

    def test_scan_failure(self, self_healing):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Test failed"
        with patch("subprocess.run", return_value=mock_result):
            result = self_healing._scan_health()
            assert result["success"] is False
            assert result["errors"] == "Test failed"

    def test_scan_timeout(self, self_healing):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="test", timeout=120)):
            result = self_healing._scan_health()
            assert result["success"] is False
            assert "timed out" in result["error"]

    def test_scan_generic_exception(self, self_healing):
        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            result = self_healing._scan_health()
            assert result["success"] is False
            assert "Unexpected error" in result["error"]


# ---------------------------------------------------------------------------
# _generate_fix_plan
# ---------------------------------------------------------------------------
class TestGenerateFixPlan:
    def test_generate_with_error_log(self, self_healing):
        result = self_healing._generate_fix_plan({
            "error_log": "TypeError: unsupported operand type",
            "context_files": ["src/main.py", "src/utils.py"]
        })
        assert "Fix Plan" in result
        assert "TypeError" in result
        assert "src/main.py" in result
        assert "src/utils.py" in result
        assert "code_read_file" in result
        assert "code_write_file" in result

    def test_generate_empty_error_log(self, self_healing):
        result = self_healing._generate_fix_plan({"error_log": ""})
        assert "Fix Plan" in result

    def test_generate_no_context_files(self, self_healing):
        result = self_healing._generate_fix_plan({"error_log": "Some error"})
        assert "Fix Plan" in result

    def test_generate_truncates_long_error(self, self_healing):
        long_error = "x" * 1000
        result = self_healing._generate_fix_plan({"error_log": long_error})
        # Error log is truncated to 500 chars
        assert "..." in result

    def test_generate_default_context_files(self, self_healing):
        result = self_healing._generate_fix_plan({"error_log": "error"})
        # Default context_files is empty list
        assert "Fix Plan" in result


# ---------------------------------------------------------------------------
# execute_tool dispatch
# ---------------------------------------------------------------------------
class TestExecuteTool:
    def test_dispatch_scan_health(self, self_healing):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            result = self_healing.execute_tool("brain_scan_health", {})
            assert result["success"] is True

    def test_dispatch_generate_fix_plan(self, self_healing):
        result = self_healing.execute_tool("brain_generate_fix_plan", {"error_log": "test error"})
        assert "Fix Plan" in result

    def test_dispatch_unknown(self, self_healing):
        result = self_healing.execute_tool("nonexistent", {})
        assert "not found" in result
