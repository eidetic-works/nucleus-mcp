# Recent pathways — what's actually been built (last ~60 days, git-verified)

Scope: read-only survey of `origin/main` (HEAD `c2cf8c5c`, 2026-07-11), local branch `feat/dsor-verifier`
(current, HEAD `a310db08`), and ~90 feature/fix/docs branches (local + `origin/*`). Method: `git log`,
`git diff --stat`, `git log --since="60 days ago" --name-only` file-churn count. No checkouts, no writes
outside this file. Not ranked — see note at bottom for the single most-active thrust.

Each entry: **name** | what it is | evidence | maturity | differentiation | who'd feel it.

---

## 1. DSoR Verifier / anchor arc — "Governance Point" ground-truth auditor
**What it is:** A structural response to the finding that the whole Nucleus substrate (relay, sessions,
engrams, slots, telemetry, federation, task-DAG) trusts self-reported claims with no independent check.
The Verifier is a ground-truth auditor; the "anchor" work (stones A1–A12 + stone-1.5) HMAC-signs or
kernel-binds specific write paths (session envelopes, relay sender, engram inserts, slots lease, telemetry
install-nonce, daemon-health witness, federation IPC/Raft term, recall provenance, governance plan
validation, role-credential possession) so those claims can't be forged. All flag-gated, default OFF.

**Evidence:** current branch `feat/dsor-verifier` (16 commits since main, e.g. `bbf0e29e` "Verifier — the
missing ground-truth auditor", `cebd2741` wiring into task-DAG release seam, `725dc78a` C1+C2
mandatory-anchor doctrine); plus 9 sibling branches off the same lineage that isolate individual stones:
`feat/anchor-relay-sender`, `feat/anchor-sessions-identity`, `feat/anchor-slots-lease`,
`feat/anchor-telemetry-nonce`, `a12-governance-anchor`, `dsor-a8-daemon-health-anchor`,
`dsor-verifier-a3-work`, `feat/dsor-verifier-a9-fedsync`, `feat/dsor-verifier-a11-recall-provenance`,
`stone-1.5-role-credential`. `mcp-server-nucleus/tests/test_verifier.py` (1130 lines) is the largest new
test file in the whole survey. Docs: `AUDIT_FINDINGS.md` (10-seam file:line map), `RATIFICATION.md`
(independent red-team pass), `docs/adr/` referencing G1/G2/G3 amendments.
**Maturity:** active — this is the branch checked out right now, most recent commit in the whole repo.
**Differentiation:** novel. This is not commodity auth/telemetry hardening — it's a coherent trust-theory
applied uniformly across every substrate write-path (relay/sessions/engrams/slots/telemetry/federation/
governance), with an explicit adversarial ratification pass. Directly answers "how do you know an agent
fleet isn't lying to itself."
**Who'd feel it:** anyone running heterogeneous/multi-agent fleets where agents self-report success —
i.e. the core Nucleus buyer. Also feeds the census/crit-4 work below (blocked on this).

---

## 2. Census v2 / v2.1 — causally-attributed, HMAC-signed cross-vendor production metric
**What it is:** A "census" self-test that measures cross-vendor agent production in a way that resists
gaming — v2 adds causal attribution + an anti-gaming self-test; v2.1 adds HMAC-signed capture so the
cross-vendor causal edge can't be forged, plus a non-triviality enforcement gate.
**Evidence:** `feat/census-v2` (1 commit, `22910e18`, +1732 lines incl. `census_v2.py` 1063 lines,
`test_census_selftest.py` 348 lines) and `feat/census-v2.1` (+1 commit `4afed3fc`, touches
`runtime/auth/signature_guard.py`, +712-line expanded self-test). Referenced explicitly in the Verifier's
`AUDIT_FINDINGS.md`: "no census aggregation exists in this repo... A7's census lives in feat/census-v2.1,
not src" — i.e. it has NOT been merged/wired into the runtime.
**Maturity:** stalled at branch tip, unmerged into main; explicitly flagged as depending on the anchor
work above ("crit-4 sits on forgeable relay+engram foundations — anchor those first" per memory index).
**Differentiation:** novel — a self-auditing, gaming-resistant productivity metric for cross-vendor agent
fleets is not something off-the-shelf. But it's currently inert (not called from anywhere in `src`).
**Who'd feel it:** whoever needs to prove (to an investor, to themselves) that a multi-agent fleet is
actually producing, not just active.

