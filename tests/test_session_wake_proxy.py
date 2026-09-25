"""Tests for Phase C — OCI session-wake proxy branch + graceful no-raise degradation.

Per .brain/specs/v022_mac_local_wake_proxy_via_cf_tunnel.md + op-assistant
2026-06-08T14:35Z PHASE_B_PERSISTENCE_LIVE_PHASE_C_NUDGE relay (8 RULES
graceful-fallback rubric + 7+ test cases).

Phase 5 empirical 2026-06-08T12:30Z proved Anthropic anti-abuse IP-binds
session cookies — OCI direct POSTs return 403, Mac POSTs return 200.
Phase C adds Mac-proxy branch so wake POSTs traverse operator's IP.

Coverage maps to 8 RULES + 7 spec test cases + supporting defensive cases.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ─────────────────────────────────────────────────────────────


def _proxy_cfg(
    kind="dispatch",
    session_id="cse_012BCRpC434rxksdqWCcDCet",
    chat_uuid=None,
    org_id="org-uuid-stub",
    cookies=None,
    wake_proxy_url="https://wake.nucleusos.dev/wake/bespoq_cowork",
    wake_proxy_token="proxy-bearer-stub",
):
    """Build a Phase C wake-map entry (with proxy fields)."""
    if cookies is None:
        cookies = {
            "sessionKey": "sk-stub", "lastActiveOrg": "lao",
            "anthropic-device-id": "dev", "cf_clearance": "cf",
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


class _MockResp:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "err",
                request=httpx.Request("POST", "https://stub"),
                response=MagicMock(status_code=self.status_code),
            )


class _MockAsyncClient:
    def __init__(self, *, response=None, raise_exc=None):
        self.response = response or _MockResp(200)
        self.raise_exc = raise_exc
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers or {}, "json": json or {}})
        if self.raise_exc:
            raise self.raise_exc
        return self.response


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch):
    from mcp_server_nucleus.http_transport import relay_route
    for k in ("NUCLEUS_SESSION_WAKE_MAP", "NUCLEUS_COWORK_WAKE_MAP"):
        monkeypatch.delenv(k, raising=False)
    relay_route._reset_session_wake_map_cache()
    yield
    relay_route._reset_session_wake_map_cache()


# ── Spec test 1: proxy returns 200 → success, direct NOT called ──────────


@pytest.mark.asyncio
async def test_proxy_200_success_direct_not_called(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": _proxy_cfg()}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_client = _MockAsyncClient(response=_MockResp(200))
    with patch("httpx.AsyncClient", return_value=proxy_client):
        await relay_route._maybe_wake_session("bespoq_cowork")

    assert len(proxy_client.calls) == 1, "proxy should be called once"
    assert "wake.nucleusos.dev" in proxy_client.calls[0]["url"]


# ── Spec test 2: proxy returns 503 → swallowed, no raise (RULE 1) ────────


@pytest.mark.asyncio
async def test_proxy_503_swallowed_no_raise(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": _proxy_cfg()}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock(side_effect=Exception("proxy 503"))
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("bespoq_cowork")

    proxy_mock.assert_awaited_once()


# ── Spec test 3: proxy timeout → same as 503 (swallowed, no raise) ───────


@pytest.mark.asyncio
async def test_proxy_timeout_swallowed_no_raise(monkeypatch):
    import httpx
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": _proxy_cfg()}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock(side_effect=httpx.TimeoutException("slow"))
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("bespoq_cowork")


# ── Spec test 4: proxy DNS-fail → graceful WARN, swallowed ──────────────


@pytest.mark.asyncio
async def test_proxy_dns_fail_swallowed_no_raise(monkeypatch, caplog):
    import logging, httpx
    caplog.set_level(logging.WARNING, logger="nucleus.relay")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({
        "bespoq_cowork": _proxy_cfg(wake_proxy_url="https://nonexistent.tld.invalid/wake/x"),
    }))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock(side_effect=httpx.ConnectError("DNS resolve failed"))
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("bespoq_cowork")
    warn_msgs = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert any("proxy failed" in m for m in warn_msgs)


# ── Spec test 5: wake_proxy_url absent → no POST attempted (proxy-only) ──


@pytest.mark.asyncio
async def test_no_proxy_url_no_post_attempted(monkeypatch):
    cfg = _proxy_cfg(wake_proxy_url=None, wake_proxy_token=None)
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock()
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("bespoq_cowork")

    proxy_mock.assert_not_awaited()


# ── Spec test 6: empty wake-map → no wake attempts ──────────────────────


@pytest.mark.asyncio
async def test_empty_wake_map_no_attempts(monkeypatch):
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock()
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("any_role")

    proxy_mock.assert_not_awaited()


# ── Spec test 7: malformed JSON env → log ERROR, treat empty ────────────


@pytest.mark.asyncio
async def test_malformed_json_env_no_attempts(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", "not-json {{")
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock()
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("any_role")

    proxy_mock.assert_not_awaited()


# ── RULE 1: wake never raises even if everything fails ──────────────────


@pytest.mark.asyncio
async def test_rule_1_proxy_fail_does_not_raise(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": _proxy_cfg()}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    with patch.object(relay_route, "_post_via_proxy",
                      new=AsyncMock(side_effect=Exception("proxy down"))):
        # MUST NOT raise — relay write succeeded, wake is best-effort
        await relay_route._maybe_wake_session("bespoq_cowork")


# ── RULE 2: unknown kind → WARN + skip + metric status=skip ─────────────


@pytest.mark.asyncio
async def test_rule_2_unknown_kind_skipped_with_metric(monkeypatch):
    cfg = _proxy_cfg(kind="quantum_telepathy")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"weird_role": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock()
    metric_mock = MagicMock()
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock), \
         patch.object(relay_route, "_emit_wake_metric", new=metric_mock):
        await relay_route._maybe_wake_session("weird_role")

    proxy_mock.assert_not_awaited()
    metric_mock.assert_called_with("weird_role", "quantum_telepathy", "skip")


# ── RULE 4: wake_proxy_url present but token missing → skip proxy ───────


@pytest.mark.asyncio
async def test_rule_4_proxy_url_without_token_aborts(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.relay")
    cfg = _proxy_cfg(wake_proxy_url="https://wake.x/wake/y", wake_proxy_token=None)
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"role_x": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_mock = AsyncMock()
    with patch.object(relay_route, "_post_via_proxy", new=proxy_mock):
        await relay_route._maybe_wake_session("role_x")

    proxy_mock.assert_not_awaited(), "proxy MUST NOT fire when token missing (RULE 4)"
    assert any("wake_proxy_token missing" in r.message for r in caplog.records)


# ── RULE 7: pseudonymity — IDs truncated, tokens/cookies never logged ────


@pytest.mark.asyncio
async def test_rule_7_log_id_truncation_and_token_never_logged(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.relay")
    SECRET_TOKEN = "sk-ant-VERY-SECRET-WAKE-PROXY-TOKEN-xyz"
    cfg = _proxy_cfg(wake_proxy_token=SECRET_TOKEN,
                     session_id="cse_012BCRpCverylongsessionidthatshouldbetruncated")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"role_x": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_client = _MockAsyncClient(response=_MockResp(200))
    with patch("httpx.AsyncClient", return_value=proxy_client):
        await relay_route._maybe_wake_session("role_x")

    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    # Token NEVER appears
    assert SECRET_TOKEN not in all_log_text, "proxy_token leaked into logs"
    # Full session_id NEVER appears (anything beyond first 12 chars)
    assert "cse_012BCRpCverylongsessionidthatshouldbetruncated" not in all_log_text
    # Truncated [:12] should be present
    assert "cse_012BCRpC"[:12] in all_log_text


# ── RULE 8: metric counter emitted with correct labels ──────────────────


@pytest.mark.asyncio
async def test_rule_8_metric_emitted_on_proxy_success(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": _proxy_cfg()}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    metric_mock = MagicMock()
    with patch.object(relay_route, "_post_via_proxy", new=AsyncMock(return_value=None)), \
         patch.object(relay_route, "_emit_wake_metric", new=metric_mock):
        await relay_route._maybe_wake_session("bespoq_cowork")

    metric_mock.assert_called_with("bespoq_cowork", "dispatch", "ok")


@pytest.mark.asyncio
async def test_rule_8_metric_emitted_on_proxy_fail(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"bespoq_cowork": _proxy_cfg()}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    metric_mock = MagicMock()
    with patch.object(relay_route, "_post_via_proxy",
                      new=AsyncMock(side_effect=Exception("proxy down"))), \
         patch.object(relay_route, "_emit_wake_metric", new=metric_mock):
        await relay_route._maybe_wake_session("bespoq_cowork")

    # Should see proxy_fail metric
    metric_calls = [c.args for c in metric_mock.call_args_list]
    assert ("bespoq_cowork", "dispatch", "fail") in metric_calls
    assert ("bespoq_cowork", "dispatch", "ok") not in metric_calls


# ── Proxy body shape ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_proxy_body_includes_session_id_for_dispatch(monkeypatch):
    cfg = _proxy_cfg(kind="dispatch", session_id="cse_abc123")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"role_x": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_client = _MockAsyncClient(response=_MockResp(200))
    with patch("httpx.AsyncClient", return_value=proxy_client):
        await relay_route._maybe_wake_session("role_x")

    assert len(proxy_client.calls) == 1
    body = proxy_client.calls[0]["json"]
    assert body["kind"] == "dispatch"
    assert body["session_id"] == "cse_abc123"
    assert body["org_id"] == "org-uuid-stub"
    assert "WAKE" in body["message"] or "wake" in body["message"].lower()


@pytest.mark.asyncio
async def test_proxy_body_includes_chat_uuid_for_chat_kind(monkeypatch):
    cfg = _proxy_cfg(kind="chat", session_id=None,
                     chat_uuid="a3218eba-61d4-447f-ba1a-55162aadaab4")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"chat_role": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_client = _MockAsyncClient(response=_MockResp(200))
    with patch("httpx.AsyncClient", return_value=proxy_client):
        await relay_route._maybe_wake_session("chat_role")

    body = proxy_client.calls[0]["json"]
    assert body["kind"] == "chat"
    assert body["chat_conversation_uuid"] == "a3218eba-61d4-447f-ba1a-55162aadaab4"
    assert "session_id" not in body


@pytest.mark.asyncio
async def test_proxy_authorization_header_is_bearer_token(monkeypatch):
    cfg = _proxy_cfg(wake_proxy_token="my-secret-proxy-token")
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"role_x": cfg}))
    from mcp_server_nucleus.http_transport import relay_route
    relay_route._reset_session_wake_map_cache()

    proxy_client = _MockAsyncClient(response=_MockResp(200))
    with patch("httpx.AsyncClient", return_value=proxy_client):
        await relay_route._maybe_wake_session("role_x")

    headers = proxy_client.calls[0]["headers"]
    assert headers.get("Authorization") == "Bearer my-secret-proxy-token"
