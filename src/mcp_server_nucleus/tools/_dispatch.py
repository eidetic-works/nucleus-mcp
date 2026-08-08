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
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Callable, Any, Optional
from collections import defaultdict

from . import _envelope

logger = logging.getLogger("nucleus.dispatch")


# ============================================================
# SHARED HELPER RESOLUTION
# ============================================================

def _default_make_response(ok, data=None, error=None):
    """Byte-identical fallback for the injected ``make_response`` helper.

    Mirrors the inline lambda the single-action facades (cost_router,
    audit_log_tool) previously each defined verbatim. In production the
    server always injects ``helpers["make_response"]`` so this fallback is
    not normally exercised; it exists only so a facade can be registered
    with a bare ``helpers`` dict (e.g. in unit tests) without crashing.
    """
    return json.dumps({"success": ok, "data": data, "error": error})


def resolve_make_response(helpers: Dict[str, Any]) -> Callable:
    """Return the injected ``make_response`` or the shared default fallback.

    Centralizes the ``helpers.get("make_response", <inline lambda>)`` snippet
    that was duplicated byte-for-byte across the hand-rolled facades, so the
    fallback lives in exactly one place alongside the other dispatch
    boilerplate. Pure refactor: the resolved callable and its JSON output are
    identical to the previous inline form.
    """
    return helpers.get("make_response", _default_make_response)


def make_response_dispatch(
    action: str,
    params: dict,
    router: Dict[str, Callable],
    make_response: Callable,
    *,
    valid_actions: Optional[list] = None,
    log_labels: Optional[Dict[str, str]] = None,
    logger_override: Optional[logging.Logger] = None,
) -> str:
    """Thin action dispatcher for the ``make_response``-envelope facades.

    The two single/few-action facades that pre-date the ``ROUTER`` + ``dispatch``
    pattern (``audit_log_tool`` → ``nucleus_audit``, ``cost_router`` →
    ``nucleus_route``) hand-rolled an identical ``if action == ... elif`` chain
    plus a per-handler ``try/except Exception → make_response(False,
    error=str(exc))`` guard. This collapses that boilerplate into one place so
    each facade only declares its ``{action: handler}`` map and its own handlers.

    Behavior is byte-identical to the previous inline form:

      * Unknown action → ``make_response(False, error="Unknown action
        '<action>'. Valid: <a | b | c>")`` where the valid list is
        ``valid_actions`` if given, else ``router`` insertion order.
      * Known action → ``handler(params)`` is invoked. Any raised ``Exception``
        is logged via ``logger.exception(<label>)`` (label from ``log_labels``
        for that action, falling back to ``"<module> <action> failed"`` shape
        only if provided) and converted to ``make_response(False,
        error=str(exc))`` — mirroring each facade's old per-action guard.

    Unlike :func:`dispatch`, this does NOT apply param sanitization, telemetry,
    rate limiting, Variant-B stubbing, ambient-health, or envelope wrapping:
    the hand-rolled facades never did, and adding them would change their
    observable output. Handlers therefore receive the raw ``params`` dict and
    own all of their own validation/success envelopes.

    Args:
        action: The requested action name.
        params: Raw params dict passed straight through to the handler.
        router: Mapping of action name → handler. Each handler is called as
            ``handler(params)`` and returns a ``make_response(...)`` string.
        make_response: The resolved ``make_response`` helper (see
            :func:`resolve_make_response`).
        valid_actions: Explicit ordering for the "Valid: ..." hint. Defaults to
            ``list(router.keys())`` (insertion order) when omitted.
        log_labels: Per-action ``logger.exception`` message. When an action has
            no entry, no label-specific log is emitted beyond the exception
            itself.
        logger_override: Logger to use for ``logger.exception``. Defaults to the
            shared dispatch logger.

    Returns:
        The handler's ``make_response`` JSON string, or the shared unknown/error
        envelope produced via ``make_response``.
    """
    log = logger_override or logger
    handler = router.get(action)
    if handler is None:
        valid = valid_actions if valid_actions is not None else list(router.keys())
        return make_response(
            False,
            error=f"Unknown action '{action}'. Valid: {' | '.join(valid)}",
        )

    try:
        return handler(params)
    except Exception as exc:  # noqa: BLE001 — mirrors per-action facade guards
        label = (log_labels or {}).get(action)
        if label:
            log.exception(label)
        else:
            log.exception("dispatch action '%s' failed", action)
        return make_response(False, error=str(exc))


