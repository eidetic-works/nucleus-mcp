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

## Import independence

`nucleus-rabbithole` is a self-contained subpackage. It imports only stdlib
and the `mcp` package (shipped by `fastmcp`, already a core dependency of
`nucleus-mcp`). It does not import anything from sibling
`mcp_server_nucleus` modules and will run correctly even if the rest of the
nucleus-mcp package is broken.
