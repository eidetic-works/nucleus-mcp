"""Skill Extractor — Cluster intents from loop turns, score skill candidates.

Reads LoopTurn data from ArchivePipeline.get_turns(), clusters by semantic
similarity (keyword Jaccard with optional Ollama embeddings), and scores
each cluster as a potential reusable skill.

Zero new dependencies. Ollama embeddings optional (keyword fallback).
"""

import re
import math
import json
import logging
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("nucleus.skill_extractor")

# -- Constants --

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "to", "and", "or", "of", "in", "for",
    "this", "that", "it", "my", "me", "do", "can", "please",
    "i", "we", "you", "with", "on", "at", "be", "have", "has",
    "was", "were", "been", "will", "would", "could", "should",
    "not", "but", "if", "then", "so", "just", "also", "some",
    "all", "any", "each", "from", "by", "as", "are", "am",
})

_PATH_PATTERN = re.compile(r"[/\\]\w{1,4}[/\\]")  # file paths
_CAMEL_SNAKE = re.compile(r"[a-z]+[A-Z][a-z]+|[a-z]+_[a-z]+_[a-z]+")  # code identifiers
_PII_PATH = re.compile(r"/Users/\w+")  # macOS user home paths
_HOSTNAME = re.compile(r"\b\w+-\w+-air\b|\b\w+s-macbook\b", re.IGNORECASE)  # hostnames

# -- Noise filtering (guards against raw first-user-message[:100] garbage) --

_NOISE_INTENTS = frozenset({
    "yes", "ok", "no", "done", "hi", "hey", "hello", "sure", "yep", "nope",
    "retry", "continue", "proceed", "wait", "chat", "thanks", "thank you",
    "go ahead", "next", "stop", "quit", "exit", "help", "back",
})
_META_PATTERN = re.compile(r"<[a-z_-]+>|^\s*$")
_SESSION_CONTINUATION = re.compile(r"^this session is being continued", re.IGNORECASE)
_MOCK_PATTERNS = re.compile(r"srv-\d+|task_qa_mock|deploy_success|ESCALATED:\s*Testing")
_CODE_BLOCK = re.compile(r"^```")
_TERMINAL_NOISE = re.compile(
    r"^(last login:|source .*/bin/activate|\w+@\w+-\w+|\$\s|%\s|#\s)",
    re.IGNORECASE,
)
_CONVERSATIONAL_FILLER = re.compile(
    r"^(keep going|what else|do you want|lets think|let me know|sounds good|"
    r"yes and|no but|ok so|ok let|sure let|go ahead)",
    re.IGNORECASE,
)
_MIN_INTENT_WORDS = 4


def _is_noise_intent(intent: str) -> bool:
    """Filter out noise intents that contaminate clustering.

    Catches: single-word acknowledgments, HTML/tool markers, session
    continuations, mock/test fixture data, code blocks, terminal output,
    and conversational filler too vague to represent a reusable skill.
    """
    stripped = intent.strip().lower()
    if not stripped:
        return True
    if stripped in _NOISE_INTENTS:
        return True
    if _META_PATTERN.search(stripped):
        return True
    if len(stripped.split()) < _MIN_INTENT_WORDS:
        return True
    if _SESSION_CONTINUATION.search(stripped):
        return True
    if _MOCK_PATTERNS.search(intent):  # case-sensitive for ESCALATED
        return True
    if _CODE_BLOCK.match(stripped):
        return True
    if _TERMINAL_NOISE.search(stripped):
        return True
    if _CONVERSATIONAL_FILLER.match(stripped):
        return True
    return False


# -- Intent distillation (extract meaningful intent from conversation data) --

_TEMPLATE_OUTCOME = re.compile(r"^(Claude Code session|Gemini session|Claude session)")


def _distill_intent(turn: dict) -> str:
    """Extract a meaningful intent from conversation data.

    The ingestion pipeline stores first-user-message[:100] as intent,
    which is often noise. Scan the conversation for the first substantive
    user message that looks like a real task/request.
    """
    conv = turn.get("conversation", [])
    if not conv:
        return turn.get("intent", "")

    for msg in conv:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "").strip()
        if not content or len(content) < 20:
            continue
        # Skip noise patterns
        if _is_noise_intent(content[:100]):
            continue
        return content[:200]

    return turn.get("intent", "")


def _distill_outcome(turn: dict) -> str:
    """Extract a meaningful outcome from conversation or stored outcome.

    Template outcomes ("Claude Code session X chunk N/M") carry no signal.
    Fall back to the last substantive assistant message.
    """
    outcome = turn.get("outcome", "")
    if outcome and not _TEMPLATE_OUTCOME.match(outcome):
        return outcome

    conv = turn.get("conversation", [])
    for msg in reversed(conv):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "").strip()
        if len(content) > 30:
            return content[:200]

    return outcome


