"""The OAuth surface must obey its own enable flag and describe its own tenancy (AU-2).

Two separate holes, both on a public endpoint:

  - NUCLEUS_OAUTH_ENABLED controlled nothing but what the `/` endpoint reported.
    The routes were inserted unconditionally, so /register (which takes no auth)
    /authorize and /token answered on every deployment. A caller could register
    a client, consent to themselves, and leave with a bearer token.
  - the consent screen told the user "Same email = same memory", which stopped
    being true when the email claim was ignored. A screen a user reads before
    granting access must not misdescribe what it grants.

The flag is deliberately THREE-state, and the tests below pin all three. The
live relay was checked on 2026-09-11: it reported "oauth_enabled": false while
its OAuth discovery endpoints returned 200, meaning the variable is unset there
and Connector sign-in works because of the bug. A two-state gate would have
404'd production the moment it shipped, so "unset" serves and warns, and only an
explicit false closes the surface.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

oauth = pytest.importorskip("mcp_server_nucleus.http_transport.oauth_server")
pytest.importorskip("pytest_asyncio", reason="async tests need pytest-asyncio")


class FakeRequest:
    """Enough of a Starlette request for these handlers."""

    def __init__(self, method="GET", query=None, form=None):
        self.method = method
        self.query_params = query or {}
        self._form = form or {}
        self.headers = {}
        self.base_url = "https://nucleus.test/"

    async def form(self):
        return self._form


def _handler(path, method="GET"):
    for route in oauth.oauth_routes:
        if route.path == path and method in route.methods:
            return route.endpoint
    raise AssertionError(f"no route serves {method} {path}")


def _body(response):
    import json

    return json.loads(response.body)


@pytest.fixture(autouse=True)
def disabled_by_default(monkeypatch):
    for var in (
        "NUCLEUS_OAUTH_ENABLED",
        "NUCLEUS_CLERK_ENABLED",
        "NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


# --- the flag controls reachability, not just self-reported metadata -------

OAUTH_PATHS = [
    ("/.well-known/oauth-protected-resource", "GET"),
    ("/.well-known/oauth-authorization-server", "GET"),
    ("/register", "POST"),
    ("/authorize", "GET"),
    ("/authorize", "POST"),
    ("/auth/clerk/callback", "GET"),
    ("/token", "POST"),
    ("/revoke", "POST"),
]


@pytest.mark.parametrize("path,method", OAUTH_PATHS)
@pytest.mark.asyncio
async def test_an_explicitly_false_flag_closes_every_route(monkeypatch, path, method):
    """The kill switch this server never had."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "false")
    response = await _handler(path, method)(FakeRequest(method=method))
    assert response.status_code == 404, (
        f"{method} {path} answered with OAuth explicitly disabled; /register takes no "
        "auth, so that is a token mint open to any caller"
    )


@pytest.mark.asyncio
async def test_the_404_names_the_variable_so_the_closed_state_is_diagnosable(monkeypatch):
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "false")
    response = await _handler("/token", "POST")(FakeRequest(method="POST"))
    assert "NUCLEUS_OAUTH_ENABLED" in _body(response)["error_description"]


@pytest.mark.parametrize("value", ["TRUE", "true", "True", "1", "yes", "on"])
@pytest.mark.asyncio
async def test_the_flag_is_case_and_spelling_tolerant(monkeypatch, value):
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", value)
    response = await _handler("/.well-known/oauth-authorization-server", "GET")(FakeRequest())
    assert response.status_code == 200


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off"])
def test_falsey_spellings_all_close_the_surface(monkeypatch, value):
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", value)
    assert oauth._oauth_enabled() is False


# --- the unset state must not break a deployment already relying on it -----


@pytest.mark.parametrize("path,method", OAUTH_PATHS)
@pytest.mark.asyncio
async def test_an_unset_flag_keeps_serving(path, method):
    """Checked against the live relay: it serves OAuth with the variable unset.

    Shipping a two-state gate would have 404'd ChatGPT and Claude.ai sign-in.
    """
    response = await _handler(path, method)(FakeRequest(method=method))
    assert response.status_code != 404, (
        f"{method} {path} 404s with the variable unset, which breaks every deployment "
        "that has been relying on the routes answering unconditionally"
    )


