# Ratification log — independent red-team pass (2026-07-12)

> The theory docs (①Adjacency ②Confinement ③Game ④JointSufficiency + VAI) each
> called for one independent red-team to ratify. A Gemini-family agent (genuine
> cross-model independence) ran the three break-jobs G1/G2/G3. Outcome: **2 HOLD
> with refinement, 1 REFUTED (a §-scoped over-claim, not the core).** Chief has
> adjudicated all three as correct. This log records the verdicts + the amendments
> they require. Where an amendment is inline-pending, applying it to the named doc
> is a delegatable follow-up.

---

## G1 — Adjacency Theorem: **HOLDS** (refinement)

Attack: OS package-receipt DB / journald / root audit log are on-machine,
root-owned, downstream of a real install/exec — a sound *internal* anchor for a
"listed-R2" fact (install-happened, is-live, who-wrote).

Adjudication: does **not** refute — R2 is *defined* by witness location relative
to `auth(P)`, so a witness outside `auth(P)` is R1 *by construction*; the boundary
is analytic. Against same-uid **root** every on-machine oracle falls (§7.1), so
nothing crosses cleanly.

**Amendment (ADJACENCY_THEOREM §4, inline-pending):** regime membership is
**topology-relative (privilege), not fact-type-intrinsic**. Re-cut §4.2's
type-taxonomy: a pre-existing *different-uid* OS oracle gives several "listed-R2"
facts a **free** R1 anchor — the "R2 always needs a bespoke built witness" framing
is too strong for the OS-oracle subset. This *helps* the roadmap (some R2 items
anchor for free via the OS).

## G2 — Joint Sufficiency: **HOLDS** (no 4th mode) + material sharpening

Attack (claim-substitution at consumption): referee soundly `CONFIRMED(φ =
--is-ancestor)`; the substrate gates *deploy*, whose real predicate is `ψ =
is-deployed` (false). Policy ③ "consume only on CONFIRMED" is *satisfied*, yet
false ψ gated. (Same shape as census: "distinct sessions" CONFIRMED-true,
"independent humans" false-and-gated.)

Adjudication: folds into **①-compositional** (the verdict-record `CONFIRMED(φ)` is
itself an *adjacent anchor* for ψ; ④/F2 already treats verdicts as claims) — so no
fourth mode. **But ③ as literally written is exploitable.**

**Amendment (VERIFICATION_GAME ③ / JOINT_SUFFICIENCY, inline-pending — LOAD-BEARING):**
tighten condition ③.1 to **predicate-binding**:
> *Consume a gating claim only on a CONFIRMED verdict whose φ **equals the gate's
> load-bearing predicate**.* A CONFIRMED verdict for an adjacent φ (e.g.
> `--is-ancestor`) does **not** license a gate whose predicate is a different fact
> (`is-deployed`). Without this clause, ③ is satisfiable while the substrate is
> adjacent-consumed.

This is the ADJACENCY Adjacent-Fact Test applied to the **verdict→gate seam** — the
one seam the trilogy hadn't named explicitly. It strengthens ④, doesn't weaken it.

## G3 — VAI §5 universality: **REFUTED** (scoped; core isomorphism survives)

Attack (counterexample): the **selection verdict** — "this is *the One* for you,"
the pick of one item over 400 — has load-bearing fact "best-aesthetic-fit-for-
user-U," whose only downstream witness (U keeps-vs-returns) fires **after** the
sale → **Regime-3 at render time**. It is the product's *core sold assertion*, so
it is neither data-anchored nor honestly omittable (omitting it dissolves "the
One"). §5's metric ("fraction of consequential assertions data-anchored") scores
100% on true attributes while the *pick* is R3 — the metric is **blind to the
thing that sells.**

Adjudication: **correct — §5's universality is refuted.** The ①②③④ isomorphism
holds at the **evidence/attribute layer** (receipts trace to data — genuinely
sound); it does **not** extend to the selection verdict, which is R3. My §5
over-claimed "one metric captures buy-side trust."

**But the theory is repaired, not destroyed** — and by ③ itself: an R3 assertion
**may not be sold as truth; it must be hedged/advisory** (③.2, no-R3-gating).
ComposedFit's honest move (which cowork *already designed*): split the pick into
(a) its **anchorable** component — "best MATCH to your stated constraints," R1/R2,
provable — asserted with receipts; and (b) its **R3** component — aesthetic
superiority — **hedged**, not asserted ("the difference is taste — you pick,"
cowork's E3 contrast-labels). The sale rests only on (a); (b) is advisory. **This
is exactly G2's predicate-binding on the B2C surface:** the gate (the buy) may
rest only on the predicate the evidence actually covers (match), never on the R3
predicate (superiority).

**Amendment (VERIFIED_ASSERTION_INTERFACE §5, inline-pending):**
- Scope the "portfolio-wide moat" claim to the **evidence/attribute layer**; delete
  "one metric captures buy-side trust."
- Add the **selection-verdict limit**: the pick is R3; it must decompose into an
  anchored *match* claim (sold) + a hedged *taste* claim (advisory), never sold as
  objective superiority. cowork's hedged-contrast-labels already implement this.
- The shared metric becomes: *fraction of **gate-bearing** assertions whose φ
  matches the gate predicate* (predicate-bound, per G2) — not "fraction of shown
  attributes anchored."

## The unifying finding (chief note)

G2 and G3 are **one defect on two surfaces**: *a sound verdict consumed for a
decision whose real predicate it does not cover.* On the substrate it's a
tightening of ③ (predicate-binding). On ComposedFit it's structural — the
"judgment" the product sells is inherently R3, honorable only by hedging the R3
part and selling only the anchored match. The asymmetry the red-team flagged is
real and worth stating: **the B2C surface cannot gate on "the best" the way B2B
gates on "done" — it can only gate on "matches your ask" and hedge the rest.**

## Status after this pass

- Core theory (①②③④, VAI at the evidence layer): **ratified, standing.**
- ③ requires the **predicate-binding** clause (G2) — LOAD-BEARING, apply inline.
- ADJACENCY §4.2 regime taxonomy: **topology-relative** re-cut (G1) — apply inline.
- VAI §5 universality: **refuted**; corrected to evidence-layer + hedged-selection
  (G3) — apply inline.
- Inline application of the three amendments to the named docs = a delegatable
  follow-up (mechanical, chief-reviewed). The theory as corrected here is the
  authoritative version until then.
