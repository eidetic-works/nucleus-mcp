# Nucleus Launch Package v1

**Status:** STRATEGIC DECISION  
**Date:** January 30, 2026  
**Decision Authority:** Founder

---

## The Core Question

> "What is the correct toolset to package for our first launch?"

## The Answer

**BOTH verifiability AND product-market fit, combined:**

1. **PMF is the SELECTOR** — What solves real problems?
2. **Verifiability is the FILTER** — What works predictably?
3. **"One Story" is the PACKAGE** — What's memorable?

---

## The Decision Framework: "Verified Value"

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAUNCH PACKAGE DECISION                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   135 Tools                                                      │
│       │                                                          │
│       ▼                                                          │
│   ┌─────────────────┐                                           │
│   │  PMF FILTER     │  "Does it solve a real problem?"          │
│   │  (Value-First)  │                                           │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼ (~40 tools)                                        │
│   ┌─────────────────┐                                           │
│   │ VERIFY FILTER   │  "Does it work in all IDEs?"              │
│   │ (Reliability)   │                                           │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼ (~20 tools)                                        │
│   ┌─────────────────┐                                           │
│   │  STORY FILTER   │  "Can I demo in 60 seconds?"              │
│   │  (Memorable)    │                                           │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼ (5-7 tools)                                        │
│   ┌─────────────────┐                                           │
│   │  LAUNCH PACKAGE │  "Govern Your Agents in 60 Seconds"       │
│   └─────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Launch Story: "Govern Your Agents in 60 Seconds"

### Primary Narrative (5 tools)

| Step | Tool | What It Does | Demo Time |
|------|------|--------------|-----------|
| 1 | `brain_mount_server` | Mount an external MCP server | 10s |
| 2 | `brain_governance_status` | Show it's sandboxed (Default-Deny) | 10s |
| 3 | `brain_write_engram` | Remember a decision persistently | 15s |
| 4 | `brain_query_engrams` | Recall it in a new session | 15s |
| 5 | `brain_audit_log` | Show the cryptographic audit trail | 10s |

**Total: 60 seconds, one story, five tools.**

### Supporting Cast (15 tools for docs)

| Category | Tools | Purpose |
|----------|-------|---------|
| **Mounting** | `brain_unmount_server`, `brain_list_mounted`, `brain_discover_mounted_tools` | Recursive Aggregator |
| **Memory** | `brain_search_memory`, `brain_read_memory` | Persistent context |
| **Tasks** | `brain_add_task`, `brain_list_tasks`, `brain_get_next_task`, `brain_update_task` | Workflow |
| **Observability** | `brain_health`, `brain_version`, `brain_dashboard` | Status |
| **DSoR (v0.6.0)** | `brain_dsor_status`, `brain_list_decisions` | Decision provenance |

---

## Tool Tiers (Post-Launch)

### Tier 1: Free (Launch Package)
- 20 tools as defined above
- Unlimited mounts
- Local .brain/ storage
- Community support

### Tier 2: Pro ($29/month)
- All Free features +
- Token metering (`brain_metering_summary`)
- IPC security (`brain_ipc_tokens`)
- Decision provenance (`brain_list_decisions`)
- Email support

### Tier 3: Enterprise (Custom)
- All Pro features +
- Federation (`brain_federation_*`)
- SSO/RBAC (roadmap)
- SLA + priority support

---

## Verification Matrix (To Complete)

| Tool | Claude Desktop | Windsurf | Antigravity | Unit Tests | Launch? |
|------|---------------|----------|-------------|------------|---------|
| `brain_mount_server` | ⬜ | ⬜ | ⬜ | ✅ | ⬜ |
| `brain_governance_status` | ⬜ | ⬜ | ⬜ | ✅ | ⬜ |
| `brain_write_engram` | ⬜ | ⬜ | ⬜ | ✅ | ⬜ |
| `brain_query_engrams` | ⬜ | ⬜ | ⬜ | ✅ | ⬜ |
| `brain_audit_log` | ⬜ | ⬜ | ⬜ | ✅ | ⬜ |

**Action:** Manually verify each tool in each IDE. Only tools with 4/4 ✅ launch.

---

## Other Strategic Questions (Answered)

### Q1: Pricing model?
**A:** Freemium with metered Pro tier. Free for adoption, Pro for revenue.

### Q2: Which IDE first?
**A:** Claude Desktop (Anthropic owns MCP), then Windsurf.

### Q3: How to handle 135 tools?
**A:** Tool Router Pattern. Group into ~10 capabilities, not 135 tools.

### Q4: GTM motion?
**A:** Developer-first PLG. Reddit/HN → PyPI → Influencers → Discord.

### Q5: vs CLAUDE.md differentiation?
**A:** "Context vs Control" — CLAUDE.md is static context, Nucleus is dynamic control.

### Q6: Key metric?
**A:** Active Mounts (weekly). Not downloads, not stars.

### Q7: Open source strategy?
**A:** Open Core. Core 20 tools open, metering/federation proprietary.

### Q8: vs LangGraph/CrewAI?
**A:** "Protocol layer, not framework." Complementary, not competitive.

### Q9: Security disclosure?
**A:** CVE + transparent disclosure. Already doing this (CVE-2026-001).

### Q10: Minimum team?
**A:** Solo founder + AI for v1. First hire: community manager at 1000 users.

### Q11: Wait for MCP 2.0?
**A:** Ship now. First mover > perfect timing.

### Q12: Biggest risk?
**A:** Complexity paralysis. Solution: One story, 5 tools, 60 seconds.

---

## Immediate Actions

1. **[ ] Complete verification matrix** — Test 5 core tools in all IDEs
2. **[ ] Record 60-second demo video** — The launch story
3. **[ ] Write landing page copy** — "Govern Your Agents in 60 Seconds"
4. **[ ] Prepare Reddit/HN post** — Authority framing, not hype
5. **[ ] Set up metering for Pro tier** — v0.6.0 DSoR enables this

---

## The Final Word

> "135 tools is a moat. 5 tools is a launch."

Ship the story, not the platform. The other 130 tools are there for power users to discover. But the launch is **ONE STORY, FIVE TOOLS, SIXTY SECONDS.**

---

*Strategic decision recorded January 30, 2026.*
