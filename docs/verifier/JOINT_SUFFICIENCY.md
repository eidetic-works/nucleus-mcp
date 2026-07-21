# Joint Sufficiency — is the trilogy a complete trust theory?

> Fable-tier closure of the Governance-Point trilogy (①Adjacency, ②Confinement,
> ③Verification-Game). Claim: every substrate trust-failure is an instance of at
> least one of the three. Method: causal decomposition of an arbitrary failure,
> then an adversarial hunt for a genuine *fourth* mode. Status: DRAFT + red-team.

---

## 1. The claim

A **trust-failure** = the substrate *consumed* a gating claim `C(φ)` — gated a DAG,
counted a metric, routed, or granted authority — while its load-bearing fact `φ`
was **false**. Claim: every such event is one (or more) of:

- **①** an **un-anchored fact** — consumed on an anchor that passed while φ false
  (adjacent anchor, or a captured witness), or
- **②** an **unconfined referee** — the verifier's discretion produced an unsound
  verdict, or
- **③** a **mis-set consumption policy** — a non-CONFIRMED claim was consumed, or a
  Regime-3 claim was allowed to gate.

## 2. Proof by decomposition (sufficiency over the base modes)

Take any trust-failure: false `φ` was consumed. The consumption decision was made
either **without a CONFIRMED verdict** or **on a CONFIRMED verdict**.

- **Without a CONFIRMED verdict** — the claim was un-adjudicated, or adjudicated
  non-CONFIRMED (REFUTED/UNVERIFIABLE/PARTIAL) and consumed anyway, or the referee
  was bypassed entirely. All three violate the universal policy *"consume a gating
  claim only on CONFIRMED."* → **③.**
- **On a CONFIRMED verdict, yet φ false** — a *false CONFIRMED*. A sound confined
  referee emits false-CONFIRMED only if (a) the anchor was **adjacent** (passed
  while φ false) or its **witness was captured** → **①** (incl. Adjacency §7.1
  same-uid-root witness-integrity limit); or (b) the referee was **not actually
  confined** — its table emitted an adjacent anchor, or classification joined
  *down* → **②**.

The two branches are exhaustive over "how a false φ reached consumption." ∎ (base)

## 3. Adversarial hunt for a genuine fourth mode (the real work)

Sufficiency over the base modes is easy; the value is trying to *break* it. Four
candidate fourth-modes, pressed hard:

**(F1) TOCTOU / staleness.** Referee *soundly* CONFIRMED `φ` at t₁; the agent
reverted the commit / killed the daemon by consumption-time t₂. Verdict sound,
referee confined, policy consumed a CONFIRMED — yet φ false at use. *Escapes?*
**No — it is ① along a new axis.** The load-bearing fact is `φ@t₂`; the anchor
attested `φ@t₁`. "φ@t₁" is *adjacent in time* to "φ@t₂" exactly as PID-lineage was
adjacent in *causation* to role. **Refinement harvested: the Adjacency Law has a
TEMPORAL dimension — a sound witness must be downstream of φ *and current at
consumption*.** Fix is ①'s own kind: re-probe at use, or a freshness witness that
invalidates on change (precisely `recall`'s mtime/rowcount R1 anchor). Folds into
① and *strengthens* it.

**(F2) Aggregation.** The substrate gates on a *function* of many claims (census =
Σ attributions; "≥3 distinct agents shipped"). Every leaf claim is soundly
CONFIRMED, yet the aggregate misleads (double-count, non-distinct, or the
aggregation function embeds a false premise like "installs" summing CI runs).
*Escapes?* **No — the aggregate is itself a claim** with its own φ ("the total is
T", "the 3 are distinct") and its own anchor duty. Gating on an un-anchored
aggregate = ① at the aggregate level; gating on an aggregate that is really
Regime-3 = ③. **Refinement harvested: the theory is COMPOSITIONAL — ①②③ apply
recursively to every derived/aggregate claim, not only leaves.** This *is* the
crit-4/census de-anon-and-double-count risk, now located precisely.

**(F3) Referee unavailable (DoS/crash).** Claims flow while the verifier is down.
*Escapes?* **No — it is ③**, the fail-open-vs-fail-closed policy choice: consuming
un-adjudicated claims when the referee is absent is "consume without CONFIRMED."
Fail-*closed* (no verdict ⇒ no consume) is safe. Folds into ③.

**(F4) The confining spec is itself wrong** (a mis-ordered class, ⊤ not actually
strongest). *Escapes?* **No — it is ②'s residual trust (§7.1):** an unconfined
referee is precisely one whose confining spec is flawed. The spec is a Regime-2
integrity object on the shared witness; auditing it once is the terminus. Folds
into ②.

Also checked and folded: a consumer that *ignores* a REFUTED verdict (③, broken
consumer policy); a consumer that *mis-binds* a verdict to the wrong claim (② —
verdict-to-claim binding is part of VC-1 verdict-integrity).

**Result: no candidate fourth mode survived. Two attempts (F1, F2) did not break
the theory but sharpened it** — ① gains a temporal axis; the whole theory is shown
compositional. That is the healthy outcome of a real completeness hunt.

## 4. Self-applicability (the theory governs its own governance)

The substrate is *built by* the fleet — so "who governs the amendment of the
governing law (PRINCIPAL)?" is the referee-recursion one level up. ② answers it
unchanged: the amendment process is *confined* (roadmap-redteam = the confinement;
amendments must join *up* a conservatism lattice; the PRINCIPAL body-hash + git
tag = the verdict-integrity witness — VC-1 on the shared object store). The theory
is **self-applicable**: governance-of-governance is ② applied to PRINCIPAL, no new
machinery. A trust theory that cannot govern its own construction would be
incomplete in the way that matters most; this one can.

## 5. The two honest out-of-theory residues (named, not hidden)

1. **Witness-integrity ceiling.** All of ①②③ hold *up to* the bar at which the
   claimant can corrupt the witnessing oracle (same-uid root). This is not a fourth
   *mode* — it is the *floor* every mode rests on. Lifting it is the single shared
   off-uid attester; the theory says build that one thing, not nine stones.
2. **Saboteurs.** An actor whose utility is *the substrate failing* (not its own
   claims consumed) is outside the game (③ limit 1). ①② still deny it a false
   CONFIRMED (bounded blast radius), but no consumption policy makes it "honest."
   Sabotage is **containment**, not equilibrium — a distinct problem the trust
   theory correctly does *not* claim to solve.

## 6. Verdict

The trilogy is **jointly sufficient over all consumption trust-failures**, modulo
two explicitly-named residues (the witness-integrity floor and out-of-model
saboteurs). The completeness hunt found no fourth mode and instead harvested two
refinements (temporal adjacency; compositional application). The theory is
self-applicable to its own governance. **The Governance-Point moat is closed on
paper.** What remains is (a) the delegatable builds the theory specifies (R1 sweep,
one shared witness, mandatory-anchor table + lattice, freshness re-probe,
recursive aggregate-anchoring) and (b) the red-team's standing job: exhibit a
consumption trust-failure that is *not* an instance of ①, ②, or ③. Until one
appears, the paper is complete.
```
①  what can be anchored        → bounded (R1 free / R2 shared witness / R3 named)
②  can the anchorer be trusted → yes, by confinement (soundness ⊥ intelligence)
③  will agents choose honesty  → yes, iff UNVERIFIABLE=denial ∧ no-R3-gating
④  is that all the failures    → yes (mod witness-floor + saboteurs); +temporal, +compositional
```
