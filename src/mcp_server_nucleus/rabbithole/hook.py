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
import re
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

    Supports both Claude Code (Read, Grep, Edit, Write, Bash) and
    Devin (read, grep, glob, edit, exec) tool-name dialects.
    """
    # Claude Code tool names
    if tool_name in ("Read", "Grep"):
        return "read"
    if tool_name in ("Edit", "Write", "NotebookEdit"):
        return "write"
    if tool_name == "Bash":
        return _classify_bash(tool_input.get("command") or "")
    # Devin tool names
    if tool_name in ("read", "grep", "glob"):
        return "read"
    if tool_name == "edit":
        return "write"
    if tool_name == "exec":
        return _classify_bash(tool_input.get("command") or "")
    return "neutral"


def _classify_bash(cmd: str) -> str:
    """Classify a Bash command as ``'read'``, ``'write'``, or ``'neutral'``.

    A command whose first token is in the known-read-only set AND that
    contains no stdout-redirection (``>``, ``>>`` but NOT ``2>``, ``2>>``,
    ``&>``, ``&>>``) is read-only.  Everything else is treated as a
    write/run command that resets depth.
    """
    cmd = cmd.strip()
    if not cmd:
        return "neutral"
    # Handle absolute paths like /bin/grep → take basename
    first_token = cmd.split()[0].rsplit("/", 1)[-1]
    # Strip stderr/both redirects (2>, 2>>, &>, &>>) before checking for stdout redirect
    cmd_no_stderr = re.sub(r'[2&]>>{0,1}', '', cmd)
    if first_token in _READ_BASH_FIRST_WORDS and ">" not in cmd_no_stderr:
        return "read"
    return "write"


def _extract_target(tool_name: str, tool_input: dict) -> str:
    """Return a short human-readable label for the thing being read."""
    if tool_name in ("Read", "read"):
        fp = tool_input.get("file_path") or ""
        return fp.rsplit("/", 1)[-1] or fp or "?"
    if tool_name in ("Grep", "grep"):
        pattern = tool_input.get("pattern") or ""
        path = (tool_input.get("path") or "").rsplit("/", 1)[-1]
        if pattern:
            return f"grep:{pattern[:30]}"
        return path or "?"
    if tool_name == "glob":
        pattern = tool_input.get("pattern") or ""
        path = (tool_input.get("path") or "").rsplit("/", 1)[-1]
        if pattern:
            return f"glob:{pattern[:30]}"
        return path or "?"
    if tool_name in ("Bash", "exec"):
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


# ---------------------------------------------------------------------------
# Pattern detection (zero-token heuristics on the read streak)
# ---------------------------------------------------------------------------

# Extensions that indicate "reading docs/specs" rather than "reading code".
_DOC_EXTENSIONS: frozenset[str] = frozenset({
    ".md", ".txt", ".rst", ".pdf", ".doc", ".docx",
    ".adoc", ".org", ".tex", ".rtf",
})


def _topic_stem(target: str) -> str:
    """Reduce a streak target to a rough topic token for clustering.

    Streak entries are short labels produced by ``_extract_target``:
    basenames (``auth.py``), grep patterns (``grep:TODO``), or bash
    prefixes (``cat config.yml``). We strip extension / common prefixes
    so that ``auth.py``, ``auth_test.py``, ``oauth.py`` all share the
    ``auth`` / ``oauth`` stems — close enough for the deep-dive heuristic.
    """
    t = target.strip().lower()
    if t.startswith("grep:"):
        t = t[5:]
    # Take the first whitespace-delimited token (handles "cat config.yml" → "config.yml")
    t = t.split()[0] if t else t
    # Strip extension
    for ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java",
                ".rb", ".php", ".c", ".h", ".cpp", ".hpp", ".cs", ".swift",
                ".kt", ".scala", ".clj", ".ex", ".exs", ".erl", ".hs",
                ".ml", ".nim", ".zig", ".v", ".sh", ".bash", ".zsh",
                ".yml", ".yaml", ".toml", ".json", ".ini", ".cfg",
                ".md", ".txt", ".rst", ".pdf", ".html", ".css", ".vue",
                ".svelte", ".sql", ".proto", ".thrift"):
        if t.endswith(ext):
            t = t[: -len(ext)]
            break
    # Take the first underscore/hyphen-delimited segment as the topic stem.
    # So auth_oauth.py → auth, jwt_helper.py → jwt, docker-compose.yml → docker.
    for sep in ("_", "-"):
        if sep in t:
            t = t.split(sep, 1)[0]
            break
    return t or target


def _classify_pattern(streak: list) -> str:
    """Classify the read streak into ``deep_dive`` / ``thrashing`` / ``research_spiral``.

    Zero-token heuristics on the streak labels:
    * ``deep_dive``       — ≤2 unique topic stems (going deeper on one thing)
    * ``research_spiral`` — >60% of targets are docs/specs (reading theory)
    * ``thrashing``       — ≥4 unique topic stems (bouncing, no focus)
    * ``unknown``         — fallback (short or ambiguous streak)
    """
    if not streak or len(streak) < 3:
        return "unknown"

    # Research spiral: mostly docs
    doc_count = sum(
        1 for t in streak
        if any(t.lower().endswith(ext) for ext in _DOC_EXTENSIONS)
    )
    if doc_count > len(streak) * 0.6:
        return "research_spiral"

    # Topic clustering
    stems = [_topic_stem(t) for t in streak]
    unique = set(s for s in stems if s)
    if len(unique) <= 2:
        return "deep_dive"
    if len(unique) >= 4:
        return "thrashing"
    return "unknown"


# ---------------------------------------------------------------------------
# Output builder — intelligent, zero-token
# ---------------------------------------------------------------------------

def _build_output(depth: int, streak: list, danger: int, rabbithole: int) -> dict:
    """Build the hook-output JSON dict with a contextual nudge.

    Two channels (per the Claude Code hook contract):
    * top-level ``systemMessage``        → shown to the HUMAN operator
    * ``hookSpecificOutput.additionalContext`` → injected into the MODEL's
      context so the agent can self-rescue (imperative instruction)
    """
    if depth >= rabbithole:
        bar = "#" * min(depth, 20)
        level = "RABBIT HOLE"
    else:
        bar = "#" * min(depth, 15)
        level = "DANGER"

    pattern = _classify_pattern(streak)
    recent = streak[-5:]
    files_str = ", ".join(recent) if recent else "?"

    # --- Human channel: contextual diagnosis + suggested action ---
    sys_msg = _human_message(depth, level, pattern, recent, files_str)

    # --- Model channel: imperative self-rescue instruction ---
    additional = _model_instruction(depth, level, pattern, streak)

    return {
        # Top-level: shown to the HUMAN operator. Per the Claude Code hook
        # contract, ``systemMessage`` is only recognized at the top level —
        # nested inside ``hookSpecificOutput`` it is an unrecognized field and
        # is silently dropped, so the human would never see the nudge.
        "systemMessage": sys_msg,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            # Injected into the model's context so the agent can self-resurface.
            "additionalContext": additional,
        },
    }


def _human_message(depth: int, level: str, pattern: str,
                   recent: list, files_str: str) -> str:
    """Build the human-visible nudge — diagnosis + suggested action."""
    prefix = f"[{('#' * min(depth, 20))}] {depth} reads, no edits ({level})"

    if pattern == "deep_dive":
        topic = _topic_stem(recent[-1]) if recent else "?"
        return (
            f"{prefix} — deep dive on {topic} ({files_str}). "
            f"You probably have enough context. Write the fix, "
            f"or save this thread with add_loop."
        )
    if pattern == "thrashing":
        return (
            f"{prefix} — thrashing across {files_str}. "
            f"This isn't a deep dive — you're bouncing. Pick one thing."
        )
    if pattern == "research_spiral":
        return (
            f"{prefix} — research spiral, mostly docs ({files_str}). "
            f"You have enough theory. Go write the code."
        )
    # unknown / short streak — fall back to the static shape
    return (
        f"{prefix} — still on your original task? (files: {files_str})"
    )


def _model_instruction(depth: int, level: str, pattern: str,
                       streak: list) -> str:
    """Build the model-facing imperative self-rescue instruction.

    This is the message that makes the agent rescue itself — it tells the
    model exactly what to do, not just what's happening.
    """
    recent_str = ", ".join(streak[-10:]) if streak else "?"

    if pattern == "deep_dive":
        action = (
            "STOP reading. You have enough context on this topic. "
            "Do one of NOW (do not read another file first): "
            "(1) write the code you already have context for; "
            "(2) call depth_pop to resurface to the parent task; "
            "(3) call add_loop to save this thread and move on."
        )
    elif pattern == "thrashing":
        action = (
            "STOP. You are thrashing — reading unrelated files without focus. "
            "State your current hypothesis in one sentence, then either "
            "write code or call depth_pop. Do not read another file."
        )
    elif pattern == "research_spiral":
        action = (
            "STOP reading docs. You have enough theory. "
            "Write the code now, or call depth_pop to resurface. "
            "Do not open another doc/spec file."
        )
    else:
        action = (
            "STOP. Call depth_show or depth_pop to resurface, "
            "or write the code you have context for. "
            "Do not read another file without doing one of these."
        )

    return (
        f"RABBIT HOLE DETECTED: {depth} consecutive reads, 0 edits ({level}). "
        f"Pattern: {pattern}. Recent targets: {recent_str}. "
        f"{action}"
    )


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
