"""Regression test: dispatch missing-param error must not leak internals.

Defect (b): When a facade action is called with missing required params,
the dispatch error message previously leaked Python internals like
``register.<locals>.<lambda>()`` or ``register.<locals>._h_end_of_day()``
in the TypeError string.  The dispatcher must surface the required
param name cleanly instead.

This test covers both ``dispatch`` (sync) and ``async_dispatch`` with
handlers that mimic the real engrams.py pattern — named functions and
lambdas defined inside a ``register()`` closure — so the qualname
contains ``register.<locals>.<...>``.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from mcp_server_nucleus.tools import _dispatch


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Reset rate limiter and telemetry per test."""
    _dispatch.get_dispatch_rate_limiter().reset()
    _dispatch.get_dispatch_telemetry().reset()
    monkeypatch.delenv("NUCLEUS_ENVELOPE", raising=False)
    monkeypatch.delenv("NUCLEUS_AMBIENT_HEALTH", raising=False)
    yield


# --------------------------------------------------------------------------
# Handlers that mimic the engrams.py register() closure pattern
# --------------------------------------------------------------------------

def _make_router():
    """Build a router whose handlers are defined inside a register() closure,
    exactly like engrams.py — so qualnames contain ``register.<locals>.``."""
    def register():
        def _h_end_of_day(summary, key_decisions=None, blockers=None):
            return "ok"

        _lambda_handler = lambda key, value, context="Decision", intensity=5: (key, value)

        return {
            "end_of_day": _h_end_of_day,
            "write_engram": _lambda_handler,
        }
    return register()


# --------------------------------------------------------------------------
# async_dispatch (used by engrams.py)
# --------------------------------------------------------------------------

def test_async_dispatch_named_func_missing_param_no_leak():
    """end_of_day without summary: error surfaces 'summary' cleanly."""
    router = _make_router()
    result = asyncio.run(
        _dispatch.async_dispatch("end_of_day", {}, router, "nucleus_engrams")
    )
    parsed = json.loads(result)

    assert "error" in parsed
    # Must NOT leak register.<locals> or <lambda> internals
    assert "register.<locals>" not in result, "leaked register.<locals> in error"
    assert "<lambda>" not in result, "leaked <lambda> in error"
    # Must surface the missing param name cleanly
    assert "summary" in parsed["error"], f"error doesn't name the missing param: {parsed['error']}"


def test_async_dispatch_lambda_missing_param_no_leak():
    """write_engram (lambda) without key/value: error surfaces names cleanly."""
    router = _make_router()
    result = asyncio.run(
        _dispatch.async_dispatch("write_engram", {}, router, "nucleus_engrams")
    )
    parsed = json.loads(result)

    assert "error" in parsed
    assert "register.<locals>" not in result, "leaked register.<locals> in error"
    assert "<lambda>" not in result, "leaked <lambda> in error"
    # Must surface the missing param names
    assert "key" in parsed["error"], f"error doesn't name missing 'key': {parsed['error']}"
    assert "value" in parsed["error"], f"error doesn't name missing 'value': {parsed['error']}"


def test_async_dispatch_expected_params_clean():
    """expected_params field shows clean signature, no <lambda> or register.<locals>."""
    router = _make_router()
    result = asyncio.run(
        _dispatch.async_dispatch("end_of_day", {}, router, "nucleus_engrams")
    )
    parsed = json.loads(result)

    assert "expected_params" in parsed
    expected = parsed["expected_params"]
    assert "register.<locals>" not in expected
    assert "<lambda>" not in expected
    assert "summary" in expected


# --------------------------------------------------------------------------
# dispatch (sync)
# --------------------------------------------------------------------------

def test_sync_dispatch_named_func_missing_param_no_leak():
    """Sync dispatch: end_of_day without summary surfaces 'summary' cleanly."""
    router = _make_router()
    result = _dispatch.dispatch("end_of_day", {}, router, "nucleus_engrams")
    parsed = json.loads(result)

    assert "error" in parsed
    assert "register.<locals>" not in result, "leaked register.<locals> in error"
    assert "<lambda>" not in result, "leaked <lambda> in error"
    assert "summary" in parsed["error"], f"error doesn't name the missing param: {parsed['error']}"


def test_sync_dispatch_lambda_missing_param_no_leak():
    """Sync dispatch: lambda handler without key/value surfaces names cleanly."""
    router = _make_router()
    result = _dispatch.dispatch("write_engram", {}, router, "nucleus_engrams")
    parsed = json.loads(result)

    assert "error" in parsed
    assert "register.<locals>" not in result, "leaked register.<locals> in error"
    assert "<lambda>" not in result, "leaked <lambda> in error"
    assert "key" in parsed["error"]
    assert "value" in parsed["error"]


def test_sync_dispatch_expected_params_clean():
    """Sync dispatch: expected_params shows clean signature."""
    router = _make_router()
    result = _dispatch.dispatch("write_engram", {}, router, "nucleus_engrams")
    parsed = json.loads(result)

    assert "expected_params" in parsed
    expected = parsed["expected_params"]
    assert "register.<locals>" not in expected
    assert "<lambda>" not in expected
    assert "key" in expected
    assert "value" in expected
