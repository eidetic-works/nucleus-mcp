"""Tests for runtime/relay_transport.py — PR-A v0.1 FS/HTTP transport switch.

Per spec at .brain/plans/2026-06-06_relay_as_service_v0_1.md:
- FS-mode regression: existing tests stay GREEN
- HTTP-mode: mock urllib.request.urlopen returning canned (status, body)
- Round-trip: post → read → mark_seen → read returns empty
- Failure paths: 401 / 403 / 404 / 5xx / connection error → empty / sent:False
- Canonical resolution at boundary: read_inbox("tb") → GET /relay/cc_tb
- Non-dict body edge case (PR #485 CRACK 5 mirror) at HTTP layer
"""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import relay_transport
from mcp_server_nucleus.runtime.relay_transport import (
    is_http_mode,
    mark_seen,
    post_relay,
    read_inbox,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _mock_urlopen_response(status: int, body: dict | str | None, headers: dict | None = None):
    """Build a MagicMock for urllib.request.urlopen context manager.

    Returns object that supports .status, .read(), .headers iteration.
    """
    mock_resp = MagicMock()
    mock_resp.status = status
    if isinstance(body, dict):
        mock_resp.read.return_value = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        mock_resp.read.return_value = body.encode("utf-8")
    else:
        mock_resp.read.return_value = b""
    # urllib's response.headers is httplib.HTTPMessage; we just need .items()
    mock_resp.headers = (headers or {}).items() if headers else {}.items()
    # Replace with a dict-like that supports .items() AND key indexing
    class _Hdrs(dict):
        def items(self_inner):
            return super().items()
    mock_resp.headers = _Hdrs(headers or {})
    # Context manager protocol
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = lambda s, *a: None
    return mock_resp


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Each test starts with NUCLEUS_RELAY_URL and BEARER unset."""
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)


@pytest.fixture
def http_env(monkeypatch):
    """Activate HTTP mode with valid URL + bearer."""
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.example.com")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "test-bearer-token-xyz")


# ── is_http_mode ─────────────────────────────────────────────────────────


def test_is_http_mode_false_when_url_unset():
    assert is_http_mode() is False


def test_is_http_mode_true_when_url_set(monkeypatch):
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://x.example/relay")
    assert is_http_mode() is True


def test_is_http_mode_false_when_url_blank(monkeypatch):
    """Empty string env var → FS mode (whitespace-only also FS)."""
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "   ")
    assert is_http_mode() is False


# ── _bearer_or_raise ─────────────────────────────────────────────────────


def test_bearer_or_raise_returns_token_when_present(http_env):
    assert relay_transport._bearer_or_raise() == "test-bearer-token-xyz"


def test_bearer_or_raise_fails_loud_when_url_set_no_bearer(monkeypatch):
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.example.com")
    # NUCLEUS_RELAY_BEARER intentionally missing
    with pytest.raises(RuntimeError, match="NUCLEUS_RELAY_BEARER missing"):
        relay_transport._bearer_or_raise()


# ── FS-mode no-op behaviour ──────────────────────────────────────────────


def test_read_inbox_fs_mode_returns_empty_list():
    assert read_inbox("tb") == []


def test_post_relay_fs_mode_returns_fs_marker_shape():
    result = post_relay({"to": "main", "subject": "x"})
    assert result == {
        "sent": False,
        "error": "fs_mode_caller_should_route_to_relay_ops",
    }


def test_mark_seen_fs_mode_returns_fs_marker_shape():
    result = mark_seen("tb", ["id-1"])
    assert result == {
        "acked": 0,
        "failed": 0,
        "error": "fs_mode_caller_should_route_to_relay_ops",
    }


def test_mark_seen_empty_list_short_circuit(http_env):
    """Even in HTTP mode, empty message_ids → short-circuit without HTTP call."""
    assert mark_seen("tb", []) == {"acked": 0, "failed": 0}


# ── read_inbox HTTP-mode ─────────────────────────────────────────────────


def test_read_inbox_http_mode_happy_path(http_env):
    """200 with messages array → list returned."""
    body = {"messages": [{"id": "m1", "subject": "hello"}, {"id": "m2"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = read_inbox("tb")
    assert result == [{"id": "m1", "subject": "hello"}, {"id": "m2"}]


def test_read_inbox_http_mode_canonical_resolution_tb_to_cc_tb(http_env):
    """role='tb' should route through resolve_canonical_inbox_name to cc_tb."""
    body = {"messages": []}
    captured = {}

    def _capture(req, **kwargs):
        captured["url"] = req.full_url
        return _mock_urlopen_response(200, body)

    with patch("urllib.request.urlopen", side_effect=_capture):
        read_inbox("tb")

    assert "/relay/cc_tb" in captured["url"]


def test_read_inbox_http_mode_query_string_unread_only_and_limit(http_env):
    body = {"messages": []}
    captured = {}

    def _capture(req, **kwargs):
        captured["url"] = req.full_url
        return _mock_urlopen_response(200, body)

    with patch("urllib.request.urlopen", side_effect=_capture):
        read_inbox("tb", unread_only=False, limit=25)

    assert "unread_only=false" in captured["url"]
    assert "limit=25" in captured["url"]


def test_read_inbox_http_mode_401_returns_empty(http_env):
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        result = read_inbox("tb")
    assert result == []


def test_read_inbox_http_mode_403_returns_empty(http_env):
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb",
        code=403, msg="Forbidden", hdrs=None, fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        assert read_inbox("tb") == []


def test_read_inbox_http_mode_404_returns_empty(http_env):
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb",
        code=404, msg="Not Found", hdrs=None, fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        assert read_inbox("tb") == []


def test_read_inbox_http_mode_500_returns_empty(http_env):
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb",
        code=500, msg="Internal Error", hdrs=None, fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        assert read_inbox("tb") == []


def test_read_inbox_http_mode_connection_refused_returns_empty(http_env):
    import urllib.error
    err = urllib.error.URLError(reason="Connection refused")
    with patch("urllib.request.urlopen", side_effect=err):
        assert read_inbox("tb") == []


def test_read_inbox_http_mode_timeout_returns_empty(http_env):
    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        assert read_inbox("tb") == []


def test_read_inbox_http_mode_rate_limit_exhausted_keeps_messages(http_env):
    """Truth-in-signaling: a SUCCESSFUL page with the budget hitting 0 keeps
    its messages and flags rate_limited=True — previously the good page was
    discarded, making backoff indistinguishable from an empty inbox."""
    body = {"messages": [{"id": "m1"}]}
    headers = {"X-RateLimit-Remaining": "0"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body, headers)):
        result = read_inbox("tb")
    assert result == [{"id": "m1"}], "successful page must not be discarded"
    assert result.rate_limited is True
    assert result.transport_error is False


def test_read_inbox_http_mode_non_dict_response_body_returns_empty(http_env):
    """PR #485 CRACK 5 class-wide mirror: list/str/null body → empty list."""
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, "not a dict")):
        assert read_inbox("tb") == []


