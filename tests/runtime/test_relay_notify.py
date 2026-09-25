"""Tests for runtime.relay_notify — native MCP notifications.

Operator FOUNDER-OVERRIDE 2026-05-31 (relay_20260531_152027_00d0da76).
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.relay_notify import (
    _envelope_summary,
    _resolve_inbox_dir,
    relay_subscribe_notifications_impl,
)


class _RecordingCtx:
    """Async-compatible Context stub that records info/warning calls."""

    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    async def info(self, msg: str) -> None:
        self.infos.append(msg)

    async def warning(self, msg: str) -> None:
        self.warnings.append(msg)


def _write_envelope(dir_: Path, name: str, **fields) -> Path:
    p = dir_ / f"{name}.json"
    p.write_text(json.dumps({"id": name, "from": "test", "subject": "smoke", **fields}))
    return p


def test_envelope_summary_happy_path(tmp_path: Path) -> None:
    p = _write_envelope(tmp_path, "abc", subject="hello", priority="high")
    env = _envelope_summary(p)
    assert env["id"] == "abc"
    assert env["from"] == "test"
    assert env["subject"] == "hello"
    assert env["priority"] == "high"


def test_envelope_summary_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "broken.json"
    p.write_text("not json {{{")
    env = _envelope_summary(p)
    assert env["id"] == "broken"
    assert "parse_failed" in env.get("error", "")


def test_resolve_inbox_dir_role_main(monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = _resolve_inbox_dir("main")
    assert inbox.name == "claude_code_main"


def test_resolve_inbox_dir_role_full_name(monkeypatch: pytest.MonkeyPatch) -> None:
    inbox = _resolve_inbox_dir("claude_code_operator_assistant")
    assert inbox.name == "claude_code_operator_assistant"


@pytest.mark.asyncio
async def test_subscribe_fires_on_new_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop a file mid-subscription, assert ctx.info() fires."""
    # Redirect _get_relay_dir to tmp_path so our subscription watches it
    from mcp_server_nucleus.runtime import relay_ops, relay_notify

    monkeypatch.setattr(relay_notify, "_resolve_inbox_dir", lambda role=None, **kw: tmp_path)
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(tmp_path / "state"))

    ctx = _RecordingCtx()

    async def producer():
        await asyncio.sleep(0.4)  # let subscription register seen-set first
        _write_envelope(tmp_path, "new_arrival", subject="surprise")

    sub_task = asyncio.create_task(
        relay_subscribe_notifications_impl(ctx, timeout_seconds=60, role="main")
    )
    prod_task = asyncio.create_task(producer())

    # Cap wall-clock at 3s (subscription clamps min to 60s but we cancel)
    await asyncio.sleep(3.0)
    sub_task.cancel()
    try:
        await sub_task
    except asyncio.CancelledError:
        pass
    await prod_task

    # First ctx.info is the "[relay-subscribe] watching" line; second should be the arrival
    arrival_msgs = [m for m in ctx.infos if "[relay-arrival]" in m]
    assert len(arrival_msgs) == 1, f"expected 1 arrival, got: {ctx.infos}"
    assert "new_arrival" in arrival_msgs[0]
    assert "surprise" in arrival_msgs[0]


@pytest.mark.asyncio
async def test_subscribe_high_priority_uses_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_server_nucleus.runtime import relay_notify

    monkeypatch.setattr(relay_notify, "_resolve_inbox_dir", lambda role=None, **kw: tmp_path)
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(tmp_path / "state"))

    ctx = _RecordingCtx()

    async def producer():
        await asyncio.sleep(0.4)
        _write_envelope(tmp_path, "urgent_msg", priority="urgent", subject="ALERT")

    sub_task = asyncio.create_task(
        relay_subscribe_notifications_impl(ctx, timeout_seconds=60, role="main")
    )
    prod_task = asyncio.create_task(producer())

    await asyncio.sleep(3.0)
    sub_task.cancel()
    try:
        await sub_task
    except asyncio.CancelledError:
        pass
    await prod_task

    assert any("urgent_msg" in w for w in ctx.warnings), \
        f"urgent envelope should ctx.warning(), got infos={ctx.infos} warnings={ctx.warnings}"
