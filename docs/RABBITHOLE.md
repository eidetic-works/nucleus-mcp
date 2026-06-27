# nucleus-rabbithole — Rabbit-Hole Depth Tracker

A standalone MCP tool that ships inside `nucleus-mcp` and solves one specific
problem: **you open one file, spot a bug, need to understand a helper, which
needs to read a spec, which needs a definition lookup — and suddenly you are
five levels deep with no memory of where you started.**

`nucleus-rabbithole` gives Claude Code (or any MCP client) a push/pop
depth stack, a context-switch thrash detector, an open-loop externaliser,
and a weekly review — all backed by a local SQLite file, no network, no
daemon.

---

## The problem

ADHD-style rabbit-holing during coding sessions:

1. You start on Task A.
2. You push into sub-task B to unblock A.
3. B needs C.
4. C surfaces D.
5. You forget A exists.

The depth stack makes this visible in real time. The thrash detector fires
when you switch context too many times inside a short window. The loop list
lets you externalise "I was in the middle of X" so it stops living
rent-free in working memory.

---

## Install

`nucleus-rabbithole` is bundled with `nucleus-mcp` — no separate package:

```bash
pip install nucleus-mcp
```

Run the server once to confirm it starts:

```bash
nucleus-rabbithole
```

---

## Claude Code MCP config

Add to your project `.mcp.json` (or `~/.claude/mcp.json` for global use):

```json
{
  "mcpServers": {
    "nucleus-rabbithole": {
      "command": "nucleus-rabbithole",
      "args": []
    }
  }
}
```

If `nucleus-rabbithole` is not on `$PATH` (e.g. installed in a venv), use
the full path:

```json
{
  "mcpServers": {
    "nucleus-rabbithole": {
      "command": "/path/to/venv/bin/nucleus-rabbithole",
      "args": []
    }
  }
}
```

Alternatively, invoke via Python:

```json
{
  "mcpServers": {
    "nucleus-rabbithole": {
      "command": "python",
      "args": ["-m", "mcp_server_nucleus.rabbithole"]
    }
  }
}
```

---

## Tools

### Depth stack

| Tool | Args | What it does |
|------|------|--------------|
| `depth_push` | `topic: str` | Push a new dive onto the stack. Warns at CAUTION / DANGER ZONE / RABBIT HOLE. |
| `depth_pop` | — | Pop the current dive, resurface to the previous level. |
| `depth_show` | — | Show the live stack (root → current). |
| `depth_map` | — | Show the full session tangent tree including already-popped dives. |

Default max depth is 4. Override with `RABBITHOLE_MAX_DEPTH=6`.

### Context-switch thrash detector

| Tool | Args | What it does |
|------|------|--------------|
| `switch_context` | `to: str` | Record a context switch. Nudges when switches in the recent window exceed the threshold. |

Defaults: 30-minute window, threshold 5 switches.
Override with `RABBITHOLE_SWITCH_WINDOW_MINUTES` and `RABBITHOLE_SWITCH_THRESHOLD`.

### Open loops

| Tool | Args | What it does |
|------|------|--------------|
| `add_loop` | `desc: str` | Externalise a started-but-unfinished thing. |
| `list_loops` | `include_closed: bool = false` | List open loops (optionally closed ones too). |
| `close_loop` | `id: int` | Close a loop by id. |

### Weekly review

| Tool | Args | What it does |
|------|------|--------------|
| `weekly_review` | `days: int = 7` | Narrative summary: threads touched, context-switch count, open loops, loops closed. |

---

## Data location

SQLite store: `$XDG_DATA_HOME/rabbithole/store.db`
Fallback:     `~/.local/share/rabbithole/store.db`

Point at a different file with `RABBITHOLE_DB_PATH` (the `connect()` function
in `store.py` accepts an explicit `db_path` argument for programmatic use).

---

## Optional: context-switch hook for Claude Code

Wire `switch_context` into Claude Code's `PostToolUse` hook so every tool
call that changes your working file is recorded automatically. Create
`.claude/hooks/rabbithole_switch.py`:

```python
"""PostToolUse hook — records context switches into nucleus-rabbithole store."""
import json
import sys

payload = json.load(sys.stdin)
tool = payload.get("tool_name", "")
# Only record file-touching tools
if tool not in {"Read", "Edit", "Write", "Bash"}:
    sys.exit(0)

# Extract a short label from the tool input
inp = payload.get("tool_input", {})
label = inp.get("file_path") or inp.get("command", "")[:60] or tool

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[2] / "src"))
from mcp_server_nucleus.rabbithole import store

conn = store.connect()
store.switch_context(conn, label)
conn.close()
```

