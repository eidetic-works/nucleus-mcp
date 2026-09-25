"""Tests for dogfood_math fixture."""

from tests.fixtures.dogfood_math import multiply

def test_multiply():
    """Verify that multiply function correctly calculates products."""
    assert multiply(2.0, 3.0) == 6.0
    assert multiply(-1.0, 5.0) == -5.0
    assert multiply(0.0, 100.0) == 0.0
