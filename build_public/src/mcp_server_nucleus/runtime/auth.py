"""
AuthManager: The Keyring.
Manages access to Private Repositories via Environment Variables.

Strategic Role:
- EXTERNAL CONFIG: Never stores secrets in Brain. Only maps URLs to Env Vars.
- INJECTION: Dynamically adds credentials to Git URLs for the Fetcher.
- SCOPING: defaults to 'oauth2' username for GitHub PATs.
"""

import os
import json
import logging
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger("AUTH")

class PrivateSource(BaseModel):
    domain: str = Field(..., description="Git Domain (e.g. github.com)")
    org: Optional[str] = Field(None, description="Optional Organization Scope")
    token_env: str = Field(..., description="Name of Env Var holding the Token")
    username: str = Field("oauth2", description="Username for HTTP Basic Auth")

class Credentials(BaseModel):
    username: str
    token: str

class AuthManager:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.config_path = brain_path / "config" / "auth.json"
        
        self.sources: List[PrivateSource] = []
        self._load_config()

    def _load_config(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                for item in data.get("sources", []):
                    self.sources.append(PrivateSource(**item))
            except Exception as e:
                logger.error(f"Failed to load auth config: {e}")

    def get_credentials(self, repo_url: str) -> Optional[Credentials]:
        """
        Match URL against configured sources to find credentials.
        """
        parsed = urlparse(repo_url)
        domain = parsed.netloc
        path = parsed.path.strip("/")
        
        # Find best match
        # 1. Match Domain + Org
        for source in self.sources:
            if source.domain == domain and source.org:
                if path.startswith(source.org + "/"):
                    return self._resolve_env(source)
                    
        # 2. Match Domain Only
        for source in self.sources:
            if source.domain == domain and not source.org:
                return self._resolve_env(source)
                
        return None

    def _resolve_env(self, source: PrivateSource) -> Optional[Credentials]:
        token = os.environ.get(source.token_env)
        if token:
            return Credentials(username=source.username, token=token)
        logger.warning(f"Auth configured for {source.domain} but {source.token_env} is missing.")
        return None

    def inject_credentials(self, repo_url: str) -> str:
        """
        If credentials exist for this URL, inject them into the URL string.
        Returns original URL if no creds found.
        """
        creds = self.get_credentials(repo_url)
        if not creds:
            return repo_url
            
        parsed = urlparse(repo_url)
        
        # Reconstruct with auth
        # netloc = username:password@hostname
        netloc = f"{creds.username}:{creds.token}@{parsed.hostname}"
        
        # Handle port if present
        if parsed.port:
            netloc += f":{parsed.port}"
            
        # Replace netloc
        new_parsed = parsed._replace(netloc=netloc)
        return urlunparse(new_parsed)
