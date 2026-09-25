#!/usr/bin/env bash
# publish_readiness.sh — everything that must be true before this package ships.
#
# It publishes NOTHING. There is no twine call anywhere in this file. On success
# it writes a receipt naming the exact artifacts it checked; publish_pypi.sh
# refuses to upload without a receipt matching the artifacts in hand. That is the
# point: a gate beside the publish path is a gate someone forgets, and this repo
# already measured what forgetting costs.
#
#   bash scripts/publish_readiness.sh                  # check
#   bash scripts/publish_readiness.sh --prove-controls # also prove each gate can FAIL
#
# Exit 0 = READY (receipt written). Anything else = not ready, reason printed.
set -u

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PKG_ROOT"
PROVE=0; [ "${1:-}" = "--prove-controls" ] && PROVE=1

RECEIPT_DIR="${NUCLEUS_RECEIPT_DIR:-$PKG_ROOT/.publish-receipts}"
RUN_TMP="$(mktemp -d "${TMPDIR:-/tmp}/nucleus-readiness-XXXXXX")"   # unique per run:
trap 'rm -rf "$RUN_TMP"' EXIT                                       # a shared temp dir
FAIL=0                                                              # lets a concurrent
step() { printf '\n[%s] %s\n' "$1" "$2"; }                          # run scan this one's
bad()  { printf '  FAIL: %s\n' "$*"; FAIL=1; }                      # planted poison
note() { printf '  %s\n' "$*"; }

step 0 "preflight"
PYTHONPATH="$PKG_ROOT/src" python3 -m mcp_server_nucleus.runtime.preflight \
    --repo "$(git rev-parse --show-toplevel)" --banner || bad "preflight could not read the repo"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
HEAD_SHA="$(git rev-parse HEAD)"
DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"
note "branch $BRANCH   head ${HEAD_SHA:0:8}   uncommitted $DIRTY"
[ "$DIRTY" = "0" ] || bad "working tree is dirty — an artifact built from uncommitted state is not reproducible"

step 1 "secrets in the worktree (tracked, untracked AND ignored)"
if [ -x "$PKG_ROOT/scripts/scan_worktree_secrets.py" ]; then
  OUT="$(python3 "$PKG_ROOT/scripts/scan_worktree_secrets.py" 2>&1)"; RC=$?
  printf '%s\n' "$OUT" | tail -3 | sed 's/^/  /'
  [ "$RC" -eq 0 ] || bad "worktree secret scan reported findings"
else
  note "scan_worktree_secrets.py not present — skipped"
fi

step 2 "build the artifacts (never reuse dist/, which may be stale)"
python3 -m build --outdir "$RUN_TMP/dist" >"$RUN_TMP/build.log" 2>&1 \
  || { bad "python -m build failed"; tail -5 "$RUN_TMP/build.log" | sed 's/^/    /'; }
SDIST="$(ls "$RUN_TMP"/dist/*.tar.gz 2>/dev/null | head -1)"
WHEEL="$(ls "$RUN_TMP"/dist/*.whl 2>/dev/null | head -1)"
[ -f "${SDIST:-}" ] && note "sdist $(basename "$SDIST")" || bad "no sdist produced"
[ -f "${WHEEL:-}" ] && note "wheel $(basename "$WHEEL")" || bad "no wheel produced"

step 3 "identity gate on BOTH artifacts"
for art in "${SDIST:-}" "${WHEEL:-}"; do
  [ -f "$art" ] || continue
  OUT="$(python3 scripts/artifact_identity_gate.py "$art" 2>&1)"; RC=$?
  note "$(basename "$art"): exit $RC — $(printf '%s' "$OUT" | grep -E 'CLEAN|POISONED|INSUFFICIENT' | head -1)"
  case "$RC" in
    0) ;;
    2) bad "$(basename "$art") is POISONED"; printf '%s\n' "$OUT" | grep '<-' | sed 's/^/    /' ;;
    *) bad "$(basename "$art"): gate could not run (exit $RC) — that is not a pass" ;;
  esac
done

