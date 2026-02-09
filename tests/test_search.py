
import json
from mcp_server_nucleus import _brain_query_engrams_impl

def test_brain_query_with_search(temp_brain, sample_engrams):
    """Test that searching by keyword works in brain_query_engrams."""
    
    # Search by key
    res_str = _brain_query_engrams_impl(query="db")
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 1
    assert res["data"]["engrams"][0]["key"] == "db_choice"
    
    # Search by value
    res_str = _brain_query_engrams_impl(query="SECRET")
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 1
    assert res["data"]["engrams"][0]["key"] == "api_key"
    
    # Case insensitive
    res_str = _brain_query_engrams_impl(query="postgres")
    res = json.loads(res_str)
    assert res["success"] is True
    assert res["data"]["count"] == 1
    
    # No results
    res_str = _brain_query_engrams_impl(query="nonexistent")
    res = json.loads(res_str)
    assert res["data"]["count"] == 0
