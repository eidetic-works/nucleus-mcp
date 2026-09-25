"""Representative-load stress tests for relay post helper + inbox scan paths.

Wave-2 S3 draft — per HARD RULE feedback_smoke_tests_need_realistic_load:
daemon/substrate tests MUST include representative-load cases before any
ship-ready claim. Prior incident: 225-file bucket exposed 45s/cycle starvation
where empty-bucket smoke had passed.

Test targets:
  (a) relay_post into a 250+-file inbox dir — wall-clock bounded (<2s/post)
  (b) relay_inbox scan over 250+ files with malformed/non-dict JSON mixed in
  (c) burst of 50 sequential posts to one recipient (unique filenames, parseable)
  (d) relay_post to recipient dir that has stale .seen/ marker artifacts
  (e) large-body payload (200 KB) round-trip without truncation / crash

All tests run in FS-mode (NUCLEUS_RELAY_URL unset). The host shell exports
NUCLEUS_RELAY_URL and NUCLEUS_RELAY_BEARER which would switch transport to
HTTP and break FS-mode assertions — each test purges both env vars via the
`_fs_mode_env` autouse fixture.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _fs_mode_env(monkeypatch):
    """Purge HTTP-mode env vars so all tests run FS-mode."""
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    yield


@pytest.fixture
def brain_root(tmp_path, monkeypatch):
    """Isolated .brain root; sets NUCLEUS_BRAIN_PATH so get_brain_path() resolves here."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


def _make_relay_envelope(*, inbox_dir: Path, recipient: str = "claude_code_main") -> Path:
    """Write one well-formed relay JSON file into inbox_dir and return its path."""
    now = datetime.now(timezone.utc)
    msg_id = f"relay_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{msg_id}.json"
    msg = {
        "id": msg_id,
        "from": "cc_test",
        "from_role": "cc_test",
        "from_provider": "claude",
        "from_session_id": None,
        "to": recipient,
        "to_session_id": None,
        "in_reply_to": None,
        "subject": "load-test relay",
        "body": "stub body",
        "priority": "normal",
        "context": {},
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "read": False,
        "read_at": None,
        "read_by": None,
        "read_by_sessions": {},
    }
    path = inbox_dir / filename
    path.write_text(json.dumps(msg, indent=2), encoding="utf-8")
    return path


# ── (a) relay_post into a 250+-file inbox dir — latency bounded ──────────────


def test_relay_post_latency_with_250_existing_files(brain_root, monkeypatch):
    """Posting one message into an already-loaded inbox (250 files) stays <2s.

    Prior incident baseline: a 225-file bucket exposed 45s/cycle starvation.
    This test is the regression gate — if post latency degrades it fails.
    """
    from mcp_server_nucleus.runtime.relay_ops import relay_post

    # Ensure FS-mode by patching env directly in relay_transport too
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    inbox_dir = brain_root / "relay" / "claude_code_main"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # Pre-populate inbox with 250 well-formed relay files
    for _ in range(250):
        _make_relay_envelope(inbox_dir=inbox_dir)

    assert len(list(inbox_dir.glob("*.json"))) == 250

    t0 = time.perf_counter()
    result = relay_post(
        to="claude_code_main",
        subject="load test subject",
        body="load test body",
        sender="cc_test",
    )
    elapsed = time.perf_counter() - t0

    assert result.get("sent") is True, f"relay_post failed: {result}"
    # Post path is a single file write; 250-file directory must not cause starvation
    assert elapsed < 2.0, (
        f"relay_post into 250-file inbox took {elapsed:.3f}s — exceeds 2s bound. "
        "Possible directory-scan starvation in the post code path."
    )
    # File count incremented by 1
    assert len(list(inbox_dir.glob("*.json"))) == 251


# ── (b) relay_inbox scan with 250+ files including malformed JSON ─────────────


