"""Unit tests for tools._envelope.

Covers:
  - wrap() default shape
  - wrap() with NUCLEUS_ENVELOPE=off returns bare data
  - error_envelope() shape and optional fields
  - unwrap() idempotence on bare + wrapped payloads
  - is_envelope() detection
  - session_id + brain_id context propagation
  - schema_version constant stability
"""

from __future__ import annotations

import os

import pytest

from mcp_server_nucleus.tools import _envelope as env


@pytest.fixture(autouse=True)
def _reset_envelope_context(monkeypatch):
    """Ensure a clean env per test.

    Envelope defaults to OFF in production (see _envelope.is_enabled docstring).
    Tests that exercise the wrap path must explicitly set NUCLEUS_ENVELOPE=on.
    """
    monkeypatch.delenv("NUCLEUS_ENVELOPE", raising=False)
    monkeypatch.delenv("NUCLEUS_BRAIN_ID", raising=False)
    env.set_session_id(None)
    env.set_brain_id(None)
    yield
    env.set_session_id(None)
    env.set_brain_id(None)


@pytest.fixture
def envelope_on(monkeypatch):
    """Enable envelope wrapping for the duration of a test."""
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "on")


def test_wrap_default_shape_has_required_fields(envelope_on):
    e = env.wrap({"hello": "world"})
    assert e["ok"] is True
    assert e["data"] == {"hello": "world"}
    assert e["schema_version"] == env.ENVELOPE_SCHEMA_VERSION
    assert e["warnings"] == []
    assert e["error"] is None
    assert "brain_id" in e
    assert "session_id" in e


def test_wrap_disabled_returns_bare_data():
    # Default (unset) is OFF
    assert env.wrap({"x": 1}) == {"x": 1}
    assert env.wrap([1, 2, 3]) == [1, 2, 3]


def test_wrap_explicit_off_returns_bare_data(monkeypatch):
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "off")
    assert env.wrap({"x": 1}) == {"x": 1}
    # Any non-'on' value is off
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "true")
    assert env.wrap({"x": 1}) == {"x": 1}


def test_wrap_disabled_by_default():
    assert env.is_enabled() is False


def test_wrap_enabled_case_insensitive(monkeypatch):
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "ON")
    assert env.is_enabled() is True
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "On")
    assert env.is_enabled() is True


def test_wrap_respects_explicit_brain_id(envelope_on):
    e = env.wrap({"k": "v"}, brain_id="override-brain")
    assert e["brain_id"] == "override-brain"


def test_wrap_respects_explicit_session_id(envelope_on):
    e = env.wrap({"k": "v"}, session_id="sess-123")
    assert e["session_id"] == "sess-123"


def test_wrap_warnings_copied_not_referenced(envelope_on):
    warns = ["a", "b"]
    e = env.wrap(None, warnings=warns)
    warns.append("c")
    assert e["warnings"] == ["a", "b"]


def test_error_envelope_required_fields(envelope_on):
    e = env.error_envelope("transport_closed", recovery_hint="restart")
    assert e["ok"] is False
    assert e["data"] is None
    err = e["error"]
    assert err["error_type"] == "transport_closed"
    assert err["recovery_hint"] == "restart"


def test_error_envelope_optional_fields_present_when_set(envelope_on):
    e = env.error_envelope(
        "timeout",
        recovery_hint="retry",
        last_healthy_at="2026-04-18T12:00:00Z",
        pid=4512,
        inflight_writes=["engram:abc"],
        detail="handler exceeded 30s",
    )
    err = e["error"]
    assert err["last_healthy_at"] == "2026-04-18T12:00:00Z"
    assert err["pid"] == 4512
    assert err["inflight_writes"] == ["engram:abc"]
    assert err["detail"] == "handler exceeded 30s"


def test_error_envelope_optional_fields_absent_when_unset(envelope_on):
    e = env.error_envelope("handler_error")
    err = e["error"]
    assert "last_healthy_at" not in err
    assert "pid" not in err
    assert "inflight_writes" not in err
    assert "detail" not in err


def test_error_envelope_accepts_extra_fields(envelope_on):
    e = env.error_envelope("validation_error", field="name", got="int")
    err = e["error"]
    assert err["field"] == "name"
    assert err["got"] == "int"


def test_unwrap_extracts_data_from_envelope(envelope_on):
    e = env.wrap({"foo": 1})
    assert env.unwrap(e) == {"foo": 1}


def test_unwrap_idempotent_on_bare_payload():
    assert env.unwrap({"foo": 1}) == {"foo": 1}
    assert env.unwrap([1, 2, 3]) == [1, 2, 3]
    assert env.unwrap("hello") == "hello"
    assert env.unwrap(None) is None


def test_is_envelope_detection(envelope_on):
    assert env.is_envelope(env.wrap({"a": 1})) is True
    assert env.is_envelope({"ok": True, "data": {}}) is False  # missing schema_version
    assert env.is_envelope({"foo": "bar"}) is False
    assert env.is_envelope(None) is False
    assert env.is_envelope("string") is False


def test_brain_id_resolution_from_context(envelope_on):
    env.set_brain_id("nucleus-primary")
    e = env.wrap({"x": 1})
    assert e["brain_id"] == "nucleus-primary"


def test_brain_id_resolution_from_env(envelope_on, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_ID", "brain-from-env")
    e = env.wrap({"x": 1})
    assert e["brain_id"] == "brain-from-env"


def test_brain_id_defaults_to_unknown(envelope_on):
    e = env.wrap({"x": 1})
    assert e["brain_id"] == "unknown"


def test_context_brain_id_overrides_env(envelope_on, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_ID", "env-brain")
    env.set_brain_id("ctx-brain")
    e = env.wrap({"x": 1})
    assert e["brain_id"] == "ctx-brain"


def test_session_id_falls_back_to_process_id(envelope_on):
    e = env.wrap({"x": 1})
    # Process fallback has the proc- prefix
    assert e["session_id"].startswith("proc-")


def test_session_id_from_context(envelope_on):
    env.set_session_id("mcp-session-xyz")
    e = env.wrap({"x": 1})
    assert e["session_id"] == "mcp-session-xyz"


def test_schema_version_constant_is_string():
    assert isinstance(env.ENVELOPE_SCHEMA_VERSION, str)
    assert env.ENVELOPE_SCHEMA_VERSION == "2"


def test_wrap_ok_false_allowed(envelope_on):
    e = env.wrap({"partial": True}, ok=False)
    assert e["ok"] is False
    assert e["data"] == {"partial": True}


def test_error_envelope_disabled_returns_bare_none():
    """When envelope disabled (default), error_envelope returns bare None.

    Explicit contract: compat mode drops error structure. Callers in
    compat mode must raise or return sentinel values instead.
    """
    assert env.error_envelope("transport_closed") is None
