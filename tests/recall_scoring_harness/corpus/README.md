# Recall scoring harness — corpus

Per issue #440 v1 framing: empirical scoring before committing to one of 3 fix directions.

## Fixture format

Each fixture in `synthetic_seed.json` (or any corpus file you author):

```json
{
  "version": "1.0.0",
  "fixtures": [
    {
      "fixture_id": "fx_001",
      "query": "scrubber consolidation HARD_BLOCK_FLOOR",
      "expected_top_keys": ["remember_20260603T...", "remember_20260602T..."],
      "description": "Highly-specific scrubber-domain query; current BM25 returns 6-week-old decomposer content (Loop #2 from cc-peer 2026-06-02 pre-review-consumption)"
    }
  ]
}
```

- `fixture_id`: unique identifier within corpus
- `query`: the recall query string (passed to bm25.search verbatim)
- `expected_top_keys`: list of `key` field values from memories table that SHOULD appear in top-5 for this query (hand-curated by author who knows the corpus)
- `description`: optional human-readable rationale

## How to author fixtures (operator-side guidance)

### Quick procedural fixtures
Synthetic queries where the expected_top_keys are derivable algorithmically:
- "find activity engrams from today" → query "activity 2026-06-03"; expected = all today's activity-kind rows
- "find feedback from yesterday" → query "feedback yesterday"; expected = yesterday's feedback-kind rows

These exercise the harness mechanics + give a baseline number, but they don't capture the REAL ranking pain.

### Hand-graded "operator-pain" fixtures
The valuable corpus: queries that surfaced operator pain in dogfood loops:
- cc-peer 2026-06-02: `"scrubber consolidation HARD_BLOCK_FLOOR brand_identity_routing"` returned 6-week-old decomposer content
- cc-main 2026-06-02 04:10Z: `"FTS5 temporal-relevance"` returned 2-month-old generic task
- cc-main Loop #6 2026-06-03 08:05Z: `"role=main activity since=24h"` returned only ≤22h-old items despite 4 today's writes

For each pain point, author should:
1. Capture the EXACT query
2. List the keys of memories that SHOULD have surfaced (find via `recall_activity` with broader filters, OR via direct sqlite query against memories.db)
3. Add a fixture with those expected keys
4. Run harness against baseline_bm25 → confirm recall@5 = 0 (matches pain)
5. PR_B's candidate ranker fixes should bring those to recall@5 > 0

### Synthetic-only mode (no operator brain)
The harness also supports running against a synthetic in-memory store (see `synthetic_seed.json`):
- Fixtures specify their own corpus content via `_seed_rows` field
- Harness builds a temporary brain dir with those rows + runs ranker against it
- No operator data leaks into test runs

## Running

```bash
# Baseline against synthetic seed
python -m tests.recall_scoring_harness.harness \
  --corpus tests/recall_scoring_harness/corpus/synthetic_seed.json \
  --ranker baseline_bm25

# Baseline against operator's actual brain (operator-keyboard; CAUTION: real data)
NUCLEUS_BRAIN_PATH=~/.eidetic/.brain python -m tests.recall_scoring_harness.harness \
  --corpus tests/recall_scoring_harness/corpus/operator_pain_fixtures.json \
  --ranker baseline_bm25

# JSON output for diffing across rankers
python -m tests.recall_scoring_harness.harness --corpus ... --ranker baseline_bm25 --json > baseline.json
python -m tests.recall_scoring_harness.harness --corpus ... --ranker candidate_time_decay --json > time_decay.json
diff baseline.json time_decay.json
```

## What this PR does NOT do (deferred to PR_B)

- Candidate rankers (`candidate_bm25_time_decay`, `candidate_time_bucket_boost`, `candidate_per_kind_weighting`)
- Operator-pain corpus (the hand-graded fixtures from dogfood loops)
- A/B comparison reporter (juxtaposes baseline vs candidates per-fixture)
- CI gate on recall@5 regression
