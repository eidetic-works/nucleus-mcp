# Nucleus MCP: Enterprise Guide

## Overview

Nucleus MCP is designed for organizations that cannot compromise on data sovereignty. This guide covers enterprise deployment, compliance, and security features.

---

## Enterprise Features

### 🔒 Air-Gap Ready

Deploy Nucleus in fully disconnected environments:

- **Zero Cloud Calls**: No external API requests, no telemetry
- **No Internet Required**: Runs entirely on local machine
- **Portable**: Copy `.brain/` folder to any machine

```bash
# Air-gap installation
pip install nucleus-mcp --no-deps
# Or from wheel
pip install nucleus_mcp-1.0.5-py3-none-any.whl
```

### 📋 Compliance First

Built for regulated industries:

- **Full Audit Trail**: Every agent interaction logged with timestamps
- **Cryptographic Hashing**: SHA-256 signatures on critical operations
- **Decision Provenance**: Track exactly why each decision was made
- **Export Capability**: Generate compliance reports from `.brain/ledger/`

**Supported Frameworks:**
- SOC 2 Type II
- ITAR (International Traffic in Arms Regulations)
- GDPR (data never leaves your infrastructure)
- HIPAA (when deployed on compliant infrastructure)

### 👥 Team Sync (Coming Soon)

Share knowledge across your team without cloud dependencies:

- **Git-Based Sync**: Commit `.brain/` to your repo
- **Conflict Resolution**: CRDT-based merge for concurrent edits
- **Role-Based Access**: Control who can read/write engrams
- **Branch Isolation**: Separate context per feature branch

---

## Deployment Options

### Option 1: Per-Developer Installation

Each developer installs Nucleus locally:

```bash
pip install nucleus-mcp
nucleus-init
```

**Pros:** Maximum isolation, no shared state
**Cons:** No cross-team learning

### Option 2: Shared Repository

Team shares `.brain/` via git:

```bash
# In team repo
git add .brain/
git commit -m "Sync team memory"
```

**Pros:** Shared learnings, decision history
**Cons:** Merge conflicts possible

### Option 3: Network Share (Air-Gap)

Mount `.brain/` on network drive:

```bash
export NUCLEAR_BRAIN_PATH=/mnt/shared/nucleus-brain
nucleus-mcp
```

**Pros:** Real-time sharing, air-gap compatible
**Cons:** Requires file locking discipline

---

## Security Architecture

```
┌─────────────────────────────────────────┐
│          Your Infrastructure            │
│  ┌─────────────────────────────────┐    │
│  │         Nucleus MCP             │    │
│  │  ┌─────────┐  ┌─────────────┐   │    │
│  │  │ Engrams │  │ Audit Logs  │   │    │
│  │  │ (Memory)│  │ (SHA-256)   │   │    │
│  │  └─────────┘  └─────────────┘   │    │
│  │  ┌─────────────────────────┐    │    │
│  │  │    Hypervisor Layer     │    │    │
│  │  │  - Default Deny Policy  │    │    │
│  │  │  - Resource Locking     │    │    │
│  │  │  - IPC Authentication   │    │    │
│  │  └─────────────────────────┘    │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ╔═════════════════════════════════╗    │
│  ║   NO DATA LEAVES THIS BOX       ║    │
│  ╚═════════════════════════════════╝    │
└─────────────────────────────────────────┘
```

### Default Deny Policy

All mounted MCP servers start with zero permissions:
- No network access
- No filesystem access outside `.brain/`
- No cross-server communication

Trust is explicitly granted via governance rules.

### IPC Authentication

Inter-process communication secured via:
- Per-session secret tokens
- Process ID verification
- Timeout-based invalidation

---

## Support & Custom Deployments

For enterprise inquiries:

- **Email**: enterprise@nucleusos.dev
- **Custom Deployments**: On-premise installation support
- **Priority Support**: SLA guarantees available
- **Training**: Team onboarding sessions

---

## FAQ

**Q: Can Nucleus run without internet?**
A: Yes. Nucleus is 100% local-first. No cloud dependencies.

**Q: How do I export audit logs for compliance?**
A: Audit logs are in `.brain/ledger/events.jsonl`. Export with:
```bash
cp .brain/ledger/events.jsonl /path/to/compliance/report/
```

**Q: Is Nucleus HIPAA compliant?**
A: Nucleus stores all data locally. HIPAA compliance depends on your infrastructure. We provide the tools; you control the environment.

**Q: How do I integrate with existing MCP servers?**
A: Use the recursive mount feature:
```python
brain_mount_server(mount_id="my-server", command="npx", args=["my-mcp-server"])
```

---

*Nucleus MCP: The Sovereign Brain for Enterprise AI*
