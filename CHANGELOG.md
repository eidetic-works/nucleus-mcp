# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-09

### 🎉 Initial Open Source Release

**The Universal Brain for AI Agents** — Cross-platform memory sync for Cursor, Claude Desktop, Windsurf, and any MCP-compatible tool.

### Added

#### Core Features
- **Persistent Memory** — `brain_write_engram` / `brain_query_engrams` for storing and retrieving knowledge
- **Audit Trail** — Immutable event log with SHA-256 integrity (`brain_audit_log`)
- **State Management** — `brain_get_state` / `brain_set_state` for project context

#### Multi-Agent Sync
- **Cross-Platform Sync** — One brain shared across Cursor, Claude Desktop, Windsurf
- **Agent Identity** — `brain_identify_agent` for tracking which agent is active
- **Manual Sync** — `brain_sync_now` to trigger immediate synchronization
- **Sync Status** — `brain_sync_status` to view sync state and active agents

#### Hypervisor (Security)
- **File Locking** — `lock_resource` / `unlock_resource` with immutable flags
- **Resource Watching** — `watch_resource` for monitoring file changes
- **Security Status** — `hypervisor_status` for system security overview

#### CLI Tools
- **Smart Init** — `nucleus-init` auto-configures Claude Desktop, Cursor, and Windsurf
- **Brain Structure** — Creates `.brain/` folder with proper structure

#### Developer Experience
- MIT License — Fully open source
- MCP Compatible — Works with any MCP-compatible client
- Local-First — Your data stays on your machine
- Zero Cloud Dependencies — No accounts, no telemetry

### Technical Details
- Python 3.10+ required
- FastMCP integration for MCP protocol
- Watchdog for file monitoring
- Pydantic for data validation

---

## Future Roadmap

### [1.1.0] - Planned
- Auto-sync with file watcher
- Conflict resolution UI
- Session persistence improvements

### [1.2.0] - Planned
- Task management system
- Multi-agent orchestration
- Decision provenance (DSoR)

### [2.0.0] - Vision
- Peer-to-peer federation
- Enterprise SSO/RBAC
- Cloud sync option (opt-in)
