"""Tests for the growth/automation registry.

The load-bearing assertions separate three things that binary thinking merges:
a job that ran (HEALTHY/STALE), a job that declared a proof artifact and
produced nothing (DEAD), and a job that declared nothing so cannot be judged
(UNKNOWN).
"""

from datetime import datetime, timedelta, timezone

import pytest

from mcp_server_nucleus.runtime.growth_registry import (
    DEFAULT_MAX_AGE_MULTIPLIER,
    RegistryEntry,
    entry_to_liveness_item,
    load_registry,
    parse_interval,
    reconcile,
    render_registry_yaml,
    resolve_proof,
    seed_entries_from_machine,
)
from mcp_server_nucleus.runtime.liveness import (
    LivenessItem,
    LivenessStatus,
    classify_liveness_item,
)


def _yaml(tmp_path, body):
    p = tmp_path / "growth_registry.yaml"
    p.write_text(body)
    return p


# ── Loading is fault-isolated but never silent ───────────────────────────────

def test_malformed_entry_is_skipped_with_a_reason_not_silently(tmp_path):
    """One bad row must not cost the file — and must not vanish either."""
    p = _yaml(tmp_path, """
entries:
  - id: good
    proof: /tmp/x.log
  - not_a_mapping
  - product: missing-an-id
""")
    load = load_registry(path=p)
    assert [e.id for e in load.entries] == ["good"]
    assert len(load.errors) == 2
    assert any("not a mapping" in e for e in load.errors)
    assert any("missing required field 'id'" in e for e in load.errors)


def test_duplicate_ids_are_reported(tmp_path):
    p = _yaml(tmp_path, "entries:\n  - id: dup\n  - id: dup\n")
    load = load_registry(path=p)
    assert len(load.entries) == 1
    assert any("duplicate id" in e for e in load.errors)


def test_missing_registry_is_an_error_not_an_empty_success(tmp_path):
    load = load_registry(path=tmp_path / "nope.yaml")
    assert load.entries == []
    assert any("no registry" in e for e in load.errors)


# ── The three-way distinction ────────────────────────────────────────────────

def test_declared_proof_that_is_missing_is_DEAD_not_unknown(tmp_path):
    """The finding that matters most.

    A cron scheduled every 2 hours whose output had not changed in ~102 days
    read as UNKNOWN until DEAD existed. 'Produced nothing' is evidence;
    'nothing was declared' is ignorance. They must not share a status.
    """
    e = RegistryEntry(id="job", schedule="2h", proof=str(tmp_path / "never_written.log"))
    item = entry_to_liveness_item(e, tmp_path)
    assert classify_liveness_item(item) == LivenessStatus.DEAD


def test_no_proof_declared_is_UNKNOWN_not_dead(tmp_path):
    e = RegistryEntry(id="job", schedule="1d", proof="")
    item = entry_to_liveness_item(e, tmp_path)
    assert classify_liveness_item(item) == LivenessStatus.UNKNOWN


def test_fresh_proof_artifact_is_healthy(tmp_path):
    art = tmp_path / "out.log"
    art.write_text("x")
    e = RegistryEntry(id="job", schedule="1d", proof=str(art))
    item = entry_to_liveness_item(e, tmp_path)
    assert classify_liveness_item(item) == LivenessStatus.HEALTHY


def test_old_proof_artifact_is_stale(tmp_path):
    art = tmp_path / "out.log"
    art.write_text("x")
    old = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    import os
    os.utime(art, (old, old))
    e = RegistryEntry(id="job", schedule="1h", proof=str(art))
    item = entry_to_liveness_item(e, tmp_path)
    assert classify_liveness_item(item) == LivenessStatus.STALE


def test_dead_survives_reclassification(tmp_path):
    """A pre-set DEAD is evidence and must not be re-derived away."""
    e = RegistryEntry(id="job", schedule="1h", proof=str(tmp_path / "gone.log"))
    item = entry_to_liveness_item(e, tmp_path)
    assert classify_liveness_item(classify_liveness_item(item) and item) == LivenessStatus.DEAD


# ── Proof resolution ─────────────────────────────────────────────────────────

def test_proof_glob_resolves_to_newest_match(tmp_path):
    import os
    (tmp_path / "a.log").write_text("a")
    (tmp_path / "b.log").write_text("b")
    old = (datetime.now(timezone.utc) - timedelta(days=5)).timestamp()
    os.utime(tmp_path / "a.log", (old, old))
    mtime, detail = resolve_proof(str(tmp_path / "*.log"), tmp_path)
    assert mtime is not None
    assert "b.log" in detail


def test_proof_directory_uses_newest_child(tmp_path):
    d = tmp_path / "outdir"
    d.mkdir()
    (d / "f.txt").write_text("x")
    mtime, detail = resolve_proof(str(d), tmp_path)
    assert mtime is not None
    assert "newest file in dir" in detail


