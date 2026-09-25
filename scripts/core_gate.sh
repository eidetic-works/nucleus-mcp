#!/usr/bin/env bash
#
# CORE FAST-GATE runner (ADR-0043 W1).
#
# Runs the spine subset of the suite defined in tests/core_gate_files.txt:
# runtime/entrypoint registration + memory facade/SoR + relay. Prints the test
# count and wall time, and exits nonzero on ANY failure. Target: < 90s.
#
# Python selection (first hit wins):
#   1. $CORE_GATE_PYTHON            (explicit override)
#   2. <pkg-root>/.venv/bin/python  (repo venv, when present)
#   3. python3 / python on PATH     (CI installs the package into this)
#
# The gate always runs with PYTHONPATH=src so the in-tree package is imported,
# matching the repo's pyproject `pythonpath = ["src"]`.
#
# Usage:
#   scripts/core_gate.sh                 # run the gate
#   CORE_GATE_PYTHON=/path/to/python scripts/core_gate.sh
#   scripts/core_gate.sh -x --tb=short   # extra args are forwarded to pytest

set -u -o pipefail

# --- locate package root (dir holding pyproject.toml) -----------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PKG_ROOT"

MANIFEST="tests/core_gate_files.txt"
if [[ ! -f "$MANIFEST" ]]; then
  echo "core-gate: FATAL manifest not found: $PKG_ROOT/$MANIFEST" >&2
  exit 2
fi

# --- pick python ------------------------------------------------------------
pick_python() {
  if [[ -n "${CORE_GATE_PYTHON:-}" ]]; then echo "$CORE_GATE_PYTHON"; return; fi
  if [[ -x "$PKG_ROOT/.venv/bin/python" ]]; then echo "$PKG_ROOT/.venv/bin/python"; return; fi
  if command -v python3 >/dev/null 2>&1; then command -v python3; return; fi
  if command -v python  >/dev/null 2>&1; then command -v python;  return; fi
  echo ""; return
}
PY="$(pick_python)"
if [[ -z "$PY" ]]; then
  echo "core-gate: FATAL no python interpreter found (set CORE_GATE_PYTHON)" >&2
  exit 2
fi

# --- read manifest into an array (skip blanks and # comments) ---------------
FILES=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%$'\r'}"                      # strip CR (Windows checkouts)
  [[ -z "${line//[[:space:]]/}" ]] && continue
  [[ "${line#\#}" != "$line" ]] && continue  # comment line
  FILES+=("$line")
done < "$MANIFEST"

if [[ "${#FILES[@]}" -eq 0 ]]; then
  echo "core-gate: FATAL manifest selected 0 files" >&2
  exit 2
fi

# --- verify every path resolves (fail loud, not silently under-select) ------
MISSING=()
for f in "${FILES[@]}"; do
  [[ -e "$f" ]] || MISSING+=("$f")
done
if [[ "${#MISSING[@]}" -gt 0 ]]; then
  echo "core-gate: FATAL ${#MISSING[@]} manifest path(s) missing:" >&2
  printf '  %s\n' "${MISSING[@]}" >&2
  exit 2
fi

echo "core-gate: interpreter=$PY"
echo "core-gate: files=${#FILES[@]} (from $MANIFEST)"

# --- run, timed -------------------------------------------------------------
START=$(date +%s)
PYTHONPATH=src "$PY" -m pytest "${FILES[@]}" -q -p no:cacheprovider "$@"
RC=$?
END=$(date +%s)
WALL=$((END - START))

echo "----------------------------------------------------------------------"
echo "core-gate: exit=$RC wall=${WALL}s files=${#FILES[@]}"
exit "$RC"
