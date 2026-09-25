#!/usr/bin/env bash
# Nightly bounded re-index of the brain RAG corpus.
#
# Replaces the cron entry disabled on 2026-04-11 with the note "broken
# (timeout)", which then stayed off for 119 days while the kind='brain' corpus
# silently served an April snapshot (fw-1786166556, fw-1786175531).
#
# The original job could not have worked: the backlog is ~5,381 chunks at ~2.7s
# of embedding each, roughly 4 hours. This one takes a wall-clock budget, stops
# cleanly when it runs out, and resumes on the next run for free — index_brain
# skips any chunk whose content hash is already present, and that check happens
# before embedding. Ten nightly runs clear the backlog; steady state is minutes.
#
# Install (nightly at 02:41, off the :00 mark):
#   41 2 * * *  /bin/bash <repo>/mcp-server-nucleus/scripts/reindex_brain_bounded.sh
set -uo pipefail

REPO="${NUCLEUS_REPO:-$HOME/ai-mvp-backend}"
BRAIN="${NUCLEUS_BRAIN_PATH:-$REPO/.brain}"
BUDGET="${NUCLEUS_REINDEX_BUDGET_SECONDS:-1500}"   # 25 min
LOG_DIR="$BRAIN/reports"
LOG="$LOG_DIR/reindex_brain.log"

mkdir -p "$LOG_DIR"
exec >>"$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') bounded reindex (budget=${BUDGET}s) ==="

cd "$REPO" || { echo "FATAL: cannot cd to $REPO"; exit 1; }

python3 - "$BRAIN" "$BUDGET" <<'PY'
import sys, time
sys.path.insert(0, ".")
from pathlib import Path
from providers.brain_rag import index_brain, index_freshness

brain, budget = Path(sys.argv[1]), float(sys.argv[2])

before = index_freshness(brain)
stale_before = list(before.get("stale", []))
if stale_before:
    print(f"  stale corpora before: {stale_before}")

t0 = time.time()
try:
    n = index_brain(brain, force=False, max_seconds=budget)
except Exception as exc:
    # Never leave a silent failure in a log nobody reads: name it and exit
    # non-zero so any wrapper or monitor can see it.
    print(f"  FATAL: index_brain raised: {type(exc).__name__}: {exc}")
    raise SystemExit(1)

after = index_freshness(brain)
print(f"  indexed {n} new chunks in {time.time() - t0:.0f}s")
for kind, info in sorted(after.get("kinds", {}).items()):
    flag = " STALE" if info["stale"] else ""
    print(f"    {kind:14s} {info['chunks']:6d} chunks  age={info['age_days']}d{flag}")

fixed = set(stale_before) - set(after.get("stale", []))
if fixed:
    print(f"  no longer stale: {sorted(fixed)}")
if after.get("stale"):
    # Expected while the backlog drains — say which, so 'still stale' after the
    # backlog should be gone is visible rather than assumed to be normal.
    print(f"  STILL STALE: {sorted(after['stale'])} — re-runs needed, or the "
          f"corpus has no live writer at all")
PY

echo "done rc=$?"
