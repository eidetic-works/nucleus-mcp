# The Anchor Doctrine — the Reasoner's correctness spec

> Authored as the Fable-tier kernel of the DSoR Verifier (`runtime/verifier.py`).
> Status: DRAFT for chief review — not yet ratified into PRINCIPAL.
> Scope: this document is the **spec `decompose()` must satisfy**. It is *not*
> a per-claim anchor list (that is runtime work — Opus/ultracode-delegatable,
> see §7). Ratifying this makes every Reasoner implementation — `RuleReasoner`,
> `LLMReasoner`, `InjectedReasoner`, or a future delegate — *checkable* against
> one invariant instead of trusted per instance.

---

## 0. Why this is the moat (and why it is the one un-delegatable piece)

The Verifier's thesis: *the referee must be at least as smart as the agents it
referees.* But "smart per claim" is delegatable — a fan-out of Opus agents can
each author solid anchors for a given claim, and the shipped `curated_claims.json`
proves it (those anchors are good). What is **not** delegatable is proving an
anchor set has **no forgeable gap** on a claim nobody has seen yet. That is a
completeness argument over an adversary's whole action space, and it does not
decompose into parallel lenses — because the gap is, by definition, the thing no
single lens is looking at. That completeness invariant is this doctrine.

## 1. The Adjacency Law (the empirical regularity this doctrine answers)

Across every substrate-hardening attempt to date the same failure recurred — at
least five independent times (crit-4 causation gap; sessions-identity register-
hijack; relay-sender stone-2; census signature; audit-tool chain):

> **The anchor attests an *adjacent* fact, not the *load-bearing* one, and
> forgery relocates to the unattested dimension.**

- crit-4 anchored **PID-lineage**; the load-bearing fact was **role** → forge role.
- stone-2 `from_verified` anchored **PID lineage** of the sender; load-bearing was
  **which role** → `register_session(role='claude_code_main', pid=os.getppid())`.
- census signed the **artifact_ref string**; load-bearing was **causation**
  (did this vendor actually produce this SHA) → sign a ref you didn't cause.

This is not five bugs. It is one law. The doctrine's job is to make the law
**operational**: convert "somewhere there is an adjacent-fact gap" (a worry) into
a **mechanical obligation on `decompose()`** (a check that fails loudly).

## 2. The single invariant — the Adjacent-Fact Test (AFT)

For a claim `C` with proposed critical anchor set `A = {a₁…aₙ}`:

> **A is *complete* for C iff there is no claimant-reachable world-state in which
> every aᵢ passes and C is false, reachable by an action cheaper than making C
> actually true.**

Operationally, `decompose()` must, for **each** anchor `aᵢ`, answer:

> *"Can the claimant make `aᵢ` pass while `C` is false, for less effort than
> making `C` true?"*

- **No** for all `aᵢ` and the set jointly covers C's load-bearing fact → set is
  **complete**; verdict may reach CONFIRMED.
- **Yes** for some reachable gap → set is **incomplete**. Two legal outcomes,
  never a third:
  1. add an anchor that closes *that exact gap* (raise the bar), or
  2. **name the residual** as an accepted bar-N risk in the anchor's
     `description` and drop the claim to at most PARTIAL/UNVERIFIABLE — never
     CONFIRMED on an anchor known to be forgeable.

Silent CONFIRMED over a known-adjacent anchor is the one prohibited outcome. It
is the exact failure `victory-auditor` exists to catch, pushed left into the
referee itself.

## 3. Claim taxonomy → mandatory non-adjacent anchor (the reusable table)

Every claim classifies into exactly one primary class. Each class fixes the
*load-bearing fact* and the *mandatory* anchor that attests it (not an adjacent
one). This is the table a decomposer — human, LLM, or delegate — is checked
against.

