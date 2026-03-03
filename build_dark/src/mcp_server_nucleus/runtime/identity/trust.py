from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class TrustLevel(str, Enum):
    VERIFIED = "verified"     # Signed by Nucleus Root or known partner
    COMMUNITY = "community"   # Signed by unknown key, but structure valid
    UNKNOWN = "unknown"       # Unsigned or invalid
    MALICIOUS = "malicious"   # Specific deny-list

class TrustProfile(BaseModel):
    """
    Represents the Identity of an Agent Publisher.
    This corresponds to the 'signer' of the .nuke artifact.
    """
    publisher_id: str = Field(..., description="Unique Key ID (Fingerprint)")
    trust_level: TrustLevel = Field(default=TrustLevel.UNKNOWN, description="Current trust status")
    label: str = Field(..., description="Human readable name (e.g., 'Antigravity')")
    public_key: str = Field(..., description="PEM encoded Public Key")
    verification_url: Optional[str] = Field(None, description="URL to verify identity (e.g. GitHub Gist)")

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "TrustProfile":
        return cls.model_validate_json(json_str)
