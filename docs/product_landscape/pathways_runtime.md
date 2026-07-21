# Hidden Runtime Pathways — Product Landscape Map

> Scope: coherent, product-shaped capabilities built into the **runtime** code
> (`src/mcp_server_nucleus/runtime/` and adjacent) that are **NOT** surfaced as
> one of the 13 headline MCP meta-tools (`nucleus_agents`, `nucleus_audit`,
> `nucleus_delegate`, `nucleus_engrams`, `nucleus_features`, `nucleus_federation`,
> `nucleus_governance`, `nucleus_infra`, `nucleus_orchestration`, `nucleus_relay`,
> `nucleus_route`, `nucleus_sessions`, `nucleus_sync`, `nucleus_tasks`).
>
> "Hidden" here means: not its own top-level tool. Some are reachable as buried
> sub-actions of a headline tool; some are CLI-only; some are daemon-only; some
> are genuinely orphaned (real logic, zero live callers). Each entry flags that.
>
> **Build-% legend:** `works-e2e` = real logic calling real subsystems, tested
> against real state; `partial` = real logic with material gaps/stubs/flag-gated-off
> /degraded paths; `scaffold` = interface/logic exists but unreachable, broken import,
> or shell-only.
>
> Not ranked. Ranking is deferred to a fresh session. Honesty over polish —
> scaffold is flagged as scaffold.
>
> Generated 2026-07-11. Branch at time of survey: `feat/dsor-verifier`.

---

## 1. GROUND — tiered code-build execution verifier

**What it does:** Runs an agent's code against reality in escalating tiers
(0=diff-nonempty, 1=syntax, 2=import, 3=test exec, 4=runtime/HTTP/process, 5=outcome-delta
vs baseline) instead of trusting a "done" self-report. A Gödel-flavored "step outside
the formal system" checker baked into the dev loop.

- **Entrypoints:** `runtime/execution_verifier.py`, `runtime/ground.py`, `.claude/hooks/ground-verify.py`
- **Build-%:** `works-e2e` for tiers 0–2 — wired live into the PostToolUse hook on every file edit (`.claude/hooks/ground-verify.py:51-65` imports `_tier1_syntax_check`/`_tier2_import_check` directly). Tiers 3–5 are code-complete but only test-covered (`tests/test_execution_verifier_coverage.py`, 139 tests), not hook-wired.
- **Differentiation:** Novel — a ground-truth build checker inside the dev loop itself, not a CI add-on; tiered escalation is distinctive.
- **Who feels the value:** An agent-fleet operator who needs proof an autonomous coding agent's "fixed it" claim actually compiles/imports/runs before trusting it.

## 2. DSoR Verifier + verify_gate — claim-adjudication referee

**What it does:** Decomposes an arbitrary text claim into deterministic Anchors, probes
live ground truth (git/http/fs/shell, stdlib-only, never raises) via a ProbeEngine,
adjudicates CONFIRMED/REFUTED/UNVERIFIABLE/PARTIAL, writes the verdict onto a
DecisionLedger, and fail-closed *gates* consumption of the claim (relay artifact refs,
task-blocker release) unless CONFIRMED on the gate's exact predicate.

- **Entrypoints:** `runtime/verifier.py`, `runtime/verify_gate.py`, `runtime/dsor.py` (DecisionLedger); wired into `runtime/relay/core.py:55` and `runtime/task_ops.py:64-65`
- **Build-%:** `partial` — core engine has 921+ tests (`tests/test_verifier.py`) and a real caught-lie demo (commit `bbf0e29e`: an "18,695 INR" claim REFUTED against a live total of 23,281), but every consumption point is env-flag-gated OFF by default (`task_ops.py:31` `NUCLEUS_VERIFY_GATES`; `relay/core.py:244` `NUCLEUS_RELAY_ARTIFACT_ANCHOR=1`). This is this-week's work on `feat/dsor-verifier`.
- **Differentiation:** Novel — THE "not self-reported" ground-truth auditor. Architecturally distinct from GROUND (#1): it adjudicates arbitrary text claims via anchors, not code-execution tiers. Directly targets the fleet's structural "narrators trust themselves" problem.
- **Who feels the value:** A multi-agent orchestrator operator who needs to stop sub-agents / relay messages from gaming "DONE" status with unverified claims.

> Note: separate from `nucleus_audit` (a hash-chained event log/ACL facade,
> `tools/audit_log_tool.py`) — zero import relationship, confirmed by grep.
> `runtime/csr.py` (a difficulty-weighted "Claim Survival Rate" scoreboard) is a
> third, related-but-**orphaned/dead** module: only its own test consumes it, and a
> same-named `flywheel/csr.py` is what's actually wired into the flywheel dashboard.

## 3. Cross-tool session mirror — unified memory across every AI coding tool

**What it does:** Concurrently watches Cursor + Claude Code + Cowork session logs
via watchdog, parses each tool's native transcript format into one shared `EngramEvent`
schema, and drains them into a pluggable sink meant to feed the engram store —
one memory substrate instead of three siloed histories.

- **Entrypoints:** `mirror/daemon.py`, `mirror/cursor_watcher.py`, `mirror/claude_code_watcher.py`, `mirror/cowork_watcher.py`, `mirror/parsers/*.py`
- **Build-%:** `partial` — parsers + watchers are real and well-tested (78 real tests across `test_mirror_*.py`, `tmp_path` not mocks), but `run_coordinator()`'s only sink is `in_memory_sink()` (`mirror/daemon.py:211-222`) and no launchd/plist runs `--coordinator` in production (the simpler bash-script mirror's plist is `.disabled`).
- **Differentiation:** Novel — a single unified event schema across three different AI-coding-tool transcript formats, not just log tailing.
- **Who feels the value:** A person who codes across Cursor / Claude Code / Cowork and wants one memory substrate rather than three disconnected histories.

