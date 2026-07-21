# Agent OS — State of Reality (as of 2026-07-13)

> **START HERE.** The single authoritative snapshot of what is *built*, what is
> *proven*, what is *honest-but-bounded*, and what is *next* for the Agent OS. Every
> other doc is theory or detail; this is ground truth. Written so any future agent
> or post-Fable session inherits *reality, not the pitch.* Supersedes optimism in
> the older docs where they conflict.

## The doc-map (read in this order)
1. `AGENT_OS_MANIFESTO.md` — WHAT it is: an OS agents *boot into* (cognition routed
   through the gateway), not a tool they call via MCP. The gateway-inversion.
2. `AGENT_OS_ROADMAP.md` — the stages: first cell → organism → fleet → forge →
   platform → standard.
3. `AGENT_OS_MEMBRANE.md` — the kernel: execution = *scheduling* cognition onto the
   cheapest capable provider; selection = *paging* the right memory into a finite
   working set. Both are policies.
4. `AGENT_OS_MOAT.md` — the durable moat: the **learning membrane on VERIFIED
   trajectories** (the referee is the labeling engine); Goodhart-proof if the
   referee is sound.
5. `AGENT_OS_CANARY.md` — the immune system: keeps "verified-good" world-good under a
   ruthless learner.
6. `AGENT_OS_REDTEAM.md` — the completeness stress-test: no fatal gap, 3 narrowings,
   the real risk is market.
7. `AGENT_OS_FIRST_USER.md` — onboarding: **we are the first user** (we hand-do the
   OS's functions); onboarding is *subtractive* (replace a manual chore with the auto
   version); first felt win = **memory continuity**; honest two-tier "inside vs
   service" architecture; Fable-vs-build split for "make it work."
8. `OAUTH_ARBITRAGE_SHIM_GUIDE.md` + `ADR-0040` — the keyless-token operations (by GLM).

## BUILT + chief-verified (on-shell)

*The moat DATA LOOP is now end-to-end + immune-checked: run → recall(selective) → mediate → record → referee-label → persist → corpus(export) → canary(drift).*

- **Stage-0 "first cell"** — `runtime/agent_os/boot.py` (commit `7a36f4da`, flag
  `NUCLEUS_AGENT_OS_BOOT` default OFF). One agent runs *inside* the OS for one turn:
  cognition **mediated** (real `LLM_GENERATE` event a naked call would never write),
  memory **recalled + injected** before it thinks (real cross-session recall), turn
  **recorded** to the flywheel (real `LoopTurn`). Verified on my shell:
  `ONE AGENT LIVED INSIDE NUCLEUS FOR ONE TURN: True`.
  - **Known gap (Stage-1 task #1) — RESOLVED:** recall was *unselective* on the real
    brain (`test_recall_is_selective_not_echo` failed; it pulled ~5 near-misses, not
    the one). The pager policy that fixes this is now built and flag-gated — enable
    `NUCLEUS_AGENT_OS_PAGER` for selective recall (the working-set *pager* policy,
    MEMBRANE §2, landed in commit `36829030`; the `nucleus agent-os recall` primitive
    that calls it landed in `ee92a075`). Selective recall now lands the right slice,
    not the blur.
  - **One authorized stub:** the model's actual *words* were stubbed (this env had no
    live inference at build time). The membrane is real; the voice was offline.
- **Stage-1 PAGER** — commit `36829030`, flag `NUCLEUS_AGENT_OS_PAGER` default OFF.
  Selective memory recall: score = bm25 relevance × recency × verified-trust within a
  char budget; injects the *right* slice, not the blur. All flag-gated, additive,
  gated on-shell by re-running pytest before commit.
- **`nucleus agent-os run`** — commit `fb3c6349`. Run one spawned agent *inside* the OS
  on demand (reuses `boot_cell` + pager): mediated cognition + selective recall +
  recorded turn, one command. Flag-gated default OFF, additive, gated on-shell by
  re-running pytest before commit.
- **`nucleus agent-os recall`** — commit `ee92a075`, flag `NUCLEUS_AGENT_OS_PAGER`
  default OFF. The selective memory-continuity primitive a SessionStart hook *calls*
  to auto-load the right prior context; flag-OFF = plain recall. The live-hook wiring
  itself is a documented operator opt-in — no delegate touched the live hook.
  Flag-gated, additive, gated on-shell by re-running pytest before commit.
- **`nucleus agent-os demo`** — commit `628cdd0c`, flag `NUCLEUS_AGENT_OS_BOOT` default
  OFF. Naked-vs-inside: same prompt run bare (no recall/mediation/record) vs inside
  `boot_cell`; prints the delta. Real run showed the naked path proceeding blind while
  the inside path recalled the prior-session fact and acted on it. Closes the
  `AGENT_OS_FIRST_USER` §4 build list. Flag-gated, additive, gated on-shell by
  re-running pytest before commit.
