"""Tests for scripts/backfill_sor.py — batch-6 legacy -> SoR backfill staging.

These use a *synthetic mini source db* (the legacy schema, a handful of rows)
built at test time — no dependency on the real multi-GB daemon store. They cover
the two load-bearing pure pieces (row mapping, checkpointing) plus the resumable
INSERT-OR-IGNORE backfill against a real SoR target and the read-only / gating
guardrails.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


# ── module loader (mirrors the existing tests/scripts pattern) ───────────────
def _load_backfill():
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / "scripts" / "backfill_sor.py"
    spec = importlib.util.spec_from_file_location("backfill_sor", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve the module's own
    # (PEP 563 stringized) annotations during class construction.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


bf = _load_backfill()


# ── legacy source schema (verbatim mirror of the daemon store) ───────────────
_LEGACY_SCHEMA = """
CREATE TABLE engrams (
  id      INTEGER PRIMARY KEY,
  surface TEXT    NOT NULL,
  ts      INTEGER NOT NULL,
  payload TEXT    NOT NULL,
  meta    TEXT
);
"""

# A valid unix-ns timestamp (2026-01-01T00:00:00Z-ish).
_TS = 1767225600_000000000


def _make_source(path: Path, rows: list[tuple]) -> Path:
    """Build a synthetic legacy source db. rows = [(id, surface, ts, payload, meta)]."""
    conn = sqlite3.connect(str(path))
    conn.executescript(_LEGACY_SCHEMA)
    conn.executemany(
        "INSERT INTO engrams (id, surface, ts, payload, meta) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return path


def _default_rows(n: int = 6) -> list[tuple]:
    out = []
    for i in range(1, n + 1):
        out.append((i, "claude_code", _TS + i, f"payload text token{i} hello world", None))
    return out


# ── ns_to_iso ────────────────────────────────────────────────────────────────
def test_ns_to_iso_roundtrips_to_utc():
    iso = bf.ns_to_iso(_TS)
    parsed = datetime.fromisoformat(iso)
    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc).year == 2026


@pytest.mark.parametrize("bad", [0, -1, 10**30])
def test_ns_to_iso_rejects_out_of_range(bad):
    with pytest.raises(bf.MappingError):
        bf.ns_to_iso(bad)


def test_ns_to_iso_rejects_non_int():
    with pytest.raises(bf.MappingError):
        bf.ns_to_iso(True)  # bool is not a valid ts
    with pytest.raises(bf.MappingError):
        bf.ns_to_iso("123")  # type: ignore[arg-type]


# ── map_row ──────────────────────────────────────────────────────────────────
def _row(**kw) -> dict:
    base = {"id": 1, "surface": "claude_code", "ts": _TS, "payload": "hi", "meta": None}
    base.update(kw)
    return base


def test_map_row_happy_path_and_provenance():
    imported_at = "2026-07-08T00:00:00+00:00"
    m = bf.map_row(_row(id=42, payload="body", surface="cursor"), imported_at=imported_at)
    assert m is not None
    assert m["id"] == 42                     # legacy id kept as PK
    assert m["key"] == "legacy:42"
    assert m["surface"] == "cursor"
    assert m["text"] == "body"               # payload -> text
    assert m["kind"] == "note"
    assert m["tags"] == ""
    assert m["optional_date"] == ""
    assert m["source"] == bf.PROVENANCE_SOURCE == "legacy-daemon"
    meta = json.loads(m["meta"])
    assert meta["backfill"]["source"] == "legacy-daemon"
    assert meta["backfill"]["imported_at"] == imported_at
    assert meta["backfill"]["legacy_id"] == 42
    assert meta["backfill"]["legacy_ts_ns"] == _TS


def test_map_row_preserves_legacy_meta_json():
    m = bf.map_row(_row(meta='{"path":"x","offset":5}'), imported_at="t")
    meta = json.loads(m["meta"])
    assert meta["legacy"] == {"path": "x", "offset": 5}


def test_map_row_keeps_unparseable_meta_as_raw():
    m = bf.map_row(_row(meta="not-json"), imported_at="t")
    meta = json.loads(m["meta"])
    assert meta["legacy"] == {"raw": "not-json"}


def test_map_row_empty_payload_is_skip():
    assert bf.map_row(_row(payload=""), imported_at="t") is None
    assert bf.map_row(_row(payload=None), imported_at="t") is None


def test_map_row_bad_ts_is_error():
    with pytest.raises(bf.MappingError):
        bf.map_row(_row(ts=-5), imported_at="t")


def test_map_row_blank_surface_is_error():
    with pytest.raises(bf.MappingError):
        bf.map_row(_row(surface=""), imported_at="t")


def test_map_row_accepts_sqlite_row(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(1))
    conn = bf.open_source_ro(src_path)
    row = conn.execute("SELECT id, surface, ts, payload, meta FROM engrams").fetchone()
    m = bf.map_row(row, imported_at="t")
    conn.close()
    assert m["key"] == "legacy:1"


# ── checkpoint (atomic) ──────────────────────────────────────────────────────
def test_checkpoint_roundtrip(tmp_path):
    ckpt_path = tmp_path / "t.ckpt"
    ck = bf.Checkpoint(path=ckpt_path)
    stats = bf.Stats(mapped=10, skipped=2, error=1, last_source_id=123, scanned=13)
    ck.save(stats)
    assert ckpt_path.exists()
    loaded = bf.Checkpoint.load(ckpt_path)
    assert loaded is not None
    assert loaded.last_source_id == 123
    assert loaded.mapped == 10
    assert loaded.skipped == 2
    assert loaded.error == 1
    # No leftover temp file after the atomic replace.
    assert not (ckpt_path.with_suffix(ckpt_path.suffix + ".tmp")).exists()


def test_checkpoint_load_missing_returns_none(tmp_path):
    assert bf.Checkpoint.load(tmp_path / "nope.ckpt") is None


# ── read-only source enforcement ─────────────────────────────────────────────
def test_source_opened_read_only(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(1))
    conn = bf.open_source_ro(src_path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO engrams (id, surface, ts, payload) VALUES (99,'x',1,'y')")
    conn.close()


# ── end-to-end backfill into a real SoR target ───────────────────────────────
def _run(src_path: Path, target: Path, *, limit=None, start_after_id=0, checkpoint=None):
    src = bf.open_source_ro(src_path)
    dst = bf.create_target(target)
    stats = bf.Stats()
    try:
        bf.backfill(
            src, dst, stats=stats, imported_at="2026-07-08T00:00:00+00:00",
            batch=2, limit=limit, start_after_id=start_after_id, checkpoint=checkpoint,
        )
    finally:
        dst.close()
        src.close()
    return stats


def test_backfill_maps_and_populates_fts(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(6))
    target = tmp_path / "sor.db"
    stats = _run(src_path, target)
    assert stats.mapped == 6
    assert stats.skipped == 0
    assert stats.error == 0

    conn = sqlite3.connect(str(target))
    assert conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0] == 6
    # FTS shadow populated in lockstep + answers a MATCH.
    assert conn.execute("SELECT COUNT(*) FROM engrams_fts").fetchone()[0] == 6
    hit = conn.execute(
        "SELECT COUNT(*) FROM engrams_fts WHERE engrams_fts MATCH ?", ("token3",)
    ).fetchone()[0]
    assert hit == 1
    # Provenance landed in both the source column and meta JSON.
    r = conn.execute("SELECT source, meta FROM engrams WHERE id=1").fetchone()
    assert r[0] == "legacy-daemon"
    assert json.loads(r[1])["backfill"]["legacy_id"] == 1
    conn.close()


def test_backfill_skips_and_errors_are_counted(tmp_path):
    rows = [
        (1, "claude_code", _TS, "good", None),
        (2, "claude_code", _TS, "", None),      # empty payload -> skip
        (3, "claude_code", -9, "badts", None),  # bad ts -> error
        (4, "claude_code", _TS, "good2", None),
    ]
    src_path = _make_source(tmp_path / "src.db", rows)
    target = tmp_path / "sor.db"
    stats = _run(src_path, target)
    assert stats.mapped == 2
    assert stats.skipped == 1
    assert stats.error == 1


def test_backfill_is_idempotent_on_rerun(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(5))
    target = tmp_path / "sor.db"
    _run(src_path, target)
    # Second full run: INSERT OR IGNORE on the stable id -> no duplicates.
    stats2 = _run(src_path, target)
    conn = sqlite3.connect(str(target))
    total = conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0]
    fts = conn.execute("SELECT COUNT(*) FROM engrams_fts").fetchone()[0]
    conn.close()
    assert total == 5
    assert fts == 5  # trigger did not double-index (IGNORE => no insert fired)


def test_backfill_resume_from_checkpoint(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(6))
    target = tmp_path / "sor.db"
    ckpt = bf.Checkpoint(path=tmp_path / "sor.db.backfill.ckpt")

    # First pass: only the first 3 source rows (simulate an interruption).
    stats1 = _run(src_path, target, limit=3, checkpoint=ckpt)
    assert stats1.last_source_id == 3
    conn = sqlite3.connect(str(target))
    assert conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0] == 3
    conn.close()

    loaded = bf.Checkpoint.load(ckpt.path)
    assert loaded.last_source_id == 3

    # Resume: continue past the checkpoint, no re-processing of 1..3.
    src = bf.open_source_ro(src_path)
    dst = bf.create_target(target)
    stats2 = bf.Stats(
        mapped=loaded.mapped, skipped=loaded.skipped, error=loaded.error,
        last_source_id=loaded.last_source_id,
    )
    try:
        bf.backfill(
            src, dst, stats=stats2, imported_at="t", batch=2, limit=None,
            start_after_id=loaded.last_source_id, checkpoint=ckpt,
        )
    finally:
        dst.close()
        src.close()
    conn = sqlite3.connect(str(target))
    assert conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0] == 6
    conn.close()
    assert stats2.mapped == 6


# ── verify_target ────────────────────────────────────────────────────────────
def test_verify_target_passes_on_clean_backfill(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(8))
    target = tmp_path / "sor.db"
    src = bf.open_source_ro(src_path)
    dst = bf.create_target(target)
    stats = bf.Stats()
    try:
        bf.backfill(src, dst, stats=stats, imported_at="t", batch=4, limit=None,
                    start_after_id=0, checkpoint=None)
        res = bf.verify_target(dst, src, stats=stats, imported_at="t", spot_check=5)
    finally:
        dst.close()
        src.close()
    assert res.target_engrams == 8
    assert res.fts_rows == 8
    assert res.fts_match_ok
    assert res.spot_checked == 5
    assert res.spot_passed == 5
    assert res.ok


# ── gating / refusal guards ──────────────────────────────────────────────────
def _args(**kw):
    base = dict(
        source="/nonexistent/src.db", target=None, no_dry_run=True,
        i_am_the_operator=False, resume=False, sample=10, batch=2, spot_check=5,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_real_mode_requires_operator_flag(capsys):
    rc = bf.run_real(_args(i_am_the_operator=False, target="/tmp/x.db"))
    assert rc == 2
    assert "operator" in capsys.readouterr().err.lower()


def test_real_mode_requires_target(capsys):
    rc = bf.run_real(_args(i_am_the_operator=True, target=None))
    assert rc == 2
    assert "target" in capsys.readouterr().err.lower()


def test_real_mode_refuses_source_equals_target(tmp_path, capsys):
    src_path = _make_source(tmp_path / "same.db", _default_rows(1))
    rc = bf.run_real(_args(i_am_the_operator=True, source=str(src_path), target=str(src_path)))
    assert rc == 2
    assert "source" in capsys.readouterr().err.lower()


def test_real_mode_refuses_nonempty_target_without_resume(tmp_path, capsys):
    src_path = _make_source(tmp_path / "src.db", _default_rows(3))
    target = tmp_path / "sor.db"
    _run(src_path, target)  # pre-populate the target
    rc = bf.run_real(_args(i_am_the_operator=True, source=str(src_path), target=str(target)))
    assert rc == 2
    assert "already contains" in capsys.readouterr().err.lower()


def test_real_mode_resume_accepts_nonempty_target(tmp_path):
    src_path = _make_source(tmp_path / "src.db", _default_rows(4))
    target = tmp_path / "sor.db"
    rc = bf.run_real(
        _args(i_am_the_operator=True, source=str(src_path), target=str(target), resume=True)
    )
    assert rc == 0
    conn = sqlite3.connect(str(target))
    assert conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0] == 4
    conn.close()


def test_dry_run_is_default(monkeypatch):
    called = {}

    def fake_dry(args):
        called["dry"] = True
        return 0

    def fake_real(args):
        called["real"] = True
        return 0

    monkeypatch.setattr(bf, "run_dry_run", fake_dry)
    monkeypatch.setattr(bf, "run_real", fake_real)
    bf.main([])  # no flags -> dry-run
    assert called == {"dry": True}


def test_dry_run_end_to_end_report(tmp_path, capsys):
    src_path = _make_source(tmp_path / "src.db", _default_rows(12))
    scratch = tmp_path / "scratch.db"
    rc = bf.run_dry_run(_args(no_dry_run=False, source=str(src_path),
                              target=str(scratch), sample=12, spot_check=5))
    out = capsys.readouterr().out
    assert rc == 0
    assert "BACKFILL DRY-RUN REPORT" in out
    assert "SCHEMA MAPPING" in out
    assert "verify verdict         : PASS" in out
