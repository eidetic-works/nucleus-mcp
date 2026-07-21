# Product-Shaped Pathways — Docs & Decisions Survey

Scope: `DECISIONS.md`, `docs/adr/` (20 files found — repo has gaps 0012-0028, 0038; not 43 as originally assumed, see note at bottom), `docs/strategy/`, `docs/org/`, `AGENTS.md`, plus a grep sweep of top-level `docs/*.md` and relevant subdirs (`docs/v10_strategy/`, `docs/architecture/`, `docs/tb_personal_ai/`, `docs/track_b/`, `docs/product/`) for product/strategy/roadmap/vision themes.

Methodology: this is a **docs-and-decisions map**, not a build audit. BUILT/PARTIAL/ASPIRATIONAL calls below are from quick, targeted greps against plausible src roots (`mcp-server-nucleus/src`, `backend/`, `providers/`, `scripts/`, `workers/`, `flutter_app/`, and the sibling `eidetic-daemon` Go repo) — enough to distinguish "real code exists" from "prose only," not a full audit. Treat every BUILT/PARTIAL call as directionally reliable, not exhaustively verified.

A roadmap entry is not a product. Several of the pathways below are explicitly DRAFT ADRs or investor-narrative prose with zero corresponding code — they are flagged as ASPIRATIONAL-ONLY and should be read as "the docs explored this," not "this exists."

---

## 1. Nucleus Agent Substrate — MCP governance/orchestration control plane

**What it is:** A governance + memory + orchestration layer that sits between AI coding clients (Claude Code, Windsurf, Cursor) and other MCP servers. Positioned two ways across docs: as a *recursive MCP aggregator with a mount catalog* (mount/unmount other MCP servers behind one governed endpoint, solving "connection sprawl") and as "operational memory" / a PM-for-agents competing against semantic-memory tools (MemGPT/Zep). Same underlying substrate, two positioning spins.

**Source docs:** `docs/v10_strategy/STRATEGIC_VISION_AGENT_OS.md`, `docs/NUCLEUS_STRATEGY_BLUEPRINT.md`, `docs/NUCLEUS_ARCHITECTURE.md`, `docs/PRIMITIVES.md`, `docs/architecture/RECURSIVE_AGGREGATOR.md`; substrate invariants in `docs/adr/0005-agent-os-foundations.md`, `docs/adr/0006-identity-model-agents-and-sessions.md`.

**Status: BUILT (core) / PARTIAL (aggregator headline feature).** `mcp-server-nucleus/src/mcp_server_nucleus/cli.py` has a real `nucleus mount/unmount/list` command set; `runtime/mounter_ops.py` and `runtime/mounter.py` implement the mount-catalog concept (docstring: "Recursive Mounter Prototype AG-021"), backed by `tests/test_mounter_traverse.py`. `docs/PRIMITIVES.md` (a self-audit dated 2026-06-11) inventories 15 registered facade tools and rates most as HOOK-NUDGED (reachable but not deterministically fired) rather than fully WIRED. `docs/architecture/RECURSIVE_AGGREGATOR.md`'s own status table marks local plugin aggregation + governance middleware + audit log as LIVE, but "mount external MCP servers" as 🔄 PLANNED — the headline aggregator capability is prototype-stage.

**Differentiation:** Genuinely differentiated architecture (multi-surface relay, role-aware identity, audit ledger, policy-enforcing MCP reverse-proxy) — not a commodity pattern in this space as of the docs' timeframe. The "persistent memory for agents" framing alone is increasingly commodity (MemGPT/Zep/various "second brain" MCP servers exist).

**Intended user + job:** Solo founders / power users running multiple AI coding surfaces who need shared state, governance, and audit across them without manual context re-pasting.

---

## 2. Eidetic Works — tiered SaaS wrapping the daemon ("AI Employees for Solo Founders")

**What it is:** Commercial packaging of a local-first, always-on memory daemon (captures AI-assistant session context, sub-100ms retrieval) as a subscription business: Free / Pro $29/mo / Pro+ $99/mo ("sovereign model" tier) / Team $299/mo, gating compliance features, swarms, and a dashboard. Licensing enforced via a custom offline-verifiable Ed25519 token (ELT) so the daemon can check entitlement without phoning home.

**Source docs:** `AGENTS.md` "90-Day Plan: Eidetic Works" stanza; `DECISIONS.md` ADR-001, 002, 004-006, 012-016; `docs/adr/0008-ed25519-license-tokens.md`; corroborated by `docs/THE_HONEST_PICTURE.md`, `docs/NUCLEUS_GROWTH_STRATEGY.md`.

