"""Tests for dogfood_util.py."""

from tests.fixtures.dogfood_util import add_numbers


def test_add_numbers():
    """Verify that add_numbers(2, 3) == 5."""
    assert add_numbers(2, 3) == 5
