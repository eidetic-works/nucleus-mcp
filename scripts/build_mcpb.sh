#!/usr/bin/env bash
# Build .mcpb extension for Claude Desktop
# Usage: bash scripts/build_mcpb.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
EXT_DIR="$ROOT/extensions/claude-desktop"
DIST_DIR="$ROOT/dist"

VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('$ROOT/pyproject.toml','rb'))['project']['version'])" 2>/dev/null || echo "1.8.0")

mkdir -p "$DIST_DIR"

# Update version in manifest
sed "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$EXT_DIR/manifest.json" > "$EXT_DIR/manifest.tmp.json"
mv "$EXT_DIR/manifest.tmp.json" "$EXT_DIR/manifest.json"

# Build .mcpb (ZIP with manifest)
cd "$EXT_DIR"
zip -j "$DIST_DIR/nucleus.mcpb" manifest.json

echo "Built: $DIST_DIR/nucleus.mcpb (v$VERSION)"
echo "Upload to GitHub Releases as an asset."
