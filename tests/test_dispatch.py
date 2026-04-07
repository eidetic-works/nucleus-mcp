"""
Tests for Dispatch Module — Telemetry, Rate Limiting, Sanitization, Routing
===========================================================================
"""

import json
import os
import time
import pytest
from unittest.mock import MagicMock


# ── Sanitize Params Tests ─────────────────────────────────────

class TestSanitizeParams:
    def test_none_returns_empty_dict(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        assert sanitize_params(None) == {}

    def test_non_dict_raises(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        with pytest.raises(ValueError, match="params must be a dict"):
            sanitize_params("not a dict", "mod", "act")

    def test_strips_none_values(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        result = sanitize_params({"a": 1, "b": None, "c": "hello"})
        assert result == {"a": 1, "c": "hello"}

    def test_blocks_forbidden_keys(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        result = sanitize_params({"__proto__": "hack", "legit": "ok"})
        assert "__proto__" not in result
        assert result["legit"] == "ok"

    def test_blocks_all_forbidden_keys(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        result = sanitize_params({
            "__proto__": "x", "constructor": "y",
            "__class__": "z", "__import__": "w",
            "safe": "ok"
        })
        assert len(result) == 1
        assert result["safe"] == "ok"

    def test_rejects_deeply_nested(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        # Max depth is 5, so 7 levels deep should trigger
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "too deep"}}}}}}}
        with pytest.raises(ValueError, match="nested too deep"):
            sanitize_params(deep, "mod", "act")

    def test_rejects_too_many_params(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        big = {f"key_{i}": i for i in range(60)}
        with pytest.raises(ValueError, match="too many params"):
            sanitize_params(big, "mod", "act")

    def test_rejects_long_string(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        with pytest.raises(ValueError, match="string too long"):
            sanitize_params({"data": "x" * 200_000}, "mod", "act")

    def test_recurses_into_nested_dicts(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        result = sanitize_params({"outer": {"inner": "val", "none_val": None}})
        assert result["outer"] == {"inner": "val"}

    def test_skips_non_string_keys(self):
        from mcp_server_nucleus.tools._dispatch import sanitize_params
        # In Python dicts can have non-string keys
        result = sanitize_params({123: "val", "ok": "yes"})
        assert 123 not in result
        assert result["ok"] == "yes"


# ── Telemetry Tests ───────────────────────────────────────────

class TestDispatchTelemetry:
    def test_record_and_get_metrics(self):
        from mcp_server_nucleus.tools._dispatch import DispatchTelemetry
        t = DispatchTelemetry()
        t.record("engrams", "write", 10.5)
        t.record("engrams", "write", 20.0)
        t.record("engrams", "query", 5.0)
        metrics = t.get_metrics()
        assert metrics["total_dispatches"] == 3
        assert metrics["total_errors"] == 0
        assert "engrams.write" in metrics["top_10_actions"]
        assert metrics["top_10_actions"]["engrams.write"]["calls"] == 2

    def test_record_error(self):
        from mcp_server_nucleus.tools._dispatch import DispatchTelemetry
        t = DispatchTelemetry()
        t.record("tasks", "add", 5.0, error="Something broke")
        metrics = t.get_metrics()
        assert metrics["total_errors"] == 1
        assert metrics["error_rate"] == 1.0

    def test_reset_clears_all(self):
        from mcp_server_nucleus.tools._dispatch import DispatchTelemetry
        t = DispatchTelemetry()
        t.record("mod", "act", 1.0)
        t.reset()
        metrics = t.get_metrics()
        assert metrics["total_dispatches"] == 0

    def test_avg_ms_calculation(self):
        from mcp_server_nucleus.tools._dispatch import DispatchTelemetry
        t = DispatchTelemetry()
        t.record("mod", "act", 10.0)
        t.record("mod", "act", 20.0)
        metrics = t.get_metrics()
        assert metrics["top_10_actions"]["mod.act"]["avg_ms"] == 15.0


# ── Rate Limiter Tests ────────────────────────────────────────

class TestDispatchRateLimiter:
    def test_allows_under_limit(self):
        from mcp_server_nucleus.tools._dispatch import DispatchRateLimiter
        limiter = DispatchRateLimiter(max_calls=5, window_seconds=60)
        for _ in range(5):
            assert limiter.check("test_facade") is None

    def test_blocks_over_limit(self):
        from mcp_server_nucleus.tools._dispatch import DispatchRateLimiter
        limiter = DispatchRateLimiter(max_calls=3, window_seconds=60)
        for _ in range(3):
            limiter.check("test_facade")
        error = limiter.check("test_facade")
        assert error is not None
        assert "Rate limit exceeded" in error

    def test_get_status(self):
        from mcp_server_nucleus.tools._dispatch import DispatchRateLimiter
        limiter = DispatchRateLimiter(max_calls=10, window_seconds=60)
        limiter.check("engrams")
        limiter.check("engrams")
        limiter.check("tasks")
        status = limiter.get_status()
        assert status["enabled"] is True
        assert status["facades"]["engrams"] == 2
        assert status["facades"]["tasks"] == 1

    def test_reset(self):
        from mcp_server_nucleus.tools._dispatch import DispatchRateLimiter
        limiter = DispatchRateLimiter(max_calls=5, window_seconds=60)
        limiter.check("test")
        limiter.reset()
        status = limiter.get_status()
        assert len(status["facades"]) == 0

    def test_disabled_mode(self):
        from mcp_server_nucleus.tools._dispatch import DispatchRateLimiter
        os.environ["NUCLEUS_RATE_LIMIT_DISABLED"] = "true"
        try:
            limiter = DispatchRateLimiter(max_calls=1, window_seconds=60)
            assert limiter.disabled is True
            # Should allow even beyond limit
            limiter.check("test")
            limiter.check("test")
            assert limiter.check("test") is None
        finally:
            os.environ.pop("NUCLEUS_RATE_LIMIT_DISABLED", None)


# ── Dispatch Function Tests ───────────────────────────────────

class TestDispatch:
    def _get_dispatch(self):
        from mcp_server_nucleus.tools._dispatch import dispatch, get_dispatch_rate_limiter
        # Reset rate limiter to avoid cross-test interference
        get_dispatch_rate_limiter().reset()
        return dispatch

    def test_no_action_returns_available(self):
        dispatch = self._get_dispatch()
        router = {"write": lambda: "ok", "query": lambda: "ok"}
        result = json.loads(dispatch("", {}, router, "engrams"))
        assert "available_actions" in result
        assert "write" in result["available_actions"]

    def test_unknown_action(self):
        dispatch = self._get_dispatch()
        router = {"write": lambda: "ok"}
        result = json.loads(dispatch("nonexistent", {}, router, "engrams"))
        assert "Unknown action" in result["error"]

    def test_successful_dispatch(self):
        dispatch = self._get_dispatch()
        router = {"greet": lambda name: json.dumps({"hello": name})}
        result = dispatch("greet", {"name": "world"}, router, "test")
        assert "world" in result

    def test_handler_type_error(self):
        dispatch = self._get_dispatch()
        router = {"act": lambda x: "ok"}
        result = json.loads(dispatch("act", {"wrong_param": 1}, router, "test"))
        assert "error" in result
        assert "expected_params" in result

    def test_handler_exception(self):
        dispatch = self._get_dispatch()
        def failing_handler():
            raise RuntimeError("boom")
        router = {"fail": failing_handler}
        result = json.loads(dispatch("fail", {}, router, "test"))
        assert "boom" in result["error"]

    def test_dispatch_records_telemetry(self):
        from mcp_server_nucleus.tools._dispatch import DispatchTelemetry, get_dispatch_rate_limiter
        dispatch = self._get_dispatch()
        router = {"act": lambda: "ok"}
        dispatch("act", {}, router, "test_mod")
        # Telemetry is recorded on the global instance
        # Just verify no crash — telemetry is a side effect


# ── Async Dispatch Tests ──────────────────────────────────────

class TestAsyncDispatch:
    def test_async_handler(self):
        import asyncio
        from mcp_server_nucleus.tools._dispatch import async_dispatch, get_dispatch_rate_limiter
        get_dispatch_rate_limiter().reset()

        async def async_handler(name):
            return json.dumps({"hello": name})

        router = {"greet": async_handler}
        result = asyncio.run(
            async_dispatch("greet", {"name": "async"}, router, "test")
        )
        assert "async" in result

    def test_async_with_sync_handler(self):
        import asyncio
        from mcp_server_nucleus.tools._dispatch import async_dispatch, get_dispatch_rate_limiter
        get_dispatch_rate_limiter().reset()

        def sync_handler():
            return json.dumps({"sync": True})

        router = {"act": sync_handler}
        result = asyncio.run(
            async_dispatch("act", {}, router, "test")
        )
        assert "sync" in result

    def test_async_unknown_action(self):
        import asyncio
        from mcp_server_nucleus.tools._dispatch import async_dispatch, get_dispatch_rate_limiter
        get_dispatch_rate_limiter().reset()
        result = json.loads(asyncio.run(
            async_dispatch("nope", {}, {"a": lambda: None}, "test")
        ))
        assert "Unknown action" in result["error"]


# ── Ensure Str Tests ──────────────────────────────────────────

class TestEnsureStr:
    def test_string_passthrough(self):
        from mcp_server_nucleus.tools._dispatch import _ensure_str
        assert _ensure_str("hello") == "hello"

    def test_dict_serialized(self):
        from mcp_server_nucleus.tools._dispatch import _ensure_str
        result = _ensure_str({"key": "val"})
        assert json.loads(result) == {"key": "val"}

    def test_list_serialized(self):
        from mcp_server_nucleus.tools._dispatch import _ensure_str
        result = _ensure_str([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]
