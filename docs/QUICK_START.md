# Nucleus Quick Start Guide
## Get Running in 5 Minutes
### v1.0.9 | The Agent Control Plane

---

## 🚀 Installation

### Option 1: pip (Recommended)

```bash
pip install nucleus-mcp
```

### Option 2: From Source

```bash
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd nucleus-mcp
pip install -e .
```

### Option 3: Docker

```bash
docker pull ghcr.io/eidetic-works/nucleus-mcp:latest
docker run -v ~/.brain:/data/.brain nucleus
```

---

## ⚙️ Configuration

### Recommended: one command

```bash
nucleus init
```

This seeds `.brain/` and auto-configures every MCP client it finds — Claude
Desktop, Claude Code, Cursor, Windsurf, and Antigravity — backing up each config
file it edits. Then restart your client. Already initialized? Run `nucleus setup`
(add `--dry-run` to preview, `--force` to overwrite) to (re)configure clients
without re-seeding the brain.

That's all most setups need — skip to **Verify Installation** below.

---

### Manual alternative

If you'd rather edit configs by hand, or a client wasn't auto-detected:

**1. Pick a brain path** (optional — Nucleus defaults to `$HOME/.nucleus/brain`):

```bash
export NUCLEUS_BRAIN_PATH="$HOME/.brain"   # add to ~/.zshrc or ~/.bashrc
mkdir -p ~/.brain
```

**2. Add the server** to your MCP client config — **Claude Desktop**
(`~/Library/Application Support/Claude/claude_desktop_config.json`), **Cursor**
(`.cursor/mcp.json`), or **Claude Code** (`.mcp.json`):

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "nucleus-mcp"
    }
  }
}
```

**3. Restart your MCP client** to load Nucleus.

---

## ✅ Verify Installation

Run these commands in your AI chat to verify Nucleus is working:

```
brain_health()
```

You should see:

```
💚 NUCLEUS HEALTH CHECK
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📋 VERSION
   Nucleus: 1.0.9
   ...

✅ System is healthy
```

---

## 🎯 Your First 5 Minutes

### 1. Start a Session

```
brain_session_start()
```

This shows your current context, pending tasks, and recommendations.

### 2. Create Your First Task

```
brain_add_task(description="Learn Nucleus basics", priority=1)
```

### 3. View Your Tasks

```
brain_list_tasks()
```

### 4. Complete a Task

```
brain_complete_task(task_id="YOUR_TASK_ID")
```

### 5. Check the Dashboard

```
brain_dashboard()
```

---

## 🔧 Core Tools

| Tool | Description |
|------|-------------|
| `brain_session_start()` | Start session, get context |
| `brain_add_task()` | Create a new task |
| `brain_list_tasks()` | View all tasks |
| `brain_claim_task()` | Claim a task to work on |
| `brain_complete_task()` | Mark task as done |
| `brain_orchestrate()` | Auto-assign best task |
| `brain_dashboard()` | View system status |
| `brain_health()` | Check system health |

---

## � Checkpoint & Handoff (V3.1)

Nucleus can save and resume long-running tasks across sessions, agents, and IDEs.

### Save Progress Before Session End

```
brain_checkpoint_task(
    task_id="task_123",
    step=3,
    progress_percent=60,
    context="Completed API integration, starting tests",
    artifacts=["src/api.py", "tests/test_api.py"]
)
```

### Resume in a New Session

```
brain_resume_from_checkpoint(task_id="task_123")
```

Returns the checkpoint data, context summary, and resume instructions.

### Generate Handoff Summary

Before handing off to another agent or ending a session:

```
brain_generate_handoff_summary(
    task_id="task_123",
    summary="API integration complete, 3 of 5 tests passing",
    key_decisions=["Used REST over GraphQL", "SQLite for MVP"],
    handoff_notes="Next agent should fix the auth test"
)
```

### When to Use Checkpoints

| Scenario | Tool |
|----------|------|
| Session ending | `brain_checkpoint_task()` |
| Hitting rate limits | `brain_checkpoint_task()` |
| Handing off to another agent | `brain_generate_handoff_summary()` |
| Starting a new session | `brain_resume_from_checkpoint()` |
| Approaching reset cycle | `brain_checkpoint_task()` + `brain_generate_handoff_summary()` |

---

## �📁 Understanding .brain/

Your `.brain/` folder structure:

```
.brain/
├── ledger/
│   ├── tasks.json      # Your task queue
│   └── events.jsonl    # Activity log
├── sessions/           # Saved sessions
├── slots/
│   └── registry.json   # Agent slots
├── artifacts/          # Generated files
└── state.json          # Current state
```

---

## 🎓 Next Steps

1. **Read the full docs:** `brain_version()` for links
2. **Explore tools:** There are 110+ tools available
3. **Try autopilot:** `brain_autopilot_sprint_v2()` for autonomous execution
4. **Save sessions:** `brain_save_session()` to preserve context

---

## 🆘 Troubleshooting

### "NUCLEUS_BRAIN_PATH not set"

```bash
export NUCLEUS_BRAIN_PATH="$HOME/.brain"
mkdir -p ~/.brain
```

### "Brain path does not exist"

```bash
mkdir -p ~/.brain/ledger ~/.brain/sessions ~/.brain/slots
```

### MCP Server Not Loading

1. Check your config file syntax (valid JSON)
2. Verify the path to `nucleus-mcp` is correct
3. Restart your MCP client

### Need Help?

- GitHub Issues: https://github.com/eidetic-works/nucleus-mcp/issues
- Discord: https://discord.gg/RJuBNNJ5MT

---

## 🧠 The Trinity Framework

Nucleus is built on three pillars:

```
ORCHESTRATION + CHOREOGRAPHY + CONTEXT = NUCLEUS
   (control)      (autonomy)     (memory)
```

- **Orchestration:** Who does what (task assignment, scheduling)
- **Choreography:** How it happens (autonomous execution)
- **Context:** What we know (Persistent Engrams)

This is what makes Nucleus different from task managers (no autonomy) or AutoGPT (no persistent state).

---

*Happy orchestrating! 🚀*