step "3b" "third-party PII gate on BOTH artifacts"
# The identity gate holds hashes of the OPERATOR's terms. Measured 2026-09-19: a
# two-row prospect list passed it, and passed the secret scanner too, because an
# email is not a credential and a stranger's name is not the operator's. Other
# people's contact data had no instrument at all until this one.
for art in "${SDIST:-}" "${WHEEL:-}"; do
  [ -f "$art" ] || continue
  OUT="$(python3 scripts/third_party_pii_gate.py "$art" 2>&1)"; RC=$?
  note "$(basename "$art"): exit $RC -- $(printf '%s' "$OUT" | grep -E 'CLEAN|FOUND|INSUFFICIENT' | head -1)"
  case "$RC" in
    0) ;;
    2) bad "$(basename "$art") carries third-party contact data"
       printf '%s\n' "$OUT" | sed -n '2,8p' | sed 's/^/    /' ;;
    *) bad "$(basename "$art"): PII gate could not run (exit $RC) -- that is not a pass" ;;
  esac
done

step "3c" "withheld-module gate on BOTH artifacts"
# The gate this pipeline never had. scripts/validate_public_surface.sh declared
# 21 paths SOVEREIGN and checked them against the `git archive` mirror only;
# export-ignore has no bearing on hatchling, so eight shipped in every wheel for
# 33 releases. This reads the artifact, against .withheld-modules.txt — the same
# list pyproject.toml excludes from.
for art in "${SDIST:-}" "${WHEEL:-}"; do
  [ -f "$art" ] || continue
  OUT="$(python3 scripts/sovereign_surface_gate.py "$art" 2>&1)"; RC=$?
  note "$(basename "$art"): exit $RC -- $(printf '%s' "$OUT" | grep -E 'CLEAN|LEAKED|INSUFFICIENT' | head -1)"
  case "$RC" in
    0) ;;
    2) bad "$(basename "$art") carries a withheld module"
       printf '%s\n' "$OUT" | sed -n '2,8p' | sed 's/^/    /' ;;
    *) bad "$(basename "$art"): withheld gate could not run (exit $RC) -- that is not a pass" ;;
  esac
done

step 4 "stranger install: clean venv, then the README's own quickstart"
if [ -f "${WHEEL:-}" ]; then
  python3 -m venv "$RUN_TMP/venv" >/dev/null 2>&1
  "$RUN_TMP/venv/bin/pip" install -q "$WHEEL" >"$RUN_TMP/install.log" 2>&1 \
    || { bad "pip install of the built wheel failed"; tail -3 "$RUN_TMP/install.log" | sed 's/^/    /'; }
  if [ -x "$RUN_TMP/venv/bin/nucleus" ]; then
    mkdir -p "$RUN_TMP/work"
    ( cd "$RUN_TMP/work" && "$RUN_TMP/venv/bin/nucleus" init --recipe founder >/dev/null 2>&1 ) \
      && note "install + 'nucleus init --recipe founder' both succeeded in an empty dir" \
      || bad "'nucleus init' failed for a fresh install"
  else
    bad "the 'nucleus' entry point is missing from the built wheel"
  fi
fi

step 5 "release gates (sdist)"
if [ -f "${SDIST:-}" ] && [ -f scripts/release_gates.py ]; then
  OUT="$(python3 scripts/release_gates.py "$SDIST" 2>&1)"; RC=$?
  printf '%s\n' "$OUT" | tail -4 | sed 's/^/  /'
  [ "$RC" -eq 0 ] || bad "release_gates.py exited $RC"
fi

if [ "$PROVE" = "1" ]; then
  step 6 "prove the controls can FAIL (planted poison)"
  python3 - "$RUN_TMP" <<'PY'
import sys, pathlib, shutil, zipfile
t = pathlib.Path(sys.argv[1]); w = next(t.glob("dist/*.whl"), None)
if w:
    p = t / "planted.whl"; shutil.copy(w, p)
    with zipfile.ZipFile(p, "a") as z:
        # assembled at runtime: an absolute home path written literally here would
        # (rightly) be blocked by this repo's own lane-hygiene guard
        planted = "/" + "Users" + "/plantedstranger/nucleus"
        z.writestr("mcp_server_nucleus/_planted.py", f'H = "{planted}"\n')
    print(p)
