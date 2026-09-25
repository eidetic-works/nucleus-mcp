"""The auth architecture doc must describe the stack that ships (AU-4).

`docs/AUTH_ARCHITECTURE.md` described HTTP/SSE authentication as "Phase 3",
"months away", with an unchecked implementation checklist — while
`http_transport/` shipped a complete OAuth 2.1 authorization server, tenant
resolution and per-request brain isolation, none of it going through
`runtime/auth/`. Someone reading it to understand the network security posture
would have concluded there was none.

A prose document cannot be fully pinned by a test. What these tests pin is the
specific way it went wrong: the doc claiming the HTTP surface is unbuilt, and
the doc failing to mention the modules that actually authenticate requests.
They also pin the structural fact the doc now asserts — that `http_transport/`
does not go through `runtime/auth/` — so that wiring the two together forces the
doc to be revisited.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "AUTH_ARCHITECTURE.md"
HTTP_TRANSPORT = ROOT / "src" / "mcp_server_nucleus" / "http_transport"

pytestmark = pytest.mark.skipif(not DOC.exists(), reason="auth doc not in this export")


@pytest.fixture(scope="module")
def doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_the_doc_names_the_modules_that_actually_authenticate(doc):
    """The old version named neither."""
    for module in ("tenant.py", "oauth_server.py"):
        assert module in doc, (
            f"the auth architecture doc never mentions {module}, which is where "
            "HTTP requests are actually authenticated"
        )


def test_the_doc_does_not_call_the_http_surface_unbuilt(doc):
    """It shipped. Calling it future work is how the doc misled."""
    # Only flag these where they are asserting status, not where the doc is
    # explaining the correction it made.
    body = doc.split("## The two transports", 1)[-1]
    for phrase in ("Phase 3", "Future Architecture", "months away"):
        assert phrase not in body, (
            f"the doc still describes the shipping HTTP auth as {phrase!r}"
        )


def test_the_doc_records_that_the_rigorous_provider_is_unwired(doc):
    assert "jwt_provider" in doc and "Unwired" in doc, (
        "the doc does not say that runtime/auth/jwt_provider.py never runs, which "
        "is the trap that made the old version plausible"
    )


def test_the_doc_states_that_dcr_takes_no_auth(doc):
    """The single most important thing an operator needs to know here."""
    assert re.search(r"DCR takes no authentication|/register.*no auth", doc, re.I), (
        "the doc does not warn that dynamic client registration is unauthenticated"
    )


@pytest.mark.skipif(not HTTP_TRANSPORT.is_dir(), reason="http_transport not present")
def test_http_transport_still_does_not_import_runtime_auth():
    """The structural claim the doc makes. Wiring them must revisit the doc."""
    offenders = []
    for path in sorted(HTTP_TRANSPORT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"from\s+\.{0,3}(?:mcp_server_nucleus\.)?runtime\.auth\b", text) or \
           re.search(r"import\s+mcp_server_nucleus\.runtime\.auth\b", text):
            offenders.append(path.name)
    assert not offenders, (
        f"{offenders} now import runtime.auth. That may well be the right change — "
        "AU-4 is about the rigorous provider being unused — but docs/AUTH_ARCHITECTURE.md "
        "states the two stacks share no code path, so update it and this test together."
    )
