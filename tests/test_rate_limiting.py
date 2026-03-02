"""
Tests for _dispatch.py rate limiting.

Verifies:
- Rate limiter allows calls within limit
- Rate limiter blocks calls exceeding limit
- Sliding window expiry works
- Disabled mode bypasses all checks
- Per-facade isolation (facade A limit doesn't affect facade B)
- get_status() reports correct state
- reset() clears all state
- Integration: rate-limited calls produce JSON error from dispatch()
- Integration: rate limit errors are recorded in telemetry
"""

import json
import time
import pytest

from mcp_server_nucleus.tools._dispatch import (
    DispatchRateLimiter,
    dispatch,
    get_dispatch_telemetry,
    get_dispatch_rate_limiter,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset global rate limiter and telemetry before each test."""
    get_dispatch_rate_limiter().reset()
    get_dispatch_telemetry().reset()
    yield
    get_dispatch_rate_limiter().reset()
    get_dispatch_telemetry().reset()


def _echo_handler(msg="hello"):
    return {"echo": msg}


ROUTER = {"echo": _echo_handler}


# ============================================================
# UNIT: DispatchRateLimiter
# ============================================================

class TestDispatchRateLimiter:
    def test_allows_within_limit(self):
        rl = DispatchRateLimiter(max_calls=5, window_seconds=60)
        for _ in range(5):
            assert rl.check("test_facade") is None

    def test_blocks_at_limit(self):
        rl = DispatchRateLimiter(max_calls=3, window_seconds=60)
        for _ in range(3):
            assert rl.check("test_facade") is None
        error = rl.check("test_facade")
        assert error is not None
        assert "Rate limit exceeded" in error
        assert "test_facade" in error

    def test_per_facade_isolation(self):
        rl = DispatchRateLimiter(max_calls=2, window_seconds=60)
        assert rl.check("facade_a") is None
        assert rl.check("facade_a") is None
        assert rl.check("facade_a") is not None  # blocked
        assert rl.check("facade_b") is None  # different facade, still allowed

    def test_sliding_window_expiry(self):
        rl = DispatchRateLimiter(max_calls=2, window_seconds=0.1)
        assert rl.check("test") is None
        assert rl.check("test") is None
        assert rl.check("test") is not None  # blocked
        time.sleep(0.15)  # wait for window to expire
        assert rl.check("test") is None  # allowed again

    def test_disabled_bypasses(self):
        rl = DispatchRateLimiter(max_calls=1, window_seconds=60)
        rl._disabled = True
        for _ in range(100):
            assert rl.check("test") is None

    def test_get_status(self):
        rl = DispatchRateLimiter(max_calls=10, window_seconds=60)
        rl.check("facade_a")
        rl.check("facade_a")
        rl.check("facade_b")
        status = rl.get_status()
        assert status["enabled"] is True
        assert status["max_calls"] == 10
        assert status["window_seconds"] == 60
        assert status["facades"]["facade_a"] == 2
        assert status["facades"]["facade_b"] == 1

    def test_get_status_disabled(self):
        rl = DispatchRateLimiter(max_calls=10, window_seconds=60)
        rl._disabled = True
        status = rl.get_status()
        assert status["enabled"] is False

    def test_reset_clears_state(self):
        rl = DispatchRateLimiter(max_calls=2, window_seconds=60)
        rl.check("test")
        rl.check("test")
        assert rl.check("test") is not None  # blocked
        rl.reset()
        assert rl.check("test") is None  # allowed after reset

    def test_error_message_contains_retry_time(self):
        rl = DispatchRateLimiter(max_calls=1, window_seconds=60)
        rl.check("test")
        error = rl.check("test")
        assert "Try again in" in error

    def test_single_call_limit(self):
        rl = DispatchRateLimiter(max_calls=1, window_seconds=60)
        assert rl.check("test") is None
        assert rl.check("test") is not None


# ============================================================
# INTEGRATION: dispatch + rate limiting
# ============================================================

class TestDispatchRateLimitingIntegration:
    def test_dispatch_rate_limited(self):
        """Calls exceeding global rate limiter produce JSON error."""
        rl = get_dispatch_rate_limiter()
        rl._max_calls = 2
        rl._window = 60

        # First 2 calls succeed
        r1 = json.loads(dispatch("echo", {}, ROUTER, "test_mod"))
        assert "echo" in r1
        r2 = json.loads(dispatch("echo", {}, ROUTER, "test_mod"))
        assert "echo" in r2

        # 3rd call is rate-limited
        r3 = json.loads(dispatch("echo", {}, ROUTER, "test_mod"))
        assert "error" in r3
        assert "Rate limit exceeded" in r3["error"]

        # Restore defaults
        rl._max_calls = 200

    def test_rate_limit_recorded_in_telemetry(self):
        rl = get_dispatch_rate_limiter()
        rl._max_calls = 1
        rl._window = 60

        dispatch("echo", {}, ROUTER, "telem_test")
        dispatch("echo", {}, ROUTER, "telem_test")  # rate-limited

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_errors"] >= 1

        rl._max_calls = 200

    def test_different_facades_independent(self):
        rl = get_dispatch_rate_limiter()
        rl._max_calls = 1
        rl._window = 60

        r1 = json.loads(dispatch("echo", {}, ROUTER, "mod_a"))
        assert "echo" in r1
        r2 = json.loads(dispatch("echo", {}, ROUTER, "mod_a"))
        assert "error" in r2  # blocked

        # Different module is still allowed
        r3 = json.loads(dispatch("echo", {}, ROUTER, "mod_b"))
        assert "echo" in r3

        rl._max_calls = 200
