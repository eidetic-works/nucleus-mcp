"""Regression tests for the 3 P0 items from Cascade's 2026-04-18 feedback.

Each test asserts the EXACT failure mode Cascade reported is now
impossible given the v1.2.0 remediations. If any of these fails on
main, we've regressed on a filed P0 — do not ship.

References:
  - .brain/handoffs/CASCADE_FEEDBACK_REMEDIATION_v1.2.0_FOR_REVIEW.md
  - .brain/handoffs/REVIEW_REPLY_FROM_CLAUDE_CODE_2026-04-18.md
  - docs/reports/cascade_feedback_2026-04-18.md (if present)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import health_sidecar as hs
from mcp_server_nucleus.runtime import hygiene
from mcp_server_nucleus.runtime import manifest
from mcp_server_nucleus.tools import _envelope


# ---------------------------------------------------------------------------
# P0 #1 — Transport health sidecar + structured errors
# Cascade report: "I got 'transport error: transport closed' with no pid,
# no recovery hint, no last_healthy_at. I could not tell the user what
# to do."
# ---------------------------------------------------------------------------


def test_p0_1_transport_closed_is_structurally_diagnosable(tmp_path):
    """The sidecar query returns a structured envelope-style error when
    the socket is absent. No bare strings. No guessing."""
    missing = tmp_path / "no-sidecar.sock"
    result = hs.query("/health", socket_path=missing, timeout=0.3)
    # Must be a structured error
    assert isinstance(result, dict)
    assert result.get("error_type") == "transport_closed"
    assert result.get("recovery_hint"), "recovery_hint must be set"
    # Must NOT be a bare 'transport closed' string
    assert not isinstance(result, str)


# ---------------------------------------------------------------------------
# P0 #2 — brain_id namespace disambiguation
# Cascade report: "Nucleus served me state from one brain as if it were
# guidance for a different project. There was no way to tell which brain
# was speaking."
# ---------------------------------------------------------------------------


def test_p0_2_envelope_echoes_brain_id_when_enabled(tmp_path, monkeypatch):
    """Every envelope carries brain_id when a manifest is loaded."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    manifest.save(brain, {"brain_id": "nucleus-primary", "brain_owner": "org/repo"})
    manifest.load(brain)  # primes envelope contextvar

    monkeypatch.setenv("NUCLEUS_ENVELOPE", "on")
    env = _envelope.wrap({"greeting": "hi"})
    assert env["brain_id"] == "nucleus-primary", (
        "Envelope must echo the manifest's brain_id — the Cascade "
        "misattribution bug required envelope to be brain-aware."
    )


def test_p0_2_manifest_is_atomic_under_race(tmp_path):
    """Concurrent writers never produce a partial manifest.yaml."""
    import threading
    import yaml

    brain = tmp_path / ".brain"
    brain.mkdir()
    manifest.save(brain, {"brain_id": "init"})
    corruptions = []

    def reader():
        for _ in range(50):
            try:
                text = manifest.manifest_path(brain).read_text()
                if text and not isinstance(yaml.safe_load(text), dict):
                    corruptions.append("non-dict")
            except Exception as e:
                corruptions.append(str(e))

    def writer(tag):
        for i in range(10):
            manifest.save(brain, {"brain_id": f"{tag}-{i}"})

    threads = [threading.Thread(target=reader)]
    threads.extend(threading.Thread(target=writer, args=(f"w{i}",)) for i in range(3))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert corruptions == []


# ---------------------------------------------------------------------------
# P0 #3 — Stale-priority garbage collection + year-bug guard
# Cascade report: "Nucleus returned 'Jan 10, 2025' as a current priority
# in April 2026. Obvious off-by-one-year data entry error served as live
# guidance."
# ---------------------------------------------------------------------------


NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)


def test_p0_3_year_bug_guard_bumps_jan_2025_to_2026():
    """The exact Cascade case: a 2025-01-10 date seen in April 2026 is
    recognized as a year-bug and normalized to 2026."""
    out = hygiene.normalize_date("2025-01-10T00:00:00Z", now=NOW)
    assert "2026-01-10" in out, (
        f"Expected year-bug guard to bump to 2026; got {out!r}"
    )


def test_p0_3_stale_priority_is_archived_not_served(tmp_path):
    """Stale priorities must be filterable out and archivable — they
    must not be returned as current guidance."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "state.json").write_text(json.dumps({
        "priorities": [
            {"id": "fresh", "updated_at": "2026-04-19T00:00:00Z"},
            {"id": "stale_jan2025", "updated_at": "2025-01-10T00:00:00Z"},
        ],
    }))
    report = hygiene.run_hygiene(brain, now=NOW)
    # Stale priority was identified + moved
    archived_ids = [a["record"]["id"] for a in report["archived"]]
    assert "stale_jan2025" in archived_ids
    assert "fresh" not in archived_ids

    # Post-state only has fresh
    new_state = json.loads((brain / "state.json").read_text())
    ids = [p["id"] for p in new_state["priorities"]]
    assert ids == ["fresh"]

    # Archive file exists under ledger/archive/YYYY-MM-DD.jsonl
    day = NOW.strftime("%Y-%m-%d")
    archive = brain / "ledger" / "archive" / f"{day}.jsonl"
    assert archive.exists()


def test_p0_3_sprint_gap_alert_emitted_when_current_sprint_orphaned(tmp_path):
    """COMPLETE sprint with no successor >7d old emits sprint_gap alert."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "state.json").write_text(json.dumps({
        "current_sprint": {
            "sprint_id": "s-42",
            "status": "COMPLETE",
            "ended_at": "2026-04-01T00:00:00Z",  # 19d ago
        },
    }))
    report = hygiene.run_hygiene(brain, now=NOW)
    assert report["sprint_gap_alert"] is not None
    alerts_file = brain / "ledger" / "alerts.jsonl"
    assert alerts_file.exists()
    entries = [json.loads(l) for l in alerts_file.read_text().splitlines()]
    assert any(e["alert_type"] == "sprint_gap" for e in entries)


# ---------------------------------------------------------------------------
# Cross-cutting: the envelope is the contract surface.
# ---------------------------------------------------------------------------


def test_cross_cut_envelope_schema_is_pinned():
    """The envelope schema artifact is shipped so consumers can pin."""
    from mcp_server_nucleus import schemas as schemas_pkg
    schema = schemas_pkg.load_schema("envelope")
    assert schema["$id"].endswith("envelope.schema.json")
    assert "schema_version" in schema["properties"]
    # Current pinned version
    assert schema["properties"]["schema_version"]["enum"] == ["2"]
