#!/usr/bin/env python3
"""Batch-6 staging — resumable legacy -> SoR backfill (dry-run default, operator-gated).

Move 2 batch 6 needs a one-time, resumable migration of the legacy external-daemon
engram store into the unified Source-of-Record (SoR) SQLite the ``MemoryFacade``
delegates to. This script *stages* that machinery and produces dry-run evidence.
It does NOT perform the real migration by default: real execution is gated behind
two explicit flags AND an explicit target, so it can only be run deliberately by
a human operator (never by an agent, never by CI).

Schemas
-------
Legacy source (the Go daemon's store, ``~/.eidetic/engrams.db``, read verbatim)::

    engrams(id INTEGER PK, surface TEXT NOT NULL,
            ts INTEGER NOT NULL,          -- unix epoch NANOSECONDS
            payload TEXT NOT NULL, meta TEXT)   -- meta is a JSON string

SoR target (this repo's ``mcp_server_nucleus.memory.sor`` — schema imported live,
never re-declared here so the two can never drift)::

    engrams(id INTEGER PK, key TEXT, surface TEXT, text TEXT NOT NULL, tags TEXT,
            kind TEXT, meta TEXT, created_at TEXT, optional_date TEXT, source TEXT)
    + engrams_fts  (FTS5 shadow, kept in lockstep by triggers)
    + curation_overlay

Field mapping (see ``MAPPING_TABLE`` / the dry-run report for the rendered form)::

    legacy.id       -> SoR.id            (kept as PK == idempotency key)
    legacy.id       -> SoR.key           ("legacy:<id>" provenance handle)
    legacy.surface  -> SoR.surface       (verbatim)
    legacy.payload  -> SoR.text          (renamed column)
    legacy.ts (ns)  -> SoR.created_at    (ns -> ISO-8601 UTC string)
    (none)          -> SoR.kind          ("note" default)
    (none)          -> SoR.tags          ("")
    legacy.meta     -> SoR.meta.legacy   (original preserved under a namespace)
    (provenance)    -> SoR.source        ("legacy-daemon")
    (provenance)    -> SoR.meta.backfill  ({source, imported_at, legacy_id, legacy_ts_ns})

Safety invariants
-----------------
* Source is opened ``file:...?mode=ro&immutable=1`` — a read-only, immutable
  handle. This process never opens a writable handle on the source.
* The script refuses to run if the resolved source path == the resolved target.
* ``--dry-run`` is the DEFAULT. Real writes require BOTH ``--no-dry-run`` and
  ``--i-am-the-operator`` AND an explicit ``--target``.
* A target that already holds engram rows is refused unless ``--resume``.
* Inserts are ``INSERT OR IGNORE`` keyed on the stable legacy id, so a resumed
  or re-run backfill is idempotent (already-present ids are no-ops).
* A checkpoint (last processed source id + running counts) is written atomically
  after every committed batch; ``--resume`` continues from it.

Run it (always safe — reads the source, writes only a throwaway scratch db)::

    PYTHONPATH=src python -m scripts.backfill_sor --dry-run --sample 5000
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

# Provenance stamped onto every backfilled row.
PROVENANCE_SOURCE = "legacy-daemon"

# Default batch / sample sizes.
DEFAULT_BATCH = 5000
DEFAULT_SAMPLE = 5000
DEFAULT_SPOT_CHECK = 20

# Default legacy source location (computed from $HOME — never a hardcoded path).
DEFAULT_SOURCE = Path.home() / ".eidetic" / "engrams.db"

# Human-readable field mapping, rendered in the dry-run report.
MAPPING_TABLE = [
    ("legacy.id", "SoR.id", "kept as PK (== idempotency key)"),
    ("legacy.id", "SoR.key", "'legacy:<id>' provenance handle"),
    ("legacy.surface", "SoR.surface", "verbatim"),
    ("legacy.payload", "SoR.text", "renamed column"),
    ("legacy.ts (ns)", "SoR.created_at", "unix-ns -> ISO-8601 UTC"),
    ("(default)", "SoR.kind", "'note'"),
    ("(default)", "SoR.tags", "'' (empty)"),
    ("legacy.meta", "SoR.meta.legacy", "original JSON preserved, namespaced"),
    ("(provenance)", "SoR.source", f"'{PROVENANCE_SOURCE}'"),
    ("(provenance)", "SoR.meta.backfill", "{source, imported_at, legacy_id, legacy_ts_ns}"),
]

# Insert columns in a fixed order (id first so it lands on the PK).
_INSERT_COLS = (
    "id", "key", "surface", "text", "tags",
    "kind", "meta", "created_at", "optional_date", "source",
)
_INSERT_SQL = (
    "INSERT OR IGNORE INTO engrams (" + ", ".join(_INSERT_COLS) + ") "
    "VALUES (" + ", ".join("?" for _ in _INSERT_COLS) + ")"
)


class MappingError(Exception):
    """A source row could not be mapped to the SoR shape (counts as an error)."""


@dataclass
class Stats:
    mapped: int = 0
    skipped: int = 0
    error: int = 0
    last_source_id: int = 0
    scanned: int = 0

    def as_dict(self) -> dict:
        return {
            "mapped": self.mapped,
            "skipped": self.skipped,
            "error": self.error,
            "last_source_id": self.last_source_id,
            "scanned": self.scanned,
        }


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested against a synthetic mini source db)
# --------------------------------------------------------------------------- #
def ns_to_iso(ts_ns: int) -> str:
    """Convert a unix-epoch-nanoseconds integer to an ISO-8601 UTC string.

    Raises ``MappingError`` for values that are not a sane wall-clock instant
    (non-int, non-positive, or outside year 1971..2100) so a corrupt ``ts`` is
    counted as an error rather than silently producing a garbage timestamp.
    """
    if not isinstance(ts_ns, int) or isinstance(ts_ns, bool):
        raise MappingError(f"ts is not an int: {type(ts_ns).__name__}")
    if ts_ns <= 0:
        raise MappingError("ts is non-positive")
    seconds = ts_ns / 1_000_000_000
    try:
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:  # pragma: no cover - platform edge
        raise MappingError(f"ts out of range: {exc}") from exc
    if not (1971 <= dt.year <= 2100):
        raise MappingError(f"ts year out of sane range: {dt.year}")
    return dt.isoformat()


def _coerce_legacy_meta(meta: Optional[str]) -> object:
    """Preserve the legacy meta: parse JSON if possible, else keep the raw string."""
    if meta is None:
        return None
    if isinstance(meta, str):
        try:
            return json.loads(meta)
        except (json.JSONDecodeError, ValueError):
            return {"raw": meta}
    return {"raw": str(meta)}


def map_row(row: sqlite3.Row | dict, *, imported_at: str) -> Optional[dict]:
    """Map one legacy row to SoR insert params.

    Returns a dict of SoR column values, or ``None`` to *skip* a row (e.g. an
    empty payload — nothing to remember). Raises ``MappingError`` for a row that
    is present but un-mappable (counts toward the error total).
    """
    legacy_id = row["id"]
    surface = row["surface"]
    payload = row["payload"]
    ts_ns = row["ts"]

    if legacy_id is None:
        raise MappingError("missing legacy id")
    if payload is None or payload == "":
        return None  # nothing to store -> skip
    if surface is None or surface == "":
        # Surface is NOT NULL in the legacy schema; a blank one is corrupt.
        raise MappingError(f"missing surface for id={legacy_id}")

    created_at = ns_to_iso(ts_ns)

    meta = {
        "backfill": {
            "source": PROVENANCE_SOURCE,
            "imported_at": imported_at,
            "legacy_id": legacy_id,
            "legacy_ts_ns": ts_ns,
        },
        "legacy": _coerce_legacy_meta(row["meta"] if "meta" in row.keys() else None)
        if isinstance(row, sqlite3.Row)
        else _coerce_legacy_meta(row.get("meta")),
    }

    return {
        "id": legacy_id,
        "key": f"legacy:{legacy_id}",
        "surface": surface,
        "text": payload,
        "tags": "",
        "kind": "note",
        "meta": json.dumps(meta, ensure_ascii=False, sort_keys=True),
        "created_at": created_at,
        "optional_date": "",
        "source": PROVENANCE_SOURCE,
    }


def _insert_params(mapped: dict) -> tuple:
    return tuple(mapped[c] for c in _INSERT_COLS)


# --------------------------------------------------------------------------- #
# Checkpoint (atomic)
# --------------------------------------------------------------------------- #
@dataclass
class Checkpoint:
    path: Path
    last_source_id: int = 0
    mapped: int = 0
    skipped: int = 0
    error: int = 0

    @classmethod
    def load(cls, path: Path) -> Optional["Checkpoint"]:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            path=path,
            last_source_id=int(data.get("last_source_id", 0)),
            mapped=int(data.get("mapped", 0)),
            skipped=int(data.get("skipped", 0)),
            error=int(data.get("error", 0)),
        )

    def save(self, stats: Stats) -> None:
        """Atomically persist progress: write a temp sibling, then ``os.replace``."""
        self.last_source_id = stats.last_source_id
        self.mapped = stats.mapped
        self.skipped = stats.skipped
        self.error = stats.error
        payload = {
            "last_source_id": self.last_source_id,
            "mapped": self.mapped,
            "skipped": self.skipped,
            "error": self.error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)  # atomic on POSIX


# --------------------------------------------------------------------------- #
# Connections
# --------------------------------------------------------------------------- #
def open_source_ro(source: Path) -> sqlite3.Connection:
    """Open the legacy source strictly read-only + immutable. Never writable."""
    uri = f"file:{source}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _get_schema_sql() -> str:
    """Return the live SoR schema DDL, imported from the package (single source).

    Imported lazily so the script has no import-time dependency on the heavy
    server startup path; only the small ``memory.sor`` module is pulled in.
    """
    from mcp_server_nucleus.memory.sor import SCHEMA

    return SCHEMA


def create_target(path: Path) -> sqlite3.Connection:
    """Create/open the target with the *live* SoR schema (FTS + triggers + overlay)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from mcp_server_nucleus.runtime.common import open_hardened_sqlite

        conn = open_hardened_sqlite(path)
    except Exception:  # pragma: no cover - fallback if runtime.common unavailable
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    conn.executescript(_get_schema_sql())
    return conn


