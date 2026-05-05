"""Tests for relay_archive() — relay-inbox retention + archival primitive.

Validates the 3 core behaviors:
1. Age-based archival: messages older than max_age_days are archived.
2. Count-based archival: when bucket exceeds max_count, oldest are archived.
3. Idempotent re-run: running archive on an already-pruned bucket is a no-op.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.relay_ops import relay_archive


def _write_relay(bucket: Path, relay_id: str, created_at: str, sender: str = "test_agent") -> Path:
    """Seed a relay JSON file into a bucket directory."""
    relay = {
        "id": relay_id,
        "from": sender,
        "to": "test_recipient",
        "subject": f"test relay {relay_id}",
        "body": json.dumps({"summary": f"body for {relay_id}"}),
        "created_at": created_at,
        "read": False,
    }
    # Use the relay_id as filename prefix for deterministic ordering.
    f = bucket / f"{relay_id}.json"
    f.write_text(json.dumps(relay))
    return f


def _iso(dt: datetime) -> str:
    """Format datetime as ISO string with Z suffix."""
    return dt.isoformat().replace("+00:00", "Z")


@pytest.fixture
def brain(tmp_path: Path) -> Path:
    """Create a minimal .brain structure with a relay bucket."""
    brain = tmp_path / ".brain"
    bucket = brain / "relay" / "test_agent"
    bucket.mkdir(parents=True)
    return brain


def test_archive_by_age(brain: Path) -> None:
    """Messages older than max_age_days are archived; recent ones kept."""
    bucket = brain / "relay" / "test_agent"
    now = datetime.now(timezone.utc)

    # 3 recent relays (within 7 days)
    for i in range(3):
        dt = now - timedelta(hours=i + 1)
        _write_relay(bucket, f"recent_{i}", _iso(dt))

    # 5 old relays (older than 7 days)
    for i in range(5):
        dt = now - timedelta(days=10 + i)
        _write_relay(bucket, f"old_{i}", _iso(dt))

    result = relay_archive(
        recipient="test_agent",
        max_age_days=7,
        max_count=3,  # count matches recent count; old ones are beyond both limits
        brain_path=brain,
    )

    assert result["archived"] == 5
    assert result["kept"] == 3
    assert result["dry_run"] is False

    # Originals should be deleted.
    remaining = list(bucket.glob("*.json"))
    assert len(remaining) == 3
    assert all("recent" in f.name for f in remaining)

    # Archive JSONL files should exist.
    archive_dir = bucket / "archive"
    assert archive_dir.is_dir()
    jsonl_files = list(archive_dir.glob("*.jsonl"))
    assert len(jsonl_files) > 0

    # Verify archive contents are valid JSONL.
    total_archived_lines = 0
    for jf in jsonl_files:
        for line in jf.read_text().strip().splitlines():
            data = json.loads(line)
            assert "id" in data
            assert data["id"].startswith("old_")
            total_archived_lines += 1
    assert total_archived_lines == 5


def test_archive_by_count(brain: Path) -> None:
    """When bucket exceeds max_count, oldest messages beyond count+age are archived."""
    bucket = brain / "relay" / "test_agent"
    now = datetime.now(timezone.utc)

    # 15 messages, all older than 1 day (outside a max_age_days=0 window)
    for i in range(15):
        dt = now - timedelta(days=2, hours=i)
        _write_relay(bucket, f"msg_{i:03d}", _iso(dt))

    result = relay_archive(
        recipient="test_agent",
        max_age_days=0,  # all are "old" relative to age
        max_count=5,     # keep only newest 5
        brain_path=brain,
    )

    assert result["archived"] == 10
    assert result["kept"] == 5
    assert result["dry_run"] is False

    remaining = list(bucket.glob("*.json"))
    assert len(remaining) == 5


def test_idempotent_rerun(brain: Path) -> None:
    """Running archive on an already-pruned bucket is a no-op."""
    bucket = brain / "relay" / "test_agent"
    now = datetime.now(timezone.utc)

    # 3 recent relays only — nothing to archive.
    for i in range(3):
        dt = now - timedelta(hours=i + 1)
        _write_relay(bucket, f"recent_{i}", _iso(dt))

    result = relay_archive(
        recipient="test_agent",
        max_age_days=7,
        max_count=100,
        brain_path=brain,
    )

    assert result["archived"] == 0
    assert result["kept"] == 3
    assert result["archive_paths"] == []

    # No archive directory created.
    assert not (bucket / "archive").exists()


def test_dry_run_does_not_modify(brain: Path) -> None:
    """dry_run=True reports what would be archived but doesn't touch files."""
    bucket = brain / "relay" / "test_agent"
    now = datetime.now(timezone.utc)

    # 5 old relays
    for i in range(5):
        dt = now - timedelta(days=20 + i)
        _write_relay(bucket, f"old_{i}", _iso(dt))

    result = relay_archive(
        recipient="test_agent",
        max_age_days=7,
        max_count=0,  # zero count so all old messages are beyond both limits
        brain_path=brain,
        dry_run=True,
    )

    assert result["archived"] == 5
    assert result["dry_run"] is True

    # Files should still be present — nothing moved.
    remaining = list(bucket.glob("*.json"))
    assert len(remaining) == 5
    assert not (bucket / "archive").exists()


def test_empty_bucket(brain: Path) -> None:
    """Empty bucket returns zero counts gracefully."""
    result = relay_archive(
        recipient="test_agent",
        max_age_days=7,
        max_count=100,
        brain_path=brain,
    )

    assert result["archived"] == 0
    assert result["kept"] == 0


def test_missing_bucket(brain: Path) -> None:
    """Non-existent bucket returns error gracefully."""
    result = relay_archive(
        recipient="nonexistent_agent",
        max_age_days=7,
        max_count=100,
        brain_path=brain,
    )

    assert result["archived"] == 0
    assert "error" in result