@pytest.mark.asyncio
async def test_the_unset_state_warns_so_it_is_not_silent(monkeypatch, caplog):
    """AU-2's complaint was that an operator could not tell the surface was live."""
    monkeypatch.setattr(oauth, "_warned_oauth_unconfigured", False)
    with caplog.at_level("WARNING", logger="nucleus.oauth_server"):
        await _handler("/register", "POST")(FakeRequest(method="POST"))
    assert any("NUCLEUS_OAUTH_ENABLED" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_the_warning_fires_once_not_per_request(monkeypatch, caplog):
    """A public endpoint must not let a caller drive log volume."""
    monkeypatch.setattr(oauth, "_warned_oauth_unconfigured", False)
    with caplog.at_level("WARNING", logger="nucleus.oauth_server"):
        for _ in range(5):
            await _handler("/register", "POST")(FakeRequest(method="POST"))
    warnings = [r for r in caplog.records if "NUCLEUS_OAUTH_ENABLED" in r.message]
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_an_enabled_deployment_does_not_warn(monkeypatch, caplog):
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    monkeypatch.setattr(oauth, "_warned_oauth_unconfigured", False)
    with caplog.at_level("WARNING", logger="nucleus.oauth_server"):
        await _handler("/register", "POST")(FakeRequest(method="POST"))
    assert not [r for r in caplog.records if "NUCLEUS_OAUTH_ENABLED" in r.message]


def test_the_gate_is_read_per_request_not_captured_at_import(monkeypatch):
    """A deployment must be able to flip the flag without a rebuild."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    assert oauth._oauth_enabled() is True
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "false")
    assert oauth._oauth_enabled() is False
    monkeypatch.delenv("NUCLEUS_OAUTH_ENABLED")
    assert oauth._oauth_enabled() is None, "unset must stay distinguishable from false"


@pytest.mark.parametrize("value", ["", "   "])
def test_an_empty_value_reads_as_unset_not_as_false(monkeypatch, value):
    """An empty env var is a deployment that set nothing, not one that said no."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", value)
    assert oauth._oauth_enabled() is None


def test_no_oauth_route_bypasses_the_gate():
    """A route added later must not quietly skip _gated."""
    for route in oauth.oauth_routes:
        assert getattr(route.endpoint, "__wrapped__", None) is not None, (
            f"{route.path} is wired without _gated, so it answers with OAuth disabled"
        )


# --- the consent screen must describe the tenancy it actually gives -------


def _consent_html(monkeypatch):
    """Render the consent screen for a registered client."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    store = oauth._get_store()
    client = store.register_client(
        client_name="Test App", redirect_uris=["https://example.test/cb"]
    )
    request = FakeRequest(
        query={
            "client_id": client["client_id"],
            "redirect_uri": "https://example.test/cb",
            "response_type": "code",
            "scope": "mcp:tools",
        }
    )
    return request, client


@pytest.mark.asyncio
async def test_the_screen_does_not_promise_per_email_brains_it_will_not_give(monkeypatch):
    request, _ = _consent_html(monkeypatch)
    html = (await oauth.authorize(request)).body.decode()
    assert "Same email = same memory" not in html, (
        "the screen promised per-email brains while the default path ignores the address"
    )
    assert "single shared Brain" in html
    assert 'name="user_email"' not in html, (
        "a field whose value is discarded invites the user to believe it routes them"
    )


@pytest.mark.asyncio
async def test_the_unverified_path_says_the_address_is_unverified(monkeypatch):
    monkeypatch.setenv("NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL", "true")
    request, _ = _consent_html(monkeypatch)
    html = (await oauth.authorize(request)).body.decode()
    assert 'name="user_email"' in html, "the field routes on this path and must be shown"
    assert "Not verified" in html
    assert "No password needed" not in html


@pytest.mark.asyncio
async def test_consent_without_an_email_field_still_issues_a_single_tenant_code(monkeypatch):
    """Dropping the field must not break the flow — it issues an unbound code."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    store = oauth._get_store()
    client = store.register_client(
        client_name="Test App", redirect_uris=["https://example.test/cb"]
    )
    request = FakeRequest(
        method="POST",
        form={
            "client_id": client["client_id"],
            "redirect_uri": "https://example.test/cb",
            "response_type": "code",
            "scope": "mcp:tools",
            "action": "allow",
        },
    )
    response = await oauth.authorize(request)
    assert response.status_code == 302
    code = response.headers["location"].split("code=")[1].split("&")[0]
    assert store.consume_code(code)["tenant_id"] is None, (
        "an unverified consent must not bind a tenant"
    )
