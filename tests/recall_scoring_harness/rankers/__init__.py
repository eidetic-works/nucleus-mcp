"""Pluggable ranker modules for the scoring harness.

Each ranker module exposes `rank(query: str, limit: int) -> list[dict]` where
each dict has at least `key` and `score`. Higher score = more relevant.

Baseline: baseline_bm25 (current production ranking; pure BM25 over all rows)
Candidates (PR_B follow-up):
- candidate_bm25_time_decay
- candidate_time_bucket_boost
- candidate_per_kind_weighting
"""