Then register it in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {"type": "command", "command": "python .claude/hooks/rabbithole_switch.py"}
        ]
      }
    ]
  }
}
```

---

## Proactive auto-depth hook (opt-in)

The `rabbithole/hook.py` module makes rabbit-hole detection **proactive**:
it watches the live tool-call stream and surfaces a visible depth indicator
**without Claude having to call any tool**.

### What it does

On every `PostToolUse` event the hook:

1. **Classifies** the tool call as `read`, `write`, or `neutral`:
   - **read** — `Read`, `Grep`, read-only Bash (`cat`/`grep`/`ls`/`find`/…)
   - **write** — `Edit`, `Write`, Bash with side-effects or output redirection
   - **neutral** — MCP tools, `WebFetch`, `WebSearch`, etc. (no change)
2. **Increments** a per-session read-depth counter on reads; **resets** it to
   zero on writes (a write means real progress was made).
3. **Emits** a `systemMessage` visible to both the user and Claude when the
   counter crosses a configurable threshold.

The message looks like:

```
[##########] 10 reads deep with no edit (DANGER) — still on your original task? (files: store.py, hook.py, server.py…)
```

### Thresholds (env-configurable)

| Env var | Default | Meaning |
|---------|---------|---------|
| `RABBITHOLE_DEPTH_CAUTION` | `6` | Tracked internally; not alerted by default |
| `RABBITHOLE_DEPTH_DANGER` | `10` | First user-visible alert |
| `RABBITHOLE_DEPTH_RABBITHOLE` | `15` | Escalated alert with `RABBIT HOLE` label |

The hook fires at **exact** threshold crossings (`depth == 10`, `depth == 15`)
and then every 5 reads above the rabbithole threshold (20, 25, …).  Between
crossings it is silent so it does not nag.

### Enable / disable

```bash
# Silence for this shell session
export RABBITHOLE_HOOK_DISABLED=1

# Lower thresholds for a focused sprint
export RABBITHOLE_DEPTH_DANGER=6
export RABBITHOLE_DEPTH_RABBITHOLE=10
```

### Wire-up: add to `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read|Grep|Bash|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python -m mcp_server_nucleus.rabbithole.hook"
          }
        ]
      }
    ]
  }
}
```

If `nucleus-mcp` is installed in a venv, use the venv's Python:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read|Grep|Bash|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/venv/bin/python -m mcp_server_nucleus.rabbithole.hook"
          }
        ]
      }
    ]
  }
}
```

A copy of the exact JSON stanza lives at
`src/mcp_server_nucleus/rabbithole/hooks.json` for easy copy-paste.

### Auto-depth state in the store

The hook writes per-session depth state into the **same** SQLite store as
the manual `depth_push` / `depth_pop` tools, using the `hook_state` table.
This means `weekly_review` and `depth_map` will include dives that were
auto-detected (though they appear as depth-counter events, not named frames).

### Fail-safe guarantees

- Any exception is swallowed; the hook **always** exits 0.
- Startup cost for neutral tools (MCP, WebFetch, …) is sub-millisecond
  because the SQLite import is lazy.
- Parallel hook invocations on the same session are safe: state updates use
  SQLite `ON CONFLICT DO UPDATE` (UPSERT), serialised by the database engine.

### False-positive risk

The Bash classifier is heuristic-based.  Commands whose first token is in the
read-only set (`cat`, `grep`, `ls`, `find`, `head`, `tail`, `wc`, `diff`,
`stat`, `file`, `echo`, `which`, `type`, `less`, `sort`, `uniq`, `cut`,
`du`, `df`, `pwd`, `date`) **without** a `>` redirection are treated as
read-only.  Anything else is treated as a write.

Known false positives:
- `git log`, `git status`, `git diff` → classified as **write** (resets
  counter). In practice this is fine: seeing git output often means you
  paused to check state, which is not rabbit-holing.
- `python -m py_compile foo.py` → classified as **write**. No impact beyond
  a premature reset.

Known false negatives (rare):
- A Bash read command that spawns a subprocess writing to disk (e.g. a
  `cat` piped through a custom script that writes) will increment the counter
  rather than reset it.

At the default `danger=10` threshold these edge cases are unlikely to cause
meaningful noise.

---

## Import independence

`nucleus-rabbithole` is a self-contained subpackage. It imports only stdlib
and the `mcp` package (shipped by `fastmcp`, already a core dependency of
`nucleus-mcp`). The `hook.py` module additionally imports
`mcp_server_nucleus.rabbithole.store` (the same subpackage) and nothing
else from sibling modules. It will run correctly even if the rest of the
nucleus-mcp package is broken.
