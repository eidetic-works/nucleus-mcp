"""How many SESSIONS a pattern appears in -- and whether we could see them all.

The flywheel files tickets: 349 on disk, each a single-session assertion that
something broke. None can say how often, in how many sessions, or point at one.
That is the gap Lamis Mukta's talk names for a dreaming pass -- a proposed
memory change arrives with "examples of transcripts where it's noticed this
pattern has happened and also some stats on how prevalent this issue is."

Two refusals are the whole design.

REFUSAL 1 -- NO COUNT OVER A SET WE COULD NOT FULLY SEE.
This machine holds 4,728 transcripts and the largest is 815 MB. Every scan is
capped by something, and a capped scan returning "3 sessions" is textually
identical to a complete one. So a cap, a skip, or an empty corpus sets
``complete = False`` and ``summary()`` refuses to print the number at all.
This repo has paid for the alternative: 1,021 envelopes, 0 qualifying BY
CONSTRUCTION, and a gate that read the zero as an answer.

REFUSAL 2 -- FREQUENCY IS NOT PREVALENCE.
A pattern fifty times in one transcript is ONE session. Counting hits would let
an agent's own repetition launder itself into evidence of a widespread problem,
which is the failure the flywheel exists to catch, not to commit.

Session identity is the FILENAME (a uuid), never a parsed field: free, and
still correct when a transcript is truncated or corrupt.

A SECOND KIND OF SOURCE -- the engram history log.
``.brain/engrams/history.jsonl`` is one file of cross-vendor activity, not
one-session-per-line: 26 of its 30,749 rows carry ``snapshot.origin.session``.
``scan_engrams`` counts distinct sessions only among rows that carry one and
reports matching rows without one as ``unattributed_matches``; a single
unattributed match makes the reading INSUFFICIENT, since the log cannot say
whether that row was a new session or a repeat. A row is not a session, and
a row count is frequency -- which REFUSAL 2 already disposes of.
"""
from __future__ import annotations

import json
import random
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_MAX_SESSIONS = 200
DEFAULT_MAX_BYTES = 8 * 1024 * 1024  # 8 MB; 815 MB transcripts exist
DEFAULT_MAX_ENGRAM_ROWS = 100_000  # history.jsonl is ~31k rows today
DEFAULT_MAX_EXAMPLES = 5
_EXCERPT = 160


@dataclass
class Prevalence:
    """A prevalence reading, with its own limits attached.

    ``complete`` is not decoration. ``sessions_matched`` may only be quoted as a
    fact when it is True; otherwise the reading is INSUFFICIENT and says why.
    """

    pattern: str
    sessions_matched: int = 0
    sessions_scanned: int = 0
    unattributed_matches: int = 0
    examples: List[Dict[str, Any]] = field(default_factory=list)
    # An UNBIASED sample of matched sessions (reservoir, seeded), for judging
    # precision. `examples` is the first few matches in file order, which
    # is biased toward whichever sessions happen to be read first.
    sample: List[Dict[str, Any]] = field(default_factory=list)
    complete: bool = True
    insufficient_reason: Optional[str] = None
    skipped: List[str] = field(default_factory=list)
    roots: List[str] = field(default_factory=list)

    def roots_label(self) -> str:
        if not self.roots:
            return "(unrecorded roots)"
        return ", ".join(Path(r).name or str(r) for r in self.roots)

    def summary(self) -> str:
        if not self.complete:
            return (
                f"INSUFFICIENT: cannot state how prevalent {self.pattern!r} is. "
                f"{self.insufficient_reason} Matches were seen in "
                f"{self.sessions_matched} of the {self.sessions_scanned} session(s) "
                "actually read, which is not a prevalence."
            )
        if self.sessions_matched == 0:
            # An absence is only ever an absence FROM A SET. Measured
            # 2026-09-20: scanning one project directory reported "0 of 5, a
            # real absence" for a string that had occurred minutes earlier in
            # the live session -- because a session's transcript lives under the
            # project it STARTED in, not where it is currently working. The
            # check was correct; the set could not contain the evidence. So the
            # roots are part of the claim, never implied.
            return (
                f"{self.pattern!r}: 0 of {self.sessions_scanned} sessions under "
                f"{self.roots_label()}. Complete for that set -- which is the "
                "only thing it is an absence from."
            )
        cites = ", ".join(
            f"{str(e.get('session') or e.get('source_agent') or '?')[:8]}:{e.get('line', '?')}"
            for e in self.examples[:3]
        )
        return (
            f"{self.pattern!r}: {self.sessions_matched} of {self.sessions_scanned} "
            f"sessions. e.g. {cites}"
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "sessions_matched": self.sessions_matched,
            "sessions_scanned": self.sessions_scanned,
            "complete": self.complete,
            "insufficient_reason": self.insufficient_reason,
            "unattributed_matches": self.unattributed_matches,
            "examples": self.examples,
            "sample": self.sample,
            "skipped": self.skipped,
        }


