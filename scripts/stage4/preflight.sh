#!/usr/bin/env bash
set -uo pipefail
NUCLEUS_URL="${NUCLEUS_URL:-https://brain.nucleusos.dev}"
VM_IP="${VM_IP:-}"
NUCLEUS_TOKEN="${NUCLEUS_TOKEN:-}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$HOME/ai-mvp-backend/scripts/sync_brain_from_oci.sh}"
SSH_USER="${SSH_USER:-ubuntu}"
SSH_TIMEOUT="${SSH_TIMEOUT:-5}"
CURL_TIMEOUT="${CURL_TIMEOUT:-10}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

gate1_vm_running() {
    [[ -z "$VM_IP" ]] && { echo "[FAIL] Gate 1: VM_IP env var not set"; return 1; }
    if ssh -o ConnectTimeout=$SSH_TIMEOUT -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" 'systemctl is-active nucleus-http' >/dev/null 2>&1; then
        echo "[PASS] Gate 1: VM running (nucleus-http active)"
        return 0
    fi
    echo "[FAIL] Gate 1: VM not reachable or nucleus-http not active"
    return 1
}

gate2_webhook_reachable() {
    local url="$NUCLEUS_URL/health"
    local resp
    resp=$(curl -sf --max-time "$CURL_TIMEOUT" "$url" 2>&1) || {
        echo "[FAIL] Gate 2: webhook not reachable at $url"
        return 1
    }
    [[ "$resp" == *"version"* ]] && echo "[PASS] Gate 2: webhook reachable (version: ${resp:0:40})" || echo "[PASS] Gate 2: webhook reachable"
    return 0
}

gate3_smoke_passes() {
    [[ -z "$NUCLEUS_TOKEN" ]] && { echo "[FAIL] Gate 3: NUCLEUS_TOKEN env var not set"; return 1; }
    local smoke_sh="$REPO_ROOT/mcp-server-nucleus/deploy/oci/smoke.sh"
    [[ ! -x "$smoke_sh" ]] && smoke_sh="$REPO_ROOT/deploy/oci/smoke.sh"
    [[ ! -x "$smoke_sh" ]] && { echo "[FAIL] Gate 3: smoke.sh not found at deploy/oci/smoke.sh"; return 1; }
    local out
    out=$(NUCLEUS_URL="$NUCLEUS_URL" NUCLEUS_TOKEN="$NUCLEUS_TOKEN" "$smoke_sh" 2>&1) || {
        echo "[FAIL] Gate 3: smoke.sh returned non-zero"
        echo "  output: ${out:0:200}"
        return 1
    }
    [[ "$out" == *"PASS"* ]] && [[ "$out" != *"FAIL 0"* ]] || [[ "$out" == *"PASS"* ]] && {
        echo "[PASS] Gate 3: smoke.sh passes"
        return 0
    }
    echo "[FAIL] Gate 3: smoke.sh did not report PASS"
    echo "  output: ${out:0:200}"
    return 1
}

gate4_sync_back_primed() {
    if [[ -f "$HOME/oci-retry/SUCCEEDED" ]]; then
        echo "[PASS] Gate 4: sync-back primed (~/oci-retry/SUCCEEDED exists)"
        return 0
    fi
    if [[ -x "$SYNC_SCRIPT" ]]; then
        echo "[PASS] Gate 4: sync-back primed ($SYNC_SCRIPT executable)"
        return 0
    fi
    echo "[FAIL] Gate 4: sync-back not primed (no ~/oci-retry/SUCCEEDED, $SYNC_SCRIPT missing or not executable)"
    return 1
}

gate5_token_issued() {
    local gen_token="$REPO_ROOT/mcp-server-nucleus/scripts/gen_relay_token.py"
    [[ ! -f "$gen_token" ]] && gen_token="$REPO_ROOT/scripts/gen_relay_token.py"
    [[ ! -f "$gen_token" ]] && { echo "[FAIL] Gate 5: gen_relay_token.py not found"; return 1; }
    local out
    out=$(python3 "$gen_token" --check perplexity 2>&1) || {
        echo "[FAIL] Gate 5: perplexity token not issued or --check failed"
        echo "  output: ${out:0:200}"
        return 1
    }
    echo "[PASS] Gate 5: perplexity token issued"
    return 0
}

main() {
    echo "=== Stage-4 Preflight ==="
    echo "NUCLEUS_URL: $NUCLEUS_URL"
    echo "VM_IP: ${VM_IP:-<not set>}"
    echo ""
    gate1_vm_running || exit 1
    gate2_webhook_reachable || exit 2
    gate3_smoke_passes || exit 3
    gate4_sync_back_primed || exit 4
    gate5_token_issued || exit 5
    echo ""
    echo "PRECHECK PASS — all 5 gates clear"
    exit 0
}

main "$@"
