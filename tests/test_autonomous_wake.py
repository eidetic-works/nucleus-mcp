"""Tests for v0.3.0 Layer 5 — mcp_server_nucleus.sessions.autonomous_wake.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 5
(spec lines 147-156) + op-assistant 2026-06-09T03:50Z Layer 3 NULL
VERDICT (no /run primitive → Layer 5 MANDATORY) + 2026-06-09T09:15Z
architectural amendment (build INTO nucleus).

Coverage:
- compose_wake_payload: shape, system/tools/mcp_servers optional,
  history threading, wake_instruction required
- post_inference: Bearer + anthropic-version + POST to
  /v1/messages?beta=true, raises on non-2xx, raises on transport
- extract_tool_use_blocks: filters content blocks
- _get_session_events: helper resilience (returns [] on failure)
- autonomous_wake_from_relay: orchestrator wires history + discovery
  context + bearer, returns ok+response+tool_use_blocks
- Pseudonymity: bearer + wake_instruction content + cookies never
  logged at any level
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.sessions import autonomous_wake as aw


@pytest.fixture(autouse=True)
def _stub_curl():
    real = aw._curl_requests
    aw._curl_requests = MagicMock()
    yield
    aw._curl_requests = real


@pytest.fixture(autouse=True)
def _stub_oauth_exchange(monkeypatch):
    """Insulate every test from the real oauth exchange (~/.tb cache reads
    + network POST to the token endpoint). _refreshed_bearer's broad
    except converts the AssertionError to None, so an accidental
    traversal degrades to original-401-propagates instead of touching
    the operator's token cache. Refresh tests monkeypatch their own
    seam on top."""
    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    monkeypatch.setattr(
        oauth_exchange, "get_access_token",
        MagicMock(side_effect=AssertionError("real oauth exchange touched")),
    )


def _ok_resp(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


def _capture_post(payload=None):
    mock = MagicMock(return_value=_ok_resp(payload or {
        "id": "msg_abc",
        "content": [{"type": "text", "text": "ack"}],
        "stop_reason": "end_turn",
    }))
    aw._curl_requests.post = mock
    return mock


def _capture_get(payload=None):
    mock = MagicMock(return_value=_ok_resp(payload or {"events": []}))
    aw._curl_requests.get = mock
    return mock


# ── compose_wake_payload ────────────────────────────────────────────────


def test_compose_payload_shape_minimum():
    """Plan B: nucleus_relay always injected → tools[] always present."""
    payload = aw.compose_wake_payload(wake_instruction="hello")
    assert payload["model"] == aw._DEFAULT_MODEL
    assert payload["max_tokens"] == aw._DEFAULT_MAX_TOKENS
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert "system" not in payload
    assert "mcp_servers" not in payload
    # nucleus_relay always injected (Plan B)
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["name"] == "nucleus_relay"


def test_compose_payload_with_system_and_tools():
    """LOOP-CLOSE: mcp_servers field is NEVER set on payload (Anthropic
    400). Instead, MCP tools are FLATTENED into tools[]."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        system_prompt="You are cc-tb.",
        tools=[{"name": "nucleus_relay", "description": "fire relay"}],
        mcp_servers=[{
            "uuid": "srv-1",
            "name": "nucleus",
            "tools": [{"name": "post_to_inbox", "description": "Post relay"}],
        }],
    )
    assert payload["system"] == "You are cc-tb."
    # mcp_servers NEVER passed as top-level field (Anthropic 400 fix)
    assert "mcp_servers" not in payload
    # caller-supplied tools + flattened MCP tools combined
    tool_names = [t["name"] for t in payload["tools"]]
    assert "nucleus_relay" in tool_names
    assert "post_to_inbox" in tool_names


