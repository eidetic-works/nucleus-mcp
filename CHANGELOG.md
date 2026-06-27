# Changelog

All notable changes to Nucleus MCP / Sovereign Agent OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.14.2] - 2026-06-27 — "Intelligent nudge: pattern detection + self-rescue"

### Fixed
- **systemMessage hoist** — moved `systemMessage` from nested inside
  `hookSpecificOutput` (where it was silently dropped per the Claude Code hook
  contract) to the top level (where it is shown to the human operator). The
  model-facing context stays nested at `hookSpecificOutput.additionalContext`.
  This was the root cause of the "human sees nothing" gap in 1.14.1.

### Added
- **Intelligent pattern detection** (zero-token heuristics) — classifies the
  read streak into three patterns and emits a contextual nudge + imperative
  self-rescue instruction:
  - `deep_dive` — files share a topic stem (e.g. auth.py, auth_oauth.py,
    auth_jwt.py). Nudge: "You probably have enough context. Write the fix."
  - `thrashing` — files scattered across ≥4 unrelated topics. Nudge: "You're
    bouncing. Pick one thing."
  - `research_spiral` — >60% docs/specs (.md, .txt, .rst, .pdf). Nudge: "You
    have enough theory. Go write the code."
  - `unknown` — fallback for short/ambiguous streaks.
