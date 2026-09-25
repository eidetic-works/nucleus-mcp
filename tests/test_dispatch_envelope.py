"""Integration tests: envelope wrapping through the dispatcher.

Validates that `tools/_dispatch.py::dispatch` and `async_dispatch`:
  - Return bare JSON strings when NUCLEUS_ENVELOPE is unset (default) —
    preserves the 1,327 existing tests.
  - Return envelope-wrapped JSON strings matching schemas/envelope.schema.json
    when NUCLEUS_ENVELOPE=on.
  - Correctly tag errors (validation_error, not_found, rate_limited,
    handler_error) in the error_type field.
  - Idempotent: handlers that already emit envelopes are not re-wrapped.
"""

from __future__ import annotations

import json

import pytest

from mcp_server_nucleus.tools import _dispatch, _envelope

jsonschema = pytest.importorskip(
    "jsonschema",
    reason="jsonschema not installed; envelope contract tests skipped",
)

from mcp_server_nucleus import schemas as schemas_pkg


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Reset rate limiter and envelope context per test."""
    _dispatch.get_dispatch_rate_limiter().reset()
    _dispatch.get_dispatch_telemetry().reset()
    monkeypatch.delenv("NUCLEUS_ENVELOPE", raising=False)
    monkeypatch.delenv("NUCLEUS_AMBIENT_HEALTH", raising=False)
    _envelope.set_session_id(None)
    _envelope.set_brain_id(None)
    yield


@pytest.fixture
def envelope_on(monkeypatch):
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "on")


@pytest.fixture(scope="module")
def validator():
    schema = schemas_pkg.load_schema("envelope")
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


# --------------------------------------------------------------------------
# Sample handlers
# --------------------------------------------------------------------------


def _ok_handler_dict(**kwargs):
    return {"result": "success", "echo": kwargs}


def _ok_handler_str(**kwargs):
    return json.dumps({"result": "ok"})


def _raises_value(**kwargs):
    raise ValueError("bad input")


def _raises_runtime(**kwargs):
    raise RuntimeError("boom")


async def _ok_async(**kwargs):
    return {"result": "async_ok"}


async def _raises_async(**kwargs):
    raise RuntimeError("async boom")


ROUTER = {
    "ok_dict": _ok_handler_dict,
    "ok_str": _ok_handler_str,
    "raises_value": _raises_value,
    "raises_runtime": _raises_runtime,
    "ok_async": _ok_async,
    "raises_async": _raises_async,
}


# --------------------------------------------------------------------------
# Default (envelope off): backward compat
# --------------------------------------------------------------------------


def test_dispatch_default_returns_bare_payload():
    result = _dispatch.dispatch("ok_dict", {}, ROUTER, "test_module")
    # No envelope structure — just the raw handler output (as JSON string)
    parsed = json.loads(result)
    assert parsed == {"result": "success", "echo": {}}
    assert "ok" not in parsed
    assert "brain_id" not in parsed
    assert "schema_version" not in parsed


def test_dispatch_default_unknown_action_bare_error():
    result = _dispatch.dispatch("nope", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    assert "error" in parsed
    # No envelope fields
    assert "ok" not in parsed
    assert "error_type" not in parsed  # bare, not structured-error


def test_dispatch_default_handler_exception_bare():
    result = _dispatch.dispatch("raises_runtime", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    assert "error" in parsed
    assert "ok" not in parsed


# --------------------------------------------------------------------------
# Envelope on: new contract
# --------------------------------------------------------------------------


def test_dispatch_envelope_wraps_success(envelope_on, validator):
    result = _dispatch.dispatch("ok_dict", {"k": "v"}, ROUTER, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["ok"] is True
    assert parsed["data"] == {"result": "success", "echo": {"k": "v"}}
    assert parsed["error"] is None
    assert parsed["brain_id"] == "unknown"  # no manifest loaded yet
    assert parsed["schema_version"] == "2"


def test_dispatch_envelope_validation_error(envelope_on, validator):
    result = _dispatch.dispatch("nope", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["ok"] is False
    assert parsed["error"]["error_type"] == "not_found"
    assert parsed["error"]["recovery_hint"]


def test_dispatch_envelope_handler_exception(envelope_on, validator):
    result = _dispatch.dispatch("raises_runtime", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["ok"] is False
    assert parsed["error"]["error_type"] == "handler_error"


def test_dispatch_envelope_idempotent_on_pre_wrapped(envelope_on):
    """Handler that returns a pre-wrapped envelope should pass through unchanged."""
    pre = _envelope.wrap({"inner": "payload"}, brain_id="test-brain")

    def _prewrap_handler(**kwargs):
        return json.dumps(pre)

    result = _dispatch.dispatch("pre", {}, {"pre": _prewrap_handler}, "test_module")
    parsed = json.loads(result)
    # brain_id preserved from handler's own wrap; not overwritten by dispatcher
    assert parsed["brain_id"] == "test-brain"
    assert parsed["data"] == {"inner": "payload"}


def test_dispatch_envelope_wraps_non_json_string(envelope_on, validator):
    """If a handler returns a non-JSON string, envelope wraps it as {'text': ...}."""

    def _str_handler(**kwargs):
        return "this is not json"

    result = _dispatch.dispatch("s", {}, {"s": _str_handler}, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["data"] == {"text": "this is not json"}


def test_dispatch_no_action_envelope_error(envelope_on, validator):
    result = _dispatch.dispatch("", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["ok"] is False
    assert parsed["error"]["error_type"] == "validation_error"


# --------------------------------------------------------------------------
# Async dispatcher
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_dispatch_default_bare():
    result = await _dispatch.async_dispatch("ok_async", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    assert parsed == {"result": "async_ok"}
    assert "ok" not in parsed


@pytest.mark.asyncio
async def test_async_dispatch_envelope_wraps(envelope_on, validator):
    result = await _dispatch.async_dispatch("ok_async", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["ok"] is True
    assert parsed["data"] == {"result": "async_ok"}


@pytest.mark.asyncio
async def test_async_dispatch_envelope_handler_exception(envelope_on, validator):
    result = await _dispatch.async_dispatch("raises_async", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    validator.validate(parsed)
    assert parsed["ok"] is False
    assert parsed["error"]["error_type"] == "handler_error"


# --------------------------------------------------------------------------
# Brain id / session id propagation via contextvars
# --------------------------------------------------------------------------


def test_dispatch_envelope_uses_context_brain_id(envelope_on):
    _envelope.set_brain_id("nucleus-primary")
    _envelope.set_session_id("sess-42")
    result = _dispatch.dispatch("ok_dict", {}, ROUTER, "test_module")
    parsed = json.loads(result)
    assert parsed["brain_id"] == "nucleus-primary"
    assert parsed["session_id"] == "sess-42"
