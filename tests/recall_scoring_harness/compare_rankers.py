"""A/B reporter: run multiple rankers against same corpus + diff results.

Usage:
  python -m tests.recall_scoring_harness.compare_rankers \\
    --corpus tests/recall_scoring_harness/corpus/synthetic_seed.json \\
    --rankers baseline_bm25 candidate_bm25_time_decay candidate_time_bucket_boost candidate_per_kind_weighting

Output: per-ranker recall@k summary + winner-per-metric.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import sibling harness module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import run_corpus  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B compare wedge recall rankers")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--rankers", nargs="+", required=True,
                        help="Ranker names to compare (each = module under rankers/)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reports = {}
    for ranker_name in args.rankers:
        reports[ranker_name] = run_corpus(args.corpus, ranker_name)

    if args.json:
        print(json.dumps(reports, indent=2))
        return 0

    # Human summary table
    print(f"corpus: {args.corpus}")
    print(f"fixtures: {reports[args.rankers[0]]['summary']['fixture_count']}")
    print()
    header = f"{'ranker':<35} {'rec@1':>7} {'rec@3':>7} {'rec@5':>7} {'recent@5':>10} {'latency_ms':>12}"
    print(header)
    print("-" * len(header))
    for ranker_name, report in reports.items():
        s = report["summary"]
        row = (
            f"{ranker_name:<35} "
            f"{s.get('mean_recall_at_1', 0):>7.3f} "
            f"{s.get('mean_recall_at_3', 0):>7.3f} "
            f"{s.get('mean_recall_at_5', 0):>7.3f} "
            f"{s.get('mean_recent_fraction_in_top_5', 0):>10.3f} "
            f"{s.get('mean_latency_ms', 0):>12.1f}"
        )
        print(row)

    # Winners per metric
    print()
    print("Winners:")
    for metric, sort_max in [
        ("mean_recall_at_1", True),
        ("mean_recall_at_3", True),
        ("mean_recall_at_5", True),
        ("mean_recent_fraction_in_top_5", True),
    ]:
        winner = max(args.rankers, key=lambda r: reports[r]["summary"].get(metric, 0))
        print(f"  {metric:<32} → {winner} ({reports[winner]['summary'].get(metric, 0):.3f})")
    latency_winner = min(args.rankers, key=lambda r: reports[r]["summary"].get("mean_latency_ms", float("inf")))
    print(f"  {'mean_latency_ms':<32} → {latency_winner} ({reports[latency_winner]['summary']['mean_latency_ms']:.1f} ms)")
    print()
    print("Note: recall@k requires hand-graded expected_top_keys (most fixtures empty in operator-pain corpus).")
    print("'recent@5' (mean_recent_fraction_in_top_5) is unsupervised — directly measures #440 temporal-relevance desideratum.")
    print("Higher recent@5 = more candidate-content from last 7 days surfaced in top-5 = closer to fixing #440.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
