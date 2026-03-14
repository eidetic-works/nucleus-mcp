"""Nucleus Runtime — Anonymous Usage Telemetry.

Opt-out anonymous telemetry that sends aggregate command-level data
to telemetry.nucleusos.dev so the Nucleus team can understand real-world
usage patterns. Uses a SEPARATE OTel pipeline from the user's enterprise
OTel config (otel_export.py) — zero interference.

What is sent:
    - command name (e.g. "morning-brief", "engram-query")
    - tool category (e.g. "nucleus_engrams")
    - duration_ms
    - error_type (class name only, e.g. "ValueError")
    - nucleus version
    - python version
    - OS platform

What is NEVER sent:
    - engram content, file paths, org docs
    - prompts or responses
    - API keys or any user-identifiable data

Config (priority order):
    1. Env var NUCLEUS_ANON_TELEMETRY=false  (highest — overrides everything)
    2. .brain/config/nucleus.yaml → telemetry.anonymous.enabled: false
    3. Default: enabled (opt-out model)

Opt out:
    nucleus config --no-telemetry

NOTE FOR FUTURE-SELF (AND AI TOOLS):
    This module is part of the "danger set" (telemetry kernel powering autonomy).
    - Do not auto-apply large refactors from code assistants without reading the diff.
    - Always run `pytest tests/test_pre_launch_validation.py` after modifying this file.
    - Treat changes here as proposals that may impact safety, privacy, or rollout behavior.
"""

import json
import logging
import os
import platform
import sys
import threading
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.anon_telemetry")

# ── Constants ────────────────────────────────────────────────────
_DEFAULT_ENDPOINT = "https://telemetry.nucleusos.dev"
_FIRST_RUN_MARKER = ".nucleus_telemetry_notice_shown"

# ── Module-level cache ───────────────────────────────────────────
_config_checked = False
_enabled_cache: Optional[bool] = None
_pending_spans: list = []
_lock = threading.Lock()


# ── Config helpers ───────────────────────────────────────────────

def _read_yaml_config() -> dict:
    """Read nucleus.yaml config, return empty dict on failure."""
    try:
        import yaml  # noqa: delayed import to avoid hard dep
    except ImportError:
        return {}
    brain = os.environ.get("NUCLEAR_BRAIN_PATH", "")
    candidates = [
        Path(brain) / ".brain" / "config" / "nucleus.yaml" if brain else None,
        Path.home() / ".brain" / "config" / "nucleus.yaml",
        Path.cwd() / ".brain" / "config" / "nucleus.yaml",
    ]
    for p in candidates:
        if p and p.exists():
            try:
                return yaml.safe_load(p.read_text()) or {}
            except Exception:
                pass
    return {}


def _get_endpoint() -> str:
    """Get the anonymous telemetry endpoint."""
    env = os.environ.get("NUCLEUS_ANON_TELEMETRY_ENDPOINT", "").strip()
    if env:
        return env
    cfg = _read_yaml_config()
    return (
        cfg.get("telemetry", {})
        .get("anonymous", {})
        .get("endpoint", _DEFAULT_ENDPOINT)
    )


def is_anon_telemetry_enabled() -> bool:
    """Check if anonymous telemetry is enabled.

    Priority: env var > yaml config > default (True).
    """
    global _config_checked, _enabled_cache

    # Fast path: already resolved
    if _config_checked and _enabled_cache is not None:
        return _enabled_cache

    # 1. Env var override (highest priority)
    env = os.environ.get("NUCLEUS_ANON_TELEMETRY", "").strip().lower()
    if env in ("false", "0", "no", "off"):
        _config_checked = True
        _enabled_cache = False
        return False
    if env in ("true", "1", "yes", "on"):
        _config_checked = True
        _enabled_cache = True
        return True

    # 2. YAML config
    cfg = _read_yaml_config()
    yaml_val = cfg.get("telemetry", {}).get("anonymous", {}).get("enabled")
    if yaml_val is not None:
        _config_checked = True
        _enabled_cache = bool(yaml_val)
        return _enabled_cache

    # 3. Default: enabled
    _config_checked = True
    _enabled_cache = True
    return True


def reset_anon_telemetry_state():
    """Reset cached config state so next call re-reads config."""
    global _config_checked, _enabled_cache
    _config_checked = False
    _enabled_cache = None


def _get_nucleus_version() -> str:
    """Get installed nucleus version."""
    try:
        from importlib.metadata import version
        return version("nucleus-mcp")
    except Exception:
        return "unknown"


