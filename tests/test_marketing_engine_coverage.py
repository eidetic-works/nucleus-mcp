"""
Coverage tests for runtime/capabilities/marketing_engine.py
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities import marketing_engine


# ---------------------------------------------------------------------------
# _get_api_key
# ---------------------------------------------------------------------------
class TestGetApiKey:
    def test_returns_key_when_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        assert marketing_engine._get_api_key() == "test-key-123"

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert marketing_engine._get_api_key() is None


# ---------------------------------------------------------------------------
# brain_synthesize_strategy
# ---------------------------------------------------------------------------
class TestBrainSynthesizeStrategy:
    def test_no_genai_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", False)
        result = marketing_engine.brain_synthesize_strategy(str(tmp_path))
        assert result["status"] == "error"
        assert "not installed" in result["message"]

    def test_no_api_key_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = marketing_engine.brain_synthesize_strategy(str(tmp_path))
        assert result["status"] == "error"
        assert "GEMINI_API_KEY" in result["message"]

    def test_log_file_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        result = marketing_engine.brain_synthesize_strategy(str(tmp_path))
        assert result["status"] == "error"
        assert "Log file not found" in result["message"]

    def test_success_writes_strategy(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        # Create marketing log
        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "marketing_log.md"
        log_file.write_text("# Marketing Log\n- Posted on X about anti-streak")

        # Mock genai client
        mock_response = MagicMock()
        mock_response.text = "# New Strategy\n- Pivot to anti-streak"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        result = marketing_engine.brain_synthesize_strategy(str(tmp_path))

        strategy_file = tmp_path / "docs" / "marketing" / "strategy.md"
        assert strategy_file.exists()
        assert "anti-streak" in strategy_file.read_text()
        mock_client.models.generate_content.assert_called_once()

    def test_success_with_existing_strategy(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("log content")
        (log_dir / "strategy.md").write_text("old strategy")

        mock_response = MagicMock()
        mock_response.text = "new strategy"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        marketing_engine.brain_synthesize_strategy(str(tmp_path), focus_topic="test")
        assert (log_dir / "strategy.md").read_text() == "new strategy"

    def test_genai_exception_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("log content")

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("API down")
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        result = marketing_engine.brain_synthesize_strategy(str(tmp_path))
        assert result["status"] == "error"
        assert "API down" in result["message"]


# ---------------------------------------------------------------------------
# brain_optimize_workflow
# ---------------------------------------------------------------------------
class TestBrainOptimizeWorkflow:
    def test_no_genai_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", False)
        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "error"
        assert "not installed" in result["message"]

    def test_no_api_key_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "error"
        assert "GEMINI_API_KEY" in result["message"]

    def test_log_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "error"
        assert "Log file not found" in result["message"]

    def test_no_meta_feedback_skips(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("Just a normal log entry")

        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "skipped"
        assert "META-FEEDBACK" in result["message"]

    def test_success_creates_improvements_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("META-FEEDBACK: improve dashboard")

        mock_response = MagicMock()
        mock_response.text = "- [ ] Update cheatsheet"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "success"
        improvement_file = tmp_path / ".brain" / "ledger" / "WORKFLOW_IMPROVEMENTS.md"
        assert improvement_file.exists()
        assert "Update cheatsheet" in improvement_file.read_text()

    def test_success_appends_to_existing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("META-FEEDBACK: new idea")

        improvement_dir = tmp_path / ".brain" / "ledger"
        improvement_dir.mkdir(parents=True)
        improvement_file = improvement_dir / "WORKFLOW_IMPROVEMENTS.md"
        improvement_file.write_text("## Existing content")

        mock_response = MagicMock()
        mock_response.text = "- [ ] New task"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "success"
        content = improvement_file.read_text()
        assert "Existing content" in content
        assert "New task" in content

    def test_success_reads_existing_cheatsheet(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("META-FEEDBACK: test")

        cheatsheet_dir = tmp_path / ".agent" / "workflows"
        cheatsheet_dir.mkdir(parents=True)
        (cheatsheet_dir / "marketing_autopilot_cheatsheet.md").write_text("Old rules")

        mock_response = MagicMock()
        mock_response.text = "- [ ] task"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        marketing_engine.brain_optimize_workflow(str(tmp_path))
        # Verify generate_content was called (cheatsheet content included in prompt)
        call_args = mock_client.models.generate_content.call_args
        assert "Old rules" in call_args.kwargs["contents"]

    def test_genai_exception_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(marketing_engine, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        log_dir = tmp_path / "docs" / "marketing"
        log_dir.mkdir(parents=True)
        (log_dir / "marketing_log.md").write_text("META-FEEDBACK: test")

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("Network error")
        monkeypatch.setattr(marketing_engine, "genai", mock_genai)

        result = marketing_engine.brain_optimize_workflow(str(tmp_path))
        assert result["status"] == "error"
        assert "Network error" in result["message"]
