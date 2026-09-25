"""The HTTP stack, exercised as a real app rather than through fakes.

Every other suite here drives the pieces directly — a fake request, a handler
called by hand. That is the right shape for pinning one behaviour, and it shares
a blind spot: it cannot catch a fix that is correct in isolation and never
reaches the wire. Middleware ordering, the route table, and the interaction
between the auth gate and the exempt-path list are all invisible to a fake.

So this file builds the actual Starlette app and makes actual requests, covering
the findings whose whole point was what an unauthenticated caller receives:

  AU-1 / TN-1  a bare X-Nucleus-Tenant-ID header as an identity claim
  TN-2         that header joined into a filesystem path
  HS-1 / RL-2  an anonymous request resolving to a real tenant
  AU-2         the OAuth surface answering on a deployment that disabled it
  HS-5         /ready describing the filesystem to strangers

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("starlette")
pytest.importorskip("fastmcp", reason="building the real app needs fastmcp")
from starlette.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def app():
    try:
        from mcp_server_nucleus.http_transport import app as app_mod
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"the HTTP app does not build here: {type(e).__name__}: {e}")
    return app_mod.app


@pytest.fixture
def client(app, tmp_path, monkeypatch):
    """A client whose brain lives in tmp_path, never the caller's home.

    Without this the tenant middleware creates ~/.nucleus/tenants/... on the
    machine running the tests.
    """
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(tmp_path / "tenants"))
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    monkeypatch.delenv("NUCLEUS_TENANT_MAP", raising=False)
    monkeypatch.delenv("NUCLEUS_TRUST_TENANT_HEADER", raising=False)
    monkeypatch.delenv("NUCLEUS_INTERNAL_ROUTING_SECRET", raising=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def secured(client, monkeypatch):
    """A deployment that has asked for authentication."""
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
    return client


# --- an anonymous caller gets nothing (HS-1, RL-2) -------------------------

GUARDED = ["/metrics", "/fleet", "/telemetry/g35"]


@pytest.mark.parametrize("path", GUARDED)
def test_an_anonymous_request_is_rejected_when_auth_is_required(secured, path):
    response = secured.get(path)
    assert response.status_code == 401, (
        f"GET {path} served an anonymous caller on a deployment with "
        f"NUCLEUS_REQUIRE_AUTH set; it returned {response.status_code}"
    )


# --- the tenant header is not an identity claim (AU-1, TN-1, TN-2) --------


def test_a_bare_tenant_header_does_not_authenticate(secured):
    response = secured.get("/metrics", headers={"X-Nucleus-Tenant-ID": "victim"})
    assert response.status_code == 401, (
        "an unauthenticated caller named a tenant in a header and was believed"
    )


def test_the_rejection_says_what_would_make_the_header_trusted(secured):
    """An operator behind a gateway must be able to diagnose this."""
    response = secured.get("/metrics", headers={"X-Nucleus-Tenant-ID": "victim"})
    assert "X-Nucleus-Tenant-ID" in response.json()["detail"]


@pytest.mark.parametrize("value", ["../../etc", "a/../../b", "..", "with/slash"])
def test_a_traversal_in_the_tenant_header_never_reaches_a_path(secured, value):
    assert secured.get("/metrics", headers={"X-Nucleus-Tenant-ID": value}).status_code == 401


def test_an_unknown_bearer_token_is_rejected_not_ignored(secured):
    response = secured.get("/metrics", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


# --- probes must keep working, or orchestrators restart the service -------


def test_health_stays_open(client):
    assert client.get("/health").status_code == 200


def test_health_stays_open_even_when_auth_is_required(secured):
    assert secured.get("/health").status_code == 200


# --- /ready says ready or not, and nothing else (HS-5) -------------------


def test_ready_answers_without_describing_the_filesystem(client, tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert set(body) == {"status"}, f"/ready returned more than a status: {body}"
    assert str(tmp_path) not in response.text


def test_ready_discloses_nothing_when_it_cannot_resolve_a_brain(client, monkeypatch, tmp_path):
    """The failure path is the one that used to return str(e).

    Pointing at a merely absent directory does not fail: get_brain_path()
    creates it on demand, which is the documented behaviour and is why this test
    blocks creation instead. A plain file where the directory should go makes
    mkdir raise, which is the closest reachable stand-in for the real failure —
    a path the process cannot use.
    """
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(blocked / "secret-dir" / ".brain"))

    response = client.get("/ready")
    assert response.status_code == 503, (
        f"a brain path that cannot be created still reported ready: {response.text}"
    )
    assert response.json() == {"status": "not_ready"}
    assert "secret-dir" not in response.text and str(tmp_path) not in response.text, (
        "the failing path was named in a response served to unauthenticated callers"
    )


# --- the OAuth surface obeys its flag (AU-2) -----------------------------

OAUTH_PATHS = [
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-authorization-server",
]


@pytest.mark.parametrize("path", OAUTH_PATHS)
def test_oauth_discovery_is_closed_when_explicitly_disabled(client, monkeypatch, path):
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "false")
    response = client.get(path)
    assert response.status_code == 404
    assert "NUCLEUS_OAUTH_ENABLED" in response.json()["error_description"]


@pytest.mark.parametrize("path", OAUTH_PATHS)
def test_oauth_discovery_is_served_when_enabled(client, monkeypatch, path):
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", OAUTH_PATHS)
def test_oauth_discovery_is_served_when_the_flag_was_never_set(client, monkeypatch, path):
    """The three-state default. A deployment predating the flag keeps working."""
    monkeypatch.delenv("NUCLEUS_OAUTH_ENABLED", raising=False)
    assert client.get(path).status_code == 200


def test_registering_a_client_is_impossible_while_oauth_is_disabled(client, monkeypatch):
    """DCR takes no auth, so the flag is the only thing standing in front of it."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "false")
    response = client.post("/register", json={"client_name": "attacker"})
    assert response.status_code == 404
    assert "client_secret" not in response.text


