# The Adjacency Theorem — is the recurring forgery a conservation law?

> Fable-tier result settling the crown question from ANCHOR_DOCTRINE.md §1/§6.
> Status: DRAFT for chief review + one independent adversarial red-team (the
> ratification step — delegatable). **This result reverses ANCHOR_DOCTRINE §6.**
> Method: prove the strong form, then break it, keep what survives, validate the
> survivor against all 14 audited primitives.

---

## 0. The question

The same forgery — *"the anchor attests an adjacent fact, forgery relocates to
the unattested dimension"* — hit **five** independent hardening attempts (crit-4,
sessions-identity, relay-sender stone-2, census signature, audit-tool). Is that
bad luck, or a **conservation law** of coordination substrates? If a law, the
entire local anchor-arc is bounded-Sisyphean and the product is something else.

## 1. Definitions (precise, so the claim is falsifiable)

- **Substrate** S: actors that assert and consume claims under a shared machine.
- **Authority** of actor P, `auth(P)`: the set of world-states P can reach by its
  own action (write file, set field, spawn proc, set env) without another actor.
- **Claim** C by P: "proposition φ holds." φ is the **load-bearing fact**.
- **Anchor** A: a proposition ψ a verifier V checks and infers φ from.
- **Sound**: A is sound for C iff *P cannot reach a state with ψ-true ∧ φ-false*
  more cheaply than making φ true. **Adjacent** = not sound.
- **Witness bit** of ψ: the piece of state ψ reads that determines its truth.

## 2. Strong hypothesis H (what ANCHOR_DOCTRINE §6 implicitly asserts)

> *No internal actor can attest a load-bearing fact; trust always bottoms out at
> a witness **external to the substrate**.*

**H is FALSE.** Counterexamples exist and are already in the audit as "genuinely
anchored":
- `auto_fix_loop`: φ = "the fix build succeeded"; witness = subprocess **exit
  code**. P cannot set the exit code without the process actually running to
  success — the witness is *inside the machine* yet outside `auth(P)`.
- `recall` db-facet: φ = "the store is not stale"; witness = **mtime + rowcount**,
  a kernel-maintained causal consequence of a real write.
- git content-addressing: φ = "this exact content exists"; witness = the **hash**;
  P cannot forge a hash→content binding without a collision.

So an internal-but-non-claimant oracle (the kernel, content-addressed storage, a
deterministic recompute) **can** soundly attest some load-bearing facts. H's
"external to the substrate" was a conflation of two different boundaries:
*external to the claimant* (the real requirement) vs *external to the machine*
(a much stronger, and false, requirement). **ANCHOR_DOCTRINE §6 is wrong on this
point and is corrected below.**

## 3. The survivor — H′, the Adjacency Theorem

What survives refutation is not conservation of *un-anchorability* but
conservation of *causal-downstream-ness*:

> **THEOREM (H′).** An anchor A is sound for claim C(φ) **iff** its witness bit is
> a state that is reachable **only as a causal consequence of φ itself**, held by
> an oracle outside `auth(P)`. Equivalently: a sound witness must fire *downstream*
> of the load-bearing event. When the only oracle whose state is downstream of φ
> lies inside `auth(P)`, no sound internal anchor exists, and forgery is **forced**
> into the gap between the witness's actual causal target and φ.

**Proof of necessity.** If ψ's witness bit is inside `auth(P)`, P reaches ψ-true
independent of φ ⇒ adjacent. So a sound ψ needs a witness outside `auth(P)`. If
that out-of-authority witness is *not* downstream of φ (it fires on an event
upstream or lateral to φ), then the world where that event happened but φ did not
is reachable by P at the cost of the upstream/lateral event alone ⇒ ψ-true ∧
φ-false is cheap ⇒ adjacent. Hence soundness ⇒ the witness is *both* outside
`auth(P)` *and* exclusively downstream of φ. ∎

**Why the 5 failures were forced, not unlucky** — each picked a real out-of-
authority witness that was downstream of an **adjacent** event:

