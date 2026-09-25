"""Discovery — an agent proposes patterns; this module refuses to believe it.

``prevalence`` can only answer a question someone already asked: give it a
regex and it counts the sessions that regex appears in. It cannot notice that
the same thing went wrong eleven times under eleven different phrasings. That
noticing is the one part of the loop a cheap agent is genuinely good at, and
the one part a counter can never do.

So the labour splits, and the split is the whole design:

    the agent DISCOVERS            this module VERIFIES
    reads a sample of sessions     counts over the full set
    proposes candidate patterns    re-derives every number itself
    may be wrong, may be vague     refuses what it cannot check

**Discovery may sample. Verification may not.** An agent handed forty
transcripts and asked what keeps going wrong is doing pattern recognition over
a sample, which is fine -- a candidate is a hypothesis. The count attached to
that hypothesis is then measured over everything ``prevalence`` can reach, and
if it cannot reach all of it the reading comes back INSUFFICIENT and the
proposal cannot be accepted.

**Counts the agent supplies are discarded, not checked.** A candidate is
allowed to say "I think this happens a lot"; it is not allowed to say how
often. Anything numeric it offers is dropped on the floor before verification,
because a number that arrives with its own authority is the failure this whole
subsystem exists to prevent. The only counts that reach a proposal are the ones
this module measured.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import proposals
from .prevalence import (Prevalence, _texts_from_row, _transcripts,
                         default_roots, scan, scan_engrams, scan_many)


# A dreaming pass is a batch job gated on accumulated activity, not an
# interactive query, so it does NOT inherit `scan`'s interactive caps. Measured
# 2026-09-20: the live corpus is 4,735 transcripts / 3.54 GB, while `scan`
# defaults to 200 sessions and 8 MB -- 0.18% of it. Every reading came back
# INSUFFICIENT by construction, so nothing could ever be accepted and the loop
# was dead on arrival. A complete pass over the whole corpus takes 1-8 minutes,
# which a pass that runs on accumulated work can easily afford.
BATCH_MAX_SESSIONS = 20_000
BATCH_MAX_BYTES = 16 * 1024 * 1024 * 1024  # 16 GB

# A pattern matching nearly every session measures nothing, even though it is
# not degenerate in the empty-string sense. Found by the first live run: a
# candidate scored 200 of 200 sessions and was proposed anyway.
DEFAULT_SAMPLE_SIZE = 20
DEFAULT_MAX_SATURATION = 0.9
SATURATION_MIN_SESSIONS = 10


@dataclass
class Candidate:
    """One hypothesis from the discovering agent.

    ``pattern`` is a regex the agent believes recurs. ``memory`` is the thing
    it proposes writing down if that belief survives. ``rationale`` is for a
    human reading the proposal later; nothing branches on it.

    There is deliberately no count field. See the module docstring.
    """

    pattern: str
    memory: str
    rationale: str = ""


@dataclass
class Verdict:
    """What became of one candidate."""

    candidate: Candidate
    prevalence: Optional[Prevalence] = None
    proposal_id: Optional[str] = None
    refused: Optional[str] = None

    @property
    def proposed(self) -> bool:
        return self.proposal_id is not None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.candidate.pattern,
            "memory": self.candidate.memory,
            "rationale": self.candidate.rationale,
            "proposal_id": self.proposal_id,
            "refused": self.refused,
            "prevalence": self.prevalence.as_dict() if self.prevalence else None,
        }


@dataclass
class Discovery:
    """The outcome of one pass."""

    verdicts: List[Verdict] = field(default_factory=list)
    candidates_seen: int = 0

    @property
    def proposed(self) -> List[Verdict]:
        return [v for v in self.verdicts if v.proposed]

    @property
    def refused(self) -> List[Verdict]:
        return [v for v in self.verdicts if v.refused]

    def summary(self) -> str:
        if not self.candidates_seen:
            return "discovery: the agent proposed nothing; no candidates to verify."
        kept = len(self.proposed)
        return (
            f"discovery: {self.candidates_seen} candidate(s), {kept} survived "
            f"verification, {len(self.refused)} refused."
        )


@dataclass
class Batch:
    """What the discovering agent is given to read.

    ``sampled`` is the honest half. A batch is nearly always a sample -- the
    corpus is far larger than any prompt -- and that is fine, because nothing
    in a batch is ever counted. It exists only to provoke hypotheses. The
    moment a hypothesis becomes a number, it is measured somewhere else, over
    everything.
    """

    excerpts: List[Dict[str, Any]] = field(default_factory=list)
    sessions_available: int = 0
    sampled: bool = False

    def as_prompt(self) -> str:
        """Render the batch for an agent, one session per block."""
        parts = []
        for ex in self.excerpts:
            body = "\n".join(ex["lines"])
            parts.append(f"--- session {ex['session']} ---\n{body}")
        return "\n\n".join(parts)


def gather_batch(
    roots: Optional[Sequence[Path]] = None,
    max_sessions: int = 40,
    max_lines: int = 60,
    max_chars: int = 400,
    oldest: bool = False,
) -> Batch:
    """Collect a bounded reading sample, newest sessions first
    (oldest first when ``oldest`` -- a different slice of the corpus).

    Caps are deliberate and the result says when they bit. Nothing here feeds
    a count, so a capped batch is not an INSUFFICIENT reading -- it is simply
    a smaller prompt.
    """
    used = list(roots if roots is not None else default_roots())
    files = _transcripts(used)
    files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=not oldest)
    batch = Batch(sessions_available=len(files), sampled=len(files) > max_sessions)

    for path in files[:max_sessions]:
        lines: List[str] = []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if len(lines) >= max_lines:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    for text in _texts_from_row(row):
                        if len(lines) >= max_lines:
                            break
                        lines.append(text.strip()[:max_chars])
        except OSError:
            continue
        if lines:
            batch.excerpts.append({"session": path.stem, "lines": lines})
    return batch



try:  # Python 3.11+
    from re import _constants as _sc, _parser as _sp
except ImportError:  # pragma: no cover
    import sre_constants as _sc, sre_parse as _sp

# Longest gap a wildcard may span. A "line" in a transcript is a whole message
# and can be many kilobytes, so `a.*b` matches whenever both words appear
# anywhere in it -- by coincidence, not because one led to the other.
MAX_WILDCARD_GAP = 120


def _unbounded_wildcard(pattern: str) -> Optional[str]:
    """Describe the first unbounded ``.``-repeat in ``pattern``, else None.

    Walks the parsed regex rather than searching its text, so an escaped dot
    and a character class like ``[.*]`` are correctly left alone. Measured
    2026-09-20: chained `.*` patterns were over-counting across multi-kilobyte
    message blocks, and their excerpt (the first 170 characters of the line)
    could not show why they matched. Neither the 2-14 nor the 60-196 session
    counts from those passes can be trusted.
    """
    def walk(items) -> Optional[str]:
        for op, av in items:
            if op in (_sc.MAX_REPEAT, _sc.MIN_REPEAT):
                lo, hi, sub = av
                if any(o == _sc.ANY for o, _ in sub):
                    if hi == _sc.MAXREPEAT:
                        return "an unbounded wildcard (.* or .+)"
                    if hi > MAX_WILDCARD_GAP:
                        return f"a wildcard gap of {hi} characters"
                found = walk(sub)
                if found:
                    return found
            elif op == _sc.SUBPATTERN:
                found = walk(av[-1])
                if found:
                    return found
            elif op == _sc.BRANCH:
                for branch in av[1]:
                    found = walk(branch)
                    if found:
                        return found
            elif op in (_sc.ASSERT, _sc.ASSERT_NOT):
                found = walk(av[1])
                if found:
                    return found
        return None

    try:
        return walk(_sp.parse(pattern))
    except Exception:  # noqa: BLE001 -- an unparseable pattern is refused elsewhere
        return None


def _degenerate(rx: "re.Pattern[str]") -> bool:
    """True when a regex matches the empty string.

    ``.*``, ``a?`` and ``(foo)?`` all match every line ever written, so they
    would report maximum prevalence while meaning nothing. This is a mechanical
    test with no judgement in it: a pattern that matches nothing at all still
    matches every haystack.
    """
    return rx.search("") is not None


def verify(
    candidates: Sequence[Candidate],
    brain_path: Path,
    roots: Optional[Sequence[Path]] = None,
    history_path: Optional[Path] = None,
    over_engrams: bool = False,
    min_sessions: int = 1,
    max_sessions: int = BATCH_MAX_SESSIONS,
    max_bytes: int = BATCH_MAX_BYTES,
    max_saturation: float = DEFAULT_MAX_SATURATION,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> Discovery:
    """Measure every candidate and propose only those that survive.

    Two passes, and the order is the point. Everything that can be refused
    WITHOUT reading the corpus is refused first -- an unusable regex costs
    nothing to reject and should never cost a scan. Only the survivors reach
    the corpus, and they reach it together, in one read.

    A candidate is refused when it is unusable (no pattern, no memory, an
    invalid or degenerate regex), when it saturates, or when the measurement
    does not support it. A candidate whose evidence is merely INSUFFICIENT is
    still proposed, carrying that verdict, because the accept gate is what
    refuses it; hiding it here would lose the fact that something was noticed
    but could not be checked.
    """
    out = Discovery(candidates_seen=len(candidates))
    verdicts: List[Optional[Verdict]] = [None] * len(candidates)
    to_scan: List[tuple] = []  # (index, candidate, pattern, memory)

    # What this brain has already been told about each pattern. A pass gated on
    # accumulated activity necessarily re-reads sessions an earlier pass saw,
    # so without this the same finding is proposed again every pass -- and
    # accepting it a second time writes the memory a second time while looking
    # like progress, which is the thing `accept` refuses by id and could not
    # see by pattern.
    already: Dict[str, Dict[str, Any]] = {}
    for row in proposals.all_proposals(brain_path):
        pat = row.get("pattern") or ""
        # keep the most decided row per pattern: accepted > rejected > pending
        rank = {"accepted": 3, "rejected": 2, "pending": 1}
        if pat and rank.get(row.get("status"), 0) >= rank.get(
            (already.get(pat) or {}).get("status"), 0
        ):
            already[pat] = row

    # Pass 1 -- refusals that need no corpus.
    for i, cand in enumerate(candidates):
        pattern = (cand.pattern or "").strip()
        memory = (cand.memory or "").strip()

        if not pattern:
            verdicts[i] = Verdict(cand, refused="no pattern to measure")
            continue
        if not memory:
            verdicts[i] = Verdict(
                cand, refused="no proposed memory; a pattern alone is not a finding")
            continue
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            verdicts[i] = Verdict(cand, refused=f"not a usable regex: {exc}")
            continue
        if _degenerate(rx):
            verdicts[i] = Verdict(
                cand,
                refused=("matches the empty string, so it matches every session "
                         "and measures nothing"),
            )
            continue

        gap = _unbounded_wildcard(pattern)
        if gap:
            verdicts[i] = Verdict(
                cand,
                refused=(
                    f"uses {gap}. A transcript line is a whole message, so the "
                    f"words on either side match by coincidence and the count "
                    f"is not a count of the failure. Bound the gap instead, "
                    f"e.g. `word.{{0,60}}word`"
                ),
            )
            continue

        prior = already.get(pattern)
        if prior is not None:
            status = prior.get("status")
            pid = prior.get("proposal_id")
            if status == "accepted":
                why = (f"already accepted as {pid}; proposing it again would "
                       f"write the same memory a second time while looking "
                       f"like progress")
            elif status == "rejected":
                why = (f"already rejected as {pid}"
                       + (f" ({prior.get('reason')})" if prior.get("reason") else "")
                       + "; re-proposing a decided finding every pass is nagging, "
                         "not discovery")
            else:
                why = (f"already pending as {pid}, awaiting a decision; a second "
                       f"copy would not add evidence")
            verdicts[i] = Verdict(cand, refused=why)
            continue

        to_scan.append((i, cand, pattern, memory))

    # Pass 2 -- one read of the corpus for every surviving pattern.
    readings: Dict[str, Prevalence] = {}
    if to_scan:
        patterns = [t[2] for t in to_scan]
        if over_engrams:
            # One file; a per-pattern scan is already a cheap read of it.
            readings = {
                pat: scan_engrams(pat, history_path=history_path, max_rows=max_sessions)
                for pat in dict.fromkeys(patterns)
            }
        else:
            readings = scan_many(
                patterns, roots=roots, max_sessions=max_sessions, max_bytes=max_bytes,
                sample_size=sample_size)

    for i, cand, pattern, memory in to_scan:
        pv = readings[pattern]

        # Saturation: a pattern present in nearly every session cannot
        # distinguish anything, so it is not evidence even when the count is
        # large and the reading is complete. This threshold is a judgement,
        # unlike the empty-string test above which is mechanical -- so the
        # refusal states the number rather than hiding behind it.
        if (
            pv.sessions_scanned >= SATURATION_MIN_SESSIONS
            and pv.sessions_matched >= max_saturation * pv.sessions_scanned
        ):
            verdicts[i] = Verdict(
                cand,
                prevalence=pv,
                refused=(
                    f"matches {pv.sessions_matched} of {pv.sessions_scanned} "
                    f"sessions scanned, at or above the saturation ceiling of "
                    f"{max_saturation:.0%}; a pattern present nearly everywhere "
                    f"distinguishes nothing, whatever it may describe"
                ),
            )
            continue

        if pv.complete and pv.sessions_matched < min_sessions:
            verdicts[i] = Verdict(
                cand,
                prevalence=pv,
                refused=(
                    f"measured {pv.sessions_matched} session(s), below the "
                    f"floor of {min_sessions}. Too rare to propose at this floor; "
                    f"that is not evidence the pattern is unreal, and a rigid "
                    f"regex undercounts"
                ),
            )
            continue

        row = proposals.propose(
            brain_path=brain_path,
            proposed_memory=memory,
            evidence=pv,
            pattern=pattern,
            # A regex counts words that co-occur. Whether those matches are
            # the FAILURE is a separate question, and it must be answered
            # before this can be accepted. The engram path records no
            # sample, so it cannot be asked.
            precision_required=not over_engrams,
        )
        verdicts[i] = Verdict(cand, prevalence=pv, proposal_id=row["proposal_id"])

    out.verdicts = [v for v in verdicts if v is not None]
    return out


def discover(
    propose_fn: Callable[[], Sequence[Candidate]],
    brain_path: Path,
    **kwargs: Any,
) -> Discovery:
    """Run one pass: ask the agent for candidates, then verify them.

    ``propose_fn`` is injected rather than called directly so the discovering
    agent can be a Haiku subagent, a free vendor lane, or a stub in a test --
    the verification half is identical either way, which is the point. If the
    agent fails outright, the pass returns an empty discovery rather than
    raising: no candidates is a real and unremarkable outcome, and a discovery
    pass must never be able to damage the memory it reads.
    """
    try:
        candidates = list(propose_fn() or [])
    except Exception as exc:  # noqa: BLE001 -- a failed discoverer is not a crash
        out = Discovery()
        out.verdicts.append(
            Verdict(
                Candidate(pattern="", memory=""),
                refused=f"the discovering agent failed: {exc}",
            )
        )
        return out
    return verify(candidates, brain_path=brain_path, **kwargs)
