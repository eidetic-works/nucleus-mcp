# Nucleus FAQ

**Last Updated:** April 7, 2026  
**Version:** 1.8.8

---

## General Questions

### What is Nucleus?

Nucleus is **The Agent Control Plane** - a governance layer for AI agents that use the Model Context Protocol (MCP). It provides:

- **Default-Deny Security**: No tool executes without explicit policy approval
- **Engram Ledger**: Persistent memory that survives across sessions
- **Cryptographic Audit**: Every interaction hashed with SHA-256
- **170+ MCP Tools**: Task orchestration, multi-agent federation, depth tracking
- **Compliance Frameworks**: EU DORA, SG MAS-TRM, US SOC2 out of the box

### How is Nucleus different from CLAUDE.md?

| Aspect | CLAUDE.md | Nucleus |
|--------|-----------|---------|
| Type | Static context file | Active runtime |
| Enforcement | Honor system | Default-deny policies |
| Memory | None | Engram Ledger |
| Audit | None | SHA-256 hashed trail |
| Tools | 0 | 170+ MCP tools |

CLAUDE.md tells agents what to do. Nucleus **enforces** what they can do.

### Is Nucleus open source?

Yes. Nucleus is open source under the MIT license. Install via PyPI (`pip install nucleus-mcp`) or clone the repository.

---

## Installation

### How do I install Nucleus?

```bash
pip install nucleus-mcp
```

### What Python version is required?

Python 3.9 or higher.

### How do I configure my MCP client?

Add to your MCP client configuration (example for Claude Desktop):

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/.brain"
      }
    }
  }
}
```

---

## Core Concepts

### What is the `.brain/` directory?

The `.brain/` directory is where Nucleus stores all persistent state:

```
.brain/
├── ledger/
│   ├── state.json          # Session state
│   ├── tasks.json          # Task queue
│   ├── events.jsonl        # Event log
│   ├── engrams.json        # Persistent memory
│   └── interaction_log.jsonl # Audit trail
├── sessions/               # Session snapshots
├── artifacts/              # Research, strategy docs
└── archive/                # Archived files
```

### What is an Engram?

An Engram is a persistent memory unit with:

- **Key**: Unique identifier (e.g., "auth_architecture")
- **Value**: The memory content (include reasoning)
- **Context**: Category (Feature, Architecture, Brand, Strategy, Decision)
- **Intensity**: 1-10 priority (10 = critical constraint)

Example:
```python
brain_write_engram(
    key="no_openai",
    value="Budget constraint - Gemini only because cost",
    context="Decision",
    intensity=10
)
```

### What is Default-Deny?

Default-Deny means every tool call is blocked by default unless explicitly allowed by policy. This prevents:

- Unauthorized file access
- Unintended external API calls
- Agent scope creep

---

## Troubleshooting

### "NUCLEAR_BRAIN_PATH environment variable not set"

Set the environment variable to point to your `.brain/` directory:

```bash
export NUCLEAR_BRAIN_PATH=/path/to/your/.brain
```

Or in your MCP client config:
```json
"env": {
  "NUCLEAR_BRAIN_PATH": "/path/to/your/.brain"
}
```

### "Tool not found" errors

Ensure you're running the latest version:
```bash
pip install --upgrade nucleus-mcp
```

### Tests failing

Run the test suite to verify your installation:
```bash
python -m pytest tests/ --ignore=tests/e2e -q
```

### How do I reset my brain state?

Delete or rename the `.brain/` directory and restart:
```bash
mv .brain .brain.backup
# Nucleus will create a fresh .brain/ on next run
```

---

## Security

### How is Nucleus different from OpenClaw?

Nucleus and OpenClaw both provide agent memory, but they differ fundamentally in security posture:

| | Nucleus | OpenClaw |
|---|---------|----------|
| Security model | Default-deny, governance-first | Permissive, no governance |
| Audit trail | Cryptographic (SHA-256 chain) | Basic logging |
| Kill switch | Yes (emergency halt) | No |
| Compliance | EU DORA, SG MAS-TRM, SOC2 | None |
| Credential scanning | Built-in | None |

See [COMPARISON.md](./COMPARISON.md) for a detailed comparison.

### Is Nucleus secure?

Nucleus was designed security-first. Key protections include:

- **Default-deny policies** enforced at the runtime level
- **Red/blue governance modes** for production vs development
- **Kill switch** for emergency halt of all agent operations
- **Cryptographic audit trail** with SHA-256 hash chain
- **Credential scanning** in engram content
- **Circuit breakers** for fault isolation

See [SECURITY_WHITEPAPER.md](./SECURITY_WHITEPAPER.md) for the full security architecture.

### How secure is the audit trail?

Every interaction is hashed with SHA-256 and stored in `interaction_log.jsonl`. The hash chain makes tampering detectable - any modification breaks subsequent hashes.

### Can agents bypass Default-Deny?

No. Default-Deny is enforced at the runtime level, not via prompts. An agent cannot "convince" Nucleus to bypass security policies.

### Where is my data stored?

All data stays local in your `.brain/` directory. Nucleus never sends data to external servers unless you explicitly configure external integrations.

---

## Advanced

### How do I mount external MCP servers?

```python
brain_mount_server(
    name="my-server",
    command="npx",
    args=["-y", "@my-org/mcp-server"]
)
```

### How do I query the audit log?

```python
brain_audit_log(limit=50)  # Get last 50 interactions
```

### How do I export my brain state?

```python
brain_export(format="json")  # Export full state
```

---

## Getting Help

- **Documentation**: [docs/](./docs/)
- **Issues**: [GitHub Issues](https://github.com/eidetic-works/nucleus-mcp/issues)
- **Discord**: Coming soon
- **Email**: hello@nucleusos.dev

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

*FAQ maintained by the Nucleus team.*
