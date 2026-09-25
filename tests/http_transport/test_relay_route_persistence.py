"""Rate-bucket restart persistence + wake-map TTL — v0.2 Seq-3.

Rate buckets: _buckets is per-process, so a server restart used to zero
every sliding window — a caller could double its 60s budget by riding a
deploy. Windows now snapshot (debounced, atomic) to
<relay_dir>/.rate_buckets.json and lazily hydrate on the first rate check
after start. Tokens persist as sha256 digests only.

Wake map: parse-once meant a NUCLEUS_SESSION_WAKE_MAP env edit needed a
full server restart. The cache now re-parses after a TTL
(NUCLEUS_SESSION_WAKE_MAP_TTL_S, default 60s).

All tests use fake `now` values passed into _check_rate (the limiter is
clock-agnostic) and the test-only reset helpers to simulate restarts.
"""
import json
import time

import pytest

from mcp_server_nucleus.http_transport import relay_route as rr


@pytest.fixture(autouse=True)
def _fresh_limiter_state():
    rr._reset_rate_bucket_persistence()
    rr._reset_session_wake_map_cache()
    yield
    rr._reset_rate_bucket_persistence()
    rr._reset_session_wake_map_cache()


@pytest.fixture
def tmp_brain(tmp_path, monkeypatch):
    """Isolated brain so snapshot writes never touch the real .brain/relay
    (#538 setenv doctrine)."""
    brain = tmp_path / "brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    monkeypatch.setenv(
        "NUCLEUS_RELAY_TOKEN_MAP",
        json.dumps({"tok-good": "test_sender", "tok-other": "other_sender"}),
    )
    return brain


def _snapshot_file(brain):
    return brain / "relay" / ".rate_buckets.json"


def _capacity():
    return rr.RATE_PER_MIN + rr.RATE_BURST


# ── snapshot contents ────────────────────────────────────────────────────


def test_snapshot_contains_hashed_keys_never_raw_tokens(tmp_brain):
    allowed, _, _ = rr._check_rate("tok-good", "cowork", now=1000.0)
    assert allowed is True
    snap = _snapshot_file(tmp_brain)
    assert snap.exists(), "first rate check past debounce must snapshot"
    text = snap.read_text(encoding="utf-8")
    assert "tok-good" not in text, "bearer secrets must never land on disk"
    digest = rr._hash_token("tok-good")
    assert digest in text
    data = json.loads(text)
    # Global ("") and per-recipient scopes both persisted under digest keys
    assert f"{digest}|" in data["buckets"]
    assert f"{digest}|cowork" in data["buckets"]


# ── restart survival ─────────────────────────────────────────────────────


def test_global_window_survives_restart(tmp_brain):
    for i in range(5):
        allowed, _, _ = rr._check_rate("tok-good", "cowork", now=1000.0 + i * 0.1)
        assert allowed is True
    # Force a final snapshot past the debounce, then "restart" the process.
    rr._last_bucket_snapshot = 0.0
    rr._maybe_snapshot_buckets(1001.0)
    rr._reset_rate_bucket_persistence()
    assert rr._buckets == {}

    allowed, remaining, _ = rr._check_rate("tok-good", "cowork", now=1002.0)
    assert allowed is True
    assert remaining == _capacity() - 6, (
        "5 pre-restart stamps must hydrate back, so the 6th call sees "
        "capacity-6 — not a refilled budget"
    )


def test_per_recipient_block_survives_restart(tmp_brain):
    for i in range(rr.RATE_PER_RECIPIENT):
        allowed, _, _ = rr._check_rate("tok-good", "cowork", now=2000.0 + i * 0.01)
        assert allowed is True
    blocked, _, retry = rr._check_rate("tok-good", "cowork", now=2001.0)
    assert blocked is False and retry >= 1

    rr._last_bucket_snapshot = 0.0
    rr._maybe_snapshot_buckets(2001.0)
    rr._reset_rate_bucket_persistence()

    still_blocked, _, _ = rr._check_rate("tok-good", "cowork", now=2001.5)
    assert still_blocked is False, "per-recipient window must not refill on deploy"
    # Global budget (capacity > RATE_PER_RECIPIENT) still allows other recipients
    other_ok, _, _ = rr._check_rate("tok-good", "elsewhere", now=2001.6)
    assert other_ok is True


