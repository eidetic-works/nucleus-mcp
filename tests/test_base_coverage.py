"""Coverage tests for runtime/agents/base.py."""
import pytest
from pydantic import ValidationError

from mcp_server_nucleus.runtime.agents.base import SovereignAgent, TrustProfile


def test_trust_profile_defaults():
    tp = TrustProfile()
    assert tp.tier == "genesis"
    assert tp.verification_hash is None
    assert tp.capabilities == []
    assert tp.maintainer == "@nucleus-core"


def test_trust_profile_custom():
    tp = TrustProfile(tier="verified", verification_hash="abc", capabilities=["fs_read"], maintainer="@me")
    assert tp.tier == "verified"
    assert tp.capabilities == ["fs_read"]


def test_sovereign_agent_required_fields():
    with pytest.raises(ValidationError):
        SovereignAgent(name="a")  # missing description, instructions


def test_sovereign_agent_defaults():
    a = SovereignAgent(name="@n/x", description="d", instructions="i")
    assert a.tools == []
    assert a.trust.tier == "genesis"


def test_sovereign_agent_run():
    a = SovereignAgent(name="@n/x", description="d", instructions="i")
    out = a.run("hello")
    assert out == "Agent @n/x received: hello"


def test_sovereign_agent_with_tools():
    a = SovereignAgent(name="@n/x", description="d", instructions="i", tools=[1, 2, 3])
    assert a.tools == [1, 2, 3]


def test_sovereign_agent_arbitrary_types():
    class Custom:
        pass
    a = SovereignAgent(name="@n/x", description="d", instructions="i", tools=[Custom()])
    assert len(a.tools) == 1
