"""Three-state verdicts for lane tasks: FIXED / CLEAN / INSUFFICIENT.

Why this module exists
----------------------
The lane's verdict used to be binary: a commit with >=5 real changed lines, or
failure. A doc that was GENUINELY ACCURATE therefore looked exactly like a
vendor that did nothing -- both surfaced as
"PAUSED: Diff verification failed: 0 real lines". A sweep that ends "13 paused"
tells you nothing; a sweep that ends "9 clean, 4 fixed, 0 insufficient" is a
finished pass you can trust and re-run against later.

"Done" was collapsing into "stopped".

The hazard this module is built against
---------------------------------------
Adding CLEAN as a passing outcome creates an obvious incentive: claiming CLEAN
is cheaper than doing the audit. So CLEAN is NOT accepted on the vendor's word.
It must carry evidence the executor can check against the filesystem, with no
appeal to vendor intent -- the executor can only ever see artifacts.

INSUFFICIENT is a first-class RESULT, not an error. A vendor that honestly could
not establish either outcome should say so and have that recorded, rather than
being retried twice and paused with an unreadable reason.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import List, Optional

FIXED = "FIXED"
CLEAN = "CLEAN"
INSUFFICIENT = "INSUFFICIENT"

ALL_VERDICTS = (FIXED, CLEAN, INSUFFICIENT)

#: A CLEAN verdict must cite at least this many distinct claims...
MIN_CLAIMS = 3
#: ...backed by at least this many DISTINCT real paths. Distinctness matters:
#: citing README.md three times is one act of verification, not three.
MIN_DISTINCT_PATHS = 3

_VERDICT_RE = re.compile(r"^\s*VERDICT:\s*([A-Z_-]+)\s*$", re.MULTILINE)
_TASK_RE = re.compile(r"^\s*TASK_ID:\s*(\S+)\s*$", re.MULTILINE)
_CLAIMS_RE = re.compile(r"^\s*CLAIMS_CHECKED:\s*(\d+)\s*$", re.MULTILINE)
# "- <claim> | TRUE | path/to/file.py:42 | <literal symbol>"
#
# The trailing symbol is what makes this expensive to forge. It must be a
# verbatim token appearing in BOTH the doc under audit and the cited file, so
# producing one requires actually reading the doc -- which is the work itself.
# Without it, conditions like "cite 3 real paths" are satisfied by pyproject.toml,
# AGENTS.md and DECISIONS.md, all guessable from the repo name alone.
_EVIDENCE_RE = re.compile(
    r"^\s*[-*]\s*(?P<claim>.+?)\s*\|\s*(?P<status>TRUE|FALSE|STALE|UNVERIFIABLE)\s*\|"
    r"\s*(?P<path>[^\s|]+)\s*(?:\|\s*(?P<symbol>.+?)\s*)?$",
    re.MULTILINE,
)


@dataclass
class EvidenceRow:
    claim: str
    status: str
    path: str
    symbol: str = ""

    @property
    def bare_symbol(self) -> str:
        """The symbol with report formatting stripped.

        Vendors write the symbol as code -- `Sovereign Monolith`, "flag", **X** --
        because that is how you present an identifier in a report. The doc and
        the source file being compared usually contain it BARE. Matching the
        decorated form against both sides rejected correct work: the first real
        refusal logged was a vendor that cited a symbol appearing bare in both
        the doc (3x) and the cited JSX file, and added the backticks itself.
        """
        return self.symbol.strip().strip("`\"'*_ ").strip()

    @property
    def bare_path(self) -> str:
        """Path with any :line suffix stripped."""
        return self.path.split(":", 1)[0]


@dataclass
class ParsedVerdict:
    verdict: Optional[str] = None
    claims_checked: int = 0
    evidence: List[EvidenceRow] = field(default_factory=list)
    task_id: Optional[str] = None
    verdict_line_count: int = 0

    @property
    def declared(self) -> bool:
        return self.verdict in ALL_VERDICTS


def parse_verdict(stdout: str) -> ParsedVerdict:
    """Pull a structured verdict block out of vendor stdout.

    Absence of a block is not an error here -- it simply yields a ParsedVerdict
    with verdict=None, and the caller decides what that means. Parsing and
    judging are kept apart on purpose: a parser that also decides is a parser
    you cannot test against hostile input.
    """
    if not stdout:
        return ParsedVerdict()
    all_verdict_lines = _VERDICT_RE.findall(stdout)
    m = _VERDICT_RE.search(stdout)
    verdict = m.group(1).upper() if m else None
    tm = _TASK_RE.search(stdout)
    cm = _CLAIMS_RE.search(stdout)
    claims = int(cm.group(1)) if cm else 0
    rows = [
        EvidenceRow(claim=e.group("claim").strip(),
                    status=e.group("status").upper(),
                    path=e.group("path").strip(),
                    symbol=(e.group("symbol") or "").strip())
        for e in _EVIDENCE_RE.finditer(stdout)
    ]
    return ParsedVerdict(verdict=verdict, claims_checked=claims, evidence=rows,
                         task_id=tm.group(1).strip() if tm else None,
                         verdict_line_count=len(all_verdict_lines))


@dataclass
class VerdictJudgement:
    verdict: str
    accepted: bool
    reason: str
    checked_paths: int = 0
    real_paths: int = 0


def _tracked(repo_root: Path, rel: str) -> Optional[bool]:
    """True if git tracks this path, False if it demonstrably does not,
    None if we could not find out.

    The third return is the point. "I could not run the check" and "the check
    failed" are different answers, and only one of them accuses the vendor.

    os.path.exists() is not enough: the vendor runs in the live tree with write
    permission, so it can create the files it then cites. An untracked file
    produces no diff and no commit, so it satisfied both "exists" and "no edit"
    at once. Tracking is the property a vendor cannot manufacture without
    committing, which it is forbidden to do.
    """
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", "--", rel],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        # Timeout, missing git binary, OSError. We learned NOTHING about this
        # path. Returning False here would report "the vendor cited a file git
        # does not track" -- an accusation -- on the strength of our own tooling
        # failing. Measured return codes: 0 = tracked, 1 = genuinely untracked,
        # 128 = git could not answer (not a repo, etc).
        logger.debug("Swallowed exception in _tracked", exc_info=True)
        return None
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None


def judge_clean(
    parsed: ParsedVerdict,
    repo_root: Path,
    has_in_scope_diff: bool,
    doc_path: Optional[str] = None,
    task_id: Optional[str] = None,
) -> VerdictJudgement:
    """Decide whether a declared CLEAN verdict may be accepted.

    Every condition is checkable from artifacts alone -- the text the vendor
    emitted and the filesystem. None of them asks what the vendor meant.

    A rejected CLEAN becomes INSUFFICIENT, never FIXED and never a silent
    failure: the task did run, it simply did not establish its claim.
    """
    if parsed.verdict != CLEAN:
        return VerdictJudgement(INSUFFICIENT, False, "no CLEAN verdict declared")

    # (a) A CLEAN verdict alongside an edit is incoherent: either the doc was
    #     already correct, or it needed changing. Not both.
    if has_in_scope_diff:
        return VerdictJudgement(
            INSUFFICIENT, False,
            "declared CLEAN but also edited the file in scope -- incoherent",
        )

    # (b) Enough claims to constitute an audit.
    if parsed.claims_checked < MIN_CLAIMS:
        return VerdictJudgement(
            INSUFFICIENT, False,
            f"CLAIMS_CHECKED={parsed.claims_checked} < {MIN_CLAIMS}",
        )

    # (c) The evidence rows must actually be there. A CLAIMS_CHECKED integer on
    #     its own is a number the vendor typed, not evidence.
    if len(parsed.evidence) < MIN_CLAIMS:
        return VerdictJudgement(
            INSUFFICIENT, False,
            f"only {len(parsed.evidence)} evidence row(s) for "
            f"CLAIMS_CHECKED={parsed.claims_checked}",
        )

    # (d) Exactly one verdict. Two blocks -- an early CLEAN and a closing
    #     INSUFFICIENT -- let a vendor hedge and pass on whichever the parser
    #     reaches first.
    if parsed.verdict_line_count != 1:
        return VerdictJudgement(
            INSUFFICIENT, False,
            f"{parsed.verdict_line_count} VERDICT lines found; exactly 1 required",
        )

    # (e) The block must name the task it belongs to. Accepted blocks are stored
    #     in the ledger and echoed in relays, both readable by the vendor, so an
    #     unbound block can be lifted verbatim from a previously-accepted task
    #     and replayed against a different doc.
    if task_id and parsed.task_id != task_id:
        return VerdictJudgement(
            INSUFFICIENT, False,
            f"verdict block declares TASK_ID={parsed.task_id!r}, dispatched task "
            f"is {task_id!r} -- replayed or misaddressed",
        )

    # (f) Cited paths must be TRACKED, not merely present. See _tracked().
    distinct = {r.bare_path for r in parsed.evidence}
    _states = {p: _tracked(repo_root, p) for p in distinct if p}
    real = {p for p, t in _states.items() if t is True}
    unknown = {p for p, t in _states.items() if t is None}
    if len(real) < MIN_DISTINCT_PATHS:
        # Name the unknowns separately. Folding them in with the untracked
        # produces "only 2 of 3 cited paths are git-tracked", which reads as the
        # vendor citing a file that is not there -- when what actually happened
        # may be that git timed out under load. The verdict is INSUFFICIENT
        # either way, but the refusal log is read by humans deciding whether a
        # vendor did its job, and a wrong reason there costs a correct vendor.
        if unknown:
            return VerdictJudgement(
                INSUFFICIENT, False,
                f"could not determine git tracking for {len(unknown)} of "
                f"{len(distinct)} cited path(s) ({', '.join(sorted(unknown))}) -- "
                f"NOT a finding against the vendor; the check itself did not run",
                checked_paths=len(distinct), real_paths=len(real),
            )
        return VerdictJudgement(
            INSUFFICIENT, False,
            f"only {len(real)} of {len(distinct)} cited path(s) are git-tracked "
            f"(need >={MIN_DISTINCT_PATHS})",
            checked_paths=len(distinct), real_paths=len(real),
        )

    # (g) THE ANTI-GUESSING CONTROL. Each row carries a literal symbol that must
    #     appear verbatim in BOTH the doc under audit and the file cited as
    #     evidence. Path existence alone is trivially satisfied by paths every
    #     model can guess from the repo name -- pyproject.toml, AGENTS.md,
    #     DECISIONS.md -- with the doc never opened. A token shared by the doc
    #     and the cited file cannot be produced without reading the doc, which
    #     is the work being claimed.
    if doc_path:
        doc_file = repo_root / doc_path
        try:
            doc_text = doc_file.read_text(errors="replace")
        except OSError:
            doc_text = ""
        if not doc_text:
            return VerdictJudgement(
                INSUFFICIENT, False,
                f"cannot read the doc under audit ({doc_path}) to corroborate evidence",
            )
        corroborated = 0
        for row in parsed.evidence:
            sym = row.bare_symbol
            if len(sym) < 3:
                continue  # too short to be distinctive; not counted, not fatal
            if sym not in doc_text:
                continue
            # The symbol corroborates if it appears in the cited file's CONTENT,
            # or if it IS the cited file's name. The second case is real
            # evidence for the commonest kind of doc claim -- "X.jsx exists" --
            # and a file does not normally contain its own filename, so
            # content-only matching rejected it. Anti-fabrication is untouched:
            # the path must still be git-tracked, and the symbol must still
            # appear in the doc, so neither can be produced without reading it.
            if sym == PurePosixPath(row.bare_path).name:
                corroborated += 1
                continue
            try:
                cited = (repo_root / row.bare_path).read_text(errors="replace")
            except OSError:
                continue
            if sym in cited:
                corroborated += 1
        if corroborated < MIN_CLAIMS:
            return VerdictJudgement(
                INSUFFICIENT, False,
                f"only {corroborated} evidence row(s) carry a literal symbol found in "
                f"BOTH {doc_path} and the cited file (need >={MIN_CLAIMS}) -- cited "
                f"paths are not tied to the doc under audit",
                checked_paths=len(distinct), real_paths=len(real),
            )

    # A CLEAN verdict whose own evidence contains a FALSE/STALE row contradicts
    # itself -- the vendor found a problem and then reported none.
    contradictory = [r for r in parsed.evidence if r.status in ("FALSE", "STALE")]
    if contradictory:
        return VerdictJudgement(
            INSUFFICIENT, False,
            f"declared CLEAN but cited {len(contradictory)} FALSE/STALE claim(s) "
            f"-- self-contradictory",
            checked_paths=len(distinct), real_paths=len(real),
        )

    return VerdictJudgement(
        CLEAN, True,
        f"{parsed.claims_checked} claims checked, {len(real)} distinct real paths cited",
        checked_paths=len(distinct), real_paths=len(real),
    )
