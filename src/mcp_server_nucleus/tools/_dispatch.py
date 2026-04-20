"""Universal action dispatcher for Super-Tools facade pattern.

Each tool module exposes ONE facade tool with an `action` parameter.
This dispatcher routes actions to the correct handler function.

Includes built-in telemetry: per-action timing, success/error counts,
and frequency tracking across all 12 facades / 171 actions.
"""

import json
import inspect
import asyncio
import time
import threading
import logging
import os
from typing import Dict, Callable, Any, Optional
from collections import defaultdict

from . import _envelope

logger = logging.getLogger("nucleus.dispatch")


# ============================================================
# AMBIENT FRONTIER HEALTH (appended to every tool response)
# ============================================================

_health_cache = {"line": "", "expires": 0.0}
_HEALTH_CACHE_TTL = 60  # seconds


def _ambient_health_line() -> str:
    """One-line frontier health summary, cached 60s. Silent fail."""
    if not os.environ.get("NUCLEUS_AMBIENT_HEALTH"):
        return ""
    now = time.time()
    if now < _health_cache["expires"] and _health_cache["line"]:
        return _health_cache["line"]
    try:
        from ..runtime.common import get_brain_path
        brain = get_brain_path()
        # GROUND
        vlog = brain / "verification_log.jsonl"
        g_count = sum(1 for _ in open(vlog)) if vlog.exists() else 0
        # ALIGN
        verdicts = brain / "driver" / "human_verdicts.jsonl"
        a_count = sum(1 for _ in open(verdicts)) if verdicts.exists() else 0
        # COMPOUND
        deltas = brain / "deltas" / "deltas.jsonl"
        c_count = sum(1 for _ in open(deltas)) if deltas.exists() else 0

        parts = []
        parts.append(f"GROUND {g_count}" if g_count else "GROUND —")
        parts.append(f"ALIGN {a_count}" if a_count else "ALIGN —")
        parts.append(f"COMPOUND {c_count}" if c_count else "COMPOUND —")
        line = "\n[frontiers: " + " | ".join(parts) + "]"
        _health_cache["line"] = line
        _health_cache["expires"] = now + _HEALTH_CACHE_TTL
        return line
    except Exception:
        return ""


# ============================================================
# DISPATCH TELEMETRY
# ============================================================

