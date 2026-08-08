"""Response envelope for facade tool dispatch.

Every facade response (when NUCLEUS_ENVELOPE != 'off') is wrapped in a
stable envelope so consumers can:
  - Identify which brain served the response (`brain_id`)
  - Detect schema version for safe migration (`schema_version`)
  - Surface non-fatal warnings without tripping ok=False (`warnings`)
  - Receive structured errors with recovery hints (`error`)

The envelope contract is mirrored as a JSON Schema artifact at
`src/mcp_server_nucleus/schemas/envelope.schema.json` — consumers can pin
to the schema version and regression-test against it.

This module is the ONE place where envelope shape is defined. Callers go
through `wrap()` / `error_envelope()` / `unwrap()` — never build dicts
by hand.

Design notes:
  - Opt-in via default-on, opt-OUT via NUCLEUS_ENVELOPE=off (keeps the
    1,327 existing tests green until codemod lands).
  - `brain_id` resolution is best-effort; failures degrade to "unknown"
    rather than raising, because an envelope that fails to build would
    mask the underlying response.
  - `session_id` is pulled from contextvars set by stdio_server on
    session init; falls back to process-scoped UUID when absent.
"""

from __future__ import annotations

import os
import uuid
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

ENVELOPE_SCHEMA_VERSION = "2"

# Session-scoped context populated by stdio_server on MCP initialize.
# Consumers should NOT set these directly — they're written by the
# transport layer once per session.
_session_id_var: ContextVar[Optional[str]] = ContextVar("nucleus_session_id", default=None)
_brain_id_var: ContextVar[Optional[str]] = ContextVar("nucleus_brain_id", default=None)

_process_session_fallback: str = f"proc-{uuid.uuid4().hex[:12]}"


def set_session_id(session_id: Optional[str]) -> None:
    """Set the session id for the current request context.

    Called by `stdio_server.handle_initialize` once per MCP session.
    Safe to call with None to clear.
    """
    _session_id_var.set(session_id)


def set_brain_id(brain_id: Optional[str]) -> None:
    """Set the brain id for the current request context.

    Called by `manifest.load()` once per brain access. Safe to call with
    None to clear (will degrade to 'unknown' in envelopes).
    """
    _brain_id_var.set(brain_id)


def get_session_id() -> str:
    """Return the current session id, falling back to process-level id."""
    sid = _session_id_var.get()
    return sid if sid else _process_session_fallback


def get_brain_id() -> str:
    """Return the current brain id. Best-effort — never raises.

    Resolution order:
      1. Explicit context var (set by manifest.load)
      2. NUCLEUS_BRAIN_ID environment variable
      3. "unknown" (degrade open)
    """
    bid = _brain_id_var.get()
    if bid:
        return bid
    env = os.environ.get("NUCLEUS_BRAIN_ID")
    if env:
        return env
    return "unknown"


def is_enabled() -> bool:
    """Return True if envelope wrapping is enabled.

    Controlled by NUCLEUS_ENVELOPE env var. Default: DISABLED.

    The default-off posture is intentional: the 1,327 existing tests
    assert on raw handler payloads and would break under envelope wrap.
    A test-fixture codemod (scripts/codemod_envelope_tests.py) migrates
    assertions to unwrap before the envelope default can safely flip on.

    Set NUCLEUS_ENVELOPE=on to opt into envelope wrapping. Any value
    other than 'on' (case-insensitive) is treated as off.
    """
    return os.environ.get("NUCLEUS_ENVELOPE", "off").lower() == "on"


def wrap(
    data: Any,
    *,
    ok: bool = True,
    warnings: Optional[List[str]] = None,
    error: Optional[Dict[str, Any]] = None,
    brain_id: Optional[str] = None,
    session_id: Optional[str] = None,
    schema_version: str = ENVELOPE_SCHEMA_VERSION,
) -> Dict[str, Any]:
    """Wrap a response payload in the standard envelope.

    When envelope is disabled via NUCLEUS_ENVELOPE=off, returns `data`
    unchanged (bare payload, legacy contract).

    Args:
      data: The response payload (any JSON-serializable value).
      ok: Success flag. When False, `error` SHOULD be set.
      warnings: Non-fatal warnings (e.g., constitution policy hints).
      error: Structured error dict. Use `error_envelope()` for convenience.
      brain_id: Override brain id. Default: resolved from context.
      session_id: Override session id. Default: resolved from context.
      schema_version: Envelope schema version. Default: current.

    Returns:
      Envelope dict, or bare `data` if disabled.
    """
    if not is_enabled():
        return data

    envelope = {
        "ok": ok,
        "data": data,
        "brain_id": brain_id if brain_id is not None else get_brain_id(),
        "session_id": session_id if session_id is not None else get_session_id(),
        "schema_version": schema_version,
        "warnings": list(warnings) if warnings else [],
        "error": error,
    }
    return envelope


def error_envelope(
    error_type: str,
    *,
    recovery_hint: str = "",
    last_healthy_at: Optional[str] = None,
    pid: Optional[int] = None,
    inflight_writes: Optional[List[str]] = None,
    detail: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build a structured error envelope.

    The shape here is the reference for every `error` field across the
    codebase — stdio_server transport errors, dispatch handler errors,
    hygiene GC failures, health sidecar timeouts all use it.

    Args:
      error_type: Short token. Examples: transport_closed, handler_error,
                  timeout, validation_error, not_found, forbidden.
      recovery_hint: Actionable one-liner for the user (e.g.,
                     "nucleus restart --force").
      last_healthy_at: ISO8601 timestamp. Used by transport_closed etc.
      pid: Process id of the server that failed.
      inflight_writes: Ids of writes that were in-flight at failure.
      detail: Optional human-readable detail string.
      **extra: Additional fields allowed by schema.

    Returns:
      A full envelope with ok=False and populated error block.
    """
    err: Dict[str, Any] = {
        "error_type": error_type,
        "recovery_hint": recovery_hint,
    }
    if last_healthy_at is not None:
        err["last_healthy_at"] = last_healthy_at
    if pid is not None:
        err["pid"] = pid
    if inflight_writes is not None:
        err["inflight_writes"] = list(inflight_writes)
    if detail is not None:
        err["detail"] = detail
    err.update(extra)
    return wrap(None, ok=False, error=err)


def unwrap(response: Any) -> Any:
    """Best-effort extraction of `data` from an envelope.

    If response is a dict that looks like an envelope (has 'ok' and
    'data' keys), returns `response["data"]`. Otherwise returns the
    response as-is. Useful for test helpers and backward-compat
    consumers.
    """
    if isinstance(response, dict) and "ok" in response and "data" in response:
        return response["data"]
    return response


def is_envelope(response: Any) -> bool:
    """Return True if `response` looks like an envelope."""
    return (
        isinstance(response, dict)
        and "ok" in response
        and "data" in response
        and "schema_version" in response
    )
