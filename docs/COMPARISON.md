# Nucleus vs. The Alternatives

Choosing a persistence layer for your AI agents is a critical decision. Here is how Nucleus compares to current alternatives like **ContextStream** and **mem0**.

## At a Glance

| Feature | Nucleus MCP | ContextStream | mem0 |
|---------|-------------|---------------|------|
| **The Moat** | **Sovereign (Local-First)** | Cloud-Locked | Cloud-Managed |
| **Recall Speed** | **0.11ms (2,672x)** | ~300ms (Network) | ~400ms (Network) |
| **Governance** | **Deterministic Hypervisor** | Basic ACLs | None |
| **Data Gravity** | **Git-Native (`.brain/`)** | SaaS Database | SaaS / Vector Store |
| **Audit Path** | **Local Event Ledger** | Enterprise-Only | Partial |
| **License** | **MIT** | Proprietary | Apache 2.0 |

---

## Why Nucleus?

### 🛡️ The Sovereign Moat (Governance)
Most memory servers focus only on "remembering". Nucleus focuses on **Defensive Control**. 
Our **Deterministic Hypervisor** ensures that your agent doesn't just have context, but it also has **Boundaries**. By enforcing local file locks and resource limits at the MCP protocol level, Nucleus prevents "Agent Drift" before it hits your codebase.

### 🧠 Engrams over Memories
We use the term **Engrams** because these aren't just strings in a database. They are version-controlled units of knowledge. 
Because Nucleus stores its state in your project's `.brain/` directory, your agent's context is:
- **Git-Native:** Diffs, branches, and merges work on your memory.
- **Offline-First:** No round-trips to a cloud server.
- **Portable:** Your repo contains everything the agent needs to continue work on any machine.

### 🔒 Privacy by Design
Nucleus doesn't want your data. There is no cloud sync (unless you explicitly configure a private relay), no tracking, and no persistent identity. 
- **Rotating Pulse IDs:** Your telemetry identity self-destructs every 30 days.
- **Local Hashing:** We proxy machine identity through your project path, not your hardware.

---

## When to use others?

- **ContextStream:** If you want a managed SaaS experience and don't mind sending your code context to a third party for the sake of zero-setup sync across teams.
- **mem0:** If you need a more traditional "Memory-as-a-Service" with high-level Python APIs and managed hosting.
