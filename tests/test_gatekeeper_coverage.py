"""Coverage tests for runtime/identity/gatekeeper.py."""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.identity.gatekeeper import (
    ACCESS_DENIED,
    ACCESS_GRANTED,
    CapabilityGrant,
    Gatekeeper,
    GrantRequest,
)


def _brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir()
    return brain


def test_constants():
    assert ACCESS_DENIED is False
    assert ACCESS_GRANTED is True


def test_grant_request_fingerprint_is_stable():
    req = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    fp1 = req.fingerprint()
    fp2 = req.fingerprint()
    assert fp1 == fp2
    assert isinstance(fp1, str)
    assert len(fp1) == 64  # sha256 hex


def test_grant_request_fingerprint_param_order_independent():
    req1 = GrantRequest(agent_id="a", capability="net", params={"a": 1, "b": 2})
    req2 = GrantRequest(agent_id="a", capability="net", params={"b": 2, "a": 1})
    assert req1.fingerprint() == req2.fingerprint()


def test_grant_request_fingerprint_differs_for_different_requests():
    req1 = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    req2 = GrantRequest(agent_id="b", capability="net", params={"domain": "x.com"})
    assert req1.fingerprint() != req2.fingerprint()


def test_capability_grant_defaults():
    req = GrantRequest(agent_id="a", capability="net", params={"d": "x"})
    fp = req.fingerprint()
    grant = CapabilityGrant(
        request_fingerprint=fp,
        agent_id="a",
        capability="net",
        params={"d": "x"},
        granted_at="2024-01-01T00:00:00",
    )
    assert grant.granted_by == "user"


def test_gatekeeper_init_creates_ledger_dir(tmp_path):
    brain = _brain(tmp_path)
    gk = Gatekeeper(brain)
    assert (brain / "ledger").exists()
    assert gk._cache_grants == {}


def test_check_permission_denied_when_no_grant(tmp_path):
    brain = _brain(tmp_path)
    gk = Gatekeeper(brain)
    req = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    assert gk.check_permission(req) is ACCESS_DENIED


def test_grant_permission_persists_and_grants(tmp_path):
    brain = _brain(tmp_path)
    gk = Gatekeeper(brain)
    req = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    gk.grant_permission(req)
    assert gk.check_permission(req) is ACCESS_GRANTED
    # file written
    assert (brain / "ledger" / "permissions.json").exists()
    data = json.loads((brain / "ledger" / "permissions.json").read_text())
    assert len(data) == 1
    assert data[0]["agent_id"] == "a"


def test_grant_then_revoke(tmp_path):
    brain = _brain(tmp_path)
    gk = Gatekeeper(brain)
    req = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    gk.grant_permission(req)
    assert gk.check_permission(req) is ACCESS_GRANTED
    gk.revoke_permission(req)
    assert gk.check_permission(req) is ACCESS_DENIED
    data = json.loads((brain / "ledger" / "permissions.json").read_text())
    assert data == []


def test_revoke_nonexistent_is_noop(tmp_path):
    brain = _brain(tmp_path)
    gk = Gatekeeper(brain)
    req = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    # should not raise
    gk.revoke_permission(req)
    assert gk.check_permission(req) is ACCESS_DENIED


def test_load_ledger_persists_across_instances(tmp_path):
    brain = _brain(tmp_path)
    gk1 = Gatekeeper(brain)
    req = GrantRequest(agent_id="a", capability="net", params={"domain": "x.com"})
    gk1.grant_permission(req)

    gk2 = Gatekeeper(brain)
    assert gk2.check_permission(req) is ACCESS_GRANTED


def test_load_ledger_handles_corrupt_file(tmp_path):
    brain = _brain(tmp_path)
    ledger = brain / "ledger"
    ledger.mkdir()
    (ledger / "permissions.json").write_text("not json{")
    # should not raise, cache empty
    gk = Gatekeeper(brain)
    assert gk._cache_grants == {}


def test_load_ledger_handles_missing_file(tmp_path):
    brain = _brain(tmp_path)
    gk = Gatekeeper(brain)
    assert gk._cache_grants == {}


def test_load_ledger_handles_invalid_grant_entry(tmp_path):
    brain = _brain(tmp_path)
    ledger = brain / "ledger"
    ledger.mkdir()
    (ledger / "permissions.json").write_text(json.dumps([{"bad": "entry"}]))
    gk = Gatekeeper(brain)
    # invalid entry skipped
    assert gk._cache_grants == {}