**Status: BUILT, then FROZEN.** Real Go daemon at sibling repo `eidetic-daemon` (`cmd/eideticd/*.go`, benchmark suite). License mechanic is real: `mcp-server-nucleus/src/mcp_server_nucleus/runtime/license.py` + `workers/eidetic-license/worker.js` implement the exact ELT/offline-verify/KV-revocation shape from ADR-0008. Stripe billing is live (`workers/stripe-checkout/worker.js`, `workers/eidetic-account/worker.js`; Stripe Payment Links confirmed live per `docs/THE_HONEST_PICTURE.md`). Business was explicitly frozen at Day-37 (per `AGENTS.md`/ADR-006 hard-kill bright-line: <5 paid Pro subs at the Day-60 gate → wind down); `docs/THE_HONEST_PICTURE.md` reports zero paid subscribers at the Day-30/60 checkpoints.

**Differentiation:** Novel packaging narrative (dogfooded, publicly-run solo-founder-by-AI story) on top of commodity SaaS-tier mechanics; the local-first sub-100ms + offline-licensable distribution shape is a real technical differentiator vs. cloud-memory competitors (explicitly benchmarked against ChatGPT Memory as the incumbent).

**Intended user + job:** Individual developers using Cursor/Claude Code who want persistent cross-session memory and compliance/swarm features without a cloud dependency, paying monthly.

---

## 3. TB Personal AI ("Third Brother") — sovereign personal AI, and its unbuilt productization

**What it is:** A privately fine-tuned model trained on the founder's own decade of archives (Telegram/WhatsApp/Perplexity), composing in his voice, with a hard sovereignty gate (data never reaches a third party without explicit breach). Explicitly documented as "not a product for others" today. Four DRAFT ADRs sketch a path to productizing the underlying substrate for other users: multi-model consensus/judge-routing for reliability, P2P CRDT cross-device sync, a federated-learning protocol for privacy-preserving cross-user pattern sharing, and a hybrid OCI-inference/Mac-RAG architecture for 24/7 availability.

**Source docs:** `docs/tb_personal_ai/00_INDEX.md` (+ `01_wide_research.md`, `02_roadmap.md`, `03_no_corners_charter.md`); `docs/adr/0029-B9-multi-model-consensus-methodology-DRAFT.md`, `docs/adr/0030-B10-cross-device-sync-sovereignty-revision-DRAFT.md`, `docs/adr/0031-B11-federated-personal-AI-protocol-DRAFT.md`, `docs/adr/0032-hybrid-oci-generation-mac-rag-DRAFT.md`.

**Status: BUILT (personal pipeline) / ASPIRATIONAL-ONLY (all four productization drafts).** ~35 `scripts/tb_*.py` files exist (`tb_endpoint.py`, `tb_telegram_bot.py`, `tb_repl.py`, `tb_build_dpo_v15.py`) plus `providers/composers/` (voice.py, sonnet_principal.py); real fine-tuned model shipped (v14, per `.brain/THIRD_BROTHER_MANIFEST.md`). The four DRAFT ADRs are explicitly labeled "Skeleton Draft" / unadopted: no Best-of-N/judge-router code found; CRDT machinery exists in the repo (`nucleus-mcp/.../crdt_task_store.py`) but is wired for multi-agent task-orchestration state, not device-to-device personal-memory sync as the ADR describes (flagged as adjacent-not-confirmed, not a direct build); no federated-learning/differential-privacy code found anywhere; the hybrid-OCI ADR is the one exception with a partially-checked implementation list (`brain_rag_server.py` done, end-to-end tunnel verification and daemonization explicitly marked not-done in the ADR itself).

**Differentiation:** Novel (sovereignty-gated personal LLM tuned on a decade of personal archive) with no direct commodity comparison for the built core. The draft extensions, if built, would be genuinely differentiated (federated cross-user learning without pooling raw data is closer to a platform moat than a feature).

**Intended user + job:** Currently the founder only, for personal reasoning/composition continuity. Draft extensions target future multi-device, multi-user operators of a personal-AI daemon.

---

## 4. GentleQuest D2C — "anti-productivity" mental-health companion

**What it is:** A gamified quest + AI chat + mood/journal-tracking app for individuals with ADHD/anxiety/burnout, built on an explicit "anti-streak" philosophy (Total Active Days instead of streaks — framed as dopamine-safe vs. the cortisol-inducing streak mechanics of competitors).

**Source docs:** `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/GENTLEQUEST_ARCHITECTURE.md`, `docs/GENTLEQUEST_BRANDING_STRATEGY.md`, `docs/strategy.md`, `docs/PRODUCT_STRATEGY_DEPTH_OVER_BREADTH.md`.

