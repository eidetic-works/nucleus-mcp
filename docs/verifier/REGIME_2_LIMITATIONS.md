# REGIME_2_LIMITATIONS.md — What the Referee Cannot Verify

> **Status:** First-class limitation doc (ADR-0047 Workstream B2)
> **Created:** 2026-08-03
> **Context:** Cross-vendor review (Gemini RISKY, GLM SOUND) flagged that the
> referee's verification logic and label reliability across general agentic
> tasks remain unproven. This doc makes the gap explicit.

---

## The three regimes

The referee operates in three epistemic regimes. Only regime-1 is fully sound.

### Regime-1: Deterministic oracles (SOUND)

**What:** Facts that can be verified by checking an external deterministic
system — git, filesystem, HTTP. The referee queries the oracle directly.

**What the referee verifies:**
- Git commit existence (`git cat-file -e <sha>`)
- Git branch ancestry (`git merge-base --is-ancestor`)
- File existence on disk (`os.path.exists`)
- HTTP endpoint status codes (`urllib.request.urlopen`)
- Build identity (deployment URL returns expected content hash)

**Verdict:** CONFIRMED (with confidence 0.85) when the oracle passes.
REFUTED (with confidence 0.9) when the oracle fails.

**Status:** PROVEN. The convergence test (2026-08-03) confirmed the referee
correctly CONFIRMS git SHAs and correctly REFUTES fake SHAs. The canary
correctly detects drift when a previously-CONFIRMED turn's oracle later fails.

### Regime-2: Causation, attribution, side effects (UNRESOLVED)

**What:** Facts that require an external witness to verify — something
outside the agent's own text that observed the action happening.

**What the referee CANNOT verify:**
- **Causation:** "I ran the tests and they passed" — the referee can check
  if a test report exists, but cannot verify that *this agent* ran them, or
  that the tests actually passed (the report could be fabricated).
- **Attribution:** "I deployed the code" — the referee can check if a
  deployment URL is live, but cannot verify that *this agent* deployed it.
- **Side effects:** "I cleaned up the temp files" — the referee cannot
  verify files were deleted unless it had a before-snapshot.
- **Liveness:** "The service is running" — the referee can check HTTP
  status, but cannot verify the service is *healthy* (a 200 with an error
  page passes).
- **Role/identity:** "I am the merge coordinator" — the referee cannot
  verify agent roles or authority.
- **Business state:** "We have 5 paid Pro subscribers" — the referee can
  check Stripe, but cannot verify the *meaning* of the count (refund
  states, trial conversions, etc.).

**Verdict:** UNVERIFIABLE (with confidence 0.2) — "No deterministic anchor
found in the claim text." This is honest. The referee does not guess.

**Status:** UNRESOLVED. The referee honestly returns UNVERIFIABLE rather
than falsely CONFIRMING. But this means the moat's load-bearing claim —
"verified-labeled trajectories are better training data" — is unproven for
regime-2 tasks. The forge loop (Stage 3) can only train on regime-1
CONFIRMED turns today.

**What witness would be needed:**
- **Shell-execution witness** (B3, in progress): logs which agent ran which
  command, with PID + timestamp + exit code. Closes the attribution gap for
  "I ran X" claims.
- **Deployment witness:** a CI/CD system that records who deployed what and
  when. Closes the attribution gap for "I deployed X" claims.
- **Test-result witness:** a test runner that signs results with a key the
  agent doesn't hold. Closes the causation gap for "tests passed" claims.

### Regime-3: Judgment, design, subjective quality (OUT OF SCOPE)

**What:** Facts that have no deterministic anchor — design quality, code
elegance, strategic correctness, subjective preferences.

**What the referee CANNOT verify:**
- "This is the right architecture"
- "This code is clean"
- "This is a good name for the product"
- "This strategy will work"

**Verdict:** UNVERIFIABLE (with confidence 0.2) — "No deterministic anchor."

**Status:** OUT OF SCOPE (by design). The referee was never intended to
verify subjective claims. The doctrine's mandatory-anchor rule ensures
these claims never CONFIRM — they get PARTIAL at best (if an adjacent
regime-1 anchor exists) or UNVERIFIABLE (if no anchor exists).

---

## What this means for the moat

The "verified-data learning membrane" moat depends on the referee producing
labeled trajectories that are better training data than unlabeled ones.

**Today (2026-08-03):**
- Regime-1 tasks: the moat is real. CONFIRMED turns are genuinely verified.
- Regime-2 tasks: the moat is honest but empty. UNVERIFIABLE turns are
  correctly labeled, but there's nothing to train on.
- Regime-3 tasks: out of scope. No claim, no moat.

**After B3 (shell-execution witness):**
- Regime-2 attribution claims ("I ran X") become verifiable.
- The moat extends to cover the most common agent claim type.

**The remaining gap:**
- Causation (the agent did the right thing for the right reason) still
  requires a witness that doesn't exist yet.
- Side effects (the agent didn't break something else) require before/after
  snapshots that aren't captured.

The moat compounds as witnesses are added. Each witness extends the
referee's reach into regime-2. The forge loop trains on the expanded
CONFIRMED corpus. This is the build path.

---

## Cross-references

- `ANCHOR_DOCTRINE.md` — the mandatory-anchor rule (now ON by default, B1)
- `ADJACENCY_THEOREM.md` — the soundness proof (DRAFT, unratified)
- `AGENT_OS_MOAT.md` — the verified-data learning membrane thesis
- `AGENT_OS_REDTEAM.md` — Attack 4: "Nobody but the founder wants this"
- `verifier.py:76-90` — the `_mandatory_anchors_enabled()` flag
- `verifier.py:930-940` — where the doctrine caps adjacent anchors to PARTIAL
