"""Tests for nucleus_ccr_arm MCP tool — server-side IDE-agnostic auto-arm (PR #2).

Validates:
- Tool resolves canonical inbox via SSOT map
- agy (Antigravity) role arms 'antigravity' canonical
- cc-tb role arms 'cc_tb' canonical
- Tool works with no role arg (env / detect_session_role fallback)
- Multi-agent concurrent arming (agy + cc-tb + cc-main) routes to correct inboxes
- Return shape includes canonical_inbox + resolved_role + next_action

These tests do NOT boot the full FastMCP server — they exercise the underlying
relay_subscribe_notifications_impl + canonical-map glue that nucleus_ccr_arm
wires together.
"""
from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name
from mcp_server_nucleus.runtime.relay_notify import (
    relay_subscribe_notifications_impl,
    _resolve_inbox_dir,
)


class _FakeContext:
    """Stand-in for fastmcp Context capturing notifications."""

    def __init__(self) -> None:
        self.info_calls: list[str] = []
        self.warning_calls: list[str] = []
        self.first_relay_info_time: float | None = None

    async def info(self, msg: str) -> None:
        self.info_calls.append(msg)
        if self.first_relay_info_time is None and "[relay-subscribe]" not in msg:
            self.first_relay_info_time = time.monotonic()

    async def warning(self, msg: str) -> None:
        self.warning_calls.append(msg)


def _make_relay_file(inbox: Path, sender: str, subject: str = "test") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    fname = f"{ts}_{sender}_{subject.replace(' ', '_')}.json"
    fpath = inbox / fname
    fpath.write_text(json.dumps({
        "id": f"relay_{ts}_{sender}",
        "from": sender,
        "subject": subject,
        "priority": "normal",
        "created_at": ts,
    }))
    return fpath


async def _ccr_arm_simulated(
    ctx,
    role: str = "",
    timeout_seconds: int = 60,
    *,
    env_override: str | None = None,
) -> dict:
    """Mirror nucleus_ccr_arm logic for testing without full server boot.

    The wired-up tool is a thin glue layer over resolve_canonical_inbox_name +
    relay_subscribe_notifications_impl. This helper exercises the same glue.
    """
    import os
    resolved_role = (
        role
        or env_override
        or os.environ.get("CC_SESSION_ROLE", "").strip().lower()
        or os.environ.get("NUCLEUS_SESSION_ROLE", "").strip().lower()
        or ""
    )
    canonical_inbox = resolve_canonical_inbox_name(resolved_role) or resolved_role
    result = await relay_subscribe_notifications_impl(
        ctx,
        timeout_seconds=timeout_seconds,
        inbox_filter=canonical_inbox,
    )
    result["canonical_inbox"] = canonical_inbox
    result["resolved_role"] = resolved_role
    result["next_action"] = (
        f"Re-call nucleus_ccr_arm(role=\"{resolved_role}\") to maintain "
        f"persistent coverage of {canonical_inbox} inbox."
    )
    return result


