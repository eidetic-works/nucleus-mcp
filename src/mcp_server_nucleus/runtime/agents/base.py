from typing import List, Any, Optional
from pydantic import BaseModel, Field

class TrustProfile(BaseModel):
    """
    Security and Trust metadata for an Agent.
    Defines what the agent is allowed to do and who verified it.
    """
    tier: str = Field(default="genesis", description="Trust Tier: genesis, verified, community, untrusted")
    verification_hash: Optional[str] = Field(None, description="Cryptographic hash of the agent's code")
    capabilities: List[str] = Field(default_factory=list, description="High-level capability grants (e.g. 'fs_read', 'net_out')")
    maintainer: str = Field(default="@nucleus-core", description="Entity responsible for this agent")

class SovereignAgent(BaseModel):
    """
    Base class for all Nucleus Sovereign Agents.
    Wraps existing MCP capabilities into a standardized Agent interface.
    """
    name: str = Field(..., description="The unique handle of the agent (e.g., @nucleus/librarian)")
    description: str = Field(..., description="Human-readable description of the agent's purpose")
    instructions: str = Field(..., description="System prompt or behavioral instructions for the agent")
    tools: List[Any] = Field(default_factory=list, description="List of MCP tools exposed by this agent")
    trust: TrustProfile = Field(default_factory=TrustProfile, description="Security profile for the agent")
    
    def run(self, input_text: str) -> str:
        """
        Syntactic sugar for 'running' the agent.
        In reality, Agents are tool containers, but this allows for simple testing.
        """
        return f"Agent {self.name} received: {input_text}"

    class Config:
        arbitrary_types_allowed = True

