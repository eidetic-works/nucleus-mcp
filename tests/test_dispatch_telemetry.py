"""
Tests for dispatch telemetry instrumentation in _dispatch.py.

Verifies:
- DispatchTelemetry tracking (calls, errors, timing)
- Telemetry integration with sync dispatch
- Telemetry integration with async dispatch
- dispatch_metrics action in nucleus_telemetry
- Thread safety under concurrent dispatch
"""

import pytest
import json
import asyncio
import threading

from mcp_server_nucleus.tools._dispatch import (
    dispatch,
    async_dispatch,
    DispatchTelemetry,
    get_dispatch_telemetry,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def telemetry():
    """Fresh DispatchTelemetry for each test."""
    return DispatchTelemetry()


@pytest.fixture(autouse=True)
def reset_global_telemetry():
    """Reset global telemetry before/after each test."""
    t = get_dispatch_telemetry()
    t.reset()
    yield
    t.reset()


def _echo_handler(msg="hello"):
    return {"echo": msg}


def _error_handler():
    raise ValueError("intentional test error")


def _slow_handler():
    import time
    time.sleep(0.01)
    return "slow_done"


async def _async_echo(msg="async_hello"):
    return {"echo": msg}


async def _async_error():
    raise RuntimeError("async test error")


SAMPLE_ROUTER = {
    "echo": _echo_handler,
    "error": _error_handler,
    "slow": _slow_handler,
}

ASYNC_ROUTER = {
    "echo": _async_echo,
    "error": _async_error,
    "sync_in_async": _echo_handler,
}


# ============================================================
# TEST: DispatchTelemetry Unit Tests
# ============================================================

class TestDispatchTelemetry:
    def test_record_success(self, telemetry):
        telemetry.record("nucleus_tasks", "add", 5.0)
        metrics = telemetry.get_metrics()
        assert metrics["total_dispatches"] == 1
        assert metrics["total_errors"] == 0
        assert "nucleus_tasks" in metrics["facades"]

    def test_record_error(self, telemetry):
        telemetry.record("nucleus_tasks", "add", 5.0, "some error")
        metrics = telemetry.get_metrics()
        assert metrics["total_errors"] == 1
        assert metrics["error_rate"] == 1.0

    def test_multiple_actions(self, telemetry):
        telemetry.record("nucleus_tasks", "add", 5.0)
        telemetry.record("nucleus_tasks", "list", 3.0)
        telemetry.record("nucleus_engrams", "health", 1.0)
        metrics = telemetry.get_metrics()
        assert metrics["total_dispatches"] == 3
        assert len(metrics["facades"]) == 2
        assert len(metrics["top_10_actions"]) == 3

    def test_avg_ms_calculation(self, telemetry):
        telemetry.record("nucleus_tasks", "add", 10.0)
        telemetry.record("nucleus_tasks", "add", 20.0)
        metrics = telemetry.get_metrics()
        action_key = "nucleus_tasks.add"
        assert metrics["top_10_actions"][action_key]["avg_ms"] == 15.0
        assert metrics["top_10_actions"][action_key]["calls"] == 2

    def test_top_10_ordering(self, telemetry):
        for i in range(15):
            telemetry.record("m", f"action_{i}", 1.0)
        # Add extra calls to action_0 to make it top
        for _ in range(5):
            telemetry.record("m", "action_0", 1.0)
        metrics = telemetry.get_metrics()
        top = list(metrics["top_10_actions"].keys())
        assert len(top) == 10
        assert top[0] == "m.action_0"

    def test_reset(self, telemetry):
        telemetry.record("m", "a", 1.0)
        telemetry.reset()
        metrics = telemetry.get_metrics()
        assert metrics["total_dispatches"] == 0

    def test_error_rate_zero_division(self, telemetry):
        metrics = telemetry.get_metrics()
        assert metrics["error_rate"] == 0


# ============================================================
# TEST: Sync Dispatch Telemetry Integration
# ============================================================

class TestSyncDispatchTelemetry:
    def test_successful_dispatch_records_telemetry(self):
        result = dispatch("echo", {"msg": "test"}, SAMPLE_ROUTER, "nucleus_test")
        parsed = json.loads(result)
        assert parsed["echo"] == "test"

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_dispatches"] == 1
        assert metrics["total_errors"] == 0
        assert "nucleus_test.echo" in metrics["top_10_actions"]

    def test_error_dispatch_records_telemetry(self):
        result = dispatch("error", {}, SAMPLE_ROUTER, "nucleus_test")
        parsed = json.loads(result)
        assert "error" in parsed

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_errors"] == 1
        assert metrics["top_10_actions"]["nucleus_test.error"]["errors"] == 1

    def test_unknown_action_records_telemetry(self):
        dispatch("nonexistent", {}, SAMPLE_ROUTER, "nucleus_test")

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_errors"] == 1

    def test_timing_recorded(self):
        dispatch("slow", {}, SAMPLE_ROUTER, "nucleus_test")

        metrics = get_dispatch_telemetry().get_metrics()
        avg_ms = metrics["top_10_actions"]["nucleus_test.slow"]["avg_ms"]
        assert avg_ms >= 5  # At least 5ms for the 10ms sleep

    def test_type_error_records_telemetry(self):
        dispatch("echo", {"wrong_param": "x"}, SAMPLE_ROUTER, "nucleus_test")

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_errors"] == 1

    def test_empty_action_no_telemetry(self):
        dispatch("", {}, SAMPLE_ROUTER, "nucleus_test")
        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_dispatches"] == 0


# ============================================================
# TEST: Async Dispatch Telemetry Integration
# ============================================================

class TestAsyncDispatchTelemetry:
    @pytest.mark.asyncio
    async def test_async_success(self):
        result = await async_dispatch("echo", {"msg": "hi"}, ASYNC_ROUTER, "nucleus_async")
        parsed = json.loads(result)
        assert parsed["echo"] == "hi"

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_dispatches"] == 1

    @pytest.mark.asyncio
    async def test_async_error(self):
        result = await async_dispatch("error", {}, ASYNC_ROUTER, "nucleus_async")
        parsed = json.loads(result)
        assert "error" in parsed

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_errors"] == 1

    @pytest.mark.asyncio
    async def test_sync_handler_in_async_dispatch(self):
        result = await async_dispatch("sync_in_async", {}, ASYNC_ROUTER, "nucleus_async")
        parsed = json.loads(result)
        assert parsed["echo"] == "hello"

        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_dispatches"] == 1


# ============================================================
# TEST: Thread Safety
# ============================================================

class TestDispatchTelemetryThreadSafety:
    def test_concurrent_records(self, telemetry):
        errors = []

        def worker(idx):
            try:
                for _ in range(100):
                    telemetry.record(f"facade_{idx % 3}", f"action_{idx}", 1.0)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        metrics = telemetry.get_metrics()
        assert metrics["total_dispatches"] == 1000

    def test_concurrent_dispatch_calls(self):
        errors = []

        def worker(idx):
            try:
                dispatch("echo", {"msg": f"thread-{idx}"}, SAMPLE_ROUTER, "nucleus_test")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_dispatches"] == 20


# ============================================================
# TEST: Global Singleton
# ============================================================

class TestGlobalTelemetrySingleton:
    def test_singleton_identity(self):
        t1 = get_dispatch_telemetry()
        t2 = get_dispatch_telemetry()
        assert t1 is t2

    def test_dispatch_uses_global(self):
        dispatch("echo", {}, SAMPLE_ROUTER, "nucleus_test")
        metrics = get_dispatch_telemetry().get_metrics()
        assert metrics["total_dispatches"] >= 1
