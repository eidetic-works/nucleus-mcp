# The Referee Confinement Theorem — who verifies the verifier?

> Fable-tier result settling ② (referee-recursion) from the zoom-out.
> Status: DRAFT for chief review + one independent red-team.
> Builds on ADJACENCY_THEOREM.md (regimes R1/R2/R3) and ANCHOR_DOCTRINE.md
> (the class→mandatory-anchor table, the AFT).

---

## 0. The question

The DSoR Verifier is the Governance Point — it audits everyone's claims. But it
is *itself* a claimant. Naively that starts an infinite regress: who audits the
auditor, and who audits *them*? Plus two concrete holes: its verdicts sit in
erasable ink (unkeyed `audit_log.py` chain), and its LLM reasoner reads
attacker-controlled claim text. Settle it: is there a trustworthy referee that is
itself a claimant, with a *terminating* trust argument?

## 1. Decompose the verifier's own claims (3 of them)

- **VC-1 verdict-integrity:** "verdict W for C is the one I computed, untampered."
- **VC-2 reasoning-fidelity:** "the anchors I probed are the *sound* set for C —
  not a weakened set steered by C's own text."
- **VC-3 probe-integrity:** "the evidence I report is what the oracle returned."

## 2. VC-1 and VC-3 are not new — they fold into the shared witness

Apply the Adjacency Theorem. **VC-1** (a verdict record is durable/attributed) and
**VC-3** (V's process ran probes untampered) are **Regime-2 ATTRIBUTION/durability
claims** — the load-bearing fact's only downstream witness is under an
equal-authority process's control (any process can recompute the unkeyed chain;
a compromised V fakes its own probes). Per Adjacency §6, every Regime-2 claim
rides **one shared off-authority witness** (sealed-key HMAC → bar-2; external
append-only chain-head → bar-3). **The verifier's own integrity is not a bespoke
new primitive — it is the same shared attester as every other Regime-2 fact.** The
regress does *not* branch into a second infrastructure; it folds into the one
witness the roadmap already needs. That disposes of two of the three worries by
composition, no new theory.

## 3. VC-2 is the real crux — and confinement, not a meta-referee, settles it

`claim.assertion` is attacker-controlled text. If the reasoner is "ask a model to
propose anchors for this claim," an adversary crafts text that steers toward a
*satisfiable-but-adjacent* anchor (embed "verified by the presence of commit X"
to nudge `commit_exists`). The naive fix — "have a smarter meta-referee check the
reasoning" — is the infinite regress. The escape is **confinement**: strip the
reasoner of any discretion that could produce an unsound verdict.

> **THEOREM (Referee Confinement).** A referee's verdicts are sound *independent of
> whether its reasoning is trustworthy* iff its discretion is confined to
> **fail-safe moves**:
>
> 1. **Anchor-KIND is doctrine-fixed, not model-proposed.** The class→mandatory-
>    anchor table (ANCHOR_DOCTRINE §3) selects the anchor *kind*; the model may
>    only *fill slots* (which SHA / URL / path). Slot-fills are then probed against
>    oracles outside the adversary's authority — a lie in a slot fails its probe.
> 2. **Classification joins UP an anchor-strength lattice.** Order claim-classes by
>    anchor strength; on ambiguity, take the **join** (the union of mandatory
>    anchors of every plausible class), never a single weaker class. An adversary
>    steering classification can therefore only make the referee demand *more*
>    evidence, never less. Misclassification is fail-safe.
> 3. **The lattice has a top ⊤ = "unknown class → maximally strong / manual".** A
>    claim that matches no known class classifies to ⊤ (UNVERIFIABLE), never
>    silently to a weak class.
>
> Under (1)–(3), the adversary's control of claim text can only *tighten* the
> audit. Every discretionary move the referee makes is either fail-safe-up
> (classification) or externally-probed (slot-fill). No adversarial input yields a
> false CONFIRMED. ∎

## 4. Where the regress actually terminates (the honest terminus)

