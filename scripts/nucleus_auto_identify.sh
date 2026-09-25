#!/usr/bin/env bash
# =============================================================================
# nucleus_auto_identify.sh — Substrate auto-identify hook
# =============================================================================
# Source this file in your shell profile (.bashrc / .zshrc) to automatically
# register your agent identity with the Nucleus substrate whenever an MCP
# session starts.
#
# Usage — add ONE of the following to your shell profile:
#
#   # Option A: source directly (always-on, any interactive shell):
#   source /path/to/nucleus_auto_identify.sh
#
#   # Option B: only when NUCLEUS_BRAIN_PATH is set:
#   [[ -n "$NUCLEUS_BRAIN_PATH" ]] && source /path/to/nucleus_auto_identify.sh
#
# Environment variables (all optional — sensible defaults apply):
#   NUCLEUS_SESSION_ROLE     — role to advertise (default: auto-detected)
#   NUCLEUS_SESSION_PROVIDER — provider/IDE name  (default: auto-detected)
#   NUCLEUS_BRAIN_PATH       — path to .brain dir (default: .brain in cwd/home)
#   NUCLEUS_AUTO_IDENTIFY    — set to "0" to suppress auto-identify
# =============================================================================

# Guard: honour opt-out
if [[ "${NUCLEUS_AUTO_IDENTIFY:-1}" == "0" ]]; then
    return 0 2>/dev/null || exit 0
fi

# Guard: only run in interactive shells or when MCP_TRANSPORT=stdio is set
# (the latter covers the daemon/server case where stdin is not a tty)
if [[ ! -t 0 && "${MCP_TRANSPORT:-}" != "stdio" ]]; then
    return 0 2>/dev/null || exit 0
fi

# ── Helper: find python3 executable ──────────────────────────────────────────
_nucleus_python() {
    # Prefer project venv, then active venv, then PATH
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
    local project_root="${here}/.."
    local venv_py="${project_root}/.venv/bin/python3"

    if [[ -x "$venv_py" ]]; then
        echo "$venv_py"
    elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python3" ]]; then
        echo "${VIRTUAL_ENV}/bin/python3"
    else
        command -v python3 2>/dev/null || echo ""
    fi
}

# ── Helper: detect provider from process environment ─────────────────────────
_nucleus_detect_provider() {
    if [[ -n "${ANTIGRAVITY_SESSION:-}" ]]; then echo "antigravity"; return; fi
    if [[ -n "${WINDSURF_SESSION:-}" ]];    then echo "windsurf";    return; fi
    if [[ -n "${CURSOR_SESSION:-}" ]];      then echo "cursor";      return; fi
    if [[ -n "${GEMINI_CLI:-}" ]];          then echo "gemini";      return; fi
    if [[ -n "${CLAUDE_CODE:-}" || -n "${CLAUDE_CODE_SESSION:-}" ]]; then
        echo "claude_code"; return
    fi
    echo "unknown"
}

# ── Helper: detect role ───────────────────────────────────────────────────────
_nucleus_detect_role() {
    if [[ -n "${NUCLEUS_SESSION_ROLE:-}" ]]; then
        echo "${NUCLEUS_SESSION_ROLE}"
        return
    fi
    # Infer from provider
    local provider
    provider="$(_nucleus_detect_provider)"
    case "$provider" in
        antigravity) echo "worker" ;;
        windsurf)    echo "worker" ;;
        cursor)      echo "worker" ;;
        gemini*)     echo "worker" ;;
        claude_code) echo "primary" ;;
        *)           echo "unknown" ;;
    esac
}

# ── Main auto-identify logic ──────────────────────────────────────────────────
_nucleus_auto_identify() {
    local python
    python="$(_nucleus_python)"
    if [[ -z "$python" ]]; then
        # Python not found — silently skip
        return 0
    fi

    local role provider session_id
    role="$(_nucleus_detect_role)"
    provider="${NUCLEUS_SESSION_PROVIDER:-$(_nucleus_detect_provider)}"
    session_id="${NUCLEUS_SESSION_ID:-$(uname -n)_$$_$(date +%s)}"

    # Emit identify_agent via Python one-liner so we don't need the CLI installed
    "$python" - <<PYEOF 2>/dev/null
import sys, json, os
try:
    # Ensure the source tree is importable if running from checkout
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath("${BASH_SOURCE[0]:-$0}")), ".."))
    from mcp_server_nucleus.runtime.sync_ops import set_current_agent
    result = set_current_agent(
        agent_id=None,
        environment="shell",
        role="${role}",
        provider="${provider}",
        session_id="${session_id}",
    )
    # Also emit the event so the substrate ledger picks it up
    try:
        from mcp_server_nucleus.runtime.event_ops import emit_event
        emit_event("AGENT_REGISTERED", result.get("agent_id", "unknown"), result,
                   "Auto-identified via nucleus_auto_identify.sh")
    except Exception:
        pass
except ImportError:
    # Package not installed — no-op
    pass
except Exception as exc:
    # Best-effort: never crash the shell
    print(f"[nucleus] auto-identify skipped: {exc}", file=sys.stderr)
PYEOF

    # Print a brief confirmation (suppress in non-interactive shells)
    if [[ -t 1 ]]; then
        echo "[nucleus] 🧠 auto-identified: role=${role} provider=${provider} session=${session_id}"
    fi
}

# Run at source time (shell startup)
_nucleus_auto_identify

# ── Optional: export a convenience alias so agents can re-identify manually ──
alias nucleus-identify='_nucleus_auto_identify'
