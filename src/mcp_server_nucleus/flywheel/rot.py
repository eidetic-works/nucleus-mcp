"""Rot -- find memory that is no longer true, before a later agent reads it as fact.

Dreaming only ever ADDED memory. A memory that is wrong is worse than none: every
later agent reads it as fact. This module is the other half -- checking the memory
already there -- and is deliberately split in two so a script does what a script can:

    Phase 0 (here, no agent)   extract the mechanically checkable claims from each
                               file and check them: does the path exist, is the SHA
                               reachable, is the line reference in range, does the
                               [[link]] point at a memory that exists.
    Phase 1 (external lanes)   the semantic residue -- "this number is still true".

Phase 0 never says STALE. A dead path is only evidence: a memory may say "X was
deleted", and then the dead path is the point. It says DEAD and lets a lane or a
human decide. What it can say with certainty is LIVE.

Nothing here writes to the memory directory. It is read-only by construction.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

LIVE, DEAD, AMBIGUOUS, UNRESOLVED, SKIPPED = "LIVE", "DEAD", "AMBIGUOUS", "UNRESOLVED", "SKIPPED"
INDEX_FILES = {"MEMORY.md", "index_archive.md"}

_PATH_EXT = r"(?:py|sh|md|json|jsonl|yaml|yml|toml|html|tsx?|jsx?|txt|sql|plist|cfg|ini)"
# A backticked path-shaped token, optionally with :line.
_PATH_RE = re.compile(r"`((?:~|\$HOME|/)?[A-Za-z0-9_@.+-]+(?:/[A-Za-z0-9_@.+*-]+)*\." + _PATH_EXT + r")(?::(\d+))?`")
_SHA_RE = re.compile(r"(?<![0-9A-Za-z_./-])([0-9a-f]{7,40})(?![0-9A-Za-z_-])")
_LINK_RE = re.compile(r"\[\[([A-Za-z0-9_.-]+)\]\]")
_FENCE_RE = re.compile(r"```.*?```", re.S)


@dataclass
class Claim:
    kind: str              # path | line | sha | link
    text: str
    status: str = SKIPPED
    detail: str = ""


@dataclass
class FileReport:
    name: str
    claims: List[Claim] = field(default_factory=list)
    identity: List[str] = field(default_factory=list)   # categories that excluded it

    def count(self, status: str) -> int:
        return sum(1 for c in self.claims if c.status == status)

    @property
    def dead(self) -> List[Claim]:
        return [c for c in self.claims if c.status == DEAD]

    @property
    def checkable(self) -> int:
        return sum(1 for c in self.claims if c.status in (LIVE, DEAD, AMBIGUOUS))

    @property
    def lane_eligible(self) -> bool:
        return not self.identity


def memory_files(memory_dir: Path) -> List[Path]:
    return sorted(p for p in Path(memory_dir).glob("*.md") if p.name not in INDEX_FILES)


def digest_all(memory_dir: Path) -> Dict[str, str]:
    """sha256 of every memory file. The integrity control: before == after."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(memory_dir).glob("*.md"))}


def _slug(text: str) -> Optional[str]:
    m = re.search(r"^name:\s*(\S+)", text, re.M)
    return m.group(1).strip("\"'") if m else None


def sibling_memory_dirs(memory_dir: Path) -> List[Path]:
    """Every project's memory directory next to this one. A memory may link to one
    written under a different project (`~/.claude/projects/*/memory`); resolving
    links inside a single directory reported 47% of them dead."""
    root = Path(memory_dir).parent.parent
    dirs = [d for d in sorted(root.glob("*/memory")) if d.is_dir()]
    return dirs or [Path(memory_dir)]


def memory_names(memory_dir: Path) -> Set[str]:
    """Every name a [[link]] may legitimately resolve to: file stem and `name:` slug,
    across all sibling memory directories."""
    names: Set[str] = set()
    for p in (q for d in sibling_memory_dirs(memory_dir) for q in d.glob("*.md")):
        names.add(p.stem)
        try:
            s = _slug(p.read_text(encoding="utf-8", errors="replace")[:1500])
        except OSError:
            s = None
        if s:
            names.add(s)
    return names


