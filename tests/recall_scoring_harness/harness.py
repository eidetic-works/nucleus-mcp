"""Scoring harness runner for nucleus_wedge recall ranking experiments.

Loads a corpus of (query, expected_top_keys) fixtures + measures ranker
performance via recall@k. Pluggable ranker interface lets us A/B compare
baseline vs candidate fix directions.

Run:
  python -m tests.recall_scoring_harness.harness \\
    --corpus tests/recall_scoring_harness/corpus/synthetic_seed.json \\
    --ranker baseline_bm25
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass
class Fixture:
    fixture_id: str
    query: str
    expected_top_keys: list[str]
    description: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Fixture":
        return cls(
            fixture_id=d["fixture_id"],
            query=d["query"],
            expected_top_keys=d["expected_top_keys"],
            description=d.get("description", ""),
        )


@dataclass
class ScoringResult:
    fixture_id: str
    query: str
    expected_top_keys: list[str]
    actual_top_keys: list[str]
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    latency_ms: float
    # Unsupervised metric (no hand-grading needed): fraction of top-5 results
    # that are <7d old. Direct proxy for #440 desideratum (temporal-relevance).
    # Candidates that better surface recent content score higher.
    recent_fraction_in_top_5: float = 0.0


def recall_at_k(expected: list[str], actual: list[str], k: int) -> float:
    """Fraction of expected keys present in actual top-k.

    Returns 0.0 if expected is empty (avoids div-by-zero). Returns 1.0 if all
    expected appear in top-k. Returns partial-fraction if some appear.
    """
    if not expected:
        return 0.0
    actual_topk = set(actual[:k])
    hits = sum(1 for e in expected if e in actual_topk)
    return hits / len(expected)


def load_corpus(corpus_path: Path) -> list[Fixture]:
    with corpus_path.open() as f:
        data = json.load(f)
    return [Fixture.from_dict(fx) for fx in data["fixtures"]]


def load_ranker(ranker_name: str) -> Callable[[str, int], list[dict]]:
    """Load a ranker by name from rankers/ module.

    Each ranker module exposes `rank(query: str, limit: int) -> list[dict]`
    where each dict has at least `key` and `score`. Higher score = more relevant.

    Tries package-style import first; falls back to direct sibling import
    when run as standalone script (no parent package).
    """
    try:
        module = importlib.import_module(f"tests.recall_scoring_harness.rankers.{ranker_name}")
    except ModuleNotFoundError:
        # Fallback for direct-run: add rankers/ to sys.path + import bare module name
        rankers_dir = Path(__file__).resolve().parent / "rankers"
        if str(rankers_dir) not in sys.path:
            sys.path.insert(0, str(rankers_dir))
        module = importlib.import_module(ranker_name)
    return module.rank


def _is_recent(ts_str: str, now: datetime, days: float = 7.0) -> bool:
    """Returns True if timestamp is within `days` of now."""
    if not ts_str:
        return False
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds() <= days * 86400.0
    except (ValueError, AttributeError):
        return False


def score_fixture(fixture: Fixture, ranker: Callable, k_values: list[int] = [1, 3, 5]) -> ScoringResult:
    t0 = time.perf_counter()
    actual = ranker(fixture.query, max(k_values))
    latency_ms = (time.perf_counter() - t0) * 1000

    actual_keys = [r["key"] for r in actual]

    # Unsupervised recent-fraction metric (no hand-grading needed).
    now = datetime.now(timezone.utc)
    top_5 = actual[:5]
    recent_count = sum(1 for r in top_5 if _is_recent(r.get("timestamp", ""), now))
    recent_fraction = (recent_count / len(top_5)) if top_5 else 0.0

    return ScoringResult(
        fixture_id=fixture.fixture_id,
        query=fixture.query,
        expected_top_keys=fixture.expected_top_keys,
        actual_top_keys=actual_keys,
        recall_at_1=recall_at_k(fixture.expected_top_keys, actual_keys, 1),
        recall_at_3=recall_at_k(fixture.expected_top_keys, actual_keys, 3),
        recall_at_5=recall_at_k(fixture.expected_top_keys, actual_keys, 5),
        latency_ms=latency_ms,
        recent_fraction_in_top_5=recent_fraction,
    )


def aggregate(results: list[ScoringResult]) -> dict[str, Any]:
    if not results:
        return {"fixture_count": 0}
    n = len(results)
    return {
        "fixture_count": n,
        "mean_recall_at_1": sum(r.recall_at_1 for r in results) / n,
        "mean_recall_at_3": sum(r.recall_at_3 for r in results) / n,
        "mean_recall_at_5": sum(r.recall_at_5 for r in results) / n,
        "mean_latency_ms": sum(r.latency_ms for r in results) / n,
        "fixtures_with_zero_recall_at_5": sum(1 for r in results if r.recall_at_5 == 0.0),
        "mean_recent_fraction_in_top_5": sum(r.recent_fraction_in_top_5 for r in results) / n,
    }


def run_corpus(corpus_path: Path, ranker_name: str) -> dict[str, Any]:
    fixtures = load_corpus(corpus_path)
    ranker = load_ranker(ranker_name)
    results = [score_fixture(fx, ranker) for fx in fixtures]
    return {
        "corpus": str(corpus_path),
        "ranker": ranker_name,
        "results": [r.__dict__ for r in results],
        "summary": aggregate(results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Wedge recall scoring harness")
    parser.add_argument("--corpus", type=Path, required=True, help="JSON corpus of fixtures")
    parser.add_argument("--ranker", default="baseline_bm25",
                        help="Ranker name (matches tests/recall_scoring_harness/rankers/<name>.py)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output (default: human summary)")
    args = parser.parse_args()

    report = run_corpus(args.corpus, args.ranker)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        s = report["summary"]
        print(f"corpus:    {report['corpus']}")
        print(f"ranker:    {report['ranker']}")
        print(f"fixtures:  {s['fixture_count']}")
        print(f"recall@1:  {s.get('mean_recall_at_1', 0):.3f}")
        print(f"recall@3:  {s.get('mean_recall_at_3', 0):.3f}")
        print(f"recall@5:  {s.get('mean_recall_at_5', 0):.3f}")
        print(f"latency:   {s.get('mean_latency_ms', 0):.1f} ms")
        print(f"zero-hit fixtures: {s.get('fixtures_with_zero_recall_at_5', 0)}/{s['fixture_count']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
