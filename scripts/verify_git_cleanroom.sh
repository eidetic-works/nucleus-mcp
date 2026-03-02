#!/bin/bash
# verify_git_cleanroom.sh
# Simulates a first-time clone/fork experience in a clean directory.

set -e

SOURCE_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR=$(mktemp -d -t nucleus_git_verify_XXXX)

echo "🚀 Created Git cleanroom: $TEMP_DIR"

cleanup() {
    echo "🧹 Cleaning up: $TEMP_DIR"
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

cd "$TEMP_DIR"

# 1. Clone the repo (Local clone to save time)
echo "📦 Cloning repository..."
git clone "$SOURCE_REPO" nucleus-mcp > /dev/null
cd nucleus-mcp

# 2. Verify .gitattributes exists
echo "🔍 Checking for .gitattributes..."
if [ -f ".gitattributes" ]; then
    echo "  ✅ .gitattributes found"
else
    echo "  ❌ .gitattributes missing"
    exit 1
fi

# 3. Verify line endings (LF enforcement)
# We can check a file with 'file' command or 'cat -A' on linux, but 'git check-attr' is more accurate.
echo "🔍 Verifying LF enforcement..."
ATTR=$(git check-attr eol src/mcp_server_nucleus/runtime/stdio_server.py)
if [[ "$ATTR" == *"eol: lf"* ]]; then
    echo "  ✅ LF line endings enforced"
else
    echo "  ❌ Line ending enforcement failed (Expected LF)"
    exit 1
fi

# 4. Verify bootstrap script existence
echo "🔍 Checking for bootstrap scripts..."
if [ -f "scripts/bootstrap_node_beta.ps1" ]; then
    echo "  ✅ bootstrap_node_beta.ps1 found"
else
    echo "  ❌ bootstrap_node_beta.ps1 missing"
    exit 1
fi

echo -e "\n✨ Nucleus Git Cleanroom Verified Successfully! ✨"
