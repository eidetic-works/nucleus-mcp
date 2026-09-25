"""OAuth scope must constrain what a token reaches (AU-3).

The consent screen lists the permissions an app is asking for, and the token
store records what was granted. Nothing read it back. `_validate_oauth_token`
pulled `tenant_id` off the validation result and discarded `scope`, so a user
who granted `mcp:resources` alone handed over a token that reached every tool.
The permission list was decorative.

Enforcement defaults to log-only — see `_scope_enforced` for why, and
`test_the_default_is_warn_not_reject` for the behaviour that pins it. These
tests cover both sides of that switch, because the mechanism is what closes the
finding and the default is what keeps it from breaking live clients.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

tenant = pytest.importorskip("mcp_server_nucleus.http_transport.tenant")


class FakeURL:
    def __init__(self, path):
        self.path = path


class FakeState:
    pass


class FakeRequest:
    def __init__(self, path="/mcp", scopes=None):
        self.url = FakeURL(path)
        self.state = FakeState()
        self.headers = {}
        if scopes is not None:
            self.state.nucleus_oauth_scopes = frozenset(scopes.split())


@pytest.fixture(autouse=True)
def enforcing(monkeypatch):
    """Most tests here are about the mechanism, so turn it on."""
    monkeypatch.setenv("NUCLEUS_OAUTH_SCOPE_ENFORCE", "true")
    yield


# --- the map itself --------------------------------------------------------


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/mcp", {"mcp:tools"}),
        ("/mcp/messages", {"mcp:tools"}),
        ("/sse", {"mcp:tools"}),
        ("/mcp-readonly", {"mcp:resources", "mcp:tools"}),
        ("/relay/agent-a", {"mcp:relay", "mcp:tools"}),
        ("/relay/agent-a/ack", {"mcp:relay", "mcp:tools"}),
    ],
)
def test_each_surface_declares_what_it_needs(path, expected):
    assert tenant.required_scopes_for_path(path) == frozenset(expected)


@pytest.mark.parametrize("path", ["/health", "/ready", "/", "/fleet", "/telemetry"])
def test_unscoped_paths_are_left_alone(path):
    assert tenant.required_scopes_for_path(path) is None


def test_a_prefix_does_not_match_a_longer_sibling():
    """/mcp-readonly must not be swallowed by the /mcp entry."""
    assert tenant.required_scopes_for_path("/mcp-readonly") == frozenset(
        {"mcp:resources", "mcp:tools"}
    )


# --- enforcement -----------------------------------------------------------


def test_a_narrowed_token_is_refused_the_tool_surface():
    err = tenant.check_scope(FakeRequest("/mcp", scopes="mcp:resources"))
    assert err is not None, (
        "a token granted only mcp:resources reached the full tool surface"
    )
    assert "mcp:tools" in err


def test_the_refusal_names_what_was_granted_and_what_was_needed():
    err = tenant.check_scope(FakeRequest("/mcp", scopes="mcp:prompts"))
    assert "mcp:prompts" in err and "mcp:tools" in err


def test_a_token_with_the_right_scope_passes():
    assert tenant.check_scope(FakeRequest("/mcp", scopes="mcp:tools")) is None


def test_any_one_of_the_accepted_scopes_is_enough():
    assert tenant.check_scope(FakeRequest("/relay/a", scopes="mcp:relay")) is None
    assert tenant.check_scope(FakeRequest("/relay/a", scopes="mcp:tools")) is None


def test_an_empty_scope_grant_reaches_nothing_scoped():
    assert tenant.check_scope(FakeRequest("/mcp", scopes="")) is not None


def test_an_unscoped_path_is_reachable_by_any_token():
    assert tenant.check_scope(FakeRequest("/health", scopes="mcp:prompts")) is None


# --- requests that are not OAuth at all ------------------------------------


def test_a_request_with_no_oauth_token_is_never_scope_checked():
    """Static map tokens and solo requests carry no scope to check."""
    assert tenant.check_scope(FakeRequest("/mcp")) is None


def test_absent_scope_state_is_distinct_from_an_empty_grant():
    """None means 'not an OAuth request'; frozenset() means 'granted nothing'."""
    assert tenant.check_scope(FakeRequest("/mcp")) is None
    assert tenant.check_scope(FakeRequest("/mcp", scopes="")) is not None


# --- the default must not break live clients -------------------------------


def test_the_default_is_warn_not_reject(monkeypatch, caplog):
    """Tokens already issued carry scopes this process cannot enumerate."""
    monkeypatch.delenv("NUCLEUS_OAUTH_SCOPE_ENFORCE", raising=False)
    with caplog.at_level("WARNING", logger="nucleus.tenant"):
        err = tenant.check_scope(FakeRequest("/mcp", scopes="mcp:resources"))
    assert err is None, "enforcement is on by default and will reject live clients"
    assert any("scope violation" in r.message for r in caplog.records), (
        "a violation passed without leaving the evidence needed to enable enforcement"
    )


def test_the_warning_records_the_path_and_the_scopes_held(monkeypatch, caplog):
    monkeypatch.delenv("NUCLEUS_OAUTH_SCOPE_ENFORCE", raising=False)
    with caplog.at_level("WARNING", logger="nucleus.tenant"):
        tenant.check_scope(FakeRequest("/relay/agent-b", scopes="mcp:prompts"))
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "/relay/agent-b" in logged and "mcp:prompts" in logged


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_enforcement_flag_spellings(monkeypatch, value):
    monkeypatch.setenv("NUCLEUS_OAUTH_SCOPE_ENFORCE", value)
    assert tenant.check_scope(FakeRequest("/mcp", scopes="mcp:resources")) is not None


@pytest.mark.parametrize("value", ["0", "false", "off", "no", ""])
def test_falsey_flag_spellings_keep_it_warn_only(monkeypatch, value):
    monkeypatch.setenv("NUCLEUS_OAUTH_SCOPE_ENFORCE", value)
    assert tenant.check_scope(FakeRequest("/mcp", scopes="mcp:resources")) is None


# --- the scope actually gets onto the request ------------------------------


def test_validation_records_the_granted_scope_on_the_request(monkeypatch):
    """The plumbing AU-3 was missing: scope was read and thrown away."""
    import mcp_server_nucleus.http_transport.oauth_server as oauth

    monkeypatch.setattr(
        oauth, "validate_bearer",
        lambda t: {"tenant_id": "tenant_x", "scope": "mcp:resources mcp:prompts"},
    )
    request = FakeRequest("/mcp")
    assert tenant._validate_oauth_token("nucleus_at_x", request) == "tenant_x"
    assert request.state.nucleus_oauth_scopes == frozenset(
        {"mcp:resources", "mcp:prompts"}
    )


def test_a_token_with_no_scope_field_records_an_empty_grant(monkeypatch):
    import mcp_server_nucleus.http_transport.oauth_server as oauth

    monkeypatch.setattr(oauth, "validate_bearer", lambda t: {"tenant_id": "tenant_x"})
    request = FakeRequest("/mcp")
    tenant._validate_oauth_token("nucleus_at_x", request)
    assert request.state.nucleus_oauth_scopes == frozenset()


def test_validation_without_a_request_still_works(monkeypatch):
    """The request argument is optional; callers that lack one must not break."""
    import mcp_server_nucleus.http_transport.oauth_server as oauth

    monkeypatch.setattr(
        oauth, "validate_bearer", lambda t: {"tenant_id": "tenant_x", "scope": "mcp:tools"}
    )
    assert tenant._validate_oauth_token("nucleus_at_x") == "tenant_x"
