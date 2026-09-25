"""Agent OS — scan a repo for a safe documentation fix and prepare it.

Tracks S1, S2 and S4 of ``.brain/strategy/BRIEFS/AGENT_OS_SAFE_FIRST_PR.md``.

That brief path is GITIGNORED (``.gitignore`` ignores ``.brain/*`` with explicit
negations), so it is local-only by policy -- it is not missing from this branch,
and a fresh clone will not have it. Carrying its guardrails here so the code is
not left without its acceptance criteria:

  - documentation targets only; deny by default on path shape AND location
  - never touch .github/, scripts/, .claude/, .brain/, or anything matching a
    sensitive keyword token
  - the safety gate re-runs at WRITE time, not only at proposal time
  - NO automated push or merge -- PR creation stays a human act
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .safe_gate import SafetyVerdict


@dataclass(frozen=True)
class SafeTask:
    path: str
    kind: str
    description: str
    evidence: str


@dataclass
class Patch:
    path: str
    original_text: str
    patched_text: str
    claims: List[str]


_DISALLOWED_DIRS = frozenset({".github", "scripts", ".claude", ".brain"})
_SENSITIVE_KEYWORDS = ("secret", "credential", "token", "key", ".env")
# Allowed SHAPES. Anything else -- extensionless, dotfile, or an unlisted
# extension -- is denied even inside docs/, because the allow-list is the
# thing standing between an agent and a file it should never edit.
_DOC_EXTS = frozenset({".md", ".rst", ".txt", ".markdown"})
_CODE_CONFIG_EXTS = frozenset({".py", ".sh", ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini"})

_MD_LINK_RE = re.compile(r"!?\[([^\]]+)\]\(([^)\s]+)(?:\s+(?:\"[^\"]*\"|\'[^\']*\'))?\)")
_EXTERNAL_ANCHOR_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+\-]*:|^//|^#")


def _run_git(argv: List[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(argv)} failed: {result.stderr.strip()}")
    return result.stdout


def _git_tracked_files(repo: Path) -> List[str]:
    try:
        output = _run_git(["ls-files"], repo)
    except RuntimeError:
        return []
    return [line for line in output.splitlines() if line]


def _repo_path(repo_root: Optional[object]) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()


def is_safe_target(path: object, repo_root: Optional[object] = None) -> Tuple[bool, str]:
    repo = _repo_path(repo_root)
    try:
        p = Path(path)
        candidate = p.resolve() if p.is_absolute() else (repo / p).resolve()
    except (OSError, ValueError) as exc:
        return False, f"denied by traversal rule: invalid path ({exc})"

    try:
        rel = candidate.relative_to(repo)
    except ValueError:
        return False, "denied by traversal rule: path escapes repo root"

    rel_parts = rel.parts

    if any(part in _DISALLOWED_DIRS for part in rel_parts):
        return False, "denied by disallowed directory rule: .github/, scripts/, .claude/, .brain/"

    lower = str(candidate).lower()
    # Match on path TOKENS, not raw substring. "key" inside "monkey.md" is not a
    # secret, and a deny-list that cries wolf gets switched off -- costing the
    # rules that DO matter. Splitting on non-alphanumerics keeps ".env",
    # "api_key", "my-token" and "secrets/" while sparing "monkey".
    _tokens = set(re.split(r"[^a-z0-9]+", lower)) - {""}
    for kw in _SENSITIVE_KEYWORDS:
        kw_clean = kw.lstrip(".")
        if kw_clean in _tokens:
            return False, f"denied by sensitive keyword rule: path contains '{kw}'"

    if candidate.suffix.lower() in _CODE_CONFIG_EXTS:
        return False, f"denied by code/config extension rule: {candidate.suffix}"

    if rel_parts and rel_parts[0] in ("docs", "examples"):
        # Location alone is NOT sufficient. The original rule allowed anything
        # sitting under docs/, which cleared docs/.netrc (credentials),
        # docs/Dockerfile, docs/deploy and docs/style.css -- none of which are
        # documentation. A path must be in an allowed PLACE *and* have an
        # allowed SHAPE. Found by the review lane against this module's own
        # deny-list; the gate was failing OPEN, the direction that matters.
        if candidate.suffix.lower() not in _DOC_EXTS:
            return (
                False,
                f"denied: {candidate.name!r} is under an allowed directory but "
                f"is not a documentation file (allowed: "
                f"{', '.join(sorted(_DOC_EXTS))})",
            )
        return True, "allowed: documentation file under docs/ or examples/"

    if len(rel_parts) == 1 and candidate.suffix.lower() == ".md":
        return True, "allowed: markdown file at repo root"

    return False, "denied by unknown shape: path is not under docs/, examples/, or a root *.md"


def _resolve_local_target(repo: Path, source: str, url: str) -> Optional[Path]:
    raw = url.split("#", 1)[0].split("?", 1)[0].strip()
    if not raw or _EXTERNAL_ANCHOR_RE.match(raw):
        return None

    if raw.startswith("/"):
        target = Path(raw.lstrip("/"))
    else:
        target = Path(source).parent / raw

    try:
        resolved = (repo / target).resolve()
        resolved.relative_to(repo)
    except (ValueError, OSError):
        return None

    return resolved


def scan_for_safe_tasks(repo_root: object) -> List[SafeTask]:
    repo = Path(repo_root).resolve()
    try:
        tracked = set(_git_tracked_files(repo))
    except RuntimeError:
        return []

    tasks: List[SafeTask] = []
    for path in sorted(tracked):
        if Path(path).suffix.lower() != ".md":
            continue
        if not is_safe_target(path, repo)[0]:
            continue

        file_path = repo / path
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line in text.splitlines():
            for match in _MD_LINK_RE.finditer(line):
                url = match.group(2).strip()
                resolved = _resolve_local_target(repo, path, url)
                if resolved is None:
                    continue
                rel = resolved.relative_to(repo).as_posix()
                if rel not in tracked:
                    tasks.append(
                        SafeTask(
                            path=path,
                            kind="broken_link",
                            description=f"markdown link to {url!r} is broken",
                            evidence=line,
                        )
                    )

    return sorted(tasks, key=lambda t: (t.path, t.kind, t.description, t.evidence))


def _remove_broken_link(repo: Path, tracked: set, source: str, line: str) -> str:
    for match in _MD_LINK_RE.finditer(line):
        url = match.group(2).strip()
        resolved = _resolve_local_target(repo, source, url)
        if resolved is None:
            continue
        try:
            rel = resolved.relative_to(repo).as_posix()
        except ValueError:
            continue
        if rel not in tracked:
            replacement = match.group(1) if not match.group(0).startswith("!") else ""
            return line[: match.start()] + replacement + line[match.end() :]
    return line


def _current_branch(repo: Path) -> Optional[str]:
    try:
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo).strip()
    except RuntimeError:
        return None
    return branch if branch and branch != "HEAD" else None


def propose_patch(repo_root: object, task: SafeTask) -> Patch:
    allowed, reason = is_safe_target(task.path, repo_root)
    if not allowed:
        raise ValueError(f"refusing to patch unsafe path {task.path}: {reason}")

    repo = Path(repo_root).resolve()
    file_path = repo / task.path
    if not file_path.is_file():
        raise ValueError(f"source file does not exist: {task.path}")

    try:
        tracked = set(_git_tracked_files(repo))
    except RuntimeError:
        tracked = set()

    if task.kind == "broken_link":
        patched_text = _remove_broken_link(repo, tracked, task.path, task.evidence)
    else:
        patched_text = task.evidence

    claims = [f"FILE EXISTS: {task.path}"]
    branch = _current_branch(repo)
    if branch:
        claims.append(f"GIT BRANCH EXISTS: {branch}")

    # WHOLE-FILE semantics. _remove_broken_link works on a single LINE, but a
    # Patch must carry the entire file: apply_patch writes patched_text as the
    # file's whole content, and its staleness check compares against the file on
    # disk. Storing the line here made every multi-line document fail that
    # comparison -- the feature could never apply to a real doc. It failed
    # CLOSED, so nothing was ever destroyed, but nothing could ever succeed.
    _full_before = (repo / task.path).read_text(encoding="utf-8")
    if task.evidence not in _full_before:
        raise ValueError(
            f"the line this task was built from is no longer in {task.path!r}; "
            f"the file changed since the scan"
        )
    _full_after = _full_before.replace(task.evidence, patched_text, 1)

    return Patch(
        path=task.path,
        original_text=_full_before,
        patched_text=_full_after,
        claims=claims,
    )


def apply_patch(repo_root: object, patch: Patch) -> int:
    """Write ``patch.patched_text`` to ``patch.path`` and return bytes written.

    The safe-target gate is re-run at the moment of writing, because the
    caller may have mutated ``patch.path`` after ``propose_patch``.  If the
    gate denies the path we raise ``PermissionError`` with the deny reason.
    We also refuse if the file on disk no longer matches ``patch.original_text``.
    """
    allowed, reason = is_safe_target(patch.path, repo_root)
    if not allowed:
        raise PermissionError(reason)

    repo = _repo_path(repo_root)
    file_path = repo / patch.path

    try:
        current = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"file {patch.path!r} does not exist; cannot apply patch"
        ) from exc

    if current != patch.original_text:
        raise ValueError(
            f"file {patch.path!r} changed since the patch was proposed"
        )

    encoded = patch.patched_text.encode("utf-8")
    file_path.write_bytes(encoded)
    return len(encoded)


def create_branch_and_commit(
    repo_root: object,
    patch: Patch,
    branch: str,
    message: Optional[str] = None,
) -> str:
    """Create ``branch`` and commit only the patched file.

    The commit is scoped to ``patch.path`` so that other staged changes in the
    shared index are not included.  Returns the full 40-character SHA of the
    new commit.

    Raises:
        ValueError: if ``branch`` already exists.
        RuntimeError: if git checkout or commit fails.
    """
    repo = _repo_path(repo_root)

    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        raise ValueError(f"branch {branch!r} already exists")

    _run_git(["checkout", "-b", branch], repo)

    msg = message if message is not None else f"Apply safe patch to {patch.path}"
    _run_git(["commit", "-m", msg, "--", patch.path], repo)

    return _run_git(["rev-parse", "HEAD"], repo).strip()


def pr_description(patch: Patch, verified: dict, verdict: SafetyVerdict) -> str:
    """Return a plain-text PR body that reports only verified facts.

    Confirmed claims from ``verified["confirmed"]`` may be stated as facts.
    Refuted or unverifiable claims are never stated as facts; instead the body
    reports how many claims were not verified.  If ``verdict.safe`` is False,
    the body leads with that and the reason.
    """
    confirmed = list(verified.get("confirmed") or [])
    refuted = list(verified.get("refuted") or [])
    unverifiable = list(verified.get("unverifiable") or [])
    not_verified = refuted + unverifiable

    lines: List[str] = []

    if not verdict.safe:
        lines.append(f"Not safe to propose: {verdict.reason}")

    if confirmed:
        if lines:
            lines.append("")
        lines.append("Confirmed facts:")
        for claim in confirmed:
            lines.append(f"* {claim}")
    else:
        if lines:
            lines.append("")
        lines.append("No claims were confirmed.")

    if not_verified:
        lines.append("")
        lines.append(
            f"{len(not_verified)} claim(s) were not verified "
            f"({len(refuted)} refuted, {len(unverifiable)} unverifiable) "
            "and are not stated as fact."
        )

    return "\n".join(lines)