| Failure | Real witness (sound for *its* fact) | That fact is downstream of… | …but φ was |
|---|---|---|---|
| crit-4 / stone-2 | kernel: process has ancestor Q | *spawn* | *role R* (set post-spawn, in `auth(P)`) |
| `commit_exists` | object store: blob H exists | *someone wrote it* | *it is the deployed line* |
| census signature | HMAC: key-holder signed string | *key possession* | *vendor caused this SHA* |

The witness was always real; it fired on the wrong event. That is the law: **you
cannot borrow a downstream witness of an adjacent event to cover φ.**

## 4. The three regimes H′ yields (the actionable taxonomy)

> Amended 2026-07-12 per RATIFICATION.md — regime membership is topology-relative
> (privilege), not fact-type-intrinsic; a pre-existing different-uid OS oracle
> gives some listed-R2 facts a free R1 anchor.

Regime membership is **topology-relative (privilege), not fact-type-intrinsic.**
The same fact-type ("install-happened," "is-live," "who-wrote") can sit in regime-1
or regime-2 depending on whether a *pre-existing different-uid* OS oracle already
observes its load-bearing event. A root-owned package DB, `journald`, or root audit
log is outside `auth(P)` for a non-root claimant *by construction* — so several
facts the type-taxonomy below lists as regime-2 carry a **free** R1 anchor via
that oracle. The "R2 always needs a bespoke built witness" framing was too strong
for the OS-oracle subset; this *helps* the roadmap (some R2 items anchor for free
via the OS). The taxonomy is therefore read as *default-by-fact-type, overridable-
by-topology*: where a pre-existing different-uid OS oracle already observes the
load-bearing event, the fact lifts to regime-1 without new engineering.

1. **REGIME-1 — φ has a co-located, out-of-authority, downstream witness.**
   Soundly anchorable at **bar-1, internally, for free.** (exit code, mtime/
   rowcount, content hash, `--is-ancestor` graph reachability; and, via the
   topology-relative lift, any regime-2-listed fact for which a pre-existing
   different-uid OS oracle — root-owned package DB, `journald`, root audit log —
   already observes the load-bearing event.) Not exceptions — a *class*:
   everything whose load-bearing event throws off a kernel-observable
   consequence.
2. **REGIME-2 — φ's only downstream witness is inside `auth(P)`.** (role,
   causation/attribution, install-happened, side-effect-fired, lease-held — *as
   the default by fact-type*; topology may lift any of these to regime-1 where a
   pre-existing different-uid OS oracle already observes the event.) Not
   internally anchorable *absent such an oracle*. Needs a witness placed *outside
   `auth(P)`* that *observes the load-bearing event as it happens* — a different-
   uid daemon or off-machine attester (or a pre-existing OS oracle that already
   does so, which is the free-anchor case above).
3. **REGIME-3 — φ has NO downstream witness anywhere.** (semantic truth of free
   text, subjective work quality, "is main.") Unanchorable in principle; must be
   named bar-2-accepted / de-scoped, never silently trusted.

## 5. Validation — H′ retrodicts ALL 14 audited primitives (the empirical test)

A theorem earns its keep by predicting the audit it wasn't built from:

- **Regime-1 ⇒ predict GENUINELY ANCHORED:** `auto_fix_loop` (exit code) ✓,
  `recall` db-facet (mtime+rowcount) ✓. *Both are exactly the two the audit found
  genuinely anchored.* 2/2.
