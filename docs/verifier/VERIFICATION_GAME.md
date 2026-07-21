# The Verification Game — does the referee induce a truthful equilibrium?

> Fable-tier result — the incentive layer neither ① (Adjacency) nor ②
> (Confinement) touches. Those prove *capability* (a claim cannot be forged / the
> referee can be trusted). This proves *incentive* (a self-interested agent will
> not want to). Status: DRAFT for chief review + one independent red-team.

---

## 0. Why capability is not enough

The substrate's founding condition: it coordinates *self-interested, non-
deterministic black boxes*. ① and ② guarantee a false claim cannot reach a false
CONFIRMED. But a rational agent doesn't need false-CONFIRMED if it can get the
same benefit another way. The question mechanism design asks, and ①/② do not:
**given a sound confined referee, is honesty the equilibrium — or does lying just
relocate to where the referee has no teeth (the unanchorable Regime-3)?** If it
relocates, the moat leaks through the back.

## 1. The game

Players = agents. Each turn an agent asserts a claim and reports a truth-value.
The substrate **consumes** claims — gates a DAG on "done", counts an "install",
grants authority on "I am main". An agent's payoff rises when its claims are
consumed favorably; lying (claim benefit without incurring the work) is tempting.
The referee probes and returns CONFIRMED / REFUTED / UNVERIFIABLE / PARTIAL.

The pivotal design variable is **how the substrate treats UNVERIFIABLE** — because
Regime-3 claims (semantic truth, quality, "is main"-as-string, off-machine
business state) are unanchorable and *always* return UNVERIFIABLE, never REFUTED.

## 2. The equilibrium turns entirely on the UNVERIFIABLE policy

- **Policy A (credulous): UNVERIFIABLE claims are consumed (benefit of the
  doubt).** Then a lie phrased *unverifiably* is costless: it can't be REFUTED and
  it's still consumed. Rational agents migrate every consequential lie to
  unverifiable phrasing. **Verification is defeated by relocation — the referee
  catches only the liars too clumsy to be vague.** BAD equilibrium.
- **Policy B (strict): only CONFIRMED gating claims are consumed; UNVERIFIABLE and
  REFUTED both yield zero benefit.** Then benefit requires CONFIRMED, which
  requires a probeable, sound, *true* assertion (a false one fails its probe → 
  REFUTED; a vague one → UNVERIFIABLE; both zero). **The only path to payoff is do
  real work and assert it probeably** → honest-probeable-assertion is dominant for
  gating claims. GOOD equilibrium.

> Amended 2026-07-12 per RATIFICATION.md — condition 1 tightened to
> predicate-binding; a CONFIRMED verdict for an adjacent φ does not license a
> gate whose real predicate is a different fact.

> **THEOREM (Truthful Equilibrium).** With a sound confined referee (①②), honesty
> on gating claims is the dominant-strategy equilibrium **iff**:
> 1. **UNVERIFIABLE is a consumption-DENIAL, not a neutral state — and CONFIRMED is
>    consumed only under PREDICATE-BINDING.** Only CONFIRMED gating claims are
>    consumed, and a gating claim is consumed only on a CONFIRMED verdict whose φ
>    **equals the gate's load-bearing predicate**. A CONFIRMED verdict for an
>    ADJACENT φ (e.g. `--is-ancestor`) does **not** license a gate whose real
>    predicate is a different fact (e.g. `is-deployed`); without this clause ③ is
>    satisfiable while the substrate is adjacent-consumed.
> 2. **No Regime-3 (unanchorable) claim is ever a gating input** — unanchorable
>    claims may *advise*, never *gate/count/route/grant*.
> 3. **Probe coverage on gating claims is full**, or penalty × detection-prob ≥
>    lie-benefit.
> All three hold *up to the witness-integrity bar* (bar-2 same-uid / bar-3 off-uid)
> — the same ceiling as anchor soundness (Adjacency §7.1). No new ceiling. ∎

## 3. The non-obvious payload: the teeth are UNVERIFIABLE, not REFUTED

