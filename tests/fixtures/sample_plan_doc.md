# Sample Plan Doc — Fixture for scout-synthesize tests

> **Status:** test fixture only — not a real plan doc.
> **Purpose:** happy-path input for `/scout-doc` and `/synthesize-doc` skill workflow tests.
> This is the pre-scout state — no scout expansion blocks have been inserted yet.

---

## 1. Event Schema Design

This section describes the schema for telemetry events emitted by the nucleus
runtime. Each event has a `type`, `emitter`, `data` dict, and an ISO-8601
`timestamp`. Events are appended to `.brain/ledger/events.jsonl`.

The schema must be stable — downstream consumers (audit scripts, dashboards,
GROUND) parse events without a version header today. Any field rename is
a breaking change.

---

## 2. Relay Transport

Relay messages travel from one Claude Code surface to another via
`.brain/relay/<bucket>/` files. Each message is a JSON envelope with a
`from`, `to`, `subject`, and `body`. The relay watcher polls the directory
and delivers to the in-session handler.

Transport must tolerate stale envelopes (re-delivery after restart) and
concurrent writes from multiple sessions without data loss.

---

## 3. Cost Telemetry Integration

The `spawn_prep` / `spawn_close` two-phase API wraps Agent invocations with
paired `agent_spawn` / `agent_return` events. These events carry `spawn_id`,
`role`, `model`, `parent`, and `prompt_chars` / `response_chars`.

Downstream, `audit_token_cost.py --pair` groups spend by `(parent, role)`
cost-pair to give a per-workflow cost breakdown. This is the load-bearing
metric for the scout-then-synthesize pattern cost math.