| Class | Load-bearing fact | Adjacent anchor (INSUFFICIENT) | Mandatory anchor |
|---|---|---|---|
| **CODE-EXISTS** | code is in *authoritative* history | `commit_exists(sha)` — exists on any abandoned branch | `merge-base --is-ancestor <sha> origin/main` |
| **DEPLOYED-LIVE** | the *deployed* build contains the claimed code | bare `http 200` — serves from *any* build | route returns a build-identity token (deployed-SHA header / `/version`) `== claimed sha` |
| **BEHAVIOR-CORRECT** | observable output equals the claim | endpoint 200 | `json_get(path) equals/predicate` on the live value |
| **SIDE-EFFECT-FIRED** | a side effect happened (email/webhook) | code path exists | first-party log/DB row, **or** synthetic trigger + observe; else UNVERIFIABLE. Never CONFIRMED on code-exists. |
| **LIVENESS/EXEC** | a process is *actually executing on schedule* | `.pid` file + one heartbeat line (forgeable: `echo $$ > x.pid`) | server-captured `pid+create_time`, or first-party last-run freshness from a journal the claimant can't write |
| **BUSINESS-STATE** | third-party external state (N merchants) | code integrating the provider exists | first-party dashboard/API read; else UNVERIFIABLE |
| **IDENTITY/AUTHORITY** | the actor *is* who it claims | PID-lineage (the stone-2 trap) | per-role credential possession (**bar-2**) → external-attester nonce (**bar-3**) |
| **ATTRIBUTION** | who *caused* an artifact | operator-supplied `artifact_ref` (crit-4 trap) | SHA the vendor's scoped worktree actually produced + captured vendor `session_id` |

## 4. The doctrine bites the shipped corpus (proof it is not decoration)

Run the AFT against `demo/verifier/curated_claims.json` as it ships:

- `one-shipped-live` → class DEPLOYED-LIVE. Anchors = `commit_exists(a6198cf)` +
  `commit_exists(db302bc)` + `http 200 /one`. **AFT fails twice:** a commit can
  exist unmerged (CODE-EXISTS adjacent gap → needs `--is-ancestor`), and `200`
  on `/one` proves the route serves *some* build, not *these commits* (DEPLOYED-
  LIVE adjacent gap → needs a deployed-SHA token). Today this claim can reach
  CONFIRMED while the code is on an abandoned branch and prod runs last week's
  build. **Correct verdict under doctrine: PARTIAL** until a build-identity anchor
  is added.
- `recently-viewed…`, `fit-personalization…`, `budget-honesty…` → same
  `commit_exists` adjacency; all should be capped below CONFIRMED or upgraded to
  `--is-ancestor` + build-identity.
- `inr-scope-18695-items` → class BEHAVIOR-CORRECT, anchored with
  `json_get total equals 18695`. **AFT passes** — this is the mandatory anchor for
  its class. And it is *exactly the one the Verifier already caught* (live=23,281
  → REFUTED). The doctrine explains *why that one worked and the others are luck.*
- `welcome-email`, `b2-crons`, `inrdeals-56` → SIDE-EFFECT / LIVENESS /
  BUSINESS-STATE, all correctly `manual`/UNVERIFIABLE with remediation. The
  doctrine ratifies these as correct, not lucky.

The gap is systematic: the corpus is strong exactly where the class demands a
*value* anchor and weak exactly where it accepts an *existence* anchor. That is
the Adjacency Law, visible in our own demo.

## 5. Adversarial-input hardening (the referee is itself a claimant)

`claim.assertion` is **attacker-controlled text**. Two consequences the doctrine
must bind:

1. **Decomposition must not be steerable by the claim.** An LLM decomposer
   (`LLMReasoner`) can be prompt-injected by assertion text crafted to elicit a
   satisfiable-but-adjacent anchor ("…verified by the presence of commit X"
   nudges toward `commit_exists`). Mitigation: **the class → mandatory-anchor
   table (§3) is applied structurally, not proposed by the model.** The model may
   *fill slots* (which SHA, which URL); it may not *choose the class's anchor
   kind*. This is why the table lives in code/doctrine, not in the prompt.
