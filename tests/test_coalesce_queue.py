"""Tests for v0.3.1 — sessions.coalesce_queue (disk-persistent).

REPLACES v0.3.0 in-memory tests. Per cc-peer 2026-06-09T13:15Z Q4 floor
+ Q3 edge case + Q5 sub-bug + Q2 race-window.

Coverage:
- test_add_arrival_persists_first_ts_to_disk (Q4 floor #1)
- test_drain_ready_roles_reads_stale_file_fires_and_deletes (Q4 floor #2)
- test_drain_ready_roles_skips_fresh_file (Q4 floor #3)
- test_concurrent_arrivals_in_same_role_coalesce (Q4 floor #4 / Q2)
- test_TB_AUTONOMOUS_WAKE_COALESCE_S_eq_0_fires_immediately (Q4 floor #5 / Q5)
- test_clock_backwards_treated_as_not_yet_stale (Q4 floor #6 / Q3)
- test_grace_window_negative_returns_default (Q5 FYI typo-protection)

Plus subprocess-spawn smoke (Step 2 instrument per cc-peer recalibration):
- test_state_survives_process_boundary (one subprocess writes, another reads)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.sessions import coalesce_queue as cq


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Redirect ~/.tb/ to per-test tmp dir."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(cq, "_COALESCE_DIR", tmp_path / ".tb")
    monkeypatch.delenv("TB_AUTONOMOUS_WAKE_COALESCE_S", raising=False)
    yield
    cq.clear_pending()


# ── Q4 floor #1: add_arrival persists first_ts to disk ─────────────────


def test_add_arrival_persists_first_ts_to_disk(tmp_path):
    cq.add_arrival("cc_tb", {"id": "r1"})
    path = tmp_path / ".tb" / "coalesce_cc_tb.json"
    assert path.exists()
    state = json.loads(path.read_text())
    assert "first_ts" in state
    assert isinstance(state["first_ts"], (int, float))
    assert state["arrivals"] == [{"id": "r1"}]


def test_add_arrival_file_mode_0o600(tmp_path):
    cq.add_arrival("cc_tb", {})
    path = tmp_path / ".tb" / "coalesce_cc_tb.json"
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600


def test_add_arrival_atomic_via_tmp_replace(monkeypatch, tmp_path):
    seen_tmp = []
    orig_replace = Path.replace

    def _trace(self, target):
        if str(self).endswith(".tmp"):
            seen_tmp.append(str(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _trace)
    cq.add_arrival("cc_tb", {})
    assert any(".tmp" in s for s in seen_tmp)


def test_add_arrival_empty_role_raises():
    with pytest.raises(ValueError):
        cq.add_arrival("", {})


# ── Q4 floor #2: drain reads stale + fires + deletes ───────────────────


def test_drain_ready_roles_reads_stale_file_fires_and_deletes(
    tmp_path, monkeypatch,
):
    """Stale file (first_ts > grace ago) → returned in drain + deleted."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "0.001")
    cq.add_arrival("cc_tb", {"id": "r1"})
    cq.add_arrival("cc_tb", {"id": "r2"})

    # Sleep past grace
    time.sleep(0.01)

    ready = cq.drain_ready_roles()
    assert "cc_tb" in ready
    assert len(ready["cc_tb"]) == 2
    assert ready["cc_tb"][0] == {"id": "r1"}
    assert ready["cc_tb"][1] == {"id": "r2"}

    # File deleted post-drain
    path = tmp_path / ".tb" / "coalesce_cc_tb.json"
    assert not path.exists()


# ── Q4 floor #3: drain skips fresh files ────────────────────────────────


def test_drain_ready_roles_skips_fresh_file(monkeypatch, tmp_path):
    """File with first_ts within grace window → NOT drained."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq.add_arrival("cc_tb", {"id": "r1"})

    ready = cq.drain_ready_roles()
    assert ready == {}

    # File still on disk
    path = tmp_path / ".tb" / "coalesce_cc_tb.json"
    assert path.exists()


# ── Q4 floor #4 / Q2: concurrent arrivals coalesce (read-merge-write) ──


def test_concurrent_arrivals_in_same_role_coalesce(monkeypatch):
    """3 sequential add_arrival calls → all 3 preserved in file."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq.add_arrival("cc_tb", {"id": "r1"})
    cq.add_arrival("cc_tb", {"id": "r2"})
    cq.add_arrival("cc_tb", {"id": "r3"})

    pending = cq.peek_pending()
    assert pending == {"cc_tb": 3}