# -- Heuristic quality grading (overrides copper default at extraction time) --

def _heuristic_quality(turn: dict) -> str:
    """Infer quality grade from turn signals when all turns are copper.

    Signals: tool count, intent length, conversation depth, presence of
    Edit/Write tools (indicates actual code changes, not just reading).
    """
    score = 0
    tools = turn.get("tools_used", [])
    if len(tools) >= 3:
        score += 1
    if len(turn.get("intent", "")) > 50:
        score += 1
    if len(turn.get("conversation", [])) >= 6:
        score += 1
    if any(t in tools for t in ("Edit", "Write")):
        score += 1
    if score >= 4:
        return "platinum"
    if score >= 3:
        return "gold"
    if score >= 2:
        return "silver"
    return "copper"

# -- Embedding (optional, inlined from brain_rag.py) --

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"


def _try_embed(text: str) -> Optional[List[float]]:
    """Embed via local Ollama. Returns None if unavailable."""
    try:
        payload = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        pass
    return None


def _cosine_sim(a: List[float], b: List[float]) -> float:
    """Dot-product cosine similarity. No numpy needed for 1024-dim."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# -- Clustering --

def _tokenize_intent(intent: str) -> Set[str]:
    """Lowercase, strip PII/paths/punctuation, remove stopwords."""
    text = _PII_PATH.sub(" ", intent)     # Strip user paths (before lowering)
    text = _HOSTNAME.sub(" ", text)       # Strip hostnames
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(_PATH_PATTERN, " ", text)
    tokens = set(text.split()) - _STOPWORDS
    return {t for t in tokens if len(t) > 2}  # >2 kills "ai", "ok", "no" etc


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity between token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class _UnionFind:
    """Simple union-find for single-linkage clustering. ~20 lines."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


def cluster_intents(
    turns: List[dict],
    min_cluster_size: int = 3,
    use_embeddings: bool = True,
    similarity_threshold: float = 0.45,  # Jaccard
    embed_threshold: float = 0.80,       # cosine
) -> List[dict]:
    """Cluster conversation turn intents into skill domains.

    Strategy:
        1. Try embeddings if use_embeddings=True and Ollama is reachable
        2. Fall back to keyword Jaccard similarity
        3. Single-linkage clustering via union-find
        4. Filter clusters below min_cluster_size
        5. Auto-label from most frequent non-stopword tokens (simple TF-IDF)

    Returns sorted by size (largest first). Each cluster:
        {
            "domain": "test-writing",
            "intents": ["write tests for...", "add test coverage...", ...],
            "turn_ids": ["turn-abc123", ...],
            "tools_used": {"Edit": 15, "Bash": 12, ...},
            "turns": [<full turn dicts>],
            "size": 23,
            "avg_quality": "silver",
        }
    """
    if not turns:
        return []

    # Extract intents via distillation, filter noise, apply heuristic quality
    filtered_turns = []
    intents = []
    for t in turns:
        intent = _distill_intent(t)
        if _is_noise_intent(intent[:100]):
            continue
        # Override copper grade with heuristic if all turns are copper
        if t.get("quality_grade", "copper") == "copper":
            t = {**t, "quality_grade": _heuristic_quality(t)}
        # Store distilled intent and outcome back into turn for downstream use
        t = {**t, "intent": intent, "outcome": _distill_outcome(t)}
        filtered_turns.append(t)
        intents.append(intent)

    turns = filtered_turns
    n = len(intents)
    if n == 0:
        return []

    # Tokenize for Jaccard
    token_sets = [_tokenize_intent(intent) for intent in intents]

    # Try embeddings
    embeddings: Optional[List[List[float]]] = None
    if use_embeddings and n > 0:
        test = _try_embed("test")
        if test is not None:
            embeddings = []
            for intent in intents:
                emb = _try_embed(intent)
                if emb is None:
                    embeddings = None
                    break
                embeddings.append(emb)

    # Build similarity and cluster
    uf = _UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if embeddings is not None:
                sim = _cosine_sim(embeddings[i], embeddings[j])
                if sim >= embed_threshold:
                    uf.union(i, j)
            else:
                sim = _jaccard(token_sets[i], token_sets[j])
                if sim >= similarity_threshold:
                    uf.union(i, j)

    # Collect clusters
    groups: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)

    # Collect valid cluster index lists and per-cluster token frequencies
    valid_clusters: List[List[int]] = []
    cluster_token_freqs: List[Counter] = []
    doc_freq: Counter = Counter()

    for indices in groups.values():
        if len(indices) < min_cluster_size:
            continue
        valid_clusters.append(indices)
        cluster_tokens: Counter = Counter()
        for idx in indices:
            cluster_tokens.update(token_sets[idx])
        cluster_token_freqs.append(cluster_tokens)
        for token in cluster_tokens:
            doc_freq[token] += 1

    num_clusters = max(len(valid_clusters), 1)

    # Build cluster dicts with TF-IDF domain labels
    grade_map = {"copper": 0, "silver": 1, "gold": 2, "platinum": 3}
    reverse_map = {0: "copper", 1: "silver", 2: "gold", 3: "platinum"}
    clusters = []

    for ci, indices in enumerate(valid_clusters):
        cluster_turns = [turns[i] for i in indices]
        cluster_intents_list = [intents[i] for i in indices]

        # Tool frequency
        tool_counts: Counter = Counter()
        for t in cluster_turns:
            for tool in t.get("tools_used", []):
                tool_counts[tool] += 1

        # Average quality
        grades = [grade_map.get(t.get("quality_grade", "copper"), 0) for t in cluster_turns]
        avg_grade = sum(grades) / len(grades) if grades else 0
        avg_quality = reverse_map.get(round(avg_grade), "copper")

        # Verb-object domain label
        tf = cluster_token_freqs[ci]
        verbs = sorted(
            [(tok, tf[tok]) for tok in tf if tok in _ABSTRACT_VERBS],
            key=lambda x: x[1], reverse=True,
        )
        best_verb = verbs[0][0] if verbs else ""

        noun_scores = {}
        for tok, freq in tf.items():
            if tok in _ABSTRACT_VERBS:
                continue
            idf = math.log(num_clusters / max(doc_freq[tok], 1)) if num_clusters > 1 else 1.0
            noun_scores[tok] = freq * max(idf, 0.1)
        best_nouns = sorted(noun_scores, key=noun_scores.get, reverse=True)
        best_noun = best_nouns[0] if best_nouns else ""

        if best_verb and best_noun:
            domain_label = f"{best_verb}-{best_noun}"
        elif best_verb:
            domain_label = best_verb
        elif best_noun:
            domain_label = best_noun
        else:
            domain_label = "general"

        # Track session diversity
        sessions = set()
        for t in cluster_turns:
            src = t.get("metadata", {}).get("source", "")
            if src:
                sessions.add(src)

        clusters.append({
            "domain": domain_label,
            "intents": cluster_intents_list,
            "turn_ids": [t.get("turn_id", "") for t in cluster_turns],
            "tools_used": dict(tool_counts),
            "turns": cluster_turns,
            "size": len(indices),
            "avg_quality": avg_quality,
            "unique_sessions": len(sessions),
        })

    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters


