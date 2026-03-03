# Changelog

All notable changes to Nucleus MCP / Sovereign Agent OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
