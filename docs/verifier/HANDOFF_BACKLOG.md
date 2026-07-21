# Governance-Point Execution Backlog — Fable→agent handoff

> **Purpose.** On 2026-07-12 a Fable pass closed the substrate's trust theory on
> paper (the "holistic impossible problem"). Every remaining piece is *apply the
> theory* — bounded, spec-driven, and **delegatable to Opus/ultracode/devin/GLM**.
> This document is the work-order so future agents execute without re-deriving.
>
> **Required reading before claiming any item** (all in `docs/verifier/`):
> `ADJACENCY_THEOREM.md` (①), `REFEREE_CONFINEMENT.md` (②), `VERIFICATION_GAME.md`
> (③), `JOINT_SUFFICIENCY.md` (④), `ANCHOR_DOCTRINE.md` (the Reasoner spec),
> `VERIFIED_ASSERTION_INTERFACE.md` (VAI, cross-portfolio). Memory:
> `nucleus-anchor-audit-doctrine`, `verified-assertion-interface-thesis`.

## The theory in one paragraph (so an agent can act from this page)

A claim is soundly anchorable **iff** its witness is state reachable *only as a
causal consequence of the claim's load-bearing fact, held outside the claimant's
authority* (①). Three regimes: **R1** = kernel-observable downstream witness →
anchor free & internal; **R2** = witness under claimant control → needs one shared
off-uid attester; **R3** = no witness → unanchorable, must be advisory-only. The
verifier is trustworthy by **confinement** (②): anchor-KIND is doctrine-fixed, the
model only fills slots, classification joins *up* a strength lattice — so soundness
is independent of the model's intelligence. Honesty is the equilibrium (③) **iff**
UNVERIFIABLE = consumption-denial and no R3 claim ever gates. These three cover
every trust-failure (④), plus a temporal axis (re-probe at use) and compositional
application (anchor aggregates too).

## Tier legend & how to claim

- **[DELEG]** — any competent agent (Opus/ultracode/devin/GLM). Just do it.
- **[CHIEF]** — needs chief gate (governing-law change / merge authority).
- **[OP]** — needs operator (off-uid/off-machine infra, or a venture call).
- Flag-gate every behavioral change **default-OFF**; commit a **forge-corpus
  regression test** per the PRINCIPAL-v3 clause; boundary-ledger deltas noted.

## Dependency order (the sequenced arc — don't jump it)

`sessions-identity (A1)` → `relay-sender (A2)` → `engram-insert (A3)` → the rest of
the R1 sweep (A4–A11, parallelizable) → the shared witness (B, unblocks the R2
residue) → Reasoner (C, independent, can start now) → policy enforcement (D) →
PRINCIPAL v3.1 (E, after A–D prove out) → VAI ratification (F, independent).
Red-teams (G) run per-artifact, anytime.

---

## A. The Regime-1 sweep — convert each primitive so its event throws off a witness

Each row: the audit finding → the mandatory fix (from ①/ANCHOR_DOCTRINE §3) →
acceptance test. All **[DELEG]**, flag-gated, forge-corpus required.

