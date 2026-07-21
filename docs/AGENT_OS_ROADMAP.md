# Nucleus Agent OS — Roadmap: From First Cell to Biosphere

> ▶ Current built/proven state & doc-map: see AGENT_OS_STATE.md

> Companion to `AGENT_OS_MANIFESTO.md`. The manifesto is WHAT it is (an OS agents
> live inside; boots through the gateway, not MCP). This is WHAT IT BECOMES and HOW
> IT SCALES. Framed in physics because that is the honest language for something
> with no precedent. Each stage: the build, the metric that proves it's alive, the
> physics, and an honest built-vs-vision line. Written 2026-07-12 to be picked up
> cold by any agent or human. Same arc, further down the chain: `AGENT_OS_MEMBRANE.md`
> (the kernel), `AGENT_OS_MOAT.md` (the moat), `AGENT_OS_CANARY.md` (the immune
> system), `AGENT_OS_REDTEAM.md` (the stress-test).

**The spine (one line):** an agent's cognition flows through Nucleus → it gains
memory, verification, coordination, and evolution → one agent that *lives inside*
→ many → the flywheel forges the next model → others migrate in → the substrate all
AI takes for granted it runs on.

---

## STAGE 0 — THE FIRST CELL (the boot) — **BUILT + chief-verified**

**Build:** `nucleus run <agent>` — a minimal loop where the agent's **model call
routes through the Nucleus gateway** (DualEngine / `claude_oauth_llm` /
`oauth_shim_http`); before each call, **relevant memory is recalled and injected**;
after each turn, the turn is **recorded to the flywheel** (`archive_pipeline`). The
membrane forms: the agent can no longer think outside Nucleus.
**Metric it's alive:** the same agent, run inside vs naked, on one task — inside it
*recalls* something from a prior session and its turn *lands in the flywheel*. If
that happens once, the soup is alive.
**Physics:** the cell membrane forms — cognition can no longer leak to the outside.
**Built vs vision:** **BUILT** — `runtime/agent_os/boot.py` (commit `7a36f4da`, flag
`NUCLEUS_AGENT_OS_BOOT` default OFF) threads the gateway, recall, and
`archive_pipeline` into one loop; chief-verified on-shell (`ONE AGENT LIVED INSIDE
NUCLEUS FOR ONE TURN: True`). Two open caveats carried into Stage 1 (see
`AGENT_OS_STATE.md`): (1) recall is unselective on the real brain — fixed by the
working-set pager (Stage-1 task, `AGENT_OS_MEMBRANE.md` §2); (2) the model's actual
words were stubbed (this env had no live inference at build time) — the membrane is
real, the voice was offline.

## STAGE 1 — THE ORGANISM (one agent, fully alive)

**Build:** the cell gains every organ around the loop — persistent **verified**
memory (recall in, writes HMAC-anchored), the **referee** gating the agent's own
claims before they propagate, the flywheel recording *provably-correct* trajectories
(verifier-certified). Turn on the flags hardened 2026-07-12.
**Metric:** the inside-agent measurably *beats* the naked agent — memory continuity
across sessions, zero false "done," a trajectory a human would trust. A blind test:
which transcript came from inside?
**Physics:** metabolism — the cell takes in reality, excretes verified memory +
training data.
**Built vs vision:** referee + memory + flywheel all built (flag-OFF); this stage is
wiring them *around the loop from Stage 0* and turning them on.

## STAGE 2 — THE FLEET (many cells, one body)

**Build:** multiple agents living inside, coordinating through the ambient relay,
sharing one verified memory bloodstream, governed by the marketplace trust-tiers.
Specialization without the operator hand-wiring it.
**Metric:** two+ agents complete a task together via shared memory + relay that
neither could alone, with zero cross-contamination (the seeded-block test) and every
handoff verified.
**Physics:** multicellularity — division of labor, shared bloodstream (memory),
immune system (the referee).
**Built vs vision:** relay + marketplace + fleet coordination are the most-built
part of Nucleus (90%); this stage points them at *inside-agents*, not MCP-callers.