class DispatchTelemetry:
    """Lightweight telemetry for facade action dispatch.

    Tracks per-action: call count, success/error counts, total duration.
    Thread-safe. Zero external dependencies.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._actions: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "errors": 0, "total_ms": 0.0, "last_error": None}
        )
        self._facades: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"calls": 0, "errors": 0}
        )

    def record(self, module: str, action: str, duration_ms: float, error: Optional[str] = None):
        with self._lock:
            a = self._actions[f"{module}.{action}"]
            a["calls"] += 1
            a["total_ms"] += duration_ms
            f = self._facades[module]
            f["calls"] += 1
            if error:
                a["errors"] += 1
                a["last_error"] = error
                f["errors"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            total_calls = sum(f["calls"] for f in self._facades.values())
            total_errors = sum(f["errors"] for f in self._facades.values())
            top_actions = sorted(
                self._actions.items(), key=lambda x: -x[1]["calls"]
            )[:10]
            return {
                "total_dispatches": total_calls,
                "total_errors": total_errors,
                "error_rate": total_errors / total_calls if total_calls else 0,
                "facades": dict(self._facades),
                "top_10_actions": {
                    k: {
                        "calls": v["calls"],
                        "errors": v["errors"],
                        "avg_ms": round(v["total_ms"] / v["calls"], 2) if v["calls"] else 0,
                    }
                    for k, v in top_actions
                },
            }

    def reset(self):
        with self._lock:
            self._actions.clear()
            self._facades.clear()


_telemetry = DispatchTelemetry()


def get_dispatch_telemetry() -> DispatchTelemetry:
    """Get the global dispatch telemetry instance."""
    return _telemetry


# ============================================================
# INPUT SANITIZATION
# ============================================================

# Limits to prevent abuse / accidental mega-payloads
_MAX_PARAM_DEPTH = 5
_MAX_STRING_LENGTH = 100_000  # 100KB per string value
_MAX_PARAMS_COUNT = 50
_FORBIDDEN_KEYS = frozenset({"__proto__", "constructor", "__class__", "__import__"})


def sanitize_params(params: Any, module_name: str = "", action: str = "", _depth: int = 0) -> dict:
    """Sanitize and validate facade action params before dispatch.

    Enforces:
    - params must be a dict (or None/missing → empty dict)
    - Max nesting depth to prevent stack overflow
    - Max param count to prevent DoS
    - Forbidden keys (prototype pollution patterns)
    - String length caps
    - Strips None-valued keys to simplify handler signatures

    Returns:
        Cleaned dict safe for **kwargs expansion into handlers.

    Raises:
        ValueError: on constraint violations.
    """
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise ValueError(
            f"[{module_name}.{action}] params must be a dict, got {type(params).__name__}"
        )
    if _depth > _MAX_PARAM_DEPTH:
        raise ValueError(
            f"[{module_name}.{action}] params nested too deep (max {_MAX_PARAM_DEPTH})"
        )
    if len(params) > _MAX_PARAMS_COUNT:
        raise ValueError(
            f"[{module_name}.{action}] too many params ({len(params)}, max {_MAX_PARAMS_COUNT})"
        )

    cleaned = {}
    for key, value in params.items():
        # Key validation
        if not isinstance(key, str):
            logger.warning(f"[{module_name}.{action}] skipping non-string key: {key!r}")
            continue
        if key in _FORBIDDEN_KEYS:
            logger.warning(f"[{module_name}.{action}] blocked forbidden key: {key}")
            continue
        # Strip None values — handlers use defaults
        if value is None:
            continue
        # Recurse into nested dicts
        if isinstance(value, dict):
            cleaned[key] = sanitize_params(value, module_name, action, _depth + 1)
        # Cap string lengths
        elif isinstance(value, str) and len(value) > _MAX_STRING_LENGTH:
            raise ValueError(
                f"[{module_name}.{action}] param '{key}' string too long "
                f"({len(value)} chars, max {_MAX_STRING_LENGTH})"
            )
        else:
            cleaned[key] = value
    return cleaned


# ============================================================
# RATE LIMITING
# ============================================================

# Defaults: 200 calls per 60-second window per facade. Override via env vars.
_DEFAULT_RATE_LIMIT = int(os.environ.get("NUCLEUS_RATE_LIMIT", "200"))
_DEFAULT_RATE_WINDOW = int(os.environ.get("NUCLEUS_RATE_WINDOW_SECONDS", "60"))


class DispatchRateLimiter:
    """Sliding-window rate limiter for facade dispatch.

    Tracks per-facade call timestamps and rejects calls that exceed
    the configured limit within the time window. Thread-safe.

    Configurable via:
      NUCLEUS_RATE_LIMIT           — max calls per window (default 200)
      NUCLEUS_RATE_WINDOW_SECONDS  — window size in seconds (default 60)
      NUCLEUS_RATE_LIMIT_DISABLED  — set to "true" to bypass entirely
    """

    def __init__(self, max_calls: int = _DEFAULT_RATE_LIMIT,
                 window_seconds: int = _DEFAULT_RATE_WINDOW):
        self._lock = threading.Lock()
        self._max_calls = max_calls
        self._window = window_seconds
        self._calls: Dict[str, list] = defaultdict(list)  # facade → [timestamps]
        self._disabled = os.environ.get("NUCLEUS_RATE_LIMIT_DISABLED", "").lower() == "true"

    @property
    def disabled(self) -> bool:
        return self._disabled

    def check(self, facade: str) -> Optional[str]:
        """Check if a facade call is allowed.

        Returns None if allowed, or an error message string if rate-limited.
        """
        if self._disabled:
            return None

        now = time.monotonic()
        cutoff = now - self._window

        with self._lock:
            timestamps = self._calls[facade]
            # Prune expired entries
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if len(timestamps) >= self._max_calls:
                return (
                    f"Rate limit exceeded for {facade}: "
                    f"{self._max_calls} calls per {self._window}s window. "
                    f"Try again in {timestamps[0] + self._window - now:.1f}s."
                )
            timestamps.append(now)
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status for all facades."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            return {
                "enabled": not self._disabled,
                "max_calls": self._max_calls,
                "window_seconds": self._window,
                "facades": {
                    facade: len([t for t in ts if t >= cutoff])
                    for facade, ts in self._calls.items()
                },
            }

    def reset(self):
        """Reset all rate limit state (for testing)."""
        with self._lock:
            self._calls.clear()


_rate_limiter = DispatchRateLimiter()


def get_dispatch_rate_limiter() -> DispatchRateLimiter:
    """Get the global dispatch rate limiter instance."""
    return _rate_limiter


# ============================================================
# DISPATCHERS
# ============================================================

def _maybe_wrap_response(
    result_str: str,
    *,
    ok: bool,
    module_name: str,
    action: str,
    error_type: Optional[str] = None,
) -> str:
    """Wrap a handler JSON string in the envelope when enabled.

    When NUCLEUS_ENVELOPE=on:
      - Parses `result_str` as JSON; on failure, wraps as `{"text": ...}`.
      - If parsed payload already looks like an envelope (idempotent guard),
        passes it through untouched — avoids double-wrapping when a handler
        pre-wraps.
      - On error paths, uses `_envelope.error_envelope(...)` when error_type
        is given; otherwise wraps with ok=ok.

    When envelope is disabled (default): returns `result_str` unchanged.
    This keeps the 1,327 existing tests green until the codemod flips the
    default ON (scripts/codemod_envelope_tests.py, shipping in the same
    v1.2.0 release).
    """
    if not _envelope.is_enabled():
        return result_str

    try:
        payload = json.loads(result_str)
    except (ValueError, TypeError):
        payload = {"text": result_str}

    if _envelope.is_envelope(payload):
        # Handler already wrapped — respect it.
        return result_str

    if error_type is not None:
        err = _envelope.error_envelope(
            error_type,
            recovery_hint=f"check {module_name}.{action} params",
            detail=payload.get("error") if isinstance(payload, dict) else None,
        )
        return json.dumps(err, indent=2, default=str)

    envelope = _envelope.wrap(payload, ok=ok)
    return json.dumps(envelope, indent=2, default=str)


def dispatch(action: str, params: dict, router: Dict[str, Callable], module_name: str) -> str:
    """Synchronous action dispatcher for facade tools.

    Args:
        action: The action name to execute.
        params: Dictionary of keyword arguments for the handler.
        router: Mapping of action names to handler functions.
        module_name: Name of the facade tool (for error messages).

    Returns:
        JSON string result from the handler, or an error message.
        When NUCLEUS_ENVELOPE=on, the string is a serialized envelope dict
        (see tools/_envelope.py + schemas/envelope.schema.json).
    """
    if not action:
        raw = json.dumps({
            "error": f"No action specified for {module_name}",
            "available_actions": sorted(router.keys()),
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action="_none", error_type="validation_error")

    # Rate limit check
    rate_error = _rate_limiter.check(module_name)
    if rate_error:
        _telemetry.record(module_name, action or "_rate_limited", 0, rate_error)
        raw = json.dumps({"error": rate_error, "module": module_name}, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="rate_limited")

    handler = router.get(action)
    if not handler:
        _telemetry.record(module_name, action or "_unknown", 0, f"Unknown action '{action}'")
        raw = json.dumps({
            "error": f"Unknown action '{action}' in {module_name}",
            "available_actions": sorted(router.keys()),
            "hint": f"Try: {module_name}(action='{sorted(router.keys())[0]}', params={{...}})"
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="not_found")

    try:
        params = sanitize_params(params, module_name, action)
    except ValueError as e:
        _telemetry.record(module_name, action, 0, str(e))
        raw = json.dumps({"error": str(e), "module": module_name}, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="validation_error")

    t0 = time.perf_counter()
    try:
        result = handler(**params)
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms)
        # Ensure result is always a string — guards against structured_content errors
        result_str = result if isinstance(result, str) else json.dumps(result, indent=2, default=str)
        wrapped = _maybe_wrap_response(result_str, ok=True, module_name=module_name, action=action)
        return wrapped + _ambient_health_line()
    except TypeError as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms, str(e))
        sig = inspect.signature(handler)
        raw = json.dumps({
            "error": f"Invalid params for action '{action}': {e}",
            "expected_params": str(sig),
            "provided_params": list(params.keys()),
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="validation_error")
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms, str(e))
        raw = json.dumps({
            "error": f"Action '{action}' failed: {e}",
            "module": module_name,
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="handler_error")


def _ensure_str(result: Any) -> str:
    """Ensure a handler result is always a string.

    This is a safety net: all handlers should return strings,
    but if one slips through returning a dict/list/other type,
    this prevents FastMCP 'structured_content must be a dict or None'
    errors by converting before the result reaches FunctionTool.run().
    """
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, default=str)


async def async_dispatch(action: str, params: dict, router: Dict[str, Callable], module_name: str) -> str:
    """Async action dispatcher for facade tools with async handlers.

    Same as dispatch() but awaits coroutine handlers. Envelope wrapping
    honors the NUCLEUS_ENVELOPE flag identically (see _maybe_wrap_response).
    """
    if not action:
        raw = json.dumps({
            "error": f"No action specified for {module_name}",
            "available_actions": sorted(router.keys()),
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action="_none", error_type="validation_error")

    # Rate limit check
    rate_error = _rate_limiter.check(module_name)
    if rate_error:
        _telemetry.record(module_name, action or "_rate_limited", 0, rate_error)
        raw = json.dumps({"error": rate_error, "module": module_name}, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="rate_limited")

    handler = router.get(action)
    if not handler:
        _telemetry.record(module_name, action or "_unknown", 0, f"Unknown action '{action}'")
        raw = json.dumps({
            "error": f"Unknown action '{action}' in {module_name}",
            "available_actions": sorted(router.keys()),
            "hint": f"Try: {module_name}(action='{sorted(router.keys())[0]}', params={{...}})"
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="not_found")

    try:
        params = sanitize_params(params, module_name, action)
    except ValueError as e:
        _telemetry.record(module_name, action, 0, str(e))
        raw = json.dumps({"error": str(e), "module": module_name}, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="validation_error")

    t0 = time.perf_counter()
    try:
        if inspect.iscoroutinefunction(handler):
            result = await handler(**params)
        else:
            result = handler(**params)
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms)
        result_str = result if isinstance(result, str) else json.dumps(result, indent=2, default=str)
        return _maybe_wrap_response(result_str, ok=True, module_name=module_name, action=action)
    except TypeError as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms, str(e))
        sig = inspect.signature(handler)
        raw = json.dumps({
            "error": f"Invalid params for action '{action}': {e}",
            "expected_params": str(sig),
            "provided_params": list(params.keys()),
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="validation_error")
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms, str(e))
        raw = json.dumps({
            "error": f"Action '{action}' failed: {e}",
            "module": module_name,
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="handler_error")
