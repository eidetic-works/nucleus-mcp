# Session-Registry Primitive (T3.11)

Agent presence + 3rd-writer detection for multi-agent Nucleus substrates.
Ships as the MCP primitive that lets Claude-Code, Cowork, Gemini-CLI, Windsurf,
and any future adapter declare liveness on a worktree without stepping on each
other's session-context snapshots.

## Surface

| MCP action            | Function                                      | Purpose                                                             |
| --------------------- | --------------------------------------------- | ------------------------------------------------------------------- |
| `register`            | `register_session(...)`                       | Create/replace a session envelope under the registry root.          |
| `heartbeat`           | `heartbeat(session_id)`                       | Refresh `last_heartbeat`; raises `FileNotFoundError` if unknown.    |
| `unregister`          | `unregister(session_id)`                      | Delete the envelope file. Idempotent.                               |
| `list_agents`         | `list_agents(worktree_path=, role=, alive_only=)` | List envelopes; filter by worktree, role, or liveness window.  |
| `detect_splits`       | `detect_splits(worktree_path=)`               | Report `(worktree, role)` buckets with more than one alive session. |

All five actions round-trip through `nucleus_sessions(action, params)` — no
new top-level tool.

## Envelope schema

```json
{
  "session_id":           "uuid-or-cowork-slug",
  "agent":                "claude_code | cowork | gemini_cli | windsurf | ...",
  "role":                 "primary | secondary | coordinator | worker | reviewer",
  "worktree_path":        "/abs/resolved/path (realpath, symlink-safe)",
  "pid":                  12345,
  "registered_at":        "2026-04-21T18:07:12.402091Z",
  "last_heartbeat":       "2026-04-21T18:07:42.101823Z",
  "heartbeat_interval_s": 30,
  "provider":             "claude_anthropic | google | openai | ...",
  "primitive_version":    "1"
}
```

`agent`, `role`, and `provider` are free strings. Generic role vocab keeps
ADR-0005's parametrize-across-AI contract intact.

## Storage

- **Write path:** `${NUCLEUS_AGENT_REGISTRY}` → fallback `brain_path() / "agent_registry"`.
- One file per session (`{session_id}.json`), atomic `os.replace` write-then-rename.
- Deliberately distinct from `.brain/sessions/` (owned by
  `nucleus_sessions.save/resume` for user-facing context snapshots) — additive
  migration with zero collision risk.

## Liveness

`now - last_heartbeat < 2 * heartbeat_interval_s`. Stale envelopes fall off
naturally without a GC pass; explicit `unregister` is the clean-shutdown path.

## Split detection

`detect_splits` groups alive envelopes by `(worktree_path, role)`. Two agents
claiming the same role on the same worktree is the 3rd-writer case — emit a
`split-brain-detected` envelope via the relay or the coordinator loop, up to
the caller.

## Primitive-gate audit

| Axis       | Status | Note                                                                           |
| ---------- | :----: | ------------------------------------------------------------------------------ |
| any-OS     |   ✓    | Pure stdlib (`json`, `os`, `pathlib`, `tempfile`, `datetime`).                 |
| any-user   |   ✓    | Path resolves through `paths.brain_path()`; no `/Users/*` hardcodes.           |
| any-agent  |   ✓    | `agent` is a free string — Codex / Gemini / Cursor register via the same call. |
| any-LLM    |   ✓    | `provider` is a free string; coercion lives in the ADR-0005 adapter layer.     |
| portable   |   ✓    | Realpath resolution handles symlinked worktree directories.                    |

## Caveats

- PID reuse across host reboots is possible; liveness is clock-based, not
  PID-based, so this is not a correctness gap.
- `session_id` slashes / path-traversal tokens are sanitized in the filename;
  the stored envelope keeps the raw id.
- No lock file — one-writer-per-filename removes the last-writer-wins class of
  bug. Two processes racing on the same `session_id` is already a split-brain
  case and is surfaced by `detect_splits`.
