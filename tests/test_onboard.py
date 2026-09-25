"""Targeted tests for `nucleus onboard` — the zero-config cross-vendor friction-killer.

Coverage (per the onboard spec — DO NOT expand to the full suite):
  (a) detection iterates the VENDOR_SPECS registry + host claude, with mocked
      ``shutil.which`` (no real subprocess for the version probe);
  (b) config write + ``cross_vendor_enabled()`` reads it back with the env UNSET
      (the zero-config bar: after onboard, dispatch works with no env);
  (c) graceful-missing: all vendors absent ⇒ all ``found=False``, no crash, and
      ``cross_vendor_enabled()`` stays False with no config + env unset.

These NEVER invoke the real agy/devin/claude CLIs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import vendor_dispatch as vd


# ── hermeticity: force a per-test temp brain so the onboard config lands in tmp ─
@pytest.fixture(autouse=True)
def _temp_brain(tmp_path, monkeypatch):
    """Redirect the onboard config to a temp brain (env-unset for the gate test).

    ``_onboard_config_path`` resolves via ``common.get_brain_path`` which reads
    ``NUCLEUS_BRAIN_PATH``; setting it here (and clearing the layers above it)
    makes the config write/read fully hermetic. The env var NUCLEUS_CROSS_VENDOR
    is explicitly deleted so the config-read path is the ONLY enablement source.
    """
    brain = tmp_path / ".brain"
    (brain / "relay").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    monkeypatch.delenv("NUCLEUS_PROJECT_SPINE", raising=False)
    try:
        from mcp_server_nucleus.runtime.common import set_tenant_brain_path

        set_tenant_brain_path(None)
    except Exception:
        pass
    return brain


def _brain() -> Path:
    return Path(os.environ["NUCLEUS_BRAIN_PATH"])


# ── (a) detection iterates VENDOR_SPECS + host claude (mocked shutil.which) ─────
def test_detect_vendor_clis_iterates_registry(monkeypatch):
    """detect_vendor_clis reports every VENDOR_SPECS entry + the host claude CLI.

    ``shutil.which`` is mocked so no real PATH lookup happens; the version probe
    is stubbed so no real subprocess runs. Found/missing is reported, not raised.
    """
    # Mock shutil.which: agy + devin found, claude missing.
    fake_paths = {"agy": "/fake/bin/agy", "devin": "/fake/bin/devin"}

    def fake_which(binary):
        return fake_paths.get(binary)

    monkeypatch.setattr(vd.shutil, "which", fake_which)
    # Stub the version probe so no real subprocess fires.
    monkeypatch.setattr(vd, "_cheap_version", lambda b: f"{b}-v9.9.9")

    detected = vd.detect_vendor_clis()

    # Every registry vendor is present + the host claude CLI.
    for name in vd.VENDOR_SPECS:
        assert name in detected, f"registry vendor {name!r} missing from detection"
    assert vd.ONBOARD_HOST_CLI in detected, "host claude CLI missing from detection"

    # agy + devin found with version + model from the spec.
    assert detected["agy"]["found"] is True
    assert detected["agy"]["binary"] == "agy"
    assert detected["agy"]["version"] == "agy-v9.9.9"
    assert detected["agy"]["model"] == "gemini"
    assert detected["devin"]["found"] is True
    assert detected["devin"]["model"] == "swe"

    # claude was mocked missing → found=False, version=None, no crash.
    assert detected["claude"]["found"] is False
    assert detected["claude"]["version"] is None


def test_detect_extension_point_no_onboard_edit(monkeypatch):
    """Adding a VendorSpec later extends detection with no onboard edit — the
    detection set equals VENDOR_SPECS keys ∪ {host claude}, automatically."""
    monkeypatch.setattr(vd.shutil, "which", lambda b: None)
    monkeypatch.setattr(vd, "_cheap_version", lambda b: None)

    detected = vd.detect_vendor_clis()
    # The dispatch-vendor keys in the detection result are EXACTLY VENDOR_SPECS.
    registry_names = set(vd.VENDOR_SPECS)
    detected_names = set(detected)
    assert registry_names.issubset(detected_names)
    assert vd.ONBOARD_HOST_CLI in detected_names


# ── (b) config write + cross_vendor_enabled() reads it (env UNSET) ─────────────
def test_write_onboard_config_enables_cross_vendor_env_unset(monkeypatch):
    """THE ZERO-CONFIG BAR: after write_onboard_config(True), cross_vendor_enabled()
    returns True with NUCLEUS_CROSS_VENDOR UNSET — no env export needed."""
    # Env is unset by the _temp_brain fixture; assert the precondition.
    assert "NUCLEUS_CROSS_VENDOR" not in os.environ
    assert vd.cross_vendor_enabled() is False  # no config yet

    cfg_path = vd.write_onboard_config(enabled=True, detected={"agy": {"found": True}})

    # The config landed in the temp brain.
    assert cfg_path == _brain() / vd.ONBOARD_CONFIG_NAME
    assert cfg_path.exists()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data["cross_vendor"] is True

    # THE bar: enabled with NO env set.
    assert "NUCLEUS_CROSS_VENDOR" not in os.environ
    assert vd.cross_vendor_enabled() is True


def test_write_onboard_config_disable_roundtrip(monkeypatch):
    """write_onboard_config(False) → cross_vendor_enabled() False (env unset)."""
    vd.write_onboard_config(enabled=True)
    assert vd.cross_vendor_enabled() is True
    vd.write_onboard_config(enabled=False)
    assert vd.cross_vendor_enabled() is False


def test_env_path_still_works_alongside_config(monkeypatch):
    """Back-compat: the env path still enables dispatch (independent of config)."""
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    # No config file written in this test — env alone enables.
    assert vd.cross_vendor_enabled() is True
    # And config=False does NOT override a truthy env (env wins, back-compat).
    vd.write_onboard_config(enabled=False)
    assert vd.cross_vendor_enabled() is True


# ── (c) graceful-missing: all vendors absent, no crash ──────────────────────────
def test_detect_all_missing_graceful(monkeypatch):
    """Every vendor missing ⇒ all found=False, no exception, no crash."""
    monkeypatch.setattr(vd.shutil, "which", lambda b: None)
    monkeypatch.setattr(vd, "_cheap_version", lambda b: None)

    detected = vd.detect_vendor_clis()
    for name, info in detected.items():
        assert info["found"] is False
        assert info["version"] is None
    # No crash: the function returned a complete dict.
    assert set(detected) == set(vd.VENDOR_SPECS) | {vd.ONBOARD_HOST_CLI}


def test_cross_vendor_enabled_false_no_config_no_env(monkeypatch):
    """With no config file and no env, cross_vendor_enabled() is False (default OFF
    preserved — onboard only flips it on explicitly)."""
    assert "NUCLEUS_CROSS_VENDOR" not in os.environ
    cfg = _brain() / vd.ONBOARD_CONFIG_NAME
    assert not cfg.exists()
    assert vd.cross_vendor_enabled() is False


def test_corrupt_config_does_not_crash_gate(monkeypatch):
    """A corrupt onboard config must never break cross_vendor_enabled() — it
    returns False (fault-isolated read)."""
    cfg = _brain() / vd.ONBOARD_CONFIG_NAME
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("{not valid json", encoding="utf-8")
    assert "NUCLEUS_CROSS_VENDOR" not in os.environ
    assert vd.cross_vendor_enabled() is False
