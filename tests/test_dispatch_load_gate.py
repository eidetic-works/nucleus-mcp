"""Regression: vendor dispatch must respect host load, not just lane count.

Defect (flywheel triage REAL): _DISPATCH_MAX_CONCURRENT caps concurrent
dispatches but nothing checked host load — a fleet on a loaded host keeps
spawning vendor subprocesses, worsening the pileup it caused.
"""
import os
import time

import pytest

from mcp_server_nucleus.runtime import vendor_dispatch as vd


class TestWaitForLoad:
    def test_low_load_returns_immediately(self, monkeypatch):
        monkeypatch.setattr(os, "getloadavg", lambda: (0.1, 0.1, 0.1))
        t0 = time.monotonic()
        vd._wait_for_load()
        assert time.monotonic() - t0 < 1.0

    def test_high_load_waits_until_ceiling(self, monkeypatch):
        monkeypatch.setattr(os, "getloadavg", lambda: (999.0, 999.0, 999.0))
        monkeypatch.setattr(vd, "_LOAD_MAX_WAIT", 0.5)
        monkeypatch.setattr(vd, "_LOAD_POLL", 0.05)
        t0 = time.monotonic()
        vd._wait_for_load()
        elapsed = time.monotonic() - t0
        # Proceeded only because the bounded ceiling hit — never blocks forever.
        assert 0.4 <= elapsed < 5.0

    def test_high_load_returns_early_when_load_drops(self, monkeypatch):
        loads = iter([999.0, 999.0, 0.1, 0.1, 0.1])
        monkeypatch.setattr(os, "getloadavg", lambda: (next(loads), 0.1, 0.1))
        monkeypatch.setattr(vd, "_LOAD_MAX_WAIT", 30)
        monkeypatch.setattr(vd, "_LOAD_POLL", 0.05)
        t0 = time.monotonic()
        vd._wait_for_load()
        assert time.monotonic() - t0 < 5.0

    def test_missing_getloadavg_is_noop(self, monkeypatch):
        monkeypatch.delattr(os, "getloadavg")
        vd._wait_for_load()  # must not raise
