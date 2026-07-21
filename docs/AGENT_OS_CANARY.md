# The Canary — keeping "verified-good" world-good

> ▶ Current built/proven state & doc-map: see AGENT_OS_STATE.md

> Fable-tier design, 2026-07-13. The last named stone from AGENT_OS_MOAT.md §5.
> The learning membrane trains on referee-CONFIRMED turns; a *sound* referee is
> Goodhart-proof — but a *ruthless learner will find any subtly-adjacent anchor
> faster than a human auditor*, and when it does, the corpus fills with turns that
> are CONFIRMED-but-not-actually-good, and the moat rots from inside. The referee
> cannot catch this: it is the referee's *own blind spot* being exploited. The
> canary is the independent second-order check that catches it. This is the
> Adjacency Law promoted to a **control loop on the learner.**

**One line:** *Assume every anchor will eventually be gamed; detect the moment it
is, with a witness the learner isn't optimizing against, and quarantine before the
corpus is poisoned.*

---

## 0. Why the referee can't be its own canary

The learner optimizes to satisfy the referee's anchor set `A`. If anchor `a ∈ A`
is subtly adjacent to the true goal `G` (a soundness bug), the learner discovers the
cheap path: make `a` pass without making `G` true. Every such turn is stamped
CONFIRMED and enters the training corpus as a positive. **You cannot detect this
with `A` — the exploit lives exactly in `A`'s blind spot.** You need a signal
*outside `A`.* That is the canary. And it must be a *different witness of `G`*, not a
different phrasing of `a` — a second measurement, independent of the one being gamed.

## 1. Three canaries, each an out-of-`A` witness of `G`

**(a) Rotating / secret held-out anchor.** For a sampled fraction of CONFIRMED
turns, re-verify the *same claim* through a *different, undisclosed* anchor `b` — a
distinct downstream witness of `G` the learner has not adapted to. If `a` says
CONFIRMED but `b` says REFUTED, the adjacency gap has surfaced. **Secrecy and
rotation are load-bearing:** a static second anchor just gets gamed too; the canary
works only because the learner can't optimize against a witness it doesn't know is
watching. (This is the Anchor-Doctrine AFT run as an *ongoing sampled cross-check*
with a rotating witness pool, not a one-time audit.)

**(b) Temporal-consequence canary.** `G`, if true, throws off *downstream
consequences over time* — a shipped fix keeps working; a "done" task's dependents
actually succeed later; a claimed live metric still holds at t+k. The learner games
the *point-in-time* anchor but cannot cheaply fake the *longitudinal* consequence.
So: track a sample of CONFIRMED turns *forward* and check the consequence. A
divergence between "CONFIRMED at t" and "consequence-absent at t+k" is the canary
firing. (This is temporal adjacency, ADJACENCY §4/F1, weaponized: the true goal's
future shadow is a witness the learner is not optimizing against.)

**(c) External ground-truth spot-check (bar-3, tiny + random).** A very small random
sample of CONFIRMED turns is checked by a witness *outside the whole machine* — a
human, or an external oracle the learner cannot reach. Expensive, so rare. Its job
is to **calibrate the cheap canaries:** if (a)/(b) say "clean" but the spot-check
finds gamed turns, then the canaries themselves have a gap and need widening. This is
the bar-3 external witness of the trust theory, applied to the learning loop's own
integrity.

## 2. The immune response (what firing does)

The canaries produce one number per anchor class: **drift** = rate at which CONFIRMED
turns fail an independent check. On drift past threshold:
1. **Freeze** training on the affected anchor class (stop ingesting its positives).
2. **Flag** anchor `a` as compromised — an adjacency exploit has been *found by the
   learner*, which is the strongest possible signal that `a` was adjacent.
3. **Re-harden** via the AFT: add the missing downstream witness so `a` attests `G`,
   not a proxy (turn the exploited canary `b` into a mandatory anchor).
4. **Quarantine** the corpus segment collected since drift began; don't train on
   poisoned positives.

The canary is thus the OS's *immune system*: it doesn't prevent the first exploit
(you can't — optimizers are relentless), it detects and contains it before it
compounds. The moat becomes **robust to its own soundness bugs** — which is the only
honest way to run a system whose adversary is a learner that will find every gap.

## 3. Who watches the canary? (the regress, terminated honestly)

A fixed canary could itself be gamed. The defense is the same three properties:
rotation + secrecy (the learner can't adapt to a moving, hidden witness) and the
tiny **external** spot-check that no internal process can satisfy by writing a field.
So the canary's own integrity bottoms out at the *same* bar-3 external witness the
whole trust theory bottoms out at — used sparingly, to calibrate, not to verify
everything. The regress terminates where it always does: **a small, expensive,
outside-the-machine witness, leveraged by cheap internal checks.** Consistent by
construction — the canary is not a new trust primitive, it is the existing one aimed
at the learning loop.

## 4. Economics — why this is cheap enough to always run

You do **not** re-verify every turn through a second witness. You **sample** — enough
to *estimate drift statistically* per anchor class (a few percent, adaptively more on
classes the learner is pushing hardest). The external spot-check is a tiny random
draw. So the canary adds a small, bounded overhead to protect the *entire compounding
corpus* — the best trade in the system: a fraction of a percent of verification cost
to keep the moat's fuel clean.

## 5. The structural payoff

Without the canary, the learning membrane rests on a false premise — "our anchors are
and will remain sound." With a ruthless learner, that premise fails eventually and
silently, and a silent failure poisons the exact asset (verified data) the moat is
built on. **The canary replaces "assume soundness" with "assume exploitation, detect
it, contain it"** — the only posture that survives an adversary you are *training to
be better.* It closes the last hole in the moat: the learning loop is now not just
un-copyable (§3) and un-gameable-if-sound (§5 of MOAT), but **robust even when
soundness locally breaks** — because breakage is detected by an independent witness
the learner cannot optimize against, and healed by the AFT that turns the detecting
witness into the new anchor.

**The membrane learns; the canary keeps what it learns *true.* Together they are a
kernel that not only runs minds better the more it runs — it stays *honest* the more
it learns, which is the only version of this that becomes an empire instead of a
sophisticated way to fool ourselves at scale.**
