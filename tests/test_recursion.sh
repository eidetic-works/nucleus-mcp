#!/bin/bash
# test_recursion.sh: Verify NUCLEUS_MAX_DEPTH guardrail.

echo "🧪 Running Recursion Depth Guardrail Test..."

# 1. Setup Environment
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"
export NUCLEUS_BRAIN_PATH="$REPO_ROOT/.brain_test"
export NUCLEUS_MAX_DEPTH=1

mkdir -p "$NUCLEUS_BRAIN_PATH"

echo "   [1] Starting Root Coordinator (Depth 0 -> 1)..."
# We simulate a "dead loop" by asking the coordinator to run a task that 
# triggered a depth push. Since max is 1, a second push should fail.

# Use a task that will trigger an internal depth push if it can
# Actually, the coordinator pushes depth at the START of watch_gemini_output
python3 -m mcp_server_nucleus.cli run coordinator --task "Root Task" --quiet

# Now, try to run a nested one in the same shell (simulating a sub-process)
export NUCLEUS_CURRENT_DEPTH=1
echo "   [2] Verification: Attempting sub-coordinator (Depth 1 -> 2 | MAX=1)..."
OUTPUT=$(python3 -m mcp_server_nucleus.cli run coordinator --task "Sub Task" --quiet 2>&1)

if echo "$OUTPUT" | grep -q "DEPTH BUDGET EXHAUSTED"; then
    echo "   ✅ Sub-coordinator correctly blocked by guardrail."
    echo "🎉 Recursion Guardrail Test: PASSED"
    exit 0
else
    echo "❌ Failed: Sub-coordinator was NOT blocked. Output:"
    echo "$OUTPUT"
    exit 1
fi