def test_concurrent_arrivals_preserve_first_ts(monkeypatch, tmp_path):
    """first_ts set on FIRST arrival; subsequent arrivals do NOT update it."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq.add_arrival("cc_tb", {"id": "r1"})
    path = tmp_path / ".tb" / "coalesce_cc_tb.json"
    first_state = json.loads(path.read_text())
    first_ts = first_state["first_ts"]

    time.sleep(0.05)
    cq.add_arrival("cc_tb", {"id": "r2"})

    second_state = json.loads(path.read_text())
    assert second_state["first_ts"] == first_ts
    assert len(second_state["arrivals"]) == 2


# ── Q4 floor #5 / Q5: TB_AUTONOMOUS_WAKE_COALESCE_S=0 fires immediately


def test_TB_AUTONOMOUS_WAKE_COALESCE_S_eq_0_fires_immediately(monkeypatch):
    """Q5 fix: 0 means immediate-fire (was: 0 fell back to 10s default)."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "0")
    assert cq._grace_window_s() == 0.0

    cq.add_arrival("cc_tb", {"id": "r1"})
    ready = cq.drain_ready_roles()
    assert "cc_tb" in ready
    assert ready["cc_tb"] == [{"id": "r1"}]


# ── Q4 floor #6 / Q3: clock-backwards safe ─────────────────────────────


