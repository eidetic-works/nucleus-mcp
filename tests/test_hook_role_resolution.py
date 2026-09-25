"""Tests for mirror/hook.py CC_SESSION_ROLE + canonical-inbox resolution.

Per PR #3a (in-chat relay visibility) — closes the structural 0%-delivery gap
where the Python SessionStart + UserPromptSubmit hook defaulted to the bare
legacy ``claude_code/`` inbox instead of the recipient's canonical inbox.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from mcp_server_nucleus.mirror import hook


ROLE_CASES = [
    ("main", "claude_code_main"),
    ("peer", "claude_code_peer"),
    ("tb", "cc_tb"),
    ("op_assistant", "claude_code_operator_assistant"),
    ("antigravity", "antigravity"),
    ("cc_gq", "claude_code_cc_gq"),
]


def _make_brain_dirs(tmp_path):
    brain = tmp_path / ".brain"
    relay_root = brain / "relay"
    mirror = brain / "session_mirror" / "cowork_last.md"
    seen = brain / "session_mirror" / ".seen_cowork_last"
    relay_root.mkdir(parents=True)
    return brain, relay_root, mirror, seen


@pytest.mark.parametrize("role,expected_dir", ROLE_CASES)
def test_hook_resolves_role_to_canonical_inbox(role, expected_dir, monkeypatch, tmp_path, capsys):
    """Hook surfaces relays from the canonical inbox for each CC_SESSION_ROLE."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / expected_dir
    inbox.mkdir(parents=True)
    msg = inbox / "20260605T000000_test_PR3A.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": f"role={role}",
        "body": "PR #3a dogfood",
        "priority": "normal",
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", role)
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0
    assert expected_dir in out, (
        f"role={role} should surface from {expected_dir}, got: {out[:300]}"
    )
    assert f"role={role}" in out, (
        f"expected the seeded relay subject for role={role} in stdout, got: {out[:300]}"
    )


def test_hook_falls_back_to_nucleus_session_role(monkeypatch, tmp_path, capsys):
    """When CC_SESSION_ROLE is unset, NUCLEUS_SESSION_ROLE should resolve."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / "cc_tb"
    inbox.mkdir(parents=True)
    msg = inbox / "20260605T000000_fallback_test.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": "fallback via NUCLEUS_SESSION_ROLE",
        "body": "...",
    }))

    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)
    monkeypatch.setenv("NUCLEUS_SESSION_ROLE", "tb")
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "cc_tb" in out


def test_hook_default_when_no_env(monkeypatch, tmp_path, capsys):
    """No env at all → resolves to 'main' → claude_code_main inbox. No relays surfaces silent exit 0."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)

    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main([])

    out = capsys.readouterr().out
    assert rc == 0
    # No inbox exists → no relays surfaced → empty stdout.
    assert out == ""


def test_hook_explicit_recipient_arg_wins_over_env(monkeypatch, tmp_path, capsys):
    """args[1] explicit recipient takes precedence over CC_SESSION_ROLE."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / "cc_tb"
    inbox.mkdir(parents=True)
    msg = inbox / "20260605T000000_explicit.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": "explicit arg overrides env",
        "body": "...",
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", "main")  # would resolve to claude_code_main
    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart", "tb"])  # explicit arg → cc_tb

    out = capsys.readouterr().out
    assert rc == 0
    assert "cc_tb" in out
    assert "explicit arg overrides env" in out


# Edge-case tests per cc-peer hole-poke verdict (PR #475 crack 4 ACTIONABLE-FYI).
# SSOT resolve_canonical_inbox_name() does .strip().lower().replace("-", "_") at
# runtime; these tests pin that behavior at the hook boundary so future SSOT
# normalization changes can't regress silently.
EDGE_CASE_ROLE_INPUTS = [
    ("TB", "cc_tb"),                              # mixed-case
    ("  tb  ", "cc_tb"),                          # whitespace padding
    ("op-assistant", "claude_code_operator_assistant"),  # hyphen → underscore
    ("OP-ASSISTANT", "claude_code_operator_assistant"),  # mixed-case + hyphen
    ("antigravity", "antigravity"),               # bare-name canonical (already canonical input)
]


@pytest.mark.parametrize("role_input,expected_dir", EDGE_CASE_ROLE_INPUTS)
def test_hook_normalizes_edge_case_role_input(role_input, expected_dir, monkeypatch, tmp_path, capsys):
    """SSOT normalization at the hook boundary handles mixed-case + whitespace + hyphen."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / expected_dir
    inbox.mkdir(parents=True)
    msg = inbox / "20260605T000000_edge_case.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": f"input={role_input!r}",
        "body": "edge case",
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", role_input)
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0
    assert expected_dir in out, (
        f"input={role_input!r} should normalize to {expected_dir}, got: {out[:300]}"
    )


