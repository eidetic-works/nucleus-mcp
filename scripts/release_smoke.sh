#!/usr/bin/env bash
# =============================================================================
# release_smoke.sh — pre-publish release gate (ADR-0043 W2, kill-list item 2)
# =============================================================================
# The 1.8.8 wheel shipped a CLI that crashed on `--help` and an MCP server that
# listed 12 tools of which every single call threw `-32603 No module named
# ...god_combos.pulse_and_polish`. It reached PyPI because nothing exercised the
# BUILT WHEEL in a clean environment before upload. This script is that gate.
#
# It builds the wheel, installs it (NOT editable) into a CLEAN venv on the
# OLDEST supported Python available on this machine, then under a sandbox HOME
# (`env -i HOME=<tmp>`) runs the exact first-run a stranger hits:
#   1. nucleus --help                     (RC 0)
#   2. nucleus init  (in a fresh project) (RC 0, writes .brain/)
#   3. MCP stdio handshake: initialize + tools/list + ONE real tools/call
# Plus a wheel-completeness assertion (every source module is in the wheel).
#
# ANY failure => nonzero exit. Wire it ahead of `twine upload`.
#
# Usage:
#   bash scripts/release_smoke.sh
#   KEEP_WORKDIR=1 bash scripts/release_smoke.sh   # keep the temp build/venv
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

log()  { printf '[smoke] %s\n' "$*"; }
fail() { printf '[smoke] FAIL: %s\n' "$*" >&2; exit 1; }

WORKDIR="$(mktemp -d)"
DIST_DIR="$WORKDIR/dist"
VENV_DIR="$WORKDIR/venv"
SANDBOX_HOME="$WORKDIR/home"
PROJECT_DIR="$WORKDIR/project"
mkdir -p "$DIST_DIR" "$SANDBOX_HOME" "$PROJECT_DIR"

cleanup() {
  if [[ "${KEEP_WORKDIR:-0}" == "1" ]]; then
    log "KEEP_WORKDIR=1 — leaving $WORKDIR"
  else
    rm -rf "$WORKDIR"
  fi
}
trap cleanup EXIT

# ── [1/6] Determine the Requires-Python floor and pick the oldest supported ──
log "[1/6] Resolving Python floor + oldest supported interpreter"
FLOOR="$(grep -E '^requires-python' pyproject.toml | grep -oE '3\.[0-9]+' | head -1)"
[[ -n "$FLOOR" ]] || fail "could not parse requires-python from pyproject.toml"
FLOOR_MINOR="${FLOOR#3.}"
log "  requires-python floor: >=$FLOOR"

SMOKE_PY=""
SMOKE_MINOR=""
for minor in $(seq "$FLOOR_MINOR" 20); do
  cand="python3.$minor"
  if command -v "$cand" >/dev/null 2>&1; then
    SMOKE_PY="$cand"; SMOKE_MINOR="$minor"; break
  fi
done
[[ -n "$SMOKE_PY" ]] || fail "no python >= $FLOOR found on PATH"
log "  oldest supported interpreter available: $SMOKE_PY ($($SMOKE_PY --version 2>&1))"

# ── [2/6] Build the wheel ────────────────────────────────────────────────────
log "[2/6] Building wheel"
BUILD_PY=""
for cand in "$SMOKE_PY" python3 python3.12 python3.13; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import build" >/dev/null 2>&1; then
    BUILD_PY="$cand"; break
  fi
done
[[ -n "$BUILD_PY" ]] || fail "no interpreter with the 'build' module found (pip install build)"

BUILD_ARGS=(-m build --wheel -o "$DIST_DIR")
# Offline-deterministic when the backend is already importable.
if "$BUILD_PY" -c "import hatchling" >/dev/null 2>&1; then
  BUILD_ARGS+=(--no-isolation)
  log "  using $BUILD_PY (hatchling present -> --no-isolation)"
else
  log "  using $BUILD_PY (isolated build)"
fi
"$BUILD_PY" "${BUILD_ARGS[@]}" >"$WORKDIR/build.log" 2>&1 || { cat "$WORKDIR/build.log"; fail "wheel build failed"; }
WHEEL="$(ls -t "$DIST_DIR"/*.whl 2>/dev/null | head -1)"
[[ -n "$WHEEL" && -f "$WHEEL" ]] || fail "wheel not produced"
log "  built: $(basename "$WHEEL") ($(du -h "$WHEEL" | cut -f1))"

