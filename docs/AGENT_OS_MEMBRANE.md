# The Membrane — the Cognition Scheduler & Memory Manager

> ▶ Current built/proven state & doc-map: see AGENT_OS_STATE.md

> Fable-tier design, 2026-07-12. Companion to `AGENT_OS_MANIFESTO.md` (the OS
> agents boot into) and `AGENT_OS_ROADMAP.md` (Stage 0→5). This defines the
> **principle** of the membrane — the layer between an agent and its own mind —
> not the patch. It unifies two things the operator surfaced: (a) run cognition on
> ANY provider/plan/no-key (the cost moat), and (b) select intelligently what the
> agent thinks WITH (the recall-blur the Stage-0 gate exposed). Both are the same
> problem, and 60 years of OS theory already named it.

**The one-line law:** *The agent thinks. The membrane decides what it thinks **with**
and what it thinks **through** — by policy, per turn, learned from the flywheel.*

---

## 0. The reframe: the membrane is a SCHEDULER + an MMU

A classical OS kernel does two things that make a process "inside" it:
- the **scheduler** decides which CPU a process runs on, when, at what priority;
- the **memory manager (MMU/pager)** decides which pages are in the process's finite
  working set, loading the right ones and evicting the rest.

The process never picks its own CPU or manages physical RAM — the kernel does, by
policy. **The Agent-OS membrane is the exact same thing for cognition:**
- **Cognition scheduling** = deciding which *provider/plan* an agent's model call
  runs on (the execution question).
- **Context paging** = deciding which *memories* are loaded into the agent's finite
  context window before it thinks (the selection question — the recall-blur).

Neither is a feature to bolt on. Both are the kernel's core job, and framing them as
scheduling+paging is what makes this a real OS and not a wrapper.

## 1. Execution = scheduling cognition onto the cheapest capable provider

Providers are not interchangeable — they are a **spectrum of (auth, cost,
capability)**:

| Path | Auth | Cost | Note |
|---|---|---|---|
| API key (Anthropic/OpenAI/…) | per-token key | $$$ | always-on, expensive |
| **OAuth / subscription** (the shim) | Max/Pro OAuth | **plan-metered, ~free at margin** | the moat — `oauth.nucleusos.dev` |
| Cross-vendor CLI (devin/agy) | vendor plan | ~free | GLM/Gemini on their plans |
| Local (ollama/OCI) | none | free | weaker, private |

**The law:** the agent holds **no key** and picks **no model.** It emits a *cognition
request* (with a capability hint — "hard reasoning" vs "cheap classify"); the
membrane **schedules** it onto the cheapest path that clears the bar, invisibly.
The agent loop is written **once** and runs on whatever's available — subscription
today, local tomorrow, a frontier key when it must. **This is the cost-moat as a
principle:** cost and provider become *membrane policy*, not an agent concern —
exactly as a program doesn't know or care which CPU core it landed on.

> Consequence the operator intuited: "runs on your plan, no expensive keys" is not a
> hack — it is the default scheduling policy (prefer OAuth/subscription/CLI/local
> over API-key). The shim is the driver for the cheapest lane. Dismissing it is
> dismissing the scheduler's best CPU.

## 2. Selection = paging the RIGHT memory into a finite working set

The Stage-0 gate caught the real crack: recall pulled **5 loosely-related** memories,
not the one that mattered. In OS terms this is a **bad page-replacement policy** —
loading the wrong pages into a finite working set. The fix is not "grep better"; it
is a **working-set policy**: score candidate memories by *relevance × recency ×
verified-trust*, load only what fits the context budget, evict the rest. The agent's
context window is its RAM; recall is its virtual memory; the membrane is the pager.

Selection is broader than memory: every turn the membrane decides **what** context
(which memories/tools/fleet-state), **through which** provider, and **what** to
verify/record. Selection *is* the membrane's intelligence — and it must be a
**policy** (a scoring function), never ad-hoc.

## 3. Why this is the MOAT, not a feature: the scheduler LEARNS

Here is the join that makes it un-copyable. The flywheel records every turn's
outcome, and the referee certifies which turns were *actually good*. So the membrane
can **learn its own scheduling and paging policies from verified outcomes:**
- which *memories*, when injected, led to verified-correct turns → a better pager;
- which *provider* cleared which capability bar at least cost → a better scheduler;
- which *context shape* produced trustworthy work → a better working-set policy.

**A learning scheduler trained on your fleet's own verified trajectories is a moat
nobody can copy without the fleet.** OpenRouter routes by static price; we route by
*learned, verified quality-per-cost.* Mem0 stores memory; we *page* it by learned
relevance. The membrane is not a better router or a better memory — it is the first
**cognition kernel that gets better at running minds the more minds it runs.**

## 4. Built vs principle (honesty, as always)

- **BUILT (the organs):** the shim (a cheap-lane driver) exists; recall exists;
  `cost_router`/`llm_resilience` exist; the Stage-0 cell proved the membrane can
  *thread* provider+recall+record into one loop.
- **NOT BUILT (the kernel):** none of it is yet a **policy-driven scheduler/pager.**
  Today: provider is hard-picked, recall is unselective (the blur), nothing learns.
  The Stage-0 model call was *stubbed* — the cheapest-lane scheduling (run a real
  thought on the subscription via the shim) is unproven and is the first thing to
  settle.
- **THE PRINCIPLE (this doc):** treat execution as scheduling and selection as
  paging; make both policies; let the flywheel+referee teach the policies. That is
  the design that turns the Stage-0 mannequin-in-a-membrane into a living,
  provider-agnostic, self-improving cognition kernel.

## 5. What this licenses next (tiered — keep Fable off the mundane)

- **[settle first, Opus/delegate]** prove the cheapest lane: one *real* model thought
  through the shim on a subscription, no API key. Real-and-working / real-but-
  unreachable-here / aspirational — this decides how big the cost-moat is.
- **[Opus/delegate]** the working-set pager: replace dump-recall with relevance ×
  recency × trust scoring against a context budget (fixes the Stage-0 blur).
- **[Opus/delegate]** the provider scheduler: a policy that routes a cognition
  request (capability hint) onto the cheapest clearing path.
- **[Fable, later]** the *learning* layer: the loop where the flywheel+referee train
  the scheduler/pager policies from verified outcomes — the un-copyable part. Design
  it once the two policies exist to be learned.

**The membrane is the kernel. Execution is scheduling. Selection is paging. The
flywheel is how the kernel learns to run minds better than anyone who doesn't have
the fleet. That is the moat, stated as an operating principle.**
