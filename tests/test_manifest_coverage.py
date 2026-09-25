"""Coverage tests for runtime/identity/manifest.py."""
import pytest
from pydantic import ValidationError

from mcp_server_nucleus.runtime.identity.manifest import (
    AgentIdentity,
    AgentManifest,
    Capability,
    CapabilityScope,
    LifecyclePolicy,
    ManifestValidator,
)


def _valid_agent_dict():
    return {
        "id": "nucleus.core.ops",
        "name": "Ops",
        "version": "1.0.0",
        "description": "desc",
        "author": "me",
        "license": "MIT",
    }


def test_capability_scope_enum_values():
    assert CapabilityScope.NETWORK.value == "network"
    assert CapabilityScope.FILESYSTEM.value == "filesystem"
    assert CapabilityScope.MEMORY.value == "memory"
    assert CapabilityScope.SHELL.value == "shell"
    assert CapabilityScope.STRATEGY.value == "strategy"
    assert CapabilityScope.BROWSER.value == "browser"


def test_capability_network_requires_domains():
    # Pydantic V1 validators only run when field is explicitly provided
    with pytest.raises(ValidationError):
        Capability(scope=CapabilityScope.NETWORK, reason="r", domains=None)


def test_capability_network_empty_domains_raises():
    with pytest.raises(ValidationError):
        Capability(scope=CapabilityScope.NETWORK, reason="r", domains=[])


def test_capability_network_with_domains_ok():
    cap = Capability(scope=CapabilityScope.NETWORK, reason="r", domains=["x.com"])
    assert cap.domains == ["x.com"]


def test_capability_filesystem_requires_paths():
    with pytest.raises(ValidationError):
        Capability(scope=CapabilityScope.FILESYSTEM, reason="r", paths=None)


def test_capability_filesystem_empty_paths_raises():
    with pytest.raises(ValidationError):
        Capability(scope=CapabilityScope.FILESYSTEM, reason="r", paths=[])


def test_capability_filesystem_with_paths_ok():
    cap = Capability(scope=CapabilityScope.FILESYSTEM, reason="r", paths=["/tmp"])
    assert cap.paths == ["/tmp"]


def test_capability_strategy_requires_paths():
    with pytest.raises(ValidationError):
        Capability(scope=CapabilityScope.STRATEGY, reason="r", paths=None)


def test_capability_strategy_with_paths_ok():
    cap = Capability(scope=CapabilityScope.STRATEGY, reason="r", paths=["/s"])
    assert cap.paths == ["/s"]


def test_capability_memory_no_required_fields():
    cap = Capability(scope=CapabilityScope.MEMORY, reason="r")
    assert cap.domains is None
    assert cap.paths is None


def test_capability_shell_no_required_fields():
    cap = Capability(scope=CapabilityScope.SHELL, reason="r")
    assert cap.scope == CapabilityScope.SHELL


def test_capability_mode_literal():
    cap = Capability(scope=CapabilityScope.FILESYSTEM, reason="r", paths=["/x"], mode="read")
    assert cap.mode == "read"


def test_capability_invalid_mode():
    with pytest.raises(ValidationError):
        Capability(scope=CapabilityScope.FILESYSTEM, reason="r", paths=["/x"], mode="bad")


def test_agent_identity_valid():
    a = AgentIdentity(**_valid_agent_dict())
    assert a.id == "nucleus.core.ops"


def test_agent_identity_bad_id_pattern():
    d = _valid_agent_dict()
    d["id"] = "BadID"
    with pytest.raises(ValidationError):
        AgentIdentity(**d)


def test_agent_identity_bad_version():
    d = _valid_agent_dict()
    d["version"] = "1.0"
    with pytest.raises(ValidationError):
        AgentIdentity(**d)


def test_lifecycle_policy_defaults():
    lp = LifecyclePolicy()
    assert lp.persistence == "session"
    assert lp.cleanup == "strict"


def test_lifecycle_policy_invalid():
    with pytest.raises(ValidationError):
        LifecyclePolicy(persistence="bad")


def test_agent_manifest_defaults():
    a = AgentIdentity(**_valid_agent_dict())
    m = AgentManifest(agent=a)
    assert m.manifest_version == "1.0.0"
    assert m.capabilities == []
    assert m.lifecycle.persistence == "session"


def test_manifest_validator_valid():
    data = {"agent": _valid_agent_dict(), "capabilities": []}
    m = ManifestValidator.validate(data)
    assert isinstance(m, AgentManifest)
    assert m.agent.id == "nucleus.core.ops"


def test_manifest_validator_invalid_raises_valueerror():
    data = {"agent": {**_valid_agent_dict(), "id": "bad"}}
    with pytest.raises(ValueError):
        ManifestValidator.validate(data)


def test_manifest_validator_with_capabilities():
    data = {
        "agent": _valid_agent_dict(),
        "capabilities": [
            {"scope": "network", "reason": "r", "domains": ["x.com"]},
            {"scope": "filesystem", "reason": "r", "paths": ["/tmp"], "mode": "read"},
        ],
    }
    m = ManifestValidator.validate(data)
    assert len(m.capabilities) == 2