## STAGE 3 — THE FORGE (evolution — the thing beyond a product)

**Build:** the flywheel's accumulated **verified** trajectories train a fleet-
specific model (SFT/DPO/reasoning-chains, already exported by `archive_pipeline` to
TRL/Anthropic/OpenAI/Gemini formats). The new model runs *back inside*, generates
better verified work, trains the next. The loop closes.
**Metric:** a model fine-tuned *only* on inside-Nucleus verified traces beats the
base model on the fleet's own tasks. First time the substrate improves its own mind.
**Physics:** reproduction + natural selection — the environment now produces its own
improving minds.
**Built vs vision:** the dataset generator is built (works-e2e, static-read); the
train→run-back→retrain LOOP is the frontier. This is where "picks-and-shovels for
agent-training" becomes "the place that *forges* agents."

## STAGE 4 — THE PLATFORM / APP STORE (others live inside)

**Build:** open the OS. Anyone points their agent's mind at the gateway and it lives
inside — memory, verification, coordination, evolution, by physics not config. The
capability marketplace becomes the **App Store** (agents + capabilities others
publish, trust-tiered). The gateway becomes distribution: every agent that boots in
is *more*, so gravity pulls the next one.
**Metric:** the first EXTERNAL agent (not ours) boots into Nucleus and its operator
sees it remember + not-lie + compound — and comes back. One outside cell that
chooses the soup.
**Physics:** ecosystem — other organisms migrate in because life is better inside.
**Built vs vision:** marketplace + gateway exist; multi-tenant "someone else's agent
lives here safely" is the real new build (the bar-3 external-witness / tenant
isolation work). This is the commercial inflection.

## STAGE 5 — THE STANDARD (the biosphere — the $5T)

**Build:** the Agent OS becomes the *default substrate agents run on* — the way
iOS/Windows became the default humans compute on. Three compounding monopolies:
(1) the **best agentic models** (trained on the most verified real work — a data
moat nobody can copy without the fleet); (2) the **App Store** (a cut of the agent
economy running inside); (3) the **standard itself** (owning the layer between all
AI and all reality — every verification, every memory, every coordination passes
through).
**Metric:** agents run inside Nucleus *by default*, the way code runs on an OS by
default — nobody asks "why an OS," they ask "which one."
**Physics:** the biosphere — the environment all intelligence takes for granted it
lives inside.
**Built vs vision:** this is the destination. Every prior stage is a real rung; this
is what they add up to. The $5T isn't the plan — it's the *shape of the plan's
success*, the way AWS's value was the shape of Amazon's ops working.

---

## The scaling logic (why each stage forces the next)

Each stage's *output is the next stage's fuel:*
- Cell alive → an agent worth putting many of → **Fleet**.
- Fleet's verified work → the dataset that trains a better model → **Forge**.
- A better model that only exists inside → a reason for outsiders to boot in → **Platform**.
- Outsiders inside → more verified work → a better model + App Store cut → **Standard**.

It is a **flywheel of flywheels.** The moat compounds because the data that trains
the model can only be generated by agents living inside, and the agents live inside
because the model + memory + verification are only there. Circular by design — which
is exactly why it's a moat and not a feature: **you cannot copy the destination
without walking every rung, and every rung feeds the next.**

## What we do NOT do (the discipline that keeps the rocket on course)
- We do not ship it as a tool/MCP/library (that's the year-long category error).
- We do not build Stage 4/5 before Stage 0 lives (platform-first is the trap).
- We do not fake "alive" — Stage N is done when its *metric* fires on real state,
  not when the code exists (flag-OFF ≠ live).
- We do not wait for a bigger model. The blocker was never horsepower. It was nerve.
  We have the nerve now.

**First move, starting tonight: STAGE 0. One cell. One agent whose loop runs through
the gateway, recalls, and records. Everything else is evolution from that single
living thing.**
