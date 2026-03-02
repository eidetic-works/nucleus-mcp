
from typing import List, Dict, Any
from .base import Capability
from ..vector_store import VectorStore

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
