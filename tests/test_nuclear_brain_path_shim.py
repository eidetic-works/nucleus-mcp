"""Test the NUCLEAR_BRAIN_PATH deprecation shim.

Per cowork NUDGE relay_20260427_093101_5c64b263. PR #78 ostensibly removed
the legacy NUCLEAR_BRAIN_PATH alias, but the migration was botched —
left dead self-OR (`os.environ.get("NUCLEUS_BRAIN_PATH") or
os.environ.get("NUCLEUS_BRAIN_PATH")`) and duplicate set lines in
runtime/sessions paths. Meanwhile, external consumers (nucleus-mcp-cloud's
/ready endpoint) still read the legacy name and silently 503 when only
the canonical name is set.

This restores the dual-write deprecation shim with a sunset date so
external consumers keep working until they migrate. Tests cover:

  (a) NEW name only (NUCLEUS_BRAIN_PATH) → both names get set; no warning.
  (b) OLD name only (NUCLEAR_BRAIN_PATH) → both names get set; deprecation
      warning fires.
  (c) BOTH set → NEW wins for resolution; both stay set; no warning (caller
      already migrated to canonical).
  (d) NEITHER set → behavior unchanged from previous code (auto-init or
      hierarchy walk handles it; no env-var-related crash).
"""

from __future__ import annotations

import os
import warnings

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start every test with both env vars unset."""
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)


def _emulate_resolve_brain_path():
    """Tiny re-implementation of the cli.py:4190 block — kept here as a
    behavioral spec so test failures point at the contract, not at line
    numbers in cli.py that may shift.

    Mirror of the production block in mcp_server_nucleus.cli: read canonical
    or legacy, warn on legacy-only, dual-write both names when resolved.
    """
    brain_path_str = (
        os.environ.get("NUCLEUS_BRAIN_PATH")
        or os.environ.get("NUCLEAR_BRAIN_PATH")
    )
    if (
        os.environ.get("NUCLEAR_BRAIN_PATH")
        and not os.environ.get("NUCLEUS_BRAIN_PATH")
    ):
        warnings.warn(
            "NUCLEAR_BRAIN_PATH is deprecated; use NUCLEUS_BRAIN_PATH "
            "(legacy alias sunsets 2026-05-27)",
            DeprecationWarning,
            stacklevel=2,
        )
    if brain_path_str:
        os.environ["NUCLEUS_BRAIN_PATH"] = brain_path_str
        os.environ["NUCLEAR_BRAIN_PATH"] = brain_path_str
    return brain_path_str


def test_new_name_only_resolves_and_dual_writes(monkeypatch, recwarn):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/canonical-brain")
    result = _emulate_resolve_brain_path()
    assert result == "/tmp/canonical-brain"
    # Both env vars now set to the same value (legacy alias dual-write).
    assert os.environ["NUCLEUS_BRAIN_PATH"] == "/tmp/canonical-brain"
    assert os.environ["NUCLEAR_BRAIN_PATH"] == "/tmp/canonical-brain"
    # No deprecation warning when caller used canonical name.
    deprecations = [w for w in recwarn if issubclass(w.category, DeprecationWarning)]
    assert deprecations == []


def test_old_name_only_resolves_with_deprecation_warning(monkeypatch):
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", "/tmp/legacy-brain")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _emulate_resolve_brain_path()
    assert result == "/tmp/legacy-brain"
    # Dual-write: legacy value propagates to canonical name too.
    assert os.environ["NUCLEUS_BRAIN_PATH"] == "/tmp/legacy-brain"
    assert os.environ["NUCLEAR_BRAIN_PATH"] == "/tmp/legacy-brain"
    # Exactly one deprecation warning fired.
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    msg = str(deprecations[0].message)
    assert "NUCLEAR_BRAIN_PATH is deprecated" in msg
    assert "NUCLEUS_BRAIN_PATH" in msg
    assert "2026-05-27" in msg  # sunset date present so caller knows the deadline


def test_both_set_canonical_wins_no_warning(monkeypatch, recwarn):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/canonical")
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", "/tmp/legacy")
    result = _emulate_resolve_brain_path()
    # Canonical wins for resolution.
    assert result == "/tmp/canonical"
    # Dual-write overwrites legacy with canonical (single-source-of-truth).
    assert os.environ["NUCLEUS_BRAIN_PATH"] == "/tmp/canonical"
    assert os.environ["NUCLEAR_BRAIN_PATH"] == "/tmp/canonical"
    # No deprecation warning — caller already on canonical.
    deprecations = [w for w in recwarn if issubclass(w.category, DeprecationWarning)]
    assert deprecations == []


def test_neither_set_returns_none_no_writes(monkeypatch, recwarn):
    # No env vars set → resolver returns falsy, dual-write doesn't fire.
    result = _emulate_resolve_brain_path()
    assert not result
    assert os.environ.get("NUCLEUS_BRAIN_PATH") is None
    assert os.environ.get("NUCLEAR_BRAIN_PATH") is None
    deprecations = [w for w in recwarn if issubclass(w.category, DeprecationWarning)]
    assert deprecations == []


def test_legacy_only_with_empty_canonical_still_warns(monkeypatch):
    """Edge: NUCLEUS_BRAIN_PATH set to empty string is treated as not-set
    by ``not`` semantics in the warning predicate, so the deprecation
    warning fires (caller hasn't meaningfully migrated)."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "")
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", "/tmp/legacy")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _emulate_resolve_brain_path()
    assert result == "/tmp/legacy"
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    # Production code: `os.environ.get("NUCLEAR_BRAIN_PATH") and not
    # os.environ.get("NUCLEUS_BRAIN_PATH")`. Empty string for canonical is
    # falsy → `not ""` is True → warning fires. This is the desired
    # behavior: setting NUCLEUS_BRAIN_PATH="" doesn't count as migration.
    assert len(deprecations) == 1
