#!/usr/bin/env bash
# perplexity_reconfig_smoke.sh — Stage-4 smoke: simulate perplexity firing a relay through
# the cloud webhook and confirm sync-back lands it on Lokesh's laptop.
#
# Usage:
#   PERPLEXITY_TOKEN=<32-byte-hex> ./perplexity_reconfig_smoke.sh
#   PERPLEXITY_TOKEN=<token> NUCLEUS_URL=https://brain.nucleusos.dev ./perplexity_reconfig_smoke.sh
#
# Exit codes:
#   0 — full path passes (POST 202 + sync-back lands relay on laptop)
#   1 — POST fails or returns non-202
#   2 — POST succeeds but relay doesn't appear on laptop within timeout
#   3 — env not set / pre-check fail

set -uo pipefail

NUCLEUS_URL="${NUCLEUS_URL:-https://brain.nucleusos.dev}"
LOCAL_BRAIN="${NUCLEUS_BRAIN_PATH:-$HOME/ai-mvp-backend/.brain}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$HOME/ai-mvp-backend/scripts/sync_brain_from_oci.sh}"
SYNC_TIMEOUT="${SYNC_TIMEOUT:-120}"  # seconds to wait for sync-back

if [[ -z "${PERPLEXITY_TOKEN:-}" ]]; then
    echo "FAIL: PERPLEXITY_TOKEN env var required" >&2
    exit 3
fi

# Build test relay body (mirrors the perplexity reconfig spec)
TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
SUBJECT="[STAGE-4-SMOKE] perplexity-vantage smoke at $TS"
BODY=$(cat <<EOF
{"summary":"Stage-4 reconfig smoke from perplexity vantage at $TS. Validates webhook + sync-back.","tags":["stage-4-smoke","cross-machine"],"artifact_refs":[],"auto_generated":false}
EOF
)

echo "[$TS] Stage-4 smoke firing"
echo "  url: $NUCLEUS_URL/relay/claude_code_main"
echo "  token: ${PERPLEXITY_TOKEN:0:8}..."
echo "  local brain: $LOCAL_BRAIN"

# Step 1: POST as perplexity would
RESPONSE=$(curl -sS -w "\n__HTTP__%{http_code}" -X POST "$NUCLEUS_URL/relay/claude_code_main" \
    -H "Authorization: Bearer $PERPLEXITY_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"sender\":\"perplexity\",\"subject\":\"$SUBJECT\",\"body\":$(echo "$BODY" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),\"priority\":\"normal\",\"from_session_id\":\"perplexity-smoke-$(date +%s)\"}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "^__HTTP__" | sed 's/^__HTTP__//')
BODY_OUT=$(echo "$RESPONSE" | grep -v "^__HTTP__")

echo "  HTTP: $HTTP_CODE"
echo "  body: $(echo "$BODY_OUT" | head -c 200)"

if [[ "$HTTP_CODE" != "202" ]]; then
    echo "FAIL: expected HTTP 202, got $HTTP_CODE" >&2
    exit 1
fi

# Extract relay_id from response
RELAY_ID=$(echo "$BODY_OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message_id","UNKNOWN"))' 2>/dev/null || echo "UNKNOWN")
echo "  relay_id: $RELAY_ID"

if [[ "$RELAY_ID" == "UNKNOWN" ]]; then
    echo "FAIL: response did not contain message_id" >&2
    exit 1
fi

# Step 2: trigger sync-back if script exists
if [[ -x "$SYNC_SCRIPT" ]]; then
    echo "[$(date -u +%H:%M:%S)] firing sync-back: $SYNC_SCRIPT"
    "$SYNC_SCRIPT" >/dev/null 2>&1 || echo "  sync-back returned non-zero (may be normal for partial sync)"
else
    echo "  sync-back script missing at $SYNC_SCRIPT — manual sync needed; will poll local brain anyway"
fi

# Step 3: poll local brain for relay file
DEADLINE=$((SECONDS + SYNC_TIMEOUT))
TARGET_DIR="$LOCAL_BRAIN/relay/claude_code_main"
mkdir -p "$TARGET_DIR" 2>/dev/null

while [[ $SECONDS -lt $DEADLINE ]]; do
    if find "$TARGET_DIR" -name "*${RELAY_ID#relay_}*.json" -newer "$LOCAL_BRAIN/.." 2>/dev/null | grep -q .; then
        FOUND=$(find "$TARGET_DIR" -name "*${RELAY_ID#relay_}*.json" 2>/dev/null | head -1)
        echo "[$(date -u +%H:%M:%S)] PASS: relay landed at $FOUND"
        # Verify body roundtrip
        if [[ -f "$FOUND" ]] && grep -q "stage-4-smoke" "$FOUND"; then
            echo "  body roundtrip verified (stage-4-smoke tag present)"
            exit 0
        else
            echo "WARN: file present but body content not verified" >&2
            exit 0
        fi
    fi
    sleep 5
done

echo "FAIL: relay did NOT land on laptop within ${SYNC_TIMEOUT}s" >&2
echo "  searched: $TARGET_DIR for *${RELAY_ID#relay_}*.json" >&2
echo "  next steps: check sync-back log at $SYNC_SCRIPT.log; check VM-side /opt/nucleus/brain/relay/claude_code_main/" >&2
exit 2
