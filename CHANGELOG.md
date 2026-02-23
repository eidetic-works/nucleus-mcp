# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.9] - 2026-02-23
### Added
- **Save System (Checkpoint & Handoff)**: Native checkpoint/resume/handoff tools for long-running tasks
  - `brain_checkpoint_task`: Save progress with artifacts and context
  - `brain_resume_from_checkpoint`: Resume tasks with full state restoration
  - `brain_generate_handoff_summary`: Cross-agent handoff with key decisions
- **UnifiedOrchestrator V3.1 Bridge**: 13 methods from legacy orchestrator now available in unified layer
  - Task lifecycle: `get_all_tasks`, `claim_task`, `complete_task`
  - Metrics: `get_pool_metrics`, `get_dependency_graph`, `get_agent_pool`, `get_ingestion_stats`
- **E2E Test Coverage**: 5 end-to-end tests verifying checkpoint tools through MCP layer
- **Checkpoint Documentation**: New section in QUICK_START.md

### Changed
- **Task ID Collision Fix**: Added monotonic counter suffix to prevent duplicate task IDs
- **Test Suite Expansion**: 197 total tests (up from 135)

### Fixed
- Task store race conditions in concurrent checkpoint operations
- Stale version assertion in release verification tests

## [1.0.8] - 2026-02-22
### Added
- **Node Beta Architecture**: Defined Plan 6 (Native Windows) with `.gitattributes` protection for zero-collision agentic deployment.
- **Postgres Storage Readiness**: Finalized storage abstraction layers for the upcoming 'Context Market' scale-up.

### Changed
- **Monolith Decomposition (Completion)**: Successfully reduced `__init__.py` from 8,000+ lines to ~5,000 lines by delegating core logic to 16+ focused modules in `src/mcp_server_nucleus/runtime/`.
- **System Hardening**: Integrated strict type-safe tool registration and refactor integrity tests.

## [1.0.7] - 2026-02-17
### Added
- **Sovereign Brain Card**: `cold_start` now returns a rich summary of memory, top tasks, and mounts.
- **Welcome Engrams**: `nucleus-init` pre-seeds 2 starter memories to prevent "empty brain syndrome".
- **OS-Aware Onboarding**: `nucleus-init` provides copy-paste config paths and auto-copies to clipboard.
- **Single Source of Truth**: Centralized versioning in `.registry/version.json`.
- **Refactor Integrity**: New `tests/test_refactor_integrity.py` ensures tool registration stability.

### Changed
- **Monolith Decomposition (Inception)**: Started the process of splitting the 8,000+ line `__init__.py` into focused `runtime/` modules.
- **Test Suite**: Modernized `tests/test_release_verification.py` to use standard `pytest`, replacing legacy scripts.

### Fixed
- **Tiered Registration**: Resolved recursion and AttributeError bugs in tool registration tests.
- **Sync Operations**: Fixed cache pollution in `test_sync_ops.py`.

## [1.0.6] - 2026-02-14
### Added
- **Sovereign Monolith**: Unified `SovereignMonolith_FINAL.jsx` UI component.
- **Sovereign Portal**: Adaptive V2 portal for ecosystem navigation.

---

## [0.6.0] - 2026-01-30

### Added
- **Decision System of Record (DSoR)**: Full decision provenance for agent actions
  - `DecisionMade` events emitted before every tool execution
  - Context hashing with SHA-256 for state verification
  - Before/after snapshots for agent run lifecycle
  
- **IPC Authentication** (CVE-2026-001 remediation):
  - Per-request auth tokens (30s TTL, single-use)
  - HMAC-signed tokens linked to decisions
  - Prevents socket impersonation attacks
  
- **Token Metering** (Pricing Rebellion remediation):
  - All tool executions metered and linked to decisions
  - Billing-ready consumption tracking
  - Prevents usage bypass via CLI forks

- **Context Manager** (`runtime/context_manager.py`):
  - `ContextSnapshot`: Immutable world-state snapshots
  - `compute_world_state_hash()`: Deterministic state hashing
  - `verify_state_integrity()`: Before/after drift detection
  
