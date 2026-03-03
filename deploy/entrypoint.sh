#!/bin/bash
# ============================================================
# Nucleus Sovereign Agent OS — Container Entrypoint
# ============================================================
# Auto-applies jurisdiction configuration on first boot,
# then executes the requested nucleus command.
# ============================================================
set -e

# Auto-apply jurisdiction if set and not already configured
if [ -n "$NUCLEUS_JURISDICTION" ] && [ ! -f /app/.brain/governance/compliance.json ]; then
    echo "[Nucleus] Applying jurisdiction: $NUCLEUS_JURISDICTION"
    nucleus comply --jurisdiction "$NUCLEUS_JURISDICTION" --brain /app/.brain 2>/dev/null || true
fi

# Execute the requested command
exec nucleus "$@"