def target_engram_count(path: Path) -> int:
    """Number of engram rows already in a target (0 if the file/table is absent)."""
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='engrams'"
        ).fetchone()
        if row is None:
            return 0
        return int(conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0])
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Core backfill
# --------------------------------------------------------------------------- #
def iter_source(
    src: sqlite3.Connection, *, start_after_id: int, batch: int, limit: Optional[int]
) -> Iterator[list]:
    """Yield lists of source rows in ascending id order, resumable + capped.

    ``start_after_id`` skips everything already processed (resume). ``limit``, if
    set, caps the *total* number of source rows scanned (used by --sample).
    """
    last = start_after_id
    scanned = 0
    while True:
        take = batch
        if limit is not None:
            remaining = limit - scanned
            if remaining <= 0:
                return
            take = min(batch, remaining)
        rows = src.execute(
            "SELECT id, surface, ts, payload, meta FROM engrams "
            "WHERE id > ? ORDER BY id ASC LIMIT ?",
            (last, take),
        ).fetchall()
        if not rows:
            return
        scanned += len(rows)
        last = rows[-1]["id"]
        yield rows


def backfill(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    *,
    stats: Stats,
    imported_at: str,
    batch: int,
    limit: Optional[int],
    start_after_id: int,
    checkpoint: Optional[Checkpoint] = None,
) -> Stats:
    """Map + INSERT OR IGNORE every source row past ``start_after_id`` into ``dst``.

    Each batch runs in a single transaction; the checkpoint (if given) is saved
    atomically after each batch commit. Mutates and returns ``stats``.
    """
    for rows in iter_source(src, start_after_id=start_after_id, batch=batch, limit=limit):
        params: list[tuple] = []
        for row in rows:
            stats.scanned += 1
            try:
                mapped = map_row(row, imported_at=imported_at)
            except MappingError:
                stats.error += 1
                continue
            if mapped is None:
                stats.skipped += 1
                continue
            params.append(_insert_params(mapped))
        # One transaction per batch.
        with dst:
            dst.executemany(_INSERT_SQL, params)
        stats.mapped += len(params)
        stats.last_source_id = rows[-1]["id"]
        if checkpoint is not None:
            checkpoint.save(stats)
    return stats


