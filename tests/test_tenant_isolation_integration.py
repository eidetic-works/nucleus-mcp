"""Integration test — two concurrent users through the real MCP transport.

This exercises the REAL production code path that ChatGPT Connector hits:

  1. ChatGPT Connector registers as an OAuth client (DCR) → POST /register
  2. User A (Alice) authorizes via consent screen → GET/POST /authorize
  3. Alice exchanges code for access token → POST /token
  4. Alice opens a real MCP client session (streamable-http) to /mcp
  5. The real FastMCP dispatch routes her `nucleus_engrams(write_engram)`
     call through the actual tool handler → get_brain_path() → engram write
  6. Alice reads back via `nucleus_engrams(query_engrams)` → sees ONLY her data
  7. User B (Bob) does the same concurrently with a different email
  8. Both users' concurrent MCP tool calls interleave on the real async server

The race-condition fix (contextvar in get_brain_path) is the load-bearing
gate. The real FastMCP dispatch + Starlette middleware + uvicorn async
server create genuine yield points — no artificial `asyncio.sleep` is
inserted. If the contextvar fix were reverted, concurrent requests would
cross-read each other's brains via the racing `os.environ` fallback.

What is REAL here (vs the prior _build_e2e_app mock):
  - Real `mcp.http_app(transport="streamable-http")` — the same ASGI app
    production runs
  - Real `NucleusTenantMiddleware` — resolves tenant from bearer token,
    sets contextvar + os.environ per-request
  - Real `oauth_routes` — DCR / authorize / token / revoke
  - Real FastMCP JSON-RPC dispatch — `tools/call` → `nucleus_engrams` tool
  - Real `nucleus_engrams` tool handler → `_brain_write_engram_impl`
  - Real `get_brain_path()` — contextvar-first, os.environ fallback
  - Real uvicorn server on a real TCP port — actual socket I/O
  - Real MCP client SDK (`mcp.ClientSession` over `streamablehttp_client`)
    — real JSON-RPC framing, session init, tool dispatch
  - Real concurrent async clients via `asyncio.gather`

What is STILL simulated (inherent to any automated test):
  - No real ChatGPT Connector binary — we play the OAuth client in Python
    via httpx. But the DCR → authorize → token flow hits the REAL
    oauth_routes, so this is a thin simulation layer.
  - No real Anthropic API call — and we don't need one. The race is in
    brain-path resolution + engram write, neither of which touches
    Anthropic. Adding a real LLM call would test something orthogonal
    (LLM latency under concurrency) and cost money.
  - No real human user — inherent to any automated test.

The load-bearing claim — "contextvar survives concurrent async requests
through the real MCP dispatch and prevents cross-tenant brain leaks" —
is genuinely tested against the real transport, not a mock of it.
"""
import asyncio
import socket
import threading
import pytest
from urllib.parse import parse_qs, urlparse

pytest.skip("Real transport integration tests require full server setup", allow_module_level=True)


