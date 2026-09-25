#!/usr/bin/env bash
# install_client_permissions.sh — write nucleus MCP permissions to all
# detected agent client configs so nucleus works out of the box.
#
# When a user installs nucleus MCP, this script:
#   1. Detects which agent CLIs are installed (Claude Code, agy, Devin)
#   2. Writes the full nucleus tool permission set to each client's config
#   3. Adds shell commands needed for task execution (git, pytest, etc.)
#
# This is the "out of the box" experience — no manual permission editing.
#
# Usage:
#   bash scripts/install_client_permissions.sh [--dry-run]
#
# Exit codes:
#   0 = success (or dry-run completed)
#   1 = no agent clients detected
set -e

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# Full nucleus MCP tool surface — all agents get all tools
NUCLEUS_TOOLS_CC=(
  "mcp(nucleus/nucleus_sync)"
  "mcp(nucleus/nucleus_engrams)"
  "mcp(nucleus/nucleus_tasks)"
  "mcp(nucleus/nucleus_next_message)"
  "mcp(nucleus/nucleus_relay_subscribe)"
  "mcp(nucleus/nucleus_ccr_arm)"
  "mcp(nucleus/nucleus_features)"
  "mcp(nucleus/nucleus_sessions)"
  "mcp(nucleus/nucleus_governance)"
)

# Devin uses mcp__ prefix instead of mcp() syntax
NUCLEUS_TOOLS_DEVIN=(
  "mcp__nucleus__nucleus_sync"
  "mcp__nucleus__nucleus_engrams"
  "mcp__nucleus__nucleus_tasks"
  "mcp__nucleus__nucleus_next_message"
  "mcp__nucleus__nucleus_relay_subscribe"
  "mcp__nucleus__nucleus_ccr_arm"
  "mcp__nucleus__nucleus_features"
  "mcp__nucleus__nucleus_sessions"
  "mcp__nucleus__nucleus_governance"
)

# Shell commands needed for task execution (gating, committing, testing)
SHELL_COMMANDS=(
  "command(git)"
  "command(gh)"
  "command(pytest)"
  "command(python3)"
  "command(uv)"
  "command(bash)"
  "command(grep)"
  "command(rg)"
  "command(cat)"
  "command(ls)"
  "command(cd)"
  "command(find)"
  "command(tail)"
  "command(head)"
  "command(which)"
  "command(mkdir)"
  "command(cp)"
  "command(mv)"
  "command(echo)"
  "command(touch)"
  "command(wc)"
  "command(sort)"
  "command(diff)"
)

UPDATED=0

# ─── agy (Antigravity CLI) ───────────────────────────────────────────────
AGY_CONFIG="${HOME}/.gemini/antigravity-cli/settings.json"
if [[ -f "$AGY_CONFIG" ]]; then
  echo "[install] agy detected: $AGY_CONFIG"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  (dry-run) would add ${#NUCLEUS_TOOLS_CC[@]} MCP tools + ${#SHELL_COMMANDS[@]} commands"
    UPDATED=$((UPDATED + 1))
  else
    python3 - "$AGY_CONFIG" "${NUCLEUS_TOOLS_CC[@]}" "${SHELL_COMMANDS[@]}" <<'PYEOF'
import json, sys, os

config_path = sys.argv[1]
new_perms = sys.argv[2:]

with open(config_path) as f:
    config = json.load(f)

allow = config.setdefault("permissions", {}).setdefault("allow", [])
added = 0
for perm in new_perms:
    if perm not in allow:
        allow.append(perm)
        added += 1

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print(f"  added {added} permissions ({len(allow)} total)")
PYEOF
    UPDATED=$((UPDATED + 1))
  fi
fi

# ─── Devin CLI ───────────────────────────────────────────────────────────
DEVIN_CONFIG="${HOME}/.config/devin/config.json"
if [[ -f "$DEVIN_CONFIG" ]]; then
  echo "[install] Devin detected: $DEVIN_CONFIG"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  (dry-run) would add ${#NUCLEUS_TOOLS_DEVIN[@]} MCP tools"
    UPDATED=$((UPDATED + 1))
  else
    python3 - "$DEVIN_CONFIG" "${NUCLEUS_TOOLS_DEVIN[@]}" <<'PYEOF'
import json, sys

config_path = sys.argv[1]
new_perms = sys.argv[2:]

with open(config_path) as f:
    config = json.load(f)

allow = config.setdefault("permissions", {}).setdefault("allow", [])
added = 0
for perm in new_perms:
    if perm not in allow:
        allow.append(perm)
        added += 1

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print(f"  added {added} permissions ({len(allow)} total)")
PYEOF
    UPDATED=$((UPDATED + 1))
  fi
fi

# ─── Claude Code (project-level) ─────────────────────────────────────────
CC_CONFIG="${HOME}/.claude/settings.json"
if [[ -f "$CC_CONFIG" ]]; then
  echo "[install] Claude Code (user) detected: $CC_CONFIG"
  # Claude Code already has hooks — just ensure nucleus tools are allowed
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  (dry-run) would verify ${#NUCLEUS_TOOLS_CC[@]} MCP tools"
    UPDATED=$((UPDATED + 1))
  else
    python3 - "$CC_CONFIG" "${NUCLEUS_TOOLS_CC[@]}" <<'PYEOF'
import json, sys

config_path = sys.argv[1]
new_perms = sys.argv[2:]

with open(config_path) as f:
    config = json.load(f)

allow = config.setdefault("permissions", {}).setdefault("allow", [])
added = 0
for perm in new_perms:
    if perm not in allow:
        allow.append(perm)
        added += 1

if added > 0:
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print(f"  added {added} permissions ({len(allow)} total)")
else:
    print(f"  already has all nucleus tools ({len(allow)} total)")
PYEOF
    UPDATED=$((UPDATED + 1))
  fi
fi

# ─── Summary ─────────────────────────────────────────────────────────────
echo ""
if [[ $UPDATED -eq 0 ]]; then
  echo "[install] No agent clients detected. Install agy, Devin, or Claude Code first."
  exit 1
elif [[ $DRY_RUN -eq 1 ]]; then
  echo "[install] Dry-run complete. $UPDATED client(s) would be updated."
else
  echo "[install] Done. $UPDATED client(s) updated. Restart agents to load new permissions."
fi
exit 0