def test_clock_backwards_treated_as_not_yet_stale(
    monkeypatch, tmp_path,
):
    """If wall-clock moves backwards (NTP/manual), elapsed negative.
    max(0, elapsed) → role NOT drained (conservative)."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "0.001")
    cq._COALESCE_DIR.mkdir(mode=0o700, exist_ok=True)
    future_ts = time.time() + 10000.0
    (cq._COALESCE_DIR / "coalesce_cc_tb.json").write_text(json.dumps({
        "first_ts": future_ts,
        "arrivals": [{"id": "r1"}],
    }))

    ready = cq.drain_ready_roles()
    assert ready == {}
    assert (cq._COALESCE_DIR / "coalesce_cc_tb.json").exists()


# ── Q5 FYI: negative env value falls back to default (typo protection) ─


def test_grace_window_negative_returns_default(monkeypatch):
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "-5")
    assert cq._grace_window_s() == cq._DEFAULT_GRACE_S


def test_grace_window_non_numeric_returns_default(monkeypatch):
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "abc")
    assert cq._grace_window_s() == cq._DEFAULT_GRACE_S


def test_grace_window_unset_returns_default(monkeypatch):
    monkeypatch.delenv("TB_AUTONOMOUS_WAKE_COALESCE_S", raising=False)
    assert cq._grace_window_s() == cq._DEFAULT_GRACE_S


def test_grace_window_positive_override_works(monkeypatch):
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "30")
    assert cq._grace_window_s() == 30.0


# ── Per-role independence ──────────────────────────────────────────────


def test_one_role_stale_other_fresh(monkeypatch, tmp_path):
    """Only stale role drained; fresh role file preserved."""
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq._COALESCE_DIR.mkdir(mode=0o700, exist_ok=True)
    (cq._COALESCE_DIR / "coalesce_cc_tb.json").write_text(json.dumps({
        "first_ts": time.time() - 200.0,
        "arrivals": [{"id": "stale"}],
    }))
    (cq._COALESCE_DIR / "coalesce_cc_peer.json").write_text(json.dumps({
        "first_ts": time.time(),
        "arrivals": [{"id": "fresh"}],
    }))

    ready = cq.drain_ready_roles()
    assert "cc_tb" in ready
    assert "cc_peer" not in ready
    assert (cq._COALESCE_DIR / "coalesce_cc_peer.json").exists()
    assert not (cq._COALESCE_DIR / "coalesce_cc_tb.json").exists()


# ── peek_pending / clear_pending ───────────────────────────────────────


def test_peek_pending_empty_when_no_files():
    assert cq.peek_pending() == {}


def test_peek_pending_returns_counts(monkeypatch):
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq.add_arrival("cc_tb", {})
    cq.add_arrival("cc_tb", {})
    cq.add_arrival("cc_peer", {})
    assert cq.peek_pending() == {"cc_tb": 2, "cc_peer": 1}


def test_clear_pending_role_only(monkeypatch):
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq.add_arrival("cc_tb", {})
    cq.add_arrival("cc_peer", {})
    cq.clear_pending("cc_tb")
    assert cq.peek_pending() == {"cc_peer": 1}


def test_clear_pending_all(monkeypatch):
    monkeypatch.setenv("TB_AUTONOMOUS_WAKE_COALESCE_S", "100")
    cq.add_arrival("cc_tb", {})
    cq.add_arrival("cc_peer", {})
    cq.clear_pending()
    assert cq.peek_pending() == {}


# ── Defensive: corrupt file handled ────────────────────────────────────


def test_corrupt_file_treated_as_absent_on_read(tmp_path, monkeypatch):
    cq._COALESCE_DIR.mkdir(mode=0o700, exist_ok=True)
    (cq._COALESCE_DIR / "coalesce_cc_tb.json").write_text("not-json{")
    assert cq.peek_pending() == {}
    assert cq.drain_ready_roles() == {}


def test_corrupt_file_overwritten_by_new_arrival(monkeypatch, tmp_path):
    cq._COALESCE_DIR.mkdir(mode=0o700, exist_ok=True)
    (cq._COALESCE_DIR / "coalesce_cc_tb.json").write_text("corrupt")
    cq.add_arrival("cc_tb", {"id": "r1"})
    state = json.loads((cq._COALESCE_DIR / "coalesce_cc_tb.json").read_text())
    assert state["arrivals"] == [{"id": "r1"}]


# ── Module exports ─────────────────────────────────────────────────────


def test_all_exported():
    expected = {"add_arrival", "drain_ready_roles", "peek_pending", "clear_pending"}
    assert set(cq.__all__) == expected


# ── Step 2 instrument: state survives subprocess boundary ──────────────


def test_state_survives_process_boundary(subprocess_runner, tmp_path):
    """v0.3.0 -> v0.3.1 load-bearing test. v0.3.0 module-level _pending
    dict was lost across subprocesses; v0.3.1 disk-persistent state survives.

    Subprocess A: add_arrival.
    Subprocess B: peek_pending must see 1 arrival.
    Subprocess C: drain_ready_roles with grace=0 must return the role.
    """
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    tmp_str = str(tmp_path)

    code_add = (
        f"import os, sys\n"
        f"sys.path.insert(0, {src_path!r})\n"
        f"os.environ['HOME'] = {tmp_str!r}\n"
        f"from mcp_server_nucleus.sessions import coalesce_queue as cq\n"
        f"from pathlib import Path\n"
        f"cq._COALESCE_DIR = Path({tmp_str!r}) / '.tb'\n"
        f"cq.add_arrival('cc_tb', {{'id': 'r1'}})\n"
        f"print('OK')\n"
    )

    rc, out, err = subprocess_runner(code_add)
    assert rc == 0, f"add subprocess failed: stderr={err}"
    assert "OK" in out

    code_peek = (
        f"import os, sys, json\n"
        f"sys.path.insert(0, {src_path!r})\n"
        f"os.environ['HOME'] = {tmp_str!r}\n"
        f"from mcp_server_nucleus.sessions import coalesce_queue as cq\n"
        f"from pathlib import Path\n"
        f"cq._COALESCE_DIR = Path({tmp_str!r}) / '.tb'\n"
        f"print(json.dumps(cq.peek_pending()))\n"
    )

    rc, out, err = subprocess_runner(code_peek)
    assert rc == 0, f"peek subprocess failed: stderr={err}"
    last_line = out.strip().splitlines()[-1]
    peek_result = json.loads(last_line)
    assert peek_result == {"cc_tb": 1}

    code_drain = (
        f"import os, sys, json\n"
        f"sys.path.insert(0, {src_path!r})\n"
        f"os.environ['HOME'] = {tmp_str!r}\n"
        f"os.environ['TB_AUTONOMOUS_WAKE_COALESCE_S'] = '0'\n"
        f"from mcp_server_nucleus.sessions import coalesce_queue as cq\n"
        f"from pathlib import Path\n"
        f"cq._COALESCE_DIR = Path({tmp_str!r}) / '.tb'\n"
        f"print(json.dumps(cq.drain_ready_roles()))\n"
    )

    rc, out, err = subprocess_runner(code_drain)
    assert rc == 0, f"drain subprocess failed: stderr={err}"
    last_line = out.strip().splitlines()[-1]
    drain_result = json.loads(last_line)
    assert "cc_tb" in drain_result
    assert drain_result["cc_tb"] == [{"id": "r1"}]
