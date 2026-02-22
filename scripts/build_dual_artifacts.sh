#!/bin/bash
# =============================================================================
# DUAL ARTIFACT BUILD SCRIPT
# =============================================================================
# The Dark Wheel Protocol - Physical Separation
#
# Artifact A (Dark Wheel): Full source + Poison Pill → Private Index
# Artifact B (Public Decoy): Tier 0 only, logic stripped → PyPI
#
# Usage:
#   ./scripts/build_dual_artifacts.sh
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "🌑 THE DARK WHEEL PROTOCOL - Dual Artifact Build"
echo "============================================================"
echo ""
echo "Project: $PROJECT_ROOT"
echo ""

# Check dependencies
echo "[PRE-FLIGHT] Checking dependencies..."
python3 -c "import build" 2>/dev/null || pip install build
echo "✅ Dependencies OK"
echo ""

# Build Dark Wheel first (full source)
echo "============================================================"
echo "PHASE 1: Building Dark Wheel (Full Source)"
echo "============================================================"
python3 "$SCRIPT_DIR/build_dark_wheel.py"

echo ""
echo "============================================================"
echo "PHASE 2: Building Public Decoy (Tier 0 Only)"
echo "============================================================"
python3 "$SCRIPT_DIR/build_public_decoy.py"

echo ""
echo "============================================================"
echo "🛡️  FINAL SECURITY AUDIT"
echo "============================================================"

# Dark Wheel verification
echo ""
echo "🌑 Dark Wheel (must contain logic):"
DARK_WHEEL=$(ls "$PROJECT_ROOT/dist/dark/"*.whl 2>/dev/null | head -1)
if [ -n "$DARK_WHEEL" ]; then
    echo "    File: $(basename "$DARK_WHEEL")"
    echo "    Size: $(du -h "$DARK_WHEEL" | cut -f1)"
    echo "    Federation: $(unzip -l "$DARK_WHEEL" | grep -c federation.py || echo 0) files"
    echo "    Autopilot: $(unzip -l "$DARK_WHEEL" | grep -c autopilot.py || echo 0) files"
fi

# Public Decoy verification
echo ""
echo "☀️  Public Decoy (must NOT contain logic):"
PUBLIC_WHEEL=$(ls "$PROJECT_ROOT/dist/public/"*.whl 2>/dev/null | head -1)
if [ -n "$PUBLIC_WHEEL" ]; then
    echo "    File: $(basename "$PUBLIC_WHEEL")"
    echo "    Size: $(du -h "$PUBLIC_WHEEL" | cut -f1)"
    
    # CRITICAL CHECK
    FEDERATION_CHECK=$(unzip -l "$PUBLIC_WHEEL" 2>/dev/null | grep "federation.py" | awk '{print $1}' | head -1)
    if [ -n "$FEDERATION_CHECK" ] && [ "$FEDERATION_CHECK" -gt 500 ]; then
        echo ""
        echo "    ❌❌❌ CRITICAL: federation.py is $FEDERATION_CHECK bytes ❌❌❌"
        echo "    🛑 DO NOT UPLOAD TO PYPI"
        exit 1
    else
        echo "    ✅ Federation: STRIPPED or STUBBED"
    fi
fi

echo ""
echo "============================================================"
echo "📦 BUILD ARTIFACTS"
echo "============================================================"
echo ""
echo "🌑 DARK WHEEL (Private Beta):"
echo "    Location: dist/dark/"
echo "    Upload:   twine upload --repository-url https://pypi.nucleusos.dev/simple/ dist/dark/*.whl"
echo ""
echo "☀️  PUBLIC DECOY (PyPI):"
echo "    Location: dist/public/"
echo "    Upload:   twine upload dist/public/*.whl"
echo ""
echo "⚠️  PARANOIA PROTOCOL - Run before PyPI upload:"
echo "    unzip -l dist/public/*.whl | grep -E 'federation|autopilot|orchestrator'"
echo "    (Must show small stub files only, not real logic)"
echo ""
echo "============================================================"
echo "✅ DUAL ARTIFACT BUILD COMPLETE"
echo "============================================================"
