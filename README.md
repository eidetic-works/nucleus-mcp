# 🧠 Nucleus MCP

[![PyPI version](https://badge.fury.io/py/nucleus-mcp.svg)](https://badge.fury.io/py/nucleus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)](https://modelcontextprotocol.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **The Universal Brain for AI Agents** — One brain that syncs Cursor, Claude Desktop, Windsurf, and any MCP-compatible tool.

---

## 🎯 The Problem

You use **multiple AI tools** daily:
- **Cursor** for coding
- **Claude Desktop** for thinking
- **Windsurf** for exploration
- **ChatGPT** for quick answers

**But they don't share memory.**

Every time you switch tools, you lose context. You re-explain decisions. You repeat yourself constantly.

---

## ✨ The Solution

**Nucleus syncs them with one brain.**

```
Tell Claude about a decision → Cursor knows it
Make a plan in Windsurf → Claude remembers it
One brain. All your tools.
```

<!-- Demo video: https://github.com/eidetic-works/nucleus-mcp/releases - see demo_video.mp4 -->

---

## 🚀 What Makes Nucleus Different

| Feature | Other Solutions | Nucleus |
|---------|-----------------|---------|
| **Cross-Platform Sync** | Single platform only | ✅ Syncs ALL your AI tools |
| **Sovereignty** | Cloud-dependent | ✅ 100% local, your data stays on your machine |
| **Protocol** | Proprietary | ✅ MCP standard (Anthropic-backed) |
| **Security** | Often misconfigured | ✅ Secure by default, audit logs included |
| **Lock-in** | Platform-specific | ✅ MIT license, open standard |

---

## ⚡ Quick Start (2 Minutes)

### 1. Install

```bash
pip install nucleus-mcp
```

### 2. Initialize

```bash
nucleus-init
```

This creates your `.brain/` folder and auto-configures Claude Desktop.

### 3. Restart Claude Desktop

Then try:
> "What decisions have we made about the architecture?"

Claude will now remember across sessions!

---

## 🔧 Manual Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/project/.brain"
      }
    }
  }
}
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/project/.brain"
      }
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/project/.brain"
      }
    }
  }
}
```

---

## 🛠 Core Tools

### Memory
| Tool | Description |
|------|-------------|
| `brain_write_engram` | Store persistent knowledge |
| `brain_query_engrams` | Retrieve knowledge |
| `brain_audit_log` | View decision history |

### Sync (Multi-Agent)
| Tool | Description |
|------|-------------|
| `brain_sync_now` | Manually trigger brain sync |
| `brain_sync_status` | Check sync state and conflicts |
| `brain_sync_auto` | Enable/disable auto-sync |
| `brain_identify_agent` | Register agent identity |

### State Management
| Tool | Description |
|------|-------------|
| `brain_get_state` | Get current project state |
| `brain_set_state` | Update project state |
| `brain_list_artifacts` | List all artifacts |

### Hypervisor (Security)
| Tool | Description |
|------|-------------|
| `lock_resource` | Lock file/folder (immutable) |
| `unlock_resource` | Unlock resource |
| `watch_resource` | Monitor file changes |
| `hypervisor_status` | View security state |

---

## 🔄 Multi-Agent Sync (The Killer Feature)

**Multiple agents, one brain.**

```python
# Agent A (Claude Desktop) makes a decision
brain_sync_now()  # Syncs to shared .brain/

# Agent B (Cursor) automatically sees it
brain_sync_status()  # Shows last sync, active agents
```

**Features:**
- **Intent-Aware Locking** — Files locked with WHO/WHEN/WHY metadata
- **Conflict Detection** — Last-write-wins with manual resolution option
- **Auto-Sync** — Optional file watcher for real-time sync
- **Audit Trail** — Every sync logged to `events.jsonl`

---

## ⚔️ Comparison: Nucleus vs Alternatives

| | OpenClaw | Claude Code | Nucleus |
|---|----------|-------------|---------|
| **What it syncs** | OpenClaw → OpenClaw | Claude → Claude | **Everything ↔ Everything** |
| **Cross-platform** | ❌ | ❌ | ✅ |
| **Local-first** | ⚠️ Some cloud | ⚠️ Some cloud | ✅ 100% local |
| **MCP Native** | ❌ Custom protocol | ⚠️ Limited | ✅ Full MCP |
| **Open Source** | ✅ MIT | ❌ Closed | ✅ MIT |

**OpenClaw is great for multi-agent teams on their platform.**
**Nucleus connects ALL your platforms with one brain.**

---

## 📁 The `.brain/` Folder

Nucleus stores everything in a `.brain/` folder in your project:

```
.brain/
├── config/
│   └── nucleus.yaml      # Configuration
├── ledger/
│   ├── state.json        # Current state
│   ├── events.jsonl      # Audit log
│   └── decisions.md      # Decision history
├── artifacts/
│   └── ...               # Your stored knowledge
└── sessions/
    └── ...               # Saved sessions
```

**Your data. Your machine. Your control.**

---

## 🤝 Contributing

We're building the universal brain for AI agents. Join us!

- **🐛 Found a bug?** Open an [Issue](https://github.com/eidetic-works/nucleus-mcp/issues)
- **💡 Feature idea?** Start a [Discussion](https://github.com/eidetic-works/nucleus-mcp/discussions)
- **🔧 Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)

### Development Setup

```bash
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd nucleus-mcp
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/
```

---

## 📜 License

MIT © Nucleus Team

---

## ⭐ Support

**Star us on GitHub if Nucleus saves you from context amnesia!**

One brain. All your AI tools. No more repeating yourself.

---

*Built for the AI-native developer.*
