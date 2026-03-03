# 🧠 Nucleus Sovereign OS

[![PyPI version](https://badge.fury.io/py/mcp-server-nucleus.svg)](https://badge.fury.io/py/mcp-server-nucleus)
[![Watch Launch Trailer](https://img.shields.io/badge/Watch-Launch_Trailer-red?logo=youtube)](https://youtu.be/jI8TUpfjS1A)
[![Join r/NucleusOS](https://img.shields.io/badge/Reddit-r%2FNucleusOS-orange?logo=reddit)](https://reddit.com/r/NucleusOS)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **The Operating System for AI Agents** — Persistent Operational Memory, Swarm Orchestration, and Local-First Sovereignty.

Nucleus is the **Recursive Aggregator** that gives your AI agents a persistent brain (`.brain/`) and a file system. It turns stateless chatbots into stateful **Sovereign Agents**.

### Context vs. Control
Claude's `CLAUDE.md` provides **static context**. Nucleus provides **active control**.

| Feature | CLAUDE.md / .cursorrules | Nucleus (Agent Control Plane) |
| :--- | :--- | :--- |
| **State** | Static (read-only text) | **Dynamic** (Stateful DB, Event Ledger) |
| **Memory** | Session-bound (forgotten on close) | **Persistent** (Project-bound, recallable) |
| **Security** | None (Prompt injection risk) | **Enforced** (Auth boundary, Default Deny) |
| **Tools** | Suggestions only | **Orchestrated Execution** (DAGs) |
| **Audit** | None | **Full Decision Trail** (Who/Why/When) |

## ✨ Governance Features (The Moat)

- **Default Deny Security** — All mounted servers start with NO network/filesystem access.
- **Explicit Consent** — You approve every command. No silent execution.
- **Isolation Boundaries** — Tools cannot see each other or the full chat history.
- **Auth Firewall** — Tokens are stored in Nucleus (Host), never passed to agents.
- **Event Ledger** — Immutable audit trail of every agent decision (`DecisionMade`).
- **Decision Provenance** — v0.6.0 DSoR: Full audit trail with context hashing.
- **IPC Security** — Per-request auth tokens prevent socket impersonation (CVE-2026-001).
- **135 Native Tools** — For orchestration, swarms, memory, and DSoR inspection.

## 🚀 Quick Start (2 Minutes)

### 1. Install
```bash
pip install mcp-server-nucleus
```

### 2. Initialize (Smart Config)
The `nucleus-init` command automatically detects your system and configures Claude Desktop for you.

```bash
# Create your .brain/ and auto-configure Claude Desktop
nucleus-init
```

### 3. Ask Claude
Restart Claude Desktop and try:
> *"Use the cold_start prompt from nucleus to see our current sprint focus."*

> **v0.2.2+**: Smart Init automatically detects Claude Desktop and adds the config for you!

### Configuration (Claude Desktop)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/.brain"
      }
    }
  }
}
```

Restart Claude Desktop and try: *"What's my current sprint focus?"*

### Configuration (Windsurf)

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/.brain"
      }
    }
  }
}
```

### Configuration (Cursor)

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/.brain"
      }
    }
  }
}
```

### ❓ Troubleshooting

**"Show me all tasks" returns nothing?**
Check your config pointer! You might be pointing to an old or temp brain.

1. **Check config:** Open `~/Library/Application Support/Claude/claude_desktop_config.json`
2. **Verify path:** Ensure `NUCLEAR_BRAIN_PATH` points to your active project (e.g., `/Users/me/my-project/.brain`)
3. **Restart:** You MUST restart Claude Desktop after any config change.

## 🛠 Tool Categories (110+ Total)

### 🎯 Core Orchestration
| Tool | Description |
|------|-------------|
| `brain_session_start` | **START HERE** — Get priorities, tasks, and recommendations |
| `brain_orchestrate` | The "God Command" — auto-claim and execute tasks |
| `brain_health` | System health dashboard with component status |
| `brain_version` | Version and capability info |

### 📋 Task Management
| Tool | Description |
|------|-------------|
| `brain_add_task` | Create tasks with priority, skills, dependencies |
| `brain_list_tasks` | Query with filters (status, priority, skill, claimed_by) |
| `brain_get_next_task` | Get highest-priority unblocked task for your skills |
| `brain_claim_task` | Atomically claim (prevents race conditions) |
| `brain_update_task` | Update status, priority, etc. |
| `brain_escalate` | Request human help when stuck |

### 🐝 Swarm Coordination
| Tool | Description |
|------|-------------|
| `brain_orchestrate_swarm` | Launch multi-agent missions |
| `brain_spawn_agent` | Create ephemeral agents for specific tasks |
| `brain_autopilot_sprint` | Orchestrate multiple slots in parallel |

### 💾 Session & Memory
| Tool | Description |
|------|-------------|
| `brain_save_session` | Persist context for later resumption |
| `brain_resume_session` | Restore previous session state |
| `brain_search_memory` | Search Engram Ledger |
| `brain_read_memory` | Read Engram categories |

### 📊 Monitoring & Audit
| Tool | Description |
|------|-------------|
| `brain_satellite_view` | Unified view of depth, activity, health |
| `brain_metrics` | Velocity, closure rates, mental load |
| `brain_open_loops` | All pending tasks, todos, drafts, decisions |

**V2 Task Schema (11 fields):**
```json
{
  "id": "task-abc123",
  "description": "Build landing page",
  "status": "PENDING | READY | IN_PROGRESS | BLOCKED | DONE | FAILED | ESCALATED",
  "priority": 1,
  "blocked_by": ["task-prerequisite"],
  "required_skills": ["python", "frontend"],
  "claimed_by": "agent-thread-id",
  "source": "user | synthesizer",
  "escalation_reason": null,
  "created_at": "2026-01-03T12:00:00",
  "updated_at": "2026-01-03T12:00:00"
}
```

## 📡 MCP Resources

| Resource | Description |
|----------|-------------|
| `brain://state` | Live state.json content |
| `brain://events` | Recent events stream |
| `brain://triggers` | Trigger definitions |
| `brain://context` | **Full context for cold start** — click in sidebar for instant context |