- **Imperative self-rescue** — the `additionalContext` (model channel) now
  contains an imperative instruction ("STOP reading. Do one of: write code,
  call depth_pop, call add_loop. Do not read another file first.") instead of
  a passive description. This is what makes the agent rescue itself.
- 4 new tests (20 total): deep_dive, thrashing, research_spiral, imperative
  instruction verification.

## [1.14.1] - 2026-06-27 — "Auto-detect hook: proactive rabbit-hole detection"

### Added
- **PostToolUse auto-detect hook** — watches the live tool-call stream and surfaces
  a visible depth indicator without the AI calling anything. Classifies each tool
  call as read/write/neutral, increments a read-depth counter, resets on writes
  (real progress), and emits a `systemMessage` at configurable thresholds.
  Kill switch: `RABBITHOLE_HOOK_DISABLED=1`. Thresholds: `RABBITHOLE_DEPTH_DANGER`
  (default 10), `RABBITHOLE_DEPTH_RABBITHOLE` (default 15). Bridged into the same
  rabbithole SQLite store. 16 new tests (28 total).

## [1.14.0] - 2026-06-27 — "nucleus-rabbithole: Rabbit-Hole Depth Tracker"

### Added
- **nucleus-rabbithole** — a second, import-independent MCP server bundled inside
  the nucleus-mcp package. A rabbit-hole depth tracker for focus-prone developers.
  9 tools: `depth_push`, `depth_pop`, `depth_show`, `depth_map`, `switch_context`,
  `add_loop`, `list_loops`, `close_loop`, `weekly_review`. Local SQLite, no network,
  no daemon. Import-independent (imports only stdlib + mcp, nothing from sibling
  nucleus-mcp modules). Console entry-point: `nucleus-rabbithole`. 12 unit tests.

## [Unreleased]

### Security
- **24 bugs found and fixed via stress-test-audit.** 5 CRITICAL security (3 path traversal,
  1 SSRF, 1 SQL injection), 1 SECURITY (HITL bypass), 3 CRITICAL dispatch (missing imports,
  federation coroutines, handler signature), 10 MEDIUM (type validation, file size, sync
  dispatch, VALID_COLUMNS), 6 LOW (path leakage, mutable defaults, flag injection, log
  noise, error message). Stress test: 713→956 pass, 0 crashes. Unit tests: 4185→4300 pass,
  0 failures.

## [1.13.6] - 2026-06-25 — "README: Hosted Relay Quick Start"

### Changed
- **README quick start now shows two paths.** Option A: add `https://relay.nucleusos.dev/mcp`
  as a remote MCP server (zero install — for ChatGPT, Claude, Perplexity users). Option B:
  `pip install nucleus-mcp && nucleus init` (local install — for Cursor, Windsurf, Claude
  Desktop users). The relay path was buried in connector docs; now it's the first thing
  a new visitor sees.

## [1.13.5] - 2026-06-25 — "Telemetry sys.exit Fix"

### Fixed
- **Telemetry bypass on sys.exit commands.** 14 commands (`doctor`, `engram`, `federation`,
  `task`, `session`, `growth`, `outbound`, `skill`, `sync`, `export`, `import`, `chief`,
  `run`, `archive`) used `sys.exit()` in the dispatch block, which raised `SystemExit` and
  jumped past the telemetry recording code. Now telemetry is recorded in the `SystemExit`
  handler before re-raising. This was causing most command-level telemetry to silently drop.

## [1.13.4] - 2026-06-25 — "Clean First Impression"

### Fixed
- **Startup noise eliminated.** Three debug messages (`[Nucleus] Tier 2 (ADVANCED)...`,
  `[NUCLEUS] tool-call instrumentation installed...`, `[NUCLEUS] Registered 17 facade
  tools...`) were printed on every single CLI invocation. Now suppressed unless
  `NUCLEUS_DEBUG=1` is set. A new user running `nucleus --version` or `nucleus help`
  now sees clean output instead of internal diagnostics.
- **Telemetry endpoint fixed.** Client SDK was sending to `telemetry.nucleusos.dev`
  (a domain that doesn't exist). Now sends to `https://eidetic.works/api/telemetry/install`.
  All telemetry was silently dropping before this fix.
- **Telemetry SDK rebuilt.** Replaced dead OTLP span builder with simple JSON events.
  New event types: `session_start`, `session_end`, `command`, `feature_adoption`,
  `error`, `daemon_install`. Every event includes `session_id`, OS, Python version,
  nucleus version, and is_ci flag. Enables per-install journey tracking.
- **Feature adoption tracking wired.** 21 trackable CLI commands now fire
  `feature_adoption` events when used, so we can see which features users actually try.
- **Error tracking wired.** Uncaught CLI exceptions now fire `error` events with
  error type and command context.
- **`filelock` dependency added.** Was used but not declared in `pyproject.toml`,
  causing a warning on every invocation. Now a proper dependency.
- **filelock warning demoted to debug.** Even if `filelock` isn't installed,
  users no longer see the warning unless debug logging is enabled.
- **Dead OTLP code removed.** `_build_otlp_span()` function was 60 lines of dead
  code after the SDK rebuild. Removed.

### Added
- **`filelock>=3.16.0`** as a core dependency.
- **Per-install journey endpoint** on the telemetry worker (`/api/telemetry/detail`).
  Returns full event timeline per install, grouped by session, with feature adoption,
  error heatmap, command popularity, and retention metrics.

### Added
- **OAuth 2.1 Authorization Server** for MCP HTTP transport. Self-contained
  OAuth 2.1 server (`http_transport/oauth_server.py`) enabling ChatGPT
  Connectors, Claude Connectors, and any MCP client following the MCP
  authorization spec. Implements DCR (RFC 7591), Protected Resource Metadata
  (RFC 9728), Authorization Server Metadata (RFC 8414), authorization code
  flow, refresh tokens, and token revocation (RFC 7009). Enable with
  `NUCLEUS_OAUTH_ENABLED=true`.
- **Perplexity connector setup doc** (`docs/connectors/PERPLEXITY_CONNECTOR.md`).
  Perplexity Pro/Max/Enterprise users can now connect to Nucleus MCP via
  Settings → Connectors → Custom MCP server → `https://relay.nucleusos.dev/mcp`.
- **ChatGPT connector setup doc** (`docs/connectors/CHATGPT_CONNECTOR.md`).
  ChatGPT Plus/Pro/Team/Enterprise users with Developer Mode can connect to
  Nucleus MCP via Settings → Connectors → Add custom connector →
  `https://relay.nucleusos.dev/mcp`. OAuth 2.1 flow is auto-discovered.
- **Connector index** (`docs/connectors/README.md`) documenting all ecosystem
  connectors (Claude, Perplexity, ChatGPT, VS Code) and their status.
- **OAuth bearer token validation in tenant middleware**. Bearer tokens
  issued by the Nucleus OAuth server (`nucleus_at_*`) are now validated by
  the tenant middleware, enabling OAuth-authenticated MCP tool calls without
  a static tenant map.
- **MCP tool annotations for ChatGPT App Catalog**. All 17 facade tools now
  declare `readOnlyHint`, `destructiveHint`, and `openWorldHint` annotations
  per the MCP spec. Required for ChatGPT App Catalog submission and used by
  ChatGPT Developer Mode to determine which tools require user confirmation.
- **`/.well-known/openai-apps` domain verification endpoint**. New HTTP
  transport route serves the OpenAI domain verification token from
  `NUCLEUS_OPENAI_APPS_TOKEN` env var. Required for ChatGPT App Catalog
  submission (domain ownership proof).
- **ChatGPT App Catalog submission checklist**
  (`docs/connectors/CHATGPT_APP_SUBMISSION.md`). Documents the full
  submission process: code-side items (done), operator-keyboard items
  (org verification, demo video, screenshots, demo account, submission
  form), test prompts, and tool annotation reference table.

## [1.13.2] - 2026-06-16 — "Telemetry Default-Flip: Opt-OUT with Disclosure"

### Changed
- **Telemetry: default flipped from opt-IN to opt-OUT with informed consent.** v1.13.1's y/N prompt on `nucleus init` is replaced with a one-time first-run notice on any CLI invocation. Spans now flow by default; three trivial disable paths preserved (env var, yaml, CLI). Industry-standard dev-tool posture (Homebrew, npm, VS Code, Sentry SaaS, Docker Desktop).

### Added
- `TELEMETRY.md` at repo root documenting exactly what's collected, what isn't, and how to disable.

## [1.13.1] - 2026-06-14 — "Opt-In Telemetry + Release-Protocol Audit"

### Security / Privacy
- **Anonymous telemetry is now OPT-IN** (was opt-out since v1.5.1). Default for fresh installs is **disabled**; existing installs honor explicit `telemetry.anonymous.enabled` in `nucleus.yaml` (no forced re-prompt). First `nucleus init` prompts `Enable anonymous telemetry? [y/N]`, defaults to **N** on non-tty / EOF / any error. Privacy contract now matches stated intent.

### Added
- **Bot / CI / install_id tags on telemetry spans** — `is_ci` (derived from CI / GITHUB_ACTIONS / CIRCLECI / etc.), `is_claude_code` (CLAUDECODE env), `install_id` (random per-machine UUID at `~/.config/nucleus/install_id`, mode 600). Lets server-side queries filter `{is_ci=false}` for real-user signal and dedupe spans per install without learning identity.

### Fixed
- **sdist tarball 691 MiB → 1 MiB** (99.8% reduction). `[tool.hatch.build.targets.sdist] only-include` was missing; sdist was pulling in `.claude/worktrees/` (Flutter canvaskit wasm + full repo mirror), `extensions/nucleus-bridge/node_modules/` (esbuild binary), etc. `git archive` for public-repo sync was clean (honors `.gitattributes export-ignore`); hatchling sdist had no fence. Now scoped to `src/`, `README.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml`.
- **`mcp_server_nucleus.__version__` returned `1.11.0` in wheel installs** — runtime parsed `pyproject.toml` at import, but wheels don't ship `pyproject.toml`, so always fell through to the hardcoded `1.11.0` fallback. Switched to `importlib.metadata.version("nucleus-mcp")`; the pyproject parse stays as a dev-editable fallback.
- **Release protocol doc had stale CLI invocation** — `.agent/workflows/release-protocol.md` Step 5 said `nucleus-init /tmp/test-brain` (separate binary, positional); actual CLI is `nucleus init <path>` (subcommand). Updated.

## [1.13.0] - 2026-06-12 — "Treatment Program + Relay v0.2 Bridge"

### Added
- **Relay v0.2 — bidirectional FS↔HTTP bridge daemon** (#570). `nucleus-relay-bridge` console script + launchd plist template at `deploy/mac/`. Mirrors local `.brain/relay/*` inboxes ↔ remote nucleus-mcp-cloud relay service, with monotonic read-state merges, dedup-by-id, and per-cycle convergence. Enables multi-host AI fleets to share one canonical message bus.
- **Tool-call instrumentation channel** (#563). `mcp_server_nucleus.runtime.tool_instrumentation` — async-aware decorator with idempotence sentinel; emits one JSONL line per tool call to `.brain/instrumentation/YYYYMMDD.jsonl`. Zero-cost when off; aggregator collapses into daily summary engrams.
- **Daily aggregator + runtime-manifest bijection gate** (#564). `scripts/instrumentation_aggregator.py` collapses JSONL → summary engrams with per-run truncation guard. `scripts/primitives_bijection_gate.py` verifies `docs/PRIMITIVES.md` ↔ runtime tool list per-server (uses `get_tools()` standalone-fastmcp / `list_tools()` mcp-SDK fallback).
- **Empty-fixture smoke detector** (#568). `scripts/empty_fixture_smoke_detector.py` — AST-based detection of three test-tautology patterns (empty-fixture, stub-string, hasattr-only body).
- **`ClaudeOAuthLLM` provider** (#539). `runtime/claude_oauth_llm.py` routes Anthropic-shaped consumers through Claude Max OAuth bearer with lazy 401-refresh retry. Flat-fee against Max subscription window (zero metered marginal cost). curl_cffi chrome120 impersonation handles Cloudflare on the OAuth path.
- **Cross-context relay (CCR) loop-close** (#513, #514, #516, #519, #522, #523, #524, #528, #530, #534). Autonomous-wake hook support modules, disk-persistent coalesce queue, bespoq context reconstruction from local Claude.app session file, hardcoded sender-prefix removal.
- **HTTP relay stress harness** (#521). `tests/stress/` — load + failure injection for the v0.2 transport.
- **Relay v0.2 Seq-2+3 — `relay_status` HTTP parity + substrate hardening** (#541). HTTP transport returns the same status shape as the FS transport; load-bearing for cross-host relay introspection.
- **`NUCLEUS_WEDGE_RANKER` flag wired into production `bm25.search`** (#465). Default OFF; opt-in alternate ranker pathway for wedge retrieval experiments.

### Changed
- **Server A facade pruned 20 → 15 tools** (#565). Dead tools removed: `align`, `skills`, `flywheel`, `delegate`, `board`, `archive`, `ground`, `synthetic_qa`. Tier registry updated. `docs/PRIMITIVES.md` resyncs.
- **`relay_ops` refactored into `runtime/relay/` package** (#520). Single-source registry, paths/core/bridge split.
- **Sender canonicalization** at server binding + FS write boundary (#542, #548). `ops` alias supported. Resolves sender-vocab drift in multi-surface relay tests.
- **`read_inbox` truth-in-signaling** (#540). Self-recursion guard, clamp-200, rate-limit vs empty disambiguation.

### Fixed
- **Test-tautology gut** (#567). 53 stub-tests removed; strategic-plan local-closure shadow replaced with real coverage.
- **`flywheel` curriculum integration** (#559). Tests now record promotion-allowlisted `task_outcome` phase.
- **Session-wake tests realigned** to Phase-C proxy-only architecture (#558).
- **Priority-2 registry import** repaired post-#520 move (#556).
- **Pseudonymity scrubber** — operator email folded into generic scrubber patterns (#526).
- **Sender-prefix drop** in CCR Plan B helper (#530).
- **`curl_cffi>=0.5.0` declared** in pyproject (#537).
- **`is_http_mode()` guards in `relay_wait` + `relay_listen`** (#536) — GAP-4 closure; prevents FS-only operations from running under HTTP transport.
- **`NUCLEAR_BRAIN_PATH` deprecation shim restored** — PR #78's removal was incomplete; `cli.py` was left with dead self-OR and duplicate set lines, while `nucleus-mcp-cloud`'s `/ready` endpoint silently 503'd because it still read the legacy name. Dual-write restored at three call sites in `cli.py`; legacy reads emit `DeprecationWarning` naming canonical name + sunset date `2026-05-27`. Tests cover the four matrix cases.

### Security
- **Pseudonymity path sweep + credential redaction** (#517). Multi-pass scan + scrub across runtime + docs.

### Docs
- **OCI deploy runbook** updated to native-systemd (#551) — replaces stale docker-compose path.

## [1.12.0] - 2026-04-20 — "Wedge Package + Three-Surface Substrate"

### Added
- **`nucleus_wedge` package** — minimal 2-tool MCP surface (`remember` + `recall`) backed by BM25 retrieval over engrams + relay projections
  - `nucleus-wedge init` — substrate-resolution-safe init flow with seed defaults, idempotent, auto-resolves brain via env > `.git`/`.brain` walk-up > `--brain-path` flag (PR #87 spec §3a)
  - `nucleus-wedge mcp register` — idempotent Claude Code config patcher with backup + atomic write + post-write validation; preserves sibling MCP entries byte-identical (PR #87 spec §3b)
  - `nucleus-wedge bench` — segmented stopwatch for per-criterion timing instrumentation (PR #89 Phase 6)
- **Three-surface relay substrate** — Cowork ↔ CC-main ↔ CC-peer message bus
  - Role-aware bucket routing: per-role inboxes at `.brain/relay/{cowork,claude_code_main,claude_code_peer}/` (PR #58 Phase A1, PR #71 Phase A4 routing symmetry)
  - Per-session read-state tracking via `read_by_sessions` dict (PR #69 Phase A3)
  - Cowork auto-surface via Hammerspoon (PR #67 Phase B, PR #81 cc_notifier Mac-notify on CC-main/peer inbound)
  - Poll-based atomic-write watcher for relay drops (PR #63 Phase C, PR #61 plugin)
  - Phase E judge — auto-ack on closed 2-party Q→R threads (PR #77, PR #79 6-edge proof)
- **Decisive-default policy** — Cowork fires "X in 10 min unless you hold" pattern (PR #82)
- **Skill v2.3 role-aware sender** — `/to-cowork` + `/to-cc` stamp `claude_code_main` vs `claude_code_peer` from `CC_SESSION_ROLE` (PR #75, PR #72)
- **Two-bounce auto-ack rails** — Step 4.5 in skills + check-inbox v4 ambient-ack + Step 5.5 auto-ack mute (PR #76)

### Changed
- **`NUCLEUS_BRAIN_PATH` is the sole brain-path env var** — legacy `NUCLEAR_BRAIN_PATH` alias removed (PR #78)

### Fixed
- **`register_cmd` writes config with `ensure_ascii=False`** — Unicode-path siblings round-trip as raw UTF-8 instead of `\uXXXX` escapes; backup-vs-rewrite stays byte-recognizable for users with non-ASCII paths (PR #92)
- **Sync validator unblock** — test fixture `engrams_src` resolves from `NUCLEUS_TEST_ENGRAMS_PATH` env var, skips cleanly when unset; replaces hardcoded sovereign path that blocked public-mirror sync (PR #91)
- **Plugin `watch-relay.sh` respects `NUCLEUS_BRAIN_PATH`** — fixes cross-worktree split-brain when sender/receiver run in different CWDs (PR #66)
- **`/check-inbox` skill** — direction bug + ack ordering + no blanket ack on peer Cowork sessions (PR #68, PR #70)
- **Hammerspoon `/check-inbox` rate-limit across distinct bursts** (PR #80)

## [1.11.0] - 2026-04-11 — "Ship What's Built"

### Added
- **Flywheel Engine** — Compounding loop that turns every failure into curriculum
  - `nucleus_flywheel` MCP facade with 6 actions: ticket, survived, csr, dashboard, week_report, curriculum_refresh
  - 6-action accountability per failure: memory note, CSR bump, training pair seed, weekly report, GitHub issue, task queue
  - CSR (Claim Survival Rate) tracking — the scalar that proves the system is trustworthy
  - Weekly markdown reports with CSR summary and ticket breakdown
  - `curriculum_refresh()` — closes the loop: promotes DPO pairs whose step has since survived
- **Skill Flywheel** — Auto-extract reusable skills from conversation data
  - `nucleus_skills` MCP facade with 4 actions: list, extract, install, status
  - Keyword-based intent clustering with optional Ollama embeddings
  - Actionability scoring separates task patterns from conversational habits
  - SKILL.md generation with trigger phrases, tool sequences, and anonymized examples
  - Skill publisher installs generated skills as Claude Code custom commands
  - Retry dedup collapses same-session retries while preserving cross-session reuse
  - Session diversity scoring — skills from many sessions rank higher
  - Verb-object domain labels (e.g., `write-tests`, `debug-errors`)
- **GROUND Tier 5** — Outcome verification (anti-premature-victory)
  - Delta-based claim checking: compares plan claims against measured actuals
  - 25% threshold: actual delta must reach 25% of claimed delta to pass
  - File existence claims: verifies claimed file creation
  - Flywheel integration: Tier 5 outcomes auto-report to CSR
- **Governance Pipeline** — CSR scoreboard, goal tracking, failure pattern detection
- **RAG Phase 2** — Conversation indexing, Perplexity thread ingestion, codebase docstring extraction
- **Layer 0 Conversation Capture** — Streaming JSONL parser for Claude Code sessions
  - SFT pairs from successful tool use, DPO pairs from corrections
  - 4 MCP actions, 6-hour ambient daemon mode
- **Integration tests** for flywheel, skill pipeline, and Tier 5 smoke testing (19 new tests)

### Fixed
- **Layer 2 sync block** — Tight timeout + fail-open prevents sync hangs
- **Cross-platform PII stripping** — macOS, Linux, Windows, and WSL home paths stripped from skill data
- **Runtime hostname detection** — Skill extractor strips machine hostnames from training data
- **Skill extraction data quality** — Noise filter, heuristic grading, tighter threshold, duplicate removal

### Changed
- Version bump from 1.8.8 to 1.11.0 to align with roadmap (v1.9, v1.10 features shipped incrementally)

## [1.7.0] - 2026-03-31 — "First User"

### Added
- **Recipe System** — YAML-based workflow packs for instant persona setup
  - `nucleus init --recipe founder` — Founder OS with engram templates, God Combos, scheduled tasks
  - `nucleus init --recipe sre` — SRE Brain with self-healing combo
  - `nucleus init --recipe adhd` — ADHD Brain with zero-maintenance design
  - `nucleus recipe list` — Browse available recipes
  - `nucleus recipe show <name>` — Preview recipe contents
- **Curated CLI Help** — `nucleus help` shows 15 user-facing commands instead of 60+ raw argparse
  - Bare `nucleus` (no args) also shows curated help
- **First-Run Experience** — Recipe-first onboarding: install → init with recipe → morning-brief
- **Universal Session Recovery** — Zero-shot recovery workflow for frozen/bloated IDE sessions
  - `nucleus recover auto <conversation-id>` — One-shot automatic recovery
  - `nucleus recover detect` — Detect bloated conversations
  - `nucleus recover extract <conversation-id>` — Extract context from conversation
  - `nucleus recover quarantine <conversation-id>` — Quarantine bloated files with checksums
  - `nucleus recover bootstrap <conversation-id>` — Generate fresh session with context inheritance

### Fixed
- **Engram store canonical path** — Recipe engrams now write to `engrams/ledger.jsonl` (JSONL), not `memory/engrams.json`
- **`datetime.utcnow()` deprecation** — Replaced with `datetime.now(tz=timezone.utc)`

### Changed
- README quickstart updated to recipe-first flow: `pip install → init --recipe founder → morning-brief`

## [1.6.2] - 2026-03-16 — "Telemetry Pipeline Optimization"

### Added
- **Smart Telemetry Drain** - Automated Upstash Redis → Local OTel pipeline
  - `scripts/smart-drain.sh` - Intelligent Docker lifecycle management
    - Auto-starts Docker Desktop on macOS if not running
    - Waits up to 60s for Docker daemon readiness
    - Starts telemetry containers only if needed
    - Drains spans from Upstash queue to local collector
    - Stops Docker Desktop only if script started it
    - Leaves running containers/Docker untouched
  - `scripts/drain-upstash-spans.js` - Queue drain with run-once mode
    - Manual `.env` parsing (no dotenv dependency)
    - Auto-detects JSON vs protobuf content-type
    - `NUCLEUS_DRAIN_ONCE=true` for single-pass execution
    - Proper process.exit(0) for clean termination
  - `scripts/first-user-alert.sh` - External user detection
    - Filters out known Python versions (3.9.6, 3.11.14, 3.14.2)
    - Filters out user platform (darwin)
    - Creates alert file with first external user details
    - macOS notification on first detection
    - Runs only once (idempotent)
  - `scripts/setup-smart-drain-cron.sh` - Cron automation
    - Installs cron job to run every 12 hours
    - Removes old telemetry:drain cron entries
    - Provides verification and removal instructions
  - npm scripts for easy access:
    - `npm run telemetry:smart-drain` - Manual drain
    - `npm run telemetry:setup-cron` - Install cron

### Fixed
- **Telemetry Resource Efficiency**
  - Reduced Upstash Redis command usage from continuous polling to 12-hour batches
  - Docker Desktop no longer needs to run continuously
  - Telemetry containers auto-managed (start/stop as needed)
  - Zero-maintenance telemetry pipeline

### Documentation
- `SMART_DRAIN_GUIDE.md` - Complete setup and usage guide
- `TELEMETRY_TOGGLE_GUIDE.md` - Telemetry on/off toggle instructions

## [1.6.1] - 2026-03-14 — "Telemetry Hotfix"

### Fixed
- **CRITICAL:** Restored missing `record_anon_command()` implementation in `anon_telemetry.py`
  - v1.6.0 shipped with a 46-line stub (docstring + imports only)
  - All telemetry calls from `_dispatch.py` and `cli.py` silently failed
  - No Python SDK users were sending anonymous telemetry in v1.6.0
  - Full 328-line implementation restored with OTLP JSON span builder
  - Verified working: Python SDK → Cloudflare Worker → OTel Collector → Jaeger
  - Service name: `nucleus-anon` with command/category/duration attributes

### Technical Details
- Lightweight HTTP OTLP sender using `urllib.request` (no heavy dependencies)
- Fire-and-forget background threads (never blocks user workflow)
- Proper config priority: env var > yaml config > default (enabled)
- First-run privacy notice with one-time marker file
- Flush on shutdown with configurable timeout (default 2s)

**All v1.6.0 users should upgrade immediately to enable telemetry.**

---
 
## [1.5.1] - 2026-03-12 — "The Transparent Brain"

### Added — Anonymous Opt-Out Telemetry

Production-ready anonymous usage telemetry using OpenTelemetry, sending aggregate command-level data to help improve Nucleus.

#### Anonymous Telemetry (`runtime/anon_telemetry.py`)
- Separate OTel pipeline (own TracerProvider/MeterProvider) — zero interference with user's enterprise OTel
- Opt-out by default: enabled unless `nucleus config --no-telemetry`
- Sends: command name, tool category, duration_ms, error type, Nucleus/Python version, OS platform
- NEVER sends: engram content, file paths, prompts, API keys, any PII
- Fire-and-forget: unreachable endpoint = zero impact on normal operation
- Endpoint: `telemetry.nucleusos.dev:4317` (configurable)

#### `nucleus config` Command
- `nucleus config --show` — View current configuration
- `nucleus config --no-telemetry` — Opt out of anonymous telemetry
- `nucleus config --telemetry` — Opt back in
- `nucleus config --telemetry-endpoint <url>` — Custom endpoint

#### First-Run Notice
- One-time notice on first CLI invocation with opt-out instructions
- Marker file at `.brain/config/.telemetry_notice_shown`

#### Infrastructure
- OpenTelemetry Collector config for `telemetry.nucleusos.dev`
- Docker Compose stack: OTel Collector + Prometheus + Grafana + Caddy (TLS)
- Pre-built Grafana dashboard with 10 panels (commands, errors, versions, OS)
- `TELEMETRY.md` transparency page

#### Brain Init
- `nucleus init` now creates `.brain/config/` directory
- Seeds `nucleus.yaml` with default telemetry configuration
- Both default and solo templates updated

### Testing
- 23 new tests for anonymous telemetry (100% pass)
- 87 total regression tests passing
- Zero new dependencies (reuses existing `opentelemetry-sdk`)

---

## [1.5.0] - 2026-03-08 — "The Sovereign Kernel"
 
### Added — Architectural Hardening & Paradox Resolution
Phase 5 completion focuses on removing "Bootstrap Paradoxes" and ensuring public scalability.
 
#### Adaptive Path Discovery
- Nucleus now dynamically locates its brain directory using a priority hierarchy:
  1. `NUCLEUS_BRAIN_PATH` / `NUCLEAR_BRAIN_PATH` environment variables.
  2. Recursive parent search from CWD for `.brain`.
  3. Fallback to `$HOME/.nucleus/brain`.
- Added `nucleus self-setup` to automate environment and path configuration.
 
#### CLI Sovereignty & Health
- Unified CLI routing in `cli.py`: Removed redundant handlers, enforced single source of truth.
- Python-native bootstrap: Replaced fragile shell scripts (`chief.sh`) with native logic.
- `nucleus status --health`: Real-time system health checks and sovereignty score.
- `nucleus status --cleanup-lock`: Safe recovery from stale `.lock` files.
 
#### Universal Shell Integration
- Added `completions.sh` providing autocompletion for `bash` and `zsh`.
- Automated completion injection via `nucleus self-setup`.
 
#### Federation Engine Level 1 (Local IPC)
- Automated local peer discovery via IPC registry in `/tmp`.
- Exclusive file locking for registry integrity and PID-liveness pruning for ghost processes.
 
#### DSoR Self-Healing
- Automated reconciliation of "orphaned" decisions in audit logs.
- `AuditReport` now syncs with `EventStream` to ensure 100% decision traceability.
 
### Fixed
- Fixed recursion depth leakage in `coordinator.py`.
- Resolved `NameError` in `selfhealer.py` related to brain path resolution.
- Improved error handling for stalled MCP connections.
 
---

## [1.4.1] - 2026-03-05 — "Agent-Native"

### Added — Gemini CLI Integration (March 5, 2026)

Production-ready integration enabling Google Gemini CLI to use Nucleus as its persistent memory and task management system.

#### Deliverables
- **Wrapper Script** (`scripts/nucleus-gemini`) — Auto-detects brain path, transparent command forwarding
- **Comprehensive Documentation** (`docs/GEMINI_CLI_INTEGRATION.md`) — 400+ lines covering architecture, patterns, troubleshooting
- **Test Suite** (`scripts/test-gemini-integration.sh`) — 16 tests across 8 phases, 100% pass rate
- **Integration Report** (`.brain/artifacts/gemini_cli_integration/INTEGRATION_REPORT.md`) — Full technical report
- **Quick Start Guide** (`.brain/artifacts/gemini_cli_integration/QUICK_START.md`) — 5-minute setup

#### Key Findings
- ✅ Command execution works perfectly (exit codes, error detection, command chaining)
- ✅ Brain safety verified (init protection prevents overwrites)
- ⚠️ stdout not visible in Gemini CLI (JSON outputs generated but not displayed)
- ✅ Workarounds documented (file redirection, exit code control flow)

#### Status
- **Integration**: Production Ready
- **Test Results**: 16/16 PASSED
- **Brain Status**: 136MB, 1,901 files, backed up
- **Documentation**: Complete with patterns, troubleshooting, security considerations

### Added — Agent-Native CLI Polish (5 features)

Nucleus CLI graduates from "Human-only" to "Agent-native".
Audit score: 6/16 → 11/16 on the "8 Rules for Agent-Callable CLIs" checklist.

#### Structured Error Envelope
- JSON errors on stdout when `--format json`: `{"ok": false, "error": "not_found", "message": "...", "exit_code": 3}`
- Human-readable errors still go to stderr (existing behavior preserved)
- Error classification: `not_found`, `usage_error`, `runtime_error`

#### Semantic Exit Codes
- `0` = success, `1` = runtime error, `2` = usage error, `3` = not found
- Agents use `$?` for control flow without parsing stderr

#### `--quiet` / `-q` Flag
- Bare output: one value per line, no headers, no decoration
- For pipes/xargs: `nucleus engram search "auth" -q | wc -l`
- Takes precedence over `--format` when both specified

#### Example-Rich `--help`
- Every agent subcommand now shows Examples section with 2-3 patterns
- Patterns: basic usage, JSON piping with jq, quiet mode for scripting

#### Universal SKILL.md
- OpenClaw-compatible skill file (YAML frontmatter + markdown instructions)
- Works with OpenClaw, Claude Code, Codex, and any agent that reads SKILL.md
- Lists all 13 CLI commands with output format documentation

### Added — Tests
- `test_cli_v141_agent_native.py` — 28 tests covering all v1.4.1 features

---

## [1.4.0] - 2026-03-05 — "The Universal Interface"

### Added — Agent CLI (13 pipe-friendly commands)

Nucleus now speaks **MCP + CLI + SDK** — the first agent brain with all three interfaces.
Every command auto-detects TTY (table) vs pipe (JSON), supports `--format json|table|tsv`,
and follows Unix conventions (stdout=data, stderr=errors, exit 0/1).

#### Engram Commands (`nucleus engram`)
- `nucleus engram search <query>` — Full-text search across engrams (JSONL when piped)
- `nucleus engram write <key> <value>` — Write engram with context and intensity
- `nucleus engram query` — Query by context/intensity with pagination

#### Task Commands (`nucleus task`)
- `nucleus task list` — List tasks with `--status` and `--priority` filters
- `nucleus task add <description>` — Create tasks from the command line
- `nucleus task update <id> --status DONE` — Update task fields atomically

#### Session Commands (`nucleus session`)
- `nucleus session save <context>` — Save session state for later resumption
- `nucleus session resume [id]` — Resume most recent or specific session

#### Growth Commands (`nucleus growth`)
- `nucleus growth pulse` — Run daily growth pulse (GitHub stars + PyPI + compound)
- `nucleus growth status` — Show growth metrics without writing engrams

#### Outbound Commands (`nucleus outbound`)
- `nucleus outbound check <channel> <id>` — Idempotency gate for outbound posts
- `nucleus outbound record <channel> <id>` — Record successful post to ledger
- `nucleus outbound plan` — Show posting plan (ready vs posted vs failed)

#### Global Flags
- `--format json|table|tsv` — Override auto-detected output format
- `--brain-path <path>` — Override brain directory (default: auto-detect)
- `--version` — Show `nucleus 1.4.0`

#### Output Formatter (`cli_output.py`)
- `format_json()` — JSON for scalars, JSONL for lists
- `format_table()` — Aligned columns with headers, value truncation
- `format_tsv()` — Tab-separated for awk/cut pipelines
- `detect_format()` — Auto-detect TTY vs pipe
- `parse_runtime_response()` — Unified parser for runtime JSON responses

#### Skill Descriptor (`nucleus.skill.yaml`)
- Machine-readable CLI capability descriptor for agent tool discovery
- Compatible with OpenClaw skill loading pattern

### Added — Tests
- `test_cli_output.py` — 42 tests covering all formatter functions
- `test_cli_agent_commands.py` — 25 tests covering all 13 agent CLI commands

### Fixed
- Task priority sorting crash when mixing string/int priorities (coerce to int)

### Architecture
- Agent CLI calls runtime functions directly (no MCP dispatch overhead)
- Same runtime powering MCP facade tools and CLI commands — single source of truth
- Unix composable: `nucleus engram search "test" | jq '.key'`

## [1.3.0] - 2026-03-03

### Added — Sovereign Agent OS Features

#### Compliance Configuration System (`nucleus comply`)
- 4 regulatory jurisdictions: `eu-dora`, `sg-mas-trm`, `us-soc2`, `global-default`
- Per-jurisdiction governance policies (data residency, HITL operations, audit retention)
- Sensitive data pattern detection per jurisdiction
- Blocked operations and required approvals per jurisdiction
- One-command jurisdiction application: `nucleus comply --jurisdiction eu-dora`
- Compliance status report: `nucleus comply --report`

#### Audit Report Generator (`nucleus audit-report`)
- Generates audit-ready compliance reports from DSoR traces, event logs, and HITL approvals
- Three output formats: text (terminal), JSON (API), HTML (sharing with compliance officers)
- Compliance checklist with pass/fail/warn status
- Sovereignty guarantee statement in every report
- Output to file: `nucleus audit-report --format html -o report.html`

#### KYC Demo Workflow (`nucleus kyc`)
- 3 pre-built demo applications covering low/medium/high risk scenarios
- 5 automated checks: sanctions, PEP, document validity, risk factors, source of funds
- Risk scoring engine with cumulative risk assessment
- Full DSoR (Decision System of Record) trace for every review
- HITL approval requests auto-generated for risky applications
- Full demo mode: `nucleus kyc demo` — runs all 3 applications in sequence

#### Sovereignty Status Report (`nucleus sovereign`)
- Sovereignty score (0-100) with A/B/C/D grading
- Brain identity: path, size, file count, directories
- Memory health: engram count, context distribution, intensity distribution
- Governance posture: jurisdiction, HITL, kill switch, blocked operations
- DSoR integrity: decision count, event count, trace coverage
- Data residency guarantee with hostname and location

#### MCP Tool Integration
- 9 new actions in `nucleus_governance` tool:
  - `comply_list` — List available jurisdictions
  - `comply_apply` — Apply jurisdiction configuration
  - `comply_report` — Generate compliance status report
  - `audit_report` — Generate audit-ready report
  - `kyc_review` — Run KYC demo review
  - `sovereign_status` — Get sovereignty posture report
  - `trace_list` — List DSoR decision traces
  - `trace_view` — View specific decision trace

#### DSoR Trace Viewer (`nucleus trace`)
- List all decision traces: `nucleus trace list`
- Filter by type: `nucleus trace list --type KYC_REVIEW`
- View detailed trace: `nucleus trace view <ID>`
- Partial ID matching for convenience
- JSON output for programmatic access

#### Deployment Kit (`deploy/`)
- Production Dockerfile with multi-stage build and non-root user
- Jurisdiction-aware build args: `docker build --build-arg JURISDICTION=eu-dora`
- Docker Compose configs per jurisdiction (EU DORA, SG MAS TRM)
- One-command deployment script: `./deploy/deploy.sh eu-dora`
- Auto-applies jurisdiction on first container boot
- Health checks using sovereignty status

### Changed
- Version bumped to 1.3.0
- Updated package description: "Sovereign Agent OS — Persistent Memory, Governance & Compliance for AI Agents"
- Complete README rewrite for Sovereign Agent OS positioning

### Tests
- 54 new tests (21 compliance + 12 KYC + 11 sovereign + 10 trace) — all passing

---

## [1.2.1] - 2026-02-XX

### Previous Features
- Engram memory system (persistent, compounding)
- God Combos (pulse_and_polish, self_healing_sre, fusion_reactor)
- HITL governance with consent management
- Dispatch telemetry and rate limiting
- Morning brief / End-of-day workflow
- Context graph and engram neighbors
- Federation for multi-brain coordination
- Hypervisor security (lock/unlock, watchdog)
- Agent spawning and orchestration slots
- Feature tracking and proof generation
- Session management with checkpoints
- File sync and deploy monitoring
- Billing summary and cost tracking