| ID | Primitive | Current (adjacent) | Mandatory fix | Acceptance test |
|---|---|---|---|---|
| A1 | **sessions-identity** | every id field client free-string; `NUCLEUS_SESSION_ROLE` spoofable; unregister unguarded | capture registrant pid **server-side**, pin to psutil `create_time`; ownership-gate heartbeat+unregister; drop the env override | forge: a lane cannot register/unregister as a role whose credential it lacks; create_time mismatch rejected |
| A2 | **relay-sender** | FS mode zero sender validation | `from_verified` via `find_session_in_ancestry` role-truth; fail-CLOSED; **depends on A1** (role must be authenticated first — the stone-2 catch) | forge: `register_session(role=main, pid=getppid())` no longer yields `from_verified=main` |
| A3 | **engram-insert** | every field caller-asserted; signature `None`; newest-ts-wins | server-stamp `source_agent`; `HMAC(server_key, canonical)+prev_hash` at `commit_ops`; verify on read; reject future-dated override | forge: forged-author / forged-future-ts engram fails read-verify |
| A4 | **tasks-status** | forged `DONE` releases sub-DAG, no commit | `evidence_ref` = commit SHA / ci_run_id; **re-verify at persist AND at consume** (④ temporal) | forge: `DONE` without an ancestor commit / green ci_run is rejected |
| A5 | **slots-lease** | fence token replay off world-readable json | `flock` + PID + CAS fence (kernel-held = downstream witness of real acquisition) | forge: replayed fence token cannot double-execute |
| A6 | **telemetry-receiver** | public unauth; 500-curl-loop = 500 fake installs | server-issued **single-use nonce** in KV; install counted only on nonce round-trip | forge: curl-loop without nonces adds 0 to the count |
| A7 | **swarm-dispatch / census** | `artifact_ref` operator-INPUT; any string accepted | run vendor in **scoped git worktree**; `artifact_ref` = SHA git reports for the commit the vendor *actually made*; capture vendor `session_id`. Dispatch schema must NOT accept `artifact_ref` as caller input | forge: a dispatch cannot claim a SHA it didn't cause |
| A8 | **infra-daemon-health** | `.pid`+one heartbeat line = "running 95% busy" | server-captured `pid`+`create_time`; liveness from a journal the daemon can't hand-write | forge: `echo $$ > x.pid` no longer passes the 40% delegate-cost gate |
| A9 | **federation-sync** | IPC auth **commented out**; version unbounded → clobber | uncomment+enforce `IPCAuthProvider`; bound + sign engram version | forge: leader with unverified term / MAXINT version rejected |
| A10 | **audit-tool** | unkeyed chain from public genesis → rewritable | `HMAC` sealed key (bar-2) **+ external witness head** (bar-3, via B) | forge: chain rewrite from public genesis fails verify |
| A11 | **recall provenance** (partial) | role-tag caller-controlled, signature slot dead | server-stamp provenance/role-tag; wire the dead signature slot | forge: forged provenance tag rejected. (read-freshness facet already R1-anchored — leave it) |
| A12 | **gates-governance** (partial) | `validate_strategic_plan` = regex `\[BB\d{2,}\]` over agent's own text; `audit_report` hardcodes pass | open the actual registry for `[BB..]`; remove hardcoded "sovereignty verified" | forge: `[BB99]` with no registry entry fails |

## B. The one shared off-uid witness (replaces 9 local stones) — **[OP]** to site, **[DELEG]** to build

The R2 residue (identity/attribution/verdict-durability) cannot be anchored on one
uid (①§7.1 ceiling). Build **one** external attester — a different-uid daemon or
off-machine service — that observes the load-bearing event and issues per-role
single-use nonces the lane round-trips; A2/A3/A6/A10 consume it. **This is the
single highest-leverage build: it crosses the wall the 9 stones each hit.**
Operator input needed only for *where it runs* (different uid vs OCI). Acceptance:
a same-uid `ptrace`/token-theft adversary can no longer forge a role/attribution
that the attester co-signs.

## C. The Reasoner — make ② concrete (independent; can start now) — **[DELEG]**

- **C1** `RuleReasoner._decompose_anchors`: emit the ANCHOR_DOCTRINE §3 **mandatory**
  anchors (`--is-ancestor`, build-identity `json_get`, flock, worktree-SHA…) —
  **not** today's `commit_exists`/bare-200. *This is the prerequisite that makes
  the ②-corollary real (sound on a weak model).* Acceptance: the shipped
  `curated_claims.json` `one-shipped-live` returns **PARTIAL, not CONFIRMED**.
- **C2** Class classifier: assertion → claim-class, with **lattice join-UP** on
  ambiguity and **⊤ = unknown → maximally-strong/manual**. Acceptance: an
  adversarial claim crafted to mis-classify only ever *raises* the anchor bar.
