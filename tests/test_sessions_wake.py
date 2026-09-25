"""Tests for v0.3.0 Layer 1 — mcp_server_nucleus.sessions.wake.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 1
+ op-assistant 2026-06-09T03:40Z Q1-Q5 empirical answers + the
inline wake test finding that PUT + presence alone don't wake +
op-assistant 2026-06-09T09:15Z amendment (build INTO nucleus, not
standalone scripts/).

Coverage:
- update_session_title (PUT api.anthropic.com OAuth bearer path)
- announce_client_presence (POST claude.ai cookie path)
- get_session_state (GET observability)
- prearm_session orchestrator (before/after deltas)
- _get_or_create_client_id (per-process persistence)
- Host-split auth: bearer on api.anthropic.com, cookies on claude.ai
- Pseudonymity: bearer + cookies + client_id never logged
- Truncation: session_id [:12] in logs
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.sessions import wake as sw


# ── Stubs + isolation ───────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _stub_curl():
    """Inject MagicMock for curl_cffi so tests work without real dep."""
    real = sw._curl_requests
    sw._curl_requests = MagicMock()
    yield
    sw._curl_requests = real


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(sw, "_CLIENT_ID_PATH", tmp_path / ".tb" / "wake_client_id")
    return tmp_path


def _ok_resp(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


# ── Client-ID lifecycle ─────────────────────────────────────────────────


def test_client_id_created_on_first_call_and_persisted(_isolate_home):
    cid1 = sw._get_or_create_client_id()
    assert len(cid1) >= 32  # UUID v4 string
    # Re-call returns same value
    cid2 = sw._get_or_create_client_id()
    assert cid1 == cid2
    # File written mode 0o600
    path = _isolate_home / ".tb" / "wake_client_id"
    assert path.exists()
    assert (path.stat().st_mode & 0o777) == 0o600


def test_client_id_short_invalid_file_regenerated(_isolate_home):
    """File exists but content too short → treated as missing, regenerate."""
    tb = _isolate_home / ".tb"
    tb.mkdir()
    (tb / "wake_client_id").write_text("xx")
    cid = sw._get_or_create_client_id()
    assert len(cid) >= 32


# ── update_session_title (PUT api.anthropic.com OAuth) ──────────────────


def test_update_session_title_uses_api_anthropic_with_bearer():
    put_mock = MagicMock(return_value=_ok_resp({
        "session": {"id": "cse_abc", "title": "Test", "worker_status": "idle",
                    "connection_status": "disconnected"},
    }))
    sw._curl_requests.put = put_mock
    result = sw.update_session_title("cse_abc123def456", "MyTitle",
                                     bearer="STUB-OAT-bearer")
    put_mock.assert_called_once()
    call_kwargs = put_mock.call_args
    args = call_kwargs.args
    kwargs = call_kwargs.kwargs
    url = args[0] if args else kwargs.get("url")
    assert "api.anthropic.com" in url
    assert "cse_abc123def456" in url
    assert kwargs["headers"]["Authorization"] == "Bearer STUB-OAT-bearer"
    assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
    assert "Cookie" not in kwargs["headers"]  # bearer host doesn't use cookies
    assert kwargs["json"] == {"title": "MyTitle"}
    assert result["title"] == "Test"


def test_update_session_title_no_anthropic_beta_header():
    """Per Q1 answer: NO ccr-byoc-2025-07-29 beta on this endpoint."""
    put_mock = MagicMock(return_value=_ok_resp({"session": {}}))
    sw._curl_requests.put = put_mock
    sw.update_session_title("cse_x", "t", bearer="STUB")
    headers = put_mock.call_args.kwargs["headers"]
    assert "anthropic-beta" not in headers
    assert "ccr-byoc" not in str(headers)


def test_update_session_title_raises_on_missing_args():
    with pytest.raises(sw.SessionStateError):
        sw.update_session_title("", "title", bearer="b")
    with pytest.raises(sw.SessionStateError):
        sw.update_session_title("cse_x", "title", bearer="")


def test_update_session_title_raises_on_non_2xx():
    sw._curl_requests.put = MagicMock(return_value=_ok_resp({}, status=401))
    with pytest.raises(sw.SessionStateError):
        sw.update_session_title("cse_x", "t", bearer="STUB")


# ── announce_client_presence (POST claude.ai cookies) ───────────────────


def test_announce_presence_uses_claude_ai_with_cookies():
    post_mock = MagicMock(return_value=_ok_resp({"refresh_after_seconds": 20}))
    sw._curl_requests.post = post_mock
    cookies = {"sessionKey": "STUB-SID", "lastActiveOrg": "lao",
               "anthropic-device-id": "dev", "cf_clearance": "cf"}
    result = sw.announce_client_presence("cse_xyz", cookies=cookies,
                                          client_id="my-client-uuid-1234567890ab")
    args = post_mock.call_args
    url = args.args[0] if args.args else args.kwargs.get("url")
    assert "claude.ai" in url
    assert "cse_xyz/client/presence" in url
    assert args.kwargs["headers"]["Cookie"].startswith("sessionKey=STUB-SID")
    assert "Authorization" not in args.kwargs["headers"]  # claude.ai host = NO bearer
    assert args.kwargs["json"] == {"client_id": "my-client-uuid-1234567890ab", "clear": True}
    assert result["refresh_after_seconds"] == 20


def test_announce_presence_uses_persisted_client_id_by_default(_isolate_home):
    """If caller doesn't pass client_id, use per-process UUID."""
    post_mock = MagicMock(return_value=_ok_resp({"refresh_after_seconds": 20}))
    sw._curl_requests.post = post_mock
    cookies = {"sessionKey": "x"}
    sw.announce_client_presence("cse_x", cookies=cookies)
    body = post_mock.call_args.kwargs["json"]
    persisted = (_isolate_home / ".tb" / "wake_client_id").read_text().strip()
    assert body["client_id"] == persisted


