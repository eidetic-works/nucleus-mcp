# Release gate — verify before publishing to PyPI

One check, and it exists because a real defect shipped and sat in the published
package for six weeks.

## MUST VERIFY: the model-pricing fix is in the artifact

Published `nucleus-mcp` **1.16.5** (2026-08-02) prices every dated or suffixed
model id at the `_default` fallback. Anyone who `pip install`s it today gets
this. Verified by executing the published code, not by reading it:

    estimate_cost(model, 1M in, 1M out) in PUBLISHED 1.16.5
        claude-opus-4-6                 $  2.50     <- what the codebase passes
        claude-opus-4                   $ 90.00     <- what the table contains
        claude-haiku-4-5-20251001       $  2.50
        _nonexistent-xyz                $  2.50
        ratio 36x

The cause is an exact dict lookup with no prefix match, so the table matches a
naming convention the callers do not use. `claude-opus-4` pricing correctly is
the coincidence, not the rule.

Fixed in-tree by **89849dc0** (`MODEL_FAMILY_PRICING`, family-prefix matching).

### The check

    python3 -c "import tarfile,sys; t=tarfile.open(sys.argv[1]); \
      print(any(b'MODEL_FAMILY_PRICING' in t.extractfile(m).read() \
      for m in t.getmembers() if m.name.endswith('token_budget.py')))" dist/*.tar.gz

Must print `True`. If it prints `False`, **do not publish** — the release would
re-ship the 36x defect.

Opposed half, so the check is known to be able to fail: run the same command
against `nucleus_mcp-1.16.5.tar.gz` from PyPI. It must print `False`.

## Why this cannot silently break

`[tool.hatch.build.targets.sdist] only-include = ["src", ...]` puts the whole
`src` tree in the sdist. `export-ignore` in `.gitattributes` does **not** apply —
that governs `git archive`, which builds the public GitHub mirror, a different
artifact. 20 of 500 src files are export-ignored deliberately (autopilot,
compounding_loop, god_combos, marketing_engine), and `token_budget.py` is among
them, so the fix reaches **PyPI but not the public mirror**. That is consistent
with the moat separation and is not a defect — but it means verifying the mirror
is not a substitute for verifying the sdist.

## Historical cost data is NOT recoverable

`.brain/metrics/agent_costs.jsonl` holds 2,645 rows priced by the broken table,
and **zero of them record which model was used**. The input needed to re-price
was never captured. Quarantined in `.brain/metrics/agent_costs.INVALID.md`; the
rows are kept as execution telemetry, the cost column is void. Vendor dashboards
are authoritative for spend.

---

# Gate 2 — does the artifact contain a real identity? (added 2026-09-15)

**Run this LAST, after everything else is green. It exists because everything
else was green.**

    python3 scripts/artifact_identity_gate.py dist/*.tar.gz

    exit 0 = patterns only, safe to publish
    exit 2 = POISONED, do not publish

**Check the exit code OUTSIDE a pipeline.** `| tail` returns tail's status and
will report 0 for a failing gate. That happened while building this very check.

## Why counting `/Users/` is the wrong instrument

A pseudonymity checker legitimately contains `/Users/` — as a regex, that is its
job. A count cannot tell the DETECTOR from the PAYLOAD. Measured on two real
artifacts:

| artifact | distinct names | files | real identity | verdict |
|---|---|---|---|---|
| published 1.16.5 | 3 | 2 | **0** | SAFE — patterns |
| unpublished 1.16.6 | 5 | 4 | **1** | **POISONED** |

Same shape, opposite verdicts. Only hashing each captured name against the real
home separates them — mechanically, with nothing sensitive printed.

## The rule

> **A detector may contain PATTERNS of what it detects.
> It may never contain INSTANCES.**

`skill_extractor.py` and `pseudonymity_guard.py` hold regexes and are publishable.
`build_runner.py:1201-1203` held the literal home directory in a hardcoded
blocklist and was not. Same purpose, two implementations, one shippable.

## Known inputs — this gate can always be shown to emit both verdicts

    known-GOOD   nucleus_mcp-1.16.5.tar.gz   from PyPI       -> exit 0
    known-BAD    nucleus_mcp-1.16.6.tar.gz   unpublished     -> exit 2

> **Corrected 2026-09-18.** Two things this document said were not true of the repo.
>
> **The script did not exist.** `scripts/artifact_identity_gate.py` was described
> here as the last gate before publishing, and credited with catching 1.16.6, but
> it was in neither the tree nor git history. It exists now, with the contract
> above plus a third state the text implied and never named: **exit 3
> INSUFFICIENT**, when no term list can be found. An empty list must never read as
> clean. It scans the **wheel as well as the sdist** — the wheel is what `pip
> install` delivers and was never identity-scanned before.
>
> **The known-bad control had already rotted.** This section said "keep the
> poisoned 1.16.6 tarball"; it is not on this machine, and a control that depends
> on a file nobody is accountable for decays silently. The control is now
> **generated per run**: `publish_readiness.sh --prove-controls` copies the real
> artifact, injects a synthetic planted string, and refuses to print READY unless
> the gate rejects it. Same shape as the 1.16.5/1.16.6 pair above, nothing to lose.
>
> **The gate now sits on the publish path, not beside it.** `publish_pypi.sh`
> refuses to upload unless a readiness receipt matches the sha256 of the artifacts
> in hand, and refuses a receipt produced without `--prove-controls`. A gate
> someone has to remember to run is the failure this whole document is about.

A gate that has only ever seen clean inputs is not known to work.

## What this caught, and why nothing upstream could

1.16.6 passed the content gate (both halves), installed cleanly into a fresh
venv, and priced correctly **from the installed package**. Then this found the
operator's home directory inside the pseudonymity preflight's own blocklist — the
guard built to stop identity reaching public artifacts was about to publish it.

A positive control would NOT have caught it. The control proves an instrument can
detect identity; that one could, via the list that *was* the payload.

**Upstream checks verify the PROCESS. Only the last one verifies the THING.**
