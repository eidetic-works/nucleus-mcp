"""Coverage tests for runtime/identity/trust.py."""
import pytest
from pydantic import ValidationError

from mcp_server_nucleus.runtime.identity.trust import TrustLevel, TrustProfile


def test_trust_level_enum_values():
    assert TrustLevel.VERIFIED.value == "verified"
    assert TrustLevel.COMMUNITY.value == "community"
    assert TrustLevel.UNKNOWN.value == "unknown"
    assert TrustLevel.MALICIOUS.value == "malicious"


def test_trust_profile_defaults():
    p = TrustProfile(publisher_id="k1", label="Antigravity", public_key="PEM")
    assert p.trust_level == TrustLevel.UNKNOWN
    assert p.verification_url is None


def test_trust_profile_required_fields():
    with pytest.raises(ValidationError):
        TrustProfile(publisher_id="k1", public_key="PEM")  # missing label


def test_trust_profile_to_json():
    p = TrustProfile(publisher_id="k1", label="L", public_key="PEM")
    j = p.to_json()
    assert '"publisher_id": "k1"' in j
    assert '"trust_level": "unknown"' in j


def test_trust_profile_from_json_roundtrip():
    p = TrustProfile(
        publisher_id="k1",
        trust_level=TrustLevel.VERIFIED,
        label="L",
        public_key="PEM",
        verification_url="https://gist.example/x",
    )
    j = p.to_json()
    p2 = TrustProfile.from_json(j)
    assert p2.publisher_id == "k1"
    assert p2.trust_level == TrustLevel.VERIFIED
    assert p2.verification_url == "https://gist.example/x"


def test_trust_profile_from_json_invalid():
    with pytest.raises(Exception):
        TrustProfile.from_json("not json")