# ── [3/6] Wheel-completeness: every source module must be inside the wheel ──
log "[3/6] Wheel-completeness check (source imports -> wheel contents)"
PYTHONPATH="$REPO_ROOT" NUCLEUS_WHEEL="$WHEEL" "$SMOKE_PY" - "$REPO_ROOT" "$WHEEL" <<'PYEOF' || fail "wheel-completeness check failed"
import sys
from pathlib import Path
repo_root = Path(sys.argv[1]); wheel = Path(sys.argv[2])
from tests.release._wheel_utils import source_modules, wheel_modules, internal_import_targets
src = repo_root / "src"
src_mods = source_modules(src)
whl_mods = wheel_modules(wheel)
targets = internal_import_targets(src)
referenced = {t for t in targets if t in src_mods}
sentinel = "mcp_server_nucleus.runtime.god_combos.pulse_and_polish"
if sentinel not in referenced:
    print(f"  ! import walker did not resolve sentinel {sentinel}", file=sys.stderr); sys.exit(1)
missing_ref = sorted(referenced - whl_mods)
dropped = sorted(src_mods - whl_mods)
if missing_ref:
    print("  import-referenced modules absent from wheel:", *missing_ref, sep="\n    ", file=sys.stderr); sys.exit(1)
if dropped:
    print("  source modules dropped from wheel:", *dropped, sep="\n    ", file=sys.stderr); sys.exit(1)
print(f"  OK: {len(src_mods)} source modules, all present in wheel; "
      f"{len(referenced)} import-referenced modules verified")
PYEOF

# ── [4/6] Clean venv + install the WHEEL (not editable) ─────────────────────
log "[4/6] Creating clean venv on $SMOKE_PY and installing the wheel"
"$SMOKE_PY" -m venv "$VENV_DIR" || fail "venv creation failed"
VPY="$VENV_DIR/bin/python"
"$VPY" -m pip install --disable-pip-version-check -q --upgrade pip >/dev/null 2>&1 || true
"$VPY" -m pip install --disable-pip-version-check -q "$WHEEL" >"$WORKDIR/install.log" 2>&1 \
  || { tail -30 "$WORKDIR/install.log"; fail "wheel install failed"; }
NUCLEUS_BIN="$VENV_DIR/bin/nucleus"
NUCLEUS_MCP_BIN="$VENV_DIR/bin/nucleus-mcp"
[[ -x "$NUCLEUS_BIN" ]]     || fail "console script 'nucleus' missing after install"
[[ -x "$NUCLEUS_MCP_BIN" ]] || fail "console script 'nucleus-mcp' missing after install"
log "  installed; console scripts present: nucleus, nucleus-mcp"

# ── [5/6] Sandbox HOME: --help + init ───────────────────────────────────────
log "[5/6] Sandbox first-run: nucleus --help + nucleus init"
env -i HOME="$SANDBOX_HOME" PATH="/usr/bin:/bin" "$NUCLEUS_BIN" --help >"$WORKDIR/help.log" 2>&1 \
  || { tail -20 "$WORKDIR/help.log"; fail "nucleus --help exited nonzero"; }
log "  nucleus --help: RC 0"

( cd "$PROJECT_DIR" && env -i HOME="$SANDBOX_HOME" PATH="/usr/bin:/bin" "$NUCLEUS_BIN" init >"$WORKDIR/init.log" 2>&1 ) \
  || { tail -20 "$WORKDIR/init.log"; fail "nucleus init exited nonzero"; }
[[ -d "$PROJECT_DIR/.brain" ]] || fail "nucleus init did not create .brain/"
log "  nucleus init: RC 0, .brain/ created"

# ── [6/6] Sandbox HOME: MCP stdio handshake + one real tool call ────────────
log "[6/6] MCP stdio handshake (initialize + tools/list + real tools/call)"
env -i HOME="$SANDBOX_HOME" PATH="/usr/bin:/bin" NUCLEUS_BRAIN_PATH="$PROJECT_DIR/.brain" \
  "$VPY" "$SCRIPT_DIR/../tests/release/mcp_stdio_probe.py" -- "$NUCLEUS_MCP_BIN" \
  || fail "MCP stdio handshake / tool call failed"

log "──────────────────────────────────────────────"
log "PASS: wheel builds, is complete, installs clean on $SMOKE_PY,"
log "      and boots a working MCP server ($(basename "$WHEEL"))."
log "──────────────────────────────────────────────"
