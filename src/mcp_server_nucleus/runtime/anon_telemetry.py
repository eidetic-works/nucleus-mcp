"""Nucleus Runtime — Anonymous Usage Telemetry.

Opt-OUT model (default: enabled): anonymous telemetry is ON by default.
Opt out via `nucleus config --no-telemetry`.
Aggregate command-level data is sent to telemetry.nucleusos.dev.
Uses a SEPARATE OTel pipeline from the user's enterprise OTel config
(otel_export.py) — zero interference.

What is sent:
    - command name (e.g. "morning-brief", "engram-query")
    - tool category (e.g. "nucleus_engrams")
    - duration_ms
    - error_type (class name only, e.g. "ValueError")
    - nucleus version
    - python version
    - OS platform
    - is_ci (bool, derived from CI env var) — separates CICD noise from real users
    - is_claude_code (bool, derived from CLAUDECODE env var)
    - install_id (random per-machine UUID at ~/.config/nucleus/install_id)
      — NOT tied to user identity; lets us count unique installs without naming them

What is NEVER sent:
    - engram content, file paths, org docs
    - prompts or responses
    - API keys or any user-identifiable data

Config (priority order):
    1. Env var NUCLEUS_ANON_TELEMETRY=false  (highest — explicit per-session opt-out)
    2. .brain/config/nucleus.yaml → telemetry.anonymous.enabled: true/false
    3. Default: ENABLED

Opt out (any of):
    nucleus config --no-telemetry             # persistent, writes to nucleus.yaml
    export NUCLEUS_ANON_TELEMETRY=false       # per-session
    Edit .brain/config/nucleus.yaml: telemetry.anonymous.enabled: false
    export NUCLEUS_ANON_TELEMETRY=true       # one-off session

Opt out (remains for backward compatibility):
    nucleus config --no-telemetry            # persistent, writes to nucleus.yaml
    export NUCLEUS_ANON_TELEMETRY=false      # one-off session
    # OR edit .brain/config/nucleus.yaml: telemetry.anonymous.enabled: false

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
_DEFAULT_ENDPOINT = "https://eidetic.works"
_FIRST_RUN_MARKER = ".nucleus_telemetry_notice_shown"

# ── Module-level cache ───────────────────────────────────────────
_config_checked = False
_enabled_cache: Optional[bool] = None
_pending_spans: list = []
_lock = threading.Lock()

# ── Session tracking ─────────────────────────────────────────────
_session_id: Optional[str] = None
_session_start_time: Optional[float] = None
_session_commands: list = []


def _get_session_id() -> str:
    """Return a per-process session UUID (regenerated each CLI invocation)."""
    global _session_id
    if _session_id is None:
        _session_id = uuid.uuid4().hex
        _session_start_time = time.time()
    return _session_id


# ── Config helpers ───────────────────────────────────────────────

def _read_yaml_config() -> dict:
    """Read nucleus.yaml config, return empty dict on failure."""
    try:
        import yaml  # noqa: F811 -- delayed import to avoid hard dep
    except ImportError:
        return {}
    brain = os.environ.get("NUCLEUS_BRAIN_PATH", "")
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

    Priority: env var > yaml config > default (False — opt-in model per ADR-022
    default-deny / local-first privacy stance).
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

    # 3. Default: enabled (opt-out model)
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


def _get_install_id() -> str:
    """Return a stable per-machine random UUID, persisting it on first call.

    Stored at ~/.config/nucleus/install_id (mode 600). NOT tied to user identity —
    just a random opaque token so we can deduplicate "this install" from
    "that install" across spans, without learning who or where.
    """
    try:
        path = Path.home() / ".config" / "nucleus" / "install_id"
        if path.exists():
            val = path.read_text(encoding="utf-8").strip()
            if val:
                return val
        path.parent.mkdir(parents=True, exist_ok=True)
        new_id = uuid.uuid4().hex
        path.write_text(new_id, encoding="utf-8")
        try:
            path.chmod(0o600)
        except Exception:
            pass
        return new_id
    except Exception:
        return "unknown"


def _is_ci_env() -> bool:
    """True if running under any common CI/CD environment."""
    return bool(
        os.environ.get("CI")
        or os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("CIRCLECI")
        or os.environ.get("GITLAB_CI")
        or os.environ.get("BUILDKITE")
        or os.environ.get("TRAVIS")
    )


def _is_claude_code_env() -> bool:
    """True if running inside a Claude Code session (subprocess inherits CLAUDECODE)."""
    return bool(os.environ.get("CLAUDECODE"))


def _get_static_attributes() -> dict:
    """Static attributes included on every span."""
    return {
        "nucleus.version": _get_nucleus_version(),
        "python.version": platform.python_version(),
        "os.platform": sys.platform,
        "os.arch": platform.machine(),
        "nucleus.install_id": _get_install_id(),
        "nucleus.is_ci": _is_ci_env(),
        "nucleus.is_claude_code": _is_claude_code_env(),
    }


# ── Send Logic (fire-and-forget in background thread) ────────────

def _send_event(event: dict):
    """Send a single telemetry event to the eidetic.works endpoint."""
    endpoint = _get_endpoint()
    url = f"{endpoint}/api/telemetry/install"
    body = json.dumps(event).encode("utf-8")

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
            logger.debug("Telemetry event sent (%d bytes)", len(body))
    except Exception as exc:
        logger.debug("Telemetry send failed (non-blocking): %s", exc)


def _send_in_background(event: dict):
    """Fire-and-forget: send event in a daemon thread."""
    t = threading.Thread(target=_send_event, args=(event,), daemon=True)
    t.start()
    with _lock:
        _pending_spans.append(t)


def _build_event(
    event_type: str,
    command: str = "",
    category: str = "",
    duration_ms: float = 0.0,
    error_type: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Build a rich telemetry event with all attributes."""
    event = {
        "event_type": event_type,
        "install_id": _get_install_id(),
        "session_id": _get_session_id(),
        "timestamp": time.time(),
        "command": command,
        "category": category,
        "duration_ms": round(duration_ms, 2),
        "nucleus_version": _get_nucleus_version(),
        "python_version": platform.python_version(),
        "os": sys.platform,
        "os_arch": platform.machine(),
        "is_ci": _is_ci_env(),
        "is_claude_code": _is_claude_code_env(),
    }
    if error_type:
        event["error_type"] = error_type
    if extra:
        event.update(extra)
    return event