- **DSoR MCP Tools** (5 new tools):
  - `brain_list_decisions`: View decision ledger
  - `brain_list_snapshots`: View context snapshots
  - `brain_metering_summary`: Billing/audit summary
  - `brain_ipc_tokens`: IPC token lifecycle
  - `brain_dsor_status`: Comprehensive DSoR status

### Security
- **CVE-2026-001**: Sidecar Exploit - REMEDIATED
- **Pricing Rebellion**: Usage metering bypass - REMEDIATED

### Documentation
- Created `docs/architecture/DSOR_V060.md` (full architecture spec)

### Tests
- Added `tests/test_dsor_v060.py` (16 tests)
- **64 total tests** (16 DSoR + 48 existing)

### Technical
- **135 MCP tools** (5 new DSoR tools)
- New runtime modules: `context_manager.py`, `ipc_auth.py`
- Enhanced `agent.py` with decision emission and state verification

## [1.0.0] - 2026-02-10

### Added
- **Sovereign Release**: The local-first Agent Control Plane is now 1.0.
- **Improved Multi-Agent Sync**: Enhanced conflict detection and file locking coordination across Cursor, Claude Desktop, and Windsurf.
- **Sovereign Metrics Ready**: Architecture finalized for non-PII, edge-blinded telemetry (deferred to v1.1.0).
- **Hardened Governance**: Finalized audit logs and default-deny policies for production use.
- **Recursive Mounting**: Full support for mounting sub-MCP servers with persistence.

### Changed
- **Final Positioning**: Rebranded as "The Local-First AI Memory Server with Governance".
- **Documentation Refactor**: Comprehensive update of README and internal docs for v1.0.0.

### Fixed
- Various pathing issues for Windows compatibility in CLI.
- Tool discovery edge cases in multi-product environments.

---

## [0.8.0] - 2026-02-05
### Added
- Multi-product support in `nucleus-init`.
- Enhanced terminal visuals for depth tracking.

---

## [0.7.0] - 2026-02-01
### Added
- **Multi-Agent Sync**: `brain_sync_now`, `brain_sync_status`, `brain_sync_auto`.
- Intent-Aware Locking for files.

---

## [0.5.1] - 2026-01-26

### Added
- **Engram Ledger Tools**: Persistent cognitive memory for agent decisions
  - `brain_write_engram`: Write memories with key, value, context, and intensity (1-10)
  - `brain_query_engrams`: Query by context category and minimum intensity
  - Context categories: Feature, Architecture, Brand, Strategy, Decision
  
- **Governance Dashboard**: `brain_governance_status` shows policy enforcement
  - Reports Default-Deny, Isolation, and Audit policy status
  - Counts audit log entries, engrams, and events
  - Shows V9 security configuration

- **Audit Trail Visibility**: `brain_audit_log` exposes cryptographic interaction log
  - SHA-256 hashed entries for trust verification
  - Shows emitter, type, timestamp, and hash

- **Demo Script**: `scripts/demo_governance.py` for video recording
  - Interactive CLI demonstration of all governance features
  - Self-cleaning demo brain directory

### Changed
- **Category Pivot**: Rebranded from "Agent OS" to "Agent Control Plane"
- **Terminology**: "Memory" → "Engram Ledger" throughout documentation
- **PyPI Description**: Updated to "The Agent Control Plane - Default-Deny Security"

### Fixed
- Removed 4 duplicate tool definitions causing import warnings
- Fixed `get_orchestrator` undefined reference in swarm tool

### Documentation
- Created `docs/GOVERNANCE_POLICIES.md` (Default-Deny, Isolation, Audit)
- Created `docs/ENGRAM_SPECIFICATION.md` (data model, query patterns)
- Updated README with Governance Moat table

### Tests
- Added 9 unit tests for Engram tools (`test_engram_tools.py`)
- **27/27 core tests passing**

## [0.5.0] - 2026-01-25

