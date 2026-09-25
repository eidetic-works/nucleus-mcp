"""Server-side self-recursion guard + limit-clamp semantics — v0.2
read_inbox truth-in-signaling bundle, items (a) and (b).

Item (a): relay_route handlers dispatch into relay_ops functions that
contain the PR-A v0.1 ``is_http_mode()`` swap-point. A server process
running with NUCLEUS_RELAY_URL set (e.g. an OCI box that is ALSO a relay
client of another relay) would loop back into itself over HTTP unbounded.
Pre-existing since PR-A v0.1; never test-caught because conftest delenvs
NUCLEUS_RELAY_URL. These tests set the env var ON and assert the route
handlers stay on the FS path (``force_fs=True`` threading).

Item (b): the GET clamp ceiling was 100 while relay_context_sync asks
limit=200 — silent truncation. Ceiling is now 200 and has_more signals
truncation honestly.

Tripwire: relay_transport._http_call is monkeypatched to raise — any
escape from the FS path explodes loudly instead of recursing.
"""
import json
from datetime import datetime, timezone

import httpx
import pytest
from starlette.applications import Starlette


def _boom(*args, **kwargs):
    raise AssertionError(
        "self-recursion: route handler escaped to relay_transport._http_call"
    )


@pytest.fixture
def relay_app(tmp_path, monkeypatch):
    """Starlette app with HTTP-mode env SET (the recursion trap armed)."""
    brain = tmp_path / "brain"
    brain.mkdir()
    (brain / "relay").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(
        "NUCLEUS_RELAY_TOKEN_MAP",
        # RL-1 binds GET/ACK/status to the token owner: an agent reads only its
        # own inbox. tok-cowork owns it; tok-good stays the poster.
        json.dumps({"tok-good": "test_sender", "tok-cowork": "cowork"}),
    )
    # The trap: this is what a server process with relay-client env looks
    # like. Without force_fs threading, every handler below would recurse.
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.example.com")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "trap-bearer")

    from mcp_server_nucleus.runtime import relay_transport as rt
    monkeypatch.setattr(rt, "_http_call", _boom)

    from mcp_server_nucleus.http_transport import relay_route as rr
    rr._buckets.clear()
    rr._idem_cache.clear()

    app = Starlette(
        routes=[
            rr.relay_route,
            rr.relay_get_route,
            rr.relay_ack_route,
            rr.relay_status_route,
        ]
    )
    return app, brain


def _write_envelope(brain, recipient, n, read=False):
    """Drop a minimal envelope file directly into the recipient's inbox."""
    inbox = brain / "relay" / recipient
    inbox.mkdir(parents=True, exist_ok=True)
    msg_id = f"relay_20260610_{n:06d}_{n:08x}"
    envelope = {
        "id": msg_id,
        "from": "test_sender",
        "to": recipient,
        "subject": f"msg {n}",
        "body": f"body {n}",
        "priority": "normal",
        "read": read,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (inbox / f"20260610_{n:06d}_{msg_id}.json").write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    return msg_id


@pytest.mark.asyncio
async def test_post_route_writes_fs_not_http(relay_app):
    app, brain = relay_app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/relay/cowork",
            headers={"Authorization": "Bearer tok-good"},
            json={"subject": "hello", "body": "fs write please", "sender": "test_sender", "sender_anchor": {"role": "test_sender", "transport": "http"}},
        )
    assert resp.status_code == 202, resp.text
    files = list((brain / "relay" / "cowork").glob("*.json"))
    assert len(files) == 1, "envelope must land on the server's own FS"


@pytest.mark.asyncio
async def test_get_route_reads_fs_not_http(relay_app):
    app, brain = relay_app
    _write_envelope(brain, "cowork", 1)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/relay/cowork",
            headers={"Authorization": "Bearer tok-cowork"},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["count"] == 1
    assert data["messages"][0]["subject"] == "msg 1"


@pytest.mark.asyncio
async def test_ack_route_marks_fs_file_not_http(relay_app):
    app, brain = relay_app
    msg_id = _write_envelope(brain, "cowork", 2)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/relay/cowork/ack",
            headers={"Authorization": "Bearer tok-cowork"},
            json={"message_ids": [msg_id]},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["acked"] == 1
    on_disk = json.loads(
        next((brain / "relay" / "cowork").glob("*.json")).read_text(encoding="utf-8")
    )
    assert on_disk["read"] is True


@pytest.mark.asyncio
async def test_status_route_returns_real_fs_stats_not_http_stub(relay_app):
    """Without force_fs, relay_status() returns the v0.1 stub
    (mailboxes={}) when NUCLEUS_RELAY_URL is set — the status route would
    silently report an empty relay even with messages on disk."""
    app, brain = relay_app
    _write_envelope(brain, "cowork", 3)
    _write_envelope(brain, "cowork", 4)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/relay/cowork/status",
            headers={"Authorization": "Bearer tok-cowork"},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["queue_depth"] == 2
    assert data["unread"] == 2


@pytest.mark.asyncio
async def test_get_limit_200_returns_full_page_no_false_truncation(relay_app):
    """Bundle item (b): the old clamp (100) silently truncated the
    relay_context_sync limit=200 ask. 120 messages + limit=200 must come
    back complete with has_more=False."""
    app, brain = relay_app
    for n in range(120):
        _write_envelope(brain, "cowork", n)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/relay/cowork?limit=200",
            headers={"Authorization": "Bearer tok-cowork"},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["count"] == 120
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_limit_100_signals_has_more(relay_app):
    app, brain = relay_app
    for n in range(120):
        _write_envelope(brain, "cowork", n)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/relay/cowork?limit=100",
            headers={"Authorization": "Bearer tok-cowork"},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["count"] == 100
    assert data["has_more"] is True


@pytest.mark.asyncio
async def test_get_limit_above_ceiling_clamps_to_200(relay_app):
    app, brain = relay_app
    for n in range(3):
        _write_envelope(brain, "cowork", n)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/relay/cowork?limit=9999",
            headers={"Authorization": "Bearer tok-cowork"},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["count"] == 3
