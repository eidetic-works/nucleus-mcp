# Nucleus Agent Adapter Contract

> **Task:** T2.5 primitive-adapter-contract
> **Authority:** Cowork directive `relay_20260422_024202_cc959e20` (E)
> **Status:** Proposed (PR #140, awaiting multi-author conformance review)
> **Provenance:** `.brain/plans/substrate_2x_layer_audit_20260421.md` §T2.5

## Primitive-gate axes (mandatory for all conformant implementations)

Any agent CLI that implements this contract MUST pass all five axes:

- **any-computer:** filesystem + MCP-stdio, no machine-specific assumptions
- **any-OS:** POSIX + Windows both supported (no `/Users/*` hardcodes, use env vars)
- **any-user:** tenant-isolated via `$NUCLEUS_ROOT` / `$NUCLEUS_BRAIN` / `$NUCLEUS_TRANSCRIPT_ROOT`
- **any-agent:** instructions are LLM-invariant (no provider-specific prompt coupling)
- **any-LLM:** MCP tool calls are the interop boundary, not natural language

## The primitive contract

Any MCP-speaking agent CLI surfaces **three primitive actions** on the `nucleus_sync` tool facade per session:

1. **Inbox poll on session-start.** Before the agent takes its first user-facing action, it calls `nucleus_sync.relay_inbox(recipient=<self-role-token>, unread_only=True)` and surfaces the returned envelopes to its context.

2. **Ack on read.** For each envelope the agent processes, it calls `nucleus_sync.relay_ack(message_id=<id>, recipient=<self-role-token>)` so the substrate tag-log tracks read state.

3. **Send with explicit sender.** On every `nucleus_sync.relay_post` call, the agent passes `sender=<self-role-token>` explicitly. Reliance on `NUCLEUS_RELAY_INFER_SENDER` (R6.1) is forbidden until R6.1 lands on origin/main; even after, explicit sender is the canonical path.

### Required self-role-token registration

Before the first inbox poll, the agent MUST call `nucleus_sync.identify_agent` with the tuple form per ADR-0005 §D1:

```
nucleus_sync.identify_agent(
    role=<"primary"|"secondary"|"coordinator"|"worker"|"reviewer">,
    provider=<canonical-provider-token>,
    session_id=<cli-session-id>,
)
```

Legacy shape `{agent_id, environment, role}` is accepted during ADR-0005 §D5 grace period (until end of Cycle C+2, ~2026-09-18). After that, tuple form is mandatory.

### Required behavior under substrate errors

- **`nucleus_sync.relay_inbox` returns empty**: agent proceeds with user turn. No error surface required.
- **`nucleus_sync.relay_inbox` errors** (substrate down, malformed envelope): agent surfaces the error in its context + proceeds. Does not block the user.
- **`nucleus_sync.relay_ack` fails**: retry once with exponential backoff, then log + proceed. Unacked envelopes will re-surface next session — acceptable.
- **`nucleus_sync.relay_post` fails with `sender` rejection**: hard-fail the send; log "R6.1 sender-coercion expected". Do not silently retry without sender.

## Conformance implementation shapes

The primitive contract above is a substrate-level agreement. How each agent CLI surfaces the three actions depends on its extension model. Five shapes are documented below; adding a sixth is a new appendix, no contract change.

**Implementation authors: only your own appendix is authoritative. Conformance review is multi-author by design.** If the Gemini appendix's author (Gemini CLI maintainers or a Gemini-speaking session) disagrees with Windsurf's draft of that appendix, they write their own. Same for every other appendix.

---

## Appendix A — Gemini CLI (Context-File + Skill Injection)

> **Authorship:** authored by the Gemini CLI maintainer session (`gemini_cli`) per the multi-author-at-conformance-layer model. Landed via `relay_20260422_132626_ef294c35` (option A: authoritative markdown paste) in response to Windsurf's correction-request `relay_20260422_041429_c5274058`.

**Extension model:** `gemini.md` (root) or `GEMINI.md` (project) is loaded as the system prompt. Gemini CLI supports turn-invariant rules via `.google/gemini/rules/` and tool-adapter stubs via `.gemini/skills/` (per T1.2).

**Authoritative Turn-0 protocol (using the `check-inbox` skill):**

On turn-0 of any session, execute in this order:

1. Run the `check-inbox` skill at `.gemini/skills/check-inbox` to surface pending relays.
2. Surface a summary line per envelope (from / subject / tags) to the user.
3. Every `relay_post` MUST include explicit `sender="gemini_cli"` per R6.1.
4. Call `nucleus_sync.identify_agent` with role=`"primary"`, provider=`"google_gemini"`, session_id=`<current_id>`.

**Conformance-test:** cold-boot session with seeded envelope in `.brain/relay/gemini_cli/`. First message must include summary.

---

## Appendix B — Cursor (settings-based rules)

**Extension model:** Cursor ships with a rules system at `.cursor/rules/*.mdc`. MCP tools are invoked via Cursor's built-in MCP client. No pre-turn-hook; rules apply at prompt-assembly time.

**Minimum conformant `.cursor/rules/nucleus_session_bootstrap.mdc`:**

```
# Nucleus session bootstrap (applies to all files, all turns)

On the first turn of any new workspace session, before handling the user
request:

1. Call mcp tool `nucleus_sync.identify_agent` with role="primary",
   provider="cursor", session_id=<cursor workspace UUID>.

2. Call mcp tool `nucleus_sync.relay_inbox(recipient="cursor",
   unread_only=true)`. Surface a summary line per envelope.

3. Ack processed envelopes via `nucleus_sync.relay_ack`.

4. All `nucleus_sync.relay_post` calls MUST include `sender="cursor"`.
```

**Conformance-test:** same as Appendix A with `.brain/relay/cursor/` seed.

---

## Appendix C — Codex (skill file)

**Extension model:** Codex CLI supports per-project skill files at `.codex/skills/<skill-name>.md`. Skills are auto-discovered at CLI start.

**Minimum conformant `.codex/skills/nucleus_session_bootstrap.md`:**

```markdown
---
description: Nucleus relay inbox poll on session-start
trigger: session_start
---

On session start:

1. Invoke MCP tool `nucleus_sync.identify_agent` with role="worker",
   provider="openai_codex", session_id=<codex session id>.

2. Invoke `nucleus_sync.relay_inbox(recipient="codex", unread_only=True)`.
   Surface a summary line per envelope.

3. Ack processed envelopes via `nucleus_sync.relay_ack`.

4. All `nucleus_sync.relay_post` calls MUST include `sender="codex"`.
```

**Conformance-test:** same as Appendix A with `.brain/relay/codex/` seed.

---

## Appendix D — Windsurf (rules-based, user-global)

**Extension model:** Windsurf rules are defined per-user under `~/.codeium/windsurf/memories/` (canonical path) and loaded at every turn. The Nucleus-AGENTS.md rule is already installed as a user rule on this machine.

**Minimum conformant user rule fragment (appended to the AGENTS.md rule body):**

```markdown
## Turn-0 Nucleus bootstrap (MANDATORY)

On every session's turn-0, before substantive work:

1. `nucleus_sync.identify_agent(role="primary", provider="windsurf",
   session_id=<windsurf session id>)`.

2. `nucleus_sync.relay_inbox(recipient="windsurf", unread_only=True)`.
   Surface envelope summary to conversation.

3. Ack processed envelopes via `nucleus_sync.relay_ack`.

4. All `nucleus_sync.relay_post` calls MUST include
   `sender="windsurf"`.

See also `.brain/nudges/windsurf_session_bootstrap.md` for turn-0
substrate-state discovery (git fetch, shared-branch detection, inbox scan).
```

**Conformance-test:** same as Appendix A with `.brain/relay/windsurf/` seed.

---

## Appendix E — Claude Code (pre-turn-hook)

**Extension model:** Claude Code supports pre-turn hooks via `.claude/hooks/` — scripts that run before every user turn is surfaced to the assistant. Hooks can invoke arbitrary MCP tools and inject results into the turn context.

**Minimum conformant `.claude/hooks/nucleus_session_bootstrap.sh`:**

```bash
#!/usr/bin/env bash
# Nucleus session-start inbox poll (T2.5 Appendix E)
set -euo pipefail

ROLE="${CC_SESSION_ROLE:-primary}"
PROVIDER="anthropic_claude_code"
SESSION_ID="${CLAUDE_SESSION_ID:-$(uuidgen)}"

# Only fire on turn-0 (when no turn marker file exists).
TURN_MARKER="${NUCLEUS_BRAIN:-${HOME}/.brain}/sessions/claude_code_${SESSION_ID}.turn0"
if [[ -f "$TURN_MARKER" ]]; then
    exit 0
fi

# Identify + poll inbox; errors non-fatal.
python3 -m nucleus_session_bootstrap \
    --role "$ROLE" \
    --provider "$PROVIDER" \
    --session-id "$SESSION_ID" \
    --recipient "claude_code_${ROLE}" \
    || echo "[nucleus] session-start inbox poll failed (non-fatal)"

touch "$TURN_MARKER"
```

The `nucleus_session_bootstrap` entry point is a thin wrapper around the three MCP tool calls; it may live in the nucleus-mcp package as a CLI.

**Conformance-test:** cold-boot `claude -c <worktree>` with `CC_SESSION_ROLE=primary` and a seeded envelope in `.brain/relay/claude_code_main/`. First assistant message must surface the envelope summary.

---

## Cross-appendix invariants

1. **Role vocabulary is the generic set** `{primary, secondary, coordinator, worker, reviewer}` per ADR-0005 §D1. Agent-specific role tokens (`claude_code_main`, `claude_code_peer`) are legacy-compat only; during §D5 grace period they coerce via `_coerce_legacy_to_tuple`. After Cycle C+2, tuple form is mandatory.

2. **`sender=` values are free strings** in the canonical tuple path; the prefix-match coercion table in `runtime/providers.yaml` (Slice #3 PR #138) determines provider-attribution. Adding a new provider is a YAML-only edit.

3. **Inbox paths are `.brain/relay/<recipient-token>/`**. The recipient-token is the agent's self-identifier (e.g. `gemini_cli`, `cursor`, `codex`, `windsurf`, `claude_code_main`). Recipient tokens must match the prefix-match table in `providers.yaml` for sender-attribution to work.

4. **No agent-specific substrate fields.** Envelopes carry `from`, `to`, `sender`, `role`, `provider`, `session_id` tuples — never Gemini-specific or Cursor-specific keys. If an agent needs extra metadata, put it under `metadata: {}` not at the top level.

5. **Failure-mode parity.** All appendices must handle the three required behaviors under substrate errors (inbox-empty / inbox-errors / ack-fails / post-fails) identically. Testable via a shared conformance harness (TBD — file as follow-up).

## Conformance harness (stub, follow-up)

A shared test harness under `mcp-server-nucleus/tests/conformance/test_adapter_contract.py` will exercise each appendix's implementation against a seeded substrate. Harness design is follow-up scope; not blocking this spec.

Harness responsibilities:

- Seed `.brain/relay/<recipient>/` with known envelopes
- Launch the agent CLI with a deterministic session-id
- Assert the first assistant-visible output mentions each seeded envelope
- Assert each envelope's tag-log entry shows `read:true` after processing
- Assert every `relay_post` fired by the agent has `sender=<recipient>` set

## References

- Primitive audit: `.brain/plans/substrate_2x_layer_audit_20260421.md` §T2.5
- ADR-0005 identity tuple: `docs/adr/0005-agent-os-foundations.md` (PR #124)
- Config-registry role_map: `mcp-server-nucleus/src/mcp_server_nucleus/runtime/providers.yaml` (PR #138)
- Worktree discipline HARD RULE: `.brain/workflows/worktree_discipline.md` (PR #139)
- Ship-report discipline: `.brain/nudges/windsurf_session_bootstrap.md` (PR #139)
- Cowork assignment relay: `relay_20260422_024202_cc959e20` (E)