### Added
- **V3.1 Task Engine**: Slot pooling and tier routing
  - `brain_status_dashboard`: ASCII visualization of pool health
  - Checkpoint and context_summary fields for tasks
  - Exhaustion tracking for slots

- **Profiling Module**: `runtime/profiling.py`
  - `@timed()` decorator for function timing
  - `brain_metrics` tool for performance data
  - Configurable via `NUCLEUS_PROFILING` env var

- **Prometheus Metrics**: `runtime/prometheus.py`
  - `brain_prometheus_metrics` tool for scraping
  - Counters, histograms, and gauges
  - JSON and Prometheus exposition formats

- **Cryptographic Audit**: `runtime/event_ops.py`
  - SHA-256 hashing of all interactions
  - `interaction_log.jsonl` for trust verification

- **Multi-Agent Protocol**: MoU enforcement
  - `brain_check_protocol`: Verify agent compliance
  - `brain_request_handoff`: Request task handoffs
  - `brain_get_handoffs`: Get pending handoffs

### Changed
- Bumped to **120+ MCP Tools**
- Integration tests now cover 18 critical paths

## [0.4.0] - 2026-01-08

### Added
- **Nucleus Agent Runtime (NAR)**: Ephemeral execution environment for autonomous agents
  - Spawns disposable agents based on intent
  - `ContextFactory` dynamically constructs relevant context
  - `brain_spawn_agent` tool for on-demand delegation

- **Dual-Engine Intelligence**: Robust AGENTIC capabilities
  - Integrated `google-genai` v0.2.2 as primary cognitive engine
  - Automatic fallback to secondary models for resilience
  - Smart routing based on task complexity

- **New Tools**:
  - `brain_list_services`: List Render.com services (delegated via Lazy Loading)

### Fixed
- **Circular Imports**: Implemented Lazy Loading pattern for `RenderOps` to prevent import cycles
- **Context Hygiene**: Enforced "Tool-First Execution" protocol - agents must act, not suggest



### Added
- **Depth Tracker**: ADHD accommodation - warns (but allows) when going deep into rabbit holes
  - `brain_depth_push/pop/show/reset/set_max` MCP tools
  - `brain://depth` resource
  - `nucleus depth show/up/reset/max/push/map` CLI commands
  - Visual indicator: `🟢 DEPTH: ●●○○○ (2/5)`
  
- **Render Poller**: Monitor deployments without leaving chat
  - `brain_start_deploy_poll`, `brain_check_deploy`, `brain_complete_deploy` tools
  - `brain_smoke_test` for health checks
  - Logs events to ledger for traceability

- **Feature Map**: Living inventory of product features
  - `brain_add_feature`, `brain_list_features`, `brain_get_feature` tools
  - `brain_update_feature`, `brain_mark_validated`, `brain_search_features` tools
  - `nucleus features list/test/search/proof` CLI commands
  - Multi-product support (`gentlequest.json`, `nucleus.json`)

- **Proof System**: Build trust with tangible evidence
  - `brain_generate_proof`, `brain_get_proof`, `brain_list_proofs` tools
  - Captures AI thinking, deployed URL, files changed, rollback plan
  - Stored as markdown in `.brain/features/proofs/`

## [0.3.2] - 2026-01-04
### Fixed
- **Hotfix:** The v0.3.1 release missed the core logic update to read `tasks.json`. This release properly enables V2 tasks, checking `tasks.json` first and falling back to `state.json`.

## [0.3.1] - 2026-01-04

### Added
- **Onboarding Flow**: `nucleus-init` now creates instructional seed tasks
  - 3 guided tasks teach users how to use Nucleus
  - Tasks form a dependency chain (blocked_by) demonstrating V2 features
- **In-Brain README**: `.brain/README.md` explains folder structure and quick commands
- **Improved CLI Output**: Clearer "Next Steps" section after init

## [0.3.0] - 2026-01-03

