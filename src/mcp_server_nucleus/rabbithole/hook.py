"""
PostToolUse hook — auto-detects rabbit-holing from the tool-call stream.

Reads a ``PostToolUse`` JSON envelope from stdin, updates per-session depth
state in the rabbithole SQLite store, and prints a ``hookSpecificOutput``
JSON to stdout when depth crosses a configured threshold.

Usage (add to ``.claude/settings.json`` — see docs/RABBITHOLE.md):

    "hooks": {
      "PostToolUse": [
        {
          "matcher": "Read|Grep|Bash|Edit|Write",
          "hooks": [
            {"type": "command",
             "command": "python -m mcp_server_nucleus.rabbithole.hook"}
          ]
        }
      ]
    }

Env vars (all optional):
  RABBITHOLE_HOOK_DISABLED=1      Silently disable this hook (exit 0).
  RABBITHOLE_DEPTH_CAUTION=6      Caution level (tracked, not alerted by default).
  RABBITHOLE_DEPTH_DANGER=10      Danger level — surfaces a warning to the user.
  RABBITHOLE_DEPTH_RABBITHOLE=15  Full rabbit-hole level — stronger warning.
  RABBITHOLE_DB_PATH              Override the SQLite store path.

Import contract:
  This module imports ONLY stdlib and ``mcp_server_nucleus.rabbithole.store``.
  It does NOT import anything else from mcp_server_nucleus.

Fail-safe:
  Any uncaught exception is swallowed and the process exits 0.  The hook
  must never break the user's tool calls.
"""
from __future__ import annotations

import json
import os
import sys


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

_DEFAULT_CAUTION = 6
_DEFAULT_DANGER = 10
_DEFAULT_RABBITHOLE = 15

# Bash first-words that indicate a purely read/inspection operation.
# A command starting with one of these and containing no redirection (>)
# is classified as a read-only Bash call.
_READ_BASH_FIRST_WORDS: frozenset[str] = frozenset({
    "cat", "grep", "ls", "find", "head", "tail", "wc", "diff",
    "stat", "file", "echo", "which", "type", "less", "sort",
    "uniq", "cut", "du", "df", "pwd", "date",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _classify(tool_name: str, tool_input: dict) -> str:
    """Classify a tool call as ``'read'``, ``'write'``, or ``'neutral'``.

    * ``read``    — increments the depth counter
    * ``write``   — resets the depth counter to zero
    * ``neutral`` — no change (MCP tool calls, WebFetch, etc.)
    """
    if tool_name in ("Read", "Grep"):
        return "read"
    if tool_name in ("Edit", "Write", "NotebookEdit"):
        return "write"
    if tool_name == "Bash":
        return _classify_bash(tool_input.get("command") or "")
    return "neutral"


def _classify_bash(cmd: str) -> str:
    """Classify a Bash command as ``'read'``, ``'write'``, or ``'neutral'``.

    A command whose first token is in the known-read-only set AND that
    contains no output-redirection character (``>``) is read-only.
    Everything else is treated as a write/run command that resets depth.
    """
    cmd = cmd.strip()
    if not cmd:
        return "neutral"
    # Handle absolute paths like /bin/grep → take basename
    first_token = cmd.split()[0].rsplit("/", 1)[-1]
    if first_token in _READ_BASH_FIRST_WORDS and ">" not in cmd:
        return "read"
    return "write"


def _extract_target(tool_name: str, tool_input: dict) -> str:
    """Return a short human-readable label for the thing being read."""
    if tool_name == "Read":
        fp = tool_input.get("file_path") or ""
        return fp.rsplit("/", 1)[-1] or fp or "?"
    if tool_name == "Grep":
        pattern = tool_input.get("pattern") or ""
        path = (tool_input.get("path") or "").rsplit("/", 1)[-1]
        if pattern:
            return f"grep:{pattern[:30]}"
        return path or "?"
    if tool_name == "Bash":
        return (tool_input.get("command") or "")[:50]
    return tool_name


def _should_emit(depth: int, danger: int, rabbithole: int) -> bool:
    """Return True only at exact threshold crossings or every 5 reads above rabbithole.

    Thresholds:
    * ``depth == danger``         — first alert
    * ``depth == rabbithole``     — escalated alert
    * ``depth > rabbithole`` and ``(depth - rabbithole) % 5 == 0``  — periodic reminder
    """
    if depth == danger:
        return True
    if depth == rabbithole:
        return True
    if depth > rabbithole and (depth - rabbithole) % 5 == 0:
        return True
    return False


def _build_output(depth: int, streak: list, danger: int, rabbithole: int) -> dict:
    """Build the ``hookSpecificOutput`` JSON dict for the given depth."""
    if depth >= rabbithole:
        bar = "#" * min(depth, 20)
        level = "RABBIT HOLE"
    else:
        bar = "#" * min(depth, 15)
        level = "DANGER"

    recent = streak[-5:]
    files_str = ", ".join(recent) if recent else "?"

    sys_msg = (
        f"[{bar}] {depth} reads deep with no edit ({level})"
        f" — still on your original task? (files: {files_str})"
    )
    additional = (
        f"Auto-depth tracker: {depth} consecutive reads without an edit. "
        f"Recent targets: {', '.join(streak[-10:]) if streak else '?'}. "
        f"Call depth_show or depth_pop to resurface or inspect the stack."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "systemMessage": sys_msg,
            "additionalContext": additional,
        }
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Read one PostToolUse JSON envelope from stdin and act on it."""
    # Global kill switch — exit 0 silently
    if os.environ.get("RABBITHOLE_HOOK_DISABLED", "").strip() == "1":
        sys.exit(0)

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)

        session_id: str = payload.get("session_id") or "unknown"
        tool_name: str = payload.get("tool_name") or ""
        tool_input: dict = payload.get("tool_input") or {}

        classification = _classify(tool_name, tool_input)
        if classification == "neutral":
            sys.exit(0)

        # Lazy import — keeps startup overhead near-zero for neutral tools
        from mcp_server_nucleus.rabbithole import store  # noqa: PLC0415

        db_path = os.environ.get("RABBITHOLE_DB_PATH") or None
        conn = store.connect(db_path)
        try:
            if classification == "write":
                store.hook_reset(conn, session_id)
                # No output — a write/reset is not user-visible
            else:
                target = _extract_target(tool_name, tool_input)
                result = store.hook_increment(conn, session_id, target)
                danger = _env_int("RABBITHOLE_DEPTH_DANGER", _DEFAULT_DANGER)
                rabbithole = _env_int("RABBITHOLE_DEPTH_RABBITHOLE", _DEFAULT_RABBITHOLE)
                if _should_emit(result["depth"], danger, rabbithole):
                    out = _build_output(result["depth"], result["streak"], danger, rabbithole)
                    sys.stdout.write(json.dumps(out) + "\n")
                    sys.stdout.flush()
        finally:
            conn.close()

    except Exception:  # noqa: BLE001
        # Fail-safe: swallow every exception — the hook must never break
        # the user's tool calls.
        pass


if __name__ == "__main__":
    main()
