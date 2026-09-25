"""v0.2 bridge server amendments — POST id-preserve/dedup + ack session_id.

Covers the two route-level changes that make the relay bridge daemon's
push and ack-state sync lossless:
  (a) POST /relay/{recipient} preserves a well-formed caller-supplied
      body.id and dedups by it (202 duplicate:true on re-push), which
      keeps re-pushes idempotent across server restarts where the
      in-memory Idempotency-Key cache is lost.
  (b) POST /relay/{recipient}/ack threads payload.session_id through to
      relay_ack so per-session read markers round-trip.
"""
import json

import httpx
import pytest
from starlette.applications import Starlette


@pytest.fixture
def app_brain(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    brain.mkdir()
    (brain / "relay").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(
        "NUCLEUS_RELAY_TOKEN_MAP",
        # RL-1: GET/ACK/status are bound to the token owner — an agent reads only
        # its own inbox (docs/relay_bus_contract.md pairs Recipient Token ==
        # Sender Token for every role). tok-cowork owns the inbox under test;
        # tok-good stays the poster, since POST keeps no ownership check.
        json.dumps({"tok-good": "test_sender", "tok-cowork": "cowork"}),
    )
    from mcp_server_nucleus.http_transport import relay_route as rr
    rr._buckets.clear()
    rr._idem_cache.clear()
    app = Starlette(routes=[rr.relay_route, rr.relay_get_route, rr.relay_ack_route])
    return app, brain


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _body(**overrides):
    sender = overrides.get("sender", "test_sender")
    body = {
        "subject": "bridge push",
        "body": json.dumps({"summary": "hi"}),
        "sender": "test_sender",
        "priority": "normal",
        "sender_anchor": {"role": sender, "transport": "http"},
    }
    body.update(overrides)
    return body


def _auth(token="tok-good"):
    return {"Authorization": f"Bearer {token}"}


# ── (a) POST id-preserve + dedup ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_preserves_caller_id(app_brain):
    app, brain = app_brain
    mid = "relay_20260612_010101_deadbeef"
    async with _client(app) as c:
        r = await c.post("/relay/cowork", json=_body(id=mid), headers=_auth())
    assert r.status_code == 202, r.text
    j = r.json()
    assert j["message_id"] == mid
    assert j["duplicate"] is False
    files = list((brain / "relay" / "cowork").glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["id"] == mid


@pytest.mark.asyncio
async def test_post_duplicate_id_is_noop(app_brain):
    """Re-push with the same id (fresh Idempotency cache) must not double-write."""
    app, brain = app_brain
    mid = "relay_20260612_010101_deadbeef"
    from mcp_server_nucleus.http_transport import relay_route as rr
    async with _client(app) as c:
        r1 = await c.post("/relay/cowork", json=_body(id=mid), headers=_auth())
        assert r1.status_code == 202
        # Simulate server restart: idempotency cache wiped
        rr._idem_cache.clear()
        r2 = await c.post("/relay/cowork", json=_body(id=mid), headers=_auth())
    assert r2.status_code == 202, r2.text
    j2 = r2.json()
    assert j2["duplicate"] is True
    assert j2["message_id"] == mid
    files = list((brain / "relay" / "cowork").glob("*.json"))
    assert len(files) == 1, [f.name for f in files]


@pytest.mark.asyncio
async def test_post_malformed_id_rejected_fresh_mint(app_brain):
    """Ids failing the charset/length policy are ignored — fresh id minted."""
    app, brain = app_brain
    async with _client(app) as c:
        r = await c.post(
            "/relay/cowork", json=_body(id="../evil/path"), headers=_auth()
        )
    assert r.status_code == 202, r.text
    j = r.json()
    assert j["message_id"] != "../evil/path"
    assert j["message_id"].startswith("relay_")
    files = list((brain / "relay" / "cowork").glob("*.json"))
    assert len(files) == 1
    assert ".." not in files[0].name


@pytest.mark.asyncio
async def test_post_filename_tail_collision_is_not_duplicate(app_brain):
    """Crack-2 (PR #570 peer verdict): a file whose NAME ends in the candidate
    id but whose embedded id differs must not be treated as a duplicate —
    that would silently drop the new message."""
    app, brain = app_brain
    mid = "relay_20260612_010101_cafe0001"
    inbox = brain / "relay" / "cowork"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"20260612_010101_{mid}.json").write_text(
        json.dumps({"id": "relay_20260612_010101_different", "subject": "older"})
    )
    async with _client(app) as c:
        r = await c.post("/relay/cowork", json=_body(id=mid), headers=_auth())
    assert r.status_code == 202, r.text
    assert r.json()["duplicate"] is False
    files = list(inbox.glob("*.json"))
    assert len(files) == 2, [f.name for f in files]


@pytest.mark.asyncio
async def test_post_without_id_unchanged(app_brain):
    app, brain = app_brain
    async with _client(app) as c:
        r = await c.post("/relay/cowork", json=_body(), headers=_auth())
    assert r.status_code == 202
    assert r.json()["message_id"].startswith("relay_")
    assert r.json()["duplicate"] is False


# ── (b) ACK session_id passthrough ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_ack_with_session_id_sets_per_session_marker(app_brain):
    app, brain = app_brain
    async with _client(app) as c:
        pr = await c.post("/relay/cowork", json=_body(), headers=_auth())
        mid = pr.json()["message_id"]
        ar = await c.post(
            "/relay/cowork/ack",
            json={"message_ids": [mid], "session_id": "sess-abc123"},
            headers=_auth("tok-cowork"),
        )
    assert ar.status_code == 200, ar.text
    assert ar.json()["acked"] == 1
    files = list((brain / "relay" / "cowork").glob("*.json"))
    msg = json.loads(files[0].read_text())
    assert msg["read"] is True
    assert "sess-abc123" in (msg.get("read_by_sessions") or {})


@pytest.mark.asyncio
async def test_ack_without_session_id_coarse_only(app_brain):
    app, brain = app_brain
    async with _client(app) as c:
        pr = await c.post("/relay/cowork", json=_body(), headers=_auth())
        mid = pr.json()["message_id"]
        ar = await c.post(
            "/relay/cowork/ack", json={"message_ids": [mid]}, headers=_auth("tok-cowork")
        )
    assert ar.status_code == 200
    files = list((brain / "relay" / "cowork").glob("*.json"))
    msg = json.loads(files[0].read_text())
    assert msg["read"] is True
    assert not (msg.get("read_by_sessions") or {})


@pytest.mark.asyncio
async def test_ack_non_string_session_id_rejected(app_brain):
    app, brain = app_brain
    async with _client(app) as c:
        ar = await c.post(
            "/relay/cowork/ack",
            json={"message_ids": ["x"], "session_id": 42},
            headers=_auth("tok-cowork"),
        )
    assert ar.status_code == 400
    assert ar.json()["error"] == "schema_violation"
