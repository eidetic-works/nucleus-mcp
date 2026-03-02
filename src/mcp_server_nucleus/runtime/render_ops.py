
import os
import json
import logging
from typing import Dict, List, Any
import urllib.request
import urllib.error

# Configure logger
logger = logging.getLogger("nucleus.render")

class RenderOps:
    """Operations for Render.com API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("RENDER_API_KEY")
        self.base_url = "https://api.render.com/v1"
        
    @property
    def is_available(self) -> bool:
        """Check if API key is present."""
        return bool(self.api_key)
        
    def list_services(self) -> List[Dict[str, Any]]:
        """List all services."""
        if not self.is_available:
            return self._get_mock_services()
            
        try:
            req = urllib.request.Request(
                f"{self.base_url}/services?limit=20",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json"
                }
            )
            
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                   raise Exception(f"API returned {response.status}")
                   
                data = json.loads(response.read().decode('utf-8'))
                return data
                
        except Exception as e:
            logger.warning(f"Render API failed: {e}. Falling back to mock.")
            return self._get_mock_services(error=str(e))

    def _get_mock_services(self, error: str = None) -> List[Dict[str, Any]]:
        """Return mock services for testing/verification."""
        mock_data = [
            {
                "service": {
                    "id": "srv-mock-1",
                    "name": "nucleus-backend",
                    "type": "web_service",
                    "repo": "https://github.com/nucleus-os/nucleus-core",
                    "branch": "main"
                },
                "cursor": "c1"
            },
            {
                "service": {
                    "id": "srv-mock-2",
                    "name": "gentlequest-app",
                    "type": "static_site",
                    "repo": "https://github.com/nucleus-os/gentlequest",
                    "branch": "production"
                },
                "cursor": "c2"
            }
        ]
        
        # Wrap in expected API format if needed, but simple list is fine for internal consumption
        return {
            "mock": True,
            "message": "Render API Key not found or call failed. Showing MOCK data.",
            "error_detail": error,
            "items": mock_data
        }

def get_render_ops():
    return RenderOps()
