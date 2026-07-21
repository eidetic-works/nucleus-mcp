"""POST /telemetry + GET /telemetry/installs — anonymous telemetry receiver stub.

Authority: SPEC.md task ``g2_telemetry_receiver_e2e`` (PRINCIPAL G2 slice 2,
"telemetry receiver verified end-to-end"). The anonymous-telemetry *sender*
lives in ``mcp_server_nucleus.runtime.anon_telemetry`` and ships events to
``{endpoint}/api/telemetry/install``; the cloud-side Worker that ingests
OTLP spans lives at ``mcp-server-nucleus/cloudflare/worker-telemetry.js``.
This module is the **in-package HTTP receiver** — a minimal, dependency-free
Starlette route pair that:

  1. accepts a POST JSON payload matching the ``anon_telemetry._build_event``
     shape and returns 200 on success,
  2. rejects payloads missing required fields with a 400,
  3. exposes a GET endpoint that returns the distinct-install count seen by
     this receiver process (mock query — the real count lives behind the
     Cloudflare Worker + Upstash queue; this stub keeps an in-process set
     so the e2e test can assert the query is wired without hitting the
     network).

The receiver is intentionally minimal: it validates the envelope, dedups
``install_id`` into an in-memory set, and acks. No PII is logged. The
sender's privacy contract (``ANONYMOUS_TELEMETRY_IMPLEMENTATION.md``) is
preserved — only the opaque ``install_id`` token is retained, never tied
to user identity.

**G3.5 instrumentation (added 2026-07-18):** the receiver now also tracks:
  - **Week-2-active**: install_ids that send telemetry on ≥2 distinct days
    (the G3.5 "durable value" criterion). Tracked via a per-install_id set
    of date strings (YYYY-MM-DD).
  - **Returning actors**: install_ids that return after their first session
    (the G3.5 "external actor returns" criterion). Tracked via session_count
    per install_id.
  - **Willingness signals**: event_types that indicate constraint-legal
    willingness (feature_request, spec_thread_engagement, reinstall). Counted
    in a dedicated counter.

These metrics are surfaced via GET /telemetry/g35 — the G3.5 signal dashboard.
The real production version backs this with the Cloudflare Worker + Upstash;
this in-process stub is the test surface.

Wire-up mirrors ``relay_route``: a ``Route`` object exported as
``telemetry_post_route`` / ``telemetry_installs_route`` for the HTTP
transport ``server.py`` to insert into the fastmcp router.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Set

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("nucleus.telemetry_route")

# ── Config ────────────────────────────────────────────────────────────

MAX_BODY_BYTES = int(os.environ.get("NUCLEUS_TELEMETRY_MAX_BODY", "65536"))  # 64 KiB

# Required envelope fields per anon_telemetry._build_event. ``install_id``
# is the load-bearing dedup key (distinct-install count); ``event_type``
# classifies the span; ``command`` is the aggregate signal; ``nucleus_version``
# is the version floor for the broken-release bright-line.
REQUIRED_FIELDS = ("install_id", "event_type", "command", "nucleus_version")

# G3.5 willingness-signal event types. These are constraint-legal signals
# that an external actor is engaged beyond a one-shot install.
WILLINGNESS_EVENT_TYPES = frozenset({
    "feature_request",
    "spec_thread_engagement",
    "reinstall",
    "bug_report",
    "question",
})

# ── In-process state ──────────────────────────────────────────────────
#
# Distinct install_ids seen by this receiver process. The real
# distinct-install count lives behind the Cloudflare Worker + Upstash
# queue; this in-process set is the mock query surface the e2e test
# asserts against. Single-process is fine for the stub — multi-process
# deploys would back this with Redis (same as relay_route's rate buckets).
_seen_install_ids: Set[str] = set()
_event_count: int = 0

# G3.5 instrumentation state:
# - _install_dates: install_id → set of "YYYY-MM-DD" date strings
#   (used to compute week-2-active: ≥2 distinct days)
# - _install_sessions: install_id → session_count
#   (used to compute returning actors: session_count > 1)
# - _willingness_signals: count of willingness-signal events received
_install_dates: Dict[str, Set[str]] = {}
_install_sessions: Dict[str, int] = {}
_willingness_signals: int = 0


def _err(status: int, code: str, message: str) -> JSONResponse:
    """Canonical error envelope — matches relay_route's _err shape."""
    return JSONResponse(
        {"accepted": False, "error": code, "message": message},
        status_code=status,
    )


def _validate_payload(payload: Any) -> tuple[bool, str | None]:
    """Validate the parsed JSON payload. Returns (ok, error_message)."""
    if not isinstance(payload, dict):
        return False, "Body must be a JSON object"
    for field in REQUIRED_FIELDS:
        val = payload.get(field)
        if val is None or val == "":
            return False, f"Required field missing: {field}"
        if not isinstance(val, str):
            return False, f"Field {field} must be a string"
    return True, None