PY
  PLANTED="$RUN_TMP/planted.whl"
  if [ -f "$PLANTED" ]; then
    python3 scripts/artifact_identity_gate.py "$PLANTED" >/dev/null 2>&1; RC=$?
    [ "$RC" -eq 2 ] && note "identity gate REJECTED a planted artifact (exit 2) — the control works" \
                    || bad "identity gate did NOT reject planted poison (exit $RC) — every green above is meaningless"

    python3 - "$RUN_TMP" <<'PYX'
import sys, pathlib, shutil, zipfile
t = pathlib.Path(sys.argv[1]); w = next(t.glob("dist/*.whl"), None)
if w:
    q = t / "planted_pii.whl"; shutil.copy(w, q)
    with zipfile.ZipFile(q, "a") as z:
        z.writestr("mcp_server_nucleus/prospects.csv",
                   "name,email" + chr(10) + "Jane Roe,jane.roe@plantedcorp.io" + chr(10))
    print(q)
PYX
    PLANTED_PII="$RUN_TMP/planted_pii.whl"
    if [ -f "$PLANTED_PII" ]; then
      python3 scripts/third_party_pii_gate.py "$PLANTED_PII" >/dev/null 2>&1; RC=$?
      [ "$RC" -eq 2 ] && note "PII gate REJECTED a planted contact list (exit 2) - the control works" \
                      || bad "PII gate did NOT reject a planted contact list (exit $RC) - its green above means nothing"
    else
      bad "could not build a planted contact list, so the PII control is unproven"
    fi

    python3 - "$RUN_TMP" <<'PYZ'
import sys, pathlib, shutil, zipfile
t = pathlib.Path(sys.argv[1]); w = next(t.glob("dist/*.whl"), None)
if w:
    q = t / "planted_withheld.whl"; shutil.copy(w, q)
    with zipfile.ZipFile(q, "a") as z:
        z.writestr("mcp_server_nucleus/siphon.py", "# planted withheld module" + chr(10))
    print(q)
PYZ
    PLANTED_W="$RUN_TMP/planted_withheld.whl"
    if [ -f "$PLANTED_W" ]; then
      python3 scripts/sovereign_surface_gate.py "$PLANTED_W" >/dev/null 2>&1; RC=$?
      [ "$RC" -eq 2 ] && note "withheld gate REJECTED a planted module (exit 2) - the control works" \
                      || bad "withheld gate did NOT reject a planted module (exit $RC) - its green above means nothing"
    else
      bad "could not build a planted withheld artifact, so that control is unproven"
    fi
  else
    bad "could not build a planted artifact, so the controls are unproven"
  fi
fi

step 7 "verdict"
if [ "$FAIL" -ne 0 ]; then
  echo "  NOT READY — see FAIL lines above"
  exit 1
fi
mkdir -p "$RECEIPT_DIR"
SHA_SDIST="$(shasum -a 256 "$SDIST" | awk '{print $1}')"
SHA_WHEEL="$(shasum -a 256 "$WHEEL" | awk '{print $1}')"
RECEIPT="$RECEIPT_DIR/$(date -u +%Y%m%dT%H%M%SZ)-${HEAD_SHA:0:8}.receipt"
cat > "$RECEIPT" <<EOF
# publish readiness receipt — publish_pypi.sh will not upload without a match
branch=$BRANCH
head=$HEAD_SHA
generated=$(date -u +%Y-%m-%dT%H:%M:%SZ)
controls_proven=$PROVE
sdist_sha256=$SHA_SDIST
wheel_sha256=$SHA_WHEEL
sdist_name=$(basename "$SDIST")
wheel_name=$(basename "$WHEEL")
EOF
cp "$SDIST" "$WHEEL" "$RECEIPT_DIR/" 2>/dev/null || true
echo "  READY"
echo "  sdist $SHA_SDIST"
echo "  wheel $SHA_WHEEL"
echo "  receipt $RECEIPT"
[ "$PROVE" = "1" ] || echo "  NOTE: run with --prove-controls before an actual release; a gate that has not failed is unproven"
exit 0