def test_announce_presence_requires_session_key_in_cookies():
    with pytest.raises(sw.SessionStateError):
        sw.announce_client_presence("cse_x", cookies={})
    with pytest.raises(sw.SessionStateError):
        sw.announce_client_presence("cse_x", cookies={"foo": "bar"})  # no sessionKey


def test_announce_presence_raises_on_non_2xx():
    sw._curl_requests.post = MagicMock(return_value=_ok_resp({}, status=403))
    with pytest.raises(sw.SessionStateError):
        sw.announce_client_presence("cse_x", cookies={"sessionKey": "k"})


def test_announce_presence_clear_false_passes_through():
    post_mock = MagicMock(return_value=_ok_resp({"refresh_after_seconds": 20}))
    sw._curl_requests.post = post_mock
    sw.announce_client_presence("cse_x", cookies={"sessionKey": "k"}, clear=False)
    assert post_mock.call_args.kwargs["json"]["clear"] is False


# ── get_session_state ───────────────────────────────────────────────────


def test_get_session_state_uses_bearer_not_cookies():
    get_mock = MagicMock(return_value=_ok_resp({
        "session": {"id": "cse_abc", "worker_status": "idle",
                    "connection_status": "disconnected", "unread": False},
    }))
    sw._curl_requests.get = get_mock
    result = sw.get_session_state("cse_abc", bearer="STUB-OAT-bearer")
    headers = get_mock.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer STUB-OAT-bearer"
    assert "Cookie" not in headers
    assert result["worker_status"] == "idle"


def test_get_session_state_unwraps_session_key():
    """Response shape per Q1: {session: {...}}. Helper unwraps."""
    sw._curl_requests.get = MagicMock(return_value=_ok_resp({
        "session": {"worker_status": "active", "connection_status": "connected"},
    }))
    result = sw.get_session_state("cse_x", bearer="b")
    assert result == {"worker_status": "active", "connection_status": "connected"}


# ── prearm_session orchestrator ────────────────────────────────────────