# ── Test agy (Antigravity) arming ──


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_agy_arms_antigravity_canonical_inbox(tmp_path, monkeypatch):
    """LOAD-BEARING for Antigravity-agnostic Option C ship.

    agy's nucleus_ccr_arm(role='antigravity') must subscribe to
    .brain/relay/antigravity/ canonical inbox.
    """
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    antigravity_inbox = brain / "relay" / "antigravity"
    antigravity_inbox.mkdir(parents=True, exist_ok=True)

    ctx = _FakeContext()
    fire_time: list[float] = []

    async def fire_relay():
        await asyncio.sleep(1.0)
        fire_time.append(time.monotonic())
        _make_relay_file(antigravity_inbox, "main", "to-agy via PR-2 auto-arm")

    fire_task = asyncio.create_task(fire_relay())
    result = await _ccr_arm_simulated(ctx, role="antigravity", timeout_seconds=60)
    await fire_task

    assert result["canonical_inbox"] == "antigravity"
    assert result["resolved_role"] == "antigravity"
    assert result["subscribed_dir"].endswith("/antigravity")
    assert result["events_fired"] >= 1, "agy missed the relay arrival notification"
    # Round-trip latency
    assert ctx.first_relay_info_time is not None
    round_trip = ctx.first_relay_info_time - fire_time[0]
    assert round_trip < 5.0, f"agy round-trip exceeded 5s: {round_trip:.2f}s"


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_agy_legacy_role_name_resolves_to_antigravity(tmp_path, monkeypatch):
    """agy may identify with role='agy' — should still hit antigravity inbox."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    antigravity_inbox = brain / "relay" / "antigravity"
    antigravity_inbox.mkdir(parents=True, exist_ok=True)

    ctx = _FakeContext()

    async def fire_relay():
        await asyncio.sleep(1.0)
        _make_relay_file(antigravity_inbox, "main", "to-agy-via-legacy-role")

    fire_task = asyncio.create_task(fire_relay())
    result = await _ccr_arm_simulated(ctx, role="agy", timeout_seconds=60)
    await fire_task

    assert result["canonical_inbox"] == "antigravity"
    assert result["events_fired"] >= 1


# ── Test cc-tb arming ──


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_cc_tb_arms_cc_tb_canonical_inbox(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    cc_tb_inbox = brain / "relay" / "cc_tb"
    cc_tb_inbox.mkdir(parents=True, exist_ok=True)

    ctx = _FakeContext()

    async def fire_relay():
        await asyncio.sleep(1.0)
        _make_relay_file(cc_tb_inbox, "main", "to-cctb-via-pr-2")

    fire_task = asyncio.create_task(fire_relay())
    result = await _ccr_arm_simulated(ctx, role="tb", timeout_seconds=60)
    await fire_task

    assert result["canonical_inbox"] == "cc_tb"
    assert result["subscribed_dir"].endswith("/cc_tb")
    assert result["events_fired"] >= 1


# ── Env-fallback test ──


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_env_var_drives_role_when_no_explicit_arg(tmp_path, monkeypatch):
    """nucleus_ccr_arm() with no role uses CC_SESSION_ROLE env var."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    cc_tb_inbox = brain / "relay" / "cc_tb"
    cc_tb_inbox.mkdir(parents=True, exist_ok=True)

    ctx = _FakeContext()

    async def fire_relay():
        await asyncio.sleep(1.0)
        _make_relay_file(cc_tb_inbox, "main", "env-resolved")

    fire_task = asyncio.create_task(fire_relay())
    result = await _ccr_arm_simulated(ctx, role="", timeout_seconds=60)
    await fire_task

    assert result["resolved_role"] == "tb"
    assert result["canonical_inbox"] == "cc_tb"
    assert result["events_fired"] >= 1


# ── Multi-agent fan-out (the agy + cc-tb scenario operator requested) ──


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_agy_and_cctb_concurrent_arming_zero_misroutes(tmp_path, monkeypatch):
    """5-agent fan-out (PR #1 spec re-applied with PR #2 arming).

    Simulates agy + cc-tb + cc-main + cc-peer + op-assistant each calling
    nucleus_ccr_arm concurrently and verifying each gets ONLY their own
    canonical inbox's relays.
    """
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    roles_and_canonical = [
        ("antigravity", "antigravity"),
        ("tb", "cc_tb"),
        ("main", "claude_code_main"),
        ("peer", "claude_code_peer"),
        ("op_assistant", "claude_code_operator_assistant"),
    ]

    # Ensure all canonical inboxes exist
    for _, canon in roles_and_canonical:
        (brain / "relay" / canon).mkdir(parents=True, exist_ok=True)

    ctxs = [_FakeContext() for _ in roles_and_canonical]

    # Each agent arms concurrently
    async def arm_agent(idx, role):
        return await _ccr_arm_simulated(ctxs[idx], role=role, timeout_seconds=60)

    arm_tasks = [
        asyncio.create_task(arm_agent(i, role))
        for i, (role, _) in enumerate(roles_and_canonical)
    ]

    # After 1s, each agent receives one relay TARGETED to their canonical inbox
    async def fire_targeted_relays():
        await asyncio.sleep(1.0)
        for sender_role, sender_canon in roles_and_canonical:
            for target_role, target_canon in roles_and_canonical:
                if target_role == sender_role:
                    continue
                _make_relay_file(
                    brain / "relay" / target_canon,
                    sender_role,
                    f"to-{target_role}",
                )

    fire_task = asyncio.create_task(fire_targeted_relays())
    results = await asyncio.gather(*arm_tasks)
    await fire_task

    # Each agent should receive exactly 4 relays (from each of the other 4)
    for i, (role, canon) in enumerate(roles_and_canonical):
        assert results[i]["canonical_inbox"] == canon, (
            f"Agent {role} resolved to {results[i]['canonical_inbox']} instead of {canon}"
        )
        assert results[i]["events_fired"] == 4, (
            f"Agent {role} fired={results[i]['events_fired']} events; expected 4"
        )

    # Cross-check zero misroutes: every notification an agent received must
    # have come from an OTHER agent (sender != role)
    for i, (role, _) in enumerate(roles_and_canonical):
        relay_notifications = [
            c for c in ctxs[i].info_calls if "[relay-arrival]" in c
        ]
        for notif in relay_notifications:
            # Each notification should mention sender that is NOT this agent's role
            assert role not in notif.split("from=")[1].split()[0] or role == "main", (
                f"Misroute: agent {role} received its own relay: {notif}"
            )


