# Ranking Decision — The Consumer Product Shape (2026-07-24)

> Chief-judgment ranking of the breadth-map pathways (`pathways_runtime.md`,
> `pathways_adrs.md`, `pathways_recent.md`, committed f8697359), per the banked
> next-action: rank on differentiation × felt-need × build-%, cull to 1–2, size
> the bet. Scored cold, against evidence in the maps — not against what the docs
> emphasize. One external red-team pass (cross-vendor, read-mode) noted at bottom.

## Verdict (up front)

The consumer product shape of Nucleus is **NOT** an OS, not a memory layer, not a
fleet dashboard, and not a marketplace. It is:

> **A single command that takes a coding task, has two rival AI vendors draft and
> adversarially attack the plan, has the cheapest capable vendor execute it, and
> hands the user a proof-carrying diff — verified against ground truth, never
> self-reported.**

Working name: **`nucleus build`** (the verb, not a brand). Consumer pitch:
*"AI that proves its work."* The user sees a verdict and a diff; they never read
agent chatter.

Everything else in the substrate is either plumbing for this shape, or parked.

## Why this and not the others — the scoring

Scale 1–5 per axis; product = D × F × B. Felt-need scores lean on the one hard
market fact in the corpus: **the only pathway that ever transacted is the $19
kit that makes an agent do a painful job end-to-end** ("shipped my app for me").
Nobody paid for memory, dashboards, or platform framing.

