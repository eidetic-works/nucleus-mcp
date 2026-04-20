"""
Tests for the multi-channel notification system.

Tests channels abstraction, router dispatch, config persistence,
and individual channel implementations (mocked — no real API calls).
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.channels.base import NotificationChannel, ChannelRouter
from mcp_server_nucleus.runtime.channels.telegram import TelegramChannel
from mcp_server_nucleus.runtime.channels.slack import SlackChannel
from mcp_server_nucleus.runtime.channels.discord import DiscordChannel
from mcp_server_nucleus.runtime.channels.whatsapp import WhatsAppChannel


# ── Fixtures ─────────────────────────────────────────────────────

class MockChannel(NotificationChannel):
    """In-memory mock channel for testing the router."""

    def __init__(self, name="mock", should_fail=False):
        self._name = name
        self._should_fail = should_fail
        self.sent = []

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        return f"Mock ({self._name})"

    def send(self, title, message, level="info"):
        self.sent.append({"title": title, "message": message, "level": level})
        return not self._should_fail

    def is_configured(self):
        return True


@pytest.fixture
def clean_env():
    """Remove channel-related env vars for a clean test."""
    keys = [
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "SLACK_WEBHOOK_URL", "DISCORD_WEBHOOK_URL",
        "WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID", "WHATSAPP_TO",
    ]
    saved = {k: os.environ.pop(k, None) for k in keys}
    # Clear secrets module cache so stale values don't leak between tests
    try:
        from mcp_server_nucleus.runtime.secrets import clear_cache
        clear_cache()
    except ImportError:
        pass
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)
    try:
        from mcp_server_nucleus.runtime.secrets import clear_cache
        clear_cache()
    except ImportError:
        pass


# ── NotificationChannel ABC ─────────────────────────────────────

class TestNotificationChannelABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            NotificationChannel()

    def test_mock_channel_satisfies_abc(self):
        ch = MockChannel()
        assert ch.name == "mock"
        assert ch.is_configured()
        assert ch.send("test", "msg") is True


# ── ChannelRouter ────────────────────────────────────────────────

class TestChannelRouter:
    def test_empty_router_returns_empty(self):
        router = ChannelRouter()
        assert router.list_channels() == []
        assert router.notify("title", "msg") == {}

    def test_register_and_list(self):
        router = ChannelRouter()
        ch = MockChannel("test1")
        router.register(ch)
        channels = router.list_channels()
        assert len(channels) == 1
        assert channels[0]["type"] == "test1"

    def test_notify_dispatches_to_all(self):
        router = ChannelRouter()
        ch1 = MockChannel("ch1")
        ch2 = MockChannel("ch2")
        router.register(ch1)
        router.register(ch2)

        results = router.notify("Alert", "Something happened", "warning")
        assert results == {"ch1": True, "ch2": True}
        assert len(ch1.sent) == 1
        assert len(ch2.sent) == 1
        assert ch1.sent[0]["title"] == "Alert"

    def test_notify_handles_failure(self):
        router = ChannelRouter()
        ch_ok = MockChannel("ok")
        ch_fail = MockChannel("fail", should_fail=True)
        router.register(ch_ok)
        router.register(ch_fail)

        results = router.notify("Test", "msg")
        assert results["ok"] is True
        assert results["fail"] is False

    def test_unregister(self):
        router = ChannelRouter()
        ch = MockChannel("removable")
        router.register(ch)
        assert len(router.list_channels()) == 1
        assert router.unregister("removable") is True
        assert len(router.list_channels()) == 0

    def test_unregister_nonexistent(self):
        router = ChannelRouter()
        assert router.unregister("ghost") is False

    def test_get_channel(self):
        router = ChannelRouter()
        ch = MockChannel("findme")
        router.register(ch)
        assert router.get_channel("findme") is ch
        assert router.get_channel("nope") is None

    def test_routing_rules(self):
        router = ChannelRouter()
        ch1 = MockChannel("critical_only")
        ch2 = MockChannel("all_levels")
        router.register(ch1)
        router.register(ch2)
        router.set_routing("info", ["all_levels"])

        results = router.notify("Info msg", "details", "info")
        assert "all_levels" in results
        assert "critical_only" not in results

    def test_persistence(self, clean_env):
        with tempfile.TemporaryDirectory() as td:
            bp = Path(td)

            # Save
            router = ChannelRouter(bp)
            os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
            os.environ["TELEGRAM_CHAT_ID"] = "12345"
            router.auto_discover()
            router.save_to_brain()

            config_file = bp / "channels" / "config.json"
            assert config_file.exists()
            data = json.loads(config_file.read_text())
            assert any(c["type"] == "telegram" for c in data["channels"])

            # Load
            router2 = ChannelRouter(bp)
            router2.load_from_brain()
            channels = router2.list_channels()
            assert any(c["type"] == "telegram" for c in channels)


# ── TelegramChannel ─────────────────────────────────────────────

class TestTelegramChannel:
    def test_not_configured_without_creds(self, clean_env):
        ch = TelegramChannel()
        assert ch.is_configured() is False
        assert ch.name == "telegram"

    def test_configured_with_creds(self, clean_env):
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
        os.environ["TELEGRAM_CHAT_ID"] = "12345"
        ch = TelegramChannel()
        assert ch.is_configured() is True

    def test_configured_with_constructor_args(self, clean_env):
        ch = TelegramChannel(token="tok", chat_id="cid")
        assert ch.is_configured() is True

    def test_send_returns_false_without_creds(self, clean_env):
        ch = TelegramChannel()
        assert ch.send("Test", "msg") is False

    @patch("urllib.request.urlopen")
    def test_send_posts_to_telegram_api(self, mock_urlopen, clean_env):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ch = TelegramChannel(token="test_token", chat_id="12345")
        result = ch.send("Alert", "Server down", "critical")

        assert result is True
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert "api.telegram.org" in req.full_url
        body = json.loads(req.data)
        assert body["chat_id"] == "12345"
        assert "Alert" in body["text"]

    @patch("urllib.request.urlopen")
    def test_send_escapes_markdown_v1_special_chars(self, mock_urlopen, clean_env):
        # Unpaired underscores/asterisks in title+message must not leak into
        # parse_mode="Markdown" as unclosed formatting — Bot API 400s and the
        # send fails silently from the caller.
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ch = TelegramChannel(token="t", chat_id="c")
        assert ch.send("Relay stall — claude_code", "foo_bar *baz* [link]") is True

        body = json.loads(mock_urlopen.call_args[0][0].data)
        text = body["text"]
        assert "claude\\_code" in text
        assert "foo\\_bar" in text
        assert "\\*baz\\*" in text
        assert "\\[link]" in text
        # The channel's own wrapping asterisks must remain unescaped.
        assert "*Relay stall — claude\\_code*" in text


# ── SlackChannel ─────────────────────────────────────────────────

class TestSlackChannel:
    def test_not_configured_without_url(self, clean_env):
        ch = SlackChannel()
        assert ch.is_configured() is False

    def test_configured_with_url(self, clean_env):
        os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test"
        ch = SlackChannel()
        assert ch.is_configured() is True

    @patch("urllib.request.urlopen")
    def test_send_posts_to_webhook(self, mock_urlopen, clean_env):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
        result = ch.send("Deploy", "v1.9.0 released", "info")

        assert result is True
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://hooks.slack.com/test"
        body = json.loads(req.data)
        assert "attachments" in body

    def test_to_dict_masks_webhook(self, clean_env):
        ch = SlackChannel(webhook_url="https://hooks.slack.com/services/T123/B456/abcdef12")
        d = ch.to_dict()
        assert "webhook_url" in d
        assert "abcdef12" not in d["webhook_url"] or d["webhook_url"].startswith("...")


# ── DiscordChannel ───────────────────────────────────────────────

class TestDiscordChannel:
    def test_not_configured_without_url(self, clean_env):
        ch = DiscordChannel()
        assert ch.is_configured() is False

    @patch("urllib.request.urlopen")
    def test_send_posts_discord_embed(self, mock_urlopen, clean_env):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ch = DiscordChannel(webhook_url="https://discord.com/api/webhooks/123/abc")
        result = ch.send("Incident", "Database down", "error")

        assert result is True
        body = json.loads(mock_urlopen.call_args[0][0].data)
        assert "embeds" in body
        assert body["embeds"][0]["title"] == "Incident"


# ── WhatsAppChannel ──────────────────────────────────────────────

class TestWhatsAppChannel:
    def test_not_configured_without_all_creds(self, clean_env):
        ch = WhatsAppChannel()
        assert ch.is_configured() is False
        # Partial creds
        os.environ["WHATSAPP_TOKEN"] = "tok"
        ch2 = WhatsAppChannel()
        assert ch2.is_configured() is False

    def test_configured_with_all_creds(self, clean_env):
        ch = WhatsAppChannel(token="tok", phone_id="pid", to_number="+1234567890")
        assert ch.is_configured() is True

    @patch("urllib.request.urlopen")
    def test_send_posts_to_graph_api(self, mock_urlopen, clean_env):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        ch = WhatsAppChannel(token="tok", phone_id="pid", to_number="+1234567890")
        result = ch.send("Alert", "Budget exceeded", "warning")

        assert result is True
        req = mock_urlopen.call_args[0][0]
        assert "graph.facebook.com" in req.full_url
        assert req.get_header("Authorization") == "Bearer tok"
        body = json.loads(req.data)
        assert body["messaging_product"] == "whatsapp"
        assert body["to"] == "+1234567890"


# ── Auto-discover ────────────────────────────────────────────────

class TestAutoDiscover:
    def test_discovers_nothing_with_no_creds(self, clean_env):
        router = ChannelRouter()
        count = router.auto_discover()
        assert count == 0

    def test_discovers_telegram(self, clean_env):
        os.environ["TELEGRAM_BOT_TOKEN"] = "tok"
        os.environ["TELEGRAM_CHAT_ID"] = "cid"
        router = ChannelRouter()
        count = router.auto_discover()
        assert count >= 1
        assert any(c["type"] == "telegram" for c in router.list_channels())

    def test_discovers_multiple(self, clean_env):
        os.environ["TELEGRAM_BOT_TOKEN"] = "tok"
        os.environ["TELEGRAM_CHAT_ID"] = "cid"
        os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test"
        router = ChannelRouter()
        count = router.auto_discover()
        assert count == 2


class TestChannelCircuitBreaker:
    """Circuit breaker integration in ChannelRouter.notify()."""

    def test_breaker_opens_after_repeated_failures(self, clean_env):
        """Channel circuit breaker opens after failure_threshold (3) failures."""
        from unittest.mock import MagicMock
        from mcp_server_nucleus.runtime.circuit_breaker import _breakers

        # Clean up any leftover breakers
        _breakers.pop("channel_mock_ch", None)

        router = ChannelRouter()
        mock_ch = MagicMock()
        mock_ch.name = "mock_ch"
        mock_ch.display_name = "Mock"
        mock_ch.is_configured.return_value = True
        mock_ch.send.side_effect = ConnectionError("API down")
        router.register(mock_ch)

        # 3 failures should open the breaker
        for _ in range(3):
            results = router.notify("test", "msg")
            assert results["mock_ch"] is False

        # 4th call should be rejected by breaker (send not called)
        mock_ch.send.reset_mock()
        results = router.notify("test", "msg")
        assert results["mock_ch"] is False
        mock_ch.send.assert_not_called()

        # Cleanup
        _breakers.pop("channel_mock_ch", None)

    def test_router_works_without_circuit_breaker_module(self, clean_env):
        """Router degrades gracefully if circuit_breaker import fails."""
        from unittest.mock import MagicMock, patch

        router = ChannelRouter()
        mock_ch = MagicMock()
        mock_ch.name = "fallback_ch"
        mock_ch.display_name = "Fallback"
        mock_ch.is_configured.return_value = True
        mock_ch.send.return_value = True
        router.register(mock_ch)

        # Patch _get_breaker to simulate import failure
        with patch.object(ChannelRouter, "_get_breaker", return_value=None):
            results = router.notify("test", "msg")
            assert results["fallback_ch"] is True
            mock_ch.send.assert_called_once()
