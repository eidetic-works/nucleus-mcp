"""
Circuit Breaker — Fault tolerance for external dependencies.
=============================================================
Prevents cascading failures when external services (Cloud Tasks,
Commitment Ledger, Federation peers) are unavailable.

States:
  CLOSED  — Normal operation, calls pass through.
  OPEN    — Failure threshold exceeded, calls fail fast.
  HALF_OPEN — After cooldown, one probe call allowed to test recovery.

Thread-safe. Zero external dependencies.
"""

import time
import threading
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("nucleus.circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-dependency circuit breaker.

    Args:
        name: Identifier for this breaker (e.g., "firestore", "commitment_ledger").
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait before transitioning to half-open.
        success_threshold: Successes in half-open needed to close again.
    """

    def __init__(self, name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 30.0, success_threshold: int = 1):
        self.name = name
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._success_threshold = success_threshold
        self._last_failure_time: float = 0.0
        self._total_failures: int = 0
        self._total_successes: int = 0
        self._total_rejected: int = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"CircuitBreaker[{self.name}]: OPEN -> HALF_OPEN")
            return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        # OPEN — fail fast
        with self._lock:
            self._total_rejected += 1
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._total_successes += 1
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"CircuitBreaker[{self.name}]: HALF_OPEN -> CLOSED")
            else:
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_failure_time = time.monotonic()
                logger.warning(f"CircuitBreaker[{self.name}]: HALF_OPEN -> OPEN (probe failed)")
            elif self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._last_failure_time = time.monotonic()
                logger.warning(
                    f"CircuitBreaker[{self.name}]: CLOSED -> OPEN "
                    f"(threshold {self._failure_threshold} reached)"
                )

    def reset(self) -> None:
        """Reset to closed state (for testing)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0

    @property
    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "total_rejected": self._total_rejected,
            }


# ── Global Registry ──────────────────────────────────────────

_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    with _registry_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name, **kwargs)
        return _breakers[name]


def get_all_breaker_status() -> Dict[str, Dict]:
    """Get status of all registered circuit breakers."""
    with _registry_lock:
        return {name: cb.status for name, cb in _breakers.items()}
