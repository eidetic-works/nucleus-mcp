"""Regression tests for #447 wedge stale-projection bug.

Per cc-main Loop #6 finding 2026-06-03 08:05Z: PR #437 mtime-check fix
re-surfaced — recall_activity returned stale data despite history.jsonl
having newer writes.

Two defensive guards added by #447 v2:
1. mtime comparison uses `>=` not `>` — catches same-second write+recall
   when stat() float-second precision can't distinguish (e.g. rapid
   back-to-back tool calls)
2. row-count sanity check — if history.jsonl has more lines than projected
   history-source rows in memories table, treat as stale even when mtime
   doesn't agree (catches rsync-preserved-mtime imports, coarse fs mtime,
   etc)

These tests would FAIL on PR #437 v1 (`>` mtime check, no row-count check)
and PASS on #447 v2 fix.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PKG_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PKG_ROOT))


def _write_history(brain: Path, lines: list[dict]) -> Path:
    engrams_dir = brain / "engrams"
    engrams_dir.mkdir(parents=True, exist_ok=True)
    path = engrams_dir / "history.jsonl"
    with open(path, "w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def _make_engram(text: str, ts_iso: str) -> dict:
    return {
        "key": f"test_{text[:20]}",
        "timestamp": ts_iso,
        "snapshot": {
            "value": text,
            "context": "[note: test]",
            "timestamp": ts_iso,
            "source_agent": "test_447",
        },
    }


class TestEnsurePopulatedRebuildOnSameSecondAppend(unittest.TestCase):
    """#447 v2: same-second write+recall MUST trigger rebuild."""

    def test_rebuilds_on_same_second_history_append(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            from nucleus_wedge.recall_cmd import _ensure_populated, _do_recall_query

            t0_iso = "2026-06-03T20:00:00+00:00"
            _write_history(brain, [_make_engram("initial_engram_str", t0_iso)])
            _ensure_populated(str(brain))

            db_path = brain / "memories.db"
            self.assertTrue(db_path.exists())

            t1_iso = "2026-06-03T20:00:01+00:00"
            history_path = brain / "engrams" / "history.jsonl"
            with open(history_path, "a") as f:
                f.write(json.dumps(_make_engram("same_second_append_xyz", t1_iso)) + "\n")

            # Force history mtime to EQUAL db mtime (same-second boundary)
            db_mtime = db_path.stat().st_mtime
            os.utime(history_path, (db_mtime, db_mtime))

            results = _do_recall_query(
                query="same_second_append_xyz",
                limit=10,
                kind=None,
                tags=None,
                since=None,
                source_filter=None,
                brain_path_arg=str(brain),
            )

            self.assertEqual(
                len(results), 1,
                "Same-second append must trigger rebuild (#447 v2 `>=` fix). "
                "If 0 results: v1 `>` is silently swallowing the write."
            )
            self.assertIn("same_second_append_xyz", results[0]["text"])


class TestEnsurePopulatedRebuildOnRowCountMismatch(unittest.TestCase):
    """#447 v2: row-count check catches mtime-mismatch edge cases."""

    def test_rebuilds_when_history_lines_exceed_projected_rows(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            from nucleus_wedge.recall_cmd import _ensure_populated, _do_recall_query

            engrams = [
                _make_engram(f"baseline_engram_{i}", f"2026-06-03T20:00:0{i}+00:00")
                for i in range(3)
            ]
            _write_history(brain, engrams)
            _ensure_populated(str(brain))

            db_path = brain / "memories.db"
            history_path = brain / "engrams" / "history.jsonl"
            db_mtime_post_build = db_path.stat().st_mtime

            # Append + backdate history.mtime (rsync-preserved-mtime simulation)
            t_new_iso = "2026-06-03T20:00:09+00:00"
            with open(history_path, "a") as f:
                f.write(json.dumps(_make_engram("rsync_mtime_engram_abc", t_new_iso)) + "\n")
            os.utime(history_path, (db_mtime_post_build - 100, db_mtime_post_build - 100))

            # Setup invariant: mtime says NOT stale; row-count says stale
            self.assertLess(history_path.stat().st_mtime, db_path.stat().st_mtime)

            results = _do_recall_query(
                query="rsync_mtime_engram_abc",
                limit=10,
                kind=None,
                tags=None,
                since=None,
                source_filter=None,
                brain_path_arg=str(brain),
            )

            self.assertEqual(
                len(results), 1,
                "Row-count check must trigger rebuild when history has more "
                "lines than projected, even if mtime doesn't agree. "
                "v1 only checked mtime; v2 adds row-count safety net."
            )
            self.assertIn("rsync_mtime_engram_abc", results[0]["text"])


class TestEnsurePopulatedNoRebuildWhenInSync(unittest.TestCase):
    """Guard against false-positive rebuilds (would cost ~500ms per call on 8K history)."""

    def test_no_rebuild_on_clean_in_sync_state(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            from nucleus_wedge.recall_cmd import _ensure_populated

            _write_history(brain, [_make_engram("clean_state_engram", "2026-06-03T20:00:00+00:00")])
            _ensure_populated(str(brain))

            db_path = brain / "memories.db"
            db_mtime_after_first_build = db_path.stat().st_mtime

            # Backdate history so it's older than db (no writes since build)
            history_path = brain / "engrams" / "history.jsonl"
            os.utime(history_path, (db_mtime_after_first_build - 60, db_mtime_after_first_build - 60))

            time.sleep(0.01)
            _ensure_populated(str(brain))

            self.assertAlmostEqual(
                db_path.stat().st_mtime, db_mtime_after_first_build,
                delta=0.001,
                msg="No-write state must NOT rebuild (db.mtime unchanged). "
                    "If changed: false-positive rebuild firing — costly on hot path."
            )


if __name__ == "__main__":
    unittest.main()