def _get_static_attributes() -> dict:
    """Static attributes included on every span."""
    return {
        "nucleus.version": _get_nucleus_version(),
        "python.version": platform.python_version(),
        "os.platform": sys.platform,
        "os.arch": platform.machine(),
    }


# ── OTLP Span Construction ──────────────────────────────────────

def _build_otlp_span(
    command: str,
    category: str,
    duration_ms: float,
    error_type: Optional[str] = None,
) -> dict:
    """Build a minimal OTLP JSON span for a single command invocation."""
    now_ns = int(time.time() * 1e9)
    start_ns = now_ns - int(duration_ms * 1e6)
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]

    attributes = [
        {"key": "nucleus.command", "value": {"stringValue": command}},
        {"key": "nucleus.category", "value": {"stringValue": category}},
        {"key": "nucleus.duration_ms", "value": {"doubleValue": duration_ms}},
    ]

    # Add static attributes
    for k, v in _get_static_attributes().items():
        attributes.append({"key": k, "value": {"stringValue": str(v)}})

    if error_type:
        attributes.append(
            {"key": "nucleus.error_type", "value": {"stringValue": error_type}}
        )

    status = {"code": 2, "message": error_type} if error_type else {"code": 1}

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": "nucleus-anon"},
                        }
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "nucleus.anon_telemetry", "version": "1.0.0"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": command,
                                "kind": 3,  # SPAN_KIND_CLIENT
                                "startTimeUnixNano": str(start_ns),
                                "endTimeUnixNano": str(now_ns),
                                "attributes": attributes,
                                "status": status,
                            }
                        ],
                    }
                ],
            }
        ]
    }


# ── Send Logic (fire-and-forget in background thread) ────────────

def _send_span(span_data: dict):
    """Send a single OTLP JSON span to the telemetry endpoint."""
    endpoint = _get_endpoint()
    url = f"{endpoint}/v1/traces"
    body = json.dumps(span_data).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"nucleus-anon/{_get_nucleus_version()}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            _ = resp.read()
            logger.debug("Telemetry span sent (%d bytes)", len(body))
    except Exception as exc:
        logger.debug("Telemetry send failed (non-blocking): %s", exc)


def _send_in_background(span_data: dict):
    """Fire-and-forget: send span in a daemon thread."""
    t = threading.Thread(target=_send_span, args=(span_data,), daemon=True)
    t.start()
    with _lock:
        _pending_spans.append(t)


# ── Public API ───────────────────────────────────────────────────

def record_anon_command(
    command: str,
    category: str,
    duration_ms: float,
    error_type: Optional[str] = None,
):
    """Record a single command invocation as anonymous telemetry.

    This is the main entry point called by _dispatch.py and cli.py.
    Fire-and-forget: never blocks, never raises.
    """
    if not is_anon_telemetry_enabled():
        return

    try:
        span = _build_otlp_span(command, category, duration_ms, error_type)
        _send_in_background(span)
    except Exception:
        pass  # Never let telemetry break the user's workflow


def shutdown_anon_telemetry(timeout: float = 2.0):
    """Wait for pending telemetry spans to flush (called before CLI exit)."""
    with _lock:
        threads = list(_pending_spans)
        _pending_spans.clear()

    for t in threads:
        t.join(timeout=timeout)


def show_first_run_notice():
    """Show a one-time notice about anonymous telemetry on first run.

    Creates a marker file so the notice is only shown once.
    """
    if not is_anon_telemetry_enabled():
        return

    brain = os.environ.get("NUCLEAR_BRAIN_PATH", "")
    marker_candidates = [
        Path(brain) / _FIRST_RUN_MARKER if brain else None,
        Path.home() / _FIRST_RUN_MARKER,
    ]

    for marker in marker_candidates:
        if marker and marker.exists():
            return  # Already shown

    # Show the notice
    print(
        "\n"
        "  📡 Nucleus sends anonymous usage telemetry to improve the product.\n"
        "     What's sent: command names, durations, version info.\n"
        "     What's NEVER sent: content, prompts, API keys, file paths.\n"
        "     Opt out: export NUCLEUS_ANON_TELEMETRY=false\n"
        "     Details: https://github.com/eidetic-works/nucleus-mcp#telemetry\n"
    )

    # Create marker
    for marker in marker_candidates:
        if marker:
            try:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.touch()
                return
            except Exception:
                continue
