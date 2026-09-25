#!/bin/bash
# Wrapper around agent_os_healthcheck.py for launchd invocation.
#
# launchd runs jobs outside any interactive shell -- no PATH from .zshrc, no
# venv activation, no inherited env. This wrapper hard-codes absolute paths
# to the repo's own venv python3 (confirmed to resolve curl_cffi and
# mcp_server_nucleus without activation) so the job is correct regardless of
# what environment launchd starts it in.
#
# Behavior:
#   - Runs the health check once.
#   - On PASS: appends one compact line to $LOG_FILE, clears any stale
#     failure marker.
#   - On FAIL: appends one compact FAIL line to $LOG_FILE AND writes/
#     overwrites $FAIL_MARKER with timestamp + full check output -- the
#     "surface it somewhere the operator will actually see it" requirement.
#     A marker file's mtime is trivially checkable (`ls -la`) without
#     reading the whole log.
#   - $LOG_FILE is capped at ~1MB via tail-truncation (crude rotation, no
#     external dependency) so it can never grow unbounded.
#
# Exit code passes through from the underlying health check.

set -uo pipefail

# Resolve the repo root from this script's own location rather than
# hard-coding a checkout path -- portable across machines/usernames, and
# correct regardless of launchd's cwd (which this script does not rely on).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PY="$REPO_ROOT/.venv/bin/python3"
SCRIPT="$REPO_ROOT/mcp-server-nucleus/scripts/agent_os_healthcheck.py"
LOG_DIR="$HOME/.nucleus/agent_os_healthcheck"
LOG_FILE="$LOG_DIR/healthcheck.log"
FAIL_MARKER="$LOG_DIR/LAST_FAILURE.txt"
MAX_LOG_BYTES=$((1024 * 1024))  # 1MB cap, crude tail-truncation rotation

mkdir -p "$LOG_DIR"

TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
OUTPUT="$("$PY" "$SCRIPT" 2>&1)"
EXIT_CODE=$?

# One compact per-check summary line, e.g. "A: Keychain credential=PASS;B: quota probe=PASS;C: test suite=PASS;"
CHECKS_SUMMARY="$(printf '%s\n' "$OUTPUT" | grep -E '✓ PASS|✗ FAIL' | sed -E 's/^ *\[(✓ PASS|✗ FAIL)\] (.+)$/\2=\1/' | sed -E 's/=✓ PASS/=PASS/; s/=✗ FAIL/=FAIL/' | tr '\n' ';')"

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "$TS PASS $CHECKS_SUMMARY" >> "$LOG_FILE"
    rm -f "$FAIL_MARKER"
else
    echo "$TS FAIL $CHECKS_SUMMARY" >> "$LOG_FILE"
    {
        echo "Agent OS health check FAILED"
        echo "timestamp: $TS"
        echo "exit_code: $EXIT_CODE"
        echo "---- full check output ----"
        printf '%s\n' "$OUTPUT"
    } > "$FAIL_MARKER"
fi

# Crude size-cap "rotation": if the log has grown past MAX_LOG_BYTES, keep
# only the most recent MAX_LOG_BYTES of it.
if [ -f "$LOG_FILE" ]; then
    SIZE="$(wc -c < "$LOG_FILE" | tr -d ' ')"
    if [ "$SIZE" -gt "$MAX_LOG_BYTES" ]; then
        tail -c "$MAX_LOG_BYTES" "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
fi

exit "$EXIT_CODE"