def test_prearm_session_returns_before_after_deltas():
    """Orchestrator returns observability bundle for caller to inspect."""
    before_state = {"connection_status": "disconnected",
                    "worker_status": "idle", "unread": False}
    after_state = {"connection_status": "disconnected",
                   "worker_status": "idle", "unread": False}
    # 2 GETs (before+after) + 1 PUT + 1 POST presence
    sw._curl_requests.get = MagicMock(side_effect=[
        _ok_resp({"session": before_state}),
        _ok_resp({"session": after_state}),
    ])
    sw._curl_requests.put = MagicMock(return_value=_ok_resp({
        "session": {**after_state, "title": "Updated"},
    }))
    sw._curl_requests.post = MagicMock(return_value=_ok_resp({
        "refresh_after_seconds": 20,
    }))

    result = sw.prearm_session(
        "cse_xyz", "MyTitle",
        bearer="STUB-OAT",
        cookies={"sessionKey": "STUB-SID"},
        client_id="cid-uuid",
    )

    assert "before" in result
    assert "put_response" in result
    assert "presence_response" in result
    assert "after" in result
    assert "deltas" in result

    # Both state snapshots had no-change → all deltas False
    assert result["deltas"]["connection_status_changed"] is False
    assert result["deltas"]["worker_status_changed"] is False
    assert result["deltas"]["unread_changed"] is False


def test_prearm_session_detects_state_changes_in_deltas():
    """If session state changes between before/after → deltas reflect it."""
    before_state = {"connection_status": "disconnected",
                    "worker_status": "idle", "unread": False}
    after_state = {"connection_status": "connected",
                   "worker_status": "active", "unread": True}
    sw._curl_requests.get = MagicMock(side_effect=[
        _ok_resp({"session": before_state}),
        _ok_resp({"session": after_state}),
    ])
    sw._curl_requests.put = MagicMock(return_value=_ok_resp({"session": after_state}))
    sw._curl_requests.post = MagicMock(return_value=_ok_resp({"refresh_after_seconds": 5}))

    result = sw.prearm_session("cse_x", "t",
                                 bearer="b", cookies={"sessionKey": "k"})
    assert result["deltas"]["connection_status_changed"] is True
    assert result["deltas"]["worker_status_changed"] is True
    assert result["deltas"]["unread_changed"] is True


# ── Pseudonymity: bearer + cookies + client_id NEVER logged ─────────────


def test_bearer_never_appears_in_any_log_record(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.session_wake")
    SECRET_BEARER = "STUB-OAT-VERY-SECRET-BEARER-do-not-leak"
    sw._curl_requests.put = MagicMock(return_value=_ok_resp({
        "session": {"worker_status": "idle"},
    }))
    sw.update_session_title("cse_test12345678", "t", bearer=SECRET_BEARER)
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_cookies_never_appear_in_any_log_record(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.session_wake")
    SECRET_SESSION = "STUB-SID-DEEP-SECRET-cookie-yyy"
    SECRET_CF = "cf-clearance-DEEP-SECRET-zzz"
    sw._curl_requests.post = MagicMock(return_value=_ok_resp({"refresh_after_seconds": 20}))
    sw.announce_client_presence(
        "cse_test12345678",
        cookies={"sessionKey": SECRET_SESSION, "cf_clearance": SECRET_CF},
        client_id="cid",
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_SESSION not in all_text
    assert SECRET_CF not in all_text


def test_session_id_truncated_in_logs(caplog):
    """Per PR #499 _LOG_ID_MAX=12 convention: session_id in logs is [:12]."""
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.session_wake")
    long_cse = "cse_012345678901234567890full"
    sw._curl_requests.put = MagicMock(return_value=_ok_resp({"session": {}}))
    sw.update_session_title(long_cse, "t", bearer="STUB")
    all_text = " ".join(r.getMessage() for r in caplog.records)
    # Truncated [:12] should be present
    assert long_cse[:12] in all_text
    # Full session_id should NOT appear (anything beyond first 12 chars)
    assert long_cse not in all_text


# ── Module-level constants (mitm-derived freezes) ───────────────────────


def test_api_anthropic_host_constant():
    """api.anthropic.com NOT claude.ai for OAuth-bearer endpoints (Q4)."""
    assert sw._API_ANTHROPIC == "https://api.anthropic.com"


def test_claude_ai_host_constant():
    """claude.ai NOT api.anthropic.com for cookie endpoints (Q4)."""
    assert sw._CLAUDE_AI == "https://claude.ai"


def test_anthropic_version_header():
    """Per Q1 captured headers."""
    assert sw._ANTHROPIC_VERSION == "2023-06-01"


def test_log_id_max_matches_pr_499_convention():
    assert sw._LOG_ID_MAX == 12


def test_all_exported():
    expected = {
        "SessionStateError",
        "update_session_title",
        "announce_client_presence",
        "get_session_state",
        "prearm_session",
    }
    assert set(sw.__all__) == expected
