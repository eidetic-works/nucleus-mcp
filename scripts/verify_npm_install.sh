#!/bin/bash
# verify_npm_install.sh
# Verifies the NPM installation of nucleus-mcp in a cleanroom.

set -e

SOURCE=${1:-"."} # Can be "." for local, or "nucleus-mcp" for registry
TEMP_DIR=$(mktemp -d -t nucleus_npm_verify_XXXX)

echo "🚀 Created NPM cleanroom: $TEMP_DIR"

cleanup() {
    echo "🧹 Cleaning up: $TEMP_DIR"
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

cd "$TEMP_DIR"

# 1. Initialize npm
echo "📦 Initializing npm project..."
npm init -y > /dev/null

# 2. Install package
echo "📦 Installing from $SOURCE..."
if [[ "$SOURCE" == "." ]]; then
    # Install from the actual project directory
    npm install "$(cd -P "$OLDPWD" && pwd)" > /dev/null
else
    npm install "$SOURCE" > /dev/null
fi

# 3. Verify availability
echo "🔍 Verifying command availability..."
if npx nucleus-mcp --help > /dev/null 2>&1; then
    echo "✅ NPM binary verified via npx"
else
    echo "❌ NPM binary verification failed"
    exit 1
fi

echo -e "\n✨ Nucleus NPM Installation Verified Successfully! ✨"
