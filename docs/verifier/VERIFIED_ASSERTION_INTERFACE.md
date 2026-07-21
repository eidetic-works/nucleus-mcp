# The Verified-Assertion Interface — is the portfolio one primitive?

> Fable-tier cross-portfolio synthesis (freed from the substrate lane). Claim:
> NucleusOS (agent-facing) and ComposedFit/"One" (human-facing) are the *same*
> primitive — a Verified-Assertion Interface — so the Governance-Point theory
> (①Adjacency ②Confinement ③Game ④Sufficiency) transfers across the B2B/B2C
> boundary. Method: state the abstraction, exhibit the isomorphism, TRANSFER the
> theory and check its predictions, then try to break it. Status: DRAFT + red-team.
> Boundary: this yields the unifying *thesis* and its *prescriptions*; whether to
> bet the portfolio on it is the operator's call, out of scope here.

---

## 0. The observation that started it

Cowork's independently-authored "One" doctrine: *"the answer arrives like a
judgment; every claim on every screen traces to data; the walk-out line is built
only from verified attributes, omitted when we can't back it; the price is a
provable fact from price_history, not a confidence score."* Read against the trust
theory, that is not a design language — it is ①+③ applied to a shopping UI, arrived
at from the opposite direction. Independent convergence on the same shape is the
signal worth chasing.

## 1. The abstraction — VAI

> A **Verified-Assertion Interface** is a coordination surface where one party
> consumes another's assertions to *act or decide*, and trust is established by:
> (a) anchoring every *consequential* assertion to a source re-checkable outside
> the asserter's authority, and (b) **refusing to assert the unanchorable** —
> silence, not a confident guess, where the data runs out.

NucleusOS is the VAI whose consumer is an **agent** (consumes claims to *act* —
gate a DAG, count a metric). ComposedFit/"One" is the VAI whose consumer is a
**human** (consumes claims to *decide* — buy or not). Same interface, two audiences.

## 2. The isomorphism (the mapping is exact, not analogical)

| Trust-theory element | NucleusOS (agent-facing) | ComposedFit "One" (human-facing) |
|---|---|---|
| Load-bearing assertion | "task done / is role / install happened" | "this item fits / this is the price / this cut suits you" |
| Re-checkable oracle | git object store, kernel, vendor session | catalog, `price_history`, verified fit-attributes |
| ① anchor | commit `--is-ancestor`, exit code | "receipts trace to data" — each attribute → catalog row |
| ③ UNVERIFIABLE = denial | un-probed claim not consumed | **"walk-out line omitted when we can't back it"** |
| No Regime-3 gating | semantic/quality never gates | **"a provable price fact, not a confidence score"** |
| ② confinement | render pipeline can't emit unsound verdict | render pipeline **structurally cannot** print an unbacked receipt |
| The consumer | an agent that probes | a human who *can't* probe → receipts ARE the pre-computed probe results |

The last row is the crux and §4 stress-tests it. Everything above it is a literal,
element-by-element correspondence, not a loose metaphor.

## 3. Transfer test — do ①②③④ make correct, non-obvious predictions on the B2C side?

A shallow analogy explains nothing new. A real isomorphism lets the theory
*predict*. It does, four times, and each matches what cowork reached independently:

1. **③ ⇒ the teeth are OMISSION, not richness.** ComposedFit's trust comes from the
   *walk-out line being omitted when unbacked* — UNVERIFIABLE-as-denial — not from
   showing more attributes. Prediction: **the conversion metric is "fraction of
   shown attributes that are data-anchored," not "number of attributes shown."**
   Cowork's E2/E3 (walk-out line from verified attributes only; named contrast
   labels only where the axis is real) is exactly this, derived independently.
2. **① temporal axis (from ④/F1) ⇒ price staleness is a live failure.** "The price
   is 22% below its 90-day average" is sound only *at render time*; a stale
   `price_history` read makes a true-at-t₁ claim false-at-decision. Prediction:
   **price claims need a freshness anchor**, the same mtime/version invalidation as
   `recall`. This is a concrete, testable requirement the design should carry.
3. **④ compositional ⇒ "22% below average" is an AGGREGATE claim needing its own
   anchor.** It's a function over `price_history`, not a leaf fact — so it must be
   anchored at the aggregate level (the window, the baseline, the arithmetic), not
   just "the current price exists." Cowork's insistence that it is "a provable
   price fact, not a confidence score" is precisely refusing to let a Regime-3
   score stand in for a Regime-1 aggregate. Match.
4. **② confinement ⇒ soundness ⊥ the model's taste.** "One" can run its styling on
   a weak model and still never *fabricate* an attribute, provided the render
   pipeline is confined (attributes come from the catalog table, the model only
   *selects/orders*, never *asserts* a value). Prediction: **the trustworthiness of
   "One" does not depend on the LLM's quality — only its taste/coverage does.**
   Same soundness-⊥-intelligence corollary, same de-risking, transferred whole.

Four transferred predictions, four independent matches. The isomorphism is deep.

## 4. Adversarial refutation — where it should break, and why it doesn't

**The break attempt:** the agent-VAI consumer *probes for itself*; the human-VAI
consumer *cannot probe a receipt* — so the human must trust that ComposedFit's
receipt is real. Doesn't that reintroduce exactly the self-report the theory
forbids ("trust me, this attribute is verified")?

