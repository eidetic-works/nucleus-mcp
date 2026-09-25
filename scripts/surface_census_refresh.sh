#!/usr/bin/env bash
# Twice-weekly Nucleus surface census refresh.
#
# Two stages, deliberately split by cost:
#   1. surface_census.py counts. Deterministic, no model, no tokens.
#   2. A FREE vendor lane (devin/glm-5.2 via the local shim) writes the short
#      "what changed since last time" note. $0 — the shim serves the
#      nucleus/<vendor>-<model> namespace and never proxies to Anthropic.
#
# Stage 2 is optional by construction: if the shim is down the report still
# lands with its table intact and an explicit note saying interpretation was
# skipped. A refresher that silently produces nothing when a dependency is
# missing is the failure this whole codebase keeps paying for.
#
# Install (twice weekly, Mon + Thu, off the :00 mark):
#   13 7 * * 1,4  /bin/bash <repo>/mcp-server-nucleus/scripts/surface_census_refresh.sh
set -uo pipefail

REPO="${NUCLEUS_REPO:-$HOME/ai-mvp-backend}"
BRAIN="${NUCLEUS_BRAIN_PATH:-$REPO/.brain}"
OUT_DIR="$BRAIN/reports"
OUT="$OUT_DIR/surface_census.md"
PREV="$OUT_DIR/surface_census.prev.md"
LOG="$OUT_DIR/surface_census.log"
SHIM="${NUCLEUS_SHIM_URL:-http://127.0.0.1:8787}"
MODEL="${NUCLEUS_SHIM_MODEL:-nucleus/devin-glm-5.2}"

mkdir -p "$OUT_DIR"
exec >>"$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') census refresh ==="

[ -f "$OUT" ] && cp "$OUT" "$PREV"

# Stage 1 — count. Exit 2 means the census found no evidence anywhere, which is
# a broken instrument, not an idle system. Keep the previous report rather than
# overwriting a good table with an empty one.
python3 "$REPO/mcp-server-nucleus/scripts/surface_census.py" --days 14 --out "$OUT" >/dev/null
rc=$?
if [ "$rc" -eq 2 ]; then
    echo "NO EVIDENCE (exit 2) — census is broken, keeping previous report"
    [ -f "$PREV" ] && cp "$PREV" "$OUT"
    exit 2
elif [ "$rc" -ne 0 ]; then
    echo "census failed rc=$rc — keeping previous report"
    [ -f "$PREV" ] && cp "$PREV" "$OUT"
    exit "$rc"
fi
echo "census written: $OUT"

# Stage 2 — free-lane interpretation. Never fatal.
if ! curl -sf -m 10 -o /dev/null "$SHIM/v1/messages" -X POST \
        -H 'content-type: application/json' \
        -d '{"model":"'"$MODEL"'","max_tokens":8,"messages":[{"role":"user","content":"ping"}]}'; then
    echo "shim unreachable at $SHIM — interpretation SKIPPED"
    printf '\n> Interpretation skipped: free vendor lane unreachable at %s. Table above is still current.\n' "$SHIM" >> "$OUT"
    exit 0
fi

python3 - "$OUT" "$PREV" "$MODEL" "$SHIM" <<'PY'
import json, sys, urllib.request

out_p, prev_p, model, shim = sys.argv[1:5]
cur = open(out_p).read()
try:
    prev = open(prev_p).read()
except OSError:
    prev = "(no previous report — this is the first run)"

prompt = (
    "You are reading two Nucleus surface-usage census reports. Write at most 6 lines on what "
    "CHANGED and what it implies. Be concrete and cite numbers.\n\n"
    "Rules:\n"
    "- A surface marked 'enforced' is called because a hook blocks the agent until it is. "
    "Never describe enforced volume as demand.\n"
    "- If a surface dropped to zero, say so plainly — that is the most important thing you can "
    "report, and it usually means something broke rather than fell out of favour.\n"
    "- If nothing meaningful changed, say 'No material change.' Do not manufacture insight.\n\n"
    f"=== PREVIOUS ===\n{prev[:6000]}\n\n=== CURRENT ===\n{cur[:6000]}\n"
)
req = urllib.request.Request(
    f"{shim}/v1/messages",
    data=json.dumps({"model": model, "max_tokens": 500,
                     "messages": [{"role": "user", "content": prompt}]}).encode(),
    headers={"content-type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.load(r)
    note = "".join(b.get("text", "") for b in d.get("content", [])).strip()
    usage = d.get("usage", {})
except Exception as e:
    note, usage = "", {}
    print(f"interpretation failed: {e}")

with open(out_p, "a") as f:
    if note:
        f.write(f"\n---\n\n## What changed\n\n{note}\n\n"
                f"<sub>Free lane `{model}` · {usage.get('output_tokens', '?')} output tokens · $0</sub>\n")
    else:
        f.write("\n> Interpretation skipped: free lane returned nothing. Table above is still current.\n")
print("interpretation appended" if note else "interpretation empty")
PY

echo "done"
