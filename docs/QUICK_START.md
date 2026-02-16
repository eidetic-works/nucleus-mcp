# Nucleus MCP: Quick Start Guide

Get cross-platform AI memory syncing in under 2 minutes.

---

## Prerequisites

- Python 3.10+
- Claude Desktop, Cursor, or any MCP-compatible tool

---

## Installation

```bash
pip install nucleus-mcp
nucleus-init
```

This creates:
- `~/.brain/` directory (your sovereign brain)
- Auto-configures Claude Desktop if installed

---

## Verify Installation

```bash
# Check brain health
python -c "from mcp_server_nucleus import brain_health; print(brain_health())"
```

Expected output:
```json
{"status": "healthy", "version": "1.0.5", "brain_path": "/Users/you/.brain"}
```

---

## First Memory (Engram)

Write your first cross-platform memory:

```python
from mcp_server_nucleus import brain_write_engram

# Save a decision
brain_write_engram(
    key="tech_stack_choice",
    value="Using FastAPI + SQLite for MVP backend",
    context="Architecture",
    intensity=8
)
```

This engram is now available in **all** your MCP tools.

---

## Query Memory

Retrieve engrams by context:

```python
from mcp_server_nucleus import brain_query_engrams

# Get all Architecture decisions
engrams = brain_query_engrams(context="Architecture", min_intensity=5)
print(engrams)
```

---

## Available Contexts

| Context | Use For |
|---------|---------|
| `Feature` | Product features, implementations |
| `Architecture` | Technical decisions, stack choices |
| `Brand` | Messaging, positioning, identity |
| `Strategy` | Business decisions, roadmap |
| `Decision` | General decisions, choices made |

---

## Connect Multiple Tools

### Claude Desktop

Already configured by `nucleus-init`. Restart Claude Desktop to activate.

### Cursor

Add to your Cursor MCP config:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python",
      "args": ["-m", "mcp_server_nucleus"]
    }
  }
}
```

### Windsurf

Add to your Windsurf MCP config (same format as Cursor).

---

## Next Steps

- **[Enterprise Guide](ENTERPRISE.md)** - Air-gap deployment, compliance
- **[Competitive Analysis](COMPETITIVE_ANALYSIS.md)** - Why Nucleus
- **[Full API Reference](https://github.com/eidetic-works/nucleus-mcp#-complete-tool-reference)** - All 15+ tools

---

## Troubleshooting

### "brain_path not found"

```bash
# Manually set brain path
export NUCLEAR_BRAIN_PATH=~/.brain
```

### Import errors

```bash
# Reinstall
pip uninstall nucleus-mcp
pip install nucleus-mcp
```

### Claude Desktop not seeing Nucleus

1. Restart Claude Desktop
2. Check `~/.config/Claude/claude_desktop_config.json` includes Nucleus
3. Run `nucleus-init` again

---

## Support

- **Discord**: [Join Nucleus Vanguard](https://discord.gg/RJuBNNJ5MT)
- **GitHub Issues**: [Report a bug](https://github.com/eidetic-works/nucleus-mcp/issues)
- **Enterprise**: [enterprise@nucleusos.dev](mailto:enterprise@nucleusos.dev)

---

*The Sovereign Brain - Cross-platform AI memory that never leaves your machine.*