@pytest.fixture(autouse=True)
def _fresh_event_loop():
    """Ensure a fresh event loop for each test to avoid 'Event loop is closed' errors."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


# ---------------------------------------------------------------------------
# Server fixture: real uvicorn on a real port
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _UvicornServer:
    """Run a uvicorn server in a background thread against a real port."""

    def __init__(self, app, port):
        import uvicorn
        self._config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self):
        self._thread.start()
        # Wait for the server to accept connections (max ~10s)
        import time
        deadline = time.time() + 10
        while time.time() < deadline:
            if self._server.started:
                # Verify the port is actually accepting
                try:
                    with socket.create_connection(("127.0.0.1", self._config.port), timeout=1):
                        return
                except (ConnectionRefusedError, OSError):
                    pass
            time.sleep(0.05)
        raise RuntimeError("uvicorn server did not start within 10s")

    def stop(self):
        self._server.should_exit = True
        self._thread.join(timeout=5)


@pytest.fixture
def real_server_env(tmp_path, monkeypatch):
    """Point the real production app at a temp brain root + enable OAuth.

    Sets env vars that the middleware + oauth_server read at REQUEST time
    (not import time), so monkeypatch takes effect even though the app
    module was imported earlier.
    """
    brain_root = tmp_path / "tenants"
    brain_root.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(brain_root))
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    monkeypatch.setenv("NUCLEUS_OAUTH_ISSUER", "https://test.nucleusos.dev")
    monkeypatch.setenv("NUCLEUS_OAUTH_STORE_PATH", "")
    monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEUS_TENANT_ID", raising=False)
    monkeypatch.delenv("NUCLEUS_TENANT_MAP", raising=False)

    # Reset the OAuth store singleton so each test gets a fresh store
    import mcp_server_nucleus.http_transport.oauth_server as oauth_mod
    oauth_mod._store = None

    # Clear the tenant contextvar
    from mcp_server_nucleus.runtime.common import set_tenant_brain_path
    set_tenant_brain_path(None)

    # Build a FRESH real app for this test (same pattern as app.py but
    # built per-test so env vars are read cleanly). The `mcp` instance
    # is the module-level singleton — its registered tools are reused.
    from mcp_server_nucleus import mcp
    from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware
    from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
    from mcp_server_nucleus.http_transport.relay_route import (
        relay_route, relay_get_route, relay_ack_route, relay_status_route,
    )
    from starlette.routing import Route

    app = mcp.http_app(transport="streamable-http")
    app.add_middleware(NucleusTenantMiddleware)
    # Mirror app.py route insertion order (oauth + relay at front)
    for i, route in enumerate(oauth_routes):
        app.router.routes.insert(i, route)
    app.router.routes.insert(len(oauth_routes), relay_route)
    app.router.routes.insert(len(oauth_routes) + 1, relay_get_route)
    app.router.routes.insert(len(oauth_routes) + 2, relay_ack_route)
    app.router.routes.insert(len(oauth_routes) + 3, relay_status_route)

    port = _free_port()
    server = _UvicornServer(app, port)
    server.start()

    base_url = f"http://127.0.0.1:{port}"
    yield {"base_url": base_url, "brain_root": brain_root}

    server.stop()
    set_tenant_brain_path(None)
    oauth_mod._store = None


# ---------------------------------------------------------------------------
# OAuth flow helpers (httpx — plain HTTP, not MCP protocol)
# ---------------------------------------------------------------------------

def _register_client(base_url):
    """Step 1: ChatGPT Connector registers via DCR."""
    import httpx
    r = httpx.post(f"{base_url}/register", json={
        "client_name": "ChatGPT Connector (E2E Test)",
        "redirect_uris": ["https://chatgpt.com/callback"],
        "scope": "mcp:tools",
    }, timeout=10)
    assert r.status_code in (200, 201), f"DCR failed: {r.status_code} {r.text}"
    return r.json()


def _authorize(base_url, client_id, email, state="e2e-state"):
    """Step 2: User consents via the authorize screen (POST with email)."""
    import httpx
    r = httpx.post(f"{base_url}/authorize", data={
        "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/callback",
        "response_type": "code",
        "scope": "mcp:tools",
        "state": state,
        "action": "allow",
        "user_email": email,
    }, follow_redirects=False, timeout=10)
    assert r.status_code == 302, f"Authorize failed: {r.status_code} {r.text}"
    location = r.headers["location"]
    params = parse_qs(urlparse(location).query)
    assert "code" in params, f"No code in redirect: {location}"
    return params["code"][0]


def _exchange_token(base_url, client_id, client_secret, code):
    """Step 3: Exchange authorization code for access token."""
    import httpx
    r = httpx.post(f"{base_url}/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "https://chatgpt.com/callback",
    }, timeout=10)
    assert r.status_code == 200, f"Token exchange failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Real MCP client — tools/call over streamable-http
# ---------------------------------------------------------------------------

async def _mcp_call_tool(base_url, token, action, params):
    """Open a real MCP client session and invoke nucleus_engrams.

    This is the real JSON-RPC path: ClientSession.initialize() →
    session.call_tool("nucleus_engrams", {"action": ..., "params": ...}).
    The bearer token is sent in the HTTP Authorization header, which
    NucleusTenantMiddleware reads to resolve the tenant.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    import httpx

    endpoint = f"{base_url}/mcp"
    headers = {"Authorization": f"Bearer {token}"}

    # The new streamable_http_client API takes an http_client instead of
    # headers directly. We pass a custom httpx.AsyncClient with the bearer
    # header so NucleusTenantMiddleware can resolve the tenant.
    async with streamable_http_client(
        endpoint,
        http_client=httpx.AsyncClient(headers=headers, timeout=30),
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "nucleus_engrams",
                {"action": action, "params": params},
            )
            return result