**Why it holds:** the receipt is not the human's probe — it is the *system's* probe
result, pre-computed. The question "is the receipt real?" is the verifier's own
VC-1/VC-3 integrity claim (② §2): does the render pipeline emit only receipts it
actually anchored? That is Regime-2, rides the same confinement + shared-witness
argument, and does **not** recurse into the human. The human's trust bottoms out
at the *same fixed, auditable pipeline spec* as an agent's does — not at
ComposedFit's word. So the "human can't probe" difference relocates the trust to
②'s confinement terminus, exactly where the agent case already put it. It doesn't
break; it re-derives ②.

**The genuine, non-breaking difference:** the *consequence* of a false assertion
differs — agent: corrupted coordination (a wrong DAG release); human: a bad
purchase + permanent trust loss. Different blast radius, identical mechanism. If
anything the human surface is *less* forgiving (a human defects forever after one
betrayed receipt), which makes the omission-discipline more valuable there, not
less — strengthening, not breaking, the transfer.

## 5. Payload — the unifying thesis (and what it is NOT)

> Amended 2026-07-12 per RATIFICATION.md — moat scoped to the evidence/attribute
> layer; "one metric captures buy-side trust" deleted; selection-verdict limit
> added (the "One" pick is Regime-3, decomposes into anchored match + hedged taste).

**The portfolio is one primitive on two surfaces.** NucleusOS and ComposedFit are
not a B2B tool and an unrelated commerce hobby; they are the agent-facing and
human-facing instances of the Verified-Assertion Interface. Consequences:

- **The moat theory is portfolio-wide — at the evidence/attribute layer.** ①②③④
  are domain-general — proved on the substrate, transferred intact to commerce's
  *evidence/attribute* layer (receipts trace to data, attributes come from catalog
  rows). Whatever defensibility the substrate has at that layer, the consumer
  product inherits, and vice-versa: two proofs of the same primitive from opposite
  ends is stronger evidence it's real than either alone. The transfer does **not**
  extend to the selection verdict (see the limit below).
- **A shared, testable metric across both surfaces:** *fraction of gate-bearing
  assertions whose φ matches the gate predicate* (predicate-bound, per G2) — not
  "fraction of shown attributes anchored." The earlier framing that "one number
  describes trust on the agent side and the buy-side" over-claimed: that number is
  blind to the selection verdict, which is Regime-3 at render time and sells, so it
  does not capture buy-side trust whole.
- **The selection-verdict limit (the "One" pick is Regime-3).** The pick of one
  item over 400 — "this is *the One* for you" — has load-bearing fact "best-
  aesthetic-fit-for-user-U," whose only downstream witness (U keeps-vs-returns)
  fires *after* the sale → **Regime-3 at render time**. It is the product's core
  sold assertion, so it is neither data-anchored nor honestly omittable (omitting
  it dissolves "the One"). The honest move, which cowork's hedged contrast-labels
  already implement: decompose the pick into (a) an **anchored MATCH claim** —
  "best match to your stated constraints," R1/R2, provable against the stated ask —
  *sold* with receipts; and (b) a **hedged TASTE claim** — aesthetic superiority —
  *advisory*, never sold as objective superiority ("the difference is taste — you
  pick"). The sale rests only on (a); (b) is advisory. This is G2's predicate-binding
  on the B2C surface: the gate (the buy) may rest only on the predicate the evidence
  actually covers (match), never on the R3 predicate (superiority). The B2C surface
  cannot gate on "the best" the way B2B gates on "done" — it can only gate on
  "matches your ask" and hedge the rest.
- **A shared design law:** never let a Regime-3 assertion gate/sell. "Silent where
  the data is" (cowork) = "no Regime-3 gating" (③) = the same rule in two dialects.
  The selection-verdict limit above is the one place this rule bites hardest on the
  B2C surface, because the pick *wants* to be sold as "the best" and must not be.
- **Cross-pollination is now principled, not incidental:** a hardening on one
  surface (e.g. the freshness anchor, the aggregate-anchor discipline) is a
  ready-made upgrade on the other.

**What this is NOT:** it is not a claim that either product has a market, nor a
recommendation to bet on the portfolio. It is a structural result — the products
share a primitive and a proof. Acting on it (positioning, resourcing, the venture
question) is the operator's decision and deliberately out of this document.

## 6. Honest limits + ratification

1. **The B2C side is asserted from cowork's *doctrine*, not its *code*.** The
   isomorphism is proven at the design-contract level. Ratifying it empirically =
   check that ComposedFit's actual render pipeline is *confined* (attributes come
   from catalog/`price_history` rows, the model cannot inject a value; the walk-out
   line is truly suppressed when an attribute is missing). **That check is
   Opus/agent-delegatable** — a concrete audit of the "One" render path against §2.
2. **"Consequential" is doing work.** The transfer covers assertions that *gate or
   sell*; decorative copy is out (correctly — it's advisory, ③). The line between
   consequential and decorative on a shopping screen needs one careful pass — a
   bounded design-review task, not Fable.
3. Ratification bar, as everywhere: one independent red-team trying to exhibit a
   consequential ComposedFit assertion that is trusted but *not* anchored and *not*
   honestly omitted — a Regime-3 claim that sells. Finding one refutes §5's
   "portfolio-wide moat"; not finding one confirms the primitive is shared.

## 7. Verdict

The isomorphism is exact at the contract level and the theory transfers with four
matched non-obvious predictions and no surviving break. **NucleusOS and ComposedFit
are one Verified-Assertion Interface on two audiences.** This is the unifying
portfolio thesis the roadmap has been circling — arrived at not by strategy
narration but by transferring a closed proof across a domain boundary. The Fable
act was the transfer; the empirical ratification (audit the "One" render pipeline)
and everything downstream are delegatable.
