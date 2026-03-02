"""
Unit tests for Engram MCP tools (AG-021).

Tests brain_write_engram, brain_query_engrams, and brain_governance_status.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path


class TestEngramTools(unittest.TestCase):
    """Test the Engram Ledger MCP tools."""
    
    def setUp(self):
        """Create a temporary brain directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.temp_dir) / ".brain"
        self.brain_path.mkdir(parents=True)
        
        # Set environment variable instead of brittle patches
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)
    
    def tearDown(self):
        """Clean up temporary directory."""
        if "NUCLEAR_BRAIN_PATH" in os.environ:
            del os.environ["NUCLEAR_BRAIN_PATH"]
            
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_engram_creates_file(self):
        """Test that write_engram creates the engram ledger file."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        
        result = _brain_write_engram_impl(
            key="test_key",
            value="test_value",
            context="Architecture",
            intensity=8
        )
        
        result_data = json.loads(result)
        self.assertTrue(result_data["success"])
        
        # Verify file exists
        engram_path = self.brain_path / "engrams" / "ledger.jsonl"
        self.assertTrue(engram_path.exists())
        
        # Verify content
        with open(engram_path, "r") as f:
            engram = json.loads(f.readline())
            self.assertEqual(engram["key"], "test_key")
            self.assertEqual(engram["value"], "test_value")
            self.assertEqual(engram["context"], "Architecture")
            self.assertEqual(engram["intensity"], 8)
    
    def test_write_engram_validates_intensity(self):
        """Test that intensity must be 1-10."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        
        # Test invalid intensity
        result = _brain_write_engram_impl(
            key="test",
            value="test",
            context="Decision",
            intensity=15
        )
        
        result_data = json.loads(result)
        self.assertFalse(result_data["success"])
        self.assertIn("1 and 10", result_data["error"])
    
    def test_write_engram_validates_context(self):
        """Test that context must be valid category."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
        
        result = _brain_write_engram_impl(
            key="test",
            value="test",
            context="InvalidContext",
            intensity=5
        )
        
        result_data = json.loads(result)
        self.assertFalse(result_data["success"])
        self.assertIn("Context must be one of", result_data["error"])
    
    def test_query_engrams_returns_empty_when_no_file(self):
        """Test query returns empty list when no engrams exist."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl
        
        result = _brain_query_engrams_impl(context=None, min_intensity=1)
        result_data = json.loads(result)
        
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["data"]["count"], 0)
    
    def test_query_engrams_filters_by_context(self):
        """Test query filters by context category."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_query_engrams_impl
        
        # Write engrams with different contexts
        _brain_write_engram_impl("arch1", "this is architecture value 1", "Architecture", 8)
        _brain_write_engram_impl("brand1", "this is brand value 2", "Brand", 5)
        _brain_write_engram_impl("arch2", "this is architecture value 3", "Architecture", 6)
        
        # Query only Architecture
        result = _brain_query_engrams_impl(context="Architecture", min_intensity=1)
        result_data = json.loads(result)
        
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["data"]["count"], 2)
    
    def test_query_engrams_filters_by_intensity(self):
        """Test query filters by minimum intensity."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_query_engrams_impl
        
        # Write engrams with different intensities
        _brain_write_engram_impl("critical", "this is a critical decision 1", "Decision", 10)
        _brain_write_engram_impl("normal", "this is a normal decision 2", "Decision", 5)
        _brain_write_engram_impl("archive", "this is an archived decision 3", "Decision", 2)
        
        # Query only high intensity
        result = _brain_query_engrams_impl(context=None, min_intensity=8)
        result_data = json.loads(result)
        
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["data"]["count"], 1)
    
    def test_query_engrams_sorts_by_intensity(self):
        """Test that results are sorted by intensity (highest first)."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_query_engrams_impl
        
        # Write engrams in random order
        _brain_write_engram_impl("low", "low intensity value 1", "Decision", 3)
        _brain_write_engram_impl("high", "high intensity value 2", "Decision", 9)
        _brain_write_engram_impl("medium", "medium intensity value 3", "Decision", 6)
        
        # Query all
        result = _brain_query_engrams_impl(context=None, min_intensity=1)
        result_data = json.loads(result)
        
        engrams = result_data["data"]["engrams"]
        self.assertEqual(engrams[0]["intensity"], 9)
        self.assertEqual(engrams[1]["intensity"], 6)
        self.assertEqual(engrams[2]["intensity"], 3)
    
    def test_governance_status_returns_policies(self):
        """Test governance status returns policy information."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_governance_status_impl
        
        result = _brain_governance_status_impl()
        result_data = json.loads(result)
        
        self.assertTrue(result_data["success"])
        policies = result_data["data"]["policies"]
        self.assertTrue(policies["default_deny"])
        self.assertTrue(policies["isolation_boundaries"])
    
    def test_governance_status_counts_engrams(self):
        """Test governance status accurately counts engrams."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_governance_status_impl
        
        # Write some engrams
        _brain_write_engram_impl("e1", "this is governance value 1", "Decision", 5)
        _brain_write_engram_impl("e2", "this is governance value 2", "Decision", 5)
        
        result = _brain_governance_status_impl()
        result_data = json.loads(result)
        
        self.assertEqual(result_data["data"]["statistics"]["engram_count"], 2)


    def test_query_engrams_pagination_limit(self):
        """Test that query_engrams respects the limit parameter (D2/D24 fix)."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_query_engrams_impl

        # Write 5 engrams
        for i in range(5):
            _brain_write_engram_impl(f"page_{i}", f"pagination test value {i}", "Decision", 5 + i)

        # Query with limit=2
        result = _brain_query_engrams_impl(context=None, min_intensity=1, limit=2)
        result_data = json.loads(result)

        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["data"]["count"], 2)
        self.assertEqual(result_data["data"]["total_matching"], 5)
        self.assertTrue(result_data["data"]["truncated"])
        self.assertEqual(result_data["data"]["limit"], 2)
        # Highest intensity first
        self.assertEqual(result_data["data"]["engrams"][0]["intensity"], 9)

    def test_query_engrams_limit_clamped(self):
        """Test that limit is clamped to safe range [1, 500]."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_query_engrams_impl

        # Limit > 500 should be clamped
        result = _brain_query_engrams_impl(context=None, min_intensity=1, limit=9999)
        result_data = json.loads(result)
        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["data"]["limit"], 500)

        # Limit < 1 should be clamped
        result = _brain_query_engrams_impl(context=None, min_intensity=1, limit=0)
        result_data = json.loads(result)
        self.assertEqual(result_data["data"]["limit"], 1)

    def test_query_engrams_no_truncation_when_within_limit(self):
        """Test truncated=False when results fit within limit."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_query_engrams_impl

        _brain_write_engram_impl("only_one", "single engram value", "Strategy", 7)

        result = _brain_query_engrams_impl(context=None, min_intensity=1, limit=50)
        result_data = json.loads(result)

        self.assertEqual(result_data["data"]["count"], 1)
        self.assertFalse(result_data["data"]["truncated"])


    def test_search_engrams_pagination_limit(self):
        """Test that search_engrams respects the limit parameter (Pillar 1.2)."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_search_engrams_impl

        for i in range(5):
            _brain_write_engram_impl(f"searchable_{i}", f"findme pagination test {i}", "Decision", 5 + i)

        result = _brain_search_engrams_impl(query="findme", limit=2)
        result_data = json.loads(result)

        self.assertTrue(result_data["success"])
        self.assertEqual(result_data["data"]["count"], 2)
        self.assertEqual(result_data["data"]["total_matching"], 5)
        self.assertTrue(result_data["data"]["truncated"])
        self.assertEqual(result_data["data"]["limit"], 2)
        self.assertEqual(result_data["data"]["engrams"][0]["intensity"], 9)

    def test_search_engrams_limit_clamped(self):
        """Test search_engrams limit clamping [1, 500]."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl

        result = json.loads(_brain_search_engrams_impl(query="x", limit=9999))
        self.assertEqual(result["data"]["limit"], 500)

        result = json.loads(_brain_search_engrams_impl(query="x", limit=0))
        self.assertEqual(result["data"]["limit"], 1)

    def test_search_engrams_no_truncation(self):
        """Test search_engrams truncated=False when within limit."""
        from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl, _brain_search_engrams_impl

        _brain_write_engram_impl("unique_needle", "unique_needle_value", "Strategy", 7)

        result = json.loads(_brain_search_engrams_impl(query="unique_needle", limit=50))
        self.assertEqual(result["data"]["count"], 1)
        self.assertFalse(result["data"]["truncated"])


if __name__ == "__main__":
    unittest.main()