def test_hook_unknown_role_falls_through_via_or_fallback(monkeypatch, tmp_path, capsys):
    """Unknown role (not in CANONICAL_ROLE_TO_INBOX_DIR) falls through to itself.

    SSOT returns the .strip().lower().replace('-', '_') normalized form for unknown
    inputs (per resolve_canonical_inbox_name fallback to .get(key, key)). The hook's
    `or role_input` clause is structurally dead for normalized non-empty inputs but
    documents the contract; this test pins the fall-through path so a future SSOT
    change to return None for unknown roles wouldn't silently break the hook.
    """
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / "future_agent_v9"
    inbox.mkdir(parents=True)
    msg = inbox / "20260605T000000_unknown.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": "unknown-role fall-through",
        "body": "...",
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", "future_agent_v9")
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "future_agent_v9" in out
    assert "unknown-role fall-through" in out


# Regression test for PR #478 — dict body crash.
# Pre-fix: m.get("body") returned dict, `or ""` didn't fire (dict truthy),
# `[:240]` raised KeyError trying to slice a dict with a slice object.
# Post-PR-475 exposed this latent bug because the canonical inbox routing
# started surfacing real relays (which use dict bodies, per fleet convention).


def test_hook_handles_dict_body_without_crashing(monkeypatch, tmp_path, capsys):
    """All cc-fleet relays use dict bodies (structured payloads). Hook MUST NOT crash."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / "cc_tb"
    inbox.mkdir(parents=True)
    msg = inbox / "20260606T000000_dict_body_relay.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": "dict body regression test",
        "body": {
            "key_1": "value_1",
            "nested": {"a": 1, "b": 2},
            "list_field": [1, 2, 3],
        },
        "priority": "normal",
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0, "Hook must not crash on dict body"
    assert "dict body regression test" in out
    # Dict body serialized to JSON in the surfaced relay summary
    assert '"key_1":"value_1"' in out or "key_1" in out


def test_hook_handles_list_body_without_crashing(monkeypatch, tmp_path, capsys):
    """Defensive: list bodies (rare but legal JSON) must also not crash."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / "cc_tb"
    inbox.mkdir(parents=True)
    msg = inbox / "20260606T000000_list_body_relay.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": "list body regression test",
        "body": ["item_a", "item_b", "item_c"],
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    monkeypatch.delenv("NUCLEUS_RELAY_RECIPIENT", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "list body regression test" in out


def test_hook_handles_missing_body_field(monkeypatch, tmp_path, capsys):
    """Relays without a body field must not crash (defensive)."""
    brain, relay_root, mirror, seen = _make_brain_dirs(tmp_path)
    inbox = relay_root / "cc_tb"
    inbox.mkdir(parents=True)
    msg = inbox / "20260606T000000_no_body.json"
    msg.write_text(json.dumps({
        "from": "tester",
        "subject": "no body field",
    }))

    monkeypatch.setenv("CC_SESSION_ROLE", "tb")

    with patch(
        "mcp_server_nucleus.mirror.hook._brain_dirs",
        return_value=(brain, relay_root, mirror, seen),
    ):
        rc = hook.main(["SessionStart"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "no body field" in out


# CRACK 5 regression tests (agy battle-test 2026-06-06 ~06:25Z + cc-main
# inline source verification). hook._read_session_id called .get() on the
# json.loads result without isinstance(dict) guard — class-wide bug pattern
# matching PR #479's collected-relay-body crash but at the stdin-payload path.


@pytest.mark.parametrize("stdin_value", [
    "null",           # null → None
    "42",             # int
    "true",           # bool
    "\"a string\"",   # str
    "[1, 2, 3]",      # list
    "[]",             # empty list
])
def test_read_session_id_handles_non_dict_json_payloads_without_crashing(stdin_value, monkeypatch):
    """Class-wide guard: any valid JSON that isn't a dict returns None safely."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_value))
    result = hook._read_session_id()
    assert result is None, f"non-dict payload {stdin_value!r} must return None safely (not crash with AttributeError)"


def test_read_session_id_returns_session_id_from_well_formed_dict(monkeypatch):
    """Happy path still works post-guard."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id": "abc123"}'))
    result = hook._read_session_id()
    assert result == "abc123"


def test_read_session_id_returns_none_when_dict_missing_session_id(monkeypatch):
    """Dict without session_id field returns None safely."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO('{"other_field": "value"}'))
    result = hook._read_session_id()
    assert result is None


def test_read_session_id_returns_none_when_session_id_is_non_string(monkeypatch):
    """session_id field present but not string-typed returns None."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id": 42}'))
    result = hook._read_session_id()
    assert result is None