def default_roots() -> List[Path]:
    """Where Claude Code keeps transcripts on this machine."""
    return [Path.home() / ".claude" / "projects"]


def _transcripts(roots: Sequence[Path]) -> List[Path]:
    out: List[Path] = []
    for r in roots:
        if not Path(r).is_dir():
            continue
        out.extend(sorted(Path(r).rglob("*.jsonl")))
    return out


# --- what a transcript line actually says -----------------------------------
#
# MEASURED 2026-09-20, and it invalidated every reading taken before it: a
# regex run against the RAW JSONL line matches text that was never part of the
# conversation. Of 120 sessions, a candidate pattern matched the raw line in 80
# and the actual message text in ZERO -- 70 of those 80 were the `skill_listing`
# attachment, the skill catalogue injected into nearly every session, plus
# `mcp_instructions_delta` and queue rows. Tool schemas, skill listings and MCP
# instructions are identical across sessions and have nothing to do with what
# happened in them, so a scanner reading raw lines measures BOILERPLATE and
# reports it as behaviour. It is also why patterns saturated at 98%.
#
# So prevalence reads the same extracted text the discovering agent reads.
# Anything else compares a hypothesis formed from conversation against a count
# taken over machinery.


def _texts_from_row(row: Dict[str, Any]) -> List[str]:
    """Pull readable text out of one transcript row.

    Measured against the live corpus 2026-09-20, because the obvious guess was
    wrong: rows carry no top-level ``text``. The payload is ``message.content``,
    which is EITHER a plain string OR a list of typed blocks (``text``,
    ``thinking``, ``tool_use``, ``tool_result``). Reading only a top-level
    ``text`` field yielded usable lines from 8 of 25 sessions while the batch
    still reported 25 -- a sample that silently was not the sample it claimed.
    """
    msg = row.get("message")
    if not isinstance(msg, dict):
        return []
    content = msg.get("content")
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    out: List[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            text = block.get("text")
        elif kind == "tool_result":
            text = block.get("content")
            if isinstance(text, list):
                text = " ".join(
                    b.get("text", "") for b in text if isinstance(b, dict)
                )
        else:
            continue  # tool_use args and thinking are not what a reader reads
        if isinstance(text, str) and text.strip():
            out.append(text)
    return out




def _excerpt_at(text: str, match: "re.Match[str]") -> str:
    """An excerpt CENTRED on what matched, not the start of the text.

    The old excerpt was the first ``_EXCERPT`` characters of the line, so for a
    match deep inside a multi-kilobyte message it showed unrelated text and
    could not explain the count. An excerpt that does not contain the match is
    a citation to nothing.
    """
    half = _EXCERPT // 2
    start = max(0, match.start() - half)
    end = min(len(text), match.end() + half)
    out = text[start:end].strip().replace("\n", " ")
    return ("..." if start > 0 else "") + out + ("..." if end < len(text) else "")


def _texts_from_line(line: str) -> List[str]:
    """Readable text in one raw JSONL line, or nothing.

    A line that is not a message -- an attachment, a queue operation, a skill
    listing -- yields nothing, and therefore cannot be counted. That refusal is
    the whole point; see the note above.
    """
    line = line.strip()
    if not line:
        return []
    try:
        row = json.loads(line)
    except ValueError:
        return []
    if not isinstance(row, dict):
        return []
    if isinstance(row.get("attachment"), dict):
        return []  # injected machinery, identical across sessions
    return _texts_from_row(row)



def scan(
    pattern: str,
    roots: Optional[Sequence[Path]] = None,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
) -> Prevalence:
    """Count the distinct sessions ``pattern`` appears in, with citations."""
    rx = re.compile(pattern, re.IGNORECASE)
    used_roots = list(roots if roots is not None else default_roots())
    res = Prevalence(pattern=pattern, roots=[str(r) for r in used_roots])
    files = _transcripts(used_roots)

    if not files:
        res.complete = False
        res.insufficient_reason = (
            "No transcript files were found under the given roots, so nothing "
            "was read. 0 of 0 is not evidence of absence."
        )
        return res

    capped = len(files) > max_sessions
    for f in files[:max_sessions]:
        try:
            if f.stat().st_size > max_bytes:
                res.skipped.append(f.name)
                continue
        except OSError:
            res.skipped.append(f.name)
            continue

        res.sessions_scanned += 1
        session = f.stem  # the uuid IS the session id
        hit_line = None
        try:
            # Streamed on purpose. A 815 MB transcript must never be
            # materialised to answer a regex question.
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    for text in _texts_from_line(line):
                        m = rx.search(text)
                        if m:
                            hit_line = (n, _excerpt_at(text, m))
                            break
                    if hit_line is not None:
                        break  # one session counts once, however many hits
        except OSError:
            res.skipped.append(f.name)
            continue

        if hit_line is not None:
            res.sessions_matched += 1
            if len(res.examples) < max_examples:
                res.examples.append(
                    {"session": session, "file": str(f), "line": hit_line[0],
                     "excerpt": hit_line[1]}
                )

    reasons = []
    if capped:
        reasons.append(
            f"the session cap of {max_sessions} was reached ({len(files)} "
            "transcripts exist), so later sessions were never read"
        )
    if res.skipped:
        reasons.append(
            f"{len(res.skipped)} file(s) were skipped as unreadable or over the "
            f"{max_bytes}-byte limit"
        )
    if reasons:
        res.complete = False
        res.insufficient_reason = "; ".join(reasons) + "."
    return res



def scan_many(
    patterns: Sequence[str],
    roots: Optional[Sequence[Path]] = None,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
    sample_size: int = 0,
    sample_seed: int = 0,
) -> Dict[str, Prevalence]:
    """Count many patterns in ONE pass over the corpus.

    ``scan`` reads the whole corpus per pattern. A dreaming pass asks about
    several patterns at once, so six candidates meant reading 3.54 GB six
    times -- measured at over 22 minutes, almost all of it re-reading bytes
    already in hand. The work is dominated by I/O and line iteration, not by
    the regexes, so testing every pattern against each line as it goes costs
    very little more than testing one.

    Results are keyed by pattern and are per-pattern identical to what
    ``scan`` returns for that pattern alone; a test asserts that equivalence,
    because a faster path that quietly disagrees with the slow one is worse
    than no fast path.
    """
    used_roots = list(roots if roots is not None else default_roots())
    pats = list(dict.fromkeys(patterns))  # de-duplicate, keep order
    out: Dict[str, Prevalence] = {
        pat: Prevalence(pattern=pat, roots=[str(r) for r in used_roots]) for pat in pats
    }
    if not pats:
        return out

    compiled = [(pat, re.compile(pat, re.IGNORECASE)) for pat in pats]
    rng = random.Random(sample_seed)
    files = _transcripts(used_roots)

    if not files:
        for res in out.values():
            res.complete = False
            res.insufficient_reason = (
                "No transcript files were found under the given roots, so nothing "
                "was read. 0 of 0 is not evidence of absence."
            )
        return out

    capped = len(files) > max_sessions
    skipped: List[str] = []
    for f in files[:max_sessions]:
        try:
            if f.stat().st_size > max_bytes:
                skipped.append(f.name)
                continue
        except OSError:
            skipped.append(f.name)
            continue

        for res in out.values():
            res.sessions_scanned += 1
        session = f.stem
        hits: Dict[str, tuple] = {}
        try:
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    texts = _texts_from_line(line)
                    if not texts:
                        continue
                    for pat, rx in compiled:
                        if pat in hits:
                            continue
                        for text in texts:
                            m = rx.search(text)
                            if m:
                                hits[pat] = (n, _excerpt_at(text, m))
                                break
                    if len(hits) == len(compiled):
                        break  # every pattern has its one hit for this session
        except OSError:
            skipped.append(f.name)
            for res in out.values():
                res.sessions_scanned -= 1
            continue

        for pat, (line_no, excerpt) in hits.items():
            res = out[pat]
            res.sessions_matched += 1
            entry = {"session": session, "file": str(f), "line": line_no,
                     "excerpt": excerpt}
            if len(res.examples) < max_examples:
                res.examples.append(entry)
            if sample_size:
                # Reservoir sampling: every matched session is equally likely
                # to be in the sample, however many sessions there turn out to be.
                if len(res.sample) < sample_size:
                    res.sample.append(entry)
                else:
                    j = rng.randrange(res.sessions_matched)
                    if j < sample_size:
                        res.sample[j] = entry

    for res in out.values():
        res.skipped = list(skipped)
        reasons = []
        if capped:
            reasons.append(
                f"the session cap of {max_sessions} was reached ({len(files)} "
                "transcripts exist), so later sessions were never read"
            )
        if skipped:
            reasons.append(
                f"{len(skipped)} file(s) were skipped as unreadable or over the "
                f"{max_bytes}-byte limit"
            )
        if reasons:
            res.complete = False
            res.insufficient_reason = "; ".join(reasons) + "."
    return out


def _default_history_path() -> Optional[Path]:
    """Locate ``.brain/engrams/history.jsonl`` without creating anything.

    Resolution order mirrors get_brain_path()'s, minus its side effects:
    ``NUCLEUS_BRAIN_PATH`` first, then a walk up from the cwd looking for a
    ``.brain/`` that already contains the log. ``None`` when absent --
    absence is a reading (INSUFFICIENT), not an error and not a zero.
    """
    env = os.environ.get("NUCLEUS_BRAIN_PATH")
    if env:
        p = Path(env) / "engrams" / "history.jsonl"
        if p.is_file():
            return p
    cwd = Path.cwd()
    for d in (cwd, *cwd.parents):
        p = d / ".brain" / "engrams" / "history.jsonl"
        if p.is_file():
            return p
    return None


def scan_engrams(
    pattern: str,
    history_path: Optional[Path] = None,
    max_rows: int = DEFAULT_MAX_ENGRAM_ROWS,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
) -> Prevalence:
    """Count the distinct sessions ``pattern`` appears in across the engram
    history log -- or refuse, when the log cannot say.

    One file, many lanes, almost no session ids. Sessions are counted only
    among rows carrying ``snapshot.origin.session``; matching rows without
    one go to ``unattributed_matches`` and spoil the count, because each may
    be a new session or a repeat of an already-counted one.
    """
    rx = re.compile(pattern, re.IGNORECASE)
    path = Path(history_path) if history_path is not None else _default_history_path()
    res = Prevalence(pattern=pattern, roots=[str(path)] if path is not None else [])

    if path is None or not path.is_file():
        res.complete = False
        res.insufficient_reason = (
            "No engram history log was found, so nothing was read. "
            "0 of 0 is not evidence of absence."
        )
        return res

    seen_sessions: set = set()
    hit_sessions: set = set()
    rows_read = 0
    capped = False
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rows_read >= max_rows:
                    capped = True
                    break
                if not line.strip():
                    continue  # blank space is not a malformed row
                rows_read += 1
                try:
                    row = json.loads(line)
                except ValueError:
                    res.skipped.append(f"{path.name}:{n} (unparseable row)")
                    continue
                snap = row.get("snapshot") or {}
                origin = snap.get("origin") or {}
                session = origin.get("session")
                # Only a session the writer could justify counts. An
                # env-derived id comes from a process whose environment was
                # frozen at spawn, and a long-lived writer serves many
                # sessions -- so counting it collapses thousands of rows onto
                # one id. Treat it as unattributed and let the reading come
                # back INSUFFICIENT, which is the true answer.
                if session and origin.get("session_source") != "explicit":
                    session = None
                if session:
                    seen_sessions.add(session)
                value = snap.get("value")
                text = (
                    value if isinstance(value, str)
                    else json.dumps(value, default=str) if value is not None
                    else ""
                )
                if not rx.search(text):
                    continue
                if session:
                    hit_sessions.add(session)
                else:
                    res.unattributed_matches += 1
                if len(res.examples) < max_examples:
                    res.examples.append(
                        {"session": session,
                         "source_agent": snap.get("source_agent"),
                         "timestamp": snap.get("timestamp") or row.get("timestamp"),
                         "line": n,
                         "excerpt": text.strip()[:_EXCERPT]}
                    )
    except OSError:
        res.complete = False
        res.insufficient_reason = (
            f"The engram history log at {path} could not be read, so nothing "
            "was scanned. 0 of 0 is not evidence of absence."
        )
        return res

    res.sessions_scanned = len(seen_sessions)
    res.sessions_matched = len(hit_sessions)

    reasons = []
    if res.unattributed_matches:
        reasons.append(
            f"{res.unattributed_matches} matching row(s) carry no "
            "snapshot.origin.session -- the log does not record a session "
            "for most rows, so a distinct-session count is not available"
        )
    if res.skipped:
        reasons.append(
            f"{len(res.skipped)} row(s) were unparseable and could not be "
            "checked for a match"
        )
    if capped:
        reasons.append(
            f"the row cap of {max_rows} was reached, so later rows were "
            "never read"
        )
    if reasons:
        res.complete = False
        res.insufficient_reason = "; ".join(reasons) + "."
    return res
