"""Relay bridge daemon (v0.2) — pull/merge/ack-up/push sync logic.

HTTP layer is faked at bridge._http (the single transport seam); FS side
uses a tmp_path brain so the real _get_relay_dir / envelope code runs.
"""
import json
import os
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.relay import bridge


@pytest.fixture
def env(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    (brain / "relay").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.test")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "bridge-token")
    monkeypatch.setenv("NUCLEUS_BRIDGE_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("NUCLEUS_BRIDGE_TOKEN_DIR", str(tmp_path / "tokens"))
    (tmp_path / "tokens").mkdir()
    bridge._warned_senders.clear()
    return brain, tmp_path


class FakeHTTP:
    """Programmable bridge._http stand-in recording every call."""

    def __init__(self):
        self.calls = []
        # route key -> (status, response) or callable(method, url, token, body)
        self.routes = {}
        self.default = (200, {"messages": []})

    def __call__(self, method, url, token, body=None, idempotency_key=None):
        self.calls.append(
            {"method": method, "url": url, "token": token,
             "body": body, "idempotency_key": idempotency_key}
        )
        for key, resp in self.routes.items():
            if key[0] == method and key[1] in url:
                return resp(method, url, token, body) if callable(resp) else resp
        return self.default


def _server_msg(mid, inbox="cc_tb", **over):
    msg = {
        "id": mid,
        "from": "claude_code_main",
        "from_role": "main",
        "to": inbox,
        "subject": f"subj {mid}",
        "body": "{}",
        "priority": "normal",
        "context": {},
        "created_at": "2026-06-12T03:00:00Z",
        "read": False,
        "read_at": None,
        "read_by": None,
        "read_by_sessions": {},
        "_file": f"20260612_030000_{mid}.json",
    }
    msg.update(over)
    return msg


def _write_local(brain, inbox, mid, **over):
    d = brain / "relay" / inbox
    d.mkdir(parents=True, exist_ok=True)
    msg = _server_msg(mid, inbox=inbox, **over)
    msg.pop("_file", None)
    p = d / f"20260612_030000_{mid}.json"
    p.write_text(json.dumps(msg), encoding="utf-8")
    return p, msg


# ── PULL ──────────────────────────────────────────────────────────────────

def test_pull_writes_missing_under_server_filename(env, monkeypatch):
    brain, _ = env
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (
        200, {"messages": [_server_msg("relay_20260612_030000_aaaa0001")]}
    )
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["pulled"] == 1
    f = brain / "relay" / "cc_tb" / "20260612_030000_relay_20260612_030000_aaaa0001.json"
    assert f.exists()
    written = json.loads(f.read_text())
    assert written["id"] == "relay_20260612_030000_aaaa0001"
    assert "_file" not in written


def test_pull_merges_remote_read_state_into_local(env, monkeypatch):
    brain, _ = env
    mid = "relay_20260612_030000_aaaa0002"
    path, _ = _write_local(brain, "cc_tb", mid)
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (
        200,
        {"messages": [_server_msg(
            mid, read=True, read_at="2026-06-12T03:05:00Z", read_by="cc_tb",
            read_by_sessions={"sess-1": "2026-06-12T03:05:00Z"},
        )]},
    )
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["merged"] == 1
    local = json.loads(path.read_text())
    assert local["read"] is True
    assert local["read_by_sessions"] == {"sess-1": "2026-06-12T03:05:00Z"}


def test_pull_transport_down_flagged(env, monkeypatch):
    fake = FakeHTTP()
    fake.default = (0, {})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["transport_down"] is True
    assert stats["pulled"] == 0


# ── ACK-up ────────────────────────────────────────────────────────────────

def test_ack_up_when_local_read_and_server_unread(env, monkeypatch):
    brain, _ = env
    mid = "relay_20260612_030000_aaaa0003"
    _write_local(
        brain, "cc_tb", mid,
        read=True, read_at="2026-06-12T03:01:00Z", read_by="cc_tb",
        read_by_sessions={"sess-9": "2026-06-12T03:01:00Z"},
    )
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": [_server_msg(mid)]})
    fake.routes[("POST", "/relay/cc_tb/ack")] = (200, {"acked": 1, "failed": 0})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["acked_up"] == 1
    ack_calls = [c for c in fake.calls if c["url"].endswith("/ack")]
    # coarse batch + one per-session call
    assert ack_calls[0]["body"] == {"message_ids": [mid]}
    assert {"message_ids": [mid], "session_id": "sess-9"} in [c["body"] for c in ack_calls]
    # recorded in state — second pass does NOT re-ack
    fake.calls.clear()
    bridge.sync_inbox("cc_tb")
    assert not [c for c in fake.calls if c["url"].endswith("/ack")]


def test_session_marker_added_after_coarse_ack_still_propagates(env, monkeypatch):
    """Crack-1a (PR #570 peer verdict): per-session ack-up must not be gated
    on the coarse acked_to_server record — a marker appearing later still syncs."""
    brain, _ = env
    mid = "relay_20260612_030000_bbbb0001"
    path, _ = _write_local(brain, "cc_tb", mid, read=True, read_by="cc_tb")
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": [_server_msg(mid)]})
    fake.routes[("POST", "/relay/cc_tb/ack")] = (200, {"acked": 1, "failed": 0})
    monkeypatch.setattr(bridge, "_http", fake)
    bridge.sync_inbox("cc_tb")  # coarse acked, no sessions yet
    # New session marker lands locally AFTER the coarse ack
    msg = json.loads(path.read_text())
    msg["read_by_sessions"] = {"sess-late": "2026-06-12T03:10:00Z"}
    path.write_text(json.dumps(msg))
    fake.calls.clear()
    bridge.sync_inbox("cc_tb")
    bodies = [c["body"] for c in fake.calls if c["url"].endswith("/ack")]
    assert {"message_ids": [mid], "session_id": "sess-late"} in bodies


def test_failed_session_ack_retried_next_cycle(env, monkeypatch):
    """Crack-1b: per-session ack recorded only on confirmed success —
    a transient failure is retried, not orphaned by the coarse record."""
    brain, _ = env
    mid = "relay_20260612_030000_bbbb0002"
    _write_local(
        brain, "cc_tb", mid, read=True, read_by="cc_tb",
        read_by_sessions={"sess-x": "2026-06-12T03:01:00Z"},
    )
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": [_server_msg(mid)]})
    session_results = iter([(200, {"acked": 0, "failed": 1}), (200, {"acked": 1, "failed": 0})])

    def ack_route(method, url, token, body):
        if body and body.get("session_id"):
            return next(session_results)
        return (200, {"acked": 1, "failed": 0})

    fake.routes[("POST", "/relay/cc_tb/ack")] = ack_route
    monkeypatch.setattr(bridge, "_http", fake)
    s1 = bridge.sync_inbox("cc_tb")
    assert s1["errors"] == 1  # session ack failed → not recorded
    fake.calls.clear()
    bridge.sync_inbox("cc_tb")  # retried this cycle, succeeds
    session_calls = [c for c in fake.calls if c["body"] and c["body"].get("session_id")]
    assert len(session_calls) == 1
    fake.calls.clear()
    bridge.sync_inbox("cc_tb")  # now recorded — no further retries
    assert not [c for c in fake.calls if c["body"] and c["body"].get("session_id")]


# ── PUSH ──────────────────────────────────────────────────────────────────

def _grant_token(tmp_path, sender, value="sender-token"):
    (tmp_path / "tokens" / f"relay_token_{sender}").write_text(value)


def test_push_local_only_message_with_id_and_idempotency_key(env, monkeypatch):
    brain, tmp_path = env
    mid = "relay_20260612_030000_aaaa0004"
    _write_local(brain, "cc_tb", mid, **{"from": "claude_code_main"})
    _grant_token(tmp_path, "claude_code_main", "main-token")
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": []})
    fake.routes[("POST", "/relay/cc_tb")] = (202, {"sent": True, "message_id": mid})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["pushed"] == 1
    push = [c for c in fake.calls if c["method"] == "POST"][0]
    assert push["body"]["id"] == mid
    assert push["body"]["sender"] == "claude_code_main"
    assert push["idempotency_key"] == mid
    assert push["token"] == "main-token"
    # state recorded — second pass does not re-push
    fake.calls.clear()
    bridge.sync_inbox("cc_tb")
    assert not [c for c in fake.calls if c["method"] == "POST"]


def test_push_409_idempotency_replay_recorded_as_pushed(env, monkeypatch):
    brain, tmp_path = env
    mid = "relay_20260612_030000_aaaa0005"
    _write_local(brain, "cc_tb", mid)
    _grant_token(tmp_path, "claude_code_main")
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": []})
    fake.routes[("POST", "/relay/cc_tb")] = (409, {"error": "idempotency_replay"})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["pushed"] == 1
    state = json.loads((tmp_path / "state" / "cc_tb.json").read_text())
    assert mid in state["pushed_ids"]


def test_push_skipped_without_sender_token(env, monkeypatch):
    brain, _ = env
    _write_local(brain, "cc_tb", "relay_20260612_030000_aaaa0006")
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": []})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["pushed"] == 0
    assert not [c for c in fake.calls if c["method"] == "POST"]


def test_push_skips_files_older_than_max_age(env, monkeypatch):
    brain, tmp_path = env
    mid = "relay_20260612_030000_aaaa0007"
    path, _ = _write_local(brain, "cc_tb", mid)
    _grant_token(tmp_path, "claude_code_main")
    old = time.time() - 10 * 24 * 3600
    os.utime(path, (old, old))
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": []})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["pushed"] == 0
    assert not [c for c in fake.calls if c["method"] == "POST"]


def test_push_skips_messages_already_on_server(env, monkeypatch):
    brain, tmp_path = env
    mid = "relay_20260612_030000_aaaa0008"
    _write_local(brain, "cc_tb", mid)
    _grant_token(tmp_path, "claude_code_main")
    fake = FakeHTTP()
    fake.routes[("GET", "/relay/cc_tb")] = (200, {"messages": [_server_msg(mid)]})
    monkeypatch.setattr(bridge, "_http", fake)
    stats = bridge.sync_inbox("cc_tb")
    assert stats["pushed"] == 0


# ── merge primitive ───────────────────────────────────────────────────────

def test_merge_read_state_is_monotonic_union():
    local = {"read": True, "read_by_sessions": {"a": "t1"}}
    remote = {"read": False, "read_by_sessions": {"b": "t2"}}
    changed, server_behind = bridge._merge_read_state(local, remote)
    assert changed is True
    assert local["read_by_sessions"] == {"a": "t1", "b": "t2"}
    assert local["read"] is True  # never downgraded
    assert server_behind is True  # server lacks read=True and session "a"


def test_merge_read_state_noop_when_identical():
    local = {"read": True, "read_by_sessions": {"a": "t1"}}
    remote = {"read": True, "read_by_sessions": {"a": "t1"}}
    changed, server_behind = bridge._merge_read_state(local, remote)
    assert changed is False
    assert server_behind is False


# ── config + filename safety ──────────────────────────────────────────────

def test_bridge_inboxes_default_is_canonical_set(monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRIDGE_INBOXES", raising=False)
    boxes = bridge.bridge_inboxes()
    assert "cc_tb" in boxes
    assert "claude_code_main" in boxes
    assert "claude_code_operator_assistant" in boxes


def test_bridge_inboxes_env_extend_and_replace(monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRIDGE_INBOXES", "bespoq,bespoq_cowork")
    boxes = bridge.bridge_inboxes()
    assert "bespoq" in boxes and "cc_tb" in boxes
    monkeypatch.setenv("NUCLEUS_BRIDGE_INBOXES", "=cc_tb,board")
    assert bridge.bridge_inboxes() == ["board", "cc_tb"]


def test_safe_filename_rejects_traversal():
    assert bridge._safe_filename(
        {"_file": "../../etc/evil.json", "id": "relay_20260612_030000_aaaa0009"}
    ) == "relay_20260612_030000_aaaa0009.json"
    assert bridge._safe_filename(
        {"_file": "ok_name.json", "id": "x"}
    ) == "ok_name.json"


def test_state_capped(env):
    state = {"pushed_ids": [f"id{i}" for i in range(3000)], "acked_to_server": []}
    bridge._save_state("cc_tb", state)
    loaded = bridge._load_state("cc_tb")
    assert len(loaded["pushed_ids"]) == bridge.STATE_MAX_IDS
    assert loaded["pushed_ids"][-1] == "id2999"


# ── sync_all / main ───────────────────────────────────────────────────────

def test_sync_all_never_raises_on_inbox_crash(env, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRIDGE_INBOXES", "=cc_tb,board")

    def boom(inbox):
        if inbox == "cc_tb":
            raise RuntimeError("boom")
        return {"inbox": inbox, "pulled": 1, "merged": 0, "acked_up": 0,
                "pushed": 0, "errors": 0, "transport_down": False}

    monkeypatch.setattr(bridge, "sync_inbox", boom)
    totals = bridge.sync_all()
    assert totals["errors"] == 1
    assert totals["pulled"] == 1


def test_main_once_exit_codes(env, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once"])
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": False,
    })
    assert bridge.main() == 0
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": True,
    })
    assert bridge.main() == 1


def test_main_requires_url_and_bearer(monkeypatch):
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once"])
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    assert bridge.main() == 2
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.test")
    assert bridge.main() == 2


# ── Engram sync (background, composed on sync module) ────────────────────

def test_engram_sync_disabled_by_default(monkeypatch):
    """Engram sync is skipped when no env flag and no NUCLEUS_SYNC_URL."""
    monkeypatch.delenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", raising=False)
    monkeypatch.delenv("NUCLEUS_SYNC_URL", raising=False)
    stats = bridge.sync_engrams()
    assert stats.get("skipped") is True
    assert stats["reason"] == "disabled"


def test_engram_sync_enabled_by_explicit_flag(monkeypatch):
    """NUCLEUS_BRIDGE_ENGRAM_SYNC=1 enables engram sync."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", "1")
    monkeypatch.delenv("NUCLEUS_SYNC_URL", raising=False)
    called = {"n": 0}

    def fake_cycle(**kw):
        called["n"] += 1
        return {"ok": True, "pushed": 5, "received": 3, "applied": 3,
                "skipped": 0, "conflicts": 0, "next_timestamp": "2026-06-21T12:00:00Z",
                "error": None, "transport_down": False}

    monkeypatch.setattr("mcp_server_nucleus.sync.perform_sync_cycle", fake_cycle)
    stats = bridge.sync_engrams()
    assert called["n"] == 1
    assert stats["ok"] is True
    assert stats["pushed"] == 5


def test_engram_sync_auto_enabled_by_sync_url(monkeypatch):
    """Setting NUCLEUS_SYNC_URL auto-enables engram sync."""
    monkeypatch.delenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", raising=False)
    monkeypatch.setenv("NUCLEUS_SYNC_URL", "https://relay.nucleusos.dev/engrams/sync")
    assert bridge._engram_sync_enabled() is True


def test_engram_sync_explicit_off_overrides_sync_url(monkeypatch):
    """NUCLEUS_BRIDGE_ENGRAM_SYNC=0 explicitly disables even with SYNC_URL set."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", "0")
    monkeypatch.setenv("NUCLEUS_SYNC_URL", "https://relay.nucleusos.dev/engrams/sync")
    assert bridge._engram_sync_enabled() is False


def test_engram_sync_never_raises_on_exception(monkeypatch):
    """Engram sync crashes are caught — never propagate to the relay loop."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", "1")

    def boom(**kw):
        raise RuntimeError("sync endpoint exploded")

    monkeypatch.setattr("mcp_server_nucleus.sync.perform_sync_cycle", boom)
    stats = bridge.sync_engrams()
    assert stats.get("ok") is False
    assert "exploded" in stats["error"]
    assert stats["transport_down"] is False


def test_engram_sync_transport_down_flagged(monkeypatch):
    """Transport errors set transport_down so the loop can back off."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", "1")

    def fake_cycle(**kw):
        return {"ok": False, "error": "Sync endpoint unreachable: connection refused",
                "transport_down": True, "pushed": 0, "received": 0}

    monkeypatch.setattr("mcp_server_nucleus.sync.perform_sync_cycle", fake_cycle)
    stats = bridge.sync_engrams()
    assert stats["ok"] is False
    assert stats["transport_down"] is True


