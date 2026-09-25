"""Live-fire tests for Slice Obs-2 ingest (relay_engram_projection).

Sandboxed per feedback_dogfood_sandbox_leak.md — every test passes an
explicit tmp brain_path so Store writes land in a tempdir. No monkeypatch
of a module-level path is needed here; Store accepts brain_path per call.
"""
from __future__ import annotations

import json
from pathlib import Path

from mcp_server_nucleus.runtime import relay_engram_projection as rep
from nucleus_wedge.store import Store


def _relay(
    relay_id: str,
    summary: str = "",
    subject: str = "",
    from_agent: str = "cowork",
    to_agent: str = "claude_code_peer",
    tags=None,
    artifact_refs=None,
    in_reply_to=None,
    from_session_id: str = "cowork-abc",
) -> dict:
    body = {
        "summary": summary,
        "tags": tags or [],
        "artifact_refs": artifact_refs or [],
        "auto_generated": False,
    }
    if in_reply_to:
        body["in_reply_to"] = in_reply_to
    return {
        "id": relay_id,
        "from": from_agent,
        "to": to_agent,
        "subject": subject,
        "body": json.dumps(body),
        "from_session_id": from_session_id,
        "created_at": "2026-04-20T09:00:00Z",
    }


def _write_to_bucket(brain: Path, bucket: str, msg: dict) -> Path:
    bdir = brain / "relay" / bucket
    bdir.mkdir(parents=True, exist_ok=True)
    p = bdir / f"{msg['id']}.json"
    p.write_text(json.dumps(msg))
    return p


def test_project_single_relay_creates_engram(tmp_path):
    msg = _relay("relay_20260420_090000_aaaaaaaa", summary="hello world",
                 subject="test subject", tags=["ship-report"])
    result = rep.project_relay_to_engram(msg, brain_path=tmp_path)
    assert result is not None
    assert result["key"] == "relay_projection_relay_20260420_090000_aaaaaaaa"
    store = Store(brain_path=tmp_path)
    rows = list(store.rows())
    assert len(rows) == 1
    snap = rows[0]["snapshot"]
    assert snap["source_agent"] == rep.PROJECTION_SOURCE
    assert "hello world" in snap["value"]
    assert "test subject" in snap["value"]
    assert "[cowork → claude_code_peer]" in snap["value"]


def test_project_is_idempotent(tmp_path):
    msg = _relay("relay_20260420_090100_bbbbbbbb", summary="dup check")
    r1 = rep.project_relay_to_engram(msg, brain_path=tmp_path)
    r2 = rep.project_relay_to_engram(msg, brain_path=tmp_path)
    assert r1 is not None
    assert r2 is None
    rows = list(Store(brain_path=tmp_path).rows())
    assert len(rows) == 1


def test_project_preserves_envelope_and_refs(tmp_path):
    msg = _relay(
        "relay_20260420_090200_cccccccc",
        summary="thread reply",
        tags=["ack", "disposition"],
        artifact_refs=["pr:org/repo#99", "git-commit:abc123"],
        in_reply_to="relay_20260420_080000_dddddddd",
    )
    rep.project_relay_to_engram(msg, brain_path=tmp_path)
    snap = next(Store(brain_path=tmp_path).rows())["snapshot"]
    assert "pr:org/repo#99" in snap["value"]
    assert "git-commit:abc123" in snap["value"]
    assert "relay_20260420_080000_dddddddd" in snap["value"]
    assert "cowork-abc" in snap["value"]
    assert "ack" in snap["context"]
    assert "disposition" in snap["context"]


def test_missing_relay_id_returns_none(tmp_path):
    msg = _relay("relay_dummy")
    del msg["id"]
    assert rep.project_relay_to_engram(msg, brain_path=tmp_path) is None
    history = tmp_path / "engrams" / "history.jsonl"
    assert not history.exists() or not history.read_text().strip()


def test_backfill_walks_recent_buckets(tmp_path):
    _write_to_bucket(tmp_path, "cowork",
                     _relay("relay_20260420_091000_e1e1e1e1", summary="from cowork"))
    _write_to_bucket(tmp_path, "claude_code_peer",
                     _relay("relay_20260420_091100_e2e2e2e2", summary="from peer",
                            from_agent="claude_code_peer", to_agent="cowork"))
    _write_to_bucket(tmp_path, "claude_code_main",
                     _relay("relay_20260420_091200_e3e3e3e3", summary="from main",
                            from_agent="claude_code_main", to_agent="cowork"))
    report = rep.backfill_recent_relays(days=14, brain_path=tmp_path)
    assert report["scanned"] == 3
    assert report["projected"] == 3
    assert report["by_bucket"] == {"cowork": 1, "claude_code_peer": 1, "claude_code_main": 1}


def test_backfill_reruns_are_noop(tmp_path):
    _write_to_bucket(tmp_path, "cowork",
                     _relay("relay_20260420_092000_f1f1f1f1", summary="first run"))
    first = rep.backfill_recent_relays(days=14, brain_path=tmp_path)
    second = rep.backfill_recent_relays(days=14, brain_path=tmp_path)
    assert first["projected"] == 1
    assert second["projected"] == 0
    assert second["skipped"] == 1
    rows = list(Store(brain_path=tmp_path).rows())
    assert len(rows) == 1
