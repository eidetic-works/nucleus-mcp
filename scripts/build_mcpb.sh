#!/usr/bin/env bash
# Build the one-click .mcpb bundle for Claude Desktop.
#
# The bundle is a uv-runtime MCPB (manifest_version 0.4): a tiny launcher that
# tells Claude Desktop's uv to install the published `nucleus-mcp` wheel from
# PyPI and run it. No product source or compiled deps are bundled — the wheel
# is the single source of truth, so the artifact stays ~KB and never drifts.
#
# Usage: bash scripts/build_mcpb.sh
# Requires: npx (bundled with Node) to fetch the official `@anthropic-ai/mcpb`
#           CLI, which validates the manifest and packs the bundle.
#
# The bundle is staged into a temp dir before the version is stamped, so this
# script never mutates the tracked source files.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
EXT_DIR="$ROOT/extensions/claude-desktop"
DIST_DIR="$ROOT/dist"

# Single source of truth for the version: the project's pyproject.toml.
VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('$ROOT/pyproject.toml','rb'))['project']['version'])")

mkdir -p "$DIST_DIR"

# Stage the bundle into a temp dir so version-stamping never touches tracked files.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$EXT_DIR/." "$STAGE/"

# Stamp the release version into the staged manifest + pyproject.
python3 - "$STAGE/manifest.json" "$STAGE/pyproject.toml" "$VERSION" <<'PY'
import json, re, sys
manifest_path, pyproject_path, version = sys.argv[1], sys.argv[2], sys.argv[3]

with open(manifest_path) as f:
    manifest = json.load(f)
manifest["version"] = version
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write("\n")

with open(pyproject_path) as f:
    text = f.read()
text = re.sub(r'(?m)^version = ".*"$', f'version = "{version}"', text, count=1)
with open(pyproject_path, "w") as f:
    f.write(text)
PY

# Validate the manifest against the official schema, then pack.
npx -y @anthropic-ai/mcpb@2.1.2 validate "$STAGE/manifest.json"
npx -y @anthropic-ai/mcpb@2.1.2 pack "$STAGE" "$DIST_DIR/nucleus.mcpb"

echo ""
echo "Built: $DIST_DIR/nucleus.mcpb (v$VERSION)"
echo "Inspect with: npx -y @anthropic-ai/mcpb@2.1.2 info $DIST_DIR/nucleus.mcpb"
echo "Ship by uploading nucleus.mcpb as a GitHub Release asset; users double-click to install."
