"""Per ADR-0033 v3 §D: recall_activity_health buckets each role by the age of
its most recent activity engram.

The load-bearing case is the SPLIT between a role that wrote and then went
quiet (`silent-fail`, a real fault) and a role that has never written at all
(`never-ran`, not a fault). Collapsing the two made 7 of 8 roles alarm on
every audit, which is how an alarm stops being read.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    return brain


def _write_history(brain: Path, records: list[dict]) -> None:
    path = brain / "engrams" / "history.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _record(value: str, *, key: str, context: str, timestamp: str) -> dict:
    return {
        "key": key,
        "op_type": "ADD",
        "timestamp": timestamp,
        "snapshot": {
            "key": key,
            "value": value,
            "context": context,
            "intensity": 5,
            "version": 1,
            "source_agent": "nucleus-wedge",
            "op_type": "ADD",
            "timestamp": timestamp,
            "deleted": False,
            "signature": None,
        },
    }


def _ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def test_health_fresh_stale_silent_buckets(fake_brain) -> None:
    from nucleus_wedge.memories import recall_activity_health

    _write_history(fake_brain, [
        _record("recent main", key="a",
                context="activity [#role:coordinator,domain:tb]", timestamp=_ts(2)),
        _record("week-old peer", key="b",
                context="activity [#role:worker,domain:audit]", timestamp=_ts(72)),
        _record("ancient gq", key="c",
                context="activity [#role:gq,domain:apple]", timestamp=_ts(24 * 30)),
    ])
    out = recall_activity_health()
    by_role = {r["role"]: r for r in out["roles"]}

    assert by_role["coordinator"]["status"] == "fresh"
    assert by_role["worker"]["status"] == "stale"
    # gq WROTE 30 days ago and then stopped. That is the genuine fault.
    assert by_role["gq"]["status"] == "silent-fail"
    assert by_role["gq"]["last_digest_at"] is not None

    # reviewer / agy have never written. Not a fault — nothing has run as them.
    assert by_role["reviewer"]["status"] == "never-ran"
    assert by_role["reviewer"]["last_digest_at"] is None
    assert by_role["agy"]["status"] == "never-ran"

    # The distinction is the whole point: these two must not be the same value.
    assert by_role["gq"]["status"] != by_role["reviewer"]["status"]


def test_health_single_role(fake_brain) -> None:
    from nucleus_wedge.memories import recall_activity_health

    _write_history(fake_brain, [
        _record("recent main", key="a",
                context="activity [#role:coordinator,domain:tb]", timestamp=_ts(2)),
    ])
    out = recall_activity_health(role="cc_main")
    assert len(out["roles"]) == 1
    assert out["roles"][0]["role"] == "coordinator"
    assert out["roles"][0]["status"] == "fresh"
    assert out["roles"][0]["age_hours"] is not None and out["roles"][0]["age_hours"] < 24


def test_health_no_engrams_means_never_ran(fake_brain) -> None:
    """An empty brain is not a broken hook. Nothing has run yet."""
    from nucleus_wedge.memories import recall_activity_health

    out = recall_activity_health(role="coordinator")
    assert out["roles"][0]["status"] == "never-ran"
    assert out["roles"][0]["last_digest_at"] is None
    assert out["roles"][0]["age_hours"] is None


def test_health_unparseable_timestamp_is_not_silence(fake_brain) -> None:
    """A timestamp that cannot be read is a bug in the WRITER, not silence in
    the role. Coercing it to silent-fail sends the investigation to the wrong
    place — the third state has to survive all the way to the report."""
    from nucleus_wedge.memories import recall_activity_health

    _write_history(fake_brain, [
        _record("garbled", key="a",
                context="activity [#role:coordinator,domain:tb]",
                timestamp="not-a-timestamp"),
    ])
    out = recall_activity_health(role="coordinator")
    assert out["roles"][0]["status"] == "unparseable"
    assert out["roles"][0]["age_hours"] is None
    assert out["roles"][0]["last_digest_at"] == "not-a-timestamp"
