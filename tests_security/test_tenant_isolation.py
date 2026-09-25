"""Regression tests for the tenant-isolation fixes (audit ledger AU-1, TN-1, TN-2, HS-1, TN-5).

This mirror ships without the main `tests/` tree, so these live in their own
directory and are runnable on their own:

    PYTHONPATH=src python3 -m pytest tests_security -q

Every test here corresponds to a finding and fails against the pre-fix code.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_server_nucleus.http_transport import tenant as T  # noqa: E402


class FakeRequest:
    """Only the surface resolve_tenant touches."""

    def __init__(self, headers=None):
        self.headers = headers or {}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for key in (
        "NUCLEUS_TENANT_MAP", "NUCLEUS_REVOKED_TOKENS", "NUCLEUS_REQUIRE_AUTH",
        "NUCLEUS_TENANT_ID", "NUCLEUS_INTERNAL_ROUTING_SECRET",
        "NUCLEUS_TRUST_TENANT_HEADER",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(tmp_path / "tenants"))


# --- HS-1: the auth flag must reject a request with no credential at all ----

def test_require_auth_rejects_request_with_no_credentials(monkeypatch):
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
    tenant_id, error = T.resolve_tenant(FakeRequest())
    assert tenant_id is None, "a credential-less request must not resolve to a tenant"
    assert error


def test_permissive_mode_still_allows_solo_default():
    tenant_id, error = T.resolve_tenant(FakeRequest())
    assert (tenant_id, error) == ("default", None)


# --- AU-1 / TN-1: the tenant header is not an identity claim ----------------

def test_tenant_header_alone_is_rejected():
    req = FakeRequest({"X-Nucleus-Tenant-ID": "acme-corp"})
    tenant_id, error = T.resolve_tenant(req)
    assert tenant_id is None, "an unauthenticated header must not select a tenant"
    assert "internal" in error.lower()


def test_tenant_header_bypass_does_not_survive_require_auth(monkeypatch):
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
    req = FakeRequest({"X-Nucleus-Tenant-ID": "victim"})
    tenant_id, _ = T.resolve_tenant(req)
    assert tenant_id is None


def test_tenant_header_honoured_with_matching_internal_secret(monkeypatch):
    monkeypatch.setenv("NUCLEUS_INTERNAL_ROUTING_SECRET", "s3cret")
    req = FakeRequest({"X-Nucleus-Tenant-ID": "acme", "X-Nucleus-Internal-Auth": "s3cret"})
    assert T.resolve_tenant(req) == ("acme", None)


def test_tenant_header_rejected_with_wrong_internal_secret(monkeypatch):
    monkeypatch.setenv("NUCLEUS_INTERNAL_ROUTING_SECRET", "s3cret")
    req = FakeRequest({"X-Nucleus-Tenant-ID": "acme", "X-Nucleus-Internal-Auth": "guess"})
    tenant_id, error = T.resolve_tenant(req)
    assert tenant_id is None and "credential" in error.lower()


def test_escape_hatch_restores_old_behaviour(monkeypatch):
    monkeypatch.setenv("NUCLEUS_TRUST_TENANT_HEADER", "true")
    req = FakeRequest({"X-Nucleus-Tenant-ID": "acme"})
    assert T.resolve_tenant(req) == ("acme", None)


# --- a bad bearer token must not degrade to the default brain --------------

def test_unknown_token_rejected_when_a_tenant_map_exists(monkeypatch):
    monkeypatch.setenv("NUCLEUS_TENANT_MAP", '{"good": "acme"}')
    req = FakeRequest({"Authorization": "Bearer wrong"})
    tenant_id, error = T.resolve_tenant(req)
    assert tenant_id is None and error


def test_valid_token_resolves(monkeypatch):
    monkeypatch.setenv("NUCLEUS_TENANT_MAP", '{"good": "acme"}')
    req = FakeRequest({"Authorization": "Bearer good"})
    assert T.resolve_tenant(req) == ("acme", None)


def test_revoked_token_rejected(monkeypatch):
    monkeypatch.setenv("NUCLEUS_TENANT_MAP", '{"good": "acme"}')
    monkeypatch.setenv("NUCLEUS_REVOKED_TOKENS", "good")
    tenant_id, error = T.resolve_tenant(FakeRequest({"Authorization": "Bearer good"}))
    assert tenant_id is None and "revoked" in error.lower()


def test_unknown_token_tolerated_in_solo_permissive_mode():
    """A local single-brain user who sends a stray header is not locked out."""
    req = FakeRequest({"Authorization": "Bearer whatever"})
    assert T.resolve_tenant(req) == ("default", None)


# --- TN-2: traversal ------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "../../etc", "..", ".", "a/b", "a\\b", "/etc/passwd", "", " ",
    "x" * 65, "-leading-dash-ok-but-not-first" * 3, ".hidden",
])
def test_malicious_tenant_ids_are_refused(slug):
    assert not T._is_valid_tenant_id(slug), f"{slug!r} should be rejected"
    with pytest.raises(ValueError):
        T.brain_path_for_tenant(slug)


@pytest.mark.parametrize("slug", ["default", "oauth", "acme-corp", "tenant_0123456789abcdef"])
def test_real_tenant_ids_are_accepted(slug):
    assert T._is_valid_tenant_id(slug)


def test_traversal_header_cannot_escape_even_with_the_escape_hatch(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_TRUST_TENANT_HEADER", "true")
    req = FakeRequest({"X-Nucleus-Tenant-ID": "../../../../etc"})
    tenant_id, error = T.resolve_tenant(req)
    assert tenant_id is None, "slug validation must run even on the trusted path"


def test_brain_path_stays_under_the_root(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(tmp_path))
    brain = T.brain_path_for_tenant("acme")
    assert str(brain.resolve()).startswith(str(tmp_path.resolve()) + os.sep)
    assert brain.exists()


# --- RL-2: a configured tenant map means anonymous must not reach "default" ---

def test_anonymous_request_rejected_when_a_tenant_map_exists(monkeypatch):
    """A configured map proves the deployment is multi-tenant.

    Data routes (/engrams/sync and friends) trust whatever tenant the middleware
    resolves, so an anonymous caller resolving to the real "default" brain was
    read/write access to it without a credential.
    """
    monkeypatch.setenv("NUCLEUS_TENANT_MAP", '{"good": "acme"}')
    tenant_id, error = T.resolve_tenant(FakeRequest())
    assert tenant_id is None, "no credential + multi-tenant deployment must not resolve"
    assert error


def test_solo_deployment_still_needs_no_credential():
    """No map and no required auth: one brain, no boundary, nothing to break."""
    assert T.resolve_tenant(FakeRequest()) == ("default", None)
