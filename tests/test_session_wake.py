"""Tests for ADR-0037 session-wake orchestration in relay_route.py (Phase C).

Per .brain/specs/v022_mac_local_wake_proxy_via_cf_tunnel.md: the wake path
is PROXY-ONLY — `_post_wake_event` routes through the Mac-side wake proxy
(`wake_proxy_url` + `wake_proxy_token` in the wake-map entry); the direct
claude.ai path was removed per dead-code audit. The proxy handles cookies
and endpoint-branching Mac-side, so client-side cfg validation (cookies,
chat uuid presence) no longer exists — missing IDs are posted as "" and
validated by the proxy.

This file covers the orchestrator surface (`_maybe_wake_session` →
`_post_wake_event`): map loading/precedence, kind gating, error
swallowing (RULE 1), and log/pseudonymity discipline. The companion
file `test_session_wake_proxy.py` covers `_post_via_proxy` specifics
(body shapes, bearer header, RULE 2/4/7/8).

History: the original 15 spec cases (oci_cowork_wake_extension.md, Phase 4)
asserted direct claude.ai endpoint URLs; cases 2/3/11 were deleted and the
rest retargeted to the proxy contract when Phase C made them stale
(Task #459).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ─────────────────────────────────────────────────────────────


_DEFAULT_COOKIES_SENTINEL = object()

_PROXY_URL = "https://wake.nucleusos.dev/wake/test-role"
_PROXY_TOKEN = "proxy-bearer-stub"


def _wake_cfg(kind="dispatch", session_id="cse_012BCRpC434rxksdqWCcDCet",
              chat_uuid=None, org_id="org-uuid-stub",
              cookies=_DEFAULT_COOKIES_SENTINEL,
              wake_proxy_url=_PROXY_URL, wake_proxy_token=_PROXY_TOKEN):
    """Build a wake-map entry matching the Phase C proxy shape.

    Legacy cookie fields are kept in the default cfg because deployed
    wake-map entries still carry them; production ignores them client-side
    (proxy reads cookies from Mac Keychain). Pass wake_proxy_url=None to
    build a proxy-less entry.

    cookies sentinel distinguishes 'not specified' (use defaults) from
    explicit empty dict.
    """
    if cookies is _DEFAULT_COOKIES_SENTINEL:
        cookies = {
            "sessionKey": "sk-ant-sid02-stub",
            "lastActiveOrg": "lao-uuid",
            "anthropic-device-id": "dev-uuid",
            "cf_clearance": "cf-stub",
        }
    cfg = {"kind": kind, "org_id": org_id, "cookies": cookies}
    if session_id is not None:
        cfg["session_id"] = session_id
    if chat_uuid is not None:
        cfg["chat_conversation_uuid"] = chat_uuid
    if wake_proxy_url is not None:
        cfg["wake_proxy_url"] = wake_proxy_url
    if wake_proxy_token is not None:
        cfg["wake_proxy_token"] = wake_proxy_token
    return cfg


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch):
    """Reset wake-map env vars + clear module-level cache each test."""
    from mcp_server_nucleus.http_transport import relay_route
    for k in ("NUCLEUS_SESSION_WAKE_MAP", "NUCLEUS_COWORK_WAKE_MAP"):
        monkeypatch.delenv(k, raising=False)
    relay_route._reset_session_wake_map_cache()
    yield
    relay_route._reset_session_wake_map_cache()


class _MockResp:
    """Minimal mock for httpx.Response that supports raise_for_status."""
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            req = httpx.Request("POST", "https://stub")
            raise httpx.HTTPStatusError("err", request=req, response=MagicMock(status_code=self.status_code))


class _MockAsyncClient:
    """Mock httpx.AsyncClient context manager."""
    def __init__(self, *, response=None, raise_exc=None):
        self.response = response or _MockResp(200)
        self.raise_exc = raise_exc
        self.last_url = None
        self.last_headers = None
        self.last_json = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers=None, json=None):
        self.last_url = url
        self.last_headers = headers
        self.last_json = json
        if self.raise_exc:
            raise self.raise_exc
        return self.response


# ── Test 1: no wake config → no POST attempted ──────────────────────────


@pytest.mark.asyncio
async def test_case1_no_wake_config_for_recipient_no_post_attempted(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch.object(relay_route, "_post_wake_event", new=AsyncMock()) as mock_post:
        await relay_route._maybe_wake_session("not_registered_role")
    mock_post.assert_not_called()


# ── Test 4: cloud_cc kind → proxy body carries kind + session_id ────────


@pytest.mark.asyncio
async def test_case4_cloud_cc_kind_posts_proxy_body_with_session_id(monkeypatch):
    """cloud_cc is the third known kind; proxy body must carry it verbatim
    with session_id (the companion proxy file only covers dispatch + chat)."""
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "cloud_cc_main": _wake_cfg(kind="cloud_cc", session_id="session_abc"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("cloud_cc_main")
    assert fake_client.last_url == _PROXY_URL
    assert fake_client.last_json["kind"] == "cloud_cc"
    assert fake_client.last_json["session_id"] == "session_abc"
    assert "chat_conversation_uuid" not in fake_client.last_json


# ── Test 5: proxy 401 → relay green, wake fail logged ───────────────────


@pytest.mark.asyncio
async def test_case5_wake_401_does_not_raise(monkeypatch, caplog):
    """Exercises the real raise_for_status → except branch in
    _post_wake_event (the proxy file patches _post_via_proxy for its
    failure tests, so the HTTP-status path is only covered here)."""
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.relay")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "bespoq_cowork": _wake_cfg(kind="dispatch"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient(response=_MockResp(status_code=401))
    with patch("httpx.AsyncClient", return_value=fake_client):
        # MUST NOT raise — best-effort, relay write succeeded
        await relay_route._maybe_wake_session("bespoq_cowork")
    # POST was actually attempted (guards against vacuous early-return pass)
    assert fake_client.last_url == _PROXY_URL
    warn_msgs = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any("session-wake proxy failed" in m for m in warn_msgs)


# ── Test 6: 200 success → relay green + INFO log ────────────────────────


@pytest.mark.asyncio
async def test_case6_wake_200_logs_info(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.relay")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "bespoq_cowork": _wake_cfg(kind="dispatch"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient(response=_MockResp(200))
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("bespoq_cowork")
    info_msgs = [r.message for r in caplog.records if r.levelname == "INFO"]
    assert any(
        "session-wake via proxy fired" in m and "kind=dispatch" in m
        for m in info_msgs
    )


# ── Test 7: timeout / connect error → no raise ──────────────────────────


@pytest.mark.asyncio
async def test_case7_wake_timeout_does_not_raise(monkeypatch):
    """httpx-level timeout inside _post_via_proxy must be swallowed by
    _post_wake_event's except (RULE 1)."""
    import httpx
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "bespoq_cowork": _wake_cfg(kind="dispatch"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient(raise_exc=httpx.TimeoutException("slow"))
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("bespoq_cowork")
    # POST attempted, exception swallowed — not a vacuous early-return pass
    assert fake_client.last_url == _PROXY_URL


# ── Test 8: empty wake-map env → early return ───────────────────────────


@pytest.mark.asyncio
async def test_case8_empty_wake_map_early_returns(monkeypatch):
    # No env vars set (autouse fixture cleared them)
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    with patch.object(relay_route, "_post_wake_event", new=AsyncMock()) as mock_post:
        await relay_route._maybe_wake_session("any_role")
    mock_post.assert_not_called()


# ── Test 9: malformed JSON env → empty map, no crash ────────────────────


@pytest.mark.asyncio
async def test_case9_malformed_json_env_disables_wake(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", "not-valid-json{{")
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    wake_map = relay_route._get_session_wake_map()
    assert wake_map == {}
    with patch.object(relay_route, "_post_wake_event", new=AsyncMock()) as mock_post:
        await relay_route._maybe_wake_session("any_role")
    mock_post.assert_not_called()


# ── Test 10: missing 'kind' field → defaults to dispatch ────────────────


@pytest.mark.asyncio
async def test_case10_missing_kind_field_defaults_to_dispatch(monkeypatch):
    """Backward-compat: wake-map entries without 'kind' must continue
    working — proxy body carries the defaulted kind."""
    cfg_without_kind = _wake_cfg(session_id="cse_legacy")
    del cfg_without_kind["kind"]
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "legacy_role": cfg_without_kind,
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("legacy_role")
    assert fake_client.last_json["kind"] == "dispatch"
    assert fake_client.last_json["session_id"] == "cse_legacy"


# ── Test 12: kind='unknown' → skipped + WARN ────────────────────────────


@pytest.mark.asyncio
async def test_case12_unknown_kind_skipped(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "weird_role": _wake_cfg(kind="some_future_kind"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("weird_role")
    assert fake_client.last_url is None


# ── Test 13: NUCLEUS_SESSION_WAKE_MAP wins over NUCLEUS_COWORK_WAKE_MAP ──


@pytest.mark.asyncio
async def test_case13_session_map_wins_over_cowork_map(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "role_x": _wake_cfg(kind="dispatch", session_id="cse_NEW_NAME"),
    }))
    monkeypatch.setenv("NUCLEUS_COWORK_WAKE_MAP", json.dumps({
        "role_x": _wake_cfg(kind="dispatch", session_id="cse_OLD_NAME"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("role_x")
    assert fake_client.last_json["session_id"] == "cse_NEW_NAME"


# ── Test 14: only NUCLEUS_COWORK_WAKE_MAP set → backward-compat ─────────


@pytest.mark.asyncio
async def test_case14_cowork_map_fallback_when_session_map_unset(monkeypatch):
    """Phase 3 deployed with the OLD env name; must keep working."""
    monkeypatch.setenv("NUCLEUS_COWORK_WAKE_MAP", json.dumps({
        "bespoq_cowork": _wake_cfg(kind="dispatch", session_id="cse_PHASE_3_LIVE"),
    }))
    # NUCLEUS_SESSION_WAKE_MAP intentionally NOT set
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("bespoq_cowork")
    assert fake_client.last_json["session_id"] == "cse_PHASE_3_LIVE"


# ── Test 15: response body never iterated (cc-peer Crack 6) ──────────────


@pytest.mark.asyncio
async def test_case15_response_body_not_iterated(monkeypatch):
    """Crack 6 guard, retargeted to the proxy path: _post_via_proxy only
    needs the HTTP head (raise_for_status + status_code) to confirm
    acceptance. Iterating the response body would hold the socket open
    per session-wake — and must never start, regardless of what the
    proxy streams back.

    Verification: mock response tracks whether aiter_* methods are called.
    """
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "chat_role": _wake_cfg(
            kind="chat", session_id=None,
            chat_uuid="a3218eba-61d4-447f-ba1a-55162aadaab4",
        ),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    iter_attempted = []

    class _TrackingResp(_MockResp):
        def __init__(self):
            super().__init__(200)
            self.aiter_bytes = lambda: iter_attempted.append("bytes")
            self.aiter_lines = lambda: iter_attempted.append("lines")
            self.aiter_text = lambda: iter_attempted.append("text")
            self.aiter_raw = lambda: iter_attempted.append("raw")

    fake_client = _MockAsyncClient(response=_TrackingResp())
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("chat_role")
    assert iter_attempted == [], (
        f"_post_via_proxy consumed response body chunks: {iter_attempted}. "
        "Should only check status_code and exit context-manager."
    )


# ── Missing session_id → posted as "" (proxy validates Mac-side) ────────


@pytest.mark.asyncio
async def test_dispatch_missing_session_id_posts_empty_id(monkeypatch):
    """Phase C behavior change: the client no longer skips entries with
    missing IDs — it posts session_id="" (resp. chat_conversation_uuid="")
    and the proxy validates Mac-side."""
    cfg = _wake_cfg(kind="dispatch", session_id=None)
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"role": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("role")
    assert fake_client.last_url == _PROXY_URL
    assert fake_client.last_json["session_id"] == ""


# ── Secrets never logged (pseudonymity discipline, RULE 7) ──────────────


@pytest.mark.asyncio
async def test_cookie_values_never_logged(monkeypatch, caplog):
    """Legacy cookie blobs may still ride in deployed wake-map entries;
    neither they nor the proxy bearer token may reach logs."""
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.relay")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "bespoq_cowork": _wake_cfg(
            kind="dispatch",
            cookies={
                "sessionKey": "sk-ant-sid02-VERY-SECRET-DO-NOT-LEAK",
                "lastActiveOrg": "org-id-secret",
                "anthropic-device-id": "dev-id-secret",
                "cf_clearance": "cf-clearance-secret",
            },
        ),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()
    fake_client = _MockAsyncClient()
    with patch("httpx.AsyncClient", return_value=fake_client):
        await relay_route._maybe_wake_session("bespoq_cowork")
    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    assert "sk-ant-sid02-VERY-SECRET-DO-NOT-LEAK" not in all_log_text
    assert "cf-clearance-secret" not in all_log_text
    assert _PROXY_TOKEN not in all_log_text