### Added
- **V2 Task Management System**: Complete agent-native task orchestration
  - `brain_list_tasks`: Query tasks with optional filters (status, priority, skill, claimed_by)
  - `brain_get_next_task`: Get highest-priority unblocked task matching agent skills
  - `brain_claim_task`: Atomically claim a task to prevent race conditions
  - `brain_update_task`: Update task fields (status, priority, description, etc.)
  - `brain_add_task`: Create new tasks with full V2 schema
  - `brain_escalate`: Request human help when agent is stuck

### Schema
- **11-Field Task Schema**: id, description, status, priority, blocked_by, required_skills, claimed_by, source, escalation_reason, created_at, updated_at
- **Status States**: PENDING, READY, IN_PROGRESS, BLOCKED, DONE, FAILED, ESCALATED
- **Backward Compatible**: Automatically migrates legacy tasks (TODO→PENDING, COMPLETE→DONE)

### Documentation
- Added `docs/SPECIFICATION.md`: Complete V2 specification (403 lines, 14 thinking passes)
- Defines 5 core principles: Legibility, Reversibility, Degradation, Trust, Simplicity

## [0.2.6] - 2026-01-03

### Added
- **Auto-Backup on Overwrite**: `nucleus-init` now automatically backs up existing `.brain/` before overwriting
  - Creates timestamped backup: `.brain.backup.YYYYMMDD_HHMMSS/`
  - Stricter confirmation for active brains (>10 files): requires typing `BACKUP-AND-OVERWRITE`
  - Your brain is never deleted without a backup existing first

## [0.2.5] - 2026-01-03

### Added
- **Template System**: `nucleus-init` now supports `--template` argument
  - `--template=solo`: Minimal structure for solo founders
    - Creates `ledger/`, `meta/`, `memory/` (no `agents/` folder)
    - Includes `thread_registry.md` for agent identity management
    - Simplified `state.json` with `mode: "solo"`
  - `--template=default`: Full structure (existing behavior)
- **Thread Registry**: New `meta/thread_registry.md` file for stable agent identity
  - Agents self-identify via thread ID lookup
  - Works across IDE thread renames

## [0.2.4] - 2025-12-30

### Added
- **`cold_start` prompt**: Get instant context when starting a new session
  - Shows current sprint, focus, and status
  - Lists recent events and artifacts
  - Detects workflow files (e.g., `lead_agent_model.md`)
  - Works across all MCP clients
- **`brain://context` resource**: Auto-visible in Claude Desktop sidebar
  - One-click access to full brain context
  - No need to type commands

### Improved
- Enhanced context loading with workflow detection
- Better error handling for missing brain paths

## [0.2.2] - 2025-12-27

### Added
- **Snippet Generator**: `nucleus init` now outputs a copyable JSON config snippet
- Shows config file paths for Claude Desktop, Cursor, and Windsurf
- Pre-fills absolute brain path for zero-friction setup

## [0.2.1] - 2025-12-27

### Added
- `nucleus-init` CLI command to bootstrap a new `.brain/` directory
- Sample state.json, triggers.json, and agent template
- Interactive init with next steps guidance

## [0.2.0] - 2025-12-27

### Added
- `brain_get_triggers` - Get all defined neural triggers
- `brain_evaluate_triggers` - Evaluate which agents should activate
- MCP Resources:
  - `brain://state` - Live state.json content
  - `brain://events` - Recent events stream
  - `brain://triggers` - Trigger definitions
- MCP Prompts:
  - `activate_synthesizer` - Orchestrate current sprint
  - `start_sprint` - Initialize a new sprint

### Changed
- Cleaned repo structure (internal files moved out)
- Improved code organization

## [0.1.0] - 2025-12-27
  - `brain_emit_event` - Emit events to the ledger
  - `brain_read_events` - Read recent events
  - `brain_get_state` - Query brain state
  - `brain_update_state` - Update brain state
  - `brain_read_artifact` - Read artifact files
  - `brain_write_artifact` - Write artifact files
  - `brain_list_artifacts` - List all artifacts
  - `brain_trigger_agent` - Trigger agent with task
- FastMCP integration for MCP protocol compliance
- Claude Desktop configuration support
- MIT License
