#!/bin/bash
# Phase 73 Installation Script
# Run this in both Windsurf and Antigravity to activate Phase 73 improvements

set -e

echo "🚀 Installing Phase 73 (99.9% Reliability Hardening)..."
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

# Reinstall in development mode
echo "📦 Reinstalling mcp-server-nucleus in development mode..."
python3 -m pip install -e . --quiet

# Verify installation
echo ""
echo "✅ Verifying Phase 73 modules..."

python3 << 'EOF'
try:
    from mcp_server_nucleus.runtime.llm_resilience import ResilientLLMClient
    from mcp_server_nucleus.runtime.environment_detector import EnvironmentDetector
    from mcp_server_nucleus.runtime.file_resilience import ResilientFileOps
    from mcp_server_nucleus.runtime.error_telemetry import ErrorTelemetry
    
    print("   ✅ ResilientLLMClient loaded")
    print("   ✅ EnvironmentDetector loaded")
    print("   ✅ ResilientFileOps loaded")
    print("   ✅ ErrorTelemetry loaded")
    
    # Test environment detection
    detector = EnvironmentDetector()
    print("")
    print("🔍 Environment Detection:")
    print(f"   OS: {detector.get_os()}")
    print(f"   MCP Host: {detector.get_mcp_host()}")
    print(f"   Brain Path: {detector.get_safe_brain_path()}")
    
    # Test error telemetry
    telemetry = ErrorTelemetry()
    stats = telemetry.get_stats()
    print("")
    print("📊 Error Telemetry:")
    print(f"   Total Errors: {stats['total_errors']}")
    print(f"   Status: Active")
    
    print("")
    print("✅ Phase 73 installation complete!")
    print("")
    print("📝 Next Steps:")
    print("   1. Restart your MCP server (Windsurf: Cmd+Shift+P → 'MCP: Restart Server')")
    print("   2. All Phase 71/72 modules now use Phase 73 resilience automatically")
    print("   3. Check docs/PHASE73_QUICK_START.md for usage examples")
    
except ImportError as e:
    print(f"❌ Installation failed: {e}")
    print("")
    print("Try running: pip install -e . --force-reinstall")
    exit(1)
EOF

echo ""
echo "🎉 Done! Phase 73 is ready to use."
