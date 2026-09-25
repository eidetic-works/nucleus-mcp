"""End-to-end user journey simulation — two concurrent users through the
full ChatGPT Connector flow, verifying per-tenant isolation at every step.

This simulates the real user journey:
  1. ChatGPT Connector registers as an OAuth client (DCR)
  2. User A (Alice) authorizes via consent screen → gets auth code
  3. Alice exchanges code for access token (tenant_id derived from email)
  4. Alice calls the MCP endpoint with her bearer token
  5. The handler resolves her brain via get_brain_path() (contextvar fix)
  6. Alice writes a private engram → stored in HER brain only
  7. User B (Bob) does the same concurrently with a different email
  8. Both users read back → each sees ONLY their own data

The race condition fix (contextvar in get_brain_path) is the load-bearing
gate. Without it, step 5 would read the OTHER user's brain because
os.environ was overwritten during the concurrent request.
"""
import asyncio
import json
import os
import pytest
from urllib.parse import parse_qs, urlparse


@pytest.fixture
def e2e_env(tmp_path, monkeypatch):
    """Full E2E environment: brain root + OAuth + auth required."""
    brain_root = tmp_path / "tenants"
    brain_root.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(brain_root))
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    monkeypatch.setenv("NUCLEUS_OAUTH_ISSUER", "https://test.nucleusos.dev")
    monkeypatch.setenv("NUCLEUS_OAUTH_STORE_PATH", "")
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
    # AU-2 made per-email tenant binding from the self-hosted /authorize form
    # opt-in, because the form's email was self-asserted and unverified. These
    # tests are about tenant ISOLATION and the TN-4 background-thread race, not
    # about email verification, so they take the documented opt-in to reach the
    # per-tenant code path they were written to exercise.
    monkeypatch.setenv("NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL", "true")
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)

    # Reset the OAuth store singleton so each test gets a fresh store
    import mcp_server_nucleus.http_transport.oauth_server as oauth_mod
    oauth_mod._store = None

    # Clear the tenant contextvar
    from mcp_server_nucleus.runtime.common import set_tenant_brain_path
    set_tenant_brain_path(None)

    yield brain_root

    # Cleanup
    set_tenant_brain_path(None)
    oauth_mod._store = None


