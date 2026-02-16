# Nucleus MCP: Frequently Asked Questions

## General

### What is Nucleus MCP?

Nucleus is a local-first, cross-platform memory system for AI coding assistants. It syncs your context, decisions, and learnings across Claude Desktop, Cursor, Windsurf, and any MCP-compatible tool.

### Why should I use Nucleus instead of just using each tool separately?

Every time you switch between AI tools, you lose context. You re-explain your codebase, repeat decisions, and waste time. Nucleus creates one "brain" that all your tools share, so they remember everything together.

### Is Nucleus free?

Yes. Nucleus is MIT licensed and 100% free. No subscription, no account required, no cloud fees.

---

## Privacy & Security

### Does Nucleus send my data to the cloud?

**No.** Nucleus is 100% local-first. All your data stays in the `.brain/` folder on your machine. Zero cloud calls, zero telemetry.

### Where is my data stored?

By default, your data is stored in `~/.brain/` (or `$NUCLEAR_BRAIN_PATH` if set). This includes:
- `engrams/` - Your memories and learnings
- `ledger/` - Audit trail and task history
- `state.json` - Current session state

### Can I back up my Nucleus data?

Yes! Just copy your `.brain/` folder. You can also commit it to git for version control:

```bash
cd ~/.brain
git init
git add .
git commit -m "Backup brain"
```

### Is Nucleus HIPAA/SOC2 compliant?

Nucleus stores all data locally, which satisfies data residency requirements. Full compliance depends on your infrastructure and policies. See [ENTERPRISE.md](ENTERPRISE.md) for details.

---

## Installation

### What are the system requirements?

- Python 3.10+
- Any MCP-compatible tool (Claude Desktop, Cursor, Windsurf)
- ~10MB disk space for the package
- Minimal RAM usage (runs as a subprocess)

### I installed Nucleus but my AI tool doesn't see it

1. Restart your AI tool completely
2. Check your MCP config file includes Nucleus
3. Run `nucleus-init` again to reconfigure
4. Verify with: `python -c "from mcp_server_nucleus import brain_health; print(brain_health())"`

### How do I update Nucleus?

```bash
pip install --upgrade nucleus-mcp
```

---

## Usage

### What are "engrams"?

Engrams are Nucleus's memory units. Each engram has:
- **Key**: Unique identifier
- **Value**: The actual content/memory
- **Context**: Category (Feature, Architecture, Brand, Strategy, Decision)
- **Intensity**: Importance (1-10)

### How do I write a memory?

Via MCP tool in your AI assistant:
```
brain_write_engram(key="my_decision", value="Chose React for frontend", context="Architecture", intensity=7)
```

### How do I retrieve memories?

```
brain_query_engrams(context="Architecture", min_intensity=5)
```

This returns all Architecture engrams with intensity >= 5.

### What's the difference between contexts?

| Context | Use For | Example |
|---------|---------|---------|
| `Feature` | Product features | "Added dark mode toggle" |
| `Architecture` | Technical decisions | "Using PostgreSQL for persistence" |
| `Brand` | Messaging, positioning | "Tagline: The Sovereign Brain" |
| `Strategy` | Business decisions | "Target enterprise market first" |
| `Decision` | General choices | "Approved PR #123" |

---

## Integration

### How do I connect Cursor?

Add to your Cursor MCP config (`~/.config/cursor/mcp.json`):

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

### How do I connect Claude Desktop?

Run `nucleus-init` and restart Claude Desktop. It auto-configures.

Or manually add to `~/.config/Claude/claude_desktop_config.json`:

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

### Can I use Nucleus with multiple AI tools simultaneously?

Yes! That's the whole point. Write a memory in Claude → it's instantly available in Cursor. All tools share the same `.brain/` folder.

---

## Troubleshooting

### "Module not found" error

```bash
pip uninstall nucleus-mcp
pip install nucleus-mcp
```

### "Brain path not found"

Set the environment variable:
```bash
export NUCLEAR_BRAIN_PATH=~/.brain
```

### Engrams not syncing between tools

1. Both tools must point to the same `.brain/` path
2. Check `NUCLEAR_BRAIN_PATH` is consistent
3. Verify engrams were written: `ls ~/.brain/engrams/`

### Tests failing with import errors

This is an IDE linting issue, not a real error. Tests pass with:
```bash
PYTHONPATH=src pytest tests/
```

---

## Comparison

### How is Nucleus different from ContextStream?

| Aspect | Nucleus | ContextStream |
|--------|---------|---------------|
| Data location | 100% local | Cloud |
| Account required | No | Yes |
| Cross-platform | All MCP tools | Limited |
| Price | Free (MIT) | Paid tiers |
| Air-gap support | Yes | No |

### How is Nucleus different from OpenClaw?

| Aspect | Nucleus | OpenClaw |
|--------|---------|----------|
| Platform support | All MCP tools | Claude only |
| Security focus | Built-in | Post-breach |
| Stability | Production | "Hype stage" |
| Data sovereignty | 100% local | Cloud bridge |

---

## Contributing

### How can I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md). We welcome:
- Bug reports
- Feature requests
- Documentation improvements
- Code contributions

### Where do I report bugs?

[GitHub Issues](https://github.com/eidetic-works/nucleus-mcp/issues)

---

## Support

- **Discord**: [Nucleus Vanguard](https://discord.gg/RJuBNNJ5MT)
- **GitHub**: [Issues & Discussions](https://github.com/eidetic-works/nucleus-mcp)
- **Enterprise**: [enterprise@nucleusos.dev](mailto:enterprise@nucleusos.dev)

---

*The Sovereign Brain - Cross-platform AI memory that never leaves your machine.*