- **C3** Wire `LLMReasoner` to `nucleus_route` (sovereign model); confine to
  **slot-fill only** (never anchor-KIND). Acceptance: prompt-injected claim text
  cannot change the anchor *kind*, only which SHA/URL, which is probe-checked.
- **C4** Freshness re-probe (④ temporal): re-probe critical anchors at
  consumption-time, or attach a freshness-witness. Acceptance: a claim CONFIRMED
  then reverted before use adjudicates REFUTED/UNVERIFIABLE at use.
- **C5** Recursive aggregate-anchoring (④ compositional): anchor derived claims
  (census Σ, "≥N distinct") at the aggregate level (distinctness, window,
  arithmetic). Acceptance: a census total of soundly-CONFIRMED-but-double-counted
  leaves is caught.

## D. Consumption-policy enforcement — make ③ real — **[DELEG]** audit + **[CHIEF]** sign-off

- **D1** Audit **every** gating/counting/routing/granting path; enforce *consume
  only on CONFIRMED* (UNVERIFIABLE = denial). Acceptance: no path consumes an
  un-adjudicated or non-CONFIRMED gating claim; referee-unavailable **fails
  closed**.
- **D2** Grep for **R3-gating leaks** (any place an unanchorable claim gates/counts/
  sells). Known instance: telemetry survival-metric on un-probed installs. Convert
  to advisory-only. Acceptance: no R3 claim is a gating input.
- **D3** Instrument the metric: **fraction of gating claims phrased probeably**
  (and honest-omission rate). This is the real Governance-Point KPI, not lies-caught.

## E. PRINCIPAL v3.1 — transcribe the theory into governing law — **[CHIEF]** + roadmap-redteam

Draft (transcription; the insight is done) then run `roadmap-redteam`:
- Role anchorable **only** by credential/attester; **PID-transitivity = zero role
  assurance** (fixes v3's insufficient transitive-anchoring clause — the stone-2 catch).
- Standing preconditions: the R1/R2/R3 regime test; the AFT as the oracle-registry
  "no oracle = BLOCKING" check; UNVERIFIABLE-as-denial + no-R3-gating.
- Keep the hash convention; preserve v3 at its tag.

## F. VAI cross-portfolio ratification — **[DELEG]** audit, **[OP]** the venture call

- **F1** Audit ComposedFit **"One" render pipeline is confined**: attributes come
  from catalog/`price_history` rows, the model cannot inject a value, the walk-out
  line is suppressed when an attribute is missing. Acceptance: no code path emits a
  displayed attribute not backed by a data row.
- **F2** Add a **price-freshness anchor** (① temporal) and an **aggregate anchor**
  for "% below N-day average" claims (④). Acceptance: a stale `price_history` read
  can't render a live price claim; the average is recomputed, not asserted.
- **F3** Instrument the **shared metric** (fraction-anchored / honest-omission) on
  the B2C surface — the same KPI as D3.
- The venture question (is the VAI a business / how to position) is **[OP]**, out
  of engineering scope.

## G. Red-team ratification jobs (adversarial; run anytime) — **[DELEG]**

Each is "try to break a proof"; not-finding is the ratification bar:
- **G1** (①) exhibit an R2 claim with a *sound internal* anchor → would break the
  regime boundary.
- **G2** (④) exhibit a consumption trust-failure that is *not* an instance of ①/②/③.
- **G3** (VAI) exhibit a *consequential* ComposedFit assertion that is trusted but
  neither anchored nor honestly omitted (an R3 claim that sells).

---

## What is explicitly NOT in this backlog

- **No Fable work remains** — the theory is closed; this whole list is delegatable
  or operator-gated. Do not spawn Fable/chief-tier to *execute* these.
- **Venture/market/positioning** (is any of this a business, resourcing, the quit
  decision) — operator only, deliberately excluded.
- **The bar-3 escape of the same-uid ceiling** beyond item B — a G3+/enterprise
  concern (selling the moat to third parties who don't trust the operator), parked.