---

## 3. Cross-vendor dispatch — devin(GLM)/agy(Gemini) as first-class execution lanes
**What it is:** Makes non-Claude CLI agents (Devin/GLM, Antigravity/Gemini) drivable through the same
Nucleus dispatch surface as Claude agents — `nucleus_delegate` MCP tool, a `VendorCLIExecutor`, capture of
artifact_refs, swarm/routing hooks. Multiple hardening passes for real-world CLI drift (agy 1.1.1 prompt
flag changes, devin stdin panics, secret-hygiene redaction on vendor stdout).
**Evidence:** merged to main across ~10 commits (`54110340` initial dispatch-and-capture behind
`NUCLEUS_CROSS_VENDOR` default OFF, `f1499f14`/`881d45ed` `nucleus_delegate` facade, `ab044ef1`
`nucleus onboard`, `1304d5d1`/`412beb6c`/`11d938ff`/`c2cf8c5c` — the last 3 commits on origin/main are all
cross-vendor hardening). `feat/cross-vendor-dispatch` (475-line `vendor_dispatch.py`) fully merged.
**Maturity:** merged and actively iterated — this is literally the tip of `origin/main`.
**Differentiation:** somewhat novel — the pattern (one dispatch endpoint, vendor-agnostic) is architecturally
distinctive (matches the "workers are interchangeable" doctrine), though "call another vendor's CLI" per se
is commodity; the value is the uniform dispatch/capture/audit wrapper.
**Who'd feel it:** cost-sensitive operators who want to route work to free/cheap vendor CLIs without losing
observability — directly matches the existing "prefer cross-vendor build over Opus" cost doctrine.

---

## 4. Project Spine (XY-1..5) — multi-project routing through one substrate
**What it is:** A staged, flag-gated ("NUCLEUS_PROJECT_SPINE", default OFF) mechanism so one Nucleus
substrate instance can serve multiple projects without cross-contaminating relay/memory: XY-1 project
detection + D1 precedence, XY-2 relay project-tag + read filter, XY-3 ContextVar wiring at entrypoints,
XY-4 brain-path-aware hooks, XY-5 relay-bridge half-mirror hard-error.
**Evidence:** ADR `docs/adr/0042-project-spine.md` (merged, `b5bc0407`/`f9196525`); 5 sequential branches
`feat/xy1-project-spine` through `feat/xy5-bridge`, each with dedicated test files (`test_project_spine.py`
301 lines, `test_project_spine_relay.py` 495+99 lines, `test_project_spine_lifecycle.py` 206 lines) — all
merged to main per the origin/main log (`4536335b`, `ee5bb873`, `5c10bef7`, `8064e9d2`, `bc1b8972`).
**Maturity:** merged, flag-gated OFF by default (i.e. shipped-but-dormant — matches "shipped ≠ live" pattern).
**Differentiation:** commodity concept (multi-tenancy) but the specific mechanism (D1 precedence inversion,
no-sentinel rule for project-less writers, ContextVar-scoped ambient project id) is a careful, tested
implementation, not a stub.
**Who'd feel it:** operator running Nucleus across more than one product (GQ + Nucleus itself) — directly
addresses the cross-project bleed problem visible in this session's own memory index (GQ vs nucleus lanes).

---

## 5. Coordination-First campaign (ADR-0043) — core/periphery boundary + fast test gate
**What it is:** A structural engineering push: classify every module as core vs periphery with an enforced
boundary ratchet (31-edge ledger), and carve out a "core fast-gate" so the merge-gate test suite runs in
27s (556 tests) instead of the full slow suite — addresses the "merge gates need quiet machine" pain point.
**Evidence:** ADR `docs/adr/0043-coordination-first.md` (merged `c8fa03ad`); `feat/core-fast-gate`
(`f6d7033d`, new `core_gate_files.txt` manifest + `test_core_gate_manifest.py`, merged as `b39961ca`);
`feat/boundary-ratchet` (`e7c0b751`/`e4852891`, `test_boundary_ratchet.py` 116 lines, merged as
`45c00740`); companion work `feat/release-smoke` (smoke gate + wheel-completeness + python floor + staged
yank, merged `367a69fd`) and `feat/stranger-wow` (CLI init demonstrates value on first run, merged
`b70d2812`).
**Maturity:** merged, active — this is the W1/W2 execution of a ratified priority campaign.
**Differentiation:** commodity practice (fast CI, module boundaries) executed with above-average rigor
(explicit ledger, manifest-pinned gate membership) — infra hygiene, not a product differentiator per se,
but a direct unblock for shipping velocity.
**Who'd feel it:** the team itself (faster iteration loop); indirectly, anyone depending on release quality.