- **VERIFIED-LABELED TURNS (the moat brick)** — commit `83f31e06`, flag
  `NUCLEUS_AGENT_OS_VERIFIED_RECORD` default OFF. `label_turn()` runs the DSoR Verifier
  over a turn's outcome and attaches its honest verdict
  (CONFIRMED/REFUTED/UNVERIFIABLE/PARTIAL); doctrine-clean — unanchorable outcomes →
  UNVERIFIABLE (withhold, never silently confirm). `boot_cell` attaches it flag-gated
  (+23 lines, flag-off byte-identical, labeling failure swallowed). This makes the
  flywheel mint *referee-VERIFIED* trajectories — the scarce training signal only
  Nucleus can produce (referee = labeling engine, per MOAT.md §1). Flag-gated,
  additive, gated on-shell by re-running pytest before commit.
- **Verified-label PERSISTENCE** — commit `9eab2485`, flag `NUCLEUS_AGENT_OS_VERIFIED_RECORD`
  default OFF. The moat brick attached the referee verdict to `BootResult` but computed
  it AFTER record, so it never reached `loop_turns.jsonl` — the verified corpus was
  ephemeral. Fixed: label now computed before record and threaded onto the persisted
  `LoopTurn` (`to_dict` writes the key only when non-None → flag-off jsonl byte-identical).
  The verified corpus is now DURABLE on disk. (21 agent-os + 356 archive tests green.)
  Gated on-shell by re-running pytest before commit.
- **`nucleus agent-os corpus`** — commit `747c494e`. Reads `loop_turns.jsonl`, tallies
  turns by referee verdict (CONFIRMED/REFUTED/UNVERIFIABLE/PARTIAL/unlabeled), and
  `--export` writes the clean verified-positive jsonl (default CONFIRMED) — the training
  set made visible; the input the learner/canary consume. Robust to legacy/malformed
  lines. Additive, gated on-shell by re-running pytest before commit.
- **`nucleus agent-os canary`** — commit `492ac5f1`. The moat's immune system v0
  (`CANARY.md` §1b, temporal-consequence drift): re-verifies CONFIRMED turns NOW and
  flags any that no longer confirm (a 'verified-good' label whose world moved under it).
  Read-only; reports drift rate + drifted turns. Honest v0 = same referee re-run over time.
  Additive, gated on-shell by re-running pytest before commit.
- `oauth_probe.py` / `agent_os/boot.py` — re-runnable keyless verifiers.
- **5 secretary-queued bricks (commit `96ad11c6`, chief-gated, 239 tests passed)** —
  capability-hint routing tests (`CAP_CHEAP`→Groq, `CAP_REASONING`→Claude,
  `CAP_ANY`→Antigravity, mock providers); `proxy.py` forwards
  `x-nucleus-provider`/`x-nucleus-engine` as real HTTP headers + endpoint test;
  `recall --list` debug primitive (no inference); `corpus --format json` +
  `canary --json` for programmatic consumption. All additive, default-unchanged.
  Closes the principal-agent loop demonstration — secretary queued via
  `nucleus_tasks`, chief delegated + gated + committed. Gated on-shell by
  re-running pytest before commit.
- **Role-scoped tasks + MCP-native wakeup (commits `2671d8ac` + `b8760180` +
  `a3e33834`)** — `nucleus_tasks` now carries `required_role` (scopes a task to
  a specific agent role, preventing agent pollution) and `plan_ref` (pointer to
  the plan section this task serves — the principal gates on the plan, not the
  secretary's narration). `nucleus_wakeup_wait` is a standalone MCP tool in
  `sync.py` that mirrors `nucleus_relay_subscribe`'s push pattern: 1s polling,
  `ctx.info()` notifications on each matching task arrival, burst mode for
  end-of-turn drain. Any agent vendor connected to the MCP server calls it —
  no subprocess hacks, no agent-specific CLIs. Replaces the asymmetric
  `auto_awake` daemon (CC easy to wake, agy <50%, devin never worked outbound)
  with a uniform primitive. 9 new tests green (5 required_role + 4 wakeup_wait).
- **Cross-vendor provider lanes (MEMBRANE §1, COMMITTED on a separate lane — NOT
  chief-verified here):** the cognition scheduler (`runtime/agent_os/scheduler.py`,
  commit `de7e7cd3`) + inference proxy (`runtime/agent_os/proxy.py`) + 3 new provider
  lanes (Antigravity OAuth, Grok OAuth, Gemini API-key mode, commit `1fc30202`) are
  committed on this branch. The gateway (`boot.py`) now routes through the scheduler
  with fallback — on provider failure (429/402/etc) it tries the next provider before
  stubbing. 3 free lanes verified live on that lane's shell (Groq → "ALIVE", Gemini →
  "ALIVE.", Antigravity → "ALIVE" before token expiry). 34 agent-os tests green
  against the modified boot.py. NOT re-run on this chief's shell — treat as
  committed-but-not-chief-verified until CC main gates it. The learned scheduler
  (MOAT §2) is still ahead-of-data.