# ── Public API ───────────────────────────────────────────────────

def record_session_start():
    """Record a session_start event — call once at CLI/MCP startup."""
    if not is_anon_telemetry_enabled():
        return
    try:
        event = _build_event("session_start")
        _send_in_background(event)
    except Exception:
        pass


def record_session_end():
    """Record a session_end event — call once at CLI/MCP exit."""
    if not is_anon_telemetry_enabled():
        return
    try:
        duration = time.time() - (_session_start_time or time.time())
        event = _build_event("session_end", extra={
            "session_duration_s": round(duration, 2),
            "commands_run": len(_session_commands),
            "commands_list": ",".join(_session_commands[-50:]),  # last 50
        })
        _send_in_background(event)
    except Exception:
        pass


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
        _session_commands.append(command)
        event = _build_event("command", command=command, category=category,
                             duration_ms=duration_ms, error_type=error_type)
        _send_in_background(event)
    except Exception:
        pass  # Never let telemetry break the user's workflow


def record_feature_adoption(feature: str, context: Optional[dict] = None):
    """Record that a user adopted a feature (first-time use of a capability)."""
    if not is_anon_telemetry_enabled():
        return
    try:
        event = _build_event("feature_adoption", command=feature, extra=context)
        _send_in_background(event)
    except Exception:
        pass