## 4. ADUN memory pipeline — deterministic auto-writing engram state machine

**What it does:** Turns raw system activity into typed ADD/UPDATE/DELETE/NOOP engram
operations with dedup, secret-pattern scanning, and optional HMAC provenance-anchoring
(chain-hashed, forged-author/timestamp-resistant) before writing to the engram ledger —
memory that writes itself as work happens, no "remember this" call needed.

- **Entrypoints:** `runtime/memory_pipeline.py` (`MemoryPipeline`, `EngramOp`); `runtime/engram_hooks.py` (auto-fires on 21 event types via `_emit_event`)
- **Build-%:** `works-e2e` — wired inline into `event_ops._emit_event` (`engram_hooks.py:9-15`, "100% for all events... wired INLINE"); `test_memory_pipeline.py` has 17 real tests over a temp-brain fixture covering dedup, anchoring, forged-timestamp resistance.
- **Differentiation:** Novel — automatic, no-prompt memory writes driven by system events, with cryptographic anchoring against tampering.
- **Who feels the value:** A fleet operator running many agents who needs an audit-honest memory trail that writes itself, not one to manually curate.

> Adjacent-but-scaffold: the **unified SoR memory facade** (`memory/facade.py`,
> `memory/sor.py`, + vector/relay/graph projections `runtime/vector_store.py`,
> `runtime/relay_engram_projection.py`, `runtime/context_graph.py`) intends to be
> the single capture/recall/curate surface consolidating FTS5 + vector + relay-thread
> + graph recall. Currently flag-gated OFF (`NUCLEUS_MEMORY_SOR`); `facade.py:12`
> self-declares "BATCH 1 IS SCAFFOLD ONLY... no existing caller is repointed here yet."

## 5. Skill auto-extraction pipeline — transcripts → installable Claude Skills

**What it does:** Clusters agent-transcript intents into skill candidates, generates
deterministic `SKILL.md`, and registers + auto-installs to `~/.claude/skills/` under
an allowlist + a self-kill "paste-friction" gate — fully automated, zero human paste.

- **Entrypoints:** `runtime/skill_extractor.py`, `runtime/skill_generator.py`, `runtime/skill_publisher.py`, `runtime/skill_registry.py`, `runtime/skill_friction.py`, `runtime/jobs/skill_extract_job.py`
- **Build-%:** `works-e2e` for extract→generate→register, gated for auto-install — `runtime/jobs/skill_extract_job.py:12-19` "Pipeline: extract -> generate -> register -> auto-install (ALLOWLIST-gated)". No MCP tool wraps it; only `runtime/daemon.py` invokes it.
- **Differentiation:** Novel — turns raw conversation history into installable Claude Code Skills, self-governed by a paste-friction metric; not just prompt-caching.
- **Who feels the value:** Power users in long agent sessions who want repeated manual pastes turned into reusable skills automatically.

## 6. Capability marketplace — trust-tier reputation registry for inter-agent calling

**What it does:** A two-sided agent-tool marketplace: permanent `name@nucleus` addresses,
capability cards, trust tiers (Unverified→Verified), reputation history, quarantine/promote
admin actions, and cross-federation capability-card sync.

- **Entrypoints:** `runtime/marketplace.py`, `tools/_marketplace_core.py`
- **Build-%:** `works-e2e` but buried — `tools/sync.py:249-333` registers 18 `marketplace_*` actions (search/whoami/promote/quarantine/audit/federation_proxy) as **sub-actions of `nucleus_sync`**, not a headline tool.
- **Differentiation:** Novel — a full trust/reputation economy (tiers, audit trail, alerts, federation-wide card sync) for inter-agent calling, beyond a static tool list.
- **Who feels the value:** Fleet operators governing which agents/tools may call each other and tracking reputation drift over time.

