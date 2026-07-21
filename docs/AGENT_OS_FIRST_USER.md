# Agent OS — We Are the First User (onboarding, dogfood, first felt value)

> ▶ Current built/proven state & doc-map: see AGENT_OS_STATE.md
>
> Fable-tier, 2026-07-13. The REDTEAM named the dominant risk as "a user who isn't
> us." This doc dissolves it, honestly: the sharper truth is *a user, starting with
> us* — and we are the realest possible first user, because **we have spent whole
> sessions hand-performing the exact functions the OS automates.** Onboarding is
> therefore *subtractive* (replace a manual chore with its automatic OS version),
> and the first felt value is *our own relief* — which cannot be faked, demoed, or
> imagined. If it doesn't relieve us, it isn't real; if it does, we've found the
> onboarding for everyone.

## 0. The proof we are the user (not theater)

Across this program we manually implemented the OS by hand:

| The OS function | How we do it BY HAND today | Pain |
|---|---|---|
| Memory-inject | hand-maintained memory files, cold re-bootstrap each session | "everything gets lost in context" — acute, recurring |
| Referee | gating every agent's "done" on my own shell, distrusting self-reports | the whole session's discipline |
| Coordination | banking, relaying, cross-linking to keep the fleet coherent | constant overhead |
| Flywheel | (not done by hand — genuinely new value) | — |

**We are not looking for a user with this pain. We are the user, and we've been
paying the tax all night.** The OS's job is to stop us paying it.

## 1. The onboarding principle: subtractive, relief-measured

Do **not** onboard by adding a new thing to learn. Onboard by **removing a manual
chore** and letting the automatic version take over. The metric is not "did they
adopt a feature" — it is **"did we stop doing something painful by hand."** One
subtraction that lands is worth more than ten features that don't, because relief
is self-evident and self-propagating: the next user has the same tax, so the same
subtraction onboards them.

## 2. The first win: memory continuity (the pick, argued)

Of the three manual chores, **memory-inject is the first onboarding win** — because:
- It is the pain we hit *hardest and most often* (this very session re-bootstrapped
  cold; the memory files exist *because* we keep losing the thread).
- It is the **first cell's existing function** (recall → inject; BUILT + verified,
  `AGENT_OS_STATE.md`). The organ exists; only the *pager* (selectivity) is missing.
- Its value is felt on **turn one**: the session opens already knowing the right
  prior context, correctly — not a wall of everything (the recall-blur), the *right*
  slice.
- It is honest and small: no model-hosting, no quota wall, no new surface — just
  "your next session starts where the last one left off, verified."

The onboarding, concretely: **our own next session's context is auto-recalled,
selectively, by the OS** — replacing the memory-file ritual. When *we* feel "I
didn't have to re-explain anything and it was the right context," the OS did
something real. That sentence is the product.

## 3. The honest architecture of "we run inside" (no self-deception)

The inversion needs the OS to own the agent's loop. We must be honest about where we
can and cannot:
- **Agents we SPAWN (delegate/GLM/Gemini, the EphemeralAgent runner): full inside.**
  We own their loop → real gateway-mediation, memory-inject, verified-record. These
  genuinely *live in the OS today.* This is the true dogfood surface.
- **Frontier clients we DON'T own (Claude Code, cowork): OS-as-service, not inside.**
  We cannot intercept Claude Code's model calls (Anthropic owns that loop — REDTEAM
  Attack 1). So Claude Code *consumes* the OS via MCP + the SessionStart hook
  (memory recall, verified status) — a **client of the OS, not a resident.** That is
  honest and fine: the value (right-context, verified) is felt either way.

So the dogfood is two-tier and we never pretend otherwise: **the spawned fleet lives
inside; the human-facing clients use the OS's organs as services.** Both relieve the
tax; only the first is the literal inversion.

## 4. What is Fable here vs what is build (the honest split you asked for)

- **FABLE (this doc):** recognizing we are the user + the manual-OS; choosing the
  *subtractive relief metric*; picking memory-continuity as the first win; the honest
  two-tier "inside vs service" architecture. These are non-decomposable product +
  architecture judgments. **Done here.**
- **BUILD (Opus/delegate) — the "make it work" list:**
  1. The **pager** (relevance × recency × verified-trust against a context budget) —
     fixes the recall-blur so the injected memory is the *right* slice. This is the
     unlock for win #1.
  2. Wire selective-recall into the **SessionStart hook** so our own next session
     auto-loads the right context (Claude-Code-as-OS-client).
  3. `nucleus run` for **spawned agents** — full inside-mediation (memory + verified-
     record) for the fleet we own.
  4. A one-command **onboarding** that flips one lane from manual to OS and shows the
     before/after relief.
- **OPERATOR:** run the dogfood for a week; log every time the OS saved a manual
  chore (the relief ledger) — that ledger *is* the traction proof, and it's real
  because it's our own pain, measured.

## 5. The reference-product path (the ambition, made concrete)

To become the category-defining thing for the AI OS — the AutoGPT/Cursor-moment for
agent operating systems — you do not start with a launch. You start with **one user
(us) who genuinely cannot go back**, because the OS quietly does the exhausting thing
they used to do by hand. The aha that makes *us* never run an agent naked again — "it
remembered, correctly, and I trusted its work" — is the *same* aha that onboards the
next person, because they have the same tax. **Dogfood to undeniable, then widen.**
The category is defined by the first person who lives in the soup and refuses to
leave — and that person is here, tonight, already paying the tax the OS was built to
end.
