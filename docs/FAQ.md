# Nucleus FAQ

**Last Updated:** January 26, 2026  
**Version:** 0.5.1

---

## General Questions

### What is Nucleus?

Nucleus is **The Agent Control Plane** - a governance layer for AI agents that use the Model Context Protocol (MCP). It provides:

- **Default-Deny Security**: No tool executes without explicit policy approval
- **Engram Ledger**: Persistent memory that survives across sessions
- **Cryptographic Audit**: Every interaction hashed with SHA-256
- **130 MCP Tools**: Task orchestration, multi-agent federation, depth tracking

### How is Nucleus different from CLAUDE.md?

| Aspect | CLAUDE.md | Nucleus |
|--------|-----------|---------|
| Type | Static context file | Active runtime |
| Enforcement | Honor system | Default-deny policies |
| Memory | None | Engram Ledger |
| Audit | None | SHA-256 hashed trail |
| Tools | 0 | 130 MCP tools |

CLAUDE.md tells agents what to do. Nucleus **enforces** what they can do.

### Is Nucleus open source?

The PyPI package (`mcp-server-nucleus`) is publicly available. The source code follows the **Citadel Strategy** - selective access for validated partners. Contact us for enterprise licensing.

---

## Installation

### How do I install Nucleus?

```bash
pip install mcp-server-nucleus
```

### What Python version is required?

Python 3.10 or higher.

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
pip install --upgrade mcp-server-nucleus
```

### Tests failing

Run the test suite to verify your installation:
```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

### How do I reset my brain state?

Delete or rename the `.brain/` directory and restart:
```bash
mv .brain .brain.backup
# Nucleus will create a fresh .brain/ on next run
```

---

## Security

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
- **Issues**: [GitHub Issues](https://github.com/NucleusSovereign/mcp-server-nucleus/issues)
- **Discord**: Coming soon
- **Email**: hello@nucleusos.dev

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

*FAQ maintained by the Nucleus team.*
