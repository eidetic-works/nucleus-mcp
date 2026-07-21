"""Agent OS — Stage 1 unlock: the working-set PAGER (selective memory recall).

The membrane principle (``AGENT_OS_MEMBRANE.md`` §2): *the agent's context window
is its RAM; recall is its virtual memory; the membrane is the pager.* Stage-0's
``recall_and_inject`` dumped the top-N raw recall rows into the agent's context
— unselective on the real brain (the "blur": ~5 near-misses, not the one that
matters). This module is the fix: a **policy** that scores each candidate memory
by **relevance × recency × verified-trust**, then loads only what fits a context
budget, best-first.

Gated behind ``NUCLEUS_AGENT_OS_PAGER`` (default OFF). When OFF, ``boot.py``'s
``recall_and_inject`` is byte-identical to the pre-pager path; this module is
imported lazily and only inside the flag-ON branch.

Scoring reuses ``nucleus_wedge.bm25.rank_candidates`` for the relevance signal
(BM25 over the candidate texts vs. the query) — the same scorer the wedge's own
hybrid recall uses, so there is no reinvention and no ranking drift. Recency and
verified-trust are layered on top as multiplicative factors so the policy is a
single, inspectable formula:

    score = bm25_relevance * recency_factor * trust_factor

where:
  - ``bm25_relevance``  = the BM25 score from ``rank_candidates`` (≥0 for a match;
    the wedge tokenizer is shared). Normalized to ≥0 so the multiplicative form
    is well-defined even on small/sparse corpora where raw BM25 can be 0.
  - ``recency_factor``  = ``1 + _RECENCY_DECAY * exp(-age_days / _RECENCY_TAU)``
    — newer memories get a bounded boost; the boost decays to 1.0 as age grows.
    Additive-on-top-of-multiplicative was considered and rejected: BM25 here is
    non-negative (matches only), so multiplication does not invert the ranking.
  - ``trust_factor``    = ``_TRUST_BOOST`` (default 1.25) if the candidate row
    carries a verified/HMAC/signed signal (any of ``verified``/``hmac``/
    ``signature`` keys truthy, or a ``source``/``tags`` string containing
    ``verified``/``hmac``/``signed``); else ``1.0``. The wedge store does not
    yet write such a field, so today every row is 1.0 — the factor is a defensive
    hook for the Stage-1 referee (MEMBRANE §3) so verified trajectories rank
    above unverified ones the moment the referee starts labeling.

The pager then walks candidates best-first and emits only those whose rendered
``- {text}`` line fits within ``budget_chars``; once the budget is exhausted the
rest are evicted (the working-set discipline — load the right pages, evict the
rest).
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

PAGER_FLAG = "NUCLEUS_AGENT_OS_PAGER"

_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Recency: a 30-day half-life, matching the wedge's own ``bm25_time_decay``
# ranker (``bm25.py`` _DECAY_HALF_LIFE_DAYS). The factor is bounded: a memory
# written "now" gets 1 + _RECENCY_DECAY = 1.5; a 30-day-old memory gets
# 1 + 0.5/e ≈ 1.18; an old memory decays toward 1.0. Bounded so recency can
# promote but never single-handedly override a strong relevance gap.
_RECENCY_TAU_DAYS = 30.0
_RECENCY_DECAY = 0.5

# Verified-trust: a 1.25x boost for HMAC/verified/signed records. Conservative
# so a verified-but-loosely-related record does not leapfrog an exact-topic
# unverified one (the relevance signal stays dominant). Defensive — the wedge
# store does not yet emit these fields; this is the hook for the Stage-1 referee.
_TRUST_BOOST = 1.25
_TRUST_KEYS = ("verified", "hmac", "signature")
_TRUST_TAG_MARKERS = ("verified", "hmac", "signed")

# Default context budget for the injected memory block (chars). Generous enough
# for ~5-8 typical memory lines, tight enough to force eviction on a noisy brain.
_DEFAULT_BUDGET_CHARS = 2000


def pager_flag_enabled() -> bool:
    """True iff ``NUCLEUS_AGENT_OS_PAGER`` is set truthy (default False)."""
    return os.environ.get(PAGER_FLAG, "").strip().lower() in _TRUTHY


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t
    except (ValueError, TypeError):
        return None


def _recency_factor(created_at: Optional[str]) -> float:
    """Bounded multiplicative recency boost in ``[1.0, 1 + _RECENCY_DECAY]``."""
    ts = _parse_ts(created_at)
    if ts is None:
        return 1.0
    age_days = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0)
    return 1.0 + _RECENCY_DECAY * math.exp(-age_days / _RECENCY_TAU_DAYS)


def _trust_factor(row: dict) -> float:
    """1.25x if the row carries a verified/HMAC/signed signal, else 1.0.

    Checked defensively in three places: (a) explicit truthy keys
    (``verified``/``hmac``/``signature``), (b) a ``source`` string containing a
    trust marker, (c) a ``tags`` string containing a trust marker. The wedge
    store does not yet write any of these, so today this is always 1.0 — the hook
    is here for the Stage-1 referee (MEMBRANE §3) so verified trajectories rank
    above unverified ones the moment the referee starts labeling.
    """
    for k in _TRUST_KEYS:
        if row.get(k):
            # truthy (bool True, non-empty string, non-zero number) → verified
            return _TRUST_BOOST
    for field in ("source", "tags"):
        val = row.get(field)
        if isinstance(val, str):
            low = val.lower()
            if any(m in low for m in _TRUST_TAG_MARKERS):
                return _TRUST_BOOST
    return 1.0


def _bm25_relevance_scores(
    candidates: List[dict], query: str
) -> List[float]:
    """Return a non-negative BM25 relevance score per candidate, in input order.

    Reuses ``nucleus_wedge.bm25.rank_candidates``'s tokenizer + scorer so the
    relevance signal is identical to the wedge's own hybrid recall (no
    reinvention, no ranking drift). ``rank_candidates`` returns reordered dicts
    without scores; to get the raw per-candidate score we replicate its scoring
    core (BM25Okapi over the same ``_tokenize``) — this is a thin reuse of the
    wedge's own primitives, not a parallel scorer.
    """
    if not candidates:
        return []
    from nucleus_wedge.bm25 import _tokenize  # reuse the wedge tokenizer

    try:
        from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
    except Exception:  # noqa: BLE001 — fall back to overlap if rank_bm25 missing
        q_tokens = set(_tokenize(query))
        return [
            float(len(q_tokens & set(_tokenize(str(c.get("text") or "")))))
            for c in candidates
        ]

    corpus = [_tokenize(str(c.get("text") or "")) for c in candidates]
    q_tokens = _tokenize(query)
    if not q_tokens:
        return [0.0] * len(candidates)
    bm25 = BM25Okapi(corpus)
    raw = bm25.get_scores(q_tokens)
    # Normalize to ≥0: raw BM25 can be 0 (no overlap) but not negative on a
    # match; clamp the floor at 0 so the multiplicative policy is well-defined.
    return [max(0.0, float(s)) for s in raw]


def _score(row: dict, relevance: float, created_at: Optional[str]) -> float:
    """The pager policy: relevance × recency × verified-trust."""
    return relevance * _recency_factor(created_at) * _trust_factor(row)


def page(
    query: str,
    candidates: List[dict],
    budget_chars: int = _DEFAULT_BUDGET_CHARS,
    *,
    text_key: str = "text",
    ts_key: str = "created_at",
    limit: Optional[int] = None,
) -> List[dict]:
    """Score candidates by relevance × recency × verified-trust and return the
    best-first subset that fits within ``budget_chars``.

    Each candidate is a recall row (``{text, tags, created_at, source, kind}``).
    The returned list is the working set: candidates ranked best-first, then
    packed greedily until the rendered ``- {text}`` lines would exceed
    ``budget_chars``; the rest are evicted. ``limit`` (if given) is an additional
    hard cap on the number of returned rows.

    The returned dicts are the caller's original candidate dicts (no ``score``
    key is added), so the output shape matches the pre-pager ``recall_and_inject``
    contract — the pager is a pure reselection/reorder, not a row transform.
    """
    if not candidates:
        return []
    rels = _bm25_relevance_scores(candidates, query)
    scored = [
        (i, _score(c, rels[i], c.get(ts_key))) for i, c in enumerate(candidates)
    ]
    # Best-first. Tie-break by original order (stable) so equal-score candidates
    # keep the recall engine's recency order.
    scored.sort(key=lambda t: (-t[1], t[0]))

    budget = max(0, int(budget_chars))
    out: List[dict] = []
    used = 0
    for idx, _score_val in scored:
        if limit is not None and len(out) >= int(limit):
            break
        text = str(candidates[idx].get(text_key) or "")
        # Rendered line shape matches boot.py's injected block: "- {text}\n".
        line_len = len("- ") + len(text) + 1
        if out and used + line_len > budget:
            break
        if not out and line_len > budget:
            # A single line that blows the budget: still take it (best-first) so
            # the working set is never empty when candidates exist; subsequent
            # lines are then budget-gated as normal.
            out.append(candidates[idx])
            used += line_len
            continue
        out.append(candidates[idx])
        used += line_len
    return out
