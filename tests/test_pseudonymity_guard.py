"""Tests for v0.3.0 — runtime.pseudonymity_guard.

Per cc-peer 2026-06-09T11:55Z SIGNOFF (Q5 CONCUR-WITH-CORRECTION):
fresh module since none existed in mcp-server-nucleus/src/.

Coverage:
- Generic pattern set: paths, bearers, OAuth tokens, cookies
- Operator config file load: present, absent, malformed
- Default-safe posture when config absent
- Empty / None input handling
- reload_patterns refresh behavior
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import pseudonymity_guard as pg


@pytest.fixture(autouse=True)
def _reload_clean(tmp_path, monkeypatch):
    """Force pattern reload from an absent path so tests start with
    generic-only patterns. Tests that want operator patterns reload
    explicitly."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH",
                        tmp_path / ".tb" / "pseudonymity_patterns.json")
    pg.reload_patterns()
    yield


# ── Generic patterns ──────────────────────────────────────────────────


def test_generic_user_path_scrubbed():
    """/Users/<name>/ → /Users/OPERATOR/"""
    text = "see file at /Users/somebody/projects/x.py and /Users/another_user/y.txt"
    out = pg.scrub_pseudonymity(text)
    assert "/Users/OPERATOR/" in out
    assert "/Users/somebody/" not in out
    assert "/Users/another_user/" not in out


def test_generic_home_path_scrubbed():
    text = "logs at /home/admin/var/log/app.log"
    out = pg.scrub_pseudonymity(text)
    assert "/home/OPERATOR/" in out
    assert "/home/admin/" not in out


def test_bearer_token_scrubbed():
    text = "Authorization: Bearer abcdef0123456789ABCDEF"
    out = pg.scrub_pseudonymity(text)
    assert "Bearer SCRUBBED" in out
    assert "abcdef0123456789ABCDEF" not in out


def test_oauth_access_token_scrubbed():
    text = "got token sk-ant-oat01-AbCdEfGh-12345 to use"
    out = pg.scrub_pseudonymity(text)
    assert "sk-ant-oat01-SCRUBBED" in out
    assert "AbCdEfGh-12345" not in out


def test_oauth_refresh_token_scrubbed():
    text = "refresh sk-ant-ort01-RefreshTokenXYZ"
    out = pg.scrub_pseudonymity(text)
    assert "sk-ant-ort01-SCRUBBED" in out
    assert "RefreshTokenXYZ" not in out


def test_session_cookie_scrubbed():
    text = "Cookie: sessionKey=secretSessionABC123; other=value"
    out = pg.scrub_pseudonymity(text)
    assert "sessionKey=SCRUBBED" in out
    assert "secretSessionABC123" not in out


def test_cf_clearance_scrubbed():
    text = "Cookie: cf_clearance=cf-secret-clearance-token-XYZ"
    out = pg.scrub_pseudonymity(text)
    assert "cf_clearance=SCRUBBED" in out


# ── Operator config file load ─────────────────────────────────────────


def test_operator_config_absent_uses_generic_only(tmp_path, monkeypatch):
    """Missing config file → generic patterns only (no raise)."""
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH",
                        tmp_path / "absent" / "pseudonymity_patterns.json")
    count = pg.reload_patterns()
    assert count == len(pg._DEFAULT_GENERIC_PATTERNS)


def test_operator_config_extends_patterns(tmp_path, monkeypatch):
    """Operator config adds additional patterns."""
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps([
        {"pattern": r"OperatorIdentity\d+", "replacement": "OPERATOR_ID"},
        {"pattern": r"super-secret-handle", "replacement": "HANDLE"},
    ]))
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    count = pg.reload_patterns()
    assert count == len(pg._DEFAULT_GENERIC_PATTERNS) + 2

    text = "user OperatorIdentity42 and super-secret-handle are scrubbed"
    out = pg.scrub_pseudonymity(text)
    assert "OPERATOR_ID" in out
    assert "HANDLE" in out
    assert "OperatorIdentity42" not in out
    assert "super-secret-handle" not in out


def test_operator_config_invalid_json_falls_back_to_generic(tmp_path, monkeypatch, caplog):
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("not-json{")
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    caplog.set_level(logging.WARNING, logger="nucleus.pseudonymity_guard")
    count = pg.reload_patterns()
    assert count == len(pg._DEFAULT_GENERIC_PATTERNS)
    # Warn emitted but no crash
    assert any("operator config" in r.getMessage() for r in caplog.records)


def test_operator_config_non_array_falls_back_to_generic(tmp_path, monkeypatch):
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"not": "an array"}))
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    count = pg.reload_patterns()
    assert count == len(pg._DEFAULT_GENERIC_PATTERNS)


def test_operator_invalid_regex_skipped_with_warn(tmp_path, monkeypatch, caplog):
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps([
        {"pattern": "[unclosed", "replacement": "X"},
        {"pattern": "valid_pattern", "replacement": "VALID"},
    ]))
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    caplog.set_level(logging.WARNING, logger="nucleus.pseudonymity_guard")
    count = pg.reload_patterns()
    # Generic + 1 valid operator pattern
    assert count == len(pg._DEFAULT_GENERIC_PATTERNS) + 1


def test_operator_entry_missing_pattern_skipped(tmp_path, monkeypatch):
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps([
        {"replacement": "X"},  # no pattern key
        "not a dict",          # entirely wrong shape
        {"pattern": 42, "replacement": "X"},  # non-string pattern
        {"pattern": "valid", "replacement": "VALID"},
    ]))
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    count = pg.reload_patterns()
    assert count == len(pg._DEFAULT_GENERIC_PATTERNS) + 1


def test_operator_entry_default_replacement_SCRUBBED(tmp_path, monkeypatch):
    """Operator omits replacement → defaults to SCRUBBED."""
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps([
        {"pattern": "MyIdentity"},
    ]))
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    pg.reload_patterns()
    out = pg.scrub_pseudonymity("see MyIdentity here")
    assert "MyIdentity" not in out
    assert "SCRUBBED" in out


# ── Defensive input handling ──────────────────────────────────────────


def test_empty_string_returns_empty():
    assert pg.scrub_pseudonymity("") == ""


def test_none_returns_empty_string():
    assert pg.scrub_pseudonymity(None) == ""


def test_no_matches_returns_original_text():
    text = "nothing to scrub here just plain text"
    assert pg.scrub_pseudonymity(text) == text


# ── Pattern set is NOT logged ─────────────────────────────────────────


def test_invalid_pattern_logs_error_class_not_pattern(tmp_path, monkeypatch, caplog):
    cfg = tmp_path / ".tb" / "pseudonymity_patterns.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    SENSITIVE_PATTERN = "[unclosed-sensitive-pattern-content"
    cfg.write_text(json.dumps([
        {"pattern": SENSITIVE_PATTERN, "replacement": "X"},
    ]))
    monkeypatch.setattr(pg, "_OPERATOR_CONFIG_PATH", cfg)
    caplog.set_level(logging.DEBUG, logger="nucleus.pseudonymity_guard")
    pg.reload_patterns()
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SENSITIVE_PATTERN not in all_text


def test_all_exported():
    assert set(pg.__all__) == {"scrub_pseudonymity", "reload_patterns"}