# --------------------------------------------------------------------------- #
# Verification (dry-run)
# --------------------------------------------------------------------------- #
@dataclass
class VerifyResult:
    target_engrams: int = 0
    fts_rows: int = 0
    fts_match_ok: bool = False
    spot_checked: int = 0
    spot_passed: int = 0
    notes: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.fts_rows == self.target_engrams
            and self.fts_match_ok
            and self.spot_checked == self.spot_passed
        )


def verify_target(
    dst: sqlite3.Connection,
    src: sqlite3.Connection,
    *,
    stats: Stats,
    imported_at: str,
    spot_check: int = DEFAULT_SPOT_CHECK,
    rng: Optional[random.Random] = None,
) -> VerifyResult:
    """Verify the scratch target: row counts, FTS population, random round-trips."""
    rng = rng or random.Random(0)
    res = VerifyResult()
    res.target_engrams = int(dst.execute("SELECT COUNT(*) FROM engrams").fetchone()[0])
    res.fts_rows = int(dst.execute("SELECT COUNT(*) FROM engrams_fts").fetchone()[0])

    if res.target_engrams != stats.mapped:
        res.notes.append(
            f"row-count mismatch: target={res.target_engrams} mapped={stats.mapped}"
        )
    if res.fts_rows != res.target_engrams:
        res.notes.append(
            f"FTS row-count != engrams: fts={res.fts_rows} engrams={res.target_engrams}"
        )

    # Prove the FTS index actually answers a MATCH (pick a token from a real row).
    sample = dst.execute("SELECT text FROM engrams LIMIT 1").fetchone()
    if sample is not None:
        token = _first_wordy_token(sample["text"])
        if token:
            try:
                hit = dst.execute(
                    "SELECT COUNT(*) FROM engrams_fts WHERE engrams_fts MATCH ?",
                    (f'"{token}"',),
                ).fetchone()[0]
                res.fts_match_ok = int(hit) >= 1
            except sqlite3.OperationalError as exc:
                res.notes.append(f"FTS MATCH failed: {exc}")
        else:
            res.fts_match_ok = res.fts_rows == res.target_engrams
    else:
        res.fts_match_ok = res.target_engrams == 0

    # Spot-check up to ``spot_check`` random round-trips (target row vs re-mapped source).
    ids = [r["id"] for r in dst.execute("SELECT id FROM engrams").fetchall()]
    if ids:
        pick = rng.sample(ids, min(spot_check, len(ids)))
        for row_id in pick:
            res.spot_checked += 1
            tgt = dst.execute(
                "SELECT surface, text, created_at, source FROM engrams WHERE id = ?",
                (row_id,),
            ).fetchone()
            srow = src.execute(
                "SELECT id, surface, ts, payload, meta FROM engrams WHERE id = ?",
                (row_id,),
            ).fetchone()
            if tgt is None or srow is None:
                continue
            try:
                expected = map_row(srow, imported_at=imported_at)
            except MappingError:
                continue
            if expected is None:
                continue
            if (
                tgt["surface"] == expected["surface"]
                and tgt["text"] == expected["text"]
                and tgt["created_at"] == expected["created_at"]
                and tgt["source"] == PROVENANCE_SOURCE
            ):
                res.spot_passed += 1
    return res