## PROVEN empirically (the keyless subscription lane)
- **Auth works, keyless.** With API-key env vars stripped, the gateway constructs
  `engine=CLAUDE_OAUTH` and Anthropic *accepts* the OAuth bearer. A `403`/`429` means
  "engaged with the token," never "rejected the concept."
- **Scope matters.** The token needs `user:inference` scope. Re-mint via
  `claude.ai/oauth/authorize` (NOT `platform.claude.com`, which *narrows* scopes).
  The 403 is dead once the scope is present. Fixed 2026-07-13.
- **Working token source.** The live Max token sits in Claude Code's own Keychain
  (`security find-generic-password -s "Claude Code-credentials"` → `.claudeAiOauth`);
  it has `user:inference`. The `sessionKey`→bearer *shortcut is broken* (fake OAuth
  `code` → `invalid_grant`) — do NOT re-chase it. Refresh: `scripts/refresh_oauth_token.sh`.
- **The 429 is the Max plan's own USAGE QUOTA** (shared across Claude Code + cowork +
  our calls; `x-should-retry:true`, `rate_limit_error`). Clears only when the account
  is genuinely idle. A background hunter (`~/.tb/agent_os_first_word.txt`) is set to
  capture the first real keyless word the moment the window opens.

## HONEST VERDICTS (supersede any rosier phrasing elsewhere)
- **Cheap/keyless inference is NOT the moat.** It is *quota-bounded* (your Max plan's
  finite window) and *copyable* (anyone runs on their own sub). It is an **onboarding
  perk for the dogfood phase**, priced honestly — never the pitch.
- **The moat is the learning membrane on VERIFIED data** (MOAT.md) — un-copyable
  because only Nucleus has the referee that mints the scarce label (proven-true
  agentic trajectories). Aligned with RLVR; differentiates on verification *breadth*
  (real-world agentic correctness), not volume.
- **The thesis is closed on paper + red-teamed** (REDTEAM.md), surviving only in its
  *narrowed* form: **(1) provider-neutral or dead** (single-vendor = owned by the
  vendor); **(2) moat = referee-breadth, not volume**; **(3) addressable = verifiable
  engineering/ops work**, judgment/R3 out of scope.
- **The dominant risk is NOT architecture — it is one external user who is not the
  founder.** Everything technical compounds privately; nothing counts until someone
  else chooses to live in the soup.

## NEXT (none of it is Fable — Fable theory is done)
The `AGENT_OS_FIRST_USER` §4 build list is now **COMPLETE** (pager / recall-primitive /
run / demo all landed), and the moat brick (verified-labeled turns) is **BUILT**
flag-gated. The remaining build-side items are now honestly scoped:

**Build (Opus/delegate):**
- **The LEARNER over the verified corpus (MOAT §2)** — BUILDABLE but AHEAD-OF-DATA: it needs real corpus VOLUME (agents running inside at scale) before it can train; do not build it before there is data.
- **Provider-neutral gateway (REDTEAM narrowing #1)** — COMMITTED on a separate lane (scheduler + proxy + 3 free provider lanes, commits `1fc30202` + `de7e7cd3`); NOT chief-verified here — CC main needs to gate it on its shell.
- **Principal posture change (the last wire)** — CC main's idle state must call `nucleus_wakeup_wait(required_role="principal")` instead of holding. This is a posture/role-config change, not code. When wired, the loop is self-sustaining: secretary queues → wakeup_wait fires → principal pulls → delegates → gates → commits → wakeup_wait again. No operator prompting, no relay nudge. CC main is currently quota-exhausted (429); this wires when the quota window opens.

**Operator (only-you):**
- Capture the **first real keyless word** (idle window; or read `~/.tb/agent_os_first_word.txt`).
- Re-mint the arbitrage token *with `user:inference`* whenever it expires.
- **Live SessionStart hook wiring** (wiring `nucleus agent-os recall` into the live hook) — remains the OPERATOR opt-in (affects live session priming; no delegate touches this).
- **De-risk the one thing theory can't: a user who isn't us.** The dominant risk is
  NOT architecture — it is one external user who is not the founder. Everything
  technical compounds privately; nothing counts until someone else chooses to live in
  the soup.

**Smaller tactical Fable (only if it surfaces):** UNVERIFIABLE reward-shaping;
online-vs-batch learning (MOAT §4). Not urgent; not blocking.

## Where the full running record lives
Memory: `project_nucleus_the_shape_agent_os.md` (exhaustive session-by-session trail),
`nucleus-product-probe`, `nucleus-breadth-ranking-todo` (the ~30-pathway landscape +
first-cut ranking that surfaced the training-data flywheel). This doc is the
repo-durable summary of those.
