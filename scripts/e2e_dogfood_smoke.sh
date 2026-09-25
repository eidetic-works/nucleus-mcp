#!/usr/bin/env bash
# e2e_dogfood_smoke.sh — Criterion 9 substrate liveness check
#
# Verifies the Nucleus substrate end-to-end without requiring an active LLM
# session. Covers:
#   1. Eidetic daemon reachable (TCP 9876) and healthy
#   2. Engram write → search round-trip (insert_engram → query_engrams FTS)
#   3. Relay pipeline: write test relay → verify inbox visibility → cleanup
#
# NOTE: The LLM synthesis step (criterion 9's "Max-OAuth path") is inherently
# session-bound and cannot run in a standalone script. This script validates
# substrate health; the synthesis step is verified during active CC sessions
# via dogfood posture (feedback_cc_main_eidetic_dogfood_posture.md).
#
# Exit codes:
#   0 = all substrate checks pass
#   1 = one or more checks failed (details logged to stderr)
#
# Failure routing: if NUCLEUS_BRAIN_PATH is set and the relay inbox exists,
# a failure notification is written to the operator inbox.
#
# Usage:
#   bash scripts/e2e_dogfood_smoke.sh
#   EIDETIC_TCP=1 bash scripts/e2e_dogfood_smoke.sh   # explicit TCP mode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BRAIN_PATH="${NUCLEUS_BRAIN_PATH:-$HOME/.brain}"
RELAY_INBOX="$BRAIN_PATH/relay/claude_code_main"
EIDETIC_TCP="${EIDETIC_TCP:-1}"
EIDETIC_HOST="${EIDETIC_HOST:-127.0.0.1}"
EIDETIC_PORT="${EIDETIC_PORT:-9876}"

FAILURES=0
TEST_SURFACE="nucleus_smoke_test"
TEST_PAYLOAD="e2e_smoke_$(date +%s)_probe"
TEST_RELAY_ID=""

log()  { echo "[smoke] $*"; }
err()  { echo "[smoke] FAIL: $*" >&2; FAILURES=$((FAILURES + 1)); }
pass() { echo "[smoke] PASS: $*"; }

# ── Check 1: Daemon TCP endpoint reachable ───────────────────────────────────
log "Check 1: eidetic daemon TCP at $EIDETIC_HOST:$EIDETIC_PORT"
if ! python3 -c "
import socket, sys
s = socket.socket()
s.settimeout(3)
try:
    s.connect(('$EIDETIC_HOST', $EIDETIC_PORT))
    s.close()
    sys.exit(0)