def _first_wordy_token(text: str) -> Optional[str]:
    """Return the first alphanumeric run of length >= 3 (a clean FTS token)."""
    import re

    for m in re.finditer(r"[A-Za-z0-9]{3,}", text or ""):
        return m.group(0)
    return None


# --------------------------------------------------------------------------- #
# Reporting (identity-safe: aggregates only, never echoes payload/meta)
# --------------------------------------------------------------------------- #
def _fmt_duration(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.2f}h"


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PiB"


def render_report(
    *,
    total_source_rows: int,
    stats: Stats,
    verify: VerifyResult,
    elapsed: float,
    scratch_db_bytes: int,
) -> str:
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append("BACKFILL DRY-RUN REPORT  (legacy-daemon -> SoR)")
    lines.append("=" * 64)
    lines.append(f"total source rows        : {total_source_rows:,}")
    lines.append(f"sample scanned           : {stats.scanned:,}")
    lines.append(f"  mapped (inserted)      : {stats.mapped:,}")
    lines.append(f"  skipped (empty payload): {stats.skipped:,}")
    lines.append(f"  errors  (unmappable)   : {stats.error:,}")
    lines.append("")
    lines.append("VERIFY (scratch target)")
    lines.append(f"  target engram rows     : {verify.target_engrams:,}")
    lines.append(f"  FTS index rows         : {verify.fts_rows:,}")
    lines.append(f"  FTS MATCH answers      : {'yes' if verify.fts_match_ok else 'NO'}")
    lines.append(
        f"  spot-check round-trips : {verify.spot_passed}/{verify.spot_checked} passed"
    )
    lines.append(f"  verify verdict         : {'PASS' if verify.ok else 'FAIL'}")
    if verify.notes:
        for n in verify.notes:
            lines.append(f"  note: {n}")
    lines.append("")

    # Projections from the sample rate.
    if stats.scanned and elapsed > 0:
        rate = stats.scanned / elapsed
        proj_time = total_source_rows / rate if rate else 0.0
    else:
        rate = 0.0
        proj_time = 0.0
    if stats.mapped and scratch_db_bytes:
        bytes_per_mapped = scratch_db_bytes / stats.mapped
        map_ratio = stats.mapped / stats.scanned if stats.scanned else 1.0
        proj_disk = bytes_per_mapped * total_source_rows * map_ratio
    else:
        proj_disk = 0.0
    lines.append("PROJECTION (full run, extrapolated from sample)")
    lines.append(f"  sample throughput      : {rate:,.0f} rows/s")
    lines.append(f"  projected full-run time: {_fmt_duration(proj_time)}")
    lines.append(f"  scratch db size        : {_fmt_bytes(scratch_db_bytes)}")
    lines.append(f"  projected target disk  : {_fmt_bytes(proj_disk)}")
    lines.append("")
    lines.append("SCHEMA MAPPING  (legacy -> SoR)")
    w1 = max(len(a) for a, _, _ in MAPPING_TABLE)
    w2 = max(len(b) for _, b, _ in MAPPING_TABLE)
    for a, b, note in MAPPING_TABLE:
        lines.append(f"  {a:<{w1}}  ->  {b:<{w2}}  {note}")
    lines.append("=" * 64)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _resolve(p: Path) -> Path:
    try:
        return p.resolve()
    except OSError:
        return p.absolute()