# ── hydrate edge cases ───────────────────────────────────────────────────


def test_hydrate_drops_stamps_outside_window(tmp_brain):
    digest = rr._hash_token("tok-good")
    _snapshot_file(tmp_brain).parent.mkdir(parents=True, exist_ok=True)
    _snapshot_file(tmp_brain).write_text(
        json.dumps({"saved_at": 110.0, "buckets": {f"{digest}|": [100.0, 110.0]}}),
        encoding="utf-8",
    )
    # now=1000 → both stamps are > 60s old → hydrate keeps nothing
    allowed, remaining, _ = rr._check_rate("tok-good", "cowork", now=1000.0)
    assert allowed is True
    assert remaining == _capacity() - 1


def test_hydrate_ignores_unknown_digest(tmp_brain):
    _snapshot_file(tmp_brain).parent.mkdir(parents=True, exist_ok=True)
    _snapshot_file(tmp_brain).write_text(
        json.dumps({"saved_at": 999.0, "buckets": {"deadbeef" * 8 + "|": [999.5]}}),
        encoding="utf-8",
    )
    allowed, remaining, _ = rr._check_rate("tok-good", "cowork", now=1000.0)
    assert allowed is True
    assert remaining == _capacity() - 1, "stamps for tokens not in the live map are dropped"


def test_corrupt_snapshot_continues_cold(tmp_brain):
    _snapshot_file(tmp_brain).parent.mkdir(parents=True, exist_ok=True)
    _snapshot_file(tmp_brain).write_text("not-json{{{", encoding="utf-8")
    allowed, remaining, _ = rr._check_rate("tok-good", "cowork", now=1000.0)
    assert allowed is True
    assert remaining == _capacity() - 1


def test_get_rate_limit_headers_hydrates_too(tmp_brain):
    """The read-only header path must see persisted windows, not a cold map."""
    digest = rr._hash_token("tok-good")
    _snapshot_file(tmp_brain).parent.mkdir(parents=True, exist_ok=True)
    _snapshot_file(tmp_brain).write_text(
        json.dumps(
            {"saved_at": 999.0, "buckets": {f"{digest}|": [995.0, 996.0, 997.0]}}
        ),
        encoding="utf-8",
    )
    headers = rr.get_rate_limit_headers("tok-good", "cowork", now=1000.0)
    assert headers["X-RateLimit-Remaining"] == str(_capacity() - 3)


# ── wake-map TTL ─────────────────────────────────────────────────────────


def test_wake_map_cached_within_ttl(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"tb": {"kind": "chat"}}))
    first = rr._get_session_wake_map()
    assert first == {"tb": {"kind": "chat"}}
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"tb": {"kind": "dispatch"}}))
    assert rr._get_session_wake_map() == {"tb": {"kind": "chat"}}, (
        "within TTL the cached parse must be returned"
    )


def test_wake_map_reparses_after_ttl(monkeypatch):
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"tb": {"kind": "chat"}}))
    assert rr._get_session_wake_map() == {"tb": {"kind": "chat"}}
    monkeypatch.setenv("NUCLEUS_SESSION_WAKE_MAP", json.dumps({"tb": {"kind": "cloud_cc"}}))
    # Age the cache past the TTL instead of sleeping
    rr._session_wake_map_loaded_at = time.monotonic() - (rr._SESSION_WAKE_MAP_TTL_S + 1)
    assert rr._get_session_wake_map() == {"tb": {"kind": "cloud_cc"}}, (
        "env edits must land within one TTL window without a server restart"
    )
