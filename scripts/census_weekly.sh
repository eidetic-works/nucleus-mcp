#!/usr/bin/env bash
# Weekly census + self-digest runner (invoked by com.nucleus.census-weekly).
# Idempotent, fail-open: a bad week must not wedge the schedule.
set -uo pipefail

REPO_ROOT="${NUCLEUS_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${PYTHON:-python3}"
REPORTS="$REPO_ROOT/infra/telemetry/reports/census"
BASELINE="$REPO_ROOT/config/census/frozen_baseline.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$REPORTS"
cd "$REPO_ROOT" || exit 0

# 1. Census: capture an immutable snapshot + score (honest baseline run).
"$PY" scripts/census_v2.py run --roots "$REPO_ROOT" \
    --out "$REPORTS/census_run_$STAMP.json" \
    > "$REPORTS/census_summary_$STAMP.json" 2>> "$REPORTS/census.err" || true

# 2. Self-digest (uses the frozen baseline when one exists).
BASELINE_ARG=()
[ -f "$BASELINE" ] && BASELINE_ARG=(--baseline "$BASELINE")
"$PY" scripts/self_digest_v2.py --roots "$REPO_ROOT" "${BASELINE_ARG[@]}" \
    --out "$REPORTS/self_digest_$STAMP.json" 2>> "$REPORTS/census.err" || true

echo "census-weekly $STAMP -> $REPORTS"
