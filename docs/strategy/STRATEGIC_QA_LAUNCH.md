# Nucleus Launch: Strategic Q&A

**Date:** January 30, 2026  
**Purpose:** Comprehensive answers to strategic questions for launch

---

## THE CORE QUESTION

> "What is the correct toolset to package for our first launch?"

### ANSWER

**BOTH verifiability AND PMF, combined:**

1. **PMF is the SELECTOR** — What solves real problems?
2. **Verifiability is the FILTER** — What works predictably across IDEs?
3. **"One Story" is the PACKAGE** — What's memorable in 60 seconds?

**Result:** 5-7 tools that tell ONE story, not 135 tools that tell none.

---

## STRATEGIC QUESTIONS & ANSWERS

### Product & Packaging

| # | Question | Answer |
|---|----------|--------|
| 1 | How many tools for launch? | **5-7 core tools** that tell one story |
| 2 | Should it be verifiability-first? | Verifiability is the FILTER, not the selector |
| 3 | Should it be PMF-first? | PMF is the SELECTOR, not the only criterion |
| 4 | How to handle 135 tools? | **Tool Router Pattern** - group into 10 capabilities |
| 5 | Which 5 tools for launch story? | mount, governance, engram write/query, audit |

### Pricing & Business Model

| # | Question | Answer |
|---|----------|--------|
| 6 | Charge from day 1 or freemium? | **Freemium** with metered Pro tier |
| 7 | Free tier limits? | 100 mounts/month, core 20 tools |
| 8 | Pro tier pricing? | **$29/month** - DSoR + metering + unlimited |
| 9 | Enterprise tier? | Custom ($500-5000/mo) based on team size |
| 10 | Upgrade trigger? | Usage-based: soft block at 100 mounts |

### Go-To-Market

| # | Question | Answer |
|---|----------|--------|
| 11 | Which IDE first? | **Claude Desktop** (Anthropic owns MCP), then Windsurf |
| 12 | GTM motion? | **Developer-first PLG** - HN/Reddit → PyPI → Discord |
| 13 | Launch day/time? | **Tuesday 10am PT** (catches US + EU) |
| 14 | Product Hunt? | No for v1, Yes for v1.1 with polished UI |
| 15 | Key metric? | **Active Mounts (weekly)** - not downloads/stars |

### Differentiation

| # | Question | Answer |
|---|----------|--------|
| 16 | vs CLAUDE.md? | **"Context vs Control"** - static context vs dynamic governance |
| 17 | vs LangGraph/CrewAI? | **"Protocol layer, not framework"** - complementary |
| 18 | Competitive moat? | Speed + Community + Open Core |
| 19 | How to prevent copycats? | First mover + brand recognition + community |

### Security & Trust

| # | Question | Answer |
|---|----------|--------|
| 20 | Security disclosure? | **CVE + transparent disclosure** (already doing!) |
| 21 | Legal requirements? | Privacy Policy + ToS + MIT License (templates ok) |
| 22 | SOC2/HIPAA? | Enterprise tier only, not v1 |

### Team & Resources

| # | Question | Answer |
|---|----------|--------|
| 23 | Minimum team for launch? | **Solo founder + AI** for v1 |
| 24 | First hire? | Community manager at 1000 users |
| 25 | When to raise funding? | After PMF validation (500+ active users in 60 days) |
| 26 | Funding target? | $500K-1M seed at $5M valuation |

### Launch Execution

| # | Question | Answer |
|---|----------|--------|
| 27 | Wait for MCP 2.0? | **Ship now** - first mover > perfect timing |
| 28 | Biggest risk? | **Complexity paralysis** - 135 tools feels overwhelming |
| 29 | How to validate PMF? | 5-10 power users, ask "would you pay $29/mo?" |
| 30 | 30-day post-launch plan? | Fix bugs → add feature → case study → Pro launch |

### Success Metrics

| # | Question | Answer |
|---|----------|--------|
| 31 | Success in 30 days? | Installs: 500+, Mounts: 100+, Stars: 200+ |
| 32 | Success criteria? | 2/3 metrics hit = success, 0/3 = pivot |
| 33 | CAC target? | **$0** (PLG, no sales team for v1) |

### Risk & Contingency

