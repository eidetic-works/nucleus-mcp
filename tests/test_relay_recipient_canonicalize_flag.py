"""Tests for flag-gated recipient canonicalization in relay_post().

Background: sender is canonicalized unconditionally at write time
(`sender = resolve_canonical_inbox_name(sender)` in relay/core.py), but
recipient `to` was only sanitized/coerced (_sanitize_recipient,
_coerce_legacy_bucket_target, _coerce_provider_to_role) and never run
through the canonical role->inbox-dir map before `_get_relay_dir(to, ...)`
resolves the write directory. That gap meant to="peer" landed in the bare
`.brain/relay/peer/` bucket instead of the canonical
`.brain/relay/claude_code_peer/` that watchers actually subscribe to (same
class of bug for "tb" -> cc_tb and "ops" -> claude_code_operator_assistant).

`NUCLEUS_RELAY_CANONICALIZE_RECIPIENT` (default OFF) gates the fix. This
module proves both states explicitly: flag OFF preserves the exact legacy
bucket-naming behavior (byte-for-byte backward compatible); flag ON routes
`to` through `resolve_canonical_inbox_name()` before the directory is
resolved. Mirrors the end-to-end `to=` coercion test shape of
test_relay_legacy_bucket_intercept.py.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.relay_ops import relay_post


@pytest.fixture(autouse=True)
def _isolated_brain(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_INFER_SENDER", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_STRICT", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_CANONICALIZE_RECIPIENT", raising=False)


# ── Flag OFF (default): exact current behavior preserved ─────────────

class TestFlagOffPreservesLegacyBehavior:
    """Flag unset/OFF is the default; relay_post(to="peer", ...) must still
    write into the bare `peer/` bucket — byte-for-byte backward compatible."""

    def test_flag_unset_peer_lands_in_bare_bucket(self, tmp_path):
        result = relay_post(
            to="peer",
            subject="flag-off regression",
            body=json.dumps({"note": "bare bucket preserved"}),
            sender="cowork",
        )
        assert result["sent"] is True
        assert result["to"] == "peer"
        bare_dir = tmp_path / "relay" / "peer"
        assert any(bare_dir.glob("*.json")), (
            "flag OFF must still write to the bare peer/ bucket"
        )
        canonical_dir = tmp_path / "relay" / "claude_code_peer"
        assert not canonical_dir.exists() or not any(canonical_dir.glob("*.json")), (
            "flag OFF must NOT write to the canonical claude_code_peer/ bucket"
        )

    def test_flag_explicitly_off_peer_lands_in_bare_bucket(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_CANONICALIZE_RECIPIENT", "0")
        result = relay_post(
            to="peer",
            subject="flag-explicitly-off regression",
            body="{}",
            sender="cowork",
        )
        assert result["sent"] is True
        assert result["to"] == "peer"
        bare_dir = tmp_path / "relay" / "peer"
        assert any(bare_dir.glob("*.json"))


# ── Flag ON: recipient routed through the canonical map ──────────────

class TestFlagOnCanonicalizesRecipient:
    """Flag ON: relay_post(to=..., ...) routes `to` through
    resolve_canonical_inbox_name() before the write directory is resolved."""

    def test_flag_on_peer_lands_in_canonical_bucket(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_CANONICALIZE_RECIPIENT", "1")
        result = relay_post(
            to="peer",
            subject="flag-on canonicalize",
            body=json.dumps({"note": "canonical bucket routed"}),
            sender="cowork",
        )
        assert result["sent"] is True
        assert result["to"] == "claude_code_peer"
        canonical_dir = tmp_path / "relay" / "claude_code_peer"
        assert any(canonical_dir.glob("*.json")), (
            "flag ON must write to the canonical claude_code_peer/ bucket"
        )
        bare_dir = tmp_path / "relay" / "peer"
        assert not bare_dir.exists() or not any(bare_dir.glob("*.json")), (
            "flag ON must NOT write to the bare peer/ bucket"
        )

    def test_flag_on_tb_lands_in_cc_tb_bucket(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_CANONICALIZE_RECIPIENT", "1")
        result = relay_post(
            to="tb",
            subject="flag-on canonicalize tb",
            body="{}",
            sender="cowork",
        )
        assert result["sent"] is True
        assert result["to"] == "cc_tb"
        canonical_dir = tmp_path / "relay" / "cc_tb"
        assert any(canonical_dir.glob("*.json")), (
            "flag ON must write to the canonical cc_tb/ bucket"
        )
        bare_dir = tmp_path / "relay" / "tb"
        assert not bare_dir.exists() or not any(bare_dir.glob("*.json")), (
            "flag ON must NOT write to the bare tb/ bucket"
        )

    def test_flag_on_ops_lands_in_operator_assistant_bucket(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_CANONICALIZE_RECIPIENT", "1")
        result = relay_post(
            to="ops",
            subject="flag-on canonicalize ops",
            body="{}",
            sender="cowork",
        )
        assert result["sent"] is True
        assert result["to"] == "claude_code_operator_assistant"
        canonical_dir = tmp_path / "relay" / "claude_code_operator_assistant"
        assert any(canonical_dir.glob("*.json")), (
            "flag ON must write to the canonical claude_code_operator_assistant/ bucket"
        )
        bare_dir = tmp_path / "relay" / "ops"
        assert not bare_dir.exists() or not any(bare_dir.glob("*.json")), (
            "flag ON must NOT write to the bare ops/ bucket"
        )

    def test_flag_on_already_canonical_recipient_unchanged(self, tmp_path, monkeypatch):
        """Flag ON with an already-canonical `to` (e.g. claude_code_main) is a
        no-op — resolve_canonical_inbox_name is idempotent."""
        monkeypatch.setenv("NUCLEUS_RELAY_CANONICALIZE_RECIPIENT", "1")
        result = relay_post(
            to="claude_code_main",
            subject="flag-on already-canonical",
            body="{}",
            sender="cowork",
        )
        assert result["sent"] is True
        assert result["to"] == "claude_code_main"
        canonical_dir = tmp_path / "relay" / "claude_code_main"
        assert any(canonical_dir.glob("*.json"))
