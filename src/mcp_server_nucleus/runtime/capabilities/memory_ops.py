
from typing import List, Dict, Any
from .base import Capability
from ..vector_store import VectorStore, _sor_flag_on

class MemoryOps(Capability):
    """Capability for Long-term Memory Access (RAG)"""
    
    def __init__(self):
        self.vector_store = VectorStore()
    
    @property
    def name(self) -> str:
        return "memory_ops"

    @property
    def description(self) -> str:
        return "Tools for accessing and searching long-term memory (RAG)."
        
    def get_tools(self) -> List[Dict]:
        return [
            {
                "name": "brain_store_memory",
                "description": "Store a text chunk in long-term memory with metadata.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The text content to remember"},
                        "category": {"type": "string", "description": "Category (e.g., learning, preference, fact)"},
                        "source": {"type": "string", "description": "Source of info (e.g., session_id, user)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "brain_search_memory",
                "description": "Semantic search for relevant memories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results (default 5)"}
                    },
                    "required": ["query"]
                }
            }
        ]

    def _search_via_facade(self, query: str, limit: int) -> List[Dict]:
        """Route brain_search_memory through the unified SoR (Move 2 batch 5,
        flag-ON). Returns rows in the ``{content, metadata}`` shape the formatter
        expects. Fault-isolated → falls back to the legacy vector store on any
        SoR read failure so recall never regresses versus flag-OFF."""
        try:
            from mcp_server_nucleus.memory.facade import MemoryFacade

            facade = MemoryFacade(enabled=True)
            hits = facade.recall(query=query or "", limit=limit, mode="hybrid")
        except Exception:
            return self.vector_store.search_memory(query=query, limit=limit)
        out: List[Dict] = []
        for h in hits:
            meta = {"category": h.get("kind") or "gen"}
            if h.get("tags"):
                meta["tags"] = h.get("tags")
            out.append({"content": h.get("text"), "metadata": meta})
        return out

    def execute_tool(self, tool_name: str, args: Dict) -> Any:
        try:
            if tool_name == "brain_store_memory":
                metadata = {
                    "category": args.get("category", "general"),
                    "source": args.get("source", "agent"),
                    "tags": args.get("tags", [])
                }
                doc_id = self.vector_store.store_memory(args["content"], metadata)
                return f"Stored memory: {doc_id}"
                
            elif tool_name == "brain_search_memory":
                # Move 2 batch 5: flag-OFF (default) is the byte-for-byte legacy
                # vector-store read; flag-ON routes the read through the unified
                # SoR (MemoryFacade.recall, hybrid), degrading gracefully to the
                # legacy vector store on any SoR read failure.
                if _sor_flag_on():
                    results = self._search_via_facade(
                        args["query"], args.get("limit", 5)
                    )
                else:
                    results = self.vector_store.search_memory(
                        query=args["query"],
                        limit=args.get("limit", 5)
                    )
                if not results:
                    return "No matching memories found."
                
                # Format for LLM consumption
                formatted = []
                for r in results:
                    meta = r.get("metadata", {})
                    formatted.append(f"- [{meta.get('category', 'gen')}] {r['content']}")
                
                return "\n".join(formatted)

            return f"Tool {tool_name} not found"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
