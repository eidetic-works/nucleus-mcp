"""
Nucleus Test Suite — conftest.py
================================
Global test configuration to prevent hanging and ensure fixture isolation.

Added by Antigravity Opus to fix the full-suite hang (1191 tests).
Root cause: resource contention makes some tests excessively slow when
run together, causing the suite to appear "hung". Timeout prevents this.
"""
import os
import pytest


# ──────────────────────────────────────────────────────────────
# Global timeout: No single test should take more than 30 seconds
# ──────────────────────────────────────────────────────────────
def pytest_collection_modifyitems(items):
    """Apply a 30-second timeout to every test that doesn't have one."""
    for item in items:
        if not any(marker.name == "timeout" for marker in item.iter_markers()):
            item.add_marker(pytest.mark.timeout(30))


# ──────────────────────────────────────────────────────────────
# Ensure NUCLEAR_BRAIN_PATH is set for tests that need it
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _ensure_brain_path(tmp_path):
    """Set a temporary brain path for tests if one isn't configured."""
    original = os.environ.get("NUCLEAR_BRAIN_PATH")
    if not original:
        test_brain = tmp_path / ".brain"
        test_brain.mkdir(exist_ok=True)
        (test_brain / "ledger").mkdir(exist_ok=True)
        (test_brain / "engrams").mkdir(exist_ok=True)
        (test_brain / "sessions").mkdir(exist_ok=True)
        (test_brain / "memory").mkdir(exist_ok=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(test_brain)
    yield
    # Restore original
    if original is None:
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    else:
        os.environ["NUCLEAR_BRAIN_PATH"] = original
