"""
Tests for Circuit Breaker — Fault tolerance for external dependencies
=====================================================================
"""

import time
import pytest
from mcp_server_nucleus.runtime.circuit_breaker import (
    CircuitBreaker, CircuitState, get_breaker, get_all_breaker_status,
)


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # After success, failure count resets, so another 2 failures shouldn't open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_and_counts(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        assert cb.allow_request() is False
        assert cb.allow_request() is False
        assert cb.status["total_rejected"] == 2

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_status_report(self):
        cb = CircuitBreaker("myservice", failure_threshold=3)
        cb.record_success()
        cb.record_failure()
        status = cb.status
        assert status["name"] == "myservice"
        assert status["state"] == "closed"
        assert status["total_successes"] == 1
        assert status["total_failures"] == 1

    def test_success_threshold_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN  # Need 2 successes
        cb.record_success()
        assert cb.state == CircuitState.CLOSED


class TestGlobalRegistry:
    def test_get_breaker_creates_once(self):
        cb1 = get_breaker("test_singleton_a")
        cb2 = get_breaker("test_singleton_a")
        assert cb1 is cb2

    def test_get_breaker_different_names(self):
        cb1 = get_breaker("service_x")
        cb2 = get_breaker("service_y")
        assert cb1 is not cb2

    def test_get_all_status(self):
        get_breaker("status_test_1")
        get_breaker("status_test_2")
        all_status = get_all_breaker_status()
        assert "status_test_1" in all_status
        assert "status_test_2" in all_status