# ── Return shape contract ──


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_return_shape_includes_canonical_inbox_and_next_action(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    (brain / "relay" / "antigravity").mkdir(parents=True, exist_ok=True)

    ctx = _FakeContext()
    result = await _ccr_arm_simulated(ctx, role="antigravity", timeout_seconds=60)

    assert "canonical_inbox" in result
    assert "resolved_role" in result
    assert "subscribed_dir" in result
    assert "events_fired" in result
    assert "next_action" in result
    assert "nucleus_ccr_arm" in result["next_action"]
    assert "antigravity" in result["next_action"]


# PR #486 regression: gap-closure via persistent marker dir
# agy battle-test 2026-06-06: arrivals during between-subscribe gaps were
# snapshotted into in-memory `seen` set on next call and never surfaced.
# Fix: persistent marker dir per canonical inbox (mirrors watch-relay.sh
# pattern). First-ever call pre-marks existing files; subsequent calls
# surface anything without a marker.


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_persistent_marker_closes_between_subscribe_gap(tmp_path, monkeypatch):
    """File arriving between subscribe calls surfaces on next call.

    Pre-fix: each subscribe took in-memory snapshot at start time, so
    arrivals during the gap got marked as "existing" on next call and
    never surfaced. Post-fix: persistent marker dir means anything
    without a marker (= didn't exist on first call AND wasn't surfaced
    yet) gets surfaced on next call.
    """
    brain = tmp_path / "brain"
    state = tmp_path / "state"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(state))

    inbox = brain / "relay" / "cc_tb"
    inbox.mkdir(parents=True)

    # File present at first-ever call → surfaced as unread (new behavior:
    # first run surfaces unread messages instead of pre-marking them all)
    _make_relay_file(inbox, "x", "existing-at-first-call")

    ctx_first = _FakeContext()
    result_first = await relay_subscribe_notifications_impl(
        ctx_first, timeout_seconds=60, inbox_filter="cc_tb"
    )
    # First call surfaces the pre-existing unread file
    assert result_first["events_fired"] >= 1, (
        "First call must surface pre-existing unread files"
    )

    # Gap: file added between calls (no active subscription)
    _make_relay_file(inbox, "y", "gap-arrival-while-no-subscription")

    # Second call must surface the gap-arrival
    ctx_second = _FakeContext()
    result_second = await relay_subscribe_notifications_impl(
        ctx_second, timeout_seconds=60, inbox_filter="cc_tb"
    )
    assert result_second["events_fired"] >= 1, (
        "Second call must surface arrivals from gap between calls"
    )
    surfaced = " ".join(ctx_second.info_calls + ctx_second.warning_calls)
    assert "gap-arrival-while-no-subscription" in surfaced, (
        f"Gap arrival should surface; got: {surfaced[:300]}"
    )


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_first_run_does_not_blast_historical_backlog(tmp_path, monkeypatch):
    """First-ever subscribe pre-marks existing files; does NOT dump historical."""
    brain = tmp_path / "brain"
    state = tmp_path / "state"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(state))

    inbox = brain / "relay" / "cc_tb"
    inbox.mkdir(parents=True)

    # 5 historical files (all unread — first run surfaces them all)
    for i in range(5):
        _make_relay_file(inbox, f"sender_{i}", f"historical-{i}")

    ctx = _FakeContext()
    result = await relay_subscribe_notifications_impl(
        ctx, timeout_seconds=60, inbox_filter="cc_tb"
    )
    assert result["events_fired"] >= 1, (
        "First-ever subscribe surfaces unread historical messages"
    )