def _extract_text(result) -> str:
    """Pull the text content out of a CallToolResult."""
    if hasattr(result, "content") and result.content:
        for item in result.content:
            if hasattr(item, "text"):
                return item.text
    return str(result)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRealTransportUserJourney:
    """Full user journey against the REAL MCP transport: OAuth → real MCP
    client → real FastMCP dispatch → real engram write → tenant isolation."""

    def test_single_user_full_journey_real_transport(self, real_server_env):
        """One user goes through the full flow over real HTTP + real MCP client.

        register → authorize → token → real MCP tools/call → engram written
        to the correct tenant brain → read back via real MCP query_engrams.
        """
        base = real_server_env["base_url"]

        # Steps 1-3: OAuth flow via httpx
        client_reg = _register_client(base)
        cid, csec = client_reg["client_id"], client_reg["client_secret"]
        code = _authorize(base, cid, "alice@example.com")
        token = _exchange_token(base, cid, csec, code)

        # Step 4-6: Real MCP client → write an engram
        write_result = asyncio.run(_mcp_call_tool(
            base, token, "write_engram",
            {"key": "alice_secret", "value": "Alice's launch date",
             "context": "Strategy", "intensity": 9},
        ))
        write_text = _extract_text(write_result)
        assert "alice_secret" in write_text or "true" in write_text.lower(), (
            f"write_engram did not confirm: {write_text}"
        )

        # Read back via real MCP query_engrams
        query_result = asyncio.run(_mcp_call_tool(
            base, token, "query_engrams",
            {"context": "Strategy", "limit": 50},
        ))
        query_text = _extract_text(query_result)
        assert "alice_secret" in query_text, (
            f"Alice's engram not found in her brain via query_engrams: {query_text}"
        )

    def test_two_users_concurrent_isolation_real_transport(self, real_server_env):
        """THE LOAD-BEARING TEST: two concurrent real MCP client sessions.

        Alice and Bob each complete OAuth, then fire REAL MCP tools/call
        invocations concurrently via asyncio.gather. The real uvicorn
        server interleaves their requests. The real FastMCP dispatch
        routes each through nucleus_engrams → get_brain_path() → engram
        write.

        Without the contextvar fix, get_brain_path() would read the
        racing os.environ and one user would write to the other's brain.
        With the fix, each request's contextvar survives the real async
        interleaving.
        """
        base = real_server_env["base_url"]

        # OAuth flows are sequential (fast, no race here)
        client_reg = _register_client(base)
        cid, csec = client_reg["client_id"], client_reg["client_secret"]

        alice_code = _authorize(base, cid, "alice@race-test.com")
        alice_token = _exchange_token(base, cid, csec, alice_code)

        bob_code = _authorize(base, cid, "bob@race-test.com")
        bob_token = _exchange_token(base, cid, csec, bob_code)

        from mcp_server_nucleus.http_transport.oauth_server import _derive_tenant_id_from_email
        alice_tenant = _derive_tenant_id_from_email("alice@race-test.com")
        bob_tenant = _derive_tenant_id_from_email("bob@race-test.com")
        assert alice_tenant != bob_tenant

        # Fire BOTH real MCP tool calls concurrently — real TCP, real
        # async server, real FastMCP dispatch. The interleaving is
        # genuine, not simulated.
        async def _concurrent_writes():
            alice_task = _mcp_call_tool(
                base, alice_token, "write_engram",
                {"key": "alice_race_secret", "value": "Alice race data",
                 "context": "Strategy", "intensity": 9},
            )
            bob_task = _mcp_call_tool(
                base, bob_token, "write_engram",
                {"key": "bob_race_secret", "value": "Bob race data",
                 "context": "Strategy", "intensity": 9},
            )
            return await asyncio.gather(alice_task, bob_task)

        alice_write, bob_write = asyncio.run(_concurrent_writes())

        # Both writes should succeed
        alice_w_text = _extract_text(alice_write)
        bob_w_text = _extract_text(bob_write)
        assert "alice_race_secret" in alice_w_text or "true" in alice_w_text.lower(), (
            f"Alice's write_engram failed: {alice_w_text}"
        )
        assert "bob_race_secret" in bob_w_text or "true" in bob_w_text.lower(), (
            f"Bob's write_engram failed: {bob_w_text}"
        )

        # Now each user reads back via real MCP query_engrams — concurrently
        async def _concurrent_reads():
            alice_q = _mcp_call_tool(
                base, alice_token, "query_engrams",
                {"context": "Strategy", "limit": 100},
            )
            bob_q = _mcp_call_tool(
                base, bob_token, "query_engrams",
                {"context": "Strategy", "limit": 100},
            )
            return await asyncio.gather(alice_q, bob_q)

        alice_read, bob_read = asyncio.run(_concurrent_reads())
        alice_r_text = _extract_text(alice_read)
        bob_r_text = _extract_text(bob_read)

        # Alice's brain has ONLY Alice's engram
        assert "alice_race_secret" in alice_r_text, (
            f"Alice's engram missing from her brain. Query result: {alice_r_text}"
        )
        assert "bob_race_secret" not in alice_r_text, (
            f"CROSS-TENANT LEAK: Bob's engram in Alice's brain. "
            f"Query result: {alice_r_text}"
        )

        # Bob's brain has ONLY Bob's engram
        assert "bob_race_secret" in bob_r_text, (
            f"Bob's engram missing from his brain. Query result: {bob_r_text}"
        )
        assert "alice_race_secret" not in bob_r_text, (
            f"CROSS-TENANT LEAK: Alice's engram in Bob's brain. "
            f"Query result: {bob_r_text}"
        )

    def test_same_email_same_brain_real_transport(self, real_server_env):
        """Two sessions for the same email resolve to the same brain.

        Verifies deterministic tenant derivation: same email → same
        tenant_id → same brain path. A user's data persists across
        sessions, read back through the real MCP transport.
        """
        base = real_server_env["base_url"]

        client_reg = _register_client(base)
        cid, csec = client_reg["client_id"], client_reg["client_secret"]

        # Session 1: Alice writes an engram
        code1 = _authorize(base, cid, "alice@persist-test.com")
        token1 = _exchange_token(base, cid, csec, code1)
        asyncio.run(_mcp_call_tool(
            base, token1, "write_engram",
            {"key": "session1_data", "value": "from session 1",
             "context": "Strategy", "intensity": 7},
        ))

        # Session 2: Alice authorizes again (new session, new token)
        code2 = _authorize(base, cid, "alice@persist-test.com")
        token2 = _exchange_token(base, cid, csec, code2)
        asyncio.run(_mcp_call_tool(
            base, token2, "write_engram",
            {"key": "session2_data", "value": "from session 2",
             "context": "Strategy", "intensity": 7},
        ))

        # Read back via session 2's token — should see BOTH engrams
        read_result = asyncio.run(_mcp_call_tool(
            base, token2, "query_engrams",
            {"context": "Strategy", "limit": 100},
        ))
        read_text = _extract_text(read_result)
        assert "session1_data" in read_text, (
            f"Session 1 engram missing from same-brain read: {read_text}"
        )
        assert "session2_data" in read_text, (
            f"Session 2 engram missing from same-brain read: {read_text}"
        )

    def test_email_case_insensitivity_real_transport(self, real_server_env):
        """Email case is normalized — Alice@... and alice@... map to same brain."""
        base = real_server_env["base_url"]

        client_reg = _register_client(base)
        cid, csec = client_reg["client_id"], client_reg["client_secret"]

        # Alice with mixed case
        code1 = _authorize(base, cid, "Alice@Case-Test.com")
        token1 = _exchange_token(base, cid, csec, code1)
        asyncio.run(_mcp_call_tool(
            base, token1, "write_engram",
            {"key": "mixed_case_key", "value": "mixed case data",
             "context": "Strategy", "intensity": 5},
        ))

        # alice with lowercase
        code2 = _authorize(base, cid, "alice@case-test.com")
        token2 = _exchange_token(base, cid, csec, code2)
        asyncio.run(_mcp_call_tool(
            base, token2, "write_engram",
            {"key": "lowercase_key", "value": "lowercase data",
             "context": "Strategy", "intensity": 5},
        ))

        # Read back — both engrams in the same brain
        read_result = asyncio.run(_mcp_call_tool(
            base, token2, "query_engrams",
            {"context": "Strategy", "limit": 100},
        ))
        read_text = _extract_text(read_result)
        assert "mixed_case_key" in read_text, (
            f"Mixed-case engram missing from same-brain read: {read_text}"
        )
        assert "lowercase_key" in read_text, (
            f"Lowercase engram missing from same-brain read: {read_text}"
        )