---

## 6. Memory Move 2 — Source-of-Record (SoR) migration for engrams/recall
**What it is:** A 7-batch, flag-gated migration moving `remember()`/`recall()`/`write_engram`/`query_engrams`
/VectorStore off ad-hoc storage onto a single `MemoryFacade` SoR, dual-writing during transition, with a
resumable legacy→SoR backfill script for the final cutover.
**Evidence:** fully merged sequence on origin/main: `51086e8b`(batch1 facade skeleton) → `1d2e3e40`(batch2
remember dual-write) → `eba70f25`(batch3 write_engram dual-write) → `b70baf30`(batch4 recall reads SoR +
"recall-beats-grep" acceptance test) → `7a3e2ad0`(batch5 VectorStore→read-model) → `f36a753a`(batch7
query_engrams SoR union). `feat/backfill-staging` (batch-6, `8ed69ecf`, 797-line `backfill_sor.py`,
dry-run default / operator-gated real mode, merged `3f75f209`) is the last piece before flag flip.
**Maturity:** merged through batch 7, flag `NUCLEUS_MEMORY_SOR` still default-off — infrastructure complete,
cutover (flipping the flag) still pending per the "untangle-progress" memory entry ("NEXT=batch 6
backfill+daemon = OPERATOR-GATED").
**Differentiation:** commodity pattern (strangler-fig migration to single source of truth) but directly
targets a load-bearing correctness gap (memory writes/reads previously not unified).
**Who'd feel it:** anyone relying on recall/memory consistency across surfaces (relay, MCP tools, CLI).

---

## 7. Auth/tenant surface — Clerk OAuth + ChatGPT App Catalog + per-user tenant routing
**What it is:** A cluster of auth work making Nucleus consumable as a hosted multi-tenant service: Clerk
hosted-auth integration, OAuth 2.1 server + tool annotations + domain verification for ChatGPT App Catalog
listing, deterministic per-user tenant_id routing from email, plus hardening fixes (well-known/OAuth
endpoints exempted from tenant middleware, authorize endpoint reading POST form body, tenant-resolution
race-condition fix).
**Evidence:** unmerged branches `feat/clerk-oauth-integration` (`9eb004cd`, +1781 lines),
`feat/chatgpt-app-catalog-readiness` (`e2f7dd03`, +2257 lines incl. landing page wiring),
`feat/oauth-per-user-tenant-routing` (`f9575340`), plus already-isolated fix branches
`fix/well-known-public-auth-bypass` (`3c197a84`) and `fix/oauth-authorize-post-form-body` (`eac74716`).
**Maturity:** active but not yet merged to main — several fix branches exist precisely because the
integration surfaced real bugs (auth bypass gaps, form-body parsing) during dogfooding.
**Differentiation:** commodity (OAuth/multi-tenant auth is standard SaaS plumbing) but it is the concrete
enabler for a hosted product / ChatGPT-distribution channel, which is a real distribution differentiator
even if the auth code itself isn't novel.
**Who'd feel it:** any end user onboarding via ChatGPT's App Catalog or a hosted (non-self-run) Nucleus.

---

## 8. Brain data portability — export/import CLI + local↔hosted engram sync
**What it is:** Two related but distinct capabilities: (a) `nucleus export`/`import` — full brain-data
portability positioned explicitly as a "sovereignty guarantee" (no lock-in); (b) a sync mechanism
(`sync.py`) to keep local and hosted engram stores consistent, later wired into the relay bridge daemon for
background sync.
**Evidence:** `feat/export-import-cli` (`5d8db2bb`, 603-line `export_import.py` + 487-line test, +1147
lines, single commit, unmerged); `feat/engram-sync` (`00bc2000`, 344-line `sync.py` + 495-line test, +1298
lines, unmerged); `feat/bridge-engram-sync` (`2ef29e6d`, wires sync into relay bridge daemon, +309 lines,
unmerged, builds on top of engram-sync).
**Maturity:** stalled at branch tip — none of the three are merged to main; they layer on each other
(bridge depends on sync) suggesting a planned-but-paused sequence.
**Differentiation:** the "sovereignty guarantee" framing (explicit anti-lock-in) is a differentiated
positioning choice, though export/import and sync-replication mechanics themselves are commodity.
**Who'd feel it:** operators wary of vendor lock-in for their agent memory; anyone running local+hosted
Nucleus side by side.

---

## 9. Skill-macro autonomy — allowlist-gated autonomous skill install/loop
**What it is:** Lets Nucleus autonomously install/invoke skills against an operator-defined allowlist, with
an explicit "paste-friction kill-gate" (ties to the "reduce the operator's manual-paste count" acceptance test
elsewhere in the memory index) and a companion "intelligent nudge" pattern-detection/self-rescue mechanism.
**Evidence:** merged `49ab54fa` ("feat(skills): allowlist-gated autonomous macro loop (seed) #624");
`feat/skill-macro-seed` branch shows the seed already on main plus a cc-peer-review follow-up
(`e0b17a3a` "wire kill-gate, tighten allowlist match") and nucleus-mcp submodule bump for "intelligent
nudge" (`3f917729`, v1.14.2). `feat/skill-macro-autoloop` branch exists in the branch list but resolves to
no diff against main (name only, content already merged/superseded).
**Maturity:** merged (seed), with an "autoloop" follow-on branch that appears to be empty/stale — likely
superseded rather than actively developed further.
**Differentiation:** novel-ish — autonomous skill invocation with a hard paste-friction gate is a specific,
opinionated answer to "how much autonomy is safe," directly wired to this operator's own acceptance test.
**Who'd feel it:** the operator directly (fewer manual pastes); any Nucleus user who wants supervised
autonomy rather than all-or-nothing.

---

## 10. Global watcher hoist + durable per-role daemons
**What it is:** Moves the SessionStart relay-arm hook to a global hoist (not per-repo) and adds durable,
per-role launchd watcher daemons so relay-arming survives across sessions/restarts without silent daemon
death (addresses the "launchd unload not durable" / "pair daemon silent death" failure modes named in the
operator's memory index).
**Evidence:** `feat/global-hoist-and-durable-watchers` (2 commits: `8f669f3d` staged proposal, `2f9e6e52`
fix making SessionStart merge additive not a wholesale replace; +712 lines incl. new
`ops/launchd/relay_watcher_daemon.sh` 119 lines and an uninstall script), unmerged.
**Maturity:** active/staged but not merged — explicitly framed in its own commit message as a "staged
proposal," consistent with operator-gated daemon changes requiring per-service confirmation.
**Differentiation:** commodity (launchd daemon supervision) but targets a specific, previously-diagnosed
operational failure mode in this exact substrate.
**Who'd feel it:** the operator's own machine reliability — infra maintenance, not user-facing.

---

## Branches surveyed but not written up as distinct pathways
- `resurrection/00-survey`, `02-rabbithole`, `02-phase2-batch3`, `03-e2e`, `04-leaks`, `04-scan-leaks`,
  `salvage/known-debt-rebase` — all **merged** to main already (test-coverage resurrection: 0→6700+ tests,
  CVE remediation 40→0, SBOM/license audit, E2E hardening). Historical, not a forward-looking pathway.
- `docs/plan-postmortem`, `docs/status-bootstrap-agents-coherence`, `day60/kill-path-staging`,
  `chore/coordination-surface-closeout` — documentation/process housekeeping, not product surface.
- `refactor/mcp-facade-dedup` (unmerged, 249-line dedup of MCP dispatch boilerplate) — real but minor,
  quality-of-life refactor rather than a direction.
- ~9 `worktree-agent-*` / `worktree-wf_*` branches — empty diffs against main (stale agent worktrees, no
  content), not pathways.
- `feat/skill-macro-autoloop`, `feat/nucleus-delegate`, `feat/nucleus-onboard` — branch names present in
  `git branch -a` but resolve to no diff against current `origin/main` tip (already merged/superseded).

---

## Most-active recent thrust

The DSoR Verifier / anchor arc (#1) is the single most-active thrust right now — it's the branch actually
checked out, has the most recent commits in the entire repo, the largest new test file of the survey
(1130 lines), and every other "anchor"/"stone" branch in the branch list is a sibling of it.
