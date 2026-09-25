"""Tests for the NUCLEAR_BRAIN_PATH legacy-alias path in
``mcp_server_nucleus.runtime.common.get_brain_path``.

The runtime resolver checks ``NUCLEUS_BRAIN_PATH`` first, then falls back to
the deprecated ``NUCLEAR_BRAIN_PATH`` alias. When the legacy alias is the one
that forced the resolved path (canonical unset), a deprecation warning is
emitted **once per process** via the module-level sentinel
``_nuclear_alias_warned``.

That once-per-process sentinel is a hazard for the test suite: a prior test
that triggered the emit suppresses the warning for every later test, and the
developer's real env (either var set in the shell) can leak in. The autouse
fixture below clears both env vars and resets the sentinel before every test
so each test starts from a clean baseline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import common


# ── autouse isolation ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_brain_env(monkeypatch):
    """Clear both brain-path env vars and reset the once-per-process warning
    sentinel before every test.

    Without this, a test inheriting the developer's real ``NUCLEAR_BRAIN_PATH``
    would resolve to the wrong brain, and a test running after one that already
    emitted the deprecation warning would see the sentinel stuck at ``True``
    and never observe the warning it expects.
    """
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    common._nuclear_alias_warned = False


# ── helpers ────────────────────────────────────────────────────────────────

def _depwarning_records(caplog) -> list:
    """Filter caplog records down to the legacy-alias deprecation warning."""
    return [
        r for r in caplog.records
        if r.levelno == logging.WARNING
        and "NUCLEAR_BRAIN_PATH is deprecated" in r.getMessage()
    ]


# ── tests ──────────────────────────────────────────────────────────────────

def test_canonical_only_resolves_no_warning(monkeypatch, tmp_path, caplog):
    """NUCLEUS_BRAIN_PATH set, NUCLEAR_BRAIN_PATH unset → resolves to the
    canonical path and emits no deprecation warning."""
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.chdir(tmp_path)  # avoid the .brain cwd/parent walk on fallback

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        result = common.get_brain_path()

    assert result == brain
    assert _depwarning_records(caplog) == []


def test_legacy_only_resolves_and_warns_once(monkeypatch, tmp_path, caplog):
    """NUCLEAR_BRAIN_PATH set, NUCLEUS_BRAIN_PATH unset → resolves to the
    legacy path and emits the deprecation warning exactly once, even on a
    second call (sentinel guards repeat emission)."""
    brain = tmp_path / "legacy-brain"
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(brain))
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        first = common.get_brain_path()
        second = common.get_brain_path()

    assert first == brain
    assert second == brain
    warnings = _depwarning_records(caplog)
    assert len(warnings) == 1, "deprecation warning must fire once, not per call"
    msg = warnings[0].getMessage()
    assert "NUCLEAR_BRAIN_PATH is deprecated" in msg
    assert "NUCLEUS_BRAIN_PATH" in msg


def test_both_set_canonical_wins_no_warning(monkeypatch, tmp_path, caplog):
    """Both env vars set → canonical NUCLEUS_BRAIN_PATH wins for resolution
    and no deprecation warning fires (caller already migrated)."""
    canonical = tmp_path / "canonical"
    legacy = tmp_path / "legacy"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(canonical))
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(legacy))
    monkeypatch.chdir(tmp_path)

    # Capture at DEBUG so the broader silence assertion below sees every
    # record the nucleus logger emits, not just WARNING+.
    with caplog.at_level(logging.DEBUG, logger="nucleus"):
        result = common.get_brain_path()

    assert result == canonical
    assert _depwarning_records(caplog) == []
    # OPPOSED — SILENT: no record at any level may mention the legacy alias
    # when the caller has already set the canonical var. Broader than the
    # deprecation-warning filter above — catches any future code path that
    # logs about NUCLEAR_BRAIN_PATH in a non-deprecation context.
    nuclear_mentions = [
        r for r in caplog.records
        if "NUCLEAR_BRAIN_PATH" in r.getMessage()
    ]
    assert nuclear_mentions == [], (
        "expected silence on NUCLEAR_BRAIN_PATH when NUCLEUS_BRAIN_PATH is set, "
        f"but got: {[r.getMessage() for r in nuclear_mentions]}"
    )


def test_neither_var_set_brain_in_cwd_no_warning(monkeypatch, tmp_path, caplog):
    """Neither env var set, ``.brain`` exists in cwd → resolves via the
    cwd fallback walk and emits no record mentioning ``NUCLEAR_BRAIN_PATH``
    at any level.

    The autouse fixture already clears both env vars, so this test exercises
    the pure cwd-fallback path (``common.get_brain_path`` § "Smart fallback").
    Capturing at DEBUG so the silence assertion sees every record the nucleus
    logger emits, not just WARNING+.
    """
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.DEBUG, logger="nucleus"):
        result = common.get_brain_path()

    assert result == brain
    nuclear_mentions = [
        r for r in caplog.records
        if "NUCLEAR_BRAIN_PATH" in r.getMessage()
    ]
    assert nuclear_mentions == [], (
        "expected silence on NUCLEAR_BRAIN_PATH when neither env var is set, "
        f"but got: {[r.getMessage() for r in nuclear_mentions]}"
    )


def test_sentinel_reset_between_tests(monkeypatch, tmp_path, caplog):
    """Regression guard for the fixture itself: this test asserts the
    deprecation warning fires. If the autouse fixture failed to reset
    ``_nuclear_alias_warned``, a preceding test that triggered the emit
    (``test_legacy_only_resolves_and_warns_once``) would leave the sentinel
    at ``True`` and this test would see zero warnings — a false pass that
    masks a real regression.

    Ordering is not guaranteed by pytest, so this must hold regardless of
    execution order, which is exactly what the sentinel reset guarantees.
    """
    brain = tmp_path / "reset-brain"
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(brain))
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.WARNING, logger="nucleus"):
        common.get_brain_path()

    assert len(_depwarning_records(caplog)) == 1, (
        "sentinel was not reset before this test — the autouse fixture is "
        "not clearing _nuclear_alias_warned"
    )
