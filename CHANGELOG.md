# Changelog

All notable changes to Nucleus MCP / Sovereign Agent OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **`NUCLEAR_BRAIN_PATH` deprecation shim restored** — PR #78's removal was incomplete; `cli.py` was left with dead self-OR (`os.environ.get("NUCLEUS_BRAIN_PATH") or os.environ.get("NUCLEUS_BRAIN_PATH")`) and duplicate set lines, while external consumers (`nucleus-mcp-cloud`'s `/ready` endpoint) silently 503'd because they still read the legacy name. Dual-write restored at three call sites in `cli.py`; legacy reads emit a `DeprecationWarning` naming the canonical name + sunset date `2026-05-27`. Tests cover the four matrix cases (new/old/both/neither). Surfaced by Perplexity track verifying Oracle Cloud deploy.

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
