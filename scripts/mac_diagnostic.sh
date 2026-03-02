#!/bin/bash
# Nucleus v1.0.9 Mac Diagnostic Script
# Use this to verify your local installation is ready for E2E testing.

echo "🔍 Checking Nucleus Installation..."
if [ -d "/path/to/your/project/nucleus-mcp" ]; then
    echo "✅ Release Repo found: /path/to/your/project/nucleus-mcp"
else
    echo "❌ Release Repo NOT found. Check sync status."
    exit 1
fi

echo "🔍 Checking Python Environment..."
python3 -c "import mcp_server_nucleus; print(f'✅ Found Nucleus Package: {mcp_server_nucleus.__version__}')" 2>/dev/null || echo "❌ Nucleus package not in global path."

echo "🔍 Validating Stdio Server Registration..."
# Test if nucleus_curl is visible in the tool list (Tier 0)
export NUCLEUS_TOOL_TIER=0
export FASTMCP_SHOW_CLI_BANNER=False
python3 -m mcp_server_nucleus --status 2>/dev/null | grep -q "nucleus_curl" && echo "✅ nucleus_curl registered in Tier 0" || echo "❌ nucleus_curl NOT registered."

echo "🚀 Diagnostics Complete. If all green, proceed to test in Claude Desktop/Windsurf."