## 💬 MCP Prompts

| Prompt | Description |
|--------|-------------|
| `cold_start` | **Get instant context** — sprint, events, artifacts, workflows |
| `activate_synthesizer` | Orchestrate current sprint |
| `start_sprint` | Initialize a new sprint |

## 🎯 Common Use Cases

### 1. Run a Sprint
```
> "What's my current sprint focus?"
> "Add a task: Build landing page with priority 1"
> "Show me all priority 1 tasks"
```

### 2. Coordinate Multiple Agents
```
> "Claim the next Python task for me"
> "Mark task-abc123 as DONE"
> "List all tasks claimed by agent-1"
```

### 3. Escalate When Stuck
```
> "Escalate task-xyz with reason: Need human approval on pricing"
```
The task is released and flagged for human intervention.

### 4. Check Agent Context
```
> "Use the cold_start prompt from nucleus"
```
Instantly loads sprint, events, and artifacts.

## 🚀 Cold Start (New in v0.2.4)

Start every new session with full context:

```
> Use the cold_start prompt from nucleus
```

Or click `brain://context` in Claude Desktop's sidebar.

**What you get:**
- Current sprint name, focus, and status
- Recent events and artifacts
- Workflow detection (e.g., `lead_agent_model.md`)
- Lead Agent role assignment

## 📁 Expected `.brain/` Structure

```
.brain/
├── ledger/
│   ├── events.jsonl
│   ├── state.json
│   └── triggers.json
├── artifacts/
│   ├── research/
│   ├── strategy/
│   └── ...
└── memory/      # Engram storage (Memory)
    └── *.md
```

## ⚠️ Known Limitations

- **IDE context is separate**: Each MCP client (Claude Desktop, Cursor, Windsurf) connects to the same `.brain/` directory and shares project state. However, IDE-specific context (Cursor's codebase memory, Antigravity's conversation artifacts, etc.) remains separate per editor.
- **No cross-editor sync**: Artifacts created in one IDE's conversation don't automatically sync to another. Manual copy is required for important documents.
- **Python 3.10+ required**: Won't work with older Python versions.

## 🚀 What's New in v0.5.1

- **130 MCP Tools** (up from 110 in v0.5.0)
- **Engram Ledger** — Persistent cognitive memory (`brain_write_engram`, `brain_query_engrams`)
- **Governance Dashboard** — `brain_governance_status()` for security monitoring
- **Cryptographic Audit** — SHA-256 hashed interaction log (`brain_audit_log`)
- **V3.1 Task Engine** with slot pooling and tier routing
- **Swarm Orchestration** for recursive multi-agent missions
- **Session Persistence** across conversations
- **Health Monitoring** endpoints for production use
- **E2E Test Suite** — 18/18 critical path tests passing

### The Governance Moat (v0.5.1)

| Policy | Description |
|--------|-------------|
| **Default-Deny** | All tools start with NO access |
| **Isolation Boundaries** | Tools can't see each other |
| **Immutable Audit** | SHA-256 hashed decision trail |
| **Engram Ledger** | Persistent memory ownership |

## 📜 License

MIT © Nucleus Team

---

**Built for the AI-native developer.** Star us on GitHub if Nucleus saves you from context amnesia! ⭐

