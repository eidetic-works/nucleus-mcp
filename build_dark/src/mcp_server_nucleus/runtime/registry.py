"""
RegistryClient: The Catalog Browser.
Fetches and searches the global directory of available Agents.

Strategic Role:
- DISCOVERY: Where do I find agents?
- TRUST: The Index is the first point of truth (though Verify Keymaster is final).
- VERSIONING: Knows what the "latest" version is.
"""

import json
import logging
import urllib.request
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger("REGISTRY")

class RegistryEntry(BaseModel):
    id: str
    name: str
    description: str
    latest_version: str
    repo_url: str
    tags: List[str] = []

class RegistryClient:
    def __init__(self, registry_url: str = "https://registry.nucleus.dev/index.json"):
        self.registry_url = registry_url
        self._cache: List[RegistryEntry] = []
        
    def fetch_index(self) -> List[RegistryEntry]:
        """Fetch the latest index from the remote registry."""
        logger.info(f"Fetching registry from {self.registry_url}...")
        
        try:
            with urllib.request.urlopen(self.registry_url) as response:
                data = json.loads(response.read().decode())
                
            entries = []
            for item in data.get("agents", []):
                entries.append(RegistryEntry(**item))
                
            self._cache = entries
            logger.info(f"✅ Fetched {len(entries)} agents.")
            return entries
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch registry: {e}")
            raise e

    def search(self, query: str) -> List[RegistryEntry]:
        """Search for agents by name, id, or tag."""
        if not self._cache:
            # Auto-fetch if empty? Or just return empty. 
            # In Phase 57 simulation, let's assume cache is primed or we try to prime.
            try:
                self.fetch_index()
            except Exception:
                pass
                
        query = query.lower()
        results = []
        
        for entry in self._cache:
            if (query in entry.name.lower() or 
                query in entry.id.lower() or 
                query in entry.description.lower() or
                any(query in tag.lower() for tag in entry.tags)):
                results.append(entry)
                
        return results

    def get_entry(self, agent_id: str) -> Optional[RegistryEntry]:
        """Get a specific agent entry."""
        if not self._cache:
            self.fetch_index()
            
        for entry in self._cache:
            if entry.id == agent_id:
                return entry
        return None
