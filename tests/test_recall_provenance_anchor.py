"""A11 (recall provenance anchoring) forge-corpus regression tests.

HANDOFF_BACKLOG.md §A11: recall's read-freshness facet (mtime+rowcount in
``recall_cmd.py::_ensure_populated``) is already Regime-1-anchored — left
untouched here. This closes the SEPARATE hole: the provenance / role-tag on a
record written through ``Store.append`` (and therefore the ``remember`` /
``write_activity`` MCP surfaces) was caller-controlled, and the ``signature``
slot on every wedge history record was hardcoded ``None``. Mirrors A3's
engram-insert anchoring (``runtime/memory_pipeline.py``) for the wedge
``history.jsonl`` write path. Flag: ``NUCLEUS_RECALL_PROVENANCE_ANCHOR``
(default OFF, byte-identical when off).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nucleus_wedge.store import Store, verify_record


@pytest.fixture
def brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    b = tmp_path / ".brain"
    (b / "engrams").mkdir(parents=True)
    (b / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False)
    return b


def _history_records(brain: Path) -> list[dict]:
    text = (brain / "engrams" / "history.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def _record(
    key: str,
    value: str,
    *,
    context: str = "note",
    source_agent: str = "nucleus-wedge",
    signature: str | None = None,
    timestamp: str = "2026-07-12T10:00:00+00:00",
) -> dict:
    return {
        "key": key,
        "op_type": "ADD",
        "timestamp": timestamp,
        "snapshot": {
            "key": key,
            "value": value,
            "context": context,
            "intensity": 5,
            "version": 1,
            "source_agent": source_agent,
            "op_type": "ADD",
            "timestamp": timestamp,
            "deleted": False,
            "signature": signature,
        },
    }


def _append_raw(brain: Path, record: dict) -> None:
    with (brain / "engrams" / "history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


class TestRecallProvenanceAnchorWrite:
    """Write-path (Store.append): server-stamping + signing."""

    def test_flag_off_is_byte_identical_to_legacy(self, brain, monkeypatch):
        monkeypatch.delenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", raising=False)
        store = Store(brain_path=brain)
        store.append(
            "legacy note",
            kind="note",
            tags=["role:main"],
            source_agent="attacker-claimed-role",
        )
        recs = _history_records(brain)
        assert len(recs) == 1
        snap = recs[0]["snapshot"]
        # Legacy shape preserved exactly: caller-asserted values pass through
        # unverified, signature slot stays dead.
        assert snap["source_agent"] == "attacker-claimed-role"
        assert snap["context"] == "note [#role:coordinator]"
        assert snap["signature"] is None
        assert verify_record(snap) is False  # never anchored when off

    def test_flag_on_server_stamps_role_and_source_ignoring_caller(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", "1")
        monkeypatch.setenv("NUCLEUS_SESSION_ROLE", "main")  # simulate a real session
        store = Store(brain_path=brain)
        store.append(
            "anchored note",
            kind="note",
            tags=["role:peer"],  # caller lies: claims "peer"
            source_agent="attacker-claimed-role",
        )
        recs = _history_records(brain)
        snap = recs[0]["snapshot"]
        # Server derivation wins — caller's asserted role/source are ignored.
        assert snap["source_agent"] == "coordinator"  # normalized from "main"
        assert snap["context"] == "note [#role:coordinator]"
        assert snap["signature"]  # non-empty, non-None
        assert verify_record(snap, brain) is True

    def test_forged_role_tag_fails_read_verify(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", "1")
        monkeypatch.setenv("NUCLEUS_SESSION_ROLE", "main")
        store = Store(brain_path=brain)
        store.append("real content", kind="note", tags=["role:main"])
        real = _history_records(brain)[0]["snapshot"]
        assert verify_record(real, brain) is True

        # Forge: mutate the role tag / source_agent post-signing, keep the
        # (now stale) signature.
        forged = dict(real)
        forged["source_agent"] = "forged-role"
        forged["context"] = "note [#role:forged-role]"
        assert verify_record(forged, brain) is False


class TestRecallProvenanceAnchorRead:
    """Read-path (memories.py::_project_row -> recall): a signature-bearing but
    tampered/forged row is excluded from the recall index when the flag is on;
    legacy unsigned rows still pass through unchanged either way."""

    @staticmethod
    def _rebuild_and_query(brain: Path) -> list[dict]:
        from nucleus_wedge.memories import build_memories_index
        from nucleus_wedge.recall_cmd import _do_recall_query

        build_memories_index(brain)
        return _do_recall_query(
            query="",
            limit=10,
            kind=None,
            tags=None,
            since=None,
            source_filter=None,
            brain_path_arg=str(brain),
        )

    def test_flag_on_genuine_signed_row_is_recalled(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", "1")
        store = Store(brain_path=brain)
        store.append("genuine signed content", kind="note", tags=["role:main"])

        results = self._rebuild_and_query(brain)
        assert [r["text"] for r in results] == ["genuine signed content"]

    def test_flag_on_spliced_forged_signature_is_excluded(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", "1")
        store = Store(brain_path=brain)
        store.append("genuine signed content", kind="note", tags=["role:main"])

        # Forge: splice a record directly into history.jsonl, bypassing
        # Store.append entirely (the realistic attack — no access to the
        # server HMAC secret), claiming a trusted role with a guessed sig.
        _append_raw(
            brain,
            _record(
                "forged_key",
                "FORGED impersonation content",
                context="note [#role:main]",
                source_agent="main",
                signature="0" * 32,
            ),
        )

        results = self._rebuild_and_query(brain)
        texts = [r["text"] for r in results]
        assert "genuine signed content" in texts
        assert "FORGED impersonation content" not in texts

    def test_flag_off_spliced_forged_signature_still_recalled(self, brain, monkeypatch):
        """Demonstrates the hole this backlog item closes: with the flag off,
        the exact same splice IS recalled unchanged — proving the fix in the
        prior test is load-bearing, not incidental."""
        monkeypatch.delenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", raising=False)
        store = Store(brain_path=brain)
        store.append("genuine content", kind="note", tags=["role:main"])
        _append_raw(
            brain,
            _record(
                "forged_key",
                "FORGED impersonation content",
                context="note [#role:main]",
                source_agent="main",
                signature="0" * 32,
            ),
        )

        results = self._rebuild_and_query(brain)
        texts = [r["text"] for r in results]
        assert "FORGED impersonation content" in texts  # the pre-A11 hole

    def test_flag_on_unsigned_legacy_row_still_recalled(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RECALL_PROVENANCE_ANCHOR", "1")
        _append_raw(
            brain,
            _record(
                "legacy_key",
                "legacy unsigned content",
                context="note [#role:main]",
                signature=None,
            ),
        )

        results = self._rebuild_and_query(brain)
        assert "legacy unsigned content" in [r["text"] for r in results]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