def test_compose_payload_threads_history_before_wake_user_turn():
    history = [
        {"role": "user", "content": "previous user msg"},
        {"role": "assistant", "content": "previous assistant reply"},
        {"role": "tool", "content": "ignored — not user/assistant"},
        {"role": "user", "content": ""},  # dropped — empty content
    ]
    payload = aw.compose_wake_payload(
        wake_instruction="new wake", history=history,
    )
    assert len(payload["messages"]) == 3  # 2 valid history + 1 new user
    assert payload["messages"][0] == {"role": "user", "content": "previous user msg"}
    assert payload["messages"][1] == {"role": "assistant", "content": "previous assistant reply"}
    assert payload["messages"][-1] == {"role": "user", "content": "new wake"}


def test_compose_payload_raises_on_empty_wake_instruction():
    with pytest.raises(aw.AutonomousWakeError):
        aw.compose_wake_payload(wake_instruction="")


# ── LOOP-CLOSE: flatten MCP tools into tools[] (Anthropic 400 fix) ─────


def test_mcp_servers_never_set_as_top_level_payload_field():
    """Anthropic /v1/messages?beta=true rejects mcp_servers (HTTP 400).
    LOOP-CLOSE fix: NEVER set this field on payload."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[{
            "uuid": "srv-1", "name": "nucleus",
            "tools": [{"name": "t1", "description": "d"}],
        }],
    )
    assert "mcp_servers" not in payload


def test_flatten_mcp_tools_one_server_one_tool():
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[{
            "name": "gmail",
            "tools": [{
                "name": "search_threads",
                "description": "List email threads from Gmail",
                "input_schema": {
                    "type": "object",
                    "properties": {"q": {"type": "string"}},
                },
            }],
        }],
    )
    # Gmail tool + injected nucleus_relay = 2 tools
    assert len(payload["tools"]) == 2
    t = next(t for t in payload["tools"] if t["name"] == "search_threads")
    assert t["description"] == "List email threads from Gmail"
    assert t["input_schema"]["type"] == "object"
    assert "q" in t["input_schema"]["properties"]
    # nucleus_relay also present
    assert any(t["name"] == "nucleus_relay" for t in payload["tools"])


def test_flatten_mcp_tools_multiple_servers_combine():
    """55 MCP tools across multiple servers all become tools[] entries
    (per op-assistant 15:56Z empirical breakthrough — bespoq has 55+)."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[
            {"name": "gmail", "tools": [
                {"name": "search_threads"},
                {"name": "send_email"},
            ]},
            {"name": "github", "tools": [
                {"name": "list_issues"},
                {"name": "create_pr"},
            ]},
        ],
    )
    tool_names = [t["name"] for t in payload["tools"]]
    # 4 MCP tools + injected nucleus_relay at end (no dedup-conflict)
    assert tool_names == [
        "search_threads", "send_email", "list_issues", "create_pr",
        "nucleus_relay",
    ]


def test_flatten_mcp_tools_combined_with_caller_tools():
    """Caller-supplied tools[] precede flattened MCP tools."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        tools=[{"name": "nucleus_relay"}],
        mcp_servers=[{"name": "gmail", "tools": [{"name": "search"}]}],
    )
    tool_names = [t["name"] for t in payload["tools"]]
    assert tool_names == ["nucleus_relay", "search"]


def test_flatten_mcp_tools_missing_input_schema_defaults():
    """Per op-assistant translation: missing input_schema → empty object."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[{"name": "x", "tools": [{"name": "t"}]}],
    )
    assert payload["tools"][0]["input_schema"] == {
        "type": "object", "properties": {},
    }


def test_flatten_mcp_tools_missing_description_defaults_to_empty():
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[{"name": "x", "tools": [{"name": "t"}]}],
    )
    assert payload["tools"][0]["description"] == ""


