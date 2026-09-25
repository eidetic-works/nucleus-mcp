"""
Coverage tests for runtime/capabilities/memory_ops.py
"""
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities.memory_ops import MemoryOps


@pytest.fixture
def memory_ops(monkeypatch):
    """Create MemoryOps with mocked VectorStore."""
    with patch("mcp_server_nucleus.runtime.capabilities.memory_ops.VectorStore") as mock_vs_class:
        mock_vs = MagicMock()
        mock_vs_class.return_value = mock_vs
        ops = MemoryOps()
        return ops


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, memory_ops):
        assert memory_ops.name == "memory_ops"

    def test_description(self, memory_ops):
        assert "memory" in memory_ops.description.lower()


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_two_tools(self, memory_ops):
        tools = memory_ops.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_store_memory" in names
        assert "brain_search_memory" in names

    def test_store_memory_required(self, memory_ops):
        tools = memory_ops.get_tools()
        tool = [t for t in tools if t["name"] == "brain_store_memory"][0]
        assert tool["parameters"]["required"] == ["content"]

    def test_search_memory_required(self, memory_ops):
        tools = memory_ops.get_tools()
        tool = [t for t in tools if t["name"] == "brain_search_memory"][0]
        assert tool["parameters"]["required"] == ["query"]


# ---------------------------------------------------------------------------
# brain_store_memory
# ---------------------------------------------------------------------------
class TestStoreMemory:
    def test_store_success(self, memory_ops):
        memory_ops.vector_store.store_memory.return_value = "mem-123"
        result = memory_ops.execute_tool("brain_store_memory", {
            "content": "Remember this",
            "category": "learning",
            "source": "test",
            "tags": ["important"]
        })
        assert "mem-123" in result
        memory_ops.vector_store.store_memory.assert_called_once()
        call_args = memory_ops.vector_store.store_memory.call_args
        assert call_args.args[0] == "Remember this"
        assert call_args.args[1]["category"] == "learning"
        assert call_args.args[1]["source"] == "test"
        assert call_args.args[1]["tags"] == ["important"]

    def test_store_with_defaults(self, memory_ops):
        memory_ops.vector_store.store_memory.return_value = "mem-456"
        result = memory_ops.execute_tool("brain_store_memory", {"content": "Simple"})
        assert "mem-456" in result
        call_args = memory_ops.vector_store.store_memory.call_args
        assert call_args.args[1]["category"] == "general"
        assert call_args.args[1]["source"] == "agent"
        assert call_args.args[1]["tags"] == []

    def test_store_exception(self, memory_ops):
        memory_ops.vector_store.store_memory.side_effect = Exception("DB error")
        result = memory_ops.execute_tool("brain_store_memory", {"content": "test"})
        assert "Error" in result
        assert "DB error" in result


