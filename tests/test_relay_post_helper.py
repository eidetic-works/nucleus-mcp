"""Tests for v0.3.x Plan B — sessions._relay_post_helper.

Per cc-peer 2026-06-09T18:00Z locked contract Q4 (6 mitigations) + Q5
(8-case body shape floor).

Coverage:
- Mitigation (a): recipient ENUM validated at autonomous_wake layer
  (covered in test_autonomous_wake.py); helper accepts what reaches it
- Mitigation (b): subject prefix [AUTONOMOUS] forced when missing
- Mitigation (c): sender_role LOCKED at call site — NOT from block_input
- Mitigation (d): body length cap 4096
- Mitigation (e): rate limit 20/hr disk-persistent
- Mitigation (f): audit log .brain/ledger/autonomous_relay_posts.jsonl
  with body_hash + NO body content
- Q5 body shape: 8-case floor (str / dict / list / nested / unicode /
  None / unsupported / oversize)
- Bearer file: lazy check at call time; warn + skip if absent
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.sessions import _relay_post_helper as rph


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(rph, "_RATE_LIMIT_DIR", tmp_path / ".tb")
    yield


def _write_bearer(tmp_path: Path, role: str = "cc_tb", value: str = "STUB-OCI"):
    p = tmp_path / ".tb" / f"relay_token_{role}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(value)
    return p


def _mock_post_200(monkeypatch):
    """Patch urllib.request.urlopen + curl_cffi to return 200.

    The relay helper tries ``curl_cffi.requests.post`` first (if installed)
    and falls back to ``urllib.request.urlopen``. We must patch BOTH so the
    mock works regardless of which transport is active.
    """
    fake = MagicMock()
    fake.status = 200
    fake.status_code = 200
    fake.__enter__ = lambda self: self
    fake.__exit__ = lambda *a: None
    # Patch urllib path (stdlib fallback)
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **kw: fake,
    )
    # Patch curl_cffi path (primary transport when installed)
    fake_curl = MagicMock()
    fake_curl.status_code = 200
    try:
        import curl_cffi.requests as _cr
        monkeypatch.setattr(_cr, "post", lambda *a, **kw: fake_curl)
    except ImportError:
        pass
    return fake


# ── Body shape (Q5 8-case test floor) ──────────────────────────────────


def test_body_string_passthrough():
    assert rph._coerce_body_to_string("hello") == "hello"


def test_body_dict_json_dumps_ensure_ascii_false():
    out = rph._coerce_body_to_string({"a": "café", "b": 1})
    assert out is not None
    parsed = json.loads(out)
    assert parsed == {"a": "café", "b": 1}
    # ensure_ascii=False means no \u escapes
    assert "café" in out


def test_body_list_json_dumps():
    out = rph._coerce_body_to_string([1, 2, 3])
    assert out == "[1, 2, 3]"


def test_body_nested_dict_with_quotes_escapes_correctly():
    out = rph._coerce_body_to_string({"x": 'has "nested" quotes'})
    parsed = json.loads(out)
    assert parsed == {"x": 'has "nested" quotes'}


def test_body_unicode_preserved_no_u_escape():
    out = rph._coerce_body_to_string({"msg": "🚀 ok"})
    # Unicode preserved (no \uXXXX escaping)
    assert "🚀" in out


def test_body_None_skipped_with_warning(caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.relay_post_helper")
    assert rph._coerce_body_to_string(None) is None
    assert any("body None" in r.getMessage() for r in caplog.records)


def test_body_unsupported_type_int_skipped_with_warning(caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.relay_post_helper")
    assert rph._coerce_body_to_string(42) is None
    assert any("unsupported type" in r.getMessage() for r in caplog.records)


def test_body_exceeds_length_cap_truncated_with_audit_flag():
    long_body = "A" * (rph._BODY_LENGTH_CAP + 100)
    truncated, flag = rph._cap_body_length(long_body)
    assert len(truncated) == rph._BODY_LENGTH_CAP
    assert flag is True


def test_body_within_cap_not_truncated():
    short_body = "A" * 100
    out, flag = rph._cap_body_length(short_body)
    assert out == short_body
    assert flag is False


# ── Mitigation (b): subject prefix [AUTONOMOUS] ────────────────────────


def test_subject_prefix_prepended_when_missing():
    out = rph._force_subject_prefix("Hello")
    assert out == "[AUTONOMOUS] Hello"


def test_subject_prefix_preserved_when_present():
    out = rph._force_subject_prefix("[AUTONOMOUS] Already here")
    assert out == "[AUTONOMOUS] Already here"


def test_subject_prefix_empty_subject_becomes_bare_prefix():
    out = rph._force_subject_prefix("")
    assert out == "[AUTONOMOUS]"


def test_subject_prefix_non_string_treated_as_empty():
    out = rph._force_subject_prefix(None)
    assert out == "[AUTONOMOUS]"


# ── Mitigation (e): rate limit 20/hr ────────────────────────────────────


def test_rate_limit_under_cap_returns_true(tmp_path):
    for _ in range(5):
        assert rph._check_and_record_rate("cc_tb") is True


def test_rate_limit_at_cap_returns_false(tmp_path):
    """Plant 20 timestamps in the last hour; next call → False."""
    rph._RATE_LIMIT_DIR.mkdir(parents=True, exist_ok=True)
    now = time.time()
    state = [now - 100 + i for i in range(20)]  # 20 in last hour
    (rph._RATE_LIMIT_DIR / "relay_post_rate_cc_tb.json").write_text(
        json.dumps(state),
    )
    assert rph._check_and_record_rate("cc_tb") is False


def test_rate_limit_prunes_old_timestamps(tmp_path):
    """Timestamps older than window dropped on next check."""
    rph._RATE_LIMIT_DIR.mkdir(parents=True, exist_ok=True)
    now = time.time()
    # 20 stale + 1 fresh
    state = [now - 5000 for _ in range(20)] + [now - 10]
    (rph._RATE_LIMIT_DIR / "relay_post_rate_cc_tb.json").write_text(
        json.dumps(state),
    )
    # Stale ones dropped → under cap → True
    assert rph._check_and_record_rate("cc_tb") is True


def test_rate_limit_file_atomic_via_tmp_replace(tmp_path, monkeypatch):
    seen_tmp = []
    orig_replace = Path.replace

    def _trace(self, target):
        if str(self).endswith(".tmp"):
            seen_tmp.append(str(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _trace)
    rph._check_and_record_rate("cc_tb")
    assert any(".tmp" in s for s in seen_tmp)


# ── post_nucleus_relay_block — happy path + mitigation enforcement ──────


def test_post_nucleus_relay_block_happy_path(tmp_path, monkeypatch):
    _write_bearer(tmp_path, "cc_tb")
    _mock_post_200(monkeypatch)
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "TEST",
            "body": "hello",
        },
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    assert result is True
    # Audit log written
    audit = brain / "ledger" / "autonomous_relay_posts.jsonl"
    assert audit.exists()
    entry = json.loads(audit.read_text().strip())
    assert entry["sender_role"] == "cc_tb"
    assert entry["recipient_role"] == "operator_assistant"
    assert entry["posted"] is True


def test_sender_role_locked_LLM_input_ignored(tmp_path, monkeypatch):
    """Mitigation (c): block_input.sender / from_role / etc. NOT used."""
    _write_bearer(tmp_path, "cc_tb")
    _mock_post_200(monkeypatch)
    brain = tmp_path / ".brain"
    rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "TEST",
            "body": "hello",
            "sender": "FAKE_ROLE",  # LLM-injected — must be ignored
            "from_role": "cc_main",  # ditto
        },
        sender_role="cc_tb",  # LOCKED — this is what audit records
        block_id="t1",
        brain_root=brain,
    )
    audit = brain / "ledger" / "autonomous_relay_posts.jsonl"
    entry = json.loads(audit.read_text().strip())
    assert entry["sender_role"] == "cc_tb"  # NOT FAKE_ROLE


def test_subject_prefix_forced_in_audit(tmp_path, monkeypatch):
    _write_bearer(tmp_path)
    _mock_post_200(monkeypatch)
    brain = tmp_path / ".brain"
    rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "no prefix yet",
            "body": "x",
        },
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    entry = json.loads((brain / "ledger" / "autonomous_relay_posts.jsonl").read_text().strip())
    assert entry["subject_first_80"].startswith("[AUTONOMOUS] ")


def test_bearer_missing_skips_post_and_audits(tmp_path):
    """Lazy check (Q3): bearer file absent → skip POST + audit reason."""
    brain = tmp_path / ".brain"
    # No bearer file written
    result = rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "TEST",
            "body": "x",
        },
        sender_role="ghost_role",
        block_id="t1",
        brain_root=brain,
    )
    assert result is False
    entry = json.loads((brain / "ledger" / "autonomous_relay_posts.jsonl").read_text().strip())
    assert entry["error_class"] == "bearer_missing"
    assert entry["posted"] is False


def test_body_None_audits_skip_reason(tmp_path):
    _write_bearer(tmp_path)
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "TEST",
            "body": None,
        },
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    assert result is False
    entry = json.loads((brain / "ledger" / "autonomous_relay_posts.jsonl").read_text().strip())
    assert entry["error_class"] == "body_shape_unsupported"


def test_rate_limit_exceeded_skips_post_and_audits(tmp_path):
    _write_bearer(tmp_path)
    # Plant 20 fresh timestamps to trigger rate-limit
    rph._RATE_LIMIT_DIR.mkdir(parents=True, exist_ok=True)
    now = time.time()
    (rph._RATE_LIMIT_DIR / "relay_post_rate_cc_tb.json").write_text(
        json.dumps([now - 1 for _ in range(20)]),
    )
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "TEST",
            "body": "x",
        },
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    assert result is False
    entry = json.loads((brain / "ledger" / "autonomous_relay_posts.jsonl").read_text().strip())
    assert entry["error_class"] == "rate_limit_exceeded"


def test_missing_recipient_skips(tmp_path):
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={"subject": "x", "body": "y"},
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    assert result is False


def test_missing_sender_role_skips(tmp_path):
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={"recipient": "op", "subject": "x", "body": "y"},
        sender_role="",
        block_id="t1",
        brain_root=brain,
    )
    assert result is False


def test_block_input_not_dict_skips(tmp_path):
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input="not a dict",  # type: ignore
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    assert result is False


# ── Mitigation (f): audit log content discipline ───────────────────────


def test_audit_log_never_contains_full_body_content(tmp_path, monkeypatch):
    _write_bearer(tmp_path)
    _mock_post_200(monkeypatch)
    brain = tmp_path / ".brain"
    SECRET = "operator-secret-body-must-not-leak-XYZ"
    rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "TEST",
            "body": SECRET,
        },
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    audit_text = (brain / "ledger" / "autonomous_relay_posts.jsonl").read_text()
    assert SECRET not in audit_text
    entry = json.loads(audit_text.strip())
    # body_hash present + body_chars present (NOT body itself)
    assert "body_hash" in entry
    assert entry["body_chars"] == len(SECRET)
    assert "body" not in entry  # full content NEVER in audit


def test_audit_log_body_hash_is_sha256(tmp_path, monkeypatch):
    _write_bearer(tmp_path)
    _mock_post_200(monkeypatch)
    brain = tmp_path / ".brain"
    body = "abc"
    rph.post_nucleus_relay_block(
        block_input={"recipient": "op", "subject": "s", "body": body},
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    entry = json.loads((brain / "ledger" / "autonomous_relay_posts.jsonl").read_text().strip())
    expected_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert entry["body_hash"] == expected_hash


# ── Bearer pseudonymity ────────────────────────────────────────────────


def test_bearer_value_never_logged(tmp_path, caplog, monkeypatch):
    import logging
    _write_bearer(tmp_path, "cc_tb", value="STUB-OCI-SECRET-do-not-leak-xyz")
    _mock_post_200(monkeypatch)
    caplog.set_level(logging.DEBUG, logger="nucleus.relay_post_helper")
    brain = tmp_path / ".brain"
    rph.post_nucleus_relay_block(
        block_input={"recipient": "op", "subject": "s", "body": "b"},
        sender_role="cc_tb",
        block_id="t1",
        brain_root=brain,
    )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert "STUB-OCI-SECRET" not in all_text


# ── Sender field: passed verbatim, NO 'claude_code_' prefix ────────────
# Empirical proof (op-assistant 2026-06-09T22:30Z LOOP-CLOSED smoke):
# OCI endpoint requires body.sender to match token-owner exactly. Token
# owners are provisioned by operator with whatever string the OCI side
# accepts; helper must pass sender_role verbatim and not invent a prefix.


def _capture_post_body(monkeypatch):
    """Patch both transports to capture the JSON body posted."""
    captured: dict = {}

    class _FakeResp:
        status = 200
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    def _fake_urlopen(req, *a, **kw):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["url"] = req.full_url
        return _FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    return captured


def test_sender_field_unprefixed_for_bespoq_cowork(tmp_path, monkeypatch):
    """bespoq_cowork → body.sender='bespoq_cowork' (not claude_code_bespoq_cowork).

    OCI test_a (op-assistant 22:30Z): prefixed form returned 403
    sender_mismatch. Helper must pass sender_role verbatim.
    """
    _write_bearer(tmp_path, role="bespoq_cowork")
    captured = _capture_post_body(monkeypatch)
    monkeypatch.setattr(rph, "_OCI_RELAY_BASE", "https://stub.invalid/relay")
    # Force urllib path (skip curl_cffi import)
    monkeypatch.setitem(__import__("sys").modules, "curl_cffi", None)
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={
            "recipient": "operator_assistant",
            "subject": "LOOP-CLOSED-ACK",
            "body": "ACK",
        },
        sender_role="bespoq_cowork",
        block_id="t1",
        brain_root=brain,
    )
    assert result is True
    assert captured["body"]["sender"] == "bespoq_cowork"
    assert not captured["body"]["sender"].startswith("claude_code_")


def test_sender_field_unprefixed_for_cc_fleet_role(tmp_path, monkeypatch):
    """main → body.sender='main' (operator provisions token owner per OCI naming).

    Helper does not invent prefixes. If OCI wants 'claude_code_main', operator
    provisions sender_role='claude_code_main'; if OCI wants 'main', sender_role='main'.
    Helper passes verbatim.
    """
    _write_bearer(tmp_path, role="main")
    captured = _capture_post_body(monkeypatch)
    monkeypatch.setattr(rph, "_OCI_RELAY_BASE", "https://stub.invalid/relay")
    monkeypatch.setitem(__import__("sys").modules, "curl_cffi", None)
    brain = tmp_path / ".brain"
    result = rph.post_nucleus_relay_block(
        block_input={"recipient": "operator_assistant", "subject": "s", "body": "b"},
        sender_role="main",
        block_id="t1",
        brain_root=brain,
    )
    assert result is True
    assert captured["body"]["sender"] == "main"


# ── Exports ────────────────────────────────────────────────────────────


def test_all_exported():
    assert set(rph.__all__) == {"RelayPostError", "post_nucleus_relay_block"}