| Pathway (map ref) | Diff | Felt-need | Build-% | Score | Call |
|---|---|---|---|---|---|
| Verify stack: GROUND + DSoR Verifier (rt#1,#2; rec#1) | 5 | 4 | 2 | 40 | **CORE of the shape** |
| Sub-agent DevOps toolbelt (rt#9) | 3 | 2 | 4 | 24 | PLUMBING — governed sandbox is commoditizing (E2B/Docker-sandbox class); buyer = swarm operators, same thin market as fleet ops. (Red-team scored it 60 and called the omission disqualifying; omission conceded, scoring not — see red-team record.) |
| Cross-vendor plan-review + dispatch (rec#3; delegate) | 4 | 3 | 4 | 48 | **CORE of the shape** |
| Agent-readable kits / $19 Gumroad (adr#10) | 2 | 4 (proven) | 5 | 40 | **KEEP — distribution wedge** |
| Cross-tool session mirror / unified memory (rt#3; adr#2) | 2 | 3 | 3 | 18 | PARK — commoditized; market already said no (0 paid, frozen, ADR-0044 clock running) |
| Skill auto-extraction (rt#5; rec#9) | 3 | 2 | 4 | 24 | PARK — internal accelerant, not a consumer door |
| ADUN auto-memory pipeline (rt#4) | 4 | 2 | 4 | 32 | PLUMBING — invisible inside the shape, not the pitch |
| Capability marketplace / trust tiers (rt#6) | 3 | 1 | 4 | 12 | PARK — two-sided market with zero sides |
| Archive/fine-tune flywheel (rt#7) | 4 | 1 | 3 | 12 | PARK — no consumer; strategic option only |
| god-combos SRE triage (rt#8) | 2 | 2 | 4 | 16 | PARK |
| Flywheel daemon / always-on kernel (rt#10) | 2 | 2 | 4 | 16 | PLUMBING |
| Census v2 (rec#2) | 4 | 1 | 2 | 8 | PARK (already gated behind anchor work) |
| Project spine / multi-tenancy (rec#4) | 2 | 1 | 4 | 8 | PLUMBING |
| Auth/hosted/ChatGPT-catalog (rec#7) | 1 | 2 | 3 | 6 | ENABLER — only matters after the shape earns strangers |
| Export/import sovereignty (rec#8) | 2 | 2 | 3 | 12 | PARK |
| OMBA framework brain (adr#8) | 3 | 2 | 2 | 12 | PARK — stalled DRAFT, no distribution half |
| TB personal-AI productization drafts (adr#3) | 4 | 1 | 1 | 4 | PARK — explicitly not-a-product today |
| GQ D2C / B2B2C (adr#4,#5) | 2 | 2 | 4 | — | SEPARATE BUSINESS — own gates (Day-60 Option B), out of scope here |
| Eidetic tiered SaaS (adr#2) | 2 | 3 | 4 | — | FROZEN by ADR — not re-litigated |

Top two scores are the two halves of one product: **cross-vendor adversarial
coordination** (48) and **ground-truth verification** (40).

**What the kit signal does and does not prove** (red-team-corrected): the $19
kit proves strangers pay for *outcomes an agent delivers end-to-end* — it does
NOT prove demand for verification software as such. Demand for "proof the agent
didn't lie" is a **hypothesis**, and the proof gate below is its test. The kit's
role in this decision is distribution shape (sell concrete jobs, not platform),
nothing more.

## The cull

- **CULLED TO ONE shape**: verified cross-vendor build (`nucleus build`), sold
  kit-style (concrete jobs), not platform-style.
- **Wedge retained**: the agent-readable kit line continues as the distribution
  surface — each kit becomes a *verified* job the shape can run ("ship to App
  Store, with proof"). Kits proved strangers pay for outcomes; verification is
  what makes the outcome trustworthy and the offer non-commodity.
- Everything marked PARK above: no further tokens until the shape earns a G3
  signal (per the gate ladder). PLUMBING items get work only when the shape
  pulls them.

## Dogfood evidence already in hand (why this isn't a fresh guess)

The shape ran end-to-end on our own repo this week, before it had a name:

1. `plan_review_loop` (agy author ↔ devin reviewer) **rejected a plausible plan
   3 rounds running for real architectural bugs** — defects a CI suite could not
   have caught because the code didn't exist yet.
2. Execution dispatched to a free vendor (devin/GLM) produced the fix.
3. The delegate layer's own `changed_paths: []` false-negative was caught **both
   times** by independent ground verification (git diff + pytest on chief's
   shell) — the exact "self-report lies, ground truth doesn't" failure the
   Verifier doctrine predicts.
4. Shipped as 25b882f8 and 375cc0eb, both gated by GROUND.

That is the probe experiment the product-probe memo asked for ("catch lies CI
can't"), passing on live work.

## Compound inventory (existing pieces; ≥5 named per doctrine, no new platform)

1. `nucleus_delegate` `plan_review_loop` — adversarial author/reviewer loop (live, battle-tested this week)
2. `nucleus_delegate` `dispatch` + VendorCLIExecutor — merged, tip of main
3. GROUND tiers 0–2 live in hooks; tiers 3–5 code-complete with 139 tests
4. DSoR Verifier engine — 921+ tests, real caught-lie demo (bbf0e29e)
5. `nucleus init` stranger-wow + release-smoke gates — merged
6. Gumroad fulfillment worker — live, transacting

**The only genuinely new build is packaging**: one CLI verb chaining
plan_review_loop → dispatch → GROUND/Verifier verdict, plus a human-readable
verdict card (what was claimed / what was proven / the diff). No new subsystem
may be started for this shape — that is a hard rule of this decision.

**Timeline, honestly split** (red-team-corrected — the original "days not
weeks" conflated two milestones):

- *Operator-dogfood verb (days)*: the verb calls the engines **directly as
  libraries** — plan_review_loop and dispatch already run live (this week's
  commits prove it), and the Verifier/GROUND tiers 3–5 are code-complete and
  importable. Direct composition does NOT require flipping the substrate-wide
  consumption flags (`NUCLEUS_VERIFY_GATES`, `NUCLEUS_RELAY_ARTIFACT_ANCHOR`) —
  those gate relay/task seams, not library use. So "no flag flips" and "verb
  works" are not in contradiction.
- *Stranger-ready (G2 window, ~3 weeks)*: install matrix, clean-environment
  proof, degraded single-vendor mode for users without agy/devin CLIs
  (BYO-vendor is real friction; the verb must work Claude-only, with the
  adversarial pass simply weaker). This rides the gate ladder's existing G2
  budget — no new schedule invented.

**Stranger entry point** (red-team answer): the consumer surface is the
local-first CLI (`pip install` + `nucleus init`, already stranger-wow-gated) —
hosted auth/OAuth is only needed for a hosted product and stays parked. No
contradiction with parking rec#7.

## Bet sizing & kill criteria

- **Slot in the gate ladder**: this shape *is* the G2 stranger-ready artifact.
  It does not amend the ladder; it names what v1.15's consumer face is.
- **Budget**: packaging + one verified-kit offer ≤ 2 weeks of lane time, built
  cross-vendor (free lanes), chief gating only. No paid-model build spend.
- **Proof gate before any scale spend**: one stranger completes one verified job
  end-to-end and says so (G3 criterion 2 — first external artifact), or one
  additional paid kit sale where the buyer used the verified path.
- **Kill**: if by the existing 2026-08-21 hard-kill checkpoint (ADR-0044 clock)
  the verified-build offer has zero stranger completions AND zero transactions,
  the consumer shape reverts to HOLD-AND-COMPOUND per the ladder's compound
  floor. No new criteria invented; we ride the gates already ratified.

## Red-team record (cross-vendor, read-mode, 2026-07-24)

One hostile pass (agy/gemini-3.1-pro-high, dispatch artifact
`relay_20260723_193906_1ebe3458`) attacked 4 lines and returned OVERALL: FALLS.
Chief adjudication of each:

1. *Kit signal over-read* — **SUSTAINED, amended**: kit proves outcome-buying,
   not verification demand; reframed as hypothesis + proof gate (above).
2. *rt#9 omitted from matrix* — **omission SUSTAINED, scoring REJECTED**: row
   added; reviewer's 60 (Diff 4 × Need 3 × Build 5) rests on scoring a governed
   sandbox as high-differentiation and mid-felt-need; chief scores 3×2×4=24 —
   sandboxed exec is a crowded commodity class and its buyer is the same thin
   fleet-operator market the decision declines to bet on.
3. *"Days not weeks" vs flag-OFF engines* — **SUSTAINED, amended**: timeline
   split into dogfood-verb (days, direct library composition, no flag flips
   needed) vs stranger-ready (G2's existing ~3-week window). The claim that
   this is an "impossible technical contradiction" is rejected — the flags gate
   substrate seams, not library imports — but the original wording earned the
   hit.
4. *Manual verification / no stranger entry / vendor drift* — **PARTIAL**:
   manual-verify point is conceded and is precisely the build (wiring chief's
   manual gate into the verb); entry-point objection rejected (local-first CLI
   is the surface); vendor-drift risk acknowledged — mitigated by the 3
   CLI-drift hardening commits at tip of main and the single-vendor degraded
   mode.

Net: verdict **STANDS as amended**. The two real defects the pass caught
(matrix omission, timeline conflation) are exactly the class of error the
product itself exists to catch — the dogfood loop worked on its own decision
document.

## What this decision does NOT do

- Does not unfreeze Eidetic SaaS, does not touch GQ, does not re-litigate ADR-0044.
- Does not flip any default-OFF substrate flag by itself — flag flips remain
  operator-gated per standing rules.
- Does not rename or rebrand anything public yet — naming is a G2 keystroke.
