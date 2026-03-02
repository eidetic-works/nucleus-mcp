# Reddit Launch Post

## Target Subreddits
1. **r/LocalLLaMA** (Primary - highest engagement for AI tools)
2. **r/ClaudeAI** (Secondary - Claude users)
3. **r/cursor** (Secondary - Cursor users)

---

## POST: r/LocalLLaMA

### Title Options (Pick one)
A) `I built an MCP server that syncs Cursor, Claude Desktop, and Windsurf with one brain [Open Source]`

B) `Tired of re-explaining context to different AI tools? I built Nucleus - cross-platform AI memory sync`

C) `After using 5 AI tools daily, I built the missing piece: a universal brain that syncs them all`

**Recommended: Option A** (specific, technical, mentions open source)

---

### Post Body

```markdown
**The Problem**

I use Cursor for coding, Claude Desktop for thinking, and Windsurf for exploration. But every time I switch tools, I lose context. I'd tell Claude about an architecture decision, then Cursor would have no idea.

Copy-pasting context between tools is tedious and error-prone. So I built something to fix it.

**What I Built**

[Nucleus OS](https://github.com/eidetic-works/mcp-server-nucleus) is an MCP server that creates a shared brain (`.brain/` folder) across all your AI tools.

- Tell Claude about a decision → Cursor knows it
- Make a plan in Windsurf → Claude remembers it
- One brain. All your tools.

**Features**

- **Cross-Platform Sync**: Works with Cursor, Claude Desktop, Windsurf, and any MCP-compatible tool
- **140+ MCP Tools**: Memory, tasks, sessions, orchestration, security
- **Local-First**: Your data stays on your machine. No cloud.
- **Intent-Aware Locking**: When one agent locks a file, others see WHO locked it, WHEN, and WHY
- **Audit Trail**: Every decision logged for traceability

**How It's Different from OpenClaw**

OpenClaw is great for running multiple agents on their platform. But if you use Cursor AND Claude AND Windsurf (different tools), OpenClaw doesn't help.

Nucleus connects different platforms. Use OpenClaw for agent teams. Use Nucleus for your universal brain.

**Quick Start**

```bash
pip install mcp-server-nucleus
nucleus-init
```

Add to your Claude Desktop config and restart. Done.

**It's Open Source**

MIT licensed. No catch. No waitlist.

GitHub: https://github.com/eidetic-works/mcp-server-nucleus

**What I'm Looking For**

- Feedback on the concept
- Feature requests
- Beta testers who use multiple AI tools daily
- Contributors (Python, MCP protocol experience)

Happy to answer any questions!
```

---

## POST: r/ClaudeAI

### Title
`I built an MCP server that syncs Claude Desktop with Cursor and Windsurf - one shared brain [Open Source]`

### Body
```markdown
**TL;DR**: Nucleus syncs your Claude Desktop context with Cursor, Windsurf, and other MCP tools. MIT licensed.

**The Pain Point**

I love Claude Desktop, but I also use Cursor for coding and Windsurf for exploration. The problem? They don't share memory.

Every time I switch from Claude to Cursor, I have to re-explain everything. It's like having three assistants who never talk to each other.

**The Solution**

Nucleus creates a shared `.brain/` folder that all your MCP-compatible tools can read and write to.

- Decisions stored in Claude → Cursor can access them
- Tasks created in Windsurf → Claude knows about them
- One brain across all your AI tools

**Quick Setup**

```bash
pip install mcp-server-nucleus
nucleus-init
```

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {"NUCLEAR_BRAIN_PATH": "/path/to/your/project/.brain"}
    }
  }
}
```

Restart Claude Desktop. Done.

**Why I Built This**

I'm a solo dev who was frustrated with context loss. After building 140+ MCP tools for my own use, I decided to open source the whole thing.

GitHub: https://github.com/eidetic-works/mcp-server-nucleus

MIT licensed. No waitlist. No catch.

Questions welcome!
```

---

## POST: r/cursor

### Title
`Built an MCP server that syncs Cursor with Claude Desktop and Windsurf - shared memory across tools [Open Source]`

### Body
```markdown
**Problem**: I use Cursor for coding but also Claude Desktop for reasoning and Windsurf for exploration. They don't share context.

**Solution**: Nucleus - an MCP server that creates a shared brain across all your AI tools.

**How it works**:
1. `pip install mcp-server-nucleus`
2. Add to `~/.cursor/mcp.json`
3. Done - your Cursor now shares memory with Claude Desktop, Windsurf, etc.

**What this enables**:
- Architecture decision in Claude → Cursor knows about it
- Task list in Windsurf → Cursor can see it
- No more copy-pasting context between tools

**It's different from OpenClaw**: OpenClaw syncs OpenClaw agents. Nucleus syncs *different* tools together.

MIT licensed, open source: https://github.com/eidetic-works/mcp-server-nucleus

Looking for feedback and beta testers who use multiple AI coding tools!
```

---

## Engagement Strategy

### First Hour
- Reply to EVERY comment within 30 minutes
- Thank people for feedback
- Answer technical questions thoroughly
- Note feature requests ("great idea, added to roadmap!")

### Common Questions to Prepare For

**Q: How is this different from just using CLAUDE.md?**
A: CLAUDE.md is static text. Nucleus is a dynamic database with 140+ tools. It can store decisions, track tasks, manage sessions, and sync across multiple AI tools automatically.

**Q: Does this work with [specific tool]?**
A: If it supports MCP protocol, yes! Currently tested with Claude Desktop, Cursor, and Windsurf. Adding more integrations based on demand.

**Q: Why should I trust this with my data?**
A: Everything stays local in your `.brain/` folder. MIT licensed, you can audit the code. No telemetry, no cloud, no accounts required.

**Q: What about OpenClaw?**
A: Different tools for different problems. OpenClaw = run agent teams on their platform. Nucleus = sync different AI tools with one brain. They can work together.

---

## Timing

**Best time to post**: Tuesday-Thursday, 9-11am PST (peak engagement)

**Sequence**:
1. r/LocalLLaMA (largest, most active)
2. Wait 2-3 hours, gauge reception
3. r/ClaudeAI (if LocalLLaMA reception positive)
4. r/cursor (cross-post)

---

*Save this file. Execute on launch day.*