def extract(text: str) -> List[Claim]:
    """The mechanically checkable claims in one memory file. Fenced code is ignored:
    an example command is not a claim about the repo."""
    body = _FENCE_RE.sub(" ", text)
    out: List[Claim] = []
    seen: Set[Tuple[str, str]] = set()

    def add(kind: str, txt: str) -> None:
        if (kind, txt) not in seen:
            seen.add((kind, txt))
            out.append(Claim(kind, txt))

    for m in _PATH_RE.finditer(body):
        add("line" if m.group(2) else "path", m.group(1) + (f":{m.group(2)}" if m.group(2) else ""))
    for m in _LINK_RE.finditer(body):
        add("link", m.group(1))
    for m in _SHA_RE.finditer(body):
        tok = m.group(1)
        # a SHA has both letters and digits; this drops words and pure numbers
        if re.search(r"[a-f]", tok) and re.search(r"\d", tok):
            add("sha", tok)
    return out


class Checkout:
    """One repo root, with a basename index so a bare `store.py` can be located."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._base: Optional[Dict[str, List[str]]] = None

    @property
    def exists(self) -> bool:
        return (self.root / ".git").exists()

    def basename_index(self) -> Dict[str, List[str]]:
        if self._base is None:
            self._base = {}
            r = subprocess.run(["git", "-C", str(self.root), "ls-files"],
                               capture_output=True, text=True, errors="replace")
            for rel in r.stdout.splitlines():
                self._base.setdefault(Path(rel).name, []).append(rel)
        return self._base

    def is_tracked(self, path: Path) -> bool:
        """True if `path` is a git-tracked file of this checkout."""
        try:
            rel = str(Path(path).resolve().relative_to(self.root.resolve()))
        except ValueError:
            return False
        if getattr(self, "_tracked", None) is None:
            r = subprocess.run(["git", "-C", str(self.root), "ls-files"],
                               capture_output=True, text=True, errors="replace")
            self._tracked = set(r.stdout.splitlines())
        # a directory is tracked if any tracked file lives under it: ls-files lists files only,
        # so a lane citing `pkg/test` (a tracked directory) was refused as untracked
        return rel in self._tracked or any(t.startswith(rel + "/") for t in self._tracked)

    def suffix_matches(self, path: str) -> List[str]:
        """Tracked files whose path ENDS with `path`.

        A memory usually writes a path relative to the subdirectory it is talking about
        (`tests/e2e/x.py` for `mcp-server-nucleus/tests/e2e/x.py`), not to the repo root.
        Found by a lane overturning a mechanical DEAD verdict on exactly this."""
        self.basename_index()
        want = "/" + path.lstrip("/")
        candidates = (self._base or {}).get(Path(path).name, [])
        return [r for r in candidates if ("/" + r).endswith(want)]

    def has_commit(self, sha: str) -> bool:
        return subprocess.run(["git", "-C", str(self.root), "cat-file", "-e", f"{sha}^{{commit}}"],
                              capture_output=True).returncode == 0


def _expand(p: str) -> str:
    return str(Path(p.replace("$HOME", "~")).expanduser()) if p.startswith(("~", "$HOME")) else p


def check(claims: Iterable[Claim], checkouts: Sequence[Checkout], names: Set[str]) -> None:
    live = [c for c in checkouts if c.exists]
    for c in claims:
        if c.kind == "link":
            # A [[link]] to a memory not yet written is ALLOWED by convention (it marks
            # something worth writing later), so a dangling one is not evidence of rot.
            # Measured: 178 of 377 links dangle even across every project's memory.
            c.status = LIVE if c.text in names else UNRESOLVED
            c.detail = "" if c.status == LIVE else "orphan link (allowed by convention)"
        elif c.kind == "sha":
            hit = next((k.root.name for k in live if k.has_commit(c.text)), None)
            c.status, c.detail = (LIVE, hit) if hit else (DEAD, "commit not found in any checkout")
        else:
            path, _, line = c.text.partition(":") if c.kind == "line" else (c.text, "", "")
            if "*" in path:
                c.status, c.detail = SKIPPED, "glob"
                continue
            found = _resolve(_expand(path), live)
            if not found and "/" not in path:
                # Located by `git ls-files`, which cannot see untracked or ignored
                # files. Absence from that set is not absence from the disk.
                c.status, c.detail = UNRESOLVED, "bare filename not among tracked files"
            elif not found:
                c.status, c.detail = DEAD, "no such path in any checkout"
            elif len(found) > 1:
                c.status, c.detail = AMBIGUOUS, f"{len(found)} matches"
            else:
                c.status, c.detail = LIVE, str(found[0])
                if line:
                    try:
                        n = sum(1 for _ in Path(found[0]).open(errors="replace"))
                    except OSError:
                        n = 0
                    if int(line) > n:
                        c.status, c.detail = DEAD, f"line {line} but the file has {n}"


def _resolve(path: str, live: Sequence[Checkout]) -> List[Path]:
    p = Path(path)
    if p.is_absolute():
        return [p] if p.exists() else []
    hits: List[Path] = []
    for k in live:
        direct = k.root / path
        if direct.exists():
            hits.append(direct)
    if hits:
        return hits[:1] if len(hits) == 1 else hits
    if "/" in path:  # qualified but not from the root: try it as a suffix of a tracked path
        for k in live:
            hits += [k.root / rel for rel in k.suffix_matches(path)]
        if hits:
            return hits
    if "/" not in path:  # a bare filename: find it by name
        for k in live:
            hits += [k.root / rel for rel in k.basename_index().get(path, [])]
    return hits


# --- identity ---------------------------------------------------------------
#
# The set of identity strings already exists in the pseudonymity guard, which is
# the single source of truth. It is READ at runtime, never copied, so no identity
# string enters this file, its tests, or the repo history.

_ARRAY_RE = re.compile(r"^(?P<name>\w+)=\(\s*$(?P<body>.*?)^\)", re.M | re.S)
_QUOTED_RE = re.compile(r"""(?<!\\)(?:"(?P<d>(?:[^"\\]|\\.)*)"|'(?P<s>[^']*)')""")
class RotError(RuntimeError):
    """Raised when the audit cannot establish what it needs to be safe."""