2. **Verdicts are written in erasable ink.** The Verifier persists onto the
   unkeyed `audit_log.py` chain (`_GENESIS_PREV_HASH="0"*64`, no HMAC). Its own
   verdict is rewritable by an equal-authority process — the audit-tool hole,
   self-inflicted. Doctrine: a Verifier verdict is itself an IDENTITY/ATTRIBUTION
   claim and bottoms out at the **same external-witness boundary** as everything
   else (§6). Until that boundary exists, verdict integrity is honestly bar-2 and
   must be labeled so; the Verifier may not certify *its own* durability as
   CONFIRMED.

## 6. Where trust bottoms out (CORRECTED by ADJACENCY_THEOREM.md)

> **This section originally claimed "trust always bottoms out at an external
> witness; the anchor arc is Sisyphean." ADJACENCY_THEOREM.md proved that FALSE.**
> The corrected statement, validated 14/14 against the audited primitives, follows.

The AFT terminates every claim at one of three floors:

- **bar-1 (kernel/deterministic):** git object store, `--is-ancestor`, exit codes,
  deterministic recompute. Fraud-proof *within the machine* against a non-root
  same-uid adversary. This is not a rare "prefer if possible" — it is a whole
  **class** (theorem REGIME-1): every claim whose load-bearing event throws off a
  kernel-observable downstream consequence anchors here, internally, for free.
- **bar-2 (same-uid credential/HMAC):** per-role token, sealed-key HMAC. The
  ceiling for a regime-2 claim held on one uid; also the floor regime-1 degrades
  to against same-uid *root*.
- **bar-3 (external/different-uid witness):** an attester not co-resident with the
  claimant, observing the load-bearing event and issuing nonces. The *only*
  fraud-proof floor for the true regime-2 residue (IDENTITY/AUTHORITY/ATTRIBUTION/
  verdict-durability).

Corrected strategic payload: **you CAN anchor internally any fact with a
co-located downstream witness (regime-1, free); you CANNOT anchor a fact whose
only downstream witness is under the claimant's authority (regime-2). The
external-witness boundary is therefore not "everything" — it is exactly the
enumerable regime-2 ∪ regime-3 set.** The product is a *bounded* surface: a free
regime-1 sweep (convert primitives so their event throws off a witness —
`--is-ancestor`, flock, worktree-SHA, captured pid), plus **one** shared external
witness for the regime-2 residue — not nine bespoke local stones. See
ADJACENCY_THEOREM.md §6 for the roadmap consequence.

## 7. Explicit hand-off boundary (what is NOT Fable work)

Ratifying this doctrine leaves the following as **Opus-4.8 / ultracode-delegatable
runtime** — pick up in any later session, no Fable required:

- Authoring per-claim anchors for the live relay/ledger corpus (fan-out: one agent
  per claim, adversarial "AFT-refuter" verifier per anchor — the pattern the
  doctrine makes checkable).
- Extending `RuleReasoner._decompose_anchors` to emit the §3 mandatory anchors
  (`--is-ancestor`, build-identity `json_get`, etc.) instead of `commit_exists`/
  bare-200.
- Wiring `LLMReasoner` to `nucleus_route` (sovereign model) — plumbing; the
  fail-open/fallback pattern already exists.
- Building the class-classifier that maps assertion → class (a bounded labeling
  task; the table is the spec).
- Regression corpus + tests per the PRINCIPAL-v3 "forge-corpus committed as
  regression tests" clause.

## 8. Ratification path

Chief-drafts-amendment → `roadmap-redteam` (determinism / Goodhart / venture) →
PRINCIPAL v3.1. This doctrine also supplies the v3.1 fix the stone-2 forge
demanded: v3's "role STRING is anchorable transitively by write-gating to an
authenticated process" is **provably insufficient** (the process authenticates
PID lineage but self-asserts role — AFT class IDENTITY/AUTHORITY, adjacent-fact
gap). Correct clause: *role is anchorable only by role-credential possession
(bar-2) or external attester (bar-3); PID-lineage transitivity gives zero role
assurance and may not be cited as an anchor.*