async def post_telemetry(request: Request) -> JSONResponse:
    """POST /telemetry — accept an anonymous telemetry event envelope."""
    global _event_count, _willingness_signals

    raw = await request.body()
    if not raw:
        return _err(400, "empty_body", "Request body is empty")
    if len(raw) > MAX_BODY_BYTES:
        return _err(
            413, "body_too_large", f"Request body exceeds {MAX_BODY_BYTES} bytes"
        )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        return _err(400, "invalid_json", f"Invalid JSON: {e}")

    ok, err = _validate_payload(payload)
    if not ok:
        return _err(400, "schema_violation", err or "schema validation failed")

    install_id = payload["install_id"]
    event_type = payload["event_type"]

    # Dedup into the in-process distinct-install set. The set is the mock
    # query surface for GET /telemetry/installs.
    _seen_install_ids.add(install_id)
    _event_count += 1

    # G3.5 instrumentation: track dates for week-2-active computation
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if install_id not in _install_dates:
        _install_dates[install_id] = set()
    _install_dates[install_id].add(today)

    # G3.5 instrumentation: track session count for returning-actor detection
    _install_sessions[install_id] = _install_sessions.get(install_id, 0) + 1

    # G3.5 instrumentation: count willingness signals
    if event_type in WILLINGNESS_EVENT_TYPES:
        _willingness_signals += 1

    logger.debug(
        "telemetry accepted install_id=%s event_type=%s command=%s",
        install_id, event_type, payload["command"],
    )

    return JSONResponse(
        {
            "accepted": True,
            "install_id": install_id,
            "event_type": event_type,
            "distinct_installs": len(_seen_install_ids),
            "events_received": _event_count,
            "received_at": time.time(),
        },
        status_code=200,
    )


async def get_telemetry_installs(request: Request) -> JSONResponse:
    """GET /telemetry/installs — return the distinct-install count.

    Mock query surface: the real count lives behind the Cloudflare Worker
    + Upstash queue. This stub returns the in-process set cardinality so
    the e2e test can assert the query is wired without hitting the
    network.
    """
    return JSONResponse(
        {
            "distinct_installs": len(_seen_install_ids),
            "events_received": _event_count,
            "source": "in-process-stub",
        },
        status_code=200,
    )


async def get_telemetry_g35(request: Request) -> JSONResponse:
    """GET /telemetry/g35 — G3.5 durable-value signal dashboard.

    Returns the three G3.5 criteria metrics:
    1. week_2_active: count of install_ids with telemetry on ≥2 distinct days
    2. returning_actors: count of install_ids with session_count > 1
    3. willingness_signals: count of willingness-signal events received

    Also returns per-install detail for debugging (without PII — only
    install_id, date_count, session_count).

    G3.5 criteria (PRINCIPAL.md line 107):
    - ≥N (default 5) week-2-active .brains
    - ≥1 external actor returns after first session
    - ≥1 constraint-legal willingness signal
    """
    week_2_active = sum(
        1 for dates in _install_dates.values() if len(dates) >= 2
    )
    returning_actors = sum(
        1 for count in _install_sessions.values() if count > 1
    )

    # Per-install detail (no PII — just counts)
    per_install = [
        {
            "install_id": iid,
            "distinct_days": len(_install_dates.get(iid, set())),
            "session_count": _install_sessions.get(iid, 0),
            "week_2_active": len(_install_dates.get(iid, set())) >= 2,
            "returning": _install_sessions.get(iid, 0) > 1,
        }
        for iid in _seen_install_ids
    ]

    return JSONResponse(
        {
            "g35_criteria": {
                "week_2_active_threshold": 5,
                "returning_actors_threshold": 1,
                "willingness_signals_threshold": 1,
            },
            "g35_metrics": {
                "week_2_active": week_2_active,
                "returning_actors": returning_actors,
                "willingness_signals": _willingness_signals,
            },
            "g35_pass": (
                week_2_active >= 5
                and returning_actors >= 1
                and _willingness_signals >= 1
            ),
            "distinct_installs": len(_seen_install_ids),
            "per_install": per_install,
            "source": "in-process-stub",
        },
        status_code=200,
    )


def reset_state() -> None:
    """Reset in-process state. Test helper — not wired in production."""
    global _event_count, _willingness_signals
    _seen_install_ids.clear()
    _event_count = 0
    _install_dates.clear()
    _install_sessions.clear()
    _willingness_signals = 0


# ── Routes ────────────────────────────────────────────────────────────

telemetry_post_route = Route("/telemetry", post_telemetry, methods=["POST"])
telemetry_installs_route = Route(
    "/telemetry/installs", get_telemetry_installs, methods=["GET"]
)
telemetry_g35_route = Route(
    "/telemetry/g35", get_telemetry_g35, methods=["GET"]
)

# Convenience aggregate for callers that want all routes at once.
telemetry_routes = [telemetry_post_route, telemetry_installs_route, telemetry_g35_route]