def test_main_once_with_engrams_includes_engram_stats(env, monkeypatch, capsys):
    """--with-engrams flag runs engram sync and includes it in the JSON output."""
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once", "--with-engrams"])
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", "1")
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": False,
    })

    def fake_cycle(**kw):
        return {"ok": True, "pushed": 2, "received": 1, "applied": 1,
                "skipped": 0, "conflicts": 0, "next_timestamp": None,
                "error": None, "transport_down": False}

    monkeypatch.setattr("mcp_server_nucleus.sync.perform_sync_cycle", fake_cycle)
    assert bridge.main() == 0
    out = capsys.readouterr().out
    result = json.loads(out)
    assert "engram_sync" in result
    assert result["engram_sync"]["ok"] is True
    assert result["engram_sync"]["pushed"] == 2


def test_main_once_without_engrams_omits_engram_key(env, monkeypatch, capsys):
    """Without --with-engrams, the JSON output has no engram_sync key."""
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once"])
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": False,
    })
    assert bridge.main() == 0
    out = capsys.readouterr().out
    result = json.loads(out)
    assert "engram_sync" not in result


def test_engram_sync_interval_respected(monkeypatch):
    """run_loop only calls sync_engrams when the interval has elapsed."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC", "1")
    monkeypatch.setenv("NUCLEUS_BRIDGE_ENGRAM_SYNC_INTERVAL_S", "999")
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": False,
    })

    call_count = {"n": 0}

    def fake_sync_engrams():
        call_count["n"] += 1
        return {"ok": True, "pushed": 0, "transport_down": False}

    monkeypatch.setattr(bridge, "sync_engrams", fake_sync_engrams)

    # Simulate 2 loop iterations with a very short sleep
    iterations = {"n": 0}
    original_sleep = time.sleep

    def fake_sleep(s):
        iterations["n"] += 1
        if iterations["n"] >= 2:
            raise KeyboardInterrupt  # break out of the loop

    monkeypatch.setattr(time, "sleep", fake_sleep)
    try:
        bridge.run_loop(interval_s=0.01)
    except KeyboardInterrupt:
        pass

    # With interval=999s and 2 iterations ~0s apart, engram sync should
    # fire exactly once (the initial last_engram_sync=0.0 triggers it on
    # the first cycle; the second cycle is within the 999s window).
    assert call_count["n"] == 1


# ── Startup preflight: half-mirror / dead-remote detection (opt-in) ────────

def test_preflight_disabled_by_default_even_with_bad_remote(env, monkeypatch):
    """Flag OFF (default): a 401 remote does NOT raise — the offline-tolerant
    loop is byte-identical to today (preflight never probes)."""
    monkeypatch.delenv("NUCLEUS_BRIDGE_PREFLIGHT", raising=False)
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once"])
    monkeypatch.setattr(bridge, "_http", lambda *a, **k: (401, {"error": "auth_missing"}))
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": False,
    })
    assert bridge.main() == 0  # no preflight, no raise


def test_preflight_raises_on_dead_remote(env, monkeypatch):
    """Flag ON + unreachable remote → BridgeConfigError naming the env + fix."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_PREFLIGHT", "1")
    monkeypatch.setattr(bridge, "_http", lambda *a, **k: (0, {}))
    with pytest.raises(bridge.BridgeConfigError) as ei:
        bridge.preflight_check()
    msg = str(ei.value)
    assert "NUCLEUS_RELAY_URL" in msg and "UNREACHABLE" in msg
    assert "NUCLEUS_BRIDGE_PREFLIGHT" in msg  # escape hatch surfaced