def test_relay_inbox_scan_250_files_with_malformed_mixed_in(brain_root, monkeypatch):
    """Inbox scan of 250+ files tolerates malformed/non-dict JSON and stays <3s."""
    from mcp_server_nucleus.runtime.relay_ops import relay_inbox

    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    inbox_dir = brain_root / "relay" / "claude_code_main"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # 240 valid files
    for _ in range(240):
        _make_relay_envelope(inbox_dir=inbox_dir)

    # 10 malformed/non-dict JSON files
    for i in range(10):
        now = datetime.now(timezone.utc)
        name = f"{now.strftime('%Y%m%d_%H%M%S')}_bad_{i:04d}.json"
        (inbox_dir / name).write_text("not-json{{{{", encoding="utf-8")

    # 5 valid JSON but wrong shape (list not dict)
    for i in range(5):
        now = datetime.now(timezone.utc)
        name = f"{now.strftime('%Y%m%d_%H%M%S')}_list_{i:04d}.json"
        (inbox_dir / name).write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    total_files = len(list(inbox_dir.glob("*.json")))
    assert total_files == 255

    t0 = time.perf_counter()
    result = relay_inbox(unread_only=False, limit=100, recipient="claude_code_main")
    elapsed = time.perf_counter() - t0

    # Malformed + wrong-shape files silently skipped; valid ones returned
    assert result["count"] > 0, "Expected some messages to be returned"
    assert result["count"] <= 100, "Should respect limit"
    assert elapsed < 3.0, (
        f"relay_inbox scan of 255 files took {elapsed:.3f}s — exceeds 3s bound."
    )


# ── (c) Burst of 50 sequential posts — unique filenames, all parseable ────────


def test_burst_50_sequential_posts_unique_files(brain_root, monkeypatch):
    """50 sequential relay_post calls produce 50 unique, parseable relay files."""
    from mcp_server_nucleus.runtime.relay_ops import relay_post

    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    inbox_dir = brain_root / "relay" / "claude_code_main"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    results = []
    for i in range(50):
        r = relay_post(
            to="claude_code_main",
            subject=f"burst-test-{i:03d}",
            body=f"burst body {i}",
            sender="cc_test",
        )
        results.append(r)
    elapsed = time.perf_counter() - t0

    # All 50 must succeed
    failed = [r for r in results if not r.get("sent")]
    assert not failed, f"{len(failed)} of 50 burst posts failed: {failed[:3]}"

    # 50 unique message IDs
    ids = [r["message_id"] for r in results]
    assert len(set(ids)) == 50, "Expected 50 unique message IDs — collision detected"

    # 50 files on disk, all parseable
    files = sorted(inbox_dir.glob("*.json"))
    assert len(files) == 50, f"Expected 50 files, got {len(files)}"

    parse_errors = []
    for f in files:
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            assert isinstance(msg, dict), f"Expected dict, got {type(msg)} in {f.name}"
        except (json.JSONDecodeError, AssertionError) as exc:
            parse_errors.append((f.name, str(exc)))

    assert not parse_errors, f"Parse errors in burst output: {parse_errors}"

    # Wall-clock check: 50 posts shouldn't take more than 5s on any reasonable FS
    assert elapsed < 5.0, (
        f"50 sequential relay_post calls took {elapsed:.3f}s — potential FS bottleneck."
    )

    # Report measured wall-clock (visible in pytest -v output)
    print(f"\n[LOAD] 50-burst elapsed: {elapsed:.3f}s ({elapsed/50*1000:.1f}ms/post)")


# ── (d) relay_post to recipient dir with stale .seen/ marker artifacts ─────────


def test_relay_post_tolerates_stale_seen_dir_in_inbox(brain_root, monkeypatch):
    """relay_post succeeds even when inbox dir contains .seen/ subdirectory.

    .seen/ directories are sometimes left as ACK-marker artifacts by
    older relay watchers. The post path must not confuse them with JSON files.
    """
    from mcp_server_nucleus.runtime.relay_ops import relay_post

    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    inbox_dir = brain_root / "relay" / "claude_code_main"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # Stale .seen/ subdirectory with some files inside
    seen_dir = inbox_dir / ".seen"
    seen_dir.mkdir()
    (seen_dir / "old_ack_1.json").write_text('{"acked": true}', encoding="utf-8")
    (seen_dir / "old_ack_2.json").write_text('{"acked": true}', encoding="utf-8")

    # Also plant a few regular relay files
    for _ in range(10):
        _make_relay_envelope(inbox_dir=inbox_dir)

    result = relay_post(
        to="claude_code_main",
        subject="test with stale .seen dir",
        body="should work fine",
        sender="cc_test",
    )

    assert result.get("sent") is True, f"relay_post failed with .seen/ present: {result}"

    # Only the legitimate relay JSONs should be in the inbox root
    inbox_jsons = list(inbox_dir.glob("*.json"))
    assert len(inbox_jsons) == 11  # 10 pre-existing + 1 new