# ============================================================
# AMBIENT FRONTIER HEALTH (appended to every tool response)
# ============================================================

_health_cache = {"line": "", "expires": 0.0}
_HEALTH_CACHE_TTL = 60  # seconds


# ============================================================
# VARIANT B (Phase-2 test vs control) — runtime-substrate-off flag
# ============================================================
# When NUCLEUS_VARIANT_B_RUNTIME_OFF=1 is set, substrate READ actions return
# a tiny stub instead of executing. Tool plumbing (registration, schemas)
# stays fully active so the experimental arm has identical prompt/tool surface
# to the baseline; only the *runtime gain* of substrate (engram retrieval,
# context injection, ledger reads) is removed. Token-economics measurement
# can then attribute the delta cleanly between "Anthropic cache" and
# "Nucleus runtime substrate."
#
# Writes pass through unchanged (token-cost effect is dominated by what gets
# returned, not what gets persisted). Always-passthrough actions (version,
# health, export_schema) execute normally regardless.
#
# Spec: .brain/plans/phase2_test_vs_control_spec.md (Variant B).

_VARIANT_B_READ_PREFIXES = (
    "query_", "search_", "read_", "get_", "list_", "view_", "recall",
    "metrics", "status", "morning_brief", "dashboard", "context_graph",
    "render_graph", "audit_log", "trace_list", "trace_view",
    "engram_neighbors", "session_inject",
)
_VARIANT_B_READ_EXACT = {
    "list_decisions", "list_snapshots", "list_agents", "list_pending_consents",
    "ipc_tokens", "metering_summary", "list_drafts", "search_threads",
    "satellite", "open_loops", "patterns", "commitment_health",
    "list_commitments", "list_dashboard_snapshots", "get_alerts",
    "weekly_consolidate", "compounding_status",
}
_VARIANT_B_PASSTHROUGH = {
    "version", "export_schema", "health", "list_tools",
    "prometheus_metrics",  # generic ops, no substrate gain
}


def _is_variant_b_active() -> bool:
    return os.environ.get("NUCLEUS_VARIANT_B_RUNTIME_OFF", "").lower() in ("1", "true", "yes")


def _variant_b_stub_if_read(module_name: str, action: str) -> Optional[str]:
    """If Variant B is on and `action` is a substrate read, return a stub
    JSON response. Otherwise return None (caller continues normal dispatch)."""
    if not _is_variant_b_active():
        return None
    if action in _VARIANT_B_PASSTHROUGH:
        return None
    is_read = (
        action in _VARIANT_B_READ_EXACT
        or any(action.startswith(p) for p in _VARIANT_B_READ_PREFIXES)
    )
    if not is_read:
        return None
    stub = json.dumps({
        "variant_b_runtime_off": True,
        "module": module_name,
        "action": action,
        "data": None,
        "note": "substrate runtime disabled for Phase-2 measurement; "
                "tool plumbing remains active",
    }, separators=(",", ":"))
    return stub


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
# UNKNOWN-PARAM REJECTION (pre-bind)
# ============================================================


def _allowed_param_names(handler: Callable) -> Optional[frozenset]:
    """Keyword names ``handler`` accepts, or None when undeterminable.

    The signature is authoritative. Handlers absorbing ``**kwargs`` hide their
    contract from ``inspect``; those must publish it as ``_nucleus_params``
    (any iterable of key names).
    """
    declared = getattr(handler, "_nucleus_params", None)
    if declared is not None:
        return frozenset(declared)
    try:
        sig = inspect.signature(handler)
    except (TypeError, ValueError):
        return None
    names = set()
    for name, param in sig.parameters.items():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            return None
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            continue
        names.add(name)
    return frozenset(names)


