"""Tests for runtime.claude_oauth_llm — OAuth-bearer LLM provider.

Drop-in replacement for AnthropicLLM that routes /v1/messages calls
through an OAuth bearer instead of an API key. Lets Max-plan quota
cover any nucleus path that previously required NUCLEUS_ANTHROPIC_API_KEY.

Coverage:
- Constructor: bearer eager-fetch, default role/model from env, ImportError
  if curl_cffi missing, ClaudeOAuthError if oauth resolve fails
- generate_content: happy path, 401-refresh-retry succeeds, 401-with-same-
  bearer-on-refresh propagates, non-401 propagates without retry, transport
  error propagates, token-budget pre-check raises RuntimeError
- _parse_response: extracts text blocks, ignores non-text blocks, parses
  usage, falls back when usage absent
- stream_content: yield-once fallback (string + list inputs)
- stream_with_tools / generate_vision: explicit NotImplementedError
- Factory dispatch: claude_oauth + claude_max + oauth all resolve to
  ClaudeOAuthLLM via get_llm_client()
- Pseudonymity: bearer NEVER appears in any log record
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.runtime import claude_oauth_llm as col


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _stub_curl():
    """Stub curl_cffi module so no real HTTP fires."""
    real = col._curl_requests
    col._curl_requests = MagicMock()
    yield
    col._curl_requests = real


@pytest.fixture(autouse=True)
def _stub_oauth_exchange(monkeypatch):
    """Insulate every test from the real oauth exchange (~/.tb cache +
    network POST to token endpoint). Each test that needs bearer
    resolution monkeypatches its own value on top.
    """
    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    monkeypatch.setattr(
        oauth_exchange, "get_access_token",
        MagicMock(return_value="test_bearer_aaa"),
    )


@pytest.fixture(autouse=True)
def _clean_oauth_env(monkeypatch):
    """Strip env vars that would affect default role/model resolution."""
    monkeypatch.delenv("NUCLEUS_OAUTH_ROLE", raising=False)
    monkeypatch.delenv("NUCLEUS_OAUTH_MODEL", raising=False)
    monkeypatch.delenv("NUCLEUS_LLM_PROVIDER", raising=False)


def _ok_resp(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


def _capture_post(payload=None, status=200):
    mock = MagicMock(return_value=_ok_resp(
        payload or {
            "id": "msg_abc",
            "model": "claude-sonnet-4-6",
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 3},
        },
        status=status,
    ))
    col._curl_requests.post = mock
    return mock


# ── Constructor ──────────────────────────────────────────────────────────


def test_constructor_eager_bearer_fetch():
    """Bearer must be resolved at construction so auth failure surfaces
    immediately rather than at first generate_content call."""
    llm = col.ClaudeOAuthLLM()
    assert llm._bearer == "test_bearer_aaa"
    assert llm.engine == "CLAUDE_OAUTH"
    assert llm.role == col._DEFAULT_ROLE
    assert llm.model_name == col._DEFAULT_MODEL


def test_constructor_uses_env_role_and_model(monkeypatch):
    monkeypatch.setenv("NUCLEUS_OAUTH_ROLE", "my_role")
    monkeypatch.setenv("NUCLEUS_OAUTH_MODEL", "claude-opus-4-7")
    llm = col.ClaudeOAuthLLM()
    assert llm.role == "my_role"
    assert llm.model_name == "claude-opus-4-7"


def test_constructor_explicit_args_override_env(monkeypatch):
    monkeypatch.setenv("NUCLEUS_OAUTH_ROLE", "env_role")
    monkeypatch.setenv("NUCLEUS_OAUTH_MODEL", "env_model")
    llm = col.ClaudeOAuthLLM(role="ctor_role", model_name="ctor_model")
    assert llm.role == "ctor_role"
    assert llm.model_name == "ctor_model"


def test_constructor_oauth_failure_raises():
    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    oauth_exchange.get_access_token = MagicMock(
        side_effect=RuntimeError("no cached token"),
    )
    with pytest.raises(col.ClaudeOAuthError, match="oauth token resolve failed"):
        col.ClaudeOAuthLLM()


def test_constructor_no_curl_cffi_raises():
    col._curl_requests = None
    with pytest.raises(ImportError, match="curl_cffi"):
        col.ClaudeOAuthLLM()


def test_constructor_ignores_factory_kwargs():
    """Factory passes provider-specific kwargs (api_key, base_url, tier,
    etc.); ClaudeOAuthLLM must swallow them silently for swap-compat."""
    llm = col.ClaudeOAuthLLM(
        api_key="ignored",
        base_url="ignored",
        tier="ignored",
        job_type="ignored",
        budget_mode="balanced",
        some_future_kwarg="ignored",
    )
    assert llm.engine == "CLAUDE_OAUTH"


# ── generate_content happy path ──────────────────────────────────────────


def test_generate_content_happy_path():
    post = _capture_post()
    llm = col.ClaudeOAuthLLM()
    resp = llm.generate_content("hi")

    assert isinstance(resp, col.ClaudeOAuthResponse)
    assert resp.text == "hello"
    assert resp.model == "claude-sonnet-4-6"
    assert resp.usage == {"input_tokens": 5, "output_tokens": 3}
    assert llm.last_stop_reason == "end_turn"

    args, kwargs = post.call_args
    assert args[0] == col._MESSAGES_URL
    assert kwargs["headers"]["Authorization"] == "Bearer test_bearer_aaa"
    assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
    assert kwargs["impersonate"] == "chrome120"
    payload = kwargs["json"]
    assert payload["model"] == "claude-sonnet-4-6"
    assert payload["messages"] == [{"role": "user", "content": "hi"}]
    assert payload["max_tokens"] == col._DEFAULT_MAX_TOKENS
    assert "system" not in payload


def test_generate_content_with_system_instruction():
    post = _capture_post()
    llm = col.ClaudeOAuthLLM(system_instruction="You are nucleus.")
    llm.generate_content("hi")
    payload = post.call_args.kwargs["json"]
    assert payload["system"] == "You are nucleus."


def test_generate_content_max_tokens_override():
    post = _capture_post()
    llm = col.ClaudeOAuthLLM()
    llm.generate_content("hi", max_tokens=2048)
    payload = post.call_args.kwargs["json"]
    assert payload["max_tokens"] == 2048


def test_generate_alias_routes_to_generate_content():
    _capture_post()
    llm = col.ClaudeOAuthLLM()
    assert llm.generate("hi").text == "hello"


def test_budget_exceeded_raises_runtime_error(monkeypatch):
    import mcp_server_nucleus.runtime.token_budget as tb
    manager_mock = MagicMock()
    manager_mock.can_execute.return_value = False
    monkeypatch.setattr(
        tb, "get_budget_manager", MagicMock(return_value=manager_mock),
    )
    llm = col.ClaudeOAuthLLM()
    with pytest.raises(RuntimeError, match="Token budget exceeded"):
        llm.generate_content("hi")


# ── 401 refresh-and-retry path ───────────────────────────────────────────


def test_401_refresh_succeeds_on_retry():
    """First POST returns 401 → fetch fresh bearer → second POST 2xx."""
    responses = [_ok_resp({"error": "auth"}, status=401), _ok_resp({
        "id": "msg_after_refresh",
        "model": "claude-sonnet-4-6",
        "content": [{"type": "text", "text": "after refresh"}],
        "stop_reason": "end_turn",
    })]
    post = MagicMock(side_effect=responses)
    col._curl_requests.post = post

    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    oauth_exchange.get_access_token = MagicMock(
        side_effect=["bearer_orig", "bearer_fresh"],
    )

    llm = col.ClaudeOAuthLLM()
    resp = llm.generate_content("hi")

    assert resp.text == "after refresh"
    assert post.call_count == 2
    assert llm._bearer == "bearer_fresh"
    second_headers = post.call_args_list[1].kwargs["headers"]
    assert second_headers["Authorization"] == "Bearer bearer_fresh"


def test_401_refresh_returns_same_bearer_propagates():
    """If force_refresh returns the same bearer, propagate the 401 rather
    than loop. (Bearer is fundamentally invalid; no point retrying.)"""
    col._curl_requests.post = MagicMock(
        return_value=_ok_resp({"error": "auth"}, status=401),
    )

    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    oauth_exchange.get_access_token = MagicMock(return_value="same_bearer")

    llm = col.ClaudeOAuthLLM()
    with pytest.raises(col.ClaudeOAuthError, match="status=401"):
        llm.generate_content("hi")


def test_401_refresh_fail_propagates_original_401():
    """If bearer-refresh itself raises, propagate the original 401 chain."""
    col._curl_requests.post = MagicMock(
        return_value=_ok_resp({"error": "auth"}, status=401),
    )

    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    call_count = {"n": 0}

    def _flaky(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "bearer_orig"
        raise RuntimeError("refresh endpoint down")

    oauth_exchange.get_access_token = MagicMock(side_effect=_flaky)

    llm = col.ClaudeOAuthLLM()
    # Either propagates as ClaudeOAuthError (refresh wrap) or original 401
    # — both acceptable; what matters is no infinite loop.
    with pytest.raises(col.ClaudeOAuthError):
        llm.generate_content("hi")


def test_non_401_does_not_retry():
    """500/429/etc must NOT trigger refresh-retry; only 401 should."""
    col._curl_requests.post = MagicMock(
        return_value=_ok_resp({"error": "rate"}, status=429),
    )
    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    refresh_mock = MagicMock(return_value="never_called")
    oauth_exchange.get_access_token = MagicMock(return_value="bearer_orig")

    llm = col.ClaudeOAuthLLM()
    # Replace refresh-path mock after construction
    oauth_exchange.get_access_token = refresh_mock

    with pytest.raises(col.ClaudeOAuthError, match="status=429"):
        llm.generate_content("hi")
    assert refresh_mock.call_count == 0


def test_transport_error_propagates():
    col._curl_requests.post = MagicMock(side_effect=ConnectionError("boom"))
    llm = col.ClaudeOAuthLLM()
    with pytest.raises(col.ClaudeOAuthError, match="transport error"):
        llm.generate_content("hi")


# ── Response parsing ─────────────────────────────────────────────────────


def test_parse_response_concatenates_text_blocks():
    payload = {
        "content": [
            {"type": "text", "text": "part 1"},
            {"type": "text", "text": "part 2"},
        ],
        "model": "claude-sonnet-4-6",
        "usage": {"input_tokens": 10, "output_tokens": 4},
    }
    llm = col.ClaudeOAuthLLM()
    resp = llm._parse_response(payload)
    assert resp.text == "part 1\npart 2"
    assert resp.usage == {"input_tokens": 10, "output_tokens": 4}


def test_parse_response_ignores_non_text_blocks():
    payload = {
        "content": [
            {"type": "text", "text": "just this"},
            {"type": "tool_use", "name": "x", "input": {}},
            "not-a-dict",
        ],
        "model": "x",
    }
    llm = col.ClaudeOAuthLLM()
    resp = llm._parse_response(payload)
    assert resp.text == "just this"


def test_parse_response_handles_missing_usage():
    llm = col.ClaudeOAuthLLM()
    resp = llm._parse_response({
        "content": [{"type": "text", "text": "hi"}], "model": "x",
    })
    assert resp.usage == {"input_tokens": 0, "output_tokens": 0}


def test_parse_response_handles_empty_content():
    llm = col.ClaudeOAuthLLM()
    resp = llm._parse_response({"model": "x"})
    assert resp.text == ""


# ── stream_content fallback ──────────────────────────────────────────────


def test_stream_content_yields_once_for_string_prompt():
    _capture_post()
    llm = col.ClaudeOAuthLLM()
    chunks = list(llm.stream_content("hi"))
    assert chunks == ["hello"]


def test_stream_content_collapses_list_to_last_user_turn():
    post = _capture_post()
    llm = col.ClaudeOAuthLLM()
    list(llm.stream_content([
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
        {"role": "user", "content": "second"},
    ]))
    payload = post.call_args.kwargs["json"]
    assert payload["messages"][0]["content"] == "second"


def test_stream_content_handles_list_with_no_user_turn():
    post = _capture_post()
    llm = col.ClaudeOAuthLLM()
    list(llm.stream_content([{"role": "assistant", "content": "alone"}]))
    payload = post.call_args.kwargs["json"]
    assert payload["messages"][0]["content"] == ""


# ── Unsupported v1 methods ───────────────────────────────────────────────


def test_stream_with_tools_raises_not_implemented():
    llm = col.ClaudeOAuthLLM()
    with pytest.raises(NotImplementedError, match="stream_with_tools"):
        next(llm.stream_with_tools([{"role": "user", "content": "hi"}]))


def test_generate_vision_raises_not_implemented():
    llm = col.ClaudeOAuthLLM()
    with pytest.raises(NotImplementedError, match="generate_vision"):
        llm.generate_vision(["/some/path.png"], "describe")


# ── Factory dispatch (the silent-fix wiring) ─────────────────────────────


def test_factory_claude_oauth_returns_ClaudeOAuthLLM():
    from mcp_server_nucleus.runtime.llm_client import get_llm_client
    llm = get_llm_client(provider="claude_oauth")
    assert isinstance(llm, col.ClaudeOAuthLLM)


def test_factory_claude_max_alias():
    from mcp_server_nucleus.runtime.llm_client import get_llm_client
    llm = get_llm_client(provider="claude_max")
    assert isinstance(llm, col.ClaudeOAuthLLM)


def test_factory_oauth_alias():
    from mcp_server_nucleus.runtime.llm_client import get_llm_client
    llm = get_llm_client(provider="oauth")
    assert isinstance(llm, col.ClaudeOAuthLLM)


def test_factory_env_var_dispatch(monkeypatch):
    monkeypatch.setenv("NUCLEUS_LLM_PROVIDER", "claude_oauth")
    from mcp_server_nucleus.runtime.llm_client import get_llm_client
    llm = get_llm_client()
    assert isinstance(llm, col.ClaudeOAuthLLM)


def test_factory_unknown_provider_message_lists_claude_oauth():
    from mcp_server_nucleus.runtime.llm_client import get_llm_client
    with pytest.raises(ValueError, match="claude_oauth"):
        get_llm_client(provider="bogus_xyz")


# ── Pseudonymity: bearer never appears in logs ───────────────────────────


def test_bearer_never_logged(caplog):
    """Bearer must never appear in any log record at any level — this is
    the pseudonymity contract carried over from autonomous_wake."""
    secret = "sk-ant-oat01-pseudonymous-test-bearer-must-not-leak"

    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    oauth_exchange.get_access_token = MagicMock(return_value=secret)

    _capture_post()
    with caplog.at_level(logging.DEBUG, logger="nucleus.oauth_llm"):
        llm = col.ClaudeOAuthLLM()
        llm.generate_content("hi")

    for rec in caplog.records:
        assert secret not in rec.getMessage(), (
            f"BEARER LEAKED in log: {rec.getMessage()!r}"
        )


def test_prompt_body_never_logged(caplog):
    """Prompt content must never appear in logs (only counts + status)."""
    sensitive = "ABRACADABRA_OPEN_SESAME_12345"
    _capture_post()
    with caplog.at_level(logging.DEBUG, logger="nucleus.oauth_llm"):
        llm = col.ClaudeOAuthLLM()
        llm.generate_content(sensitive)
    for rec in caplog.records:
        assert sensitive not in rec.getMessage(), (
            f"PROMPT LEAKED in log: {rec.getMessage()!r}"
        )