def test_preflight_raises_on_401_half_mirror(env, monkeypatch):
    """Flag ON + 401 → BridgeConfigError flagging the one-way / half-mirror."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_PREFLIGHT", "1")
    monkeypatch.setattr(bridge, "_http", lambda *a, **k: (401, {"error": "auth_missing"}))
    with pytest.raises(bridge.BridgeConfigError) as ei:
        bridge.preflight_check()
    msg = str(ei.value)
    assert "half-mirror" in msg and "NUCLEUS_RELAY_BEARER" in msg
    assert "ghosted" in msg


def test_preflight_raises_on_misconfigured_endpoint(env, monkeypatch):
    """Flag ON + non-200/401 (e.g. 500) → BridgeConfigError naming the status."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_PREFLIGHT", "1")
    monkeypatch.setattr(bridge, "_http", lambda *a, **k: (500, {"error": "boom"}))
    with pytest.raises(bridge.BridgeConfigError) as ei:
        bridge.preflight_check()
    assert "500" in str(ei.value)


def test_preflight_passes_on_healthy_200(env, monkeypatch):
    """Flag ON + healthy 200 remote → no raise; main proceeds and exits clean."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_PREFLIGHT", "1")
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once"])
    monkeypatch.setattr(bridge, "_http", lambda *a, **k: (200, {"messages": []}))
    monkeypatch.setattr(bridge, "sync_all", lambda: {
        "pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
        "errors": 0, "transport_down": False,
    })
    assert bridge.main() == 0


def test_preflight_main_propagates_hard_error_when_enabled(env, monkeypatch):
    """Wiring: main() invokes preflight under the flag and propagates the hard
    error (vs silently ghosting) when the remote is down."""
    monkeypatch.setenv("NUCLEUS_BRIDGE_PREFLIGHT", "1")
    monkeypatch.setattr("sys.argv", ["nucleus-relay-bridge", "--once"])
    monkeypatch.setattr(bridge, "_http", lambda *a, **k: (0, {}))
    with pytest.raises(bridge.BridgeConfigError):
        bridge.main()