## 7. Archive pipeline — training-data flywheel ("third brother" model)

**What it does:** Records every agent loop-turn as SFT examples, preference pairs (DPO),
and full reasoning chains, then exports to Gemini/OpenAI/Anthropic/TRL fine-tuning
formats — a purpose-built dataset generator to self-train a fleet-specific model on
accumulated decision intelligence.

- **Entrypoints:** `runtime/archive_pipeline.py` (3,632 lines — largest file in runtime/; `LoopTurn`/`ArchivePipeline` at `:79-183`), `sovereign/archive_cli.py`
- **Build-%:** `works-e2e` as CLI-only, no MCP exposure — `sovereign/archive_cli.py:91-97` wires `nucleus archive pipeline`; grep of `tools/` shows zero references to `archive_pipeline`.
- **Differentiation:** Novel — SFT + DPO + reasoning-chain dataset generation from live agent operation, aimed at fine-tuning a proprietary fleet model.
- **Who feels the value:** An ML/infra team wanting to fine-tune a model on the fleet's own accumulated agent behavior.

## 8. god-combo pipelines — SRE triage + self-reinforcing memory

**What it does:** Sub-action pipelines under `nucleus_engrams`: a prometheus/audit
health rollup (pulse-and-polish); a symptom→metrics→diagnosis→recommendation SRE triage;
and an observation→recall→synthesis compounding-memory loop that tiers synthesis into
memory itself (NOVEL/REINFORCED/COMPOUNDED).

- **Entrypoints:** `runtime/god_combos/pulse_and_polish.py`, `self_healing_sre.py`, `fusion_reactor.py`; wired at `tools/engrams.py:305-319`
- **Build-%:** `works-e2e` — `tests/test_god_combos.py` runs against real temp `.brain` state, no mocks, 51/51 pass (`:34-46`); `self_healing_sre.py:92-116` parses live Prometheus text output.
- **Differentiation:** Commodity idea (health-check script) made distinct by tiering synthesis into memory itself (`fusion_reactor.py:160-187`).
- **Who feels the value:** An SRE/on-call engineer wanting one-shot triage; a knowledge-ops user wanting self-reinforcing memory.

> Adjacent-but-dead in this cluster: `god_combos/self_healing_v2.py` (predictive
> failure-trend + autonomous fix/refactor proposal — real threshold logic at `:88-119`
> but zero importers) and `capabilities/self_healing.py` + `enforcement_ops.py`
> (registered at `factory.py:285,288` but absent from every persona's capability list,
> so never loaded). Genuinely orphaned.

## 9. Sub-agent DevOps toolbelt — governed shell + web + live delegation

**What it does:** The actual tool-belt handed to spawned agent personas (not a headline
tool): a path-sandboxed filesystem/shell with a command allowlist, web search/scrape,
and live sub-agent delegation that spins a real `EphemeralAgent` via `ContextFactory` +
`DualEngineLLM`.

- **Entrypoints:** `runtime/capabilities/code_ops.py`, `web_ops.py`, `brain_ops.py`, `base.py` (Capability ABC); registered by `runtime/factory.py` into `ContextFactory`
- **Build-%:** `works-e2e` — `code_ops.py:170-188` runs `subprocess.run` against a `SAFE_COMMANDS` allowlist with path-sandboxed read/write; `brain_ops.py:142-171` actually `asyncio.run(agent.run())`s a real delegated agent.
- **Differentiation:** Real exec sandbox + real recursive sub-agent spawn loop, not a stub wrapper around an LLM call.
- **Who feels the value:** Infra/eng builders running autonomous coding swarms who need a governed shell instead of raw subprocess access.