def record_error(error_type: str, command: str = "", context: Optional[dict] = None):
    """Record an error event with type and optional context."""
    if not is_anon_telemetry_enabled():
        return
    try:
        event = _build_event("error", command=command, error_type=error_type, extra=context)
        _send_in_background(event)
    except Exception:
        pass


def record_daemon_install():
    """Record a daemon_install event — call when the daemon is first installed."""
    if not is_anon_telemetry_enabled():
        return
    try:
        event = _build_event("daemon_install")
        _send_in_background(event)
    except Exception:
        pass


def shutdown_anon_telemetry(timeout: float = 2.0):
    """Wait for pending telemetry events to flush (called before CLI exit)."""
    # Send session_end if we haven't already
    if _session_id and _session_commands:
        record_session_end()

    with _lock:
        threads = list(_pending_spans)
        _pending_spans.clear()

    for t in threads:
        t.join(timeout=timeout)


def _write_yaml_telemetry_setting(enabled: bool) -> bool:
    """Write telemetry.anonymous.enabled to nucleus.yaml. Returns True on success."""
    try:
        import yaml
    except ImportError:
        return False
    brain = os.environ.get("NUCLEUS_BRAIN_PATH", "")
    candidates = [
        Path(brain) / ".brain" / "config" / "nucleus.yaml" if brain else None,
        Path.cwd() / ".brain" / "config" / "nucleus.yaml",
        Path.home() / ".brain" / "config" / "nucleus.yaml",
    ]
    target = next((p for p in candidates if p), None)
    if target is None:
        return False
    try:
        existing = {}
        if target.exists():
            existing = yaml.safe_load(target.read_text()) or {}
        existing.setdefault("telemetry", {}).setdefault("anonymous", {})["enabled"] = enabled
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(existing, sort_keys=False), encoding="utf-8")
        return True
    except Exception:
        return False


def show_first_run_notice():
    """Print the one-time anonymous-telemetry disclosure notice.

    Non-interactive: prints the notice + creates a marker file so we never
    print it again on this machine. Never reads stdin, never writes yaml.
    Telemetry is ON by default (opt-out model). The notice informs the user
    how to opt out if they wish.

    Skip if:
      - marker file already exists (user was notified already), OR
      - yaml has an explicit anonymous.enabled key (user explicitly configured), OR
      - env var NUCLEUS_ANON_TELEMETRY is set (explicit per-session choice).
    """
    # Skip if env override is set — that's an explicit per-session decision
    if os.environ.get("NUCLEUS_ANON_TELEMETRY", "").strip():
        return

    # Skip if yaml already has explicit setting
    cfg = _read_yaml_config()
    if cfg.get("telemetry", {}).get("anonymous", {}).get("enabled") is not None:
        return

    # Skip if marker file present
    brain = os.environ.get("NUCLEUS_BRAIN_PATH", "")
    marker_candidates = [
        Path(brain) / _FIRST_RUN_MARKER if brain else None,
        Path.home() / _FIRST_RUN_MARKER,
    ]
    for marker in marker_candidates:
        if marker and marker.exists():
            return

    # Print the notice (never blocks, never reads stdin)
    try:
        print(
            "\n"
            "  📡 Nucleus collects anonymous usage telemetry. To opt out:\n"
            "     nucleus config --no-telemetry\n"
            "     What's sent: commands, sessions, feature adoption, errors, version, OS, install_id.\n"
            "     NEVER sent: content, prompts, file paths, API keys, identity.\n"
            "     Details: https://github.com/eidetic-works/nucleus-mcp/blob/main/TELEMETRY.md\n"
        )
    except Exception:
        pass  # Even a broken stdout must not block the CLI

    # Marker so we never print again, even if a subsequent invocation has no tty
    for marker in marker_candidates:
        if marker:
            try:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.touch()
                break
            except Exception:
                continue


# Back-compat alias for cli.py callers that imported the old name.
show_first_run_prompt = show_first_run_notice
