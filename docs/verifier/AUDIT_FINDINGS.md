# D1/D2 audit findings + execution addenda (2026-07-12)

> Banked from the Wave-1 consumption-policy audit so the Wave-3 "D-fix" (wiring the
> Verifier into the gating seams) has exact file:line targets, not a category list.
> **Structural finding: the DSoR Verifier has ZERO callers outside `verifier.py` /
> `verify_cli.py` — every seam below currently consumes a raw claim.** Wiring these
> (predicate-bound per RATIFICATION G2, flag `NUCLEUS_VERIFY_GATES`) is the single
> highest-leverage remaining build.

## The 10 located seams (most-severe first)

| # | file:line | consumes | gap | maps to | sev |
|---|---|---|---|---|---|
| 1 | `runtime/federation.py:363-369` | IPC `token`/`sender_id` | token-verify **commented out** — message dispatched regardless | A9 | HIGH |
| 2 | `runtime/federation.py:780-814`→`816-822` | `candidate_id` (unauth RPC) | Raft vote → `_become_leader` on raw body (inherits #1) | A9 | HIGH |
| 3 | `runtime/relay/core.py:178-183` | `sender`/`from_role`/`from_session_id` | "FS mode has no sender validation at all" | A2 | HIGH |
| 4 | `runtime/relay/core.py:27-29` + `207-224` | `body.artifact_refs` (`NUCLEUS_RELAY_STRICT`) | evidence gate = string-nonblank + regex; never probes SHA/URL | A4-adjacent | HIGH |
| 5 | `runtime/task_ops.py:184-224` + `257-296`/`279` | `status` (DONE/COMPLETE) | DAG release on a raw status field, no probe | **A4** (D-fix proof seam) | HIGH |
| 6 | `runtime/slot_ops.py:29-114` | `outcome` (default "success") | `status=DONE` + counter on self-asserted outcome | A5-adjacent | HIGH |
| 7 | `runtime/anon_telemetry.py:236-256` + `267-298` | `install_id`/`event_type` | fire-and-forget self-report → install/survival counts | A6 | HIGH |
| 8 | `sessions/registry.py:77-107` | `role` (+`agent`) | arbitrary caller string persisted as identity (the stone-2 gap) | A1/stone-1.5 | HIGH |
| 9 | `tools/governance.py:158-201` | `plan_text` | `[BB##]` regex over the submitter's own text | A12 | MED |
| 10 | `runtime/identity/gatekeeper.py:66-96` | `agent_id` | capability grants on raw string; **no live caller (dead today)** | A1-adjacent | MED (contained) |

Note: **no `census` aggregation exists in this repo** (grep empty) — A7's census lives in the `feat/census-v2.1` branch, not `src`.

## Execution addenda (gaps the transcript-scan caught)

- **A5 merge caveat (banked here, not just in the commit):** `feat/anchor-slots-lease`
  (428998f5) is chief-verified (62 pass incl. forge test) BUT its diff carries 159
  deletions from context-manager re-indentation — **flagged "needs an eyeball
  before merge"**; do NOT merge without confirming no unrelated refactor slipped in.
- **F1 (VAI render-pipeline confinement audit) — PARKED, not dropped.** Owner:
  delegate/agent (read-only). Trigger: next ComposedFit-lane touch OR when the VAI
  thesis is acted on. Scope: verify "One"'s render path is confined (attributes
  from catalog/`price_history` rows; model cannot inject a value; walk-out line
  suppressed when an attribute is missing). Cross-lane (bespoq/composedfit repo) —
  coordinate with cowork. This closes the orphaned "I'll add F1" commitment.
- **`nucleus_delegate` effect-detection false-negative** — filed separately (GH +
  memory): the tool returned `changed_paths: [] / effect: unknown` on TWO dispatches
  (A5 build, doc amendments) whose edits were real and on-shell-verified. A
  detection miss in the `_snapshot_paths`/`expect_paths` logic shipped in #679/#680.
  Until fixed: **always verify delegate writes on-shell** (`git status`), never
  trust `changed_paths`.
