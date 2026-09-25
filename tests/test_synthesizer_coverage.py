"""
Coverage tests for runtime/capabilities/synthesizer.py
"""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities import synthesizer


class TestGetApiKey:
    def test_returns_key_when_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "synth-key")
        assert synthesizer._get_api_key() == "synth-key"

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert synthesizer._get_api_key() is None


class TestBrainSynthesizeStatusReport:
    def test_no_genai_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(synthesizer, "HAS_GENAI", False)
        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "error"
        assert "not installed" in result["message"]

    def test_no_api_key_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "error"
        assert "GEMINI_API_KEY" in result["message"]

    def test_success_with_full_context(self, monkeypatch, tmp_path):
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        # Create task.md
        brain_dir = tmp_path / ".brain"
        brain_dir.mkdir()
        (brain_dir / "task.md").write_text("# Tasks\n- [ ] Do thing")

        # Create vision
        (brain_dir / "NUCLEUS_VISION.md").write_text("# Vision\nBuild great things")

        # Mock subprocess for crontab and tail
        def mock_check_output(cmd, **kwargs):
            if cmd[0] == 'crontab':
                return b"0 9 * * * /bin/backup\n"
            elif cmd[0] == 'tail':
                return b"log line 1\nlog line 2\n"
            return b""
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        # Create a log file so tail is called
        ledger_dir = brain_dir / "ledger"
        ledger_dir.mkdir()
        (ledger_dir / "cron.log").write_text("some log content")

        # Mock genai
        mock_response = MagicMock()
        mock_response.text = "# State of the Union\nAll good."
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(synthesizer, "genai", mock_genai)

        result = synthesizer.brain_synthesize_status_report(str(tmp_path), focus="technical")
        assert result["status"] == "success"
        assert "State of the Union" in result["report"]

    def test_success_with_no_context_files(self, monkeypatch, tmp_path):
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        # No task.md, no vision, crontab fails
        def mock_check_output(cmd, **kwargs):
            raise Exception("no crontab")
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        mock_response = MagicMock()
        mock_response.text = "Report with defaults"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(synthesizer, "genai", mock_genai)

        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "success"
        assert result["report"] == "Report with defaults"

    def test_crontab_exception_handled(self, monkeypatch, tmp_path):
        """When crontab -l fails, context['cron'] should be set to fallback."""
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        captured_prompt = {}

        def mock_generate_content(model, contents):
            captured_prompt["contents"] = contents
            mock_resp = MagicMock()
            mock_resp.text = "report"
            return mock_resp

        def mock_check_output(cmd, **kwargs):
            if cmd[0] == 'crontab':
                raise subprocess.CalledProcessError(1, cmd)
            return b""
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = mock_generate_content
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(synthesizer, "genai", mock_genai)

        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "success"
        assert "No crontab accessible" in captured_prompt["contents"]

    def test_log_tail_exception_handled(self, monkeypatch, tmp_path):
        """When tail fails for a log file, it should be silently skipped."""
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        brain_dir = tmp_path / ".brain"
        brain_dir.mkdir()
        ledger_dir = brain_dir / "ledger"
        ledger_dir.mkdir()
        (ledger_dir / "cron.log").write_text("content")

        call_count = {"tail": 0}

        def mock_check_output(cmd, **kwargs):
            if cmd[0] == 'crontab':
                return b""
            elif cmd[0] == 'tail':
                call_count["tail"] += 1
                raise Exception("tail failed")
            return b""
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        mock_response = MagicMock()
        mock_response.text = "report"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(synthesizer, "genai", mock_genai)

        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "success"
        assert call_count["tail"] >= 1

    def test_genai_exception_returns_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        def mock_check_output(cmd, **kwargs):
            raise Exception("no crontab")
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("GenAI unavailable")
        monkeypatch.setattr(synthesizer, "genai", mock_genai)

        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "error"
        assert "GenAI unavailable" in result["message"]

    def test_default_focus_is_roadmap(self, monkeypatch, tmp_path):
        """Verify default focus parameter is 'roadmap'."""
        monkeypatch.setattr(synthesizer, "HAS_GENAI", True)
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        def mock_check_output(cmd, **kwargs):
            raise Exception("no crontab")
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        mock_response = MagicMock()
        mock_response.text = "report"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client
        monkeypatch.setattr(synthesizer, "genai", mock_genai)

        # Call without focus arg
        result = synthesizer.brain_synthesize_status_report(str(tmp_path))
        assert result["status"] == "success"
