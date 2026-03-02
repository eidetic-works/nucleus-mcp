#!/bin/bash
# Nucleus PyPI Publishing Script
# Usage: ./scripts/publish_pypi.sh [--test]
#
# Prerequisites:
# 1. pip install build twine
# 2. PyPI account with API token
# 3. ~/.pypirc configured OR TWINE_USERNAME/TWINE_PASSWORD env vars

set -e

echo "============================================================"
echo "🚀 NUCLEUS PYPI PUBLISHING SCRIPT"
echo "============================================================"

# Configuration
PACKAGE_NAME="nucleus-mcp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check for test mode
if [[ "$1" == "--test" ]]; then
    PYPI_REPO="testpypi"
    PYPI_URL="https://test.pypi.org/simple/"
    echo "📦 Mode: TEST PyPI"
else
    PYPI_REPO="pypi"
    PYPI_URL="https://pypi.org/simple/"
    echo "📦 Mode: PRODUCTION PyPI"
fi

echo ""

# Step 1: Pre-flight checks
echo "[1/6] Pre-flight Checks..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

if ! python3 -c "import build" &> /dev/null; then
    echo "❌ 'build' module not found. Run: pip install build"
    exit 1
fi

if ! command -v twine &> /dev/null; then
    echo "❌ 'twine' not found. Run: pip install twine"
    exit 1
fi

echo "  ✅ All dependencies available"

# Step 2: Run tests
echo ""
echo "[2/6] Running Tests..."

PYTHONPATH=src python3 -m unittest discover -s tests -q
if [[ $? -ne 0 ]]; then
    echo "❌ Tests failed. Aborting publish."
    exit 1
fi
echo "  ✅ All tests passed"

# Step 3: Run smoke test
echo ""
echo "[3/6] Running Smoke Test..."

PYTHONPATH=src python3 scripts/smoke_test_130.py > /dev/null 2>&1
if [[ $? -ne 0 ]]; then
    echo "❌ Smoke test failed. Aborting publish."
    exit 1
fi
echo "  ✅ Smoke test passed (130 tools)"

# Step 4: Clean previous builds
echo ""
echo "[4/6] Cleaning Previous Builds..."

rm -rf dist/ build/ *.egg-info
echo "  ✅ Cleaned"

# Step 5: Build package
echo ""
echo "[5/6] Building Package..."

python3 -m build

# Verify build artifacts
if [[ ! -f dist/*.whl ]]; then
    echo "❌ Wheel not created"
    exit 1
fi

WHEEL_FILE=$(ls dist/*.whl)
WHEEL_SIZE=$(du -h "$WHEEL_FILE" | cut -f1)
echo "  ✅ Built: $WHEEL_FILE ($WHEEL_SIZE)"

# Step 6: Upload to PyPI
echo ""
echo "[6/6] Uploading to PyPI..."

if [[ "$PYPI_REPO" == "testpypi" ]]; then
    twine upload --repository testpypi dist/*
else
    twine upload dist/*
fi

echo ""
echo "============================================================"
echo "✅ PUBLISH COMPLETE"
echo "============================================================"
echo ""
echo "Package: $PACKAGE_NAME"
echo "Wheel: $WHEEL_FILE"
echo "Size: $WHEEL_SIZE"
echo ""

if [[ "$PYPI_REPO" == "testpypi" ]]; then
    echo "Test install:"
    echo "  pip install -i https://test.pypi.org/simple/ $PACKAGE_NAME"
else
    echo "Install:"
    echo "  pip install $PACKAGE_NAME"
    echo ""
    echo "View on PyPI:"
    echo "  https://pypi.org/project/$PACKAGE_NAME/"
fi

echo ""
