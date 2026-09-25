#!/usr/bin/env bash
# check_product_leak.sh — does the shipped package name an ACCOUNT, ORG, or
# SIBLING PRODUCT?
#
# WHY THIS IS NOT THE IDENTITY GATE
# ---------------------------------
# Three hardcoded references were removed from the published surface on
# 2026-09-16 and the identity gates saw NONE of them:
#     flywheel/core.py        gargworks/nucleus-private, gargworks/gentlequest-app
#     growth_ops.py:37        eidetic-works/nucleus-mcp   (dead org)
#     marketing_engine.py:72  "Chief Strategy Officer for GentleQuest"
# None is a person's name, an email, or a /Users/ path, so every identity check
# read clean. This is a DIFFERENT CLASS: strings that link the package to an
# account, a dead org, or another product the operator ships. Orthogonal to
# identity; it needs its own gate.
#
# WHERE IT LOOKS
#   default        the PyPI include set derived from pyproject (what SHIPS)
#   <dir>          any tree — point it at an unpacked wheel/sdist to ask what
#                  is ALREADY PUBLIC, which the repo cannot tell you
#
# EXIT  0 clean   1 leak found   2 INSUFFICIENT (could not establish the check works)
set -u

TERMS_DEFAULT="gentlequest eidetic-works gargworks"
TERMS="${PRODUCT_LEAK_TERMS:-$TERMS_DEFAULT}"
CONTROL_DIR="${PRODUCT_LEAK_CONTROL:-}"

scan() {  # scan <dir-or-file> -> prints "file:line:text", one per line
  d="$1"
  for t in $TERMS; do
    grep -rIn -i -- "$t" "$d" 2>/dev/null \
      | grep -v '/__pycache__/' \
      | grep -v '\.pyc:' \
      | sed "s|^$d/||"
  done | sort -u
}

# ── Positive control ───────────────────────────────────────────────────────
# A scanner that reports clean is worthless until it has been shown to report
# dirty. The control is a REAL artifact that genuinely contains the terms — the
# published wheel, or a pre-fix commit — never a string this script writes
# itself. A planted control proves the grep runs; it does not prove the grep
# runs over the thing you care about.
if [ -z "$CONTROL_DIR" ]; then
  echo "INSUFFICIENT: no positive control supplied." >&2
  echo "  Set PRODUCT_LEAK_CONTROL to a tree known to contain the terms —" >&2
  echo "  an unpacked published wheel is the right choice; it is real and dated." >&2
  echo "  Without it a clean result here is unearned." >&2
  exit 2
fi
if [ ! -d "$CONTROL_DIR" ]; then
  echo "INSUFFICIENT: control dir does not exist: $CONTROL_DIR" >&2; exit 2
fi
CONTROL_HITS=$(scan "$CONTROL_DIR" | wc -l | tr -d ' ')
if [ "$CONTROL_HITS" -eq 0 ]; then
  echo "INSUFFICIENT: the positive control produced ZERO hits." >&2
  echo "  control: $CONTROL_DIR" >&2
  echo "  terms:   $TERMS" >&2
  echo "  The instrument cannot be shown to fire, so a clean scan of the target" >&2
  echo "  proves nothing. Fix the control before trusting any result." >&2
  exit 2
fi
echo "positive control: $CONTROL_HITS hit(s) in $CONTROL_DIR — instrument fires"

# ── Target ─────────────────────────────────────────────────────────────────
TARGET="${1:-}"
if [ -n "$TARGET" ]; then
  [ -d "$TARGET" ] || { echo "INSUFFICIENT: target is not a directory: $TARGET" >&2; exit 2; }
  echo "target: $TARGET (explicit tree)"
  SCAN_ROOTS="$TARGET"
else
  # Derive what actually ships from pyproject — never hardcode it here, or this
  # gate drifts away from the build the way the SOVEREIGN gate drifted away
  # from PyPI.
  ROOTS=$(python3 - <<'PYEOF'
import tomllib, sys, os
try:
    cfg = tomllib.load(open("pyproject.toml","rb"))
except Exception as e:
    print("ERROR:%s" % e); sys.exit(0)
t = cfg.get("tool",{}).get("hatch",{}).get("build",{}).get("targets",{})
roots=set(t.get("wheel",{}).get("packages",[]) or [])
roots|={r for r in (t.get("sdist",{}).get("only-include",[]) or []) if r != "."}
# force-include ships files from OUTSIDE the package dirs, and scanning only
# `packages` never sees them. Measured 2026-09-19: source read 7 leaks while the
# built wheel carried 12 -- the extra five were all in docs/QUICK_START.md,
# force-included into mcp_server_nucleus/docs/ and telling a new user to
# `git clone` and `docker pull` two dead URLs. A gate that scans a narrower set
# than the build produces is a gate that reads clean and ships dirty.
for src in (t.get("wheel",{}).get("force-include",{}) or {}):
    roots.add(os.path.normpath(src))
roots={os.path.normpath(r) for r in roots if os.path.isdir(r) or os.path.isfile(r)}
# Drop any root CONTAINED in another root. "src" and "src/mcp_server_nucleus"
# both appear in pyproject; scanning both counted every shared file twice and
# reported 82 where the truth was 43. An inflated leak count is still a wrong
# number, and a wrong number is what this whole gate exists to prevent.
roots={r for r in roots
       if not any(r != o and (r == o or r.startswith(o + os.sep)) for o in roots)}
print("\n".join(sorted(roots)) if roots else "ERROR:no include dirs")
PYEOF
)
  case "$ROOTS" in
    ERROR:*|"") echo "INSUFFICIENT: cannot derive the PyPI include set (${ROOTS:-empty})" >&2; exit 2 ;;
  esac
  echo "target: PyPI include set — $(echo "$ROOTS" | tr '\n' ' ')"
  SCAN_ROOTS="$ROOTS"
fi

HITS=""
for r in $SCAN_ROOTS; do
  out=$(scan "$r")
  [ -n "$out" ] && HITS="${HITS}${out}
"
done
HITS=$(printf '%s' "$HITS" | grep -v '^$' || true)
N=$(printf '%s' "$HITS" | grep -c . || true)

if [ "${N:-0}" -eq 0 ]; then
  echo "OK — no account, org, or sibling-product reference in the shipped surface."
  exit 0
fi
echo ""
echo "LEAK: $N reference(s) to an account, org, or sibling product:"
printf '%s\n' "$HITS" | sed 's/^/  /'
echo ""
echo "These do not trip the identity gates — none is a name, email, or path."
echo "Fix by parameterising (caller-supplied or env), not by deleting a module:"
echo "check for live importers first."
exit 1
