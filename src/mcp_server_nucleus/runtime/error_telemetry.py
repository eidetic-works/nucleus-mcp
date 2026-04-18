"""
Structured Error Telemetry
=============================
Phase 73.4: Production-Grade Error Tracking

Provides:
1. Error categorization (Network, LLM, FileSystem, Validation, Auth, Unknown)
2. Structured error codes (E001-E999)
3. Error aggregation and pattern detection
4. Threshold-based alerting
5. Error rate monitoring with sliding window
6. Persistent error log for post-mortem analysis

Target: 100% error observability for 99.9% reliability.
"""

import json
import logging
import os
import threading
import time
from collections import deque
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger("nucleus.error_telemetry")


# ============================================================
# ERROR TAXONOMY
# ============================================================

class ErrorDomain(str, Enum):
    LLM = "LLM"
    FILESYSTEM = "FILESYSTEM"
    NETWORK = "NETWORK"
    VALIDATION = "VALIDATION"
    AUTH = "AUTH"
    CONCURRENCY = "CONCURRENCY"
    ENVIRONMENT = "ENVIRONMENT"
    TOOL_CALLING = "TOOL_CALLING"
    UNKNOWN = "UNKNOWN"


@dataclass
class StructuredError:
    """A structured, categorized error record."""
    error_id: str
    domain: ErrorDomain
    code: str
    message: str
    source_module: str
    severity: str = "ERROR"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    frontier: str = "COMPOUND"  # GROUND, ALIGN, COMPOUND
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "error_id": self.error_id,
            "domain": self.domain.value,
            "frontier": self.frontier,
            "code": self.code,
            "message": self.message,
            "source_module": self.source_module,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }
        if self.context:
            d["context"] = self.context
        if self.stack_trace:
            d["stack_trace"] = self.stack_trace[:500]
        return d


# Error code registry
ERROR_CODES = {
    # LLM errors (E1xx)
    "E100": ("LLM", "Timeout"),
    "E101": ("LLM", "Rate limited"),
    "E102": ("LLM", "Quota exceeded"),
    "E103": ("LLM", "Invalid response"),
    "E104": ("LLM", "Model error"),
    "E105": ("LLM", "JSON parse failure"),
    "E106": ("LLM", "Empty response"),
    "E107": ("LLM", "Circuit breaker open"),
    # Filesystem errors (E2xx)
    "E200": ("FILESYSTEM", "Write failed"),
    "E201": ("FILESYSTEM", "Read failed"),
    "E202": ("FILESYSTEM", "Permission denied"),
    "E203": ("FILESYSTEM", "Disk full"),
    "E204": ("FILESYSTEM", "File corrupted"),
    "E205": ("FILESYSTEM", "Lock timeout"),
    "E206": ("FILESYSTEM", "Atomic write failed"),
    # Network errors (E3xx)
    "E300": ("NETWORK", "Connection failed"),
    "E301": ("NETWORK", "DNS resolution failed"),
    "E302": ("NETWORK", "Connection reset"),
    "E303": ("NETWORK", "SSL error"),
    # Validation errors (E4xx)
    "E400": ("VALIDATION", "Invalid input"),
    "E401": ("VALIDATION", "Schema violation"),
    "E402": ("VALIDATION", "Missing required field"),
    "E403": ("VALIDATION", "Type mismatch"),
    # Auth errors (E5xx)
    "E500": ("AUTH", "API key missing"),
    "E501": ("AUTH", "API key invalid"),
    "E502": ("AUTH", "Permission denied"),
    "E503": ("AUTH", "Token expired"),
    # Tool calling errors (E6xx)
    "E600": ("TOOL_CALLING", "Intent analysis failed"),
    "E601": ("TOOL_CALLING", "Validation failed"),
    "E602": ("TOOL_CALLING", "Enforcement failed"),
    "E603": ("TOOL_CALLING", "Pattern learning failed"),
    "E604": ("TOOL_CALLING", "Tool not found"),
    "E605": ("TOOL_CALLING", "Tool execution failed"),
    # Concurrency errors (E7xx)
    "E700": ("CONCURRENCY", "Race condition detected"),
    "E701": ("CONCURRENCY", "Deadlock detected"),
    "E702": ("CONCURRENCY", "Stale data"),
    # Environment errors (E8xx)
    "E800": ("ENVIRONMENT", "Unsupported OS"),
    "E801": ("ENVIRONMENT", "Missing dependency"),
    "E802": ("ENVIRONMENT", "Invalid configuration"),
    "E803": ("ENVIRONMENT", "MCP host incompatibility"),
    # Unknown (E9xx)
    "E999": ("UNKNOWN", "Unclassified error"),
}