def _build_e2e_app():
    """Build a Starlette app that simulates the full ChatGPT Connector flow.

    Includes:
      - OAuth routes (register, authorize, token)
      - NucleusTenantMiddleware (resolves tenant from bearer token)
      - A simulated MCP tool endpoint that calls get_brain_path() + engram ops
    """
    from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware
    from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
    from mcp_server_nucleus.runtime.common import get_brain_path
    from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def mcp_tool_handler(request):
        """Simulates an MCP tools/call invocation.

        In the real system, the MCP protocol (JSON-RPC over streamable HTTP)
        dispatches to tool handlers. This handler does what a real tool
        handler does: call get_brain_path() to resolve the tenant's brain,
        then perform engram operations.

        The await here simulates the async yield point where the race
        condition would trigger under concurrent load.
        """
        # Yield to the event loop — this is the race window where
        # os.environ gets overwritten by the other tenant's request
        await asyncio.sleep(0.05)

        brain = get_brain_path()
        tenant = getattr(request.state, "nucleus_tenant_id", "unknown")

        # Simulate a write_engram tool call.
        # We use MemoryPipeline directly with the explicit brain path instead
        # of _brain_write_engram_impl because the latter calls get_brain_path()
        # internally via a module-level import that can become stale when other
        # tests evict mcp_server_nucleus.runtime.* from sys.modules.
        body = await request.json()
        key = body.get("key", f"test_{tenant}")
        value = body.get("value", f"value for {tenant}")

        pipeline = MemoryPipeline(brain)
        pipeline.process(
            text=value,
            context="Strategy",
            intensity=9,
            source_agent="brain_write_engram",
            key=key,
        )

        # Read back the ledger to prove the engram landed in THIS brain
        ledger = brain / "engrams" / "ledger.jsonl"
        lines = [l for l in ledger.read_text().splitlines() if l.strip()]
        keys = [json.loads(l)["key"] for l in lines]

        return JSONResponse({
            "tenant": tenant,
            "brain_path": str(brain),
            "brain_basename": brain.name,
            "written_key": key,
            "ledger_keys": keys,
        })

    routes = list(oauth_routes) + [
        Route("/mcp/tools/call", mcp_tool_handler, methods=["POST"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(NucleusTenantMiddleware)
    return app


def _register_client(client):
    """Step 1: ChatGPT Connector registers via DCR."""
    r = client.post("/register", json={
        "client_name": "ChatGPT Connector (E2E Test)",
        "redirect_uris": ["https://chatgpt.com/callback"],
        "scope": "mcp:tools",
    })
    assert r.status_code in (200, 201), f"DCR failed: {r.text}"
    return r.json()


def _authorize(client, client_id, email, state="e2e-state"):
    """Step 2: User consents via the authorize screen (POST with email).

    Returns the authorization code extracted from the redirect.
    """
    r = client.post("/authorize", data={
        "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/callback",
        "response_type": "code",
        "scope": "mcp:tools",
        "state": state,
        "action": "allow",
        "user_email": email,
    }, follow_redirects=False)
    assert r.status_code == 302, f"Authorize failed: {r.status_code} {r.text}"
    location = r.headers["location"]
    params = parse_qs(urlparse(location).query)
    assert "code" in params, f"No code in redirect: {location}"
    return params["code"][0]


def _exchange_token(client, client_id, client_secret, code):
    """Step 3: Exchange authorization code for access token."""
    r = client.post("/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "https://chatgpt.com/callback",
    })
    assert r.status_code == 200, f"Token exchange failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _call_tool(client, token, key, value):
    """Step 4-6: Call the MCP tool endpoint with the bearer token.

    The handler resolves the tenant's brain and writes an engram.
    """
    r = client.post("/mcp/tools/call", json={"key": key, "value": value},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Tool call failed: {r.status_code} {r.text}"
    return r.json()


class TestUserJourneyE2E:
    """Full user journey: OAuth → token → MCP tool call → tenant isolation."""

    def test_single_user_full_journey(self, e2e_env):
        """One user goes through the full flow end-to-end.

        Verifies the basic pipeline works: register → authorize → token →
        tool call → engram written to the correct tenant brain.
        """
        from starlette.testclient import TestClient

        app = _build_e2e_app()
        with TestClient(app) as http:
            # Step 1: ChatGPT Connector registers
            client_reg = _register_client(http)
            client_id = client_reg["client_id"]
            client_secret = client_reg["client_secret"]

            # Step 2: Alice authorizes
            code = _authorize(http, client_id, "alice@example.com")

            # Step 3: Exchange for token
            token = _exchange_token(http, client_id, client_secret, code)

            # Step 4-6: Call MCP tool
            result = _call_tool(http, token, "alice_secret", "Alice's launch date")

            # Verify
            from mcp_server_nucleus.http_transport.oauth_server import _derive_tenant_id_from_email
            expected_tenant = _derive_tenant_id_from_email("alice@example.com")
            assert result["tenant"] == expected_tenant
            assert expected_tenant in result["brain_path"]
            assert "alice_secret" in result["ledger_keys"]

    def test_two_users_sequential_isolation(self, e2e_env):
        """Two users go through the full flow sequentially.

        Each user's engram lands in their own brain; neither can see
        the other's data.
        """
        from starlette.testclient import TestClient

        app = _build_e2e_app()
        with TestClient(app) as http:
            client_reg = _register_client(http)
            cid, csec = client_reg["client_id"], client_reg["client_secret"]

            # Alice's journey
            alice_code = _authorize(http, cid, "alice@seq-test.com")
            alice_token = _exchange_token(http, cid, csec, alice_code)
            alice_result = _call_tool(http, alice_token, "alice_seq_secret", "Alice seq data")

            # Bob's journey
            bob_code = _authorize(http, cid, "bob@seq-test.com")
            bob_token = _exchange_token(http, cid, csec, bob_code)
            bob_result = _call_tool(http, bob_token, "bob_seq_secret", "Bob seq data")

            # Verify isolation
            assert alice_result["tenant"] != bob_result["tenant"]
            assert alice_result["brain_path"] != bob_result["brain_path"]

            # Alice's brain has only Alice's engram
            assert "alice_seq_secret" in alice_result["ledger_keys"]
            assert "bob_seq_secret" not in alice_result["ledger_keys"]

            # Bob's brain has only Bob's engram
            assert "bob_seq_secret" in bob_result["ledger_keys"]
            assert "alice_seq_secret" not in bob_result["ledger_keys"]

    async def test_two_users_concurrent_isolation_race_fix(self, e2e_env):
        """Two users make concurrent MCP tool calls — the race condition test.

        This is the load-bearing E2E test. Both users call the MCP tool
        endpoint at the same time. The handler yields (await asyncio.sleep)
        before calling get_brain_path(), which is the exact race window.

        Without the contextvar fix, the second request's middleware would
        overwrite os.environ["NUCLEUS_BRAIN_PATH"] during the first
        request's await, causing the first request to read the second
        user's brain.

        With the fix, each request's contextvar survives the await.

        Uses httpx.AsyncClient with ASGITransport for the entire test —
        both OAuth setup and concurrent tool calls — as an async test
        managed by pytest-asyncio. This avoids TestClient (which manages
        its own event loop) and ensures contextvars propagate correctly
        through BaseHTTPMiddleware.
        """
        import httpx
        from mcp_server_nucleus.http_transport.oauth_server import _derive_tenant_id_from_email

        app = _build_e2e_app()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
            # Step 1: Register OAuth client
            r = await http.post("/register", json={
                "client_name": "ChatGPT Connector (E2E Test)",
                "redirect_uris": ["https://chatgpt.com/callback"],
                "scope": "mcp:tools",
            })
            assert r.status_code in (200, 201), f"DCR failed: {r.text}"
            client_reg = r.json()
            cid, csec = client_reg["client_id"], client_reg["client_secret"]

            # Step 2-3: Alice + Bob each complete OAuth sequentially
            async def _do_oauth(email):
                r = await http.post("/authorize", data={
                    "client_id": cid,
                    "redirect_uri": "https://chatgpt.com/callback",
                    "response_type": "code",
                    "scope": "mcp:tools",
                    "state": "e2e-state",
                    "action": "allow",
                    "user_email": email,
                }, follow_redirects=False)
                assert r.status_code == 302, f"Authorize failed: {r.status_code} {r.text}"
                location = r.headers["location"]
                params = parse_qs(urlparse(location).query)
                assert "code" in params, f"No code in redirect: {location}"
                code = params["code"][0]

                r = await http.post("/token", data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": cid,
                    "client_secret": csec,
                    "redirect_uri": "https://chatgpt.com/callback",
                })
                assert r.status_code == 200, f"Token exchange failed: {r.status_code} {r.text}"
                return r.json()["access_token"]

            alice_token = await _do_oauth("alice@race-test.com")
            bob_token = await _do_oauth("bob@race-test.com")

            alice_tenant = _derive_tenant_id_from_email("alice@race-test.com")
            bob_tenant = _derive_tenant_id_from_email("bob@race-test.com")
            assert alice_tenant != bob_tenant

            # Step 4: Fire BOTH tool calls concurrently with asyncio.gather.
            # This properly interleaves at await points within a single
            # event loop — the real production scenario (Starlette + uvicorn).
            async def _tool_call(token, key, value):
                r = await http.post(
                    "/mcp/tools/call",
                    json={"key": key, "value": value},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert r.status_code == 200, f"Tool call failed: {r.status_code} {r.text}"
                return r.json()

            alice_result, bob_result = await asyncio.gather(
                _tool_call(alice_token, "alice_race_secret", "Alice race data"),
                _tool_call(bob_token, "bob_race_secret", "Bob race data"),
            )

        # Verify each user got their OWN brain, not the other's
        assert alice_result["tenant"] == alice_tenant, (
            f"Alice got tenant {alice_result['tenant']}, expected {alice_tenant}. "
            f"CROSS-TENANT LEAK via race condition."
        )
        assert bob_result["tenant"] == bob_tenant, (
            f"Bob got tenant {bob_result['tenant']}, expected {bob_tenant}. "
            f"CROSS-TENANT LEAK via race condition."
        )

        assert alice_result["brain_path"] != bob_result["brain_path"]

        # Alice's brain has ONLY Alice's engram
        assert "alice_race_secret" in alice_result["ledger_keys"], (
            f"Alice's engram missing from her brain. Keys: {alice_result['ledger_keys']}"
        )
        assert "bob_race_secret" not in alice_result["ledger_keys"], (
            f"CROSS-TENANT LEAK: Bob's engram in Alice's brain. "
            f"Keys: {alice_result['ledger_keys']}"
        )

        # Bob's brain has ONLY Bob's engram
        assert "bob_race_secret" in bob_result["ledger_keys"], (
            f"Bob's engram missing from his brain. Keys: {bob_result['ledger_keys']}"
        )
        assert "alice_race_secret" not in bob_result["ledger_keys"], (
            f"CROSS-TENANT LEAK: Alice's engram in Bob's brain. "
            f"Keys: {bob_result['ledger_keys']}"
        )

    def test_same_email_same_brain(self, e2e_env):
        """Two sessions for the same email resolve to the same brain.

        This verifies the deterministic tenant derivation: same email →
        same tenant_id → same brain path. A user's data persists across
        sessions.
        """
        from starlette.testclient import TestClient

        app = _build_e2e_app()
        with TestClient(app) as http:
            client_reg = _register_client(http)
            cid, csec = client_reg["client_id"], client_reg["client_secret"]

            # Session 1: Alice writes an engram
            code1 = _authorize(http, cid, "alice@persist-test.com")
            token1 = _exchange_token(http, cid, csec, code1)
            result1 = _call_tool(http, token1, "session1_data", "from session 1")

            # Session 2: Alice authorizes again (new session)
            code2 = _authorize(http, cid, "alice@persist-test.com")
            token2 = _exchange_token(http, cid, csec, code2)
            result2 = _call_tool(http, token2, "session2_data", "from session 2")

            # Same tenant, same brain
            assert result1["tenant"] == result2["tenant"]
            assert result1["brain_path"] == result2["brain_path"]

            # Session 2's brain should contain BOTH engrams (same brain)
            assert "session1_data" in result2["ledger_keys"]
            assert "session2_data" in result2["ledger_keys"]

    def test_email_case_insensitivity(self, e2e_env):
        """Email case is normalized — Alice@... and alice@... map to same brain."""
        from starlette.testclient import TestClient
        from mcp_server_nucleus.http_transport.oauth_server import _derive_tenant_id_from_email

        app = _build_e2e_app()
        with TestClient(app) as http:
            client_reg = _register_client(http)
            cid, csec = client_reg["client_id"], client_reg["client_secret"]

            # Alice with mixed case
            code1 = _authorize(http, cid, "Alice@Case-Test.com")
            token1 = _exchange_token(http, cid, csec, code1)
            result1 = _call_tool(http, token1, "mixed_case_key", "mixed case data")

            # alice with lowercase
            code2 = _authorize(http, cid, "alice@case-test.com")
            token2 = _exchange_token(http, cid, csec, code2)
            result2 = _call_tool(http, token2, "lowercase_key", "lowercase data")

            # Same tenant_id (case-insensitive derivation)
            assert result1["tenant"] == result2["tenant"]
            assert result1["brain_path"] == result2["brain_path"]

            # Both engrams in the same brain
            assert "mixed_case_key" in result2["ledger_keys"]
            assert "lowercase_key" in result2["ledger_keys"]