# ── (d2) relay_inbox scan tolerates .seen/ dir without crashing ───────────────


def test_relay_inbox_scan_tolerates_stale_seen_artifacts(brain_root, monkeypatch):
    """relay_inbox scan with .seen/ subdirectory does not raise or hang."""
    from mcp_server_nucleus.runtime.relay_ops import relay_inbox

    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    inbox_dir = brain_root / "relay" / "claude_code_main"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # 20 valid relay files
    for _ in range(20):
        _make_relay_envelope(inbox_dir=inbox_dir)

    # Stale .seen/ dir — glob("*.json") on the inbox root should not descend into it
    seen_dir = inbox_dir / ".seen"
    seen_dir.mkdir()
    for i in range(5):
        (seen_dir / f"ack_{i}.json").write_text('{"x": 1}', encoding="utf-8")

    result = relay_inbox(unread_only=False, limit=50, recipient="claude_code_main")

    # .seen/ files are NOT in inbox_dir.glob("*.json") — count should be exactly 20
    assert result["count"] == 20, (
        f"Expected 20 messages from inbox root; got {result['count']}. "
        ".seen/ file bleed-through detected."
    )


# ── (e) Large-body payload (200 KB) round-trip ────────────────────────────────


def test_large_body_200kb_round_trip(brain_root, monkeypatch):
    """A 200 KB body posts and is readable back without corruption.

    Note: _relay_post_helper enforces 4096-char cap, but relay_post (the FS
    writer in relay_ops/core) does NOT cap — it writes the full body. This
    test covers the core FS relay path (not the autonomous-wake helper).
    """
    from mcp_server_nucleus.runtime.relay_ops import relay_post, relay_inbox

    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")

    inbox_dir = brain_root / "relay" / "claude_code_main"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    large_body = "X" * 200_000  # 200 KB of ASCII

    t0 = time.perf_counter()
    result = relay_post(
        to="claude_code_main",
        subject="large-body test",
        body=large_body,
        sender="cc_test",
    )
    post_elapsed = time.perf_counter() - t0

    assert result.get("sent") is True, f"Large-body relay_post failed: {result}"
    assert post_elapsed < 2.0, (
        f"200 KB relay_post took {post_elapsed:.3f}s — unexpected FS bottleneck."
    )

    # Verify file is on disk and body round-trips intact
    msg_id = result["message_id"]
    matching_files = list(inbox_dir.glob("*.json"))
    assert len(matching_files) == 1

    on_disk = json.loads(matching_files[0].read_text(encoding="utf-8"))
    assert on_disk["id"] == msg_id
    assert on_disk["body"] == large_body, (
        f"Body round-trip failed: expected {len(large_body)} chars, "
        f"got {len(on_disk['body'])} chars"
    )

    # Inbox scan should surface it (even large bodies)
    t1 = time.perf_counter()
    inbox_result = relay_inbox(unread_only=False, limit=5, recipient="claude_code_main")
    scan_elapsed = time.perf_counter() - t1

    assert inbox_result["count"] == 1
    assert inbox_result["messages"][0]["body"] == large_body
    assert scan_elapsed < 2.0, (
        f"relay_inbox scan of 1 large (200KB) file took {scan_elapsed:.3f}s."
    )

    print(
        f"\n[LOAD] 200KB body: post={post_elapsed*1000:.1f}ms, "
        f"scan={scan_elapsed*1000:.1f}ms"
    )