_NAME_HINTS = ("user_", "identity", "employ", "legal", "pseudonym", "corporate", "moonlight")


def identity_terms(guard_file: Path) -> Dict[str, List[str]]:
    """{array_name: [terms]} parsed from the guard's bash arrays.

    Comment lines are skipped so the prose in the guard's header is not mistaken
    for a term. Returns {} if the guard is unreadable -- and the caller must treat
    that as 'cannot tell', never as 'nothing sensitive'."""
    try:
        text = Path(guard_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    out: Dict[str, List[str]] = {}
    for m in _ARRAY_RE.finditer(text):
        terms = []
        for line in m.group("body").splitlines():
            if line.strip().startswith("#"):
                continue
            for q in _QUOTED_RE.finditer(line):
                terms.append(q.group("d") if q.group("d") is not None else q.group("s"))
        if terms:
            out[m.group("name")] = terms
    return out


def classify_identity(name: str, text: str, terms: Dict[str, List[str]]) -> List[str]:
    """Why a file must not go to an external vendor. Empty list = nothing found.

    A file about identity may not CONTAIN an identity string, so the file name is
    checked too."""
    why: List[str] = []
    low = text.lower()
    for arr, items in terms.items():
        ci = "ci" in arr
        is_regex = "regex" in arr
        for t in items:
            if not t:
                continue
            if is_regex:
                # An unparseable regex must not silently pass a file: treat it as a hit.
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", FutureWarning)  # the guard's own regexes
                        hit = re.search(t, text, re.I if ci else 0) is not None
                except re.error:
                    hit = True
            else:
                hit = (t.lower() in low) if ci else (t in text)
            if hit:
                why.append(f"term:{arr}")
                break
    if any(h in name.lower() for h in _NAME_HINTS):
        why.append("name")
    return why


def load_identity_terms(guard_file: Path) -> Dict[str, List[str]]:
    """identity_terms, but refusing to continue without any.

    An unreadable or empty term list would make every file look clean, and a
    clean file is one that may be sent to an external vendor. Absence of the
    filter is not the absence of sensitive content -- so this fails closed."""
    terms = identity_terms(guard_file)
    if not terms:
        raise RotError(
            f"no identity terms could be read from {guard_file}; refusing to decide "
            f"which memory files are safe to send to a vendor")
    return terms



# --- Phase 1: lane tasks, controls, and the judge ---------------------------

from ..runtime.lane import verdict as V  # noqa: E402  (the existing 3-state judge)

STALE_VERDICT = "STALE"


@dataclass
class Task:
    task_id: str
    path: str                      # absolute path of the memory file to audit
    kind: str                      # "real" | "control"
    expected: Optional[str] = None # controls only: the verdict the chief planted
    prompt: str = ""


MAX_CLAIMS = 6

PROMPT = """\
You are auditing ONE memory file for claims that are no longer true. READ-ONLY.
Do not edit, create, move or delete any file. Do not run git commands that change anything.

STEP 0 (mandatory, do it first): run
  cd {repo} && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git rev-parse main
and print all three lines. If `git rev-parse main` fails because there is no local `main`
branch, run `git rev-parse origin/main` for the tip SHA instead. Proceed ONLY if the branch
is `main`, or HEAD is detached (`--abbrev-ref` prints `HEAD`) and the HEAD SHA equals the
main tip SHA. If HEAD is on any other branch, or detached at a SHA that is not main's tip,
STOP and print VERDICT: INSUFFICIENT.

The memory file to audit (absolute path): {path}
The repository it describes: {repo}  (other checkouts that may hold a referenced file:
~/nucleus, ~/ai-mvp-backend, ~/gentlequest)

READ ONLY git-tracked files inside the four checkouts. NEVER open anything under `.brain/`,
`~/.claude`, `~/Library`, `~/.ssh`, `~/career`, dotfiles, credentials or `.env` files, or any OTHER memory file.
If a claim would need such a file, do NOT read it: mark it UNVERIFIABLE and leave it unchecked.

Verify AT MOST {max_claims} claims, then STOP. Choose the {max_claims} most checkable -- a file path,
a function or constant, a PR or commit, a number -- and verify each against the repository as it
is NOW. Prefer claims you can grep. Skip pure opinion. Do not audit the rest of the file; say how
many you left unchecked. Between tool calls write at most one short line.
{hints}
Finish with EXACTLY this block and nothing after it:

VERDICT: CLEAN | STALE | INSUFFICIENT
TASK_ID: {task_id}
CLAIMS_CHECKED: <integer>
UNCHECKED: <integer>
- <the claim, one line> | TRUE | <repo-relative path>:<line> | <a token that appears in BOTH the memory file and that path>
- <the claim, one line> | STALE | <repo-relative path> | <a token that appears in the memory file>

Rules:
- CLEAN: every checked claim is TRUE. Needs at least 3 rows, citing 3 distinct tracked files.
- STALE: at least one claim is FALSE or STALE. Each such row's last field must be a token
  that appears VERBATIM in the memory file (it proves you read the claim).
- INSUFFICIENT: you could not establish either. This is a valid answer; say why in one line
  BEFORE the block. Never guess CLEAN.
"""


def build_prompt(task_id: str, path: str, repo: str, report: Optional[FileReport] = None) -> str:
    hints = ""
    if report is not None and report.dead:
        lines = "\n".join(f"  - {c.kind} `{c.text}`: {c.detail}" for c in report.dead[:8])
        hints = ("\nA mechanical pre-check could not find these. They are LEADS, not verdicts -- "
                 "a memory may say a file was deleted, in which case a dead path is correct:\n" + lines + "\n")
    return PROMPT.format(repo=repo, path=path, task_id=task_id, hints=hints, max_claims=MAX_CLAIMS)


CONTROL_EXPECTED = {
    "ctl-clean": V.CLEAN,
    "ctl-stale": STALE_VERDICT,
    "ctl-outside": V.INSUFFICIENT,
    "ctl-empty": V.INSUFFICIENT,
}


def default_controls_dir() -> Path:
    import os
    return Path(os.environ.get("NUCLEUS_ROT_CONTROLS_DIR") or Path.home() / ".nucleus" / "rot" / "controls")


def write_controls(directory: Path, source_dir: Optional[Path] = None, tag: str = "") -> List[Task]:
    """Copy the four planted memory files, with chief-owned ground truth, to `directory`.

    The BODIES live OUTSIDE the repository, in `source_dir` (default ~/.nucleus/rot/controls),
    and never in this file. Measured: a lane auditing a control searched the repo, found the
    body verbatim in this module, and reported "this is a planted control, expected STALE".
    A control whose answer key sits in the tree the lane searches is not a blind check.
    """
    src = Path(source_dir) if source_dir else default_controls_dir()
    d = Path(directory); d.mkdir(parents=True, exist_ok=True)
    tasks = []
    for name, expected in CONTROL_EXPECTED.items():
        body_file = src / f"{name}.md"
        if not body_file.exists():
            raise RotError(f"control body {body_file} is missing; controls are deliberately kept out of the repo")
        tid = f"{name}-{tag}" if tag else name
        f = d / f"{tid}.md"; f.write_text(body_file.read_text())
        tasks.append(Task(task_id=tid, path=str(f), kind="control", expected=expected))
    return tasks


@dataclass
class Judgement:
    verdict: str
    accepted: bool
    reason: str = ""
    stale_rows: List["V.EvidenceRow"] = field(default_factory=list)


def judge_audit(stdout: str, task: Task, repo_root: Path) -> Judgement:
    """Judge one lane's output. CLEAN is delegated UNCHANGED to the existing judge;
    STALE gets its own strict rule; everything unprovable is INSUFFICIENT."""
    if is_transport_failure(stdout):
        return Judgement(RETRY, False, "vendor outage (retryable); says nothing about the file")
    parsed = V.parse_verdict(stdout)
    if parsed.verdict is None:
        return Judgement(V.INSUFFICIENT, False, "no VERDICT block")
    if parsed.task_id != task.task_id:
        return Judgement(V.INSUFFICIENT, False,
                         f"TASK_ID {parsed.task_id!r} is not {task.task_id!r}")
    if parsed.verdict == V.INSUFFICIENT:
        return Judgement(V.INSUFFICIENT, True, "declared insufficient")
    checkouts = [Checkout(Path(repo_root))] + [Checkout(Path.home() / d) for d in ("nucleus", "ai-mvp-backend", "gentlequest")]
    leaked = [r.path for r in parsed.evidence if _is_private_citation(r.bare_path, checkouts)]
    if leaked:
        return Judgement(V.INSUFFICIENT, False,
                         f"cited a private path ({leaked[0]}); the lane read outside the tracked repo")
    if parsed.verdict == V.CLEAN:
        j = V.judge_clean(parsed, Path(repo_root), has_in_scope_diff=False,
                          doc_path=task.path, task_id=task.task_id)
        return Judgement(j.verdict, j.accepted, j.reason)
    if parsed.verdict == STALE_VERDICT:
        rows = [r for r in parsed.evidence if r.status in ("STALE", "FALSE")]
        if not rows:
            return Judgement(V.INSUFFICIENT, False, "declared STALE with no STALE/FALSE row")
        try:
            doc = Path(task.path).read_text(errors="replace")
        except OSError:
            return Judgement(V.INSUFFICIENT, False, "cannot read the memory file to corroborate")
        bad = [r for r in rows if not r.bare_symbol or r.bare_symbol not in doc]
        if bad:
            return Judgement(V.INSUFFICIENT, False,
                             f"{len(bad)} stale row(s) cite a token not in the memory file: "
                             f"{bad[0].bare_symbol!r}")
        return Judgement(STALE_VERDICT, True, f"{len(rows)} stale claim(s), each quoting the file", rows)
    return Judgement(V.INSUFFICIENT, False, f"unrecognised verdict {parsed.verdict!r}")


RETRY = "RETRY"
_TRANSPORT = re.compile(
    r"cognition\.ai/retryable[\"']?\s*:\s*true|Connection error|errorKind[\"']?\s*:\s*[\"']unavailable", re.I)
RELAY_RESULT_CAP = 3000


def is_transport_failure(stdout: str) -> bool:
    """A vendor outage says nothing about the memory file: retry, do not record a verdict.
    A result that carries a VERDICT block finished, whatever error text it quotes."""
    return bool(_TRANSPORT.search(stdout or "")) and "VERDICT:" not in (stdout or "")


def from_relay(path: Path) -> Tuple[str, bool]:
    """(result text, possibly_truncated) from a cross-vendor relay message.

    The relay keeps only the first RELAY_RESULT_CAP characters of a lane's result, and a
    lane's narration precedes its verdict block, so a long audit loses exactly the part
    the judge needs. Measured: a lane that finished a 13-claim audit arrived as 3000
    characters ending mid-block. The judge refuses such a result, which is correct; the
    remedy is a shorter task, not a looser judge."""
    import json
    msg = json.loads(Path(path).read_text())
    body = msg.get("body")
    body = json.loads(body) if isinstance(body, str) else (body or {})
    text = body.get("result", "") or ""
    return text, len(text) >= RELAY_RESULT_CAP


# --- who may be sent to an external lane ------------------------------------
#
# MEASURED 2026-09-21 (w3-06): a memory file that held no guard term pointed at a private
# personal-career document under .brain/, the lane followed the pointer, and excerpts left the
# machine. Two mechanisms leak: a file that is personal without containing a LISTED term, and a
# lane FOLLOWING A POINTER from a harmless memory into a private file. The guard's term list is the
# set of strings someone already thought of; it is not the boundary of "sensitive". So the rule is
# an ALLOWLIST -- only a file whose every pointer stays inside git-tracked repo files -- and a
# screen for personal subject matter on top of it.

PERSONAL_MARKERS = re.compile(
    r"\b(resume|r[ée]sum[ée]|CV|career|salary|employer|day.?job|moonlight\w*|appraisal|promotion|"
    r"linkedin|thrive|M\.?Tech|IIT|Assistant Manager|Management Trainee|\d+ years of experience|"
    r"years experience)\b", re.I)
# A credential in a memory file is the worst thing to send out. Screen the SHAPE of a secret, not a
# list of known ones: a long mixed token that is not a plain hex digest, and the well-known prefixes.
SECRET_SHAPES = re.compile(
    r"(sk_live_|sk_test_|cfut_|AKIA[0-9A-Z]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abprs]-|AIza[0-9A-Za-z_-]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?=[A-Za-z0-9_-]{32,}\b)(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+)")
SECRET_NAME_HINTS = ("token", "secret", "credential", "password", "passwd", "api_key", "apikey", "live_key", "private_key")
PRIVATE_PREFIXES = (".brain/", "~/.claude", "~/Library", "~/.ssh", "~/.cloudflared", "~/.nucleus", ".claude/", "~/career")


def private_pointers(claims: Iterable[Claim], checkouts: Sequence[Checkout]) -> List[str]:
    """Pointers a lane would have to READ that are not git-tracked repo files.

    A path that does not exist is harmless (nothing to read). One that exists but is untracked,
    ignored, under .brain/, or outside every checkout is a private pointer."""
    live = [c for c in checkouts if c.exists]
    out: List[str] = []
    for c in claims:
        if c.kind not in ("path", "line"):
            continue
        raw = c.text.partition(":")[0] if c.kind == "line" else c.text
        if raw.startswith(PRIVATE_PREFIXES) or "/.brain/" in raw or raw.startswith((".brain/")):
            out.append(f"{c.text}: private location")
            continue
        for f in _resolve(_expand(raw), live):
            if not any(k.is_tracked(f) for k in live):
                out.append(f"{c.text}: exists but is not a tracked repo file")
                break
    return out



_ALWAYS_PRIVATE = ("~/career", "~/.claude", "~/.ssh", "~/Library", "~/.cloudflared", "~/.nucleus")


def _is_private_citation(path: str, checkouts: Sequence[Checkout]) -> bool:
    """Did a lane cite something it should not have read?

    Decided by whether the cited file is TRACKED, not by its prefix. A repo-relative `.claude/...`
    or `.brain/...` path can be tracked (this repo commits hooks and plugins under `.claude/`, and
    parts of `.brain/`), and a prefix rule refused a correct result for citing one. What is private
    is a file that exists but is not tracked in any checkout, anything under a home-directory
    location such as ~/career, and an absolute path outside every checkout. A path that does not
    exist is harmless: nothing was read."""
    if path.startswith(_ALWAYS_PRIVATE):
        return True
    live = [c for c in checkouts if c.exists]
    found = _resolve(_expand(path), live)
    if not found:
        return path.startswith(("~/", "/Users/")) and not path.startswith(tuple(str(c.root) for c in live))
    return not any(k.is_tracked(f) for f in found for k in live)


def lane_allowlist(name: str, text: str, report: FileReport, checkouts: Sequence[Checkout]) -> List[str]:
    """Reasons a memory file must NOT go to an external lane. Empty list = allowed."""
    why: List[str] = list(report.identity)
    # underscores are word characters, so `project_thrive_x` has no \b before `thrive`: split them
    if PERSONAL_MARKERS.search(text) or PERSONAL_MARKERS.search(name.replace("_", " ").replace("-", " ")):
        why.append("personal-subject")
    if SECRET_SHAPES.search(text) or any(h in name.lower() for h in SECRET_NAME_HINTS):
        why.append("credential-shaped")
    why += private_pointers(report.claims, checkouts)
    return why