# -- Scoring --

_GRADE_WEIGHTS = {"copper": 0.2, "silver": 0.5, "gold": 0.8, "platinum": 1.0}

_ABSTRACT_VERBS = frozenset({
    "write", "fix", "add", "test", "deploy", "configure", "refactor",
    "update", "create", "build", "debug", "implement", "remove", "setup",
    "migrate", "optimize", "review", "integrate", "summarize", "analyze",
    "investigate", "wire", "extract", "generate", "install", "run",
})
_TASK_MARKERS = re.compile(r"^##\s*(task|investigation):", re.IGNORECASE)


def score_skill_candidate(cluster: dict) -> dict:
    """Score on 5 dimensions. Returns cluster with added score fields.

    Dimensions:
        frequency:     min(size / 10, 1.0) — more occurrences = more useful
        diversity:     unique_tools / total_tool_calls — multi-tool = richer
        quality:       weighted avg of turn quality grades
        generality:    1.0 - specificity + abstract verb boost
        actionability: fraction of intents with task verbs or ## Task markers
                       separates "write tests for X" from "did we complete"

    Composite: 0.15*freq + 0.15*div + 0.10*qual + 0.15*gen + 0.20*act + 0.25*sess_div
    """
    size = cluster.get("size", 0)

    # Frequency
    frequency = min(size / 10.0, 1.0)

    # Diversity — neutral 0.5 when no tool data (not penalized)
    tools = cluster.get("tools_used", {})
    total_tool_calls = sum(tools.values())
    if total_tool_calls == 0:
        diversity = 0.5  # unknowable, not zero
    else:
        unique_tools = len(tools)
        diversity = unique_tools / total_tool_calls

    # Quality
    turns = cluster.get("turns", [])
    if turns:
        grades = [_GRADE_WEIGHTS.get(t.get("quality_grade", "copper"), 0.2) for t in turns]
        quality = sum(grades) / len(grades)
    else:
        quality = 0.2

    # Generality
    all_text = " ".join(cluster.get("intents", []))
    tokens = all_text.lower().split()
    if tokens:
        path_count = sum(1 for t in tokens if _PATH_PATTERN.search(t))
        code_count = sum(1 for t in tokens if _CAMEL_SNAKE.search(t))
        abstract_count = sum(1 for t in tokens if t in _ABSTRACT_VERBS)
        specificity = (path_count + code_count) / len(tokens)
        abstract_boost = min(abstract_count / len(tokens) * 2, 0.3)
        generality = max(0.0, min(1.0, 1.0 - specificity + abstract_boost))
    else:
        generality = 0.5

    # Actionability — does this look like a task or a conversational habit?
    intents = cluster.get("intents", [])
    if intents:
        actionable = 0
        for intent in intents:
            low = intent.lower()
            words = low.split()
            has_verb = any(w in _ABSTRACT_VERBS for w in words[:5])
            has_marker = bool(_TASK_MARKERS.match(intent))
            if has_verb or has_marker:
                actionable += 1
        actionability = actionable / len(intents)
    else:
        actionability = 0.0

    # Session diversity — real skills appear across many different sessions
    unique_sessions = cluster.get("unique_sessions", 1)
    session_diversity = min(unique_sessions / max(size * 0.5, 1), 1.0)

    composite = (0.15 * frequency + 0.15 * diversity + 0.10 * quality
                 + 0.15 * generality + 0.20 * actionability + 0.25 * session_diversity)

    cluster["score"] = round(composite, 3)
    cluster["score_breakdown"] = {
        "frequency": round(frequency, 3),
        "diversity": round(diversity, 3),
        "quality": round(quality, 3),
        "generality": round(generality, 3),
        "actionability": round(actionability, 3),
        "session_diversity": round(session_diversity, 3),
    }
    return cluster


