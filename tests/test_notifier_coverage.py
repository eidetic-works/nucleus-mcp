"""Comprehensive tests for notifier module."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.notifier import Notifier


class TestNotifierInit:
    def test_default_init(self):
        n = Notifier()
        assert n.brain_path is None
        assert n._router is None

    def test_init_with_brain_path(self, tmp_path):
        n = Notifier(brain_path=tmp_path)
        assert n.brain_path == tmp_path

    def test_get_router_lazy(self):
        n = Notifier()
        with patch("mcp_server_nucleus.runtime.channels.get_channel_router") as mock:
            mock.return_value = MagicMock()
            router = n._get_router()
            assert router is not None
            # Second call should use cached
            router2 = n._get_router()
            assert router is router2
            mock.assert_called_once()


class TestNotifierLog:
    def test_log_info(self, caplog):
        import logging
        caplog.set_level(logging.INFO, logger="NucleusNotifier")
        n = Notifier()
        n.log("Title", "Message", "info")
        assert "Title" in caplog.text
        assert "Message" in caplog.text

    def test_log_warning(self, caplog):
        import logging
        caplog.set_level(logging.WARNING, logger="NucleusNotifier")
        n = Notifier()
        n.log("Title", "Message", "warning")
        assert "Title" in caplog.text

    def test_log_error(self, caplog):
        import logging
        caplog.set_level(logging.ERROR, logger="NucleusNotifier")
        n = Notifier()
        n.log("Title", "Message", "error")
        assert "Title" in caplog.text

    def test_log_invalid_level_defaults_info(self, caplog):
        import logging
        caplog.set_level(logging.INFO, logger="NucleusNotifier")
        n = Notifier()
        n.log("Title", "Message", "invalid_level")
        assert "Title" in caplog.text


class TestNotifierMacos:
    def test_macos_success(self):
        n = Notifier()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = n.macos("Test Title", "Test Message")
            assert result is True
            mock_run.assert_called_once()
            # Check the command includes osascript
            cmd = mock_run.call_args[0][0]
            assert "osascript" in cmd

    def test_macos_failure(self):
        n = Notifier()
        with patch("subprocess.run", side_effect=Exception("failed")):
            result = n.macos("Title", "Message")
            assert result is False

    def test_macos_timeout(self):
        n = Notifier()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="osascript", timeout=5)):
            result = n.macos("Title", "Message")
            assert result is False

    def test_macos_escapes_quotes(self):
        n = Notifier()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            n.macos('Title with "quotes"', 'Message with "quotes"')
            cmd = mock_run.call_args[0][0]
            # The escaped string should be in the command
            cmd_str = " ".join(cmd)
            assert '\\"' in cmd_str

    def test_macos_escapes_single_quotes(self):
        n = Notifier()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            n.macos("Title with 'quotes'", "Message with 'quotes'")
            cmd = mock_run.call_args[0][0]
            cmd_str = " ".join(cmd)
            assert "\\'" in cmd_str


class TestNotifierSend:
    def test_send_info_level(self):
        n = Notifier()
        with patch.object(n, "log") as mock_log:
            with patch.object(n, "macos") as mock_macos:
                with patch.object(n, "_get_router") as mock_router:
                    n.send("Title", "Message", "info")
                    mock_log.assert_called_once_with("Title", "Message", "info")
                    mock_macos.assert_called_once_with("Title", "Message")
                    mock_router.assert_not_called()

    def test_send_warning_level(self):
        n = Notifier()
        mock_router = MagicMock()
        with patch.object(n, "log"):
            with patch.object(n, "macos"):
                with patch.object(n, "_get_router", return_value=mock_router):
                    n.send("Title", "Message", "warning")
                    mock_router.notify.assert_called_once_with("Title", "Message", "warning")

    def test_send_error_level(self):
        n = Notifier()
        mock_router = MagicMock()
        with patch.object(n, "log"):
            with patch.object(n, "macos"):
                with patch.object(n, "_get_router", return_value=mock_router):
                    n.send("Title", "Message", "error")
                    mock_router.notify.assert_called_once_with("Title", "Message", "error")

    def test_send_critical_level(self):
        n = Notifier()
        mock_router = MagicMock()
        with patch.object(n, "log"):
            with patch.object(n, "macos"):
                with patch.object(n, "_get_router", return_value=mock_router):
                    n.send("Title", "Message", "critical")
                    mock_router.notify.assert_called_once_with("Title", "Message", "critical")

    def test_send_default_level(self):
        n = Notifier()
        with patch.object(n, "log") as mock_log:
            with patch.object(n, "macos"):
                with patch.object(n, "_get_router") as mock_router:
                    n.send("Title", "Message")
                    mock_log.assert_called_once_with("Title", "Message", "info")
                    mock_router.assert_not_called()
