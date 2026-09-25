"""Empirical scoring harness for nucleus_wedge recall ranking.

Per issue #440 (FTS5/BM25 temporal-relevance): current bm25.search returns
results ranked purely by BM25 score with NO temporal weighting. Surfaced via
cc-main + cc-peer dogfood — recall_activity returns 6-week-old generic content
above week-old relevant content for highly-specific queries.

3 v1 fix directions to compare empirically (per cc-main framing in #440):
1. BM25 + time-decay: score * exp(-age_days * decay_rate)
2. Time-bucket-boost post-filter: re-rank top-K by recency tier (last-7d × 3,
   last-30d × 1.5, older × 1)
3. Per-kind weighting: kind=activity > kind=note for same BM25 score

PR_A (this PR): harness skeleton + 5 procedurally-generated fixtures + recall@k
metric + baseline measurement against current BM25-only ranking.

PR_B (follow-up): implement chosen v1 fix based on harness data + corpus
expansion (hand-graded fixtures from operator's actual dogfood pain points).
"""