# -- Retry dedup --

def _dedup_retries(turns: List[dict], threshold: float = 0.7) -> List[dict]:
    """Within each session, collapse near-identical intents. Keep the richest turn."""
    session_groups: Dict[str, List[dict]] = defaultdict(list)
    for i, t in enumerate(turns):
        sid = t.get("metadata", {}).get("source", f"__orphan_{i}")
        session_groups[sid].append(t)

    result = []
    for sid, group in session_groups.items():
        if len(group) <= 1 or sid.startswith("__orphan_"):
            result.extend(group)
            continue
        kept = [group[0]]
        for t in group[1:]:
            t_tokens = _tokenize_intent(t.get("intent", ""))
            is_retry = False
            for ki, k in enumerate(kept):
                k_tokens = _tokenize_intent(k.get("intent", ""))
                if t_tokens and k_tokens:
                    jaccard = len(t_tokens & k_tokens) / len(t_tokens | k_tokens)
                    if jaccard > threshold:
                        is_retry = True
                        # Keep the one with more tools
                        if len(t.get("tools_used", [])) > len(k.get("tools_used", [])):
                            kept[ki] = t
                        break
            if not is_retry:
                kept.append(t)
        result.extend(kept)
    return result


# -- Main entry point --

def extract_skills(
    brain_path: Path,
    min_score: float = 0.5,
    min_cluster_size: int = 3,
    use_embeddings: bool = True,
    max_turns: int = 4000,
) -> List[dict]:
    """Full pipeline: load turns → dedup → cluster → score → filter → return.

    Pairwise comparison is O(n²), so max_turns caps input size.
    With 1000 turns: ~500K comparisons (fast with Jaccard, ~136s with embeddings).
    When capped, takes the most recent turns (highest quality signal).
    """
    from .archive_pipeline import ArchivePipeline

    archive = ArchivePipeline(brain_path=brain_path)
    turns = archive.get_turns()

    if not turns:
        logger.info("No conversation turns found — nothing to extract.")
        return []

    # Dedup by content_hash (same turn ingested multiple times)
    seen_hashes = set()
    unique_turns = []
    for t in turns:
        h = t.get("content_hash", "")
        if h and h in seen_hashes:
            continue
        if h:
            seen_hashes.add(h)
        unique_turns.append(t)
    logger.info("Deduped %d -> %d unique turns", len(turns), len(unique_turns))
    turns = unique_turns

    # Retry dedup — same session, similar intent → keep richest
    turns = _dedup_retries(turns)
    logger.info("After retry dedup: %d turns", len(turns))

    if len(turns) > max_turns:
        logger.info("Capping %d turns to most recent %d (O(n²) safety)", len(turns), max_turns)
        turns = turns[-max_turns:]

    logger.info("Clustering %d turns...", len(turns))
    clusters = cluster_intents(
        turns,
        min_cluster_size=min_cluster_size,
        use_embeddings=use_embeddings,
    )
    logger.info("Found %d intent clusters", len(clusters))

    # Score each cluster
    scored = [score_skill_candidate(c) for c in clusters]

    # Filter by min_score
    qualified = [c for c in scored if c.get("score", 0) >= min_score]
    logger.info("Scored: %d above threshold (%.2f)", len(qualified), min_score)

    return qualified