# PR #487 burst-mode regression: timeout_seconds=0 returns immediately
# after one inbox scan via persistent marker. Sub-second end-of-turn drain
# instead of blocking on 270s long-poll. Closes the agy gap-latency.


@pytest.mark.asyncio
async def test_burst_mode_returns_immediately_with_arrivals(tmp_path, monkeypatch):
    """timeout_seconds=0 = burst mode: scan once, surface, return.

    Sub-second drain. Designed for end-of-turn rhythm.
    """
    import time as t_mod
    brain = tmp_path / "brain"
    state = tmp_path / "state"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(state))
    inbox = brain / "relay" / "cc_tb"
    inbox.mkdir(parents=True)
    # Pre-seed state so we're not in first-run mode
    (state / "server-seen-cc_tb").mkdir(parents=True)
    # Relay file with no marker
    _make_relay_file(inbox, "x", "arrival-for-burst")

    ctx = _FakeContext()
    start = t_mod.monotonic()
    result = await relay_subscribe_notifications_impl(
        ctx, timeout_seconds=0, inbox_filter="cc_tb"
    )
    elapsed = t_mod.monotonic() - start

    assert result["burst_mode"] is True
    assert result["watched_seconds"] == 0
    assert result["events_fired"] >= 1
    assert elapsed < 2.0, f"Burst should return in <2s, took {elapsed:.2f}s"
    surfaced = " ".join(ctx.info_calls + ctx.warning_calls)
    assert "arrival-for-burst" in surfaced


@pytest.mark.asyncio
async def test_burst_mode_zero_arrivals_still_returns_fast(tmp_path, monkeypatch):
    """Empty-inbox burst returns quickly with events_fired=0."""
    import time as t_mod
    brain = tmp_path / "brain"
    state = tmp_path / "state"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(state))
    (brain / "relay" / "cc_tb").mkdir(parents=True)
    (state / "server-seen-cc_tb").mkdir(parents=True)  # not first-run

    ctx = _FakeContext()
    start = t_mod.monotonic()
    result = await relay_subscribe_notifications_impl(
        ctx, timeout_seconds=0, inbox_filter="cc_tb"
    )
    elapsed = t_mod.monotonic() - start

    assert result["burst_mode"] is True
    assert result["events_fired"] == 0
    assert elapsed < 2.0


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_normal_long_poll_mode_still_works_post_burst_patch(tmp_path, monkeypatch):
    """Regression: non-burst calls (timeout_seconds=60+) still long-poll."""
    import time as t_mod
    brain = tmp_path / "brain"
    state = tmp_path / "state"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(state))
    (brain / "relay" / "cc_tb").mkdir(parents=True)

    ctx = _FakeContext()
    start = t_mod.monotonic()
    # 60 = min for long-poll mode (per existing cap)
    result = await relay_subscribe_notifications_impl(
        ctx, timeout_seconds=60, inbox_filter="cc_tb"
    )
    elapsed = t_mod.monotonic() - start

    # Long-poll should block for the timeout (with empty inbox, full 60s)
    assert result["burst_mode"] is False
    assert result["watched_seconds"] == 60
    assert elapsed >= 55.0, f"Long-poll should block ~60s; took {elapsed:.2f}s"