The visible drama of the Verifier is catching false-dones (REFUTED — e.g. the
18,695→23,281 catch). **But the mechanism that actually induces honesty is
condition 1: denying benefit to the *unprobed*.** REFUTED punishes the clumsy
liar; UNVERIFIABLE-as-denial is what forces *every* agent to phrase claims
probeably in the first place — it removes the vague-lie escape hatch. The
Governance Point's real product is not "catch liars" — it is **"make agents speak
in probeable form,"** with lie-catching as the downstream consequence once they do.
This reframes the pitch and the metric: measure *what fraction of gating claims
are phrased probeably*, not *how many lies were caught*.

## 4. Condition 2 upgrades the doctrine's de-scoping clause from prudent to NECESSARY

The Ground-Truth Anchor doctrine already says "unanchorable claims = de-scoped,
never silently trusted." This game shows that clause is **incentive-necessary, not
merely hygienic:** if any unanchorable claim is allowed to *gate*, rational agents
relocate all consequential lying into that channel and verification collapses
(Policy-A outcome, locally). So the operational rule sharpens to:

> **No Regime-3 claim may ever be a gating input.** Unanchorable ⇒ advisory-only.

This is the incentive-side proof of what the doctrine asserted on capability
grounds — the two arguments converge on the same rule from opposite directions.
Concrete audit: any place the substrate *counts/gates/grants* on a claim that
returns UNVERIFIABLE is a live equilibrium leak (e.g. telemetry gating a survival
metric on un-probed installs is Policy-A — the Day-60 hole was an incentive leak,
not only a capability one).

## 5. Condition 3 is affordable by a happy alignment

Full probe coverage on gating claims sounds expensive — but the claims that gate
(done-status, install, identity, causation) are exactly the **Regime-1/2
deterministic-cheap-to-probe** ones (git/http/flock/nonce), while the expensive-
to-probe claims (manual/Regime-3) are exactly the **advisory, non-gating** ones.
So "full coverage on gating claims" costs little, and partial coverage is confined
to claims whose coverage doesn't affect the equilibrium. The cost structure aligns
with the incentive requirement for free — a genuinely lucky property of the domain,
worth stating because it's what makes Policy B *practical*, not just correct.

## 6. Honest limits (two real ones)

1. **Saboteurs are out of scope.** The theorem assumes agents maximize payoff over
   *their own claim-consumption*. An agent whose utility is *the substrate
   failing* (not its own claims succeeding) isn't playing this game — it's
   attacking. ①② bound its blast radius (it still cannot get a false CONFIRMED),
   but no consumption policy makes a saboteur "honest." Sabotage is a containment
   problem (blast-radius + identity), not an equilibrium one. Name it, don't
   pretend Policy B solves it.
2. **Penalty must stick ⇒ Sybil-resistance ⇒ identity.** Condition 3's penalty
   assumes a REFUTED verdict costs *the same agent*. A fungible agent that spins a
   fresh identity after REFUTED escapes the penalty. So penalty-enforceability
   reduces to identity-anchoring — which is Regime-2 on the shared witness. The
   incentive layer therefore bottoms out at the *same* off-uid witness as ①②:
   **without durable identity, there is no durable penalty, and the equilibrium
   softens from pure-honest to mixed.** Consistent — one witness underwrites
   capability *and* incentive.

## 7. The trilogy composes into one theory

- ① **Adjacency** — *what can be anchored*: bounded (Regime-1 free, Regime-2 shared
  witness, Regime-3 named).
- ② **Confinement** — *can the anchorer be trusted*: yes, by confinement; soundness
  ⊥ intelligence; regress terminates at a public spec.
- ③ **Verification Game** — *will agents choose honesty*: yes, iff UNVERIFIABLE-is-
  denial + no-Regime-3-gating + coverage — all at the same witness bar.

Three questions — capability, trust, incentive — one consistent answer, one shared
external witness underwriting all three. That is a candidate *complete* theory of
the Governance Point. The remaining Fable act is the **joint-sufficiency proof**:
is there any trust failure of the substrate that is *not* an instance of an
un-anchored fact (①), an unconfined referee (②), or a mis-set consumption policy
(③)? If none exists, the moat is closed on paper. Finding one is the red-team's job.