def _looks_like_brain_engrams(path: Path) -> bool:
    return path.name == "engrams.db" and path.parent.name == ".brain"


def run_dry_run(args) -> int:
    source = _resolve(Path(args.source))
    if not source.exists():
        # Degrade gracefully — the source is a read; if it is genuinely absent or
        # locked we cannot produce real evidence. Report and exit non-zero so the
        # caller knows the dry-run did not exercise real data.
        print(
            f"[backfill] source not found or unreadable: {source}\n"
            "           (expected the legacy daemon store; build against the "
            "inferred schema and re-run when the file is present).",
            file=sys.stderr,
        )
        return 3

    # Scratch target under the OS temp dir (never near the real .brain).
    if args.target:
        scratch = _resolve(Path(args.target))
        scratch_dir = scratch.parent
        cleanup_dir = None
    else:
        scratch_dir = Path(tempfile.mkdtemp(prefix="backfill_sor_dryrun_"))
        scratch = scratch_dir / "scratch.db"
        cleanup_dir = scratch_dir

    if _resolve(scratch) == source:
        print("[backfill] refusing: scratch target == source path", file=sys.stderr)
        return 2

    imported_at = datetime.now(timezone.utc).isoformat()
    src = open_source_ro(source)
    try:
        total_source_rows = int(src.execute("SELECT COUNT(*) FROM engrams").fetchone()[0])
        dst = create_target(scratch)
        try:
            stats = Stats()
            t0 = time.monotonic()
            backfill(
                src,
                dst,
                stats=stats,
                imported_at=imported_at,
                batch=args.batch,
                limit=args.sample,
                start_after_id=0,
                checkpoint=None,
            )
            elapsed = time.monotonic() - t0
            verify = verify_target(
                dst, src, stats=stats, imported_at=imported_at,
                spot_check=args.spot_check,
            )
        finally:
            dst.close()
    finally:
        src.close()

    scratch_bytes = scratch.stat().st_size if scratch.exists() else 0
    report = render_report(
        total_source_rows=total_source_rows,
        stats=stats,
        verify=verify,
        elapsed=elapsed,
        scratch_db_bytes=scratch_bytes,
    )
    print(report)
    if cleanup_dir is not None:
        print(f"[backfill] scratch db retained at: {scratch}")
    return 0 if verify.ok else 1