def test_flatten_mcp_tools_defensive_skip_malformed():
    """Defensive: non-dict servers / non-dict tools / missing name → skipped."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[
            "not a dict",  # skipped
            {"name": "ok", "tools": [
                {"name": "good"},
                "not a dict",  # skipped
                {"description": "no name"},  # skipped
                {"name": ""},  # skipped (empty name)
                {"name": 42},  # skipped (non-string name)
            ]},
            {"name": "no_tools_key"},  # skipped (no tools)
            {"name": "bad_tools", "tools": "not a list"},  # skipped
        ],
    )
    tool_names = [t["name"] for t in payload["tools"]]
    # "good" from malformed-skip path + injected nucleus_relay
    assert tool_names == ["good", "nucleus_relay"]


def test_only_injected_nucleus_relay_when_no_mcp_and_no_caller_tools():
    """Plan B: nucleus_relay ALWAYS injected even with no other tools."""
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        mcp_servers=[],
    )
    assert "mcp_servers" not in payload
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["name"] == "nucleus_relay"


def test_only_caller_tools_when_mcp_servers_none():
    payload = aw.compose_wake_payload(
        wake_instruction="wake",
        tools=[{"name": "nucleus_relay"}],
    )
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["name"] == "nucleus_relay"


def test_flatten_helper_direct_with_55_simulated_tools():
    """Per op-assistant empirical: 55 MCP tools across multiple servers
    all flatten correctly. Direct test of _flatten_mcp_tools helper."""
    mcp_servers = []
    for srv_idx in range(11):  # 11 servers x 5 tools = 55
        mcp_servers.append({
            "name": f"server_{srv_idx}",
            "tools": [
                {"name": f"tool_{srv_idx}_{t}", "description": f"d{t}"}
                for t in range(5)
            ],
        })
    flat = aw._flatten_mcp_tools(mcp_servers)
    assert len(flat) == 55
    assert all("name" in t for t in flat)
    assert all("input_schema" in t for t in flat)


def test_compose_payload_custom_model_and_max_tokens():
    payload = aw.compose_wake_payload(
        wake_instruction="x",
        model="claude-opus-4-7",
        max_tokens=8192,
    )
    assert payload["model"] == "claude-opus-4-7"
    assert payload["max_tokens"] == 8192


# ── post_inference ─────────────────────────────────────────────────


def test_post_inference_posts_to_v1_messages_beta_true():
    mock = _capture_post()
    payload = {"model": "m", "max_tokens": 100, "messages": [{"role": "user", "content": "x"}]}
    result = aw.post_inference(payload, bearer="STUB-OAT")
    url = mock.call_args.args[0] if mock.call_args.args else mock.call_args.kwargs["url"]
    assert url == "https://api.anthropic.com/v1/messages?beta=true"
    headers = mock.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer STUB-OAT"
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["Content-Type"] == "application/json"
    assert mock.call_args.kwargs["json"] == payload
    assert result["stop_reason"] == "end_turn"


def test_post_inference_raises_on_non_2xx():
    aw._curl_requests.post = MagicMock(return_value=_ok_resp({}, status=429))
    payload = {"messages": [{"role": "user", "content": "x"}]}
    with pytest.raises(aw.AutonomousWakeError):
        aw.post_inference(payload, bearer="STUB-OAT")


def test_post_inference_raises_on_missing_bearer():
    payload = {"messages": [{"role": "user", "content": "x"}]}
    with pytest.raises(aw.AutonomousWakeError):
        aw.post_inference(payload, bearer="")


def test_post_inference_raises_on_missing_messages():
    with pytest.raises(aw.AutonomousWakeError):
        aw.post_inference({}, bearer="STUB-OAT")


def test_post_inference_raises_on_transport_failure():
    aw._curl_requests.post = MagicMock(side_effect=Exception("dns fail"))
    payload = {"messages": [{"role": "user", "content": "x"}]}
    with pytest.raises(aw.AutonomousWakeError):
        aw.post_inference(payload, bearer="STUB-OAT", session_id="cse_x")


# ── extract_tool_use_blocks ─────────────────────────────────────────────


def test_extract_tool_use_blocks_filters_correctly():
    response = {
        "content": [
            {"type": "text", "text": "thinking..."},
            {"type": "tool_use", "id": "t1", "name": "nucleus_relay",
             "input": {"to": "main", "subject": "ack"}},
            {"type": "text", "text": "more thinking"},
            {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "x"}},
        ],
    }
    blocks = aw.extract_tool_use_blocks(response)
    assert len(blocks) == 2
    assert blocks[0]["name"] == "nucleus_relay"
    assert blocks[1]["name"] == "Read"


def test_extract_tool_use_blocks_empty_content():
    assert aw.extract_tool_use_blocks({"content": []}) == []
    assert aw.extract_tool_use_blocks({}) == []
    assert aw.extract_tool_use_blocks({"content": "not-a-list"}) == []


# ── _get_session_events helper resilience ───────────────────────────────


def test_get_session_events_returns_empty_on_limit_zero():
    assert aw._get_session_events("cse_x", bearer="b", limit=0) == []


def test_get_session_events_returns_empty_on_missing_session_or_bearer():
    assert aw._get_session_events("", bearer="b", limit=10) == []
    assert aw._get_session_events("cse_x", bearer="", limit=10) == []


def test_get_session_events_returns_empty_on_transport_failure():
    """History fetch must NOT abort the wake — return [] gracefully."""
    aw._curl_requests.get = MagicMock(side_effect=Exception("timeout"))
    assert aw._get_session_events("cse_x", bearer="b", limit=10) == []


def test_get_session_events_returns_empty_on_non_2xx():
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({}, status=404))
    assert aw._get_session_events("cse_x", bearer="b", limit=10) == []


def test_get_session_events_parses_events_key():
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({
        "events": [{"role": "user", "content": "hi"}],
    }))
    out = aw._get_session_events("cse_x", bearer="b", limit=10)
    assert out == [{"role": "user", "content": "hi"}]


def test_get_session_events_parses_data_key_fallback():
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({
        "data": [{"role": "assistant", "content": "ok"}],
    }))
    out = aw._get_session_events("cse_x", bearer="b", limit=10)
    assert out == [{"role": "assistant", "content": "ok"}]


def test_get_session_events_parses_top_level_list():
    aw._curl_requests.get = MagicMock(return_value=_ok_resp(
        [{"role": "user", "content": "a"}],
    ))
    out = aw._get_session_events("cse_x", bearer="b", limit=10)
    assert out == [{"role": "user", "content": "a"}]


def test_get_session_events_url_shape_includes_limit():
    mock = _capture_get({"events": []})
    aw._get_session_events("cse_abc", bearer="b", limit=25)
    url = mock.call_args.args[0] if mock.call_args.args else mock.call_args.kwargs["url"]
    assert url == "https://api.anthropic.com/v1/sessions/cse_abc/events?limit=25"


# ── autonomous_wake_from_relay orchestrator ─────────────────────────────


def test_autonomous_wake_from_relay_returns_ok_bundle():
    """End-to-end: history + discovery → payload → POST → response."""
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({"events": [
        {"role": "user", "content": "earlier turn"},
    ]}))
    post_mock = _capture_post({
        "id": "msg_wake_ok",
        "content": [
            {"type": "text", "text": "ack relay"},
            {"type": "tool_use", "id": "t1", "name": "nucleus_relay",
             "input": {"to": "main", "subject": "forward"}},
        ],
        "stop_reason": "tool_use",
    })

    result = aw.autonomous_wake_from_relay(
        role="cc_tb",
        session_id="cse_test_session_id_long",
        relay_subject="[TEST] wake me",
        relay_body="please do X",
        bearer="STUB-OAT",
        org_uuid="903554b9-org-uuid",
        history_limit=10,
        discovery_context={
            "system_prompt": "You are cc-tb autonomous.",
            "tools": [{"name": "nucleus_relay"}],
            "mcp_servers": [{"url": "https://nucleus", "type": "url"}],
        },
    )

    assert result["ok"] is True
    assert result["response"]["stop_reason"] == "tool_use"
    assert len(result["tool_use_blocks"]) == 1
    assert result["tool_use_blocks"][0]["name"] == "nucleus_relay"
    # wake_instruction echoed for caller observability
    assert "cc_tb" in result["wake_instruction"]
    assert "[TEST] wake me" in result["wake_instruction"]
    assert "please do X" in result["wake_instruction"]

    # Verify payload composition wired discovery context
    sent_payload = post_mock.call_args.kwargs["json"]
    assert sent_payload["system"] == "You are cc-tb autonomous."
    assert sent_payload["tools"][0]["name"] == "nucleus_relay"
    # 1 history + 1 new user turn = 2 messages
    assert len(sent_payload["messages"]) == 2
    assert sent_payload["messages"][-1]["role"] == "user"


def test_autonomous_wake_from_relay_raises_on_missing_args():
    with pytest.raises(aw.AutonomousWakeError):
        aw.autonomous_wake_from_relay(
            role="", session_id="cse_x", relay_subject="s",
            relay_body="b", bearer="STUB",
        )
    with pytest.raises(aw.AutonomousWakeError):
        aw.autonomous_wake_from_relay(
            role="cc_tb", session_id="", relay_subject="s",
            relay_body="b", bearer="STUB",
        )
    with pytest.raises(aw.AutonomousWakeError):
        aw.autonomous_wake_from_relay(
            role="cc_tb", session_id="cse_x", relay_subject="s",
            relay_body="b", bearer="",
        )


def test_autonomous_wake_from_relay_raises_when_subject_and_body_empty():
    with pytest.raises(aw.AutonomousWakeError):
        aw.autonomous_wake_from_relay(
            role="cc_tb", session_id="cse_x",
            relay_subject="", relay_body="",
            bearer="STUB",
        )


def test_autonomous_wake_from_relay_survives_history_fetch_failure():
    """History fetch failure → still fires inference (graceful degrade)."""
    aw._curl_requests.get = MagicMock(side_effect=Exception("timeout"))
    post_mock = _capture_post()
    result = aw.autonomous_wake_from_relay(
        role="cc_tb", session_id="cse_x",
        relay_subject="s", relay_body="b",
        bearer="STUB-OAT", history_limit=10,
    )
    assert result["ok"] is True
    # No history loaded → 1 message (just the wake user turn)
    sent_payload = post_mock.call_args.kwargs["json"]
    assert len(sent_payload["messages"]) == 1


def test_autonomous_wake_from_relay_skips_history_when_discovery_context_absent():
    post_mock = _capture_post()
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({"events": []}))
    result = aw.autonomous_wake_from_relay(
        role="cc_tb", session_id="cse_x",
        relay_subject="s", relay_body="b",
        bearer="STUB-OAT", history_limit=0,  # explicit skip
    )
    # discovery_context omitted → no system/mcp_servers in payload.
    # Plan B: tools[] still present (injected nucleus_relay).
    sent_payload = post_mock.call_args.kwargs["json"]
    assert "system" not in sent_payload
    assert "mcp_servers" not in sent_payload
    assert sent_payload["tools"] == [dict(aw.NUCLEUS_RELAY_TOOL)]
    assert result["ok"] is True


# ── Pseudonymity discipline ─────────────────────────────────────────────


def test_bearer_never_logged_on_inference_success(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.autonomous_wake")
    SECRET_BEARER = "STUB-OAT-INFERENCE-secret-do-not-leak-xyz"
    _capture_post()
    payload = {"messages": [{"role": "user", "content": "x"}]}
    aw.post_inference(payload, bearer=SECRET_BEARER, session_id="cse_xyz")
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_bearer_never_logged_on_inference_failure(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.autonomous_wake")
    SECRET_BEARER = "STUB-OAT-FAIL-leak-check"
    aw._curl_requests.post = MagicMock(side_effect=Exception("network"))
    with pytest.raises(aw.AutonomousWakeError):
        aw.post_inference(
            {"messages": [{"role": "user", "content": "x"}]},
            bearer=SECRET_BEARER, session_id="cse_x",
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_relay_body_content_never_logged(caplog):
    """User content from relay body MUST NOT appear in any log record."""
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.autonomous_wake")
    SECRET_BODY = "private operator content should not leak ABC-XYZ-123"
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({"events": []}))
    _capture_post()
    aw.autonomous_wake_from_relay(
        role="cc_tb", session_id="cse_xyz",
        relay_subject="ok", relay_body=SECRET_BODY,
        bearer="STUB-OAT",
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BODY not in all_text


def test_session_id_truncated_in_logs(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.autonomous_wake")
    long_cse = "cse_THISisAlongSessionId0123456789abc"
    aw._curl_requests.get = MagicMock(return_value=_ok_resp({"events": []}))
    _capture_post()
    aw.autonomous_wake_from_relay(
        role="cc_tb", session_id=long_cse,
        relay_subject="s", relay_body="b",
        bearer="STUB-OAT",
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert long_cse[:12] in all_text
    assert long_cse not in all_text


# ── Module constants ────────────────────────────────────────────────────


def test_api_anthropic_host_constant():
    assert aw._API_ANTHROPIC == "https://api.anthropic.com"


def test_messages_url_includes_beta_true():
    """Per spec line 149: POST /v1/messages?beta=true."""
    assert aw._MESSAGES_URL == "https://api.anthropic.com/v1/messages?beta=true"


def test_anthropic_version_header():
    assert aw._ANTHROPIC_VERSION == "2023-06-01"


def test_log_id_max_matches_pr_499_convention():
    assert aw._LOG_ID_MAX == 12


def test_all_exported():
    expected = {
        "AutonomousWakeError",
        "WakeAuthError",
        "compose_wake_payload",
        "post_inference",
        "extract_tool_use_blocks",
        "autonomous_wake_from_relay",
    }
    assert set(aw.__all__) == expected


def test_no_destructive_http_verbs_used():
    """Layer 5 ships POST + GET only — no PUT/DELETE/PATCH anywhere."""
    import inspect
    src = inspect.getsource(aw)
    code_lines = []
    in_string = False
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_string = not in_string
            continue
        if not in_string and not stripped.startswith("#"):
            code_lines.append(line)
    code = "\n".join(code_lines)
    assert "_curl_requests.put" not in code
    assert "_curl_requests.delete" not in code
    assert "_curl_requests.patch" not in code


# ── 401-refresh retry (GAP-1 / op-assistant Task #66) ───────────────────


def _resp_401():
    return _ok_resp({}, status=401)


def _wake(**overrides):
    kwargs = dict(
        role="cc_tb", session_id="cse_x",
        relay_subject="s", relay_body="b",
        bearer="STALE-OAT", history_limit=0,
    )
    kwargs.update(overrides)
    return aw.autonomous_wake_from_relay(**kwargs)


def test_wake_auth_error_is_autonomous_wake_error():
    """Backward compat: callers catching AutonomousWakeError still catch 401s."""
    assert issubclass(aw.WakeAuthError, aw.AutonomousWakeError)


def test_post_inference_raises_wake_auth_error_on_401():
    aw._curl_requests.post = MagicMock(return_value=_resp_401())
    payload = {"messages": [{"role": "user", "content": "x"}]}
    with pytest.raises(aw.WakeAuthError):
        aw.post_inference(payload, bearer="STALE-OAT")


def test_refreshed_bearer_calls_force_refresh(monkeypatch):
    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    mock = MagicMock(return_value="sk-ant-oat01-fresh")
    monkeypatch.setattr(oauth_exchange, "get_access_token", mock)
    assert aw._refreshed_bearer("cc_tb") == "sk-ant-oat01-fresh"
    mock.assert_called_once_with("cc_tb", force_refresh=True)


def test_refreshed_bearer_returns_none_on_exchange_failure(monkeypatch):
    import mcp_server_nucleus.oauth.exchange as oauth_exchange
    monkeypatch.setattr(
        oauth_exchange, "get_access_token",
        MagicMock(side_effect=RuntimeError("boom")),
    )
    assert aw._refreshed_bearer("cc_tb") is None


def test_wake_retries_once_with_refreshed_bearer_on_401(monkeypatch):
    ok = _ok_resp({
        "id": "msg_ok",
        "content": [{"type": "text", "text": "ack"}],
        "stop_reason": "end_turn",
    })
    post_mock = MagicMock(side_effect=[_resp_401(), ok])
    aw._curl_requests.post = post_mock
    refresh = MagicMock(return_value="FRESH-OAT")
    monkeypatch.setattr(aw, "_refreshed_bearer", refresh)

    result = _wake()

    assert result["ok"] is True
    assert post_mock.call_count == 2
    refresh.assert_called_once_with("cc_tb")
    retry_headers = post_mock.call_args_list[1].kwargs["headers"]
    assert retry_headers["Authorization"] == "Bearer FRESH-OAT"


def test_wake_propagates_401_when_refresh_fails(monkeypatch):
    post_mock = MagicMock(return_value=_resp_401())
    aw._curl_requests.post = post_mock
    monkeypatch.setattr(aw, "_refreshed_bearer", MagicMock(return_value=None))
    with pytest.raises(aw.WakeAuthError):
        _wake()
    assert post_mock.call_count == 1


def test_wake_propagates_401_when_refreshed_bearer_unchanged(monkeypatch):
    """Same token back from cache ⇒ retry would 401 identically; skip it."""
    post_mock = MagicMock(return_value=_resp_401())
    aw._curl_requests.post = post_mock
    monkeypatch.setattr(
        aw, "_refreshed_bearer", MagicMock(return_value="STALE-OAT"),
    )
    with pytest.raises(aw.WakeAuthError):
        _wake()
    assert post_mock.call_count == 1


def test_wake_second_401_not_retried_again(monkeypatch):
    """Exactly one refresh + one retry — no refresh loop."""
    post_mock = MagicMock(side_effect=[_resp_401(), _resp_401()])
    aw._curl_requests.post = post_mock
    refresh = MagicMock(return_value="FRESH-OAT")
    monkeypatch.setattr(aw, "_refreshed_bearer", refresh)
    with pytest.raises(aw.WakeAuthError):
        _wake()
    assert post_mock.call_count == 2
    assert refresh.call_count == 1


def test_wake_refetches_history_with_fresh_bearer_on_retry(monkeypatch):
    """Stale bearer empties the history GET (non-2xx → []); the retry
    must re-fetch with the fresh bearer so the wake keeps continuity."""
    get_mock = MagicMock(side_effect=[
        _resp_401(),
        _ok_resp({"events": [{"role": "user", "content": "earlier"}]}),
    ])
    aw._curl_requests.get = get_mock
    ok = _ok_resp({"id": "m", "content": [], "stop_reason": "end_turn"})
    post_mock = MagicMock(side_effect=[_resp_401(), ok])
    aw._curl_requests.post = post_mock
    monkeypatch.setattr(
        aw, "_refreshed_bearer", MagicMock(return_value="FRESH-OAT"),
    )

    result = _wake(history_limit=10)

    assert result["ok"] is True
    assert get_mock.call_count == 2
    second_get_headers = get_mock.call_args_list[1].kwargs["headers"]
    assert second_get_headers["Authorization"] == "Bearer FRESH-OAT"
    # Retry payload = 1 re-fetched history turn + 1 wake user turn
    retry_payload = post_mock.call_args_list[1].kwargs["json"]
    assert len(retry_payload["messages"]) == 2


def test_wake_non_401_rejection_does_not_refresh(monkeypatch):
    aw._curl_requests.post = MagicMock(return_value=_ok_resp({}, status=429))
    refresh = MagicMock(return_value="FRESH-OAT")
    monkeypatch.setattr(aw, "_refreshed_bearer", refresh)
    with pytest.raises(aw.AutonomousWakeError):
        _wake()
    refresh.assert_not_called()


def test_wake_401_refresh_never_logs_bearer(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.autonomous_wake")
    ok = _ok_resp({"id": "m", "content": [], "stop_reason": "end_turn"})
    aw._curl_requests.post = MagicMock(side_effect=[_resp_401(), ok])
    monkeypatch.setattr(
        aw, "_refreshed_bearer", MagicMock(return_value="FRESH-OAT"),
    )
    _wake()
    assert "FRESH-OAT" not in caplog.text
    assert "STALE-OAT" not in caplog.text