# --- the solo deployment is deliberately untouched ------------------------


def test_a_solo_deployment_still_serves_its_own_operator(client, monkeypatch):
    """No tenant map, no required auth: one brain, no boundary to breach."""
    monkeypatch.delenv("NUCLEUS_REQUIRE_AUTH", raising=False)
    response = client.get("/metrics")
    assert response.status_code == 200, (
        "the auth fixes locked a solo user out of their own machine"
    )


# --- real multi-tenant isolation, not a fake ------------------------------


@pytest.fixture
def two_tenants(client, monkeypatch, tmp_path):
    """A deployment with two real tokens mapping to two real tenants."""
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(tmp_path / "tenants"))
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.setenv("NUCLEUS_TENANT_MAP", '{"tok-a": "alpha", "tok-b": "bravo"}')
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
    return client


def _as(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("token,tenant", [("tok-a", "alpha"), ("tok-b", "bravo")])
def test_each_token_resolves_to_its_own_tenant(two_tenants, token, tenant):
    response = two_tenants.get("/metrics", headers=_as(token))
    assert response.status_code == 200
    assert response.headers.get("X-Nucleus-Tenant") == tenant


def test_each_tenant_gets_its_own_brain_on_disk(two_tenants, tmp_path):
    for token in ("tok-a", "tok-b"):
        two_tenants.get("/metrics", headers=_as(token))
    roots = sorted(p.name for p in (tmp_path / "tenants").iterdir())
    assert roots == ["alpha", "bravo"], f"tenants did not get separate brains: {roots}"


def test_a_valid_token_cannot_escalate_by_naming_another_tenant(two_tenants):
    """Holding one tenant's credential must not let you ask for another's."""
    response = two_tenants.get(
        "/metrics", headers={**_as("tok-a"), "X-Nucleus-Tenant-ID": "bravo"}
    )
    assert response.headers.get("X-Nucleus-Tenant") == "alpha", (
        "a token for alpha was served bravo's tenant because the request asked for it"
    )


def test_an_unmapped_token_is_rejected_where_a_map_exists(two_tenants):
    assert two_tenants.get("/metrics", headers=_as("tok-z")).status_code == 401


def test_the_relay_does_not_accept_tenant_map_tokens(two_tenants):
    """Recorded because it surprised me, not because it is wrong.

    The relay routes carry their own token system, separate from
    NUCLEUS_TENANT_MAP, so a tenant-map bearer token is 'Token not recognised'
    there. That means relay ownership (RL-1) cannot be exercised with these
    credentials and is covered by test_relay_ownership.py instead. Pinned here
    so nobody later reads a 401 from this surface as a broken tenant map.
    """
    response = two_tenants.get("/relay/alpha", headers=_as("tok-a"))
    assert response.status_code == 401
    assert "auth" in response.text.lower()


def test_the_root_endpoint_reports_both_oauth_fields(client, monkeypatch):
    """oauth_configured distinguishes 'never set' from 'off' (AU-2)."""
    monkeypatch.delenv("NUCLEUS_OAUTH_ENABLED", raising=False)
    body = json.loads(client.get("/").text)
    assert body["oauth_enabled"] is True
    assert body["oauth_configured"] is False, (
        "an unset deployment reports as configured, which is what let the relay "
        "serve OAuth while reporting oauth_enabled:false"
    )


# --- the read-only mount is not an access boundary (HS-4) ----------------


def test_the_readonly_mount_is_not_a_way_around_auth(secured):
    """It restricts which tools exist, not who may reach them.

    The module's framing — "enterprise sandboxes", "federated connectors" —
    reads like a lower-trust surface. It is not one, and the dangerous
    misreading is the other direction: that /mcp-readonly needs less credential
    than /mcp. It needs exactly the same.
    """
    assert secured.get("/mcp-readonly").status_code == 401, (
        "/mcp-readonly served an anonymous caller on a deployment that requires "
        "auth, so it is a bypass around /mcp rather than a restriction of it"
    )


def test_both_mcp_mounts_answer_an_anonymous_caller_the_same_way(secured):
    assert secured.get("/mcp").status_code == secured.get("/mcp-readonly").status_code


def test_the_readonly_module_says_it_is_not_an_access_boundary():
    """The fix HS-4 actually asked for was the documentation."""
    import mcp_server_nucleus.http_transport.readonly_app as ro

    doc = (ro.__doc__ or "")
    assert "same tenant and authentication posture" in doc, (
        "readonly_app's docstring still lets a reader infer that /mcp-readonly "
        "is a lower-trust surface"
    )
