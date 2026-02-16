"""
Search tests for Nucleus MCP - Updated for v1.0.5 API

Note: The current API queries by context and min_intensity, not by keyword.
"""

import json
import os
import tempfile

import pytest
from mcp_server_nucleus import _brain_query_engrams_impl, _brain_write_engram_impl


@pytest.fixture
def temp_brain():
    """Create a temporary brain directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
        yield tmpdir
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)


@pytest.fixture
def sample_engrams(temp_brain):
    """Create sample engrams for testing."""
    engrams = [
        ("db_choice", "PostgreSQL for ACID compliance", "Architecture", 8),
        ("api_key", "SECRET_KEY_12345", "Decision", 5),
        ("design_pattern", "Use factory pattern", "Architecture", 6),
    ]
    for key, value, context, intensity in engrams:
        _brain_write_engram_impl(key, value, context, intensity)
    return engrams


def test_brain_query_by_context(temp_brain, sample_engrams):
    """Test querying engrams by context."""
    
    # Query Architecture context
    res_str = _brain_query_engrams_impl(context="Architecture", min_intensity=1)
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 2  # db_choice and design_pattern
    
    # Query Decision context
    res_str = _brain_query_engrams_impl(context="Decision", min_intensity=1)
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 1  # api_key


def test_brain_query_by_intensity(temp_brain, sample_engrams):
    """Test filtering engrams by minimum intensity."""
    
    # High intensity only
    res_str = _brain_query_engrams_impl(context="Architecture", min_intensity=7)
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 1  # only db_choice has intensity 8


def test_brain_query_all(temp_brain, sample_engrams):
    """Test querying all engrams (no context filter)."""
    
    res_str = _brain_query_engrams_impl(context=None, min_intensity=1)
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 3  # all engrams