> Related capabilities in the same framework: a **Render deploy-and-verify pipeline**
> (`render_ops.py`, `render_poller_cap.py` — real API + async poll + smoke test, but
> `partial`: deploy URL is a hardcoded guess `render_poller_cap.py:187` and degrades to
> "simulation mode" with no key); a **Gemini strategy/status content brain**
> (`marketing_engine.py`, `synthesizer.py` — `partial`: `brain_synthesize_strategy`
> has no `return` on success so the caller's `result.get("path")` crashes); and an
> **agent-fleet governance suite** (`budget_ops.py`, `depth_tracker.py`,
> `agent_dashboard.py`, `feature_map.py`, `memory_ops.py` — mostly `works-e2e`, but
> `feature_map._discover_products` references an unset `self._brain` and silently
> falls back to `["nucleus"]` only, `feature_map.py:216`).

## 10. Persistent flywheel daemon — the always-on agent OS kernel

**What it does:** A long-running background kernel process (launched by `nucleus start`,
outside any MCP tool call) that runs a real cron-style scheduler of ~15 jobs: briefing,
morning/evening routine, meta-optimizer, tb-compound learning, backups.

- **Entrypoints:** `runtime/daemon.py` (`DaemonManager.start`, `:220`), `runtime/orchestrator.py` (the daemon's live V2 orchestrator, imported `daemon.py:27`), `runtime/scheduler.py`
- **Build-%:** `works-e2e` — `daemon.py:220` wired from `cli.py:7370` `nucleus start`, scheduling 15 real jobs at `daemon.py:122-168`.
- **Differentiation:** Commodity concept (cron daemon) but owns the "always-on agent OS" narrative vs request/response MCP tools.
- **Who feels the value:** Ops/founder wanting Nucleus to keep working unattended between chat sessions.

---

## Also-found (real logic, currently unreachable — noted, not counted in the 10)

- **NOP v3.1 shadow stack** — `runtime/autopilot.py` (sprint autopilot), `runtime/agent_pool.py`
  (rate-limit-aware exhaustion/respawn with HITL consent), `runtime/task_ingestion.py`
  (multi-format task ingestion). Fully coded in-repo but **disconnected**: live call sites
  import a same-named *external* `nop_core` package (`sprint_ops.py:42`, `ingestion_ops.py:30`),
  so exposed actions degrade to "❌ ... Install nop_v3_refactor." `nucleus_agents`
  consent actions are hardcoded stubs (`orchestration.py:1185`). `scaffold`.
- **Autonomous-wake inference replay** — `sessions/autonomous_wake*.py` + `mirror/hook.py`:
  wakes a dormant remote Claude session via a raw `POST /v1/messages` replay with harvested
  system-prompt/tools/history, injecting a constrained `nucleus_relay` ACK tool. Highly novel
  but `scaffold` — the whole HTTP path is mocked in tests and no shell/console hook registers
  `mirror/hook.py::main()`.
- **Founder-absence quiescent mode** — `runtime/founder_absence.py`: a 6-signal numeric
  "autonomous readiness score" gating an offline maintenance mode. Only `readiness_score()`
  is live (`health_check.py:257`); `enter_quiescent_mode`/`run_autonomous_maintenance` have
  zero non-test callers. `partial`.
- **Idempotent outbound posting** — `runtime/outbound_ops.py` (`nucleus outbound check|record|plan`
  CLI): content-addressed hash-dedup ledger for external posts, recorded as engrams with
  auto task-closure + growth-hook firing. `works-e2e` for the ledger/dedup logic; external
  posting deliberately out of scope.
- **Problem board + PM view** — `runtime/board_ops.py` (tagged post/claim/resolve "common
  problem board", tested e2e but zero production callers, points to a `tools/board.py` facade
  that doesn't exist) and `runtime/pm_view_ops.py` (task HUD + ASCII Gantt, `scaffold`/broken:
  imports `_brain_federation_status_json_impl` which doesn't exist in `federation_ops.py`).
- **Federation deep engine** — `runtime/federation.py` (1,884 lines): a full Raft consensus
  engine, vector-clock/merkle gossip sync, partition detection/healing, and a DSoR
  per-decision provenance ledger sit under `nucleus_federation`'s 7-action facade
  (`propose` `:1049`, `check_partition_status` `:1280` have no exposed action). Mostly commodity
  distributed-systems backend; the per-decision audit ledger is the distinctive bit.

---

## Coverage note

Did NOT reach: the `runtime/loops/`, `runtime/channels/`, `runtime/agents/oracle/`,
`runtime/jobs/`, `runtime/auth/`, `runtime/identity/`, and `runtime/relay/` sub-packages;
the billing/stripe/license/KYC monetization cluster (`stripe_billing.py`, `billing.py`,
`license.py`, `kyc_demo.py`); the LLM cost-routing/resilience cluster (`cost_router.py`,
`llm_resilience.py`, `providers.py`, `claude_oauth_llm.py`, `oauth_shim_http.py`); the
telemetry/observability cluster (`otel_export.py`, `prometheus.py`, `anon_telemetry.py`,
`saturation_telemetry.py`, `emergence_rate.py`); recipes/recovery/hardening/hygiene; and
`conversation_ops.py`, `sync_ops.py`, `session_ops.py`, `slot_ops.py`, `depth_ops.py`,
`delta_ops.py`. Verdicts on flag-gated pathways reflect default-OFF state, not the wired-on
behavior. Build-% is a static-read estimate; none of these pathways were executed live.
