import pytest
from datetime import datetime, timezone, timedelta
from mcp_server_nucleus.runtime.marketplace import ReputationSignals


def test_reputation_no_decay():
    """Fresh interaction should have no decay."""
    now = datetime.now(timezone.utc)
    metrics = {
        "connection_count": 100,
        "last_seen_at": now.isoformat().replace("+00:00", "Z")
    }
    
    decayed = ReputationSignals.apply_decay(metrics, now=now, half_life_days=30)
    assert decayed["connection_count"] == 100


def test_reputation_30_day_stale():
    """30-day stale should decay by exactly 50% (one half-life)."""
    now = datetime.now(timezone.utc)
    last_seen = now - timedelta(days=30)
    
    metrics = {
        "connection_count": 100,
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z")
    }
    
    decayed = ReputationSignals.apply_decay(metrics, now=now, half_life_days=30)
    # 100 * 0.5^1 = 50
    assert decayed["connection_count"] == 50


def test_reputation_90_day_stale():
    """90-day stale should decay by 87.5% (three half-lives, remains 12.5%)."""
    now = datetime.now(timezone.utc)
    last_seen = now - timedelta(days=90)
    
    metrics = {
        "connection_count": 100,
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z")
    }
    
    decayed = ReputationSignals.apply_decay(metrics, now=now, half_life_days=30)
    # 100 * 0.5^3 = 100 * 0.125 = 12.5 -> int(12)
    assert decayed["connection_count"] == 12


def test_reputation_missing_last_seen():
    """If last_seen is missing, decay shouldn't crash and should return unchanged metrics."""
    metrics = {
        "connection_count": 100,
        "last_seen_at": None
    }
    
    decayed = ReputationSignals.apply_decay(metrics)
    assert decayed["connection_count"] == 100