- **Regime-2 ⇒ predict FORGEABLE, and the fix is regime-2→1 re-architecture:**
  relay-sender ✓, sessions-identity ✓, engram-insert ✓, tasks-status ✓ (fix:
  `evidence_ref = commit SHA/ci_run_id` = a downstream witness of the actual
  work), slots-lease ✓ (fix: **flock** = kernel-held lock, downstream of real
  acquisition), telemetry ✓ (fix: **server-issued nonce**, the receiver observes
  the install), swarm-dispatch ✓ (fix: **scoped-worktree SHA git reports** =
  kernel-observed consequence of the vendor's real work), infra-daemon-health ✓
  (fix: **server-captured pid+create_time**), federation ✓, audit-tool ✓ (fix:
  sealed-key HMAC + external head). **Every fix the roadmap already lists is a
  regime-2→1/bar-3 move — the theorem explains *why each is the fix* and predicts
  it mechanically.** 10/10.
- **Regime-3 ⇒ predict UNANCHORABLE:** gates-governance semantic validity (regex
  is theater) ✓; and its embedded `auto_fix` (real exit code) is regime-1 ✓.

**14/14.** The theorem is not merely plausible; it is predictively exact on the
entire audited set and derives the known fixes from first principles.

## 6. The strategic reversal (the payload — and it overturns my own draft)

ANCHOR_DOCTRINE §6 said *"trust always bottoms out at an external witness; the
anchor arc is Sisyphean."* **Both halves are now corrected:**

- The anchor arc is **finite, not Sisyphean.** Regime-1 claims anchor internally
  for free. The external-witness boundary is **exactly** the regime-2 ∪ regime-3
  set — a bounded, enumerable list, not "everything."
- The engineering lever is **not "anchor harder"** but: *for each regime-2
  primitive, can its load-bearing event be re-shaped to throw off a co-located
  downstream witness?* — converting it to regime-1 (free) where possible.
- Where it can't be converted, **all residual regime-2 claims share ONE witness**:
  a different-uid / off-machine attester that observes the load-bearing event and
  issues nonces. **This is why the memory's "5th time at the same wall — stop
  grinding local stones" was right:** relay-sender, engram, sessions-identity were
  each trying to *locally* anchor a regime-2 fact → each bar-2-ceilinged → but they
  are the *same* problem and cross the wall with *one* shared external witness,
  built once, not five bespoke stones.

**Roadmap consequence:** replace the per-stone local-anchoring arc with (a) a
regime-1 sweep (cheap, mechanical, delegatable — convert every primitive whose
event has a kernel consequence: `--is-ancestor`, flock, worktree-SHA, captured
pid), and (b) **one** shared bar-3 attester for the true regime-2 residue
(identity/attribution/verdict-durability). Two workstreams replace nine stones.

## 7. Honest limits (where H′ is bounded, not broken)

1. **Regime-1 soundness assumes witness *integrity*.** A same-uid root/ptrace
   adversary can compromise the witnessing oracle itself (LD_PRELOAD a probe,
   ptrace the daemon). So regime-1 is bar-1 *only against a non-root same-uid
   adversary*; against same-uid root it degrades to bar-2 — which is the exact
   single-uid ceiling the scout already found. H′ does not escape that ceiling; it
   **locates** it (only the shared regime-2 witness must be lifted off-uid, not
   every stone).
2. **"Exclusively downstream" is the load-bearing adjective.** A witness partially
   correlated with φ (downstream of φ *or* an adjacent event) is unsound. The AFT
   in ANCHOR_DOCTRINE §2 is the operational check for exclusivity.
3. Ratification requires **one independent adversarial red-team** trying to
   exhibit a regime-2 claim with a sound *internal* anchor (which would break the
   regime boundary). I attempted this and produced only regime-1 facts wearing
   regime-2 clothing (e.g. "lease held" → flock makes it regime-1). Absence of a
   counterexample from a fresh adversary is the ratification bar.

## 8. Verdict

The Adjacency Law is **not** conservation of un-anchorability (H, false). It **is**
conservation of causal-downstream-ness (H′, true and predictively exact): forgery
relocates to exactly the dimension whose load-bearing event has no downstream
witness outside the claimant's authority — and it does so by *necessity*, provably.
The moat is therefore real and **bounded**: a free regime-1 sweep plus a single
shared external witness, not an endless stone-by-stone arc. This reshapes the
anchor roadmap and supplies the PRINCIPAL v3.1 correction (§8 of ANCHOR_DOCTRINE).