# ---------------------------------------------------------------------------
# brain_search_memory
# ---------------------------------------------------------------------------
class TestSearchMemory:
    def test_search_with_results(self, memory_ops):
        memory_ops.vector_store.search_memory.return_value = [
            {"content": "Found memory 1", "metadata": {"category": "learning"}},
            {"content": "Found memory 2", "metadata": {"category": "fact"}},
        ]
        result = memory_ops.execute_tool("brain_search_memory", {
            "query": "test query",
            "limit": 10
        })
        assert "Found memory 1" in result
        assert "Found memory 2" in result
        assert "[learning]" in result
        assert "[fact]" in result
        memory_ops.vector_store.search_memory.assert_called_once_with(query="test query", limit=10)

    def test_search_default_limit(self, memory_ops):
        memory_ops.vector_store.search_memory.return_value = []
        memory_ops.execute_tool("brain_search_memory", {"query": "test"})
        call_args = memory_ops.vector_store.search_memory.call_args
        assert call_args.kwargs["limit"] == 5

    def test_search_no_results(self, memory_ops):
        memory_ops.vector_store.search_memory.return_value = []
        result = memory_ops.execute_tool("brain_search_memory", {"query": "nothing"})
        assert "No matching memories" in result

    def test_search_with_no_metadata(self, memory_ops):
        memory_ops.vector_store.search_memory.return_value = [
            {"content": "No meta", "metadata": {}},
        ]
        result = memory_ops.execute_tool("brain_search_memory", {"query": "test"})
        assert "No meta" in result
        assert "[gen]" in result  # default category

    def test_search_with_none_metadata(self, memory_ops):
        """When metadata is None, the code raises an exception (caught by handler)."""
        memory_ops.vector_store.search_memory.return_value = [
            {"content": "None meta", "metadata": None},
        ]
        result = memory_ops.execute_tool("brain_search_memory", {"query": "test"})
        # None metadata causes AttributeError, caught by execute_tool's except
        assert "Error" in result

    def test_search_exception(self, memory_ops):
        memory_ops.vector_store.search_memory.side_effect = Exception("Search failed")
        result = memory_ops.execute_tool("brain_search_memory", {"query": "test"})
        assert "Error" in result
        assert "Search failed" in result


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------
class TestUnknownTool:
    def test_unknown_tool(self, memory_ops):
        result = memory_ops.execute_tool("nonexistent", {})
        assert "not found" in result


# ---------------------------------------------------------------------------
# Move 2 batch 5: SoR read-model repoint (flag-ON, STRICT)
# ---------------------------------------------------------------------------
class TestSearchMemoryFlagOn:
    """brain_search_memory routes through MemoryFacade.recall under the flag.

    STRICT: the assertions fail if the read falls back to the vector store
    instead of delegating to the facade — no `or True`.
    """

    def test_flag_on_routes_through_facade_not_vector_store(self, memory_ops, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
        # A facade whose recall returns a distinguishable hit the vector store
        # cannot produce (its search_memory is the mock and would return []).
        fake_facade = MagicMock()
        fake_facade.recall.return_value = [
            {"text": "facade-routed hit", "kind": "learning", "tags": "t1"},
        ]
        memory_ops.vector_store.search_memory.return_value = []
        monkeypatch.setattr(
            "mcp_server_nucleus.memory.facade.MemoryFacade",
            lambda *a, **k: fake_facade,
        )
        result = memory_ops.execute_tool("brain_search_memory", {"query": "q", "limit": 7})
        # STRICT: the facade hit is present ...
        assert "facade-routed hit" in result
        assert "[learning]" in result
        # ... recall was called with the caller's args ...
        fake_facade.recall.assert_called_once()
        assert fake_facade.recall.call_args.kwargs["limit"] == 7
        assert fake_facade.recall.call_args.kwargs["mode"] == "hybrid"
        # ... and the legacy vector-store read was NOT used under the flag.
        memory_ops.vector_store.search_memory.assert_not_called()

    def test_flag_off_uses_vector_store(self, memory_ops, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "")
        memory_ops.vector_store.search_memory.return_value = [
            {"content": "vector hit", "metadata": {"category": "fact"}},
        ]
        result = memory_ops.execute_tool("brain_search_memory", {"query": "q", "limit": 3})
        # STRICT: flag-OFF is byte-for-byte the legacy vector-store call.
        assert "vector hit" in result
        memory_ops.vector_store.search_memory.assert_called_once_with(query="q", limit=3)

    def test_flag_on_falls_back_to_vector_store_on_facade_error(self, memory_ops, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
        memory_ops.vector_store.search_memory.return_value = [
            {"content": "fallback hit", "metadata": {"category": "fact"}},
        ]

        def _boom(*a, **k):
            raise RuntimeError("SoR down")

        monkeypatch.setattr(
            "mcp_server_nucleus.memory.facade.MemoryFacade", _boom
        )
        result = memory_ops.execute_tool("brain_search_memory", {"query": "q"})
        # STRICT: a facade failure degrades to the legacy store (never worse).
        assert "fallback hit" in result
        memory_ops.vector_store.search_memory.assert_called_once()
