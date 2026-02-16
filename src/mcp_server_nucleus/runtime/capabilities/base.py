from abc import ABC, abstractmethod
from typing import List, Dict, Any

class Capability(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the capability cluster (e.g., 'render_ops')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description for the Context Factory."""
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of MCP tool definitions."""
        pass
