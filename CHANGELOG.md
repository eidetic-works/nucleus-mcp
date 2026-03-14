# Changelog

All notable changes to Nucleus MCP / Sovereign Agent OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

Nucleus CLI graduates from ⚠️ "Human-only" to ✅ "Agent-native" in the competitive matrix.
Audit score: 6/16 → 11/16 on the industry "8 Rules for Agent-Callable CLIs" checklist.

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
