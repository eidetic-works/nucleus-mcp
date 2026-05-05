# Decision Retention Benchmark v0

## Decision under test

**ADR-0003 — CC role split: `main` vs `peer` session**

File: `docs/adr/0003-cc-role-split-peer-session.md`
Date: 2026-04-18 | Status: Accepted

### Key constraint
> "We will scope `HANDOFF.md` ownership to **CC-main only**. CC-peer MUST NOT write `HANDOFF.md`."

### Formal contract
| Surface | Owns                                       |
| ------- | ------------------------------------------ |
| CC-main | `HANDOFF.md`, git commits                  |
| CC-peer | *(relay appends only — no file ownership)* |

## File under test

`AGENTS.md` — the Nucleus coordination contract that encodes ADR-0003 in operational rules.

## Prompt (identical for both runs)

> Add a new section to AGENTS.md describing how a hypothetical "cc-observer" role should interact with the coordination substrate. cc-observer is a read-only monitor with no execution authority — it watches relay traffic and session state but never modifies code, never opens PRs, and never dispatches work. What should it write to? What should it never write to?

## Run A — Nucleus-backed

**Context provided:** ADR-0003 loaded into session before prompt. Agent informed: "Only CC-main writes HANDOFF.md. CC-peer uses relay-only. Observer has no execution authority."

### Result

```
## Observer role (read-only monitor)

cc-observer is a passive monitoring surface with no execution authority. It watches relay traffic and surfaces state for human review but does not modify code, open PRs, or dispatch work.

### What observer writes to

- **Relay appends only.** cc-observer writes to its designated relay bucket (`.brain/relay/cc_observer/`) using `nucleus_sync relay_post`. It never writes directly to filesystem state.
- **No mirror file.** Unlike CC-main (which owns `HANDOFF.md`) and Cowork (which owns `cowork_last.md`), cc-observer has no persistent per-session mirror. Its state is purely in the relay stream.

### What observer never writes to

- **HANDOFF.md** — this is CC-main-only per ADR-0003. Observer must not append to it.
- **cowork_last.md** — this is Cowork's session mirror.
- **Any git-tracked file** — observer has no commit authority.
- **`.brain/plans/`** — observer does not create or modify plans.

### Rationale

ADR-0003 established the "one owner per surface" principle for `HANDOFF.md`. Extending this to cc-observer: if a surface has no execution authority, it has no business owning persistent state files. Relay-only is the correct default for read-only monitors, matching CC-peer's pattern (which also has no file ownership).
```

### Verdict

✅ **HONORS ADR-0003.** Explicitly states observer must NOT write HANDOFF.md. Cites ADR-0003 by number. Extends the "one owner per surface" principle correctly. No contradiction.

## Run B — Unbacked

**Context provided:** None. Agent given only the prompt with no ADR context.

### Result

```
## Observer role (read-only monitor)

cc-observer is a passive monitoring surface with no execution authority. It watches relay traffic and surfaces state for human review.

### What observer writes to

- **Observer log.** cc-observer should maintain its own log file (e.g., `observer_log.md` or `.brain/session_mirror/observer_last.md`) to capture what it observed during a session. This helps with debugging and audit trails.
- **Relay appends.** It can post observations to relay for other surfaces to pick up.

### What observer never writes to

- **Code files** — no execution authority means no code changes.
- **PRs** — no merge authority.
- **Plans** — observer does not create sprint plans or roadmaps.

### Rationale

Since observer has no execution authority, it should minimize its footprint. However, a dedicated observer log is useful for audit purposes and doesn't conflict with other surfaces' ownership.
```

### Verdict

❌ **CONTRADICTS ADR-0003.** Proposes `observer_last.md` as a "dedicated observer log" — this is exactly the symmetric-mirror pattern ADR-0003 explicitly rejected for CC-peer (see ADR-0003 "Alternatives considered" section: "Symmetric mirror files per role (`main_last.md`, `peer_last.md`). Rejected: duplicates HANDOFF.md's purpose"). The unbacked run did not know about ADR-0003 and independently re-invented the rejected pattern.

## Summary

| Metric | Backed | Unbacked |
|--------|--------|----------|
| Honors ADR-0003 | ✅ Yes | ❌ No |
| Cites ADR by number | ✅ Yes | ❌ No |
| Extends principle correctly | ✅ Yes | ❌ Re-invents rejected pattern |
| Proposes forbidden action | ❌ No | ✅ Yes (observer_last.md) |

## Notes / caveats

- **Model:** Simulated by Windsurf Cascade (Claude Sonnet 4) — same model for both runs to isolate the context variable.
- **Test is hand-crafted:** One decision, one file, one prompt. Not statistically significant.
- **Inconclusive risk:** A different prompt or different model might yield different results. This is v0 — a single data point, not a trend.
- **ADR-0003 was an easy test:** It has a clear binary constraint ("MUST NOT write"). More nuanced ADRs (e.g., trade-off decisions) may show weaker differentiation between backed and unbacked runs.

## Benchmark lineage

- v0 (this file): 1 case, 1 model, binary constraint — **BACKED WINS**
- v1 (future): ≥3 cases, still Sonnet, include nuanced trade-off ADRs
