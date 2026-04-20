"""TelegramChannel: silent-400 detection + edge-title coverage (E (iii)+(iv)).

PR #103 (open) escapes markdown-v1 chars at the channel layer; the underlying
silent-failure was that any 4xx response from the Bot API got swallowed at
DEBUG-only log level. This module verifies the fix that hardens the failure
mode itself: HTTPError lands at WARNING with status code + truncated body.
Edge-title cases ensure the detection works for realistic identifier titles.
"""
from __future__ import annotations

import io
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server_nucleus.runtime.channels.telegram import TelegramChannel  # noqa: E402


def _channel() -> TelegramChannel:
    return TelegramChannel(token="t", chat_id="c")


class _FakeResp:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code: int, body: bytes = b'{"error":"bad"}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.telegram.org/", code=code, msg="err",
        hdrs=None, fp=io.BytesIO(body),
    )


def test_200_returns_true():
    with patch("urllib.request.urlopen", return_value=_FakeResp(200)):
        assert _channel().send("Hello", "world") is True


def test_400_logged_as_warning_and_returns_false(caplog):
    caplog.set_level("WARNING", logger="nucleus.channels.telegram")
    with patch("urllib.request.urlopen", side_effect=_http_error(400)):
        assert _channel().send("Title", "body") is False
    assert any("HTTP 400" in r.message for r in caplog.records)


def test_400_log_includes_response_body(caplog):
    caplog.set_level("WARNING", logger="nucleus.channels.telegram")
    body = b'{"description":"can\'t parse entities"}'
    with patch("urllib.request.urlopen", side_effect=_http_error(400, body)):
        _channel().send("T", "B")
    assert any("can\\'t parse entities" in r.message or "can't parse" in r.message
               for r in caplog.records)


def test_network_error_stays_at_debug(caplog):
    caplog.set_level("DEBUG", logger="nucleus.channels.telegram")
    with patch("urllib.request.urlopen", side_effect=ConnectionError("net down")):
        assert _channel().send("T", "B") is False
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert warnings == []


def test_underscore_title_400_surfaces():
    """The original silent-stall trigger: 'claude_code' title 400'd silently."""
    captured = {}

    def fake_urlopen(req, timeout):
        captured["called"] = True
        raise _http_error(400, b'{"description":"unsupported start tag"}')

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = _channel().send("Relay stall — claude_code", "watchdog tripped")
    assert result is False
    assert captured.get("called") is True


@pytest.mark.parametrize("title", [
    "underscore_in_title",
    "asterisk*in*title",
    "[bracket] in title",
    "back`tick in title",
    "unicode \u2014 emdash \U0001f4a3",
    "mixed _ * ` [ all together",
])
def test_edge_titles_dont_crash_send(title):
    """Edge titles must reach urlopen; they don't crash before the network call.
    400-class responses are caught + logged (above tests). Pre-network code
    must not raise on any printable str.
    """
    with patch("urllib.request.urlopen", return_value=_FakeResp(200)):
        assert _channel().send(title, "body") is True


def test_edge_title_400_response_logs_truncated_title(caplog):
    caplog.set_level("WARNING", logger="nucleus.channels.telegram")
    long_underscore = "claude_code_" + "x" * 200
    with patch("urllib.request.urlopen", side_effect=_http_error(400)):
        _channel().send(long_underscore, "body")
    assert any("claude_code_" in r.message for r in caplog.records)
    msg = next(r.message for r in caplog.records if "HTTP 400" in r.message)
    assert "x" * 200 not in msg