# ── Frontier mapping: Domain → Three Frontiers ──
_DOMAIN_TO_FRONTIER = {
    "LLM": "GROUND",
    "TOOL_CALLING": "GROUND",
    "NETWORK": "GROUND",
    "FILESYSTEM": "ALIGN",
    "VALIDATION": "ALIGN",
    "AUTH": "ALIGN",
    "ENVIRONMENT": "ALIGN",
    "CONCURRENCY": "COMPOUND",
    "UNKNOWN": "COMPOUND",
}


# ============================================================
# ERROR AGGREGATOR
# ============================================================

@dataclass
class ErrorWindow:
    """Sliding window for error rate calculation."""
    window_size_s: float = 300.0  # 5 minutes
    _timestamps: deque = field(default_factory=deque)

    def record(self):
        now = time.monotonic()
        self._timestamps.append(now)
        self._prune(now)

    def count(self) -> int:
        self._prune(time.monotonic())
        return len(self._timestamps)

    def rate_per_minute(self) -> float:
        self._prune(time.monotonic())
        if not self._timestamps:
            return 0.0
        elapsed = time.monotonic() - self._timestamps[0] if self._timestamps else 1.0
        if elapsed <= 0:
            return 0.0
        return len(self._timestamps) / (elapsed / 60.0)

    def _prune(self, now: float):
        cutoff = now - self.window_size_s
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()


class ErrorAggregator:
    """Aggregates errors by domain and code for pattern detection."""

    def __init__(self):
        self._by_domain: Dict[str, int] = {}
        self._by_code: Dict[str, int] = {}
        self._recent_errors: deque = deque(maxlen=100)
        self._windows: Dict[str, ErrorWindow] = {}
        self._total = 0
        self._lock = threading.Lock()

    def record(self, error: StructuredError):
        with self._lock:
            self._total += 1
            domain = error.domain.value
            self._by_domain[domain] = self._by_domain.get(domain, 0) + 1
            self._by_code[error.code] = self._by_code.get(error.code, 0) + 1
            self._recent_errors.append(error.to_dict())

            if domain not in self._windows:
                self._windows[domain] = ErrorWindow()
            self._windows[domain].record()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            rates = {}
            for domain, window in self._windows.items():
                rates[domain] = round(window.rate_per_minute(), 2)

            return {
                "total_errors": self._total,
                "by_domain": dict(self._by_domain),
                "by_code": dict(self._by_code),
                "error_rates_per_min": rates,
                "recent_count": len(self._recent_errors),
            }

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._recent_errors)[-limit:]

    def get_top_errors(self, n: int = 5) -> List[tuple]:
        with self._lock:
            return sorted(self._by_code.items(), key=lambda x: -x[1])[:n]


# ============================================================
# ALERT SYSTEM
# ============================================================

@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    domain: str
    max_errors_per_minute: float
    max_total_errors: int
    alert_level: str = "WARNING"