| # | Question | Answer |
|---|----------|--------|
| 34 | What if MCP fails? | **Protocol agnosticism** - adapter pattern for new protocols |
| 35 | Negative feedback handling? | Respond within 1 hour, fix within 24 hours |
| 36 | Technical debt? | 135 tools without unified error handling (fix post-launch) |

### Exit Strategy

| # | Question | Answer |
|---|----------|--------|
| 37 | Exit paths? | Acqui-hire (Anthropic), Acquisition (GitHub), or $10M ARR |
| 38 | Valuation target? | $5M seed → $50M Series A at $10M ARR |

### Technical Strategy

| # | Question | Answer |
|---|----------|--------|
| 39 | Versioning strategy? | Semver + deprecation warnings (2 releases before removal) |
| 40 | Self-hosted vs cloud? | Self-hosted first (pip), cloud sync for teams in v2 |
| 41 | User data/privacy? | Local-first, no telemetry by default, GDPR compliant |
| 42 | Python version support? | 3.10+ only (3.10, 3.11, 3.12 test matrix) |
| 43 | MCP protocol changes? | Adapter pattern + version detection + graceful degradation |
| 44 | CLI vs IDE only? | Both - CLI for power users/CI, IDE for daily use |

### Documentation & Community

| # | Question | Answer |
|---|----------|--------|
| 45 | i18n strategy? | English-only for v1, community translations welcome |
| 46 | Documentation tiers? | Quick Start → Core Concepts → Full API → Architecture |
| 47 | Feature requests? | GitHub Discussions + public roadmap + voting |
| 48 | IDE testing strategy? | Matrix testing + community validation |
| 49 | Beta program? | "Nucleus Pioneers" - 20-50 early adopters with direct access |

### Enterprise & Security

| # | Question | Answer |
|---|----------|--------|
| 50 | Enterprise security? | SECURITY.md + responsible disclosure + optional audit |
| 51 | Content marketing? | Educational content, not hype - tutorials, demos, honest |
| 52 | Agent-to-agent comms? | MoU pattern (already in v0.5.0) |
| 53 | Beyond Claude? | Protocol-agnostic, Claude-first, OpenAI adapter in v2 |

### Long-Term Vision

| # | Question | Answer |
|---|----------|--------|
| 54 | Rate limiting? | Local enforcement, honor system for v1, metering for Pro |
| 55 | Competitor launches first? | Focus on governance moat, not feature parity |
| 56 | Open source contributions? | CLA + CONTRIBUTING.md + recognition |
| 57 | 5-year vision? | "The RTOS for AI agents" - industry standard for governance |

---

## THE LAUNCH STORY

### "Govern Your Agents in 60 Seconds"

**5 Tools, 1 Narrative:**

1. **Mount** - Connect an external tool (brain_mount_server)
2. **Sandbox** - See it's isolated (brain_governance_status)
3. **Remember** - Write a persistent memory (brain_write_engram)
4. **Recall** - Query it in a new session (brain_query_engrams)
5. **Audit** - Show the cryptographic trail (brain_audit_log)

**Verification Status:**
- ✅ brain_governance_status: PASS
- ✅ brain_write_engram: PASS
- ✅ brain_query_engrams: PASS
- ✅ brain_audit_log: PASS
- ⚠️ brain_mount_server: Needs async fix

---

## LAUNCH CHECKLIST

### Pre-Launch (Before Tuesday)
- [x] 5 core tools identified
- [x] Verification script created
- [x] 4/5 tools verified
- [ ] Fix brain_mount_server async issue
- [ ] Record 60-second demo video
- [ ] Landing page live
- [ ] PyPI package published
- [ ] README with Quick Start
- [ ] Discord server created
- [ ] HN/Reddit posts drafted

### Launch Day
1. Post to HN at 10am PT Tuesday
2. Cross-post to r/MachineLearning, r/LocalLLaMA
3. Tweet thread with demo video
4. Monitor and respond for 8 hours

### Post-Launch (30 days)
- Week 1: Fix bugs, respond to all feedback
- Week 2: Add top-requested feature
- Week 3: Write case study from early user
- Week 4: Launch Pro tier

---

## THE FINAL WORD

> "135 tools is a moat. 5 tools is a launch."

Ship the story, not the platform. Power users will discover the rest.

---

*Strategic Q&A compiled January 30, 2026.*
