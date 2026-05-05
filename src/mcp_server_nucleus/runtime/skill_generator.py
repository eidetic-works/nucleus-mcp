"""Skill Generator — Turn a scored cluster into a SKILL.md string.

Deterministic generation. No LLM required.
The DATA is the skill, not a summary of the data.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple

from . import skill_extractor as _skill_extractor

# Patterns for anonymization
_FILE_PATH_RE = re.compile(r"(?:[/\\][\w.-]+){2,}")
_CAMEL_RE = re.compile(r"\b[a-z]+(?:[A-Z][a-z]+){1,}\b")
_PASCAL_RE = re.compile(r"\b(?:[A-Z][a-z]+){2,}\b")
_SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z]+){2,}\b")
_URL_RE = re.compile(r"https?://\S+")
_ERROR_RE = re.compile(r"(?:Error|Exception|Traceback|FAILED|error:)\s*[^\n]{10,}")

# Markdown / prose-prefix artifacts that leak from raw conversation prompts
# into trigger phrases and descriptions. Strip these BEFORE tokenizing intent.
_MARKDOWN_LEAD_RE = re.compile(r"^[\s>#*+\-]+")  # leading #, *, -, >, +, whitespace
_LABEL_PREFIX_RE = re.compile(
    r"^(task|investigation|tldr|summary|note|context|goal|objective|instruction|prompt|user|assistant|q|question|a|answer)\s*[:\-]\s*",
    re.IGNORECASE,
)
_BACKTICK_RE = re.compile(r"`+")
_BOLD_ITALIC_RE = re.compile(r"\*+|_+")


def _clean_intent(text: str) -> str:
    """Strip markdown / label artifacts from the start of an intent.

    Removes leading `#`, `*`, `-`, `>` (markdown headers/lists/quotes),
    leading labels like "Task:", "Investigation:", "TLDR:" (case-insensitive),
    inline backticks and bold/italic markers, and collapses whitespace.

    Idempotent. Empty-safe (returns "" for blank input).
    """
    if not text:
        return ""
    s = text.strip()
    # Iterate up to 3 times: first strip leading markdown, then label prefix,
    # then markdown again in case the label was preceded by `##`.
    for _ in range(3):
        prev = s
        s = _MARKDOWN_LEAD_RE.sub("", s).strip()
        s = _LABEL_PREFIX_RE.sub("", s).strip()
        if s == prev:
            break
    s = _BACKTICK_RE.sub("", s)
    s = _BOLD_ITALIC_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _build_description(domain: str, triggers: List[str], size: int) -> str:
    """Build a generalizable description matching well-formed skill shapes.

    Targets the gstack/qa shape: a verb-phrase summary + an explicit list of
    trigger keywords CC's auto-activation can match against.

    Avoids the verbatim-prompt-slice bug observed in
    .brain/research/2026-04-28_tier_architecture/03_skill_activation_telemetry.md
    (e.g. "When user asks to ## investigation: debug why /chat endpoint").
    """
    if not triggers:
        return f"Skill for {domain} (auto-extracted from {size} conversation turns)."

    verb_phrase = triggers[0].strip()
    # Cap verb-phrase to first 5 words to keep the lead generalized.
    verb_phrase = " ".join(verb_phrase.split()[:5])

    # Show up to 3 trigger phrases as the keyword list (post-clean, deduped).
    seen = set()
    keyword_list: List[str] = []
    for t in triggers:
        t = t.strip().strip("'\"")
        if not t or t in seen:
            continue
        seen.add(t)
        keyword_list.append(t)
        if len(keyword_list) >= 3:
            break

    if keyword_list:
        keys_str = ", ".join(f"'{k}'" for k in keyword_list)
        return (
            f"When user asks to {verb_phrase}, or says: {keys_str}. "
            f"Auto-extracted from {size} {domain} conversation turns."
        )
    return (
        f"When user asks to {verb_phrase}. "
        f"Auto-extracted from {size} {domain} conversation turns."
    )


def _extract_trigger_phrases(intents: List[str], top_n: int = 5) -> List[str]:
    """Extract distinctive trigger phrases from cluster intents.

    Algorithm:
        1. Take first 6 words of each intent (the "verb phrase")
        2. Normalize: lowercase, strip articles
        3. Group by leading 3-gram
        4. Pick most frequent variant from each group
        5. Return top_n most distinctive phrases
    """
    prefixes: Counter = Counter()
    prefix_to_full: Dict[str, str] = {}

    for intent in intents:
        cleaned = _clean_intent(intent).lower()
        if not cleaned:
            continue
        words = cleaned.split()[:6]
        if not words:
            continue
        phrase = " ".join(words)
        # Normalize: strip leading articles / politeness wrappers
        phrase = re.sub(r"^(please |can you |could you |i need to |i want to )", "", phrase)
        key = " ".join(phrase.split()[:3])  # 3-gram grouping key
        prefixes[key] += 1
        # Keep the longest variant as representative
        if key not in prefix_to_full or len(phrase) > len(prefix_to_full[key]):
            prefix_to_full[key] = phrase

    # Return top_n most frequent, using the full representative phrase
    top = prefixes.most_common(top_n)
    return [prefix_to_full[key] for key, _ in top if key in prefix_to_full]


def _extract_tool_sequence(turns: List[dict]) -> str:
    """Build a topic-aware tool workflow from cluster turns."""
    # Count tool frequency across all turns
    tool_freq: Counter = Counter()
    for turn in turns:
        for tool in turn.get("tools_used", []):
            tool_freq[tool] += 1
    if not tool_freq:
        return "No consistent tool pattern detected."

    # Extract dominant topic from intents
    _TOPIC_STOPS = {"the", "and", "for", "with", "from", "that", "this",
                    "all", "are", "was", "has", "have", "been", "will",
                    "can", "you", "your", "our", "not", "but"}
    _TOPIC_VERBS = {"write", "fix", "add", "test", "deploy", "configure",
                    "refactor", "update", "create", "build", "debug",
                    "implement", "remove", "setup", "migrate", "optimize",
                    "review", "integrate", "summarize", "analyze",
                    "investigate", "extract", "generate", "install", "run"}
    word_freq: Counter = Counter()
    for turn in turns:
        words = re.sub(r"[^\w\s]", " ", turn.get("intent", "").lower()).split()
        for w in words:
            if len(w) > 3 and w not in _TOPIC_STOPS and w not in _TOPIC_VERBS:
                word_freq[w] += 1
    topic = word_freq.most_common(1)[0][0] if word_freq else "relevant"

    # Map tools to topic-aware descriptions
    templates = {
        "Read": f"Read {topic} code",
        "Edit": f"Edit {topic} implementation",
        "Bash": f"Run {topic} verification",
        "Write": f"Write new {topic} files",
        "Grep": f"Search {topic} patterns",
        "Glob": f"Find {topic} files",
        "Agent": f"Delegate {topic} subtasks",
    }

    # Top 4 tools by frequency
    top_tools = [t for t, _ in tool_freq.most_common(4)]
    parts = [templates.get(t, t) for t in top_tools]
    return " -> ".join(parts)


def _anonymize_text(text: str) -> str:
    """Strip project-specific details from intent/outcome text.

    Replaces:
        - URLs           -> <url>
        - File paths     -> <file>
        - Error messages -> <error>
        - Hostnames      -> <host>   (runtime-detected; see skill_extractor)
        - camelCase / PascalCase / snake_case identifiers -> <name>

    Preserves: action verbs, general descriptions, tool names.
    """
    text = _clean_intent(text)
    text = _URL_RE.sub("<url>", text)
    text = _FILE_PATH_RE.sub("<file>", text)
    text = _ERROR_RE.sub("<error>", text)
    text = _skill_extractor._HOSTNAME.sub("<host>", text)
    text = _CAMEL_RE.sub("<name>", text)
    text = _PASCAL_RE.sub("<name>", text)
    text = _SNAKE_RE.sub("<name>", text)
    # Collapse multiple <name> in a row
    text = re.sub(r"(<name>\s*){2,}", "<name> ", text)
    return text.strip()


def _select_examples(turns: List[dict], n: int = 3) -> List[dict]:
    """Pick highest-quality, most diverse examples from cluster turns.

    Sorts by quality_grade (platinum first), then by intent length
    (longer = more descriptive). Deduplicates by first-5-word prefix.
    Returns anonymized intent->outcome pairs.
    """
    grade_order = {"platinum": 0, "gold": 1, "silver": 2, "copper": 3}

    sorted_turns = sorted(
        turns,
        key=lambda t: (
            grade_order.get(t.get("quality_grade", "copper"), 3),
            -len(t.get("intent", "")),
        ),
    )

    seen_prefixes = set()
    examples = []
    for turn in sorted_turns:
        intent = turn.get("intent", "")
        if not intent:
            continue
        prefix = " ".join(intent.lower().split()[:5])
        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)
        examples.append({
            "intent": _anonymize_text(intent),
            "outcome": _anonymize_text(turn.get("outcome", "")),
        })
        if len(examples) >= n:
            break

    return examples


def generate_skill_md(cluster: dict) -> str:
    """Generate SKILL.md from a scored cluster.

    SKILL.md output format:
        ---
        name: {domain}
        description: {1-line summary from trigger phrases}
        version: 1.0.0
        source: nucleus-flywheel
        generated_from: {N} conversation turns
        score: {composite_score}
        ---

        # {Domain Title}

        ## When to use
        - {trigger phrase 1}
        - {trigger phrase 2}
        ...

        ## Approach
        {tool sequence description}

        ## Key patterns
        {common decisions/actions extracted from turn data}

        ## Examples
        ### Example 1
        **Intent:** {anonymized intent}
        **Outcome:** {anonymized outcome}
    """
    domain = cluster.get("domain", "unknown")
    score = cluster.get("score", 0)
    size = cluster.get("size", 0)
    intents = cluster.get("intents", [])
    turns = cluster.get("turns", [])

    # Title: capitalize each word
    title = " ".join(word.capitalize() for word in domain.split("-"))

    # Trigger phrases (cleaned of markdown / label artifacts)
    triggers = _extract_trigger_phrases(intents)
    if not triggers:
        cleaned_first = _clean_intent(intents[0]) if intents else ""
        triggers = [_anonymize_text(cleaned_first)] if cleaned_first else ["(no triggers)"]

    # Description: template-shaped, not verbatim-prompt-shaped.
    # Format mirrors well-formed skills like gstack/qa:
    #   "When user asks to <verb-phrase>, or says: '<t1>', '<t2>', '<t3>'.
    #    Generated from <N> conversation turns in domain <domain>."
    description = _build_description(domain, triggers, size)

    # Tool sequence
    tool_seq = _extract_tool_sequence(turns)

    # Key patterns from decisions
    decision_counts: Counter = Counter()
    for turn in turns:
        for d in turn.get("decisions", []):
            anon = _anonymize_text(d)
            if len(anon) > 10:
                decision_counts[anon] += 1
    key_patterns = [d for d, _ in decision_counts.most_common(5)]

    # Examples
    examples = _select_examples(turns)

    # Build SKILL.md
    lines = [
        "---",
        f"name: {domain}",
        f"description: {description}",
        "version: 1.0.0",
        "source: nucleus-flywheel",
        f"generated_from: {size} conversation turns",
        f"score: {score}",
        "---",
        "",
        f"# {title}",
        "",
        "## When to use",
    ]
    for trigger in triggers:
        lines.append(f"- {trigger}")
    lines.append("")
    lines.append("## Approach")
    lines.append(tool_seq)
    lines.append("")

    if key_patterns:
        lines.append("## Key patterns")
        for pattern in key_patterns:
            lines.append(f"- {pattern}")
        lines.append("")

    if examples:
        lines.append("## Examples")
        for i, ex in enumerate(examples, 1):
            lines.append(f"### Example {i}")
            lines.append(f"**Intent:** {ex['intent']}")
            lines.append(f"**Outcome:** {ex['outcome']}")
            lines.append("")

    return "\n".join(lines)
