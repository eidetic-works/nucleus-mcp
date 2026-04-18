"""Tests for the relay_post artifact-ref gate.

The gate is opt-in: default is permissive (backward-compatible). Setting
NUCLEUS_RELAY_STRICT=1 rejects relays whose body.artifact_refs contains only
relay_ids (relay-of-relay = convergence theater).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.relay_ops import relay_post, _is_shipped_artifact


@pytest.fixture(autouse=True)
def _isolated_brain(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_STRICT", raising=False)


def _post(body_obj, subject="t"):
    body = json.dumps(body_obj) if not isinstance(body_obj, str) else body_obj
    return relay_post(to="cowork", subject=subject, body=body, sender="claude_code")


class TestIsShippedArtifact:
    def test_relay_id_rejected(self):
        assert not _is_shipped_artifact("relay_20260415_011553_a8fbd81b")

    def test_relay_id_with_trailing_comment_rejected(self):
        assert not _is_shipped_artifact("relay_20260415_011553_a8fbd81b (posture-lock proposal)")

    def test_path_accepted(self):
        assert _is_shipped_artifact("src/mcp_server_nucleus/runtime/relay_ops.py:185")

    def test_commit_sha_accepted(self):
        assert _is_shipped_artifact("eaf5bce3")

    def test_pr_accepted(self):
        assert _is_shipped_artifact("PR #51")

    def test_empty_rejected(self):
        assert not _is_shipped_artifact("")
        assert not _is_shipped_artifact("   ")


class TestDefaultPermissive:
    """Default behavior (no env var): backward-compatible — all bodies pass."""

    def test_relay_id_only_passes_by_default(self):
        result = _post({"artifact_refs": ["relay_20260415_011553_a8fbd81b"]})
        assert result["sent"] is True

    def test_empty_refs_passes_by_default(self):
        result = _post({"artifact_refs": []})
        assert result["sent"] is True

    def test_prose_body_passes_by_default(self):
        result = _post("plain prose, no JSON")
        assert result["sent"] is True

    def test_missing_refs_passes_by_default(self):
        result = _post({"summary": "no refs"})
        assert result["sent"] is True


class TestStrictMode:
    """NUCLEUS_RELAY_STRICT=1 activates the gate."""

    @pytest.fixture(autouse=True)
    def _strict(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_STRICT", "1")

    def test_rejects_relay_id_only(self):
        result = _post({"artifact_refs": ["relay_20260415_011553_a8fbd81b"]})
        assert result["sent"] is False
        assert result["error"] == "gate_rejected"

    def test_rejects_multiple_relay_ids(self):
        result = _post({"artifact_refs": [
            "relay_20260415_011553_a8fbd81b",
            "relay_20260415_012743_9e442f7d",
        ]})
        assert result["sent"] is False

    def test_rejects_empty_artifact_refs(self):
        result = _post({"artifact_refs": []})
        assert result["sent"] is False

    def test_rejects_missing_artifact_refs(self):
        result = _post({"summary": "no refs here"})
        assert result["sent"] is False

    def test_rejects_non_json_body(self):
        result = _post("just some prose, not JSON")
        assert result["sent"] is False

    def test_accepts_file_path_ref(self):
        result = _post({"artifact_refs": ["src/mcp_server_nucleus/runtime/relay_ops.py"]})
        assert result["sent"] is True

    def test_accepts_commit_sha_ref(self):
        result = _post({"artifact_refs": ["eaf5bce3"]})
        assert result["sent"] is True

    def test_accepts_pr_ref(self):
        result = _post({"artifact_refs": ["PR #51"]})
        assert result["sent"] is True

    def test_accepts_mixed_when_at_least_one_shipped(self):
        result = _post({"artifact_refs": [
            "relay_20260415_011553_a8fbd81b",
            "src/foo.py:10",
        ]})
        assert result["sent"] is True

    def test_rejected_response_includes_to_and_subject(self):
        result = _post({"artifact_refs": []}, subject="my-subject")
        assert result["to"] == "cowork"
        assert result["subject"] == "my-subject"
        assert "NUCLEUS_RELAY_STRICT" in result["reason"]

    def test_relay_of_relay_theater_rejected(self):
        """Pin the intended behavior on real-world theater refs.

        Of the 6 theater relays in the 2026-04-15 thread, 5 cited only other
        relay_ids — these the gate blocks when STRICT=1. One (f2ef6101) cited
        NO_DRIFT.md alongside a relay_id; it would pass this gate because
        mechanical artifact-presence can't distinguish 'cites a file' from
        'is theater'. That's a known limitation, not a bug.
        """
        relay_only_refs = [
            ["relay_20260415_005844_22e2fdb9 (your posture-lock proposal)"],
            ["relay_20260415_011553_a8fbd81b"],
            ["relay_20260415_012743_9e442f7d", "relay_20260415_011553_a8fbd81b"],
            ["relay_20260415_013917_f70d3b4d"],
            ["relay_20260415_022328_f2ef6101"],
        ]
        for refs in relay_only_refs:
            result = _post({"artifact_refs": refs})
            assert result["sent"] is False, f"Gate failed to block theater refs: {refs}"