class AlertManager:
    """Threshold-based alerting for error rates."""

    DEFAULT_THRESHOLDS = [
        AlertThreshold("LLM", 5.0, 50, "WARNING"),
        AlertThreshold("LLM", 15.0, 100, "CRITICAL"),
        AlertThreshold("FILESYSTEM", 3.0, 30, "WARNING"),
        AlertThreshold("FILESYSTEM", 10.0, 50, "CRITICAL"),
        AlertThreshold("NETWORK", 5.0, 50, "WARNING"),
        AlertThreshold("TOOL_CALLING", 10.0, 100, "WARNING"),
    ]

    def __init__(self, thresholds: Optional[List[AlertThreshold]] = None):
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self._active_alerts: List[Dict[str, Any]] = []
        self._callbacks: List[Callable] = []

    def check(self, aggregator: ErrorAggregator) -> List[Dict[str, Any]]:
        """Check thresholds and return triggered alerts."""
        stats = aggregator.get_stats()
        triggered = []

        for threshold in self.thresholds:
            domain = threshold.domain
            rate = stats["error_rates_per_min"].get(domain, 0)
            total = stats["by_domain"].get(domain, 0)

            if rate > threshold.max_errors_per_minute or total > threshold.max_total_errors:
                alert = {
                    "domain": domain,
                    "level": threshold.alert_level,
                    "rate_per_min": rate,
                    "threshold_rate": threshold.max_errors_per_minute,
                    "total": total,
                    "threshold_total": threshold.max_total_errors,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                triggered.append(alert)
                self._active_alerts.append(alert)

                for cb in self._callbacks:
                    try:
                        cb(alert)
                    except Exception:
                        pass

        return triggered

    def on_alert(self, callback: Callable):
        self._callbacks.append(callback)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return self._active_alerts[-20:]


# ============================================================
# ERROR TELEMETRY (Main Class)
# ============================================================

class ErrorTelemetry:
    """
    Central error telemetry system for Nucleus.
    
    Usage:
        telemetry = get_error_telemetry()
        telemetry.record_error("E100", "LLM timeout after 30s", "llm_intent_analyzer")
        stats = telemetry.get_stats()
    """

    def __init__(self):
        self._aggregator = ErrorAggregator()
        self._alert_manager = AlertManager()
        self._error_counter = 0
        self._log_path = Path(
            os.getenv("NUCLEAR_BRAIN_PATH", "./.brain")
        ) / "metrics" / "error_telemetry.jsonl"
        self._lock = threading.Lock()

    def record_error(
        self,
        code: str,
        message: str,
        source_module: str,
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> StructuredError:
        """Record a structured error."""
        with self._lock:
            self._error_counter += 1
            error_id = f"err-{self._error_counter:06d}"

        # Determine domain from code
        domain_str = ERROR_CODES.get(code, ("UNKNOWN", "Unknown"))[0]
        try:
            domain = ErrorDomain(domain_str)
        except ValueError:
            domain = ErrorDomain.UNKNOWN

        stack_trace = None
        if exception:
            import traceback
            stack_trace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

        frontier = _DOMAIN_TO_FRONTIER.get(domain_str, "COMPOUND")

        error = StructuredError(
            error_id=error_id,
            domain=domain,
            code=code,
            message=message[:500],
            source_module=source_module,
            severity=severity,
            frontier=frontier,
            context=context or {},
            stack_trace=stack_trace,
        )

        # Aggregate
        self._aggregator.record(error)

        # Log
        logger.log(
            getattr(logging, severity, logging.ERROR),
            f"[{code}] {source_module}: {message[:200]}"
        )

        # Persist (non-blocking)
        self._persist_error(error)

        # Check alerts
        self._alert_manager.check(self._aggregator)

        # Auto-Delta: significant errors produce learning signals
        if severity in ("ERROR", "CRITICAL"):
            self._emit_error_delta(error)

        return error

    def _emit_error_delta(self, error: StructuredError):
        """Produce a Delta from a significant error — errors are learning signals."""
        try:
            from .delta_ops import record_delta
            record_delta(
                frontier=error.frontier,
                expected_source=error.source_module,
                expected_intent="Successful operation",
                actual_source="error_telemetry",
                actual_outcome=f"[{error.code}] {error.message[:120]}",
                insight=f"Error in {error.domain.value} domain",
            )
        except Exception:
            pass  # Delta pipeline failure must never block error recording

    def _persist_error(self, error: StructuredError):
        """Persist error to JSONL log."""
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(error.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass  # Can't log errors about logging errors

    def get_stats(self) -> Dict[str, Any]:
        return self._aggregator.get_stats()

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._aggregator.get_recent(limit)

    def get_alerts(self) -> List[Dict[str, Any]]:
        return self._alert_manager.get_active_alerts()

    def get_top_errors(self, n: int = 5) -> List[tuple]:
        return self._aggregator.get_top_errors(n)

    def on_alert(self, callback: Callable):
        self._alert_manager.on_alert(callback)


# ============================================================
# SINGLETON
# ============================================================

_telemetry_instance: Optional[ErrorTelemetry] = None
_telemetry_lock = threading.Lock()

def get_error_telemetry() -> ErrorTelemetry:
    """Get singleton error telemetry instance."""
    global _telemetry_instance
    if _telemetry_instance is None:
        with _telemetry_lock:
            if _telemetry_instance is None:
                _telemetry_instance = ErrorTelemetry()
    return _telemetry_instance
