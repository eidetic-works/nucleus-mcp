---
name: nucleus-brain
description: Persistent agent memory, task management, session state, and governance. The sovereign agent brain that speaks MCP + CLI + SDK.
homepage: https://nucleusos.dev
---

# Nucleus Brain — CLI Reference

Nucleus gives your agent persistent memory with built-in governance. Install with `pip install nucleus-mcp`, then initialize with `nucleus init`.

## Memory (Engrams)

```bash
nucleus engram search "auth"                    # Search memory
nucleus engram search "auth" --format json       # JSON for piping
nucleus engram search "auth" -q                  # Bare keys only
nucleus engram write my_key "insight" --context Strategy --intensity 8
nucleus engram query --context Decision --limit 10
```

## Tasks

```bash
nucleus task list --status READY                 # Filter by status
nucleus task list --format json | jq length      # Count tasks
nucleus task list -q                             # Bare task IDs
nucleus task add "Ship feature" --priority 1
nucleus task update task-abc123 --status DONE
```

## Sessions

```bash
nucleus session save "Working on auth module"
nucleus session resume                           # Most recent
nucleus session resume sess-abc123               # Specific session
```

## Growth & Outbound

```bash
nucleus growth pulse                             # Daily growth metrics
nucleus growth status --format json
nucleus outbound check reddit r/ClaudeAI         # Idempotency gate
nucleus outbound record reddit r/ClaudeAI --permalink https://reddit.com/abc
nucleus outbound plan                            # What's ready vs posted
```

## Output Formats

All commands support `--format json|table|tsv` and `-q`/`--quiet` for bare output. Default: table in terminal, JSON when piped.

## Errors

With `--format json`, errors return structured JSON: `{"ok": false, "error": "not_found", "message": "...", "exit_code": 3}`. Exit codes: 0=success, 1=error, 2=usage, 3=not found.