except Exception as e:
    print(f'  connection refused: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
    err "daemon not reachable at $EIDETIC_HOST:$EIDETIC_PORT — run: launchctl kickstart -k gui/\$(id -u)/works.eidetic.eideticd"
    DAEMON_UP=0
else
    pass "daemon TCP reachable"
    DAEMON_UP=1
fi

# ── Check 2: Daemon API /engrams endpoint responds ───────────────────────────
if [ "$DAEMON_UP" = "1" ]; then
    log "Check 2: GET /engrams?limit=1"
    ENGRAMS_OUT=$(python3 -c "
import http.client, json, sys
try:
    conn = http.client.HTTPConnection('$EIDETIC_HOST', $EIDETIC_PORT, timeout=5)
    conn.request('GET', '/engrams?limit=1')
    r = conn.getresponse()
    body = r.read().decode()
    if r.status == 200:
        d = json.loads(body)
        print(f'ok status=200 count={len(d)}')
        sys.exit(0)
    else:
        print(f'bad status={r.status} body={body[:80]}', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
    if echo "$ENGRAMS_OUT" | grep -q "^ok"; then
        pass "GET /engrams: $ENGRAMS_OUT"
    else
        err "GET /engrams failed: $ENGRAMS_OUT"
    fi
else
    log "Check 2: SKIPPED (daemon not reachable)"
fi

# ── Check 3: Write engram + FTS search round-trip ───────────────────────────
if [ "$DAEMON_UP" = "1" ]; then
    log "Check 3: insert_engram + search_engrams round-trip (FTS)"
    ROUNDTRIP=$(python3 - <<'PYEOF'
import sys, os, http.client
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "eidetic-daemon/bridge/python"))
os.environ["EIDETIC_TCP"] = "1"
try:
    from eidetic_mcp.client import DaemonClient, DaemonError
    client = DaemonClient()

    # Insert
    eid = client.insert_engram(surface="SMOKE_TEST_SURFACE", payload="e2e_nucleus_smoke_token_xyzzy")
    if not eid:
        print("error: insert returned empty id", file=sys.stderr)
        sys.exit(1)

    # Search — returns Engram dataclass objects; check snippet field
    rows = client.search_engrams(q="e2e_nucleus_smoke_token_xyzzy", surface="SMOKE_TEST_SURFACE", limit=5)
    found = any("e2e_nucleus_smoke_token_xyzzy" in str(getattr(r, "snippet", "") + getattr(r, "payload", "")) for r in rows)

    # Cleanup: DELETE /engrams/<id>
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 9876, timeout=5)
        conn.request("DELETE", f"/engrams/{eid}")
        conn.getresponse()
    except Exception:
        pass  # cleanup is best-effort

    if found:
        print(f"ok engram_id={eid} fts_hit=true")
        sys.exit(0)
    else:
        print(f"error: engram {eid} inserted but not found by FTS", file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)
    if echo "$ROUNDTRIP" | grep -q "^ok"; then
        pass "Engram write+search: $ROUNDTRIP"
    else
        err "Engram round-trip failed: $ROUNDTRIP"
    fi
else
    log "Check 3: SKIPPED (daemon not reachable)"
fi

# ── Check 4: Relay pipeline — write + verify visibility ─────────────────────
log "Check 4: relay write → inbox visibility (brain path: $BRAIN_PATH)"
if [ -d "$RELAY_INBOX" ]; then
    TEST_RELAY_TS=$(date -u +%Y%m%dT%H%M%SZ)
    TEST_RELAY_FILE="$RELAY_INBOX/${TEST_RELAY_TS}_smoke_e2e_probe.json"
    RELAY_PAYLOAD="{\"schema\":\"relay/v1\",\"id\":\"smoke-$TEST_RELAY_TS\",\"ts\":\"$TEST_RELAY_TS\",\"from\":\"e2e_smoke\",\"to\":\"claude_code_main\",\"subject\":\"[SMOKE] e2e probe\",\"body\":{\"probe\":true}}"
    echo "$RELAY_PAYLOAD" > "$TEST_RELAY_FILE"
    if [ -f "$TEST_RELAY_FILE" ]; then
        pass "Relay write: $TEST_RELAY_FILE exists"
        # Verify readback
        READ_BACK=$(cat "$TEST_RELAY_FILE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))")
        if [ "$READ_BACK" = "smoke-$TEST_RELAY_TS" ]; then
            pass "Relay readback: id=$READ_BACK"
        else
            err "Relay readback: expected smoke-$TEST_RELAY_TS got $READ_BACK"
        fi
        # Cleanup
        rm -f "$TEST_RELAY_FILE"
    else
        err "Relay write: file not created at $TEST_RELAY_FILE"
    fi
else
    log "Check 4: relay inbox dir not found at $RELAY_INBOX — skipping (brain not configured)"
fi

# ── Check 5: Instrumentation channel writable ────────────────────────────────
log "Check 5: instrumentation channel writable"
INSTRUMENT_DIR="${INSTRUMENT_DIR:-$HOME/.brain/instrumentation}"
mkdir -p "$INSTRUMENT_DIR"
INSTRUMENT_FILE="$INSTRUMENT_DIR/$(date -u +%Y%m%d).jsonl"
TEST_LINE="{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"tool\":\"smoke_probe\",\"server\":\"smoke\",\"ms\":0}"
echo "$TEST_LINE" >> "$INSTRUMENT_FILE"
LAST=$(tail -1 "$INSTRUMENT_FILE")
if echo "$LAST" | grep -q "smoke_probe"; then
    pass "Instrumentation channel: wrote + verified $INSTRUMENT_FILE"
    # Remove the test line
    python3 -c "
import sys
lines = open('$INSTRUMENT_FILE').readlines()
open('$INSTRUMENT_FILE', 'w').writelines([l for l in lines if 'smoke_probe' not in l])
"
else
    err "Instrumentation channel: write+readback failed"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
if [ "$FAILURES" -eq 0 ]; then
    log "ALL CHECKS PASSED — Nucleus substrate healthy"
    exit 0
else
    FAIL_MSG="e2e_dogfood_smoke: $FAILURES check(s) failed — see stderr for details"
    err "$FAIL_MSG"

    # Route failure notification to operator inbox if relay path is available
    if [ -d "$RELAY_INBOX" ]; then
        FAIL_TS=$(date -u +%Y%m%dT%H%M%SZ)
        FAIL_RELAY="$RELAY_INBOX/${FAIL_TS}_smoke_FAILURE_$(hostname -s).json"
        cat > "$FAIL_RELAY" <<RELAY_EOF
{
  "schema": "relay/v1",
  "id": "smoke-fail-${FAIL_TS}",
  "ts": "${FAIL_TS}",
  "from": "e2e_dogfood_smoke",
  "to": "claude_code_main",
  "subject": "[GATE-RED] e2e_dogfood_smoke: ${FAILURES} substrate check(s) failed",
  "priority": "high",
  "body": {
    "failures": ${FAILURES},
    "run_at": "${FAIL_TS}",
    "action": "Check docs/runbooks/primitives_server_c.md §2 (daemon) or §1 (deploy) for debug steps"
  }
}
RELAY_EOF
        log "Failure notification written to $FAIL_RELAY"
    fi

    exit 1
fi
