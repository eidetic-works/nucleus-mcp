"""PKCE must actually bind the authorization code (AU-5).

`/.well-known/oauth-authorization-server` advertised `"code_challenge_methods_supported":
["S256"]`. `/authorize` read `code_challenge` and `code_challenge_method` off the
query string. `create_code` had no parameter for either and never stored them,
and `/token` never read `code_verifier` at all.

So an intercepted authorization code could be redeemed by anyone — the exact
attack PKCE exists to prevent — while the server told clients it was protected.
Open dynamic client registration made it worse: the `client_secret` check at
`/token` does not distinguish a real app from an attacker who registered one
thirty seconds ago.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

oauth = pytest.importorskip("mcp_server_nucleus.http_transport.oauth_server")

VERIFIER = "a" * 64  # within RFC 7636's 43-128 range


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")


def _entry(challenge="", method="S256"):
    return {"code_challenge": challenge, "code_challenge_method": method}


@pytest.fixture(autouse=True)
def pkce_optional(monkeypatch):
    monkeypatch.delenv("NUCLEUS_OAUTH_REQUIRE_PKCE", raising=False)
    yield


# --- the check itself ------------------------------------------------------


def test_a_matching_verifier_is_accepted():
    assert oauth._check_pkce(_entry(_challenge(VERIFIER)), VERIFIER) is None


def test_a_wrong_verifier_is_rejected():
    err = oauth._check_pkce(_entry(_challenge(VERIFIER)), "b" * 64)
    assert err is not None and "does not match" in err


def test_a_missing_verifier_is_rejected_when_a_challenge_was_used():
    """This is the whole attack: redeeming an intercepted code without one."""
    err = oauth._check_pkce(_entry(_challenge(VERIFIER)), "")
    assert err is not None and "code_verifier is required" in err


def test_plain_is_not_honoured_even_if_a_client_asks_for_it():
    """Advertising S256 while accepting plain would let a downgrade undo it."""
    err = oauth._check_pkce(_entry(VERIFIER, method="plain"), VERIFIER)
    assert err is not None and "S256" in err


def test_an_unknown_method_is_rejected():
    err = oauth._check_pkce(_entry(_challenge(VERIFIER), method="S512"), VERIFIER)
    assert err is not None and "S512" in err


def test_a_method_omitted_alongside_a_challenge_is_treated_as_s256():
    """RFC 7636 defaults to plain, but this server only ever advertised S256."""
    assert oauth._check_pkce(_entry(_challenge(VERIFIER), method=""), VERIFIER) is None


@pytest.mark.parametrize("length", [42, 129])
def test_a_verifier_outside_the_rfc_length_range_is_rejected(length):
    verifier = "a" * length
    err = oauth._check_pkce(_entry(_challenge(verifier)), verifier)
    assert err is not None and "43-128" in err


def test_the_challenge_is_compared_without_padding():
    """base64url challenges are unpadded; a padded comparison never matches."""
    challenge = _challenge(VERIFIER)
    assert "=" not in challenge
    assert oauth._check_pkce(_entry(challenge), VERIFIER) is None


# --- clients that do not use PKCE must keep working ------------------------


def test_a_code_with_no_challenge_is_allowed_by_default():
    """This server has accepted such clients since it shipped."""
    assert oauth._check_pkce(_entry(""), "") is None


def test_a_stray_verifier_on_an_unbound_code_is_ignored():
    assert oauth._check_pkce(_entry(""), VERIFIER) is None


def test_requiring_pkce_rejects_a_code_with_no_challenge(monkeypatch):
    monkeypatch.setenv("NUCLEUS_OAUTH_REQUIRE_PKCE", "true")
    err = oauth._check_pkce(_entry(""), "")
    assert err is not None and "PKCE is required" in err


def test_requiring_pkce_still_accepts_a_correct_verifier(monkeypatch):
    monkeypatch.setenv("NUCLEUS_OAUTH_REQUIRE_PKCE", "true")
    assert oauth._check_pkce(_entry(_challenge(VERIFIER)), VERIFIER) is None


# --- the challenge must survive the whole flow -----------------------------


def test_create_code_stores_the_challenge():
    store = oauth._OAuthStore()
    code = store.create_code(
        "client-1", "mcp:tools", "https://example.test/cb",
        code_challenge=_challenge(VERIFIER), code_challenge_method="S256",
    )
    entry = store.consume_code(code)
    assert entry["code_challenge"] == _challenge(VERIFIER)
    assert entry["code_challenge_method"] == "S256"


def test_create_code_without_pkce_stores_empty_strings():
    store = oauth._OAuthStore()
    entry = store.consume_code(
        store.create_code("client-1", "mcp:tools", "https://example.test/cb")
    )
    assert entry["code_challenge"] == "" and entry["code_challenge_method"] == ""


def test_the_consent_form_carries_the_challenge_through_its_post():
    """Without hidden fields the challenge is lost across the consent POST."""
    import ast

    source = Path(oauth.__file__).read_text(encoding="utf-8")
    assert 'name="code_challenge"' in source, (
        "the consent form drops code_challenge, so PKCE is silently lost on the "
        "path most users take"
    )
    assert 'name="code_challenge_method"' in source

    tree = ast.parse(source)
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "authorize"
    )
    body = ast.unparse(fn)
    assert 'form.get(\'code_challenge\'' in body or 'form.get("code_challenge"' in body, (
        "authorize() never reads code_challenge back off the form body"
    )


def test_both_code_issuing_paths_bind_the_challenge():
    """The Clerk path must bind it too, or verified sign-in loses PKCE."""
    import ast

    tree = ast.parse(Path(oauth.__file__).read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_code"
    ]
    assert calls, "no create_code call sites found; this test needs updating"
    for call in calls:
        kwargs = {kw.arg for kw in call.keywords}
        assert "code_challenge" in kwargs, (
            f"create_code at line {call.lineno} mints a code without binding the "
            "PKCE challenge"
        )