# ── post_relay HTTP-mode ─────────────────────────────────────────────────


def test_post_relay_http_mode_happy_path(http_env):
    """Server returns HTTP 202 Accepted per relay_route.py POST /relay/{recipient}.

    Pre-2026-06-07 this test mocked 201 which passed against the narrow
    (200, 201) status check while real server traffic returned 202 and the
    wrapper reported sent=False for messages that were actually persisted.
    """
    body = {"id": "msg-abc-123", "stored": True}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = post_relay({"id": "msg-abc-123", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "msg-abc-123"}


def test_post_relay_http_mode_canonical_resolution_at_to_role(http_env):
    """payload['to']='tb' → POST /relay/cc_tb."""
    body = {"id": "m"}
    captured = {}
    def _capture(req, **kwargs):
        captured["url"] = req.full_url
        return _mock_urlopen_response(202, body)
    with patch("urllib.request.urlopen", side_effect=_capture):
        post_relay({"to": "tb", "subject": "x"})
    assert "/relay/cc_tb" in captured["url"]


def test_post_relay_http_mode_idempotency_key_header_from_id(http_env):
    body = {"id": "id-from-server"}
    captured = {}
    def _capture(req, **kwargs):
        captured["headers"] = dict(req.headers)
        return _mock_urlopen_response(202, body)
    with patch("urllib.request.urlopen", side_effect=_capture):
        post_relay({"id": "my-idempotency-key", "to": "main"})
    # urllib uppercases header keys to Title-Case
    assert captured["headers"].get("Idempotency-key") == "my-idempotency-key"


def test_post_relay_http_mode_sender_session_id_header(http_env):
    body = {"id": "m"}
    captured = {}
    def _capture(req, **kwargs):
        captured["headers"] = dict(req.headers)
        return _mock_urlopen_response(202, body)
    with patch("urllib.request.urlopen", side_effect=_capture):
        post_relay({"to": "main", "from_session_id": "sess-abc"})
    assert captured["headers"].get("X-sender-session-id") == "sess-abc"


def test_post_relay_http_mode_200_returns_sent_true(http_env):
    """2xx contract: 200 OK also counts as success (back-compat with prior code path)."""
    body = {"id": "msg-200"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = post_relay({"id": "msg-200", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "msg-200"}


def test_post_relay_http_mode_201_returns_sent_true(http_env):
    """2xx contract: 201 Created also counts as success (back-compat with prior code path)."""
    body = {"id": "msg-201"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(201, body)):
        result = post_relay({"id": "msg-201", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "msg-201"}


def test_post_relay_http_mode_204_with_body_returns_sent_true(http_env):
    """2xx contract upper bound: 204 No Content also accepted when body is dict."""
    body = {"id": "msg-204"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(204, body)):
        result = post_relay({"id": "msg-204", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "msg-204"}


def test_post_relay_http_mode_300_returns_sent_false(http_env):
    """2xx contract lower bound: 300 redirect class falls through to sent=False."""
    body = {"id": "msg-300"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(300, body)):
        result = post_relay({"id": "msg-300", "to": "main", "subject": "x"})
    assert result == {"sent": False, "error": 300}


def test_post_relay_http_mode_missing_to_field(http_env):
    """payload without 'to' → no HTTP call, marker error."""
    result = post_relay({"subject": "no recipient"})
    assert result == {"sent": False, "error": "missing_to_field"}


def test_post_relay_http_mode_500_returns_sent_false(http_env):
    import urllib.error
    err = urllib.error.HTTPError(
        url="x", code=500, msg="oops", hdrs=None, fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        result = post_relay({"to": "main"})
    assert result == {"sent": False, "error": 500}


def test_post_relay_http_mode_connection_error(http_env):
    import urllib.error
    err = urllib.error.URLError(reason="DNS")
    with patch("urllib.request.urlopen", side_effect=err):
        result = post_relay({"to": "main"})
    assert result == {"sent": False, "error": "transport_failure"}


def test_post_relay_http_mode_extracts_message_id_field(http_env):
    """Task #62 root cause: the live server's 202 echoes the stored id as
    "message_id" (relay_route.py response contract), not "id". Old code read
    only "id" and returned "" for callers that supplied no client id
    (the Dispatch 'no message_id came back' symptom)."""
    body = {"sent": True, "message_id": "relay_20260610_140000_aabbccdd"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = post_relay({"to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "relay_20260610_140000_aabbccdd"}


def test_post_relay_http_mode_message_id_wins_over_id(http_env):
    """When both fields are present, server-canonical message_id wins."""
    body = {"message_id": "server-canonical", "id": "legacy-alias"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = post_relay({"to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "server-canonical"}


def test_post_relay_http_mode_blank_ids_fall_back_to_idempotency_key(http_env):
    """Blank/empty id fields degrade to the client idempotency key, never ''."""
    body = {"message_id": "", "id": ""}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = post_relay({"id": "client-key-7", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "client-key-7"}


# ── mark_seen HTTP-mode ─────────────────────────────────────────────────


def test_mark_seen_http_mode_happy_path(http_env):
    body = {"acked": 2, "failed": 0}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = mark_seen("tb", ["id-1", "id-2"])
    assert result == {"acked": 2, "failed": 0}


def test_mark_seen_http_mode_canonical_resolution(http_env):
    body = {"acked": 1, "failed": 0}
    captured = {}
    def _capture(req, **kwargs):
        captured["url"] = req.full_url
        return _mock_urlopen_response(200, body)
    with patch("urllib.request.urlopen", side_effect=_capture):
        mark_seen("tb", ["id-1"])
    assert "/relay/cc_tb/ack" in captured["url"]


def test_mark_seen_http_mode_body_contains_message_ids(http_env):
    body = {"acked": 1, "failed": 0}
    captured = {}
    def _capture(req, **kwargs):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _mock_urlopen_response(200, body)
    with patch("urllib.request.urlopen", side_effect=_capture):
        mark_seen("tb", ["id-1", "id-2"])
    assert captured["body"] == {"message_ids": ["id-1", "id-2"]}


def test_mark_seen_http_mode_500_returns_failed(http_env):
    import urllib.error
    err = urllib.error.HTTPError(url="x", code=500, msg="oops", hdrs=None, fp=io.BytesIO(b""))
    with patch("urllib.request.urlopen", side_effect=err):
        result = mark_seen("tb", ["id-1", "id-2"])
    assert result == {"acked": 0, "failed": 2, "error": 500}


def test_mark_seen_http_mode_connection_error(http_env):
    import urllib.error
    err = urllib.error.URLError(reason="x")
    with patch("urllib.request.urlopen", side_effect=err):
        result = mark_seen("tb", ["id-1"])
    assert result == {"acked": 0, "failed": 1, "error": "transport_failure"}


def test_mark_seen_http_mode_202_returns_acked(http_env):
    """2xx contract: 202 Accepted also counts as success (server currently 200)."""
    body = {"acked": 1, "failed": 0}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = mark_seen("tb", ["id-1"])
    assert result == {"acked": 1, "failed": 0}


def test_mark_seen_http_mode_204_with_body_returns_acked(http_env):
    """2xx contract: 204 No Content (with body dict) also accepted."""
    body = {"acked": 1, "failed": 0}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(204, body)):
        result = mark_seen("tb", ["id-1"])
    assert result == {"acked": 1, "failed": 0}


def test_read_inbox_http_mode_201_returns_messages(http_env):
    """2xx contract: 201 also returns messages (server currently 200)."""
    body = {"messages": [{"id": "m1"}, {"id": "m2"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(201, body)):
        result = read_inbox("tb")
    assert result == [{"id": "m1"}, {"id": "m2"}]


def test_read_inbox_http_mode_202_returns_messages(http_env):
    """2xx contract: 202 also returns messages."""
    body = {"messages": [{"id": "m1"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = read_inbox("tb")
    assert result == [{"id": "m1"}]


# ── Round-trip integration (HTTP-mode) ──────────────────────────────────


def test_round_trip_post_read_mark_seen_read_returns_empty(http_env):
    """post → read returns msg → mark_seen → read returns empty.

    Validates the full lifecycle from sender's perspective: write a relay,
    fetch unread, ack, fetch unread again returns nothing.
    """
    # Step 1: POST relay → server returns id
    post_resp = {"id": "round-trip-id-42", "stored": True}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(201, post_resp)):
        post_result = post_relay({"id": "round-trip-id-42", "to": "main", "subject": "rt"})
    assert post_result == {"sent": True, "id": "round-trip-id-42"}

    # Step 2: GET inbox returns the message
    read_resp = {"messages": [{"id": "round-trip-id-42", "subject": "rt"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, read_resp)):
        msgs = read_inbox("main")
    assert msgs == [{"id": "round-trip-id-42", "subject": "rt"}]

    # Step 3: mark_seen the message
    ack_resp = {"acked": 1, "failed": 0}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, ack_resp)):
        ack_result = mark_seen("main", ["round-trip-id-42"])
    assert ack_result == {"acked": 1, "failed": 0}

    # Step 4: GET inbox returns empty (server filtered ack'd msg)
    empty_resp = {"messages": []}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, empty_resp)):
        msgs_after = read_inbox("main")
    assert msgs_after == []


# ── InboxResult truth-in-signaling (v0.2 read_inbox bundle) ──────────────


def test_read_inbox_returns_inbox_result_backward_compatible_list(http_env):
    """InboxResult IS a list: isinstance checks, equality, and JSON
    serialization all behave exactly as before."""
    from mcp_server_nucleus.runtime.relay_transport import InboxResult

    body = {"messages": [{"id": "m1"}, {"id": "m2"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = read_inbox("tb")
    assert isinstance(result, list)
    assert isinstance(result, InboxResult)
    assert result == [{"id": "m1"}, {"id": "m2"}]
    assert json.loads(json.dumps(result)) == [{"id": "m1"}, {"id": "m2"}]


def test_read_inbox_surfaces_has_more_from_server(http_env):
    body = {"messages": [{"id": "m1"}], "count": 1, "has_more": True}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = read_inbox("tb")
    assert result.has_more is True


def test_read_inbox_omitted_has_more_is_false(http_env):
    """Older servers that don't send has_more → False, not an error."""
    body = {"messages": [{"id": "m1"}]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = read_inbox("tb")
    assert result.has_more is False


def test_read_inbox_transport_error_flag_on_500(http_env):
    import urllib.error

    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        result = read_inbox("tb")
    assert result == []
    assert result.transport_error is True
    assert result.rate_limited is False


def test_read_inbox_transport_error_flag_on_connection_refused(http_env):
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = read_inbox("tb")
    assert result == []
    assert result.transport_error is True


def test_read_inbox_429_sets_both_rate_limited_and_transport_error(http_env):
    """A hard 429 means the request itself was rejected: the caller got NO
    page (transport_error) AND should back off (rate_limited)."""
    import urllib.error

    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        result = read_inbox("tb")
    assert result == []
    assert result.rate_limited is True
    assert result.transport_error is True


def test_read_inbox_fs_mode_returns_inbox_result_with_clean_flags():
    from mcp_server_nucleus.runtime.relay_transport import InboxResult

    result = read_inbox("tb")
    assert isinstance(result, InboxResult)
    assert result == []
    assert result.has_more is False
    assert result.rate_limited is False
    assert result.transport_error is False


def test_read_inbox_truly_empty_inbox_has_all_flags_false(http_env):
    """The other half of truth-in-signaling: a genuinely empty inbox with
    budget remaining must be distinguishable from every failure mode."""
    body = {"messages": [], "count": 0, "has_more": False}
    headers = {"X-RateLimit-Remaining": "57"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body, headers)):
        result = read_inbox("tb")
    assert result == []
    assert result.has_more is False
    assert result.rate_limited is False
    assert result.transport_error is False


# ── get_status (v0.2 Seq-2: relay_status HTTP parity client) ────────────


def test_get_status_fs_mode_returns_fs_marker_shape():
    result = relay_transport.get_status("tb")
    assert result == {
        "ok": False,
        "error": "fs_mode_caller_should_route_to_relay_ops",
    }


def test_get_status_http_happy_path_merges_server_body(http_env):
    body = {"role": "cc_tb", "queue_depth": 4, "unread": 2}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(200, body)):
        result = relay_transport.get_status("cc_tb")
    assert result == {"ok": True, "role": "cc_tb", "queue_depth": 4, "unread": 2}


def test_get_status_canonical_resolution_at_role(http_env):
    """get_status('tb') → GET /relay/cc_tb/status (resolution at boundary)."""
    captured = {}

    def _capture(req, **kwargs):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return _mock_urlopen_response(200, {"queue_depth": 0, "unread": 0})

    with patch("urllib.request.urlopen", side_effect=_capture):
        relay_transport.get_status("tb")
    assert captured["url"].endswith("/relay/cc_tb/status")
    assert captured["method"] == "GET"


def test_get_status_http_error_surfaces_status_code(http_env):
    import urllib.error

    err = urllib.error.HTTPError(
        url="https://relay.example.com/relay/cc_tb/status",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=io.BytesIO(b""),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        result = relay_transport.get_status("tb")
    assert result == {"ok": False, "error": 500}


def test_get_status_connection_error_reports_transport_failure(http_env):
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = relay_transport.get_status("tb")
    assert result == {"ok": False, "error": "transport_failure"}


# ── post_relay client-side body cap (v0.2 Seq-3) ────────────────────────


def _boom_http_call(*args, **kwargs):
    raise AssertionError("_http_call must NOT fire for an over-cap payload")


def test_post_relay_over_cap_fails_fast_without_http_call(http_env, monkeypatch):
    """Over-cap payload is refused client-side BEFORE any HTTP traffic —
    no rate-budget slot is burned on a request the server would 413."""
    monkeypatch.setattr(relay_transport, "_http_call", _boom_http_call)
    payload = {"to": "main", "subject": "big", "body": {"blob": "x" * 70000}}
    result = post_relay(payload)
    assert result == {"sent": False, "error": "body_too_large"}


def test_post_relay_body_cap_env_override(http_env, monkeypatch):
    """NUCLEUS_RELAY_MAX_BODY lowers the cap in lockstep with the server's
    413 guard reading the same env var."""
    monkeypatch.setenv("NUCLEUS_RELAY_MAX_BODY", "100")
    monkeypatch.setattr(relay_transport, "_http_call", _boom_http_call)
    payload = {"to": "main", "subject": "small-but-over-100-bytes", "body": {"k": "y" * 200}}
    result = post_relay(payload)
    assert result == {"sent": False, "error": "body_too_large"}


def test_post_relay_under_cap_proceeds_to_http(http_env):
    body = {"id": "msg-under-cap"}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, body)):
        result = post_relay({"id": "msg-under-cap", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "msg-under-cap"}


def test_post_relay_body_cap_malformed_env_falls_back_to_default(http_env, monkeypatch):
    """Garbage in NUCLEUS_RELAY_MAX_BODY → default 65536 cap still enforced."""
    orig_http_call = relay_transport._http_call
    monkeypatch.setenv("NUCLEUS_RELAY_MAX_BODY", "not-a-number")
    monkeypatch.setattr(relay_transport, "_http_call", _boom_http_call)
    over_default = {"to": "main", "subject": "big", "body": {"blob": "z" * 70000}}
    assert post_relay(over_default) == {"sent": False, "error": "body_too_large"}
    # And an under-default payload still goes through (cap fell back, not 0).
    monkeypatch.setattr(relay_transport, "_http_call", orig_http_call)
    with patch("urllib.request.urlopen", return_value=_mock_urlopen_response(202, {"id": "m-ok"})):
        result = post_relay({"id": "m-ok", "to": "main", "subject": "x"})
    assert result == {"sent": True, "id": "m-ok"}