def run_real(args) -> int:
    if not args.i_am_the_operator:
        print(
            "[backfill] REAL mode requires --i-am-the-operator (operator-gated).",
            file=sys.stderr,
        )
        return 2
    if not args.target:
        print("[backfill] REAL mode requires an explicit --target path.", file=sys.stderr)
        return 2

    source = _resolve(Path(args.source))
    target = _resolve(Path(args.target))
    if not source.exists():
        print(f"[backfill] source not found: {source}", file=sys.stderr)
        return 3
    if source == target:
        print("[backfill] refusing: source path == target path.", file=sys.stderr)
        return 2

    existing = target_engram_count(target)
    if existing > 0 and not args.resume:
        where = "the production .brain SoR" if _looks_like_brain_engrams(target) else "target"
        print(
            f"[backfill] refusing: {where} already contains {existing:,} engram rows. "
            "Pass --resume to continue an interrupted backfill.",
            file=sys.stderr,
        )
        return 2

    ckpt_path = Path(str(target) + ".backfill.ckpt")
    start_after = 0
    stats = Stats()
    if args.resume:
        loaded = Checkpoint.load(ckpt_path)
        if loaded is not None:
            start_after = loaded.last_source_id
            stats.mapped = loaded.mapped
            stats.skipped = loaded.skipped
            stats.error = loaded.error
            stats.last_source_id = loaded.last_source_id
            print(f"[backfill] resuming after source id {start_after:,}")
    checkpoint = Checkpoint(path=ckpt_path)

    imported_at = datetime.now(timezone.utc).isoformat()
    src = open_source_ro(source)
    try:
        total = int(src.execute("SELECT COUNT(*) FROM engrams").fetchone()[0])
        dst = create_target(target)
        try:
            t0 = time.monotonic()
            backfill(
                src,
                dst,
                stats=stats,
                imported_at=imported_at,
                batch=args.batch,
                limit=None,
                start_after_id=start_after,
                checkpoint=checkpoint,
            )
            elapsed = time.monotonic() - t0
        finally:
            dst.close()
    finally:
        src.close()

    print(
        f"[backfill] done: {stats.mapped:,} mapped / {stats.skipped:,} skipped / "
        f"{stats.error:,} errors of {total:,} source rows in {_fmt_duration(elapsed)}. "
        f"checkpoint: {ckpt_path}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="backfill_sor",
        description=(
            "Stage a resumable legacy-daemon -> SoR engram backfill. Dry-run is the "
            "default; real execution is operator-gated (--no-dry-run + "
            "--i-am-the-operator + --target)."
        ),
    )
    p.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="legacy source db (opened read-only+immutable). Default: ~/.eidetic/engrams.db",
    )
    p.add_argument(
        "--target",
        default=None,
        help="target SoR db path. Required for real mode; optional scratch path for dry-run.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="explicit no-op: dry-run is already the default (accepted for clarity).",
    )
    p.add_argument(
        "--no-dry-run",
        action="store_true",
        help="perform REAL writes (also requires --i-am-the-operator + --target).",
    )
    p.add_argument(
        "--i-am-the-operator",
        action="store_true",
        help="operator acknowledgement required for real mode.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="continue from the checkpoint; allow a non-empty target.",
    )
    p.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE,
        help=f"dry-run: number of source rows to sample (default {DEFAULT_SAMPLE}).",
    )
    p.add_argument(
        "--batch",
        type=int,
        default=DEFAULT_BATCH,
        help=f"rows per insert transaction / checkpoint interval (default {DEFAULT_BATCH}).",
    )
    p.add_argument(
        "--spot-check",
        type=int,
        default=DEFAULT_SPOT_CHECK,
        help=f"dry-run: random round-trips to verify (default {DEFAULT_SPOT_CHECK}).",
    )
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = not args.no_dry_run
    if dry_run:
        return run_dry_run(args)
    return run_real(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
