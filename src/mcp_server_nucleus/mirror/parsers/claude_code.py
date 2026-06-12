"""Claude Code session-JSONL parser.

Empirically determined from
``~/.claude/projects/<project-slug>/<session-uuid>.jsonl`` on macOS
(2026-05-21, Claude Code CLI 1.x):

- Each line is a JSON object. Multiple types coexist in one file:

  * ``user`` — message envelope with ``role: "user"``; ``content`` is either a
    string (typed prompt) or a list of structured blocks (slash-command
    expansions, tool results, image attachments).
  * ``assistant`` — ``content`` is a list of blocks (``text``, ``thinking``,
    ``tool_use``); model identifier in ``message.model``.
  * ``attachment`` — file/image attachment metadata; emitted as a system event
    with the attachment filename as content.
  * ``queue-operation`` — internal queue ops (PUSH/POP/...); emitted as system
    event for completeness (filtered downstream if not needed).
  * ``last-prompt`` — pointer record only; skipped.

- Common envelope keys: ``uuid``, ``parentUuid``, ``timestamp`` (ISO-8601 UTC),
  ``sessionId``, ``type``.

- Line ordering is monotonic by ``timestamp`` but the parser does not assume
  sort — emits in file order.

- Per memory ``feedback_never_prune_claude_paths.md``: parsing is READ-ONLY.
  We never open these files for writing. The watcher (``claude_code_watcher``)
  enforces the same contract.

Version tolerance: unknown ``type`` values are emitted as ``role="system"`` with
the type string in ``extra["envelope_type"]`` so future schema changes don't
silently drop data.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Iterator, Optional

from . import EngramEvent


def _extract_text_from_blocks(blocks: Any) -> str:
    """Assistant ``content`` is a list of {type, ...} dicts; concatenate text +
    thinking blocks. Tool-use blocks are summarized as
    ``[tool_use: <name>(<input_summary>)]``."""
    if not isinstance(blocks, list):
        return ""
    chunks = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        btype = b.get("type")
        if btype == "text":
            t = b.get("text")
            if isinstance(t, str):
                chunks.append(t)
        elif btype == "thinking":
            t = b.get("thinking")
            if isinstance(t, str):
                chunks.append(f"[thinking]\n{t}\n[/thinking]")
        elif btype == "tool_use":
            name = b.get("name") or "?"
            inp = b.get("input")
            inp_summary = ""
            if isinstance(inp, dict):
                # Compact summary; full input is verbose
                keys = list(inp.keys())[:3]
                inp_summary = ", ".join(keys)
            chunks.append(f"[tool_use: {name}({inp_summary})]")
        elif btype == "tool_result":
            # Embedded tool_result inside an assistant block (rare)
            c = b.get("content")
            if isinstance(c, str):
                chunks.append(f"[tool_result]\n{c}\n[/tool_result]")
    return "\n".join(c for c in chunks if c).strip()


def _extract_user_content(content: Any) -> str:
    """User ``content`` may be a string OR a list (when slash commands expand
    or tool_results are embedded)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                itype = item.get("type")
                if itype == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        chunks.append(t)
                elif itype == "tool_result":
                    c = item.get("content")
                    if isinstance(c, str):
                        chunks.append(f"[tool_result]\n{c}\n[/tool_result]")
                    elif isinstance(c, list):
                        for sub in c:
                            if isinstance(sub, dict):
                                st = sub.get("text")
                                if isinstance(st, str):
                                    chunks.append(st)
                elif itype == "image":
                    src = item.get("source", {})
                    media = src.get("media_type") if isinstance(src, dict) else "?"
                    chunks.append(f"[image: {media}]")
        return "\n".join(c for c in chunks if c).strip()
    return ""


def parse_session_file(path: pathlib.Path) -> Iterator[EngramEvent]:
    """Yield ``EngramEvent`` for each line in the Claude Code session JSONL.

    READ-ONLY: opens the file in read mode only. Never writes.
    Tolerates malformed lines (skipped silently). Empty files yield nothing.
    """
    try:
        # Explicit read-only mode satisfies the memory contract on .claude/
        f = path.open("r", encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(d, dict):
                continue

            envelope_type = d.get("type")
            timestamp = d.get("timestamp") if isinstance(d.get("timestamp"), str) else None
            session_id = d.get("sessionId") if isinstance(d.get("sessionId"), str) else None
            uuid = d.get("uuid") if isinstance(d.get("uuid"), str) else None

            base_extra = {
                "envelope_type": envelope_type,
                "uuid": uuid,
                "parent_uuid": d.get("parentUuid"),
            }

            if envelope_type == "user":
                msg = d.get("message")
                if not isinstance(msg, dict):
                    continue
                text = _extract_user_content(msg.get("content"))
                if not text:
                    continue
                yield EngramEvent(
                    surface="claude_code",
                    role="user",
                    content=text,
                    timestamp=timestamp,
                    session_id=session_id,
                    source_path=str(path),
                    extra=base_extra,
                )
            elif envelope_type == "assistant":
                msg = d.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                text = _extract_text_from_blocks(content) if isinstance(content, list) else (
                    content.strip() if isinstance(content, str) else ""
                )
                if not text:
                    continue
                extra = dict(base_extra)
                if isinstance(msg.get("model"), str):
                    extra["model"] = msg["model"]
                yield EngramEvent(
                    surface="claude_code",
                    role="assistant",
                    content=text,
                    timestamp=timestamp,
                    session_id=session_id,
                    source_path=str(path),
                    extra=extra,
                )
            elif envelope_type == "attachment":
                att = d.get("attachment")
                name: Optional[str] = None
                if isinstance(att, dict):
                    name = att.get("filename") or att.get("path") or att.get("name")
                if not isinstance(name, str):
                    continue
                yield EngramEvent(
                    surface="claude_code",
                    role="system",
                    content=f"[attachment: {name}]",
                    timestamp=timestamp,
                    session_id=session_id,
                    source_path=str(path),
                    extra=base_extra,
                )
            elif envelope_type == "last-prompt":
                # Pointer record, no content; skip.
                continue
            elif envelope_type == "queue-operation":
                # Internal queue state; useful for debugging only. Skip by default.
                continue
            else:
                # Unknown envelope type — emit as system event with whatever
                # text-ish payload we can find, so future schema additions are
                # captured rather than silently dropped.
                text_blob = ""
                msg = d.get("message")
                if isinstance(msg, dict):
                    c = msg.get("content")
                    if isinstance(c, str):
                        text_blob = c.strip()
                    elif isinstance(c, list):
                        text_blob = _extract_text_from_blocks(c)
                if not text_blob:
                    continue
                yield EngramEvent(
                    surface="claude_code",
                    role="system",
                    content=text_blob,
                    timestamp=timestamp,
                    session_id=session_id,
                    source_path=str(path),
                    extra=base_extra,
                )


__all__ = ["parse_session_file"]
