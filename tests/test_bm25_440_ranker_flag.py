"""Regression tests for #440 PR_C: NUCLEUS_WEDGE_RANKER env-flag dispatch.

Verifies:
- Default flag = baseline (no re-rank; preserves pre-#440 behavior)
- Recognized values dispatch to correct re-ranker
- Unknown value falls back to baseline (defensive)
- Re-rank order differs from baseline when flag is set
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

PKG_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PKG_ROOT))


def _seed_brain(brain: Path, engrams: list[dict]) -> None:
    (brain / "engrams").mkdir(parents=True, exist_ok=True)
    history = brain / "engrams" / "history.jsonl"
    with open(history, "w") as f:
        for e in engrams:
            f.write(json.dumps(e) + "\n")


def _engram(value: str, ts_iso: str) -> dict:
    return {
        "key": f"k_{value[:20]}",
        "timestamp": ts_iso,
        "snapshot": {
            "value": value,
            "context": "[note: test]",
            "timestamp": ts_iso,
            "source_agent": "test_440_prc",
        },
    }


class TestRankerFlagDispatch(unittest.TestCase):
    """Verify NUCLEUS_WEDGE_RANKER env-flag selects correct re-ranker."""

    def setUp(self) -> None:
        self._old_env = os.environ.pop("NUCLEUS_WEDGE_RANKER", None)

    def tearDown(self) -> None:
        os.environ.pop("NUCLEUS_WEDGE_RANKER", None)
        if self._old_env is not None:
            os.environ["NUCLEUS_WEDGE_RANKER"] = self._old_env

    def _run_query(self, brain: Path, query: str, ranker_flag) -> list[dict]:
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
        if ranker_flag is not None:
            os.environ["NUCLEUS_WEDGE_RANKER"] = ranker_flag
        else:
            os.environ.pop("NUCLEUS_WEDGE_RANKER", None)

        from nucleus_wedge import bm25 as _bm25
        from nucleus_wedge.store import Store

        store = Store(Store.brain_path(None))
        return _bm25.search(store, query=query, limit=5)

    def test_default_flag_is_baseline_unchanged_pre_440_behavior(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            now = datetime.now(timezone.utc)
            _seed_brain(brain, [
                _engram("foo bar baz qux foo bar baz qux", (now - timedelta(days=200)).isoformat()),
                _engram("foo single", now.isoformat()),
            ])
            results = self._run_query(brain, "foo bar baz qux", ranker_flag=None)
            self.assertGreater(len(results), 0)
            # Baseline: high-token-density old content wins on BM25
            self.assertIn("foo bar baz qux", results[0]["content"])

    def test_time_bucket_boost_flag_promotes_recent_content(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            now = datetime.now(timezone.utc)
            # Two engrams with COMPARABLE BM25 scores (same token frequency)
            # but different ages. With baseline (BM25 only), the tied score
            # leaves order indeterminate. With time_bucket_boost (recent × 3.0,
            # older × 1.0), recent must win.
            _seed_brain(brain, [
                _engram("foo bar baz qux", (now - timedelta(days=200)).isoformat()),
                _engram("foo bar baz qux", now.isoformat()),
            ])
            results = self._run_query(brain, "foo bar baz qux", ranker_flag="time_bucket_boost")
            self.assertGreaterEqual(len(results), 2)
            timestamps_in_order = [r.get("timestamp", "") for r in results]
            # Recent (today) should be in position 0 since boost 3.0 > older boost 1.0
            top_ts = results[0].get("timestamp", "")
            self.assertIn(now.strftime("%Y-%m-%d"), top_ts,
                          f"time_bucket_boost should promote recent content; got order {timestamps_in_order}")

    def test_unknown_flag_falls_back_to_baseline(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            now = datetime.now(timezone.utc)
            _seed_brain(brain, [
                _engram("alpha beta gamma", now.isoformat()),
            ])
            results = self._run_query(brain, "alpha beta gamma", ranker_flag="nonexistent_ranker_xyz")
            self.assertGreater(len(results), 0,
                               "Unknown ranker flag must defensively fall back to baseline, not crash.")

    def test_ranker_name_recorded_in_recall_timings(self):
        with TemporaryDirectory() as tmp:
            brain = Path(tmp)
            _seed_brain(brain, [_engram("observability test", datetime.now(timezone.utc).isoformat())])
            self._run_query(brain, "observability test", ranker_flag="time_bucket_boost")

            metrics_log = brain / "metrics" / "recall_timings.jsonl"
            self.assertTrue(metrics_log.exists())
            with open(metrics_log) as f:
                last_line = f.readlines()[-1]
            entry = json.loads(last_line)
            self.assertEqual(entry.get("ranker"), "time_bucket_boost")


if __name__ == "__main__":
    unittest.main()