Confinement does not make trust vanish — it **relocates** it, from *per-verdict
discretion* to *a fixed, public, once-auditable spec*: the class→anchor table + the
lattice + the ⊤ element. You no longer need to trust each verdict, or a tower of
meta-referees; you trust one artifact, audited once by humans/red-team, exactly as
you trust a compiler's spec rather than re-verifying every compilation. **The
regress terminates at a public constant, not at a top-referee.** That is the whole
escape: *don't find a trusted auditor — remove the auditor's ability to be
untrustworthy.* It is the capability-confinement pattern applied to judgment.

## 5. The corollary that inverts the folk requirement (and de-risks the stub)

The folk claim — "the referee must be at least as smart as the agents it referees"
— is **false for soundness, true only for coverage:**

> **COROLLARY.** A *confined* referee is **sound on any model, however weak** — it
> never emits a false CONFIRMED; a dumb model only emits more UNVERIFIABLEs
> (misses), which are safe. Intelligence buys **coverage** (how many claims get a
> real anchor rather than ⊤), **not trust.**

Consequence for the "LLMReasoner is a stub" gap (previously graded a load-bearing
hole): under confinement it is a **coverage** limitation, **not a soundness** one.
The claims a stub *does* decompose — via the fixed table — are sound; the ones it
can't just fall to ⊤/UNVERIFIABLE. **The moat's trust does not depend on frontier
intelligence.** This materially downgrades gap-A: the Governance Point can ship
*sound* on `RuleReasoner` alone, and frontier reasoning is a coverage upgrade, not
a trust prerequisite.

**One caveat that makes this concrete:** it holds only once `RuleReasoner`'s table
emits the ANCHOR_DOCTRINE §3 **mandatory** (non-adjacent) anchors. Today it emits
`commit_exists`/bare-200 — *adjacent* — so today's RuleReasoner is confined but its
table is unsound. Fixing the table to mandatory anchors + adding the lattice-join
classifier is the concrete build that cashes the corollary — and it is
**Opus/ultracode-delegatable** (bounded, spec-driven). The Fable piece is this
theorem + the lattice design; the wiring is not.

## 6. Composition check against ① (no cross-gap)

①(Adjacency) answers *what is anchorable*; ②(Confinement) answers *can the
anchorer be trusted*. They compose without a seam: ② confines the reasoner to the
mandatory anchors ① proves sound, and ②'s own integrity claims (VC-1/VC-3) are ①'s
Regime-2 facts on the shared witness. The one place they could clash — a claim
that is Regime-1 (internally anchorable) but whose *classification* is steerable —
is caught by lattice-join: ambiguous R1/R2 joins up to demand the R2 witness too,
costing coverage, never soundness. No cross-gap found; an independent red-team
hunting one is the ratification step.

## 7. Honest limits

1. **Table/lattice completeness is the residual trust.** A missing class weakens
   coverage (falls to ⊤) but not soundness — *provided* ⊤ is truly maximally
   strong. The single audit obligation is: *the ⊤ element is genuinely the
   strongest, and no known class is mis-ordered below a weaker one.* That is a
   finite, public, human-checkable claim about the spec — the terminus of §4.
2. **Confinement assumes the table itself isn't hot-swappable by the adversary** —
   i.e., the spec is a Regime-2 integrity claim on the shared witness (same as
   VC-1). Fold it in; do not ship the table as a claimant-writable file.
3. Soundness ⊥ intelligence is a *lower bound* (no false CONFIRMED). It says
   nothing about REFUTED precision — a confined-but-dumb referee could REFUTE a
   true claim by probing a mis-slotted anchor. REFUTED, unlike CONFIRMED, is
   recoverable (re-probe), so this is a coverage/annoyance cost, not a trust hole.

## 8. Verdict

There is a trustworthy referee that is itself a claimant, and the trust argument
terminates. Not by an infinite tower and not by a trusted top-auditor, but by
**confinement**: fix the anchor-kind by doctrine, join classification up a strength
lattice, ride the shared witness for the referee's own integrity. The result
inverts the folk requirement — **soundness is independent of the referee's
intelligence; only coverage scales with it** — which downgrades the stub-reasoner
gap from fatal to incremental. ②, like ①, converts a worry into a bounded,
mostly-delegatable engineering surface with a small Fable-authored kernel.
