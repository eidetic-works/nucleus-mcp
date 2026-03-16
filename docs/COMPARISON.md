# Nucleus vs. The Alternatives

Choosing a governance layer for your AI agents is a critical decision. Here is how Nucleus compares to current alternatives.

## At a Glance

| Feature | Nucleus | OpenClaw | ContextStream | mem0 |
|---------|---------|----------|---------------|------|
| **Architecture** | **Local-First Sovereign** | Cloud-Dependent | Cloud-Locked | Cloud-Managed |
| **Security Model** | **Default-Deny Hypervisor** | Permissive (opt-in) | Basic ACLs | None |
| **Compliance** | **4 Jurisdictions** (DORA, MAS, SOC2) | None | Enterprise-Only | None |
| **Kill Switch** | **Yes** | No | No | No |
| **Audit Trail** | **SHA-256 Hashed DSoR** | Basic Logging | Enterprise-Only | Partial |
| **Prompt Injection Defense** | **Input Sanitization** | Vulnerable (CVE-2026-*) | Unknown | None |
| **Recall Speed** | **0.11ms** | N/A | ~300ms (Network) | ~400ms (Network) |
| **Data Location** | **Your Machine** | Their Cloud | Their Cloud | Their Cloud |
| **License** | **MIT** | MIT | Proprietary | Apache 2.0 |

---

## Why Nucleus Over OpenClaw?

OpenClaw went viral for autonomous agents on messaging platforms (WhatsApp, Telegram, Discord). But its security posture has proven inadequate for production use:

- **1.5M API keys leaked** through weak default configuration
- **Sleeper agents** found in the community skills marketplace
- **Banned from Chinese government computers** due to data exfiltration risks
- **No governance layer**: agents operate without boundaries, audit trails, or kill switches
- **No compliance**: zero jurisdiction awareness, no regulatory audit capability

Nucleus was built security-first. Every agent decision is logged to an immutable Decision System of Record. The Hypervisor enforces default-deny policies before any tool executes. Four jurisdiction presets (EU-DORA, SG-MAS-TRM, US-SOC2, Global) provide out-of-the-box compliance.

**OpenClaw is fast to deploy. Nucleus is safe to deploy.**

### Migrating from OpenClaw

If you're running OpenClaw agents and need governance:

1. `pip install mcp-server-nucleus`
2. `nucleus init` — creates your local `.brain/` directory
3. Point your MCP client at Nucleus
4. Your agent now has: audit trail, kill switch, compliance, memory persistence

Nucleus detects OpenClaw environments automatically and can run alongside existing setups.

---

## Why Nucleus Over ContextStream / mem0?

### The Sovereign Moat (Governance)
Most memory servers focus only on "remembering". Nucleus focuses on **Defensive Control**.
The **Deterministic Hypervisor** ensures your agent has context AND boundaries. File locks, resource limits, and default-deny policies at the MCP protocol level prevent "Agent Drift" before it hits your codebase.

### Engrams over Memories
Nucleus stores knowledge as **Engrams** — version-controlled units with intensity scoring.
Because state lives in your project's `.brain/` directory:
- **Git-Native:** Diffs, branches, and merges work on your memory.
- **Offline-First:** No round-trips to a cloud server.
- **Portable:** Your repo contains everything the agent needs on any machine.

### Privacy by Design
Nucleus doesn't want your data. No cloud sync (unless you explicitly configure a private relay), no tracking, no persistent identity.
- **Rotating Pulse IDs:** Telemetry identity self-destructs every 30 days.
- **Local Hashing:** Machine identity proxied through project path, not hardware.

---

## When to Use Others

- **OpenClaw:** If you need messaging-app agent deployment (WhatsApp/Telegram) and can accept the security trade-offs for speed of setup.
- **ContextStream:** If you want managed SaaS and don't mind sending code context to a third party.
- **mem0:** If you need traditional "Memory-as-a-Service" with high-level Python APIs and managed hosting.
