# Nucleus Relay Bus Primitive Contract

This document defines the conformance requirements for MCP clients integrating with the Nucleus Relay Bus. It mirrors the structure of the Agent Adapter Contract (PR #140) but focuses specifically on the relay primitives: `relay_send` (or `relay_post`), `relay_inbox`, and `relay_ack`.

## Core Semantics

To safely participate in the Nucleus Relay Bus, an agent MUST:

1. **Inbox Polling**: Call `relay_inbox(recipient=<token>, unread_only=True)` exactly once at turn-0.
2. **Acknowledgment**: Call `relay_ack(message_id=<id>, recipient=<token>)` for every processed envelope.
3. **Explicit Sender**: Provide the `sender` parameter explicitly in every outbound `relay_post` call.

This ensures accurate attribution, prevents duplicate processing, and retires the legacy coupling where the system implicitly guessed the sender based on the agent's identity string.

---

## Appendix A — Gemini CLI

- **Recipient Token**: `gemini_cli`
- **Sender Token**: `gemini_cli`
- **Pattern**: Context-file + Skill injection. Gemini must poll `gemini_cli`, ack all messages, and include `sender="gemini_cli"` when replying.

## Appendix B — Cursor

- **Recipient Token**: `cursor`
- **Sender Token**: `cursor`
- **Pattern**: Settings-based rules. Cursor must poll `cursor`, ack all messages, and include `sender="cursor"` when replying.

## Appendix C — Codex

- **Recipient Token**: `codex`
- **Sender Token**: `codex`
- **Pattern**: Skill file. Codex must poll `codex`, ack all messages, and include `sender="codex"` when replying.

## Appendix D — Windsurf

- **Recipient Token**: `windsurf`
- **Sender Token**: `windsurf`
- **Pattern**: Rules-based (user-global). Windsurf must poll `windsurf`, ack all messages, and include `sender="windsurf"` when replying.

## Appendix E — Claude Code

- **Recipient Token**: `claude_code_main`
- **Sender Token**: `claude_code_main`
- **Pattern**: Pre-turn-hook. Claude Code must poll `claude_code_main`, ack all messages, and include `sender="claude_code_main"` when replying.

---

## Conformance Harness

The relay bus primitive contract is mechanically verified by `tests/conformance/test_relay_bus_contract.py`. The harness tests each of the 5 appendices above using a mock agent against seeded substrate fixtures (`tests/conformance/fixtures/relay/*.json`).