**Status: BUILT.** `models.py` has `Quest`, `QuestProgress`, `UserProfile`, `MoodEntry`, `CrisisEvent`; Flutter routes for quests/wellness-dashboard exist; shipped to both app stores (v1.4.2 per `docs/THE_HONEST_PICTURE.md`), live at gentlequest.onrender.com. Same doc reports zero users at the Day-30/60 gates.

**Differentiation:** Genuinely differentiated messaging (anti-streak vs. Woebot/Wysa/Headspace's gamified-streak norm); commodity underlying tech (chatbot + CBT content + gamification loop).

**Intended user + job:** Individuals with ADHD/anxiety/burnout wanting low-pressure emotional check-ins rather than another productivity/streak app.

---

## 5. GentleQuest B2B2C — clinical/enterprise wellness platform

**What it is:** The same app repositioned for institutional buyers — PHQ-9/GAD-7 clinical assessments, counselor dashboards, crisis escalation/alerting, white-labeled for university counseling centers and corporate EAP programs, priced per-student/per-employee.

**Source docs:** `docs/IMPLEMENTATION_ROADMAP.md` (explicit "B2B2C mental health platform" executive summary), `docs/strategy.md`, `docs/PILOT_TIER_PLAYBOOKS.md`, `docs/CUSTOMER_JOURNEY_MAPS.md`, `docs/MARKET_ENTRY_CHECKLISTS.md`, `docs/STRATEGIC_AI_CAPABILITIES_ROADMAP.md`.

**Status: PARTIAL (schema/API) / ASPIRATIONAL (go-to-market).** `models.py` has real `University`, `UniversityCounselor`, `CounselorAlert`, `AlertAcknowledgment` classes with `/api/clinical/*` and `/api/alerts/*` endpoints implemented. `docs/THE_HONEST_PICTURE.md` states the B2B2C pilot plan "was written but never executed" — zero pilots run, zero enterprise deals closed.

**Differentiation:** Commodity go-to-market motion (standard campus wellness B2B2C playbook); the clinical framework is credible but not differentiated vs. incumbents, and clinical validation itself hasn't been done.

**Intended user + job:** University CAPS directors / corporate HR-EAP buyers needing scalable, evidence-based student/employee mental-health triage and visibility.

---

## 6. Dual-brand portfolio + automated Distribution Officer

**What it is:** Two coupled pieces: (a) a brand architecture separating "Eidetic Works" (umbrella company) from "NucleusOS" (flagship product) and sub-brands (GentleQuest, Hypomnemata, etc.) — an Apple/Anthropic/Notion-style portfolio model chosen after an earlier single-brand collapse was reversed; (b) an autonomous "Distribution Officer" sub-agent that drafts and routes public marketing content across a 9-type taxonomy to the correct handle, gated by mandatory Telegram approval (never auto-posts), with a bidirectional identity firewall preventing pseudonymous↔real-name leakage.

**Source docs:** `DECISIONS.md` ADR-011, 017, 018, 023, 025, 027, 028; `docs/adr/0009-distribution-officer-telegram-gated.md`, `docs/adr/0011-brand-architecture-dual-brand-multi-product.md` (this and `DECISIONS.md` ADR-028 describe the same decision at two tiers — duplicate, not two pathways); `docs/distribution_officer.md`, `docs/distribution_officer_charter_v3.md`, `docs/DISTRIBUTION_AUTOPILOT.md`.

**Status: PARTIAL/BUILT (automation) / dormant (as a live lever).** `scripts/distribution-officer/{content_router.py, draft_generator.py, telegram_approval_bridge.py}` exist and ran (drafting + Buffer/dev.to firing confirmed shipped per `docs/THE_HONEST_PICTURE.md`). The portfolio strategy itself (a public MRR/activity dashboard modeled on Pieter Levels-style build-in-public, referenced in strategy prose) has no corresponding code found anywhere in the repo. Distribution is reported paused as of the Day-37 freeze.

**Differentiation:** The automated multi-brand routing + bidirectional identity firewall is a genuinely novel operational mechanic, purpose-built for a pseudonymous-founder-with-day-job constraint; the underlying "draft-then-approve-via-Telegram" pattern is commodity marketing automation.

**Intended user + job:** The operator (internal tool), not an external customer — though its output (public posts) targets prospective Eidetic Works / NucleusOS customers.

---

## 7. IIP — Innovation/Incubation-Program venture-coaching platform

**What it is:** A third, distinct product line: a structured tool for teams running a customer-discovery/venture-building curriculum (Double Diamond method: POV → interviews → ANRUM insight extraction → personas → CVP → experiments), with an LLM "coach" meant to recommend next experiments and extract structured insights from interview notes.

**Source docs:** `docs/product/IIP_LLM_IMPLEMENTATION_AND_USAGE_GUIDE.md`.

**Status: BUILT (API) / under-verified (LLM-coach layer).** `backend/app/main.py` declares `FastAPI(title="IIP Module 6 API")` with real routers (teams, llm, personas, cvp, roadmap, interviews, tasks, chat, project_chat) and real models (`app/models/{persona,cvp,roadmap,tasks,chat}.py`) — a working REST API matching the spec closely. A `flutter_app/` exists as the UI counterpart. The specific LLM-coach endpoints (ANRUM extraction, experiment recommendation) were not directly confirmed as implemented in this pass.

**Differentiation:** Commodity CRUD-app skeleton; any real differentiation would come from the under-verified LLM-coach layer.

**Intended user + job:** Program managers/instructors running an innovation-methodology course (e.g., an MBA-style incubator) and teams doing structured customer discovery within it.

---

## 8. OMBA Framework Brain — "AI Co-founder that reasons like a strategist" (flagship pivot attempt)

**What it is:** A proposed reframing of Nucleus's entire flagship value proposition: a library of ~10-50 MBA-style decision frameworks (Porter Five Forces, JTBD, Lean Canvas, RICE, etc.), a "Decision-Archetype Router" that maps a user's business situation to relevant frameworks, and a "Structured-Reasoning Composer" that produces an auditable reasoning trace instead of free-form chat — distributed as a Microsoft 365/Azure app (OneNote ingest, AppSource or side-loaded).

**Source docs:** `docs/adr/0035-nucleus-flagship-pivot-omba-framework-brain-DRAFT.md` (a 74KB, still-DRAFT, live-amended ADR spanning v0.2-v0.13 over roughly a week).

**Status: PARTIAL, and likely stalled.** Real implementation exists: `providers/composers/framework_composer.py`, `framework_runner.py`, `cross_framework_synthesis.py`, with matching tests. But the *distribution* half (multi-tenant Azure app, AppSource listing, customer-token-vault) shows no code — no `omba-callback` worker or equivalent found. `AGENTS.md`'s current active-arc header (dated after this ADR) makes no mention of OMBA as the live flagship, suggesting the pivot was absorbed as a side-capability or parked rather than fully executed. The ADR itself never dropped its `-DRAFT` filename suffix despite reaching "v0.5 ACCEPTED in substance" mid-document.

**Differentiation:** Genuinely differentiated concept ("reasoning trace grounded in named business frameworks" vs. opaque chat co-pilots); the ADR's own risk section flags framework narrative-fidelity and generic-feeling reasoning outside the founder's own MBA domain as real execution risk.

**Intended user + job:** Solo founders / small teams (<50 employees, per the ADR's own market-segment assumption) making pricing, hiring, and positioning decisions without access to a strategist or consultant.

---

## 9. Track B — AI-memory-portability consumer wedge (parked, signal-only)

**What it is:** A lighter-weight consumer product idea scouted alongside the Eidetic Works daemon: sell ordinary consumers on memory that follows them across ChatGPT/Claude/Gemini/etc., rather than developer-tool session memory. By explicit design, kept to signal-only validation (landing page, waitlist, interviews) with zero product code committed until a Day-30 gate authorized further build.

**Source docs:** `docs/track_b/interview_script.md`; `DECISIONS.md` ADR-001 (Track A/B split), ADR-018 (domain stack for `try.eideticworks.ai`).

**Status: ASPIRATIONAL-ONLY, by deliberate design — not a build gap.** `PLAN.md` states the Day-30 gate never authorized a consumer build; `docs/THE_HONEST_PICTURE.md` reports zero waitlist signups, 0% conversion. Only the interview script exists as an artifact.

**Differentiation:** Potentially real pain point (memory portability across vendor AI products), but the space is conceptually crowded with memory-layer startups broadly, and the doc itself acknowledges the incumbent-disadvantage of a free, bundled ChatGPT Memory.

**Intended user + job:** A person who regularly uses 3+ AI chat tools and loses context switching between them.

---

## 10. Agent-Readable Infrastructure — deployment kit sold as a $19 Gumroad product

**What it is:** The insight "don't build new agent tools, make existing tools readable by agents" — instantiated as a sellable "Flutter Store Deployment Kit" (a markdown runbook letting any AI coding agent ship an app to the App/Play Store from the terminal without manual Xcode/Play Console fiddling), plus reusable "Agent-Readable Workflow Templates" for other repeatable ops tasks (e.g. DB migration).

**Source docs:** `docs/AGENT_READABLE_INFRASTRUCTURE_DRAFT.md`, `docs/AGENT_READABLE_TEMPLATES.md`; called out in `docs/THE_HONEST_PICTURE.md` as "the most interesting thing built in months."

**Status: BUILT and transacting.** `workers/gumroad-kit-sync/worker.js` is live production code routing Gumroad webhooks by named product SKU, confirming this is a real, sold product rather than only a doc — `docs/DISTRIBUTION_AUTOPILOT.md` describes the working purchase-to-fulfillment pipeline. (A literal file matching the runbook's own filename wasn't located in this pass, but the surrounding sales/fulfillment infrastructure is unambiguously real.)

**Differentiation:** Genuinely novel framing (agent-native documentation-as-tooling) even though the underlying deployment steps themselves are commodity DevOps knowledge. Notably the only pathway in this list confirmed to have generated actual transactions.

**Intended user + job:** Flutter/mobile developers using AI coding agents who want to skip manual App Store / Play Store release friction.

---

## Also explored but out of scope as "pathways" (per the docs' own framing)

- **Multi-model consensus, cross-device CRDT sync, federated personal-AI protocol, hybrid OCI/Mac-RAG** — folded into #3 above as unbuilt extension drafts, not standalone pathways.
- **Sovereign Monolith** (`docs/EXHAUSTIVE_DESIGN_THINKING_PLAN_SOVEREIGN_MONOLITH.md`) — a design proposal for one unified, progressively-disclosed entry point spanning novice-to-power-user access to all of Nucleus. No file or directory matching it exists anywhere outside `docs/` — pure design-thinking exercise, ASPIRATIONAL-ONLY, not substantial enough on its own to rank in the top 10 alongside the above.
- **Nucleus skill/plugin marketplace subscription** (paywalled Claude Code skill library) — mentioned in strategy prose (`docs/strategy/2026-05-09_face-question-for-ultraplan.md`) but the marketplace repo itself lives outside this repository (per prior investigation, at a separate `nucleus-cc-plugins` repo) and is unverifiable from here; appears functionally folded into pathway #2's Pro tier rather than shipped standalone.
- **Concierge/manual-fulfillment micro-offers and multi-surface orchestration consulting** — the strategy ultraplan's own final recommendation (turns 87-88 of `docs/strategy/2026-05-09_face-question-for-ultraplan.md`) explicitly argues *against* building the tiered SaaS ladder in favor of manually-fulfilled, pre-validated offers — a recommendation the team did not follow (they built #2 instead, then froze it). Notable as an internal contradiction inside the strategy doc itself, not substantial as a standalone pathway.
- **DECISIONS.md ADR-0040** (`nucleus chat` over an OAuth arbitrage shim) is explicitly designed by its own text to never be a public/marketed surface — excluded by the document's own guardrail, not by outside judgment.
- Internal agent-coordination/process ADRs (`docs/adr/0001-0004, 0006, 0010, 0033, 0034, 0036, 0037, 0039`, plus `docs/architecture/three_surface_contract.md`, and most of `docs/org/charters/`) shape how the agents that build these products coordinate with each other — they are substrate plumbing, not user- or market-facing pathways, so they're omitted from the numbered list above.

## Scope notes

- `docs/adr/` contains **20 files** (numbered 0001-0039 with gaps at 0012-0028 and 0038), not 43 as assumed going in — no other `docs/adr/`-equivalent directory with more ADRs was found elsewhere in the repo (a few individually-numbered ADR-style files exist under `.brain/adrs/` and `.brain/audits/`, but those are agent working-memory/audit artifacts, not the canonical decision record, and were left out of scope).
- No file at `docs/strategy/BILLION_DOLLAR_ROADMAP.md` exists. The closest artifact in scope, `docs/strategy/2026-05-09_face-question-for-ultraplan.md`, is a raw strategy-conversation transcript (not a formal roadmap doc) whose substantive content lives in its first ~20% of lines; the remainder is relay/operational log noise. It never mentions a "billion-dollar roadmap" by name.

## What the docs emphasize most vs. what's actually built

The docs pour by far the most words into speculative substrate evolution and go-to-market strategy for Eidetic Works / Nucleus and GentleQuest's B2B2C ambitions (#1, #2, #3's draft extensions, #5, #6, #8) — yet the one pathway independently confirmed to have generated real transactions is the smallest, least-discussed one in the corpus: the $19 Gumroad deployment kit (#10).