def _reject_unknown(
    handler: Callable, params: Any, module_name: str, action: str
) -> Optional[str]:
    """Reject RAW params carrying keys the handler does not accept.

    MUST run BEFORE sanitize_params: sanitize strips None-valued keys, so an
    unknown key with a null value would otherwise bind cleanly. Measured
    2026-08-01: ``nucleus_tasks list {"zzz":"X"}`` was rejected while
    ``{"zzz":None}`` executed — a universal bypass across all 280 actions.
    """
    if not isinstance(params, dict):
        return None  # sanitize_params owns the "must be a dict" error
    allowed = _allowed_param_names(handler)
    if allowed is None:
        logger.warning(
            "[%s.%s] unknown-param check SKIPPED: handler absorbs **kwargs "
            "and declares no _nucleus_params", module_name, action,
        )
        return None
    provided = [k for k in params if isinstance(k, str)]
    unknown = sorted(k for k in provided if k not in allowed)
    if not unknown:
        return None
    return json.dumps({
        "error": (
            f"Invalid params for action '{action}': unexpected keyword "
            f"argument(s) {', '.join(repr(k) for k in unknown)}"
        ),
        "expected_params": sorted(allowed),
        "provided_params": provided,
    }, indent=2)


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
# ORCHESTRATION DEMAND TELEMETRY RECORDER
# ============================================================

_ORCHESTRATION_FACADES = frozenset({
    "nucleus_orchestration",
    "nucleus_telemetry",
    "nucleus_slots",
    "nucleus_infra",
    "nucleus_agents",
})


