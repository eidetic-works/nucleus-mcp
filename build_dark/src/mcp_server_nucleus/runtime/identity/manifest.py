from enum import Enum
from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Optional, Literal, Dict, Any

class CapabilityScope(str, Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"
    SHELL = "shell"
    STRATEGY = "strategy"
    BROWSER = "browser"

class Capability(BaseModel):
    scope: CapabilityScope
    reason: str = Field(..., description="Why this capability is needed")
    
    # Scope-specific fields
    domains: Optional[List[str]] = Field(None, description="For network scope: Whitelisted domains")
    paths: Optional[List[str]] = Field(None, description="For filesystem/strategy scope: Allowed paths")
    mode: Optional[Literal["read", "write", "readwrite", "read_write"]] = Field(None, description="For filesystem/strategy scope: Access mode")

    @validator("domains")
    def validate_network_domains(cls, v, values):
        if values.get("scope") == CapabilityScope.NETWORK and not v:
            raise ValueError("Network capability must specify 'domains' whitelist.")
        return v

    @validator("paths")
    def validate_fs_paths(cls, v, values):
        scope = values.get("scope")
        if scope in [CapabilityScope.FILESYSTEM, CapabilityScope.STRATEGY] and not v:
            raise ValueError(f"{scope} capability must specify 'paths' whitelist.")
        return v

class AgentIdentity(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9]+(\.[a-z0-9]+)+$", description="Reverse DNS ID (e.g. nucleus.core.ops)")
    name: str
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Semantic Version")
    description: str
    author: str
    license: str

class LifecyclePolicy(BaseModel):
    persistence: Literal["session", "persistent", "immortal"] = "session"
    cleanup: Literal["strict", "lazy", "none"] = "strict"

class AgentManifest(BaseModel):
    manifest_version: str = "1.0.0"
    agent: AgentIdentity
    capabilities: List[Capability] = Field(default_factory=list)
    lifecycle: LifecyclePolicy = Field(default_factory=LifecyclePolicy)

class ManifestValidator:
    """
    Validates Agent Manifests against the strict zero-trust schema.
    """
    @staticmethod
    def validate(manifest_data: Dict[str, Any]) -> AgentManifest:
        try:
            return AgentManifest(**manifest_data)
        except ValidationError as e:
            raise ValueError(f"Manifest Validation Failed: {e}")
