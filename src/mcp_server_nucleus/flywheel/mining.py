"""Mining -- discover recurring failures WITHOUT asking an agent to imagine them.

The agent-driven discoverer proposed semantic patterns ("a stub passed a check")
that a regex cannot verify: three passes, no acceptable finding, and the one
survivor was 20% precision. The trouble was never the verifier. It was asking a
model to name failures from a 38-session sample and then measuring words.

The harness already marks failures. Every tool result carries ``is_error``.
This module counts those, normalises the message so that the same failure with
a different path, id or number is recognised as the same, and reports how many
DISTINCT SESSIONS each signature appears in. Nothing is guessed: every count is
of a thing the harness flagged as an error, so precision is high by
construction and needs no labeller.

What it cannot do is say what a failure MEANS or that it is worth remembering.
That is judgement, and it stays with a human or an agent reading a ranked list
of things that demonstrably happened.

Dreaming sessions are excluded. A discovery pass writes its own prompt into a
transcript, and a later pass that reads it finds its own words. Measured
2026-09-20: two of three "false" matches on one pattern were the ALREADY KNOWN
list from the previous discoverer's prompt.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .prevalence import _transcripts, default_roots

# Text that identifies a session as a dreaming agent's own. Checked against the
# head of the file, where a subagent's prompt lives.
DREAMING_MARKERS = (
    "DISCOVERY half of a memory flywheel",
    "PRECISION half of a memory flywheel",
)
_HEAD_BYTES = 6000
SIGNATURE_CHARS = 110

_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_HEX = re.compile(r"\b[0-9a-f]{7,}\b", re.I)
_PATH = re.compile(r"(?:/[\w.@+-]+){2,}")
_NUM = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def is_dreaming_session(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(_HEAD_BYTES)
    except OSError:
        return False
    return any(m in head for m in DREAMING_MARKERS)


def signature(text: str) -> str:
    """A stable identity for an error, blind to paths, ids and numbers.

    Two occurrences of "File does not exist" in different directories are ONE
    failure; treating them as two is how a real recurrence hides in the tail.
    """
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    # A bare exit code says nothing: measured, "Exit code 1" alone swallowed 293
    # sessions of unrelated failures. The informative part is the next line.
    if len(lines) > 1 and re.fullmatch(r"\s*exit code[: ]*\d+\s*", first, re.I):
        first = f"{first.strip()} | {lines[1].strip()}"
    s = _UUID.sub("<id>", first)
    s = _PATH.sub("<path>", s)
    s = _HEX.sub("<hex>", s)
    s = _NUM.sub("<n>", s)
    return _WS.sub(" ", s).strip().lower()[:SIGNATURE_CHARS]


def _error_texts(line: str) -> List[str]:
    if '"tool_result"' not in line:
        return []
    try:
        row = json.loads(line)
    except ValueError:
        return []
    content = (row.get("message") or {}).get("content") if isinstance(row, dict) else None
    if not isinstance(content, list):
        return []
    out: List[str] = []
    for b in content:
        if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error") is True:
            t = b.get("content")
            if isinstance(t, list):
                t = " ".join(x.get("text", "") for x in t if isinstance(x, dict))
            if isinstance(t, str) and t.strip():
                out.append(t)
    return out


@dataclass
class Cluster:
    signature: str
    sessions: int = 0
    occurrences: int = 0
    example: str = ""
    example_session: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"signature": self.signature, "sessions": self.sessions,
                "occurrences": self.occurrences, "example": self.example,
                "example_session": self.example_session}


@dataclass
class Mined:
    clusters: List[Cluster] = field(default_factory=list)
    sessions_scanned: int = 0
    sessions_excluded: int = 0
    sessions_with_errors: int = 0
    errors_seen: int = 0


def mine(roots: Optional[Sequence[Path]] = None, min_sessions: int = 5,
         top: int = 40, exclude_dreaming: bool = True) -> Mined:
    """Rank recurring error signatures by the distinct sessions they appear in.

    ``occurrences`` is reported next to ``sessions`` on purpose: one session
    hitting the same error 200 times in a retry loop is one session, not 200.
    """
    files = _transcripts(list(roots if roots is not None else default_roots()))
    sess: Dict[str, set] = defaultdict(set)
    occ: Dict[str, int] = defaultdict(int)
    ex: Dict[str, tuple] = {}
    m = Mined()

    for f in files:
        if exclude_dreaming and is_dreaming_session(f):
            m.sessions_excluded += 1
            continue
        m.sessions_scanned += 1
        had = False
        try:
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    for text in _error_texts(line):
                        sig = signature(text)
                        if not sig:
                            continue
                        had = True
                        m.errors_seen += 1
                        sess[sig].add(f.stem)
                        occ[sig] += 1
                        ex.setdefault(sig, (text.strip().replace("\n", " ")[:220], f.stem))
        except OSError:
            continue
        m.sessions_with_errors += had

    rows = [Cluster(sig, len(s), occ[sig], ex[sig][0], ex[sig][1])
            for sig, s in sess.items() if len(s) >= min_sessions]
    rows.sort(key=lambda c: (-c.sessions, -c.occurrences))
    m.clusters = rows[:top]
    return m