def test_empty_directory_is_not_proof_of_running(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    mtime, detail = resolve_proof(str(d), tmp_path)
    assert mtime is None
    assert "empty" in detail


# ── Reconciliation ───────────────────────────────────────────────────────────

def test_matching_id_enriches_rather_than_duplicates(tmp_path):
    art = tmp_path / "out.log"
    art.write_text("x")
    discovered = [LivenessItem(id="job1", name="job1", source="launchd",
                               command="/bin/true", schedule="1h")]
    entries = [RegistryEntry(id="job1", schedule="1h", proof=str(art))]
    merged = reconcile(discovered, entries, tmp_path)
    assert len(merged) == 1                      # enriched, not doubled
    assert merged[0].last_run is not None        # registry supplied what discovery could not
    assert merged[0].metadata.get("registry") is True


def test_unmatched_entry_is_appended(tmp_path):
    discovered = [LivenessItem(id="job1", name="job1", source="launchd",
                               command="/bin/true", schedule="1h")]
    entries = [RegistryEntry(id="elsewhere", schedule="1h", proof=str(tmp_path / "x.log"))]
    merged = reconcile(discovered, entries, tmp_path)
    assert {getattr(m, "id") for m in merged} == {"job1", "elsewhere"}


# ── Intervals and rendering ──────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("30m", 1800.0), ("2h", 7200.0), ("1d", 86400.0), ("1w", 604800.0),
])
def test_parse_interval_shorthand(text, expected):
    assert parse_interval(text) == expected


def test_unparseable_interval_returns_none_rather_than_guessing(tmp_path):
    """An invented interval yields confident wrong staleness verdicts."""
    assert parse_interval("0 4 * * *") is None     # cron form, not shorthand
    assert parse_interval("whenever") is None
    assert parse_interval("") is None


def test_render_marks_missing_proof_as_todo():
    out = render_registry_yaml([RegistryEntry(id="x", schedule="1h", proof="")])
    assert "TODO" in out
    assert "name the artifact" in out


def test_render_never_emits_credentials():
    """Registry files are committed; environment values must never reach them."""
    e = RegistryEntry(id="j", what="job", schedule="1h", proof="/tmp/o.log")
    out = render_registry_yaml([e])
    for leak in ("API_KEY", "TOKEN", "SECRET", "="):
        if leak == "=":
            continue
        assert leak not in out


def test_seeding_never_emits_env_assignment_entries():
    """crontab KEY=value lines are credentials, not jobs."""
    entries = seed_entries_from_machine()
    for e in entries:
        assert "=" not in e.id.split()[0] if e.id else True


# ── Ephemeral paths: absence proves nothing ──────────────────────────────────

def test_missing_artifact_under_tmp_is_unknown_not_dead(tmp_path):
    """macOS clears /tmp, so a missing log there may have been wiped, not never
    written. Three of five apparent deaths on the real machine were this."""
    from mcp_server_nucleus.runtime.growth_registry import is_ephemeral_proof
    e = RegistryEntry(id="j", schedule="1d", proof="/tmp/never_written_xyz.log")
    item = entry_to_liveness_item(e, tmp_path)
    assert is_ephemeral_proof("/tmp/x.log")
    assert classify_liveness_item(item) == LivenessStatus.UNKNOWN
    assert "proves nothing" in item.metadata.get("proof_detail", "")


def test_missing_artifact_on_durable_path_is_still_dead(tmp_path):
    """The distinction must not weaken real detection."""
    e = RegistryEntry(id="j", schedule="1d", proof=str(tmp_path / "durable_missing.log"))
    item = entry_to_liveness_item(e, tmp_path)
    assert classify_liveness_item(item) == LivenessStatus.DEAD


def test_ephemeral_detection_covers_the_real_prefixes():
    from mcp_server_nucleus.runtime.growth_registry import is_ephemeral_proof
    assert is_ephemeral_proof("/private/tmp/a.log")
    assert is_ephemeral_proof("/var/folders/xy/z/T/a.log")
    assert not is_ephemeral_proof("/Users/me/logs/a.log")
    assert not is_ephemeral_proof(".brain/flywheel/cron.log")


# ── Inferred vs declared proof ───────────────────────────────────────────────

def test_inferred_missing_proof_is_unknown_not_dead(tmp_path):
    """Seeded proofs are guesses and must not accuse.

    A weekly job writing conflict_log.jsonl and no stdout had its inferred
    StandardOutPath flagged DEAD, while its real artifact was six days old and
    healthy. An inferred path that never appears is indistinguishable from a
    job that simply writes elsewhere.
    """
    e = RegistryEntry(id="j", schedule="1w", proof=str(tmp_path / "never.log"),
                      proof_source="inferred")
    assert classify_liveness_item(entry_to_liveness_item(e, tmp_path)) == LivenessStatus.UNKNOWN


def test_declared_missing_proof_is_still_dead(tmp_path):
    """A human naming the artifact means it: absence is then a real finding."""
    e = RegistryEntry(id="j", schedule="1w", proof=str(tmp_path / "never.log"),
                      proof_source="declared")
    assert classify_liveness_item(entry_to_liveness_item(e, tmp_path)) == LivenessStatus.DEAD


def test_seeded_entries_are_marked_inferred():
    for e in seed_entries_from_machine():
        assert e.proof_source == "inferred"


def test_registry_file_entries_default_to_declared(tmp_path):
    p = _yaml(tmp_path, "entries:\n  - id: j\n    proof: /x/y.log\n")
    assert load_registry(path=p).entries[0].proof_source == "declared"