def _record_orchestration_demand(
    facade: str, action: Any, params: Any, router: Optional[Dict[str, Callable]] = None
) -> None:
    """Record call-attempt telemetry for orchestration facades.

    Appends one JSON line to ~/.nucleus/orchestration_demand.jsonl (or NUCLEUS_DEMAND_LOG).
    Must NEVER raise, change behavior, or fail facade dispatch.
    """
    try:
        caller = None
        if isinstance(params, dict) and "caller" in params and isinstance(params["caller"], str) and params["caller"]:
            caller = params["caller"]
        else:
            for env_var in ("NUCLEUS_CALLER", "NUCLEUS_SESSION_ROLE", "NUCLEUS_AGENT_ID", "USER", "LOGNAME"):
                val = os.environ.get(env_var)
                if val and val.strip():
                    caller = val.strip()
                    break

        action_str = str(action) if action is not None else ""
        well_formed = False
        if isinstance(params, dict) and isinstance(action, str) and action:
            well_formed = True
            if router and action in router:
                handler = router[action]
                if _reject_unknown(handler, params, facade, action) is not None:
                    well_formed = False
            if well_formed:
                try:
                    sanitize_params(params, facade, action_str)
                except Exception:
                    well_formed = False

        # SYNTHETIC MARKING — without this the instrument reports its own tests
        # as demand, which is the exact failure it was built to prevent.
        #
        # Measured on the first real read: 1,420 rows, ALL inside a 3-minute
        # window, ALL from the controls script. The report said
        # "CALLED: 128 | UNCALLED: 0" — which would have flipped the
        # orchestration verdict from SUPERSEDED to "actively used" on pure
        # instrument pollution, and 71 surfaces would have been kept or folded
        # on the strength of a test suite calling itself.
        #
        # `caller` cannot save us: it falls back to USER/LOGNAME, so a control
        # run and a real agent call are both just the unix user. The signal has
        # to be set explicitly by whoever knows they are testing.
        #
        # Same fix as scripts/stop_gates_flip_report.py, where control fixtures
        # were 82% and 93% of each gate's promotion bar.
        synthetic = bool(
            os.environ.get("NUCLEUS_DEMAND_SYNTHETIC")
            or os.environ.get("NUCLEUS_DEMAND_LOG")  # a redirected log is a test by definition
            or os.environ.get("PYTEST_CURRENT_TEST")
        )

        ts = datetime.now(timezone.utc).isoformat()
        row = {
            "ts": ts,
            "facade": facade,
            "action": action_str,
            "caller": caller,
            "synthetic": synthetic,
            "well_formed": well_formed,
            "params_well_formed": well_formed,
        }

        log_path_env = os.environ.get("NUCLEUS_DEMAND_LOG")
        if log_path_env:
            log_path = Path(log_path_env)
        else:
            log_path = Path.home() / ".nucleus" / "orchestration_demand.jsonl"

        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


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

    if module_name in _ORCHESTRATION_FACADES:
        _record_orchestration_demand(module_name, action, params, router)

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
    if module_name in _ORCHESTRATION_FACADES:
        _record_orchestration_demand(module_name, action, params, router)

    # Guard against non-string action (e.g. LLM swaps action/params args)
    if not isinstance(action, str):
        raw = json.dumps({
            "error": f"action must be a string, got {type(action).__name__}",
            "available_actions": sorted(router.keys()),
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action="_invalid_type", error_type="validation_error")

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

    # Variant B (Phase-2 test vs control): if runtime-substrate-off flag is
    # set and this action is a substrate read, stub it. Tool plumbing stays
    # active so prompt/tool surface is identical between baseline + experimental.
    stub = _variant_b_stub_if_read(module_name, action)
    if stub is not None:
        _telemetry.record(module_name, action, 0)
        return _maybe_wrap_response(stub, ok=True, module_name=module_name, action=action)

    # Reject unknown keys on the RAW params, BEFORE sanitize_params strips
    # None values — a null-valued unknown key otherwise binds silently.
    reject = _reject_unknown(handler, params, module_name, action)
    if reject is not None:
        _telemetry.record(module_name, action, 0, "unknown params")
        return _maybe_wrap_response(reject, ok=False, module_name=module_name, action=action, error_type="validation_error")

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
        if e.__traceback__ is not None and e.__traceback__.tb_next is not None:
            # Raised INSIDE the handler body, not by kwarg binding: a server bug,
            # not a caller param error. Do not fabricate expected_params.
            raw = json.dumps({
                "error": f"Action '{action}' failed: {e}",
                "module": module_name,
            }, indent=2)
            return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="handler_error")
        sig = inspect.signature(handler)
        # Clean up the error message — don't leak internal implementation
        # details like "register.<locals>.<lambda>()" (fw-1781007677).
        clean_msg = str(e)
        if "missing" in clean_msg and "required" in clean_msg:
            import re as _re
            _m = _re.search(r"missing (\d+) required positional argument(?:s)?: (.+)", clean_msg)
            if _m:
                clean_msg = f"Missing required parameter: {_m.group(2)}"
        raw = json.dumps({
            "error": f"Invalid params for action '{action}': {clean_msg}",
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
    if module_name in _ORCHESTRATION_FACADES:
        _record_orchestration_demand(module_name, action, params, router)

    # Guard against non-string action (e.g. LLM swaps action/params args)
    if not isinstance(action, str):
        raw = json.dumps({
            "error": f"action must be a string, got {type(action).__name__}",
            "available_actions": sorted(router.keys()),
        }, indent=2)
        return _maybe_wrap_response(raw, ok=False, module_name=module_name, action="_invalid_type", error_type="validation_error")

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

    # Variant B (Phase-2 test vs control): if runtime-substrate-off flag is
    # set and this action is a substrate read, stub it. Tool plumbing stays
    # active so prompt/tool surface is identical between baseline + experimental.
    stub = _variant_b_stub_if_read(module_name, action)
    if stub is not None:
        _telemetry.record(module_name, action, 0)
        return _maybe_wrap_response(stub, ok=True, module_name=module_name, action=action)

    # Reject unknown keys on the RAW params, BEFORE sanitize_params strips
    # None values — a null-valued unknown key otherwise binds silently.
    reject = _reject_unknown(handler, params, module_name, action)
    if reject is not None:
        _telemetry.record(module_name, action, 0, "unknown params")
        return _maybe_wrap_response(reject, ok=False, module_name=module_name, action=action, error_type="validation_error")

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
            # Sync lambdas may wrap async impls — await the returned coroutine
            if asyncio.iscoroutine(result):
                result = await result
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms)
        result_str = result if isinstance(result, str) else json.dumps(result, indent=2, default=str)
        return _maybe_wrap_response(result_str, ok=True, module_name=module_name, action=action)
    except TypeError as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        _telemetry.record(module_name, action, duration_ms, str(e))
        if e.__traceback__ is not None and e.__traceback__.tb_next is not None:
            # Raised INSIDE the handler body, not by kwarg binding: a server bug,
            # not a caller param error. Do not fabricate expected_params.
            raw = json.dumps({
                "error": f"Action '{action}' failed: {e}",
                "module": module_name,
            }, indent=2)
            return _maybe_wrap_response(raw, ok=False, module_name=module_name, action=action, error_type="handler_error")
        sig = inspect.signature(handler)
        # Clean up the error message — don't leak internal implementation
        # details like "register.<locals>.<lambda>()" (fw-1781007677).
        clean_msg = str(e)
        if "missing" in clean_msg and "required" in clean_msg:
            import re as _re
            _m = _re.search(r"missing (\d+) required positional argument(?:s)?: (.+)", clean_msg)
            if _m:
                clean_msg = f"Missing required parameter: {_m.group(2)}"
        raw = json.dumps({
            "error": f"Invalid params for action '{action}': {clean_msg}",
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
