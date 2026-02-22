# Nucleus v0.6.0 Launch Posts

**Date:** January 31, 2026  
**Narrative:** Sovereign Memory  
**Target:** r/LocalLLaMA, r/MachineLearning, Hacker News

---

## Reddit Post (r/LocalLLaMA)

### Title
**I built an MCP server that gives your AI agents sovereign memory - no cloud required**

### Body

I've been working on this for 3 months and just shipped v0.6.0.

**The Problem:**
Every AI agent framework stores context in some cloud database. Your reasoning traces, your decisions, your memories - all on someone else's server. 

**The Solution:**
Nucleus is an MCP server that runs 100% locally. Your agent's memory stays on YOUR machine.

**What it does (free tier):**

```bash
pip install mcp-server-nucleus
```

6 tools, zero cloud dependencies:

- `brain_write_engram` - Persist any memory with context tagging
- `brain_query_engrams` - Semantic search across your agent's history  
- `brain_mount_server` - Connect to other MCP servers (recursive aggregation)
- `brain_health` / `brain_version` / `brain_list_tools`

**The "Sovereign Memory" concept:**

Instead of vector similarity search (which loses structure), Nucleus uses an **Engram Ledger** - a local JSON-based memory system where every entry is:
- Categorized (Feature, Architecture, Decision, Strategy)
- Intensity-weighted (1-10 priority)
- Queryable by context

Your agent remembers WHY it made decisions, not just WHAT it decided.

**Why I built this:**

I was frustrated that every "memory" solution for agents was either:
1. A vector DB that loses semantic structure
2. A cloud service that owns your data
3. A toy that doesn't scale

Nucleus is none of those. It's a proper control plane for sovereign agents.

**What's NOT in free tier:**

Orchestration, compliance tools, and full execution require Tier 1+. Free tier is "Journal Mode" - prove the memory works, then upgrade for action.

**Links:**
- GitHub: [link]
- Docs: nucleusos.dev

Feedback welcome. Roast my architecture.

---

## Reddit Post (r/MachineLearning)

### Title
**[P] Nucleus: Local-first Decision System of Record for AI Agents**

### Body

Releasing v0.6.0 of Nucleus - an MCP server focused on **decision provenance** for AI agents.

**Core thesis:** 
AI agents need an audit trail. Not just logs - a cryptographically anchored record of WHY decisions were made.

**What makes this different:**

1. **Engram Ledger** - Structured memory with intensity weighting and context categories. Not just embeddings.

2. **Decision System of Record (DSoR)** - Every agent action can be traced back to its reasoning context.

3. **Local-first** - No cloud. Your agent's cognition stays on your machine.

4. **MCP Native** - Works with Claude, Cursor, Windsurf, any MCP client.

**Architecture:**

```
┌─────────────────────────────────────┐
│         MCP Client (Claude)         │
├─────────────────────────────────────┤
│      Nucleus Control Plane          │
│  ┌─────────┐  ┌─────────────────┐   │
│  │ Engram  │  │ Recursive       │   │
│  │ Ledger  │  │ Aggregator      │   │
│  └─────────┘  └─────────────────┘   │
├─────────────────────────────────────┤
│        Local File System            │
└─────────────────────────────────────┘
```

**Free tier (6 tools):**
- Memory write/query
- Server mounting (teaser)
- Health/version/discovery

**Paper/spec:** Working on a technical writeup about the DSoR pattern. Happy to share if there's interest.

---

## Hacker News Post

### Title
**Show HN: Nucleus – Local MCP server for sovereign AI agent memory**

### Body

Hi HN,

I built Nucleus because I wanted my AI agents to have memory that I own.

The problem: Every agent framework stores context somewhere else. RAG systems use cloud vector DBs. Memory tools phone home. Your agent's reasoning becomes someone else's training data.

Nucleus is different:
- 100% local (JSON ledger on disk)
- MCP protocol (works with Claude, etc.)
- Structured memory, not just vectors
- Decision provenance built-in

Free tier gives you 6 tools for "journal mode" - write memories, query them, mount other servers. Enough to prove sovereign memory works.

Paid tiers add orchestration, compliance, and full execution.

Why MCP? It's becoming the standard for AI tool calling. Nucleus acts as a "recursive aggregator" - mount multiple MCP servers and query them through one interface.

Technical decisions:
- JSON over SQLite (human-readable, git-friendly)
- Engram model (key/value/context/intensity)
- No embeddings by default (structure > similarity)

Would love feedback on the architecture. Particularly interested in thoughts on the decision provenance model.

GitHub: [link]
Docs: nucleusos.dev

---

## Key Talking Points

### For skeptics:
- "Why not just use a vector DB?" → Structure preservation. Vectors lose semantic relationships.
- "Why not SQLite?" → Human-readable, git-friendly, portable.
- "What about scale?" → Designed for personal/team agents, not enterprise swarms (yet).

### For enterprise interest:
- Tier 1 adds compliance tools (audit log, governance status)
- Tier 2 adds full orchestration (task scheduling, agent spawning)
- On-prem deployment available

### For developers:
- `pip install mcp-server-nucleus`
- Works with any MCP client
- Extensible via mounted servers

---

## Hashtags / Keywords

- #LocalLLaMA
- #MCP
- #AIAgents  
- #SovereignAI
- #DecisionProvenance
- #LocalFirst

---

*Prepared by Titan for v0.6.0 launch*
