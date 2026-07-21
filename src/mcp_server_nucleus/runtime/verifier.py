"""
DSoR Verifier — Ground-Truth Auditor for Agentic Claims
=========================================================
The missing "auditor" for the Decision System of Record (dsor.py).

dsor.py records WHAT an agent decided (DecisionEntry) but never checks
whether the decision — or any downstream claim an agent makes about its own
work ("I shipped X", "commit abc123 fixes it", "the endpoint returns 200")
— is actually TRUE. Every DecisionEntry is born with audit_status="PENDING"
and deterministic_anchor="NONE" and, absent this module, stays that way
forever.

This module closes that loop:

    Claim  -- decompose() -->  Anchor(s)  -- probe (read-only) -->  Evidence
                                                                        |
                                                                   adjudicate()
                                                                        |
                                                                     Verdict

  * Claim     — something an agent asserted (from a relay message, a DSoR
                ledger entry, or any other pipeline).
  * Anchor    — a DETERMINISTIC, machine-checkable proposition that would
                confirm or refute the claim (a git commit exists, an HTTP
                endpoint returns a value, a file contains a string, ...).
  * Evidence  — the result of actually probing an anchor. ``ok=True``
                (confirmed), ``ok=False`` (refuted), or ``ok=None``
                (UNVERIFIABLE — we could not determine truth, e.g. network
                down, anchor malformed, no deterministic anchor exists).
  * Verdict   — the final adjudication: CONFIRMED / REFUTED / UNVERIFIABLE
                / PARTIAL, with a human-readable rationale and remediation.

Design constraints (see feat/dsor-verifier task brief):
  * ADDITIVE ONLY — this file does not modify dsor.py, common.py, or
    llm_intent_analyzer.py; it only reads their public API.
  * stdlib only — no new pip dependencies. HTTP via urllib, git via
    subprocess.
  * Everything here is READ-ONLY at runtime except the optional
    ``Verifier(record=True)`` path, which writes ONLY to a
    ``DecisionLedger`` the caller explicitly constructs and passes in —
    never a hardcoded ``~/.nucleus`` or ``~/.brain`` path.
  * The LLM-assisted reasoner mirrors the lazy-import / fail-open pattern
    in ``llm_intent_analyzer.py`` so this module imports cleanly and runs
    correctly with zero API keys configured (it just falls back to the
    deterministic ``RuleReasoner``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .dsor import DecisionLedger

logger = logging.getLogger("nucleus.verifier")


# ============================================================
# MANDATORY-ANCHOR DOCTRINE (flag-gated; default OFF)
# ============================================================
#
# Implements ANCHOR_DOCTRINE.md §3 (class -> mandatory non-adjacent anchor)
# and REFEREE_CONFINEMENT.md §3 (anchor-KIND is doctrine-fixed; classification
# joins UP a strength lattice; unknown class -> maximally strong / manual).
#
# EVERYTHING below is inert unless NUCLEUS_VERIFIER_MANDATORY_ANCHORS is set to
# a truthy value. With the flag OFF the decompose/adjudicate paths are
# byte-identical to their pre-doctrine behavior — the flag is the ONLY switch.

_MANDATORY_ANCHORS_ENV = "NUCLEUS_VERIFIER_MANDATORY_ANCHORS"


def _mandatory_anchors_enabled() -> bool:
    """Is the mandatory-anchor doctrine turned on? Read live from the
    environment (not cached) so tests can flip it per-case."""
    return os.environ.get(_MANDATORY_ANCHORS_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


# Claim-class keyword table (C2 classifier). Deterministic, keyword-driven —
# per REFEREE_CONFINEMENT §3.1 the class -> anchor-KIND mapping lives in code,
# never proposed by a model. Each pattern is matched word-boundary against the
# lower-cased assertion. A claim may match several classes; on ambiguity we take
# the JOIN (union) of their mandatory requirements (§3.2 — fail-safe UP).
_CLASS_PATTERNS: Dict[str, List[str]] = {
    "DEPLOYED-LIVE": [r"\blive\b", r"\bin production\b", r"\bproduction\b", r"\bdeployed\b", r"\bprod\b"],
    "CODE-EXISTS": [r"\bbuilt\b", r"\bcommit\w*\b", r"\bmerged\b", r"\blanded\b", r"\bpushed\b", r"\bimplemented\b"],
    "BEHAVIOR-CORRECT": [r"\breturns?\b", r"\brenders?\b", r"\bcorrectly?\b", r"\bequals?\b", r"\bshows?\b", r"\bdisplays?\b", r"\bscoped?\b", r"\bitems\b", r"\bcount\b"],
    "SIDE-EFFECT": [r"\bemail\b", r"\bwebhook\b", r"\bfired\b", r"\bsent\b", r"\bnotification\b", r"\btriggered\b"],
    "LIVENESS": [r"\bcrons?\b", r"\bdaemon\b", r"\brunning\b", r"\bscheduled?\b", r"\bheartbeat\b"],
    "BUSINESS-STATE": [r"\bmerchants?\b", r"\busers?\b", r"\bactive\b", r"\bsubscribers?\b", r"\bcustomers?\b"],
    "IDENTITY": [r"\bauthenticated\b", r"\bidentity\b", r"\brole\b", r"\bcredential\b"],
    "ATTRIBUTION": [r"\battribution\b", r"\bauthored\b", r"\bproduced by\b", r"\bcaused\b"],
}

# The ⊤ (top) element of the lattice: an assertion matching no known class.
# ⊤ is "unknown class -> maximally strong / manual" (REFEREE_CONFINEMENT §3.3) —
# it is intentionally NOT present in _CLASS_MANDATORY, so it can never be
# satisfied by any deterministic anchor and thus never reaches CONFIRMED.
_TOP_CLASS = "UNKNOWN"

# For each class, the (kind, op) pairs that count as the MANDATORY non-adjacent
# anchor for that class (ANCHOR_DOCTRINE §3, "Mandatory anchor" column). A class
# absent from this map (SIDE-EFFECT / LIVENESS / BUSINESS-STATE / IDENTITY /
# ATTRIBUTION / ⊤) has no deterministic external anchor — it can only be
# manual/UNVERIFIABLE and must never be silently CONFIRMED.
_CLASS_MANDATORY: Dict[str, set] = {
    "CODE-EXISTS": {("git", "is_ancestor")},
    "DEPLOYED-LIVE": {("http", "json_get")},        # build-identity / deployed-SHA token
    "BEHAVIOR-CORRECT": {("http", "json_get")},     # value predicate on the live output
}


def classify_claim(assertion: str) -> "frozenset[str]":
    """Map an assertion to the set of plausible claim-classes (C2).

    Returns the JOIN (union) of every class whose keyword pattern matches —
    on ambiguity the confinement theorem demands we join UP the strength
    lattice (demand MORE evidence), never pick a single weaker class. An
    assertion matching nothing classifies to the ⊤ element (``{_TOP_CLASS}``),
    which is maximally strong (manual) — never a weak class.
    """
    text = (assertion or "").lower()
    matched = {
        cls for cls, patterns in _CLASS_PATTERNS.items()
        if any(re.search(p, text) for p in patterns)
    }
    return frozenset(matched) if matched else frozenset({_TOP_CLASS})


def _confirmable_under_doctrine(classes: "frozenset[str]", passing_anchors: List["Anchor"]) -> bool:
    """Would the mandatory (non-adjacent) anchor for EVERY plausible class be
    satisfied by the passing anchors? (join = AND across classes.)

    Returns True only if, for each class, at least one passing critical anchor
    is that class's mandatory (kind, op). Any class with no deterministic
    mandatory anchor (or the ⊤ element) makes this False — such a claim can
    never be CONFIRMED on deterministic anchors alone. This is the mechanical
    form of the Adjacent-Fact Test: adjacent anchors never yield CONFIRMED.
    """
    present = {(a.kind, (a.spec or {}).get("op")) for a in passing_anchors}
    for cls in classes:
        required = _CLASS_MANDATORY.get(cls)
        if not required:
            return False  # manual-only / ⊤ class: not deterministically confirmable
        if present.isdisjoint(required):
            return False  # only adjacent anchors present for this class
    return True


def _is_deployment_claim(text: str) -> bool:
    """Does this assertion claim something is shipped / live / deployed? Used
    by decompose() to decide whether a git SHA needs the ancestry anchor and a
    bare URL needs a build-identity anchor rather than the adjacent ones."""
    lowered = (text or "").lower()
    return any(
        re.search(p, lowered)
        for p in (r"\bshipped\b", r"\blive\b", r"\bdeployed\b", r"\bin production\b", r"\bproduction\b", r"\bprod\b")
    )


# ============================================================
# DATA CLASSES
# ============================================================

class Claim:
    """Something an agent asserted, waiting to be checked against reality.

    ``source`` is typically one of 'relay' | 'ledger' | 'pipeline' but is
    not runtime-enforced — a curated/hand-authored claim set may use any
    label that means something to its own tooling.
    """

    def __init__(
        self,
        claim_id: str,
        source: str,
        claimant: str,
        assertion: str,
        evidence_refs: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.claim_id = claim_id
        self.source = source
        self.claimant = claimant
        self.assertion = assertion
        self.evidence_refs = evidence_refs if evidence_refs is not None else []
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.raw = raw if raw is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "source": self.source,
            "claimant": self.claimant,
            "assertion": self.assertion,
            "evidence_refs": self.evidence_refs,
            "timestamp": self.timestamp,
            "raw": self.raw,
        }


class Anchor:
    """A deterministic, machine-checkable proposition derived from a claim.

    ``spec`` is a small dict whose shape depends on ``kind``:
      git:   {"op": "commit_exists"|"file_exists_at_head"|"log_grep"|
                    "branch_contains", "repo": <path, optional — falls
                    back to ProbeEngine.default_repo>, ...op-specific keys}
      http:  {"op": "get_status"|"get_contains"|"json_get", "url": ...,
                    ...op-specific keys}
      fs:    {"op": "file_exists"|"file_contains", "path": ..., ...}
      shell: {"cmd": [...], "cwd": <optional>}
      manual: {} — no deterministic check exists; always UNVERIFIABLE.
    """

    def __init__(
        self,
        anchor_id: str,
        kind: str,
        spec: Dict[str, Any],
        description: str,
        critical: bool = True,
    ):
        self.anchor_id = anchor_id
        self.kind = kind
        self.spec = spec if spec is not None else {}
        self.description = description
        self.critical = critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "kind": self.kind,
            "spec": self.spec,
            "description": self.description,
            "critical": self.critical,
        }


class Evidence:
    """The result of probing a single Anchor.

    ``ok`` is a tri-state:
      True  — anchor confirmed
      False — anchor refuted (deterministic, real negative)
      None  — UNVERIFIABLE (network error, anchor malformed, no anchor
              could be derived, etc.) — this is NOT the same as False.
    """

    def __init__(self, anchor_id: str, ok: Optional[bool], detail: str, raw: Any = None):
        self.anchor_id = anchor_id
        self.ok = ok
        self.detail = detail
        self.raw = raw

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "ok": self.ok,
            "detail": self.detail,
            "raw": self.raw,
        }


class Verdict:
    """The final adjudication for a Claim.

    status is one of CONFIRMED | REFUTED | UNVERIFIABLE | PARTIAL.
    """

    def __init__(
        self,
        claim_id: str,
        status: str,
        confidence: float,
        rationale: str,
        anchors: Optional[List[Dict[str, Any]]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        remediation: str = "",
        verified_at: Optional[str] = None,
    ):
        self.claim_id = claim_id
        self.status = status
        self.confidence = confidence
        self.rationale = rationale
        self.anchors = anchors if anchors is not None else []
        self.evidence = evidence if evidence is not None else []
        self.remediation = remediation
        self.verified_at = verified_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "status": self.status,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "anchors": self.anchors,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "verified_at": self.verified_at,
        }


def anchor_from_dict(d: Dict[str, Any], idx: int = 0, prefix: str = "anchor") -> Anchor:
    """Build an Anchor from a plain dict (as loaded from a JSON anchor
    file). Shared by the CLI's --anchors and --claims (inline anchors)
    loaders."""
    return Anchor(
        anchor_id=d.get("anchor_id") or f"{prefix}-{idx}",
        kind=d.get("kind", "manual"),
        spec=d.get("spec", {}) or {},
        description=d.get("description", ""),
        critical=bool(d.get("critical", True)),
    )


# ============================================================
# PROBE ENGINE — deterministic, read-only executors
# ============================================================

# Shell anchors may only invoke these binaries. This is the entire safety
# boundary for kind="shell" — callers are expected to pass read-only
# invocations (git log, curl -s GET, ls, cat, grep, wc, head, find). The
# allowlist blocks anything else outright (ok=None, "not allowlisted").
_SHELL_ALLOWLIST = {"git", "curl", "ls", "cat", "grep", "wc", "head", "find"}

_HTTP_MAX_BYTES = 200_000  # ~200KB cap per fetch, per task brief
_UNSET = object()  # sentinel: "this kwarg was not supplied" (distinct from None)


def _extract_json_path(data: Any, path: str) -> Any:
    """Dot-path extraction supporting numeric list indices.

    "total" -> data["total"]
    "items.0.gender" -> data["items"][0]["gender"]

    Returns None if any segment is missing / out of range / the wrong
    container type — never raises.
    """
    if not path:
        return data
    current = data
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        elif isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        else:
            return None
    return current


class ProbeEngine:
    """Executes deterministic, read-only checks against reality.

    Every probe method returns an ``Evidence`` and NEVER raises — any
    failure (missing binary, network error, timeout, bad path) is turned
    into ``Evidence(ok=None, detail=...)`` (UNVERIFIABLE), which is exactly
    what an honest auditor should report when it can't determine truth.
    """

    def __init__(
        self,
        default_repo: Optional[str] = None,
        http_timeout: float = 10.0,
        shell_timeout: float = 10.0,
        git_timeout: float = 8.0,
    ):
        self.default_repo = default_repo
        self.http_timeout = http_timeout
        self.shell_timeout = shell_timeout
        self.git_timeout = git_timeout

    # ------------------------------------------------------------------
    # git anchors
    # ------------------------------------------------------------------

    def _git_unavailable(self, repo: Optional[str], anchor_id: str) -> Optional[Evidence]:
        """Pre-flight check: is `repo` a usable git work tree? Returns an
        UNVERIFIABLE Evidence if not, else None (safe to proceed)."""
        if not repo:
            return Evidence(anchor_id, None, "no git repo path provided", None)
        if not Path(repo).exists():
            return Evidence(anchor_id, None, f"repo path does not exist: {repo}", None)
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=repo, capture_output=True, text=True, timeout=min(self.git_timeout, 5),
            )
        except FileNotFoundError:
            return Evidence(anchor_id, None, "git executable not found", None)
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "git rev-parse timed out", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error checking repo: {exc}", None)
        if r.returncode != 0 or r.stdout.strip() != "true":
            return Evidence(anchor_id, None, f"{repo} is not inside a git work tree", None)
        return None

    def commit_exists(self, repo: str, sha: str) -> Evidence:
        """Does commit `sha` exist in `repo`? (git cat-file -e)"""
        anchor_id = f"git:commit_exists:{sha}"
        pre = self._git_unavailable(repo, anchor_id)
        if pre is not None:
            return pre
        try:
            r = subprocess.run(
                ["git", "cat-file", "-e", sha],
                cwd=repo, capture_output=True, text=True, timeout=self.git_timeout,
            )
            ok = r.returncode == 0
            detail = (
                f"commit {sha} exists in {repo}" if ok
                else f"commit {sha} not found in {repo}: {(r.stderr or '').strip()[:200]}"
            )
            return Evidence(anchor_id, ok, detail, {"returncode": r.returncode})
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "git cat-file timed out", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def file_exists_at_head(self, repo: str, path: str) -> Evidence:
        """Does `path` (relative to `repo`) exist as a tracked blob at HEAD?

        `<rev>:<path>` git object syntax resolves `path` relative to the
        repository's TOP-LEVEL, not relative to `repo` — which matters
        whenever `repo` is itself a subdirectory of a larger git repo (as
        it is for this very package: mcp-server-nucleus/ lives inside a
        parent ai-mvp-backend/ repo). `git rev-parse --show-prefix` gives
        the offset from top-level to `repo`, which we prepend so `path`
        behaves the way a caller who passed `repo` actually expects.
        """
        anchor_id = f"git:file_exists_at_head:{path}"
        pre = self._git_unavailable(repo, anchor_id)
        if pre is not None:
            return pre
        prefix = ""
        try:
            pr = subprocess.run(
                ["git", "rev-parse", "--show-prefix"],
                cwd=repo, capture_output=True, text=True, timeout=self.git_timeout,
            )
            if pr.returncode == 0:
                prefix = pr.stdout.strip()
        except Exception:  # pragma: no cover - defensive; falls back to no prefix
            prefix = ""
        full_path = f"{prefix}{path}" if prefix else path
        ref = f"HEAD:{full_path}"
        try:
            r = subprocess.run(
                ["git", "cat-file", "-e", ref],
                cwd=repo, capture_output=True, text=True, timeout=self.git_timeout,
            )
            ok = r.returncode == 0
            detail = f"{path} {'exists' if ok else 'does not exist'} at HEAD in {repo}"
            return Evidence(anchor_id, ok, detail, {"returncode": r.returncode})
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "git cat-file timed out", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def log_grep(self, repo: str, pattern: str) -> Evidence:
        """Does any commit (any branch) have a subject/body matching `pattern`?"""
        anchor_id = f"git:log_grep:{pattern[:40]}"
        pre = self._git_unavailable(repo, anchor_id)
        if pre is not None:
            return pre
        try:
            r = subprocess.run(
                ["git", "log", "--all", "-i", f"--grep={pattern}", "--format=%H", "-n", "1"],
                cwd=repo, capture_output=True, text=True, timeout=self.git_timeout,
            )
            if r.returncode != 0:
                return Evidence(anchor_id, None, f"git log failed: {(r.stderr or '').strip()[:200]}", None)
            sha = r.stdout.strip()
            ok = bool(sha)
            detail = f"found matching commit {sha}" if ok else f"no commit subject/body matches {pattern!r}"
            return Evidence(anchor_id, ok, detail, {"sha": sha})
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "git log timed out", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def branch_contains(self, repo: str, sha: str, branch: str) -> Evidence:
        """Is `branch` one of the branches containing commit `sha`?"""
        anchor_id = f"git:branch_contains:{sha}:{branch}"
        pre = self._git_unavailable(repo, anchor_id)
        if pre is not None:
            return pre
        try:
            r = subprocess.run(
                ["git", "branch", "--contains", sha],
                cwd=repo, capture_output=True, text=True, timeout=self.git_timeout,
            )
            if r.returncode != 0:
                detail = f"git branch --contains failed: {(r.stderr or '').strip()[:200]}"
                return Evidence(anchor_id, None, detail, None)
            branches = [line.strip().lstrip("*").strip() for line in r.stdout.splitlines()]
            branches = [b for b in branches if b]
            ok = branch in branches
            detail = (
                f"{sha} is in branch {branch}" if ok
                else f"{sha} is NOT in branch {branch} (found in: {', '.join(branches) or 'none'})"
            )
            return Evidence(anchor_id, ok, detail, {"branches": branches})
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "git branch --contains timed out", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def is_ancestor(self, repo: str, sha: str, ref: str = "origin/main") -> Evidence:
        """Is `sha` an ancestor of `ref` (default origin/main)? — i.e. is the
        commit actually in the *authoritative* history, not merely present on
        some abandoned branch?

        This is the ANCHOR_DOCTRINE §3 MANDATORY anchor for CODE-EXISTS /
        DEPLOYED-LIVE, closing the `commit_exists` adjacency gap (a commit can
        exist unmerged). Read-only: `git merge-base --is-ancestor`.

        Tri-state maps to git's exit codes: 0 -> ancestor (ok=True), 1 -> not
        an ancestor (ok=False), anything else (e.g. `ref` not fetched locally,
        bad sha) -> UNVERIFIABLE (ok=None) — an honest "cannot determine".
        """
        anchor_id = f"git:is_ancestor:{sha}:{ref}"
        pre = self._git_unavailable(repo, anchor_id)
        if pre is not None:
            return pre
        try:
            r = subprocess.run(
                ["git", "merge-base", "--is-ancestor", sha, ref],
                cwd=repo, capture_output=True, text=True, timeout=self.git_timeout,
            )
            if r.returncode == 0:
                return Evidence(anchor_id, True, f"{sha} is an ancestor of {ref} in {repo}", {"returncode": 0})
            if r.returncode == 1:
                return Evidence(anchor_id, False, f"{sha} is NOT an ancestor of {ref} in {repo}", {"returncode": 1})
            detail = f"cannot determine ancestry of {sha} vs {ref}: {(r.stderr or '').strip()[:200]}"
            return Evidence(anchor_id, None, detail, {"returncode": r.returncode})
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "git merge-base --is-ancestor timed out", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    # ------------------------------------------------------------------
    # http anchors
    # ------------------------------------------------------------------

    def get_status(self, url: str, expect_status: int = 200) -> Evidence:
        """GET `url`, compare the response status code to `expect_status`."""
        anchor_id = f"http:get_status:{url}"
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "dsor-verifier/1.0"})
            with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
                status = resp.status
            ok = status == expect_status
            return Evidence(anchor_id, ok, f"GET {url} -> {status} (expected {expect_status})", {"status": status})
        except urllib.error.HTTPError as exc:
            ok = exc.code == expect_status
            return Evidence(anchor_id, ok, f"GET {url} -> {exc.code} (expected {expect_status})", {"status": exc.code})
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Evidence(anchor_id, None, f"network error fetching {url}: {exc}", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def get_contains(self, url: str, substring: str) -> Evidence:
        """GET `url`, check whether `substring` appears in the body (first ~200KB)."""
        anchor_id = f"http:get_contains:{url}"
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "dsor-verifier/1.0"})
            with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
                body = resp.read(_HTTP_MAX_BYTES)
            text = body.decode("utf-8", errors="replace")
            ok = substring in text
            detail = f"GET {url}: substring {'found' if ok else 'NOT found'} (read {len(body)} bytes)"
            return Evidence(anchor_id, ok, detail, {"bytes_read": len(body)})
        except urllib.error.HTTPError as exc:
            return Evidence(anchor_id, None, f"HTTP {exc.code} fetching {url}", None)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Evidence(anchor_id, None, f"network error fetching {url}: {exc}", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def json_get(
        self,
        url: str,
        path: str,
        *,
        equals: Any = _UNSET,
        max_val: Any = _UNSET,
        min_val: Any = _UNSET,
        contains: Any = _UNSET,
        in_list: Any = _UNSET,
    ) -> Evidence:
        """GET `url`, parse JSON, extract `path` (dot-path, supports
        numeric list indices), then compare using whichever comparator was
        supplied. Exactly one of equals/max_val/min_val/contains/in_list is
        expected; if none are given the extracted value is reported for
        manual adjudication (ok=None)."""
        anchor_id = f"http:json_get:{url}:{path}"
        try:
            req = urllib.request.Request(
                url, method="GET",
                headers={"User-Agent": "dsor-verifier/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
                body = resp.read(_HTTP_MAX_BYTES)
        except urllib.error.HTTPError as exc:
            return Evidence(anchor_id, None, f"HTTP {exc.code} fetching {url}", None)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Evidence(anchor_id, None, f"network error fetching {url}: {exc}", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

        try:
            data = json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            return Evidence(anchor_id, None, f"response from {url} was not valid JSON: {exc}", None)

        value = _extract_json_path(data, path)
        try:
            value_repr = json.dumps(value)
        except (TypeError, ValueError):
            value_repr = repr(value)

        if equals is not _UNSET:
            ok = value == equals
            detail = f"{path} = {value_repr}; expected == {equals!r} -> {'OK' if ok else 'MISMATCH'}"
        elif max_val is not _UNSET:
            if value is None:
                ok, detail = None, f"{path} = {value_repr}; expected <= {max_val} -> value missing (UNKNOWN)"
            else:
                try:
                    ok = float(value) <= float(max_val)
                    detail = f"{path} = {value_repr}; expected <= {max_val} -> {'OK' if ok else 'EXCEEDS'}"
                except (TypeError, ValueError):
                    ok, detail = None, f"{path} = {value_repr}; not numeric, cannot compare to max {max_val} (UNKNOWN)"
        elif min_val is not _UNSET:
            if value is None:
                ok, detail = None, f"{path} = {value_repr}; expected >= {min_val} -> value missing (UNKNOWN)"
            else:
                try:
                    ok = float(value) >= float(min_val)
                    detail = f"{path} = {value_repr}; expected >= {min_val} -> {'OK' if ok else 'BELOW'}"
                except (TypeError, ValueError):
                    ok, detail = None, f"{path} = {value_repr}; not numeric, cannot compare to min {min_val} (UNKNOWN)"
        elif contains is not _UNSET:
            ok = contains in str(value)
            detail = f"{path} = {value_repr}; expected to contain {contains!r} -> {'OK' if ok else 'MISMATCH'}"
        elif in_list is not _UNSET:
            try:
                ok = value in in_list
            except TypeError:
                ok = False
            detail = f"{path} = {value_repr}; expected in {in_list!r} -> {'OK' if ok else 'MISMATCH'}"
        else:
            ok = None
            detail = f"{path} = {value_repr} (no comparator given; extracted for manual adjudication)"

        return Evidence(anchor_id, ok, detail, {"value": value})

    # ------------------------------------------------------------------
    # fs anchors
    # ------------------------------------------------------------------

    def file_exists(self, path: str) -> Evidence:
        anchor_id = f"fs:file_exists:{path}"
        try:
            ok = Path(path).exists()
            return Evidence(anchor_id, ok, f"{path} {'exists' if ok else 'does not exist'}", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    def file_contains(self, path: str, substring: str) -> Evidence:
        anchor_id = f"fs:file_contains:{path}"
        try:
            p = Path(path)
            if not p.exists():
                return Evidence(anchor_id, False, f"{path} does not exist", None)
            text = p.read_text(encoding="utf-8", errors="replace")
            ok = substring in text
            detail = f"substring {'found' if ok else 'NOT found'} in {path}"
            return Evidence(anchor_id, ok, detail, None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    # ------------------------------------------------------------------
    # shell anchors
    # ------------------------------------------------------------------

    def run_shell(self, cmd: List[str], cwd: Optional[str] = None) -> Evidence:
        """Run an allowlisted read-only shell command."""
        anchor_id = f"shell:run:{' '.join(str(c) for c in cmd)[:60]}"
        if not cmd or not isinstance(cmd, (list, tuple)) or cmd[0] not in _SHELL_ALLOWLIST:
            return Evidence(anchor_id, None, "command not allowlisted", None)
        try:
            r = subprocess.run(
                list(cmd), cwd=cwd, capture_output=True, text=True, timeout=self.shell_timeout,
            )
            ok = r.returncode == 0
            out = (r.stdout or "").strip()
            detail = f"exit={r.returncode}: {out[:300]}" if out else f"exit={r.returncode}"
            return Evidence(anchor_id, ok, detail, {"stdout": out[:2000], "returncode": r.returncode})
        except subprocess.TimeoutExpired:
            return Evidence(anchor_id, None, "command timed out", None)
        except FileNotFoundError:
            return Evidence(anchor_id, None, f"{cmd[0]} not installed", None)
        except Exception as exc:  # pragma: no cover - defensive
            return Evidence(anchor_id, None, f"error: {exc}", None)

    # ------------------------------------------------------------------
    # dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def _retag(anchor: Anchor, evidence: Evidence) -> Evidence:
        """Probe methods derive their own anchor_id from their args; retag
        the Evidence with the caller's actual Anchor.anchor_id so callers
        can correlate Evidence back to the Anchor that produced it."""
        evidence.anchor_id = anchor.anchor_id
        return evidence

    def run_anchor(self, anchor: Anchor) -> Evidence:
        """Single dispatch point: run whichever probe `anchor.kind` +
        `anchor.spec['op']` selects. Never raises."""
        try:
            kind = anchor.kind
            spec = anchor.spec or {}
            op = spec.get("op")

            if kind == "git":
                repo = spec.get("repo") or self.default_repo
                if not repo:
                    return Evidence(anchor.anchor_id, None, "no repo specified for git anchor", None)
                if op == "commit_exists":
                    return self._retag(anchor, self.commit_exists(repo, spec.get("sha", "")))
                if op == "is_ancestor":
                    return self._retag(
                        anchor, self.is_ancestor(repo, spec.get("sha", ""), spec.get("ref", "origin/main"))
                    )
                if op == "file_exists_at_head":
                    return self._retag(anchor, self.file_exists_at_head(repo, spec.get("path", "")))
                if op == "log_grep":
                    return self._retag(anchor, self.log_grep(repo, spec.get("pattern", "")))
                if op == "branch_contains":
                    return self._retag(
                        anchor, self.branch_contains(repo, spec.get("sha", ""), spec.get("branch", ""))
                    )
                return Evidence(anchor.anchor_id, None, f"unknown git op: {op!r}", None)

            if kind == "http":
                # "status"/"contains" are accepted aliases for
                # "get_status"/"get_contains" — curated anchor files
                # (hand-authored, e.g. by a frontier model) tend to reach
                # for the shorter name; both spellings are unambiguous.
                if op in ("get_status", "status"):
                    return self._retag(
                        anchor, self.get_status(spec.get("url", ""), spec.get("expect_status", 200))
                    )
                if op in ("get_contains", "contains"):
                    return self._retag(
                        anchor, self.get_contains(spec.get("url", ""), spec.get("substring", ""))
                    )
                if op == "json_get":
                    kwargs: Dict[str, Any] = {}
                    if "equals" in spec:
                        kwargs["equals"] = spec["equals"]
                    if "max" in spec:
                        kwargs["max_val"] = spec["max"]
                    if "min" in spec:
                        kwargs["min_val"] = spec["min"]
                    if "contains" in spec:
                        kwargs["contains"] = spec["contains"]
                    if "in" in spec:
                        kwargs["in_list"] = spec["in"]
                    return self._retag(
                        anchor, self.json_get(spec.get("url", ""), spec.get("path", ""), **kwargs)
                    )
                return Evidence(anchor.anchor_id, None, f"unknown http op: {op!r}", None)

            if kind == "fs":
                # Relative fs paths resolve against default_repo when set, so
                # curated anchor files stay machine-agnostic (no absolute,
                # user-specific paths baked into committed demo data).
                raw_path = spec.get("path", "")
                path = raw_path
                if raw_path and not Path(raw_path).is_absolute() and self.default_repo:
                    path = str(Path(self.default_repo) / raw_path)
                if op == "file_exists":
                    return self._retag(anchor, self.file_exists(path))
                if op == "file_contains":
                    return self._retag(
                        anchor, self.file_contains(path, spec.get("substring", ""))
                    )
                return Evidence(anchor.anchor_id, None, f"unknown fs op: {op!r}", None)

            if kind == "shell":
                cmd = spec.get("cmd", [])
                cwd = spec.get("cwd") or spec.get("repo") or self.default_repo
                return self._retag(anchor, self.run_shell(cmd, cwd=cwd))

            if kind == "manual":
                return Evidence(anchor.anchor_id, None, anchor.description or "no deterministic anchor; manual review required", None)

            return Evidence(anchor.anchor_id, None, f"unknown anchor kind: {kind!r}", None)
        except Exception as exc:  # pragma: no cover - top-level safety net
            return Evidence(anchor.anchor_id, None, f"probe dispatch error: {exc}", None)


# ============================================================
# REASONERS
# ============================================================

class Reasoner(ABC):
    """decompose() breaks a claim into checkable Anchors; adjudicate()
    turns the resulting Evidence back into a Verdict."""

    @abstractmethod
    def decompose(self, claim: Claim) -> List[Anchor]:
        ...

    @abstractmethod
    def adjudicate(self, claim: Claim, evidence: List[Evidence]) -> Verdict:
        ...


_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_URL_RE = re.compile(r"https?://[^\s'\"<>()\[\]]+")


class RuleReasoner(Reasoner):
    """Deterministic fallback reasoner — no LLM involved. Mirrors
    LLMIntentAnalyzer.analyze_without_llm(): regex-based, always available,
    never fails. Also serves as the scoring engine for every other
    Reasoner in this module (InjectedReasoner and LLMReasoner both
    delegate adjudicate() here)."""

    def __init__(self):
        # anchor_id -> Anchor for the most recently decomposed claim.
        # adjudicate() consults this (when the caller doesn't pass anchors
        # explicitly) to know which Evidence came from a `critical` anchor.
        self._anchor_index: Dict[str, Anchor] = {}

    def decompose(self, claim: Claim) -> List[Anchor]:
        anchors = self._decompose_anchors(claim)
        self._anchor_index = {a.anchor_id: a for a in anchors}
        return anchors

    @staticmethod
    def _decompose_anchors(claim: Claim) -> List[Anchor]:
        """Pure function (no side effects) so InjectedReasoner can reuse it
        as a fallback without touching RuleReasoner's own index."""
        text = claim.assertion or ""
        anchors: List[Anchor] = []

        # Flag-gated (default OFF). When ON, a git SHA in a shipped/live/deployed
        # claim gets the MANDATORY ancestry anchor (`--is-ancestor origin/main`)
        # instead of the adjacent `commit_exists`, and a bare URL in a live claim
        # gets a build-identity requirement instead of a bare 200 — per
        # ANCHOR_DOCTRINE §3. With the flag OFF this block is skipped and the
        # decomposition below is byte-identical to the pre-doctrine behavior.
        mandatory = _mandatory_anchors_enabled()
        deployment_claim = mandatory and _is_deployment_claim(text)

        urls = _URL_RE.findall(text)
        text_without_urls = _URL_RE.sub(" ", text)

        seen_shas = set()
        for match in _SHA_RE.finditer(text_without_urls):
            sha = match.group(0)
            if sha in seen_shas:
                continue
            seen_shas.add(sha)
            if deployment_claim:
                anchors.append(Anchor(
                    anchor_id=f"git-anc-{sha[:12]}",
                    kind="git",
                    spec={"op": "is_ancestor", "sha": sha, "ref": "origin/main"},
                    description=f"commit {sha} is an ancestor of origin/main (in authoritative history, not just an abandoned branch)",
                    critical=True,
                ))
            else:
                anchors.append(Anchor(
                    anchor_id=f"git-sha-{sha[:12]}",
                    kind="git",
                    spec={"op": "commit_exists", "sha": sha},
                    description=f"commit {sha} exists in the repo",
                    critical=True,
                ))

        seen_urls = set()
        for url in urls:
            url = url.rstrip(").,;:!?\"'")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            if deployment_claim:
                # A bare 200 proves the route serves *some* build, not *this*
                # code (DEPLOYED-LIVE adjacency gap). The mandatory anchor is a
                # build-identity token (deployed-SHA header / /version) == the
                # claimed SHA. We cannot synthesize the expected token here, so
                # we emit a critical `manual` anchor naming the residual — which
                # keeps the claim below CONFIRMED rather than certifying a bare
                # 200 as "deployed".
                anchors.append(Anchor(
                    anchor_id=f"http-build-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]}",
                    kind="manual",
                    spec={"op": "manual", "url": url},
                    description=(
                        f"{url} must return a build-identity token (deployed-SHA header / "
                        f"/version) equal to the claimed commit — a bare 200 only proves the "
                        f"route serves some build (ANCHOR_DOCTRINE §3 DEPLOYED-LIVE)"
                    ),
                    critical=True,
                ))
            else:
                anchors.append(Anchor(
                    anchor_id=f"http-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]}",
                    kind="http",
                    spec={"op": "get_status", "url": url, "expect_status": 200},
                    description=f"{url} responds 200",
                    critical=True,
                ))

        if not anchors:
            anchors.append(Anchor(
                anchor_id="manual-review",
                kind="manual",
                spec={},
                description="No deterministic anchor (git sha / URL) found in the claim text",
                critical=False,
            ))

        return anchors

    def adjudicate(
        self,
        claim: Claim,
        evidence: List[Evidence],
        anchors: Optional[List[Anchor]] = None,
    ) -> Verdict:
        """`anchors` is an internal extension point (not part of the
        Reasoner ABC contract) used by InjectedReasoner / LLMReasoner to
        tell RuleReasoner exactly which anchors backed this evidence, so
        criticality is scored correctly even when RuleReasoner itself
        didn't run decompose() for this claim."""
        anchor_lookup = {a.anchor_id: a for a in (anchors if anchors is not None else self._anchor_index.values())}

        def is_critical(e: Evidence) -> bool:
            a = anchor_lookup.get(e.anchor_id)
            return a.critical if a is not None else True

        critical_evidence = [e for e in evidence if is_critical(e)]
        if not critical_evidence:
            # No anchor metadata available (or everything was non-critical)
            # — fall back to treating all evidence as critical rather than
            # silently declaring victory on nothing.
            critical_evidence = list(evidence)

        failed = [e for e in critical_evidence if e.ok is False]
        passed = [e for e in critical_evidence if e.ok is True]
        unverifiable = [e for e in critical_evidence if e.ok is None]

        rationale_parts = []
        for e in evidence:
            mark = "PASS" if e.ok is True else ("FAIL" if e.ok is False else "UNKNOWN")
            rationale_parts.append(f"[{mark}] {e.anchor_id}: {e.detail}")
        rationale = " | ".join(rationale_parts) if rationale_parts else "no anchors were probed"

        if failed:
            status, confidence = "REFUTED", 0.9
            remediation = "Re-check: " + ", ".join(e.anchor_id for e in failed)
        elif passed and not unverifiable:
            status, confidence = "CONFIRMED", 0.85
            remediation = ""
            # Confinement cap (flag-gated, default OFF): a CONFIRMED verdict may
            # not rest on ADJACENT anchors alone. Classify the claim and require
            # the mandatory (non-adjacent) anchor of every plausible class to be
            # among the passing anchors (join = AND, fail-safe UP). If not, drop
            # to PARTIAL and name the residual — never silently CONFIRMED on a
            # known-adjacent anchor (ANCHOR_DOCTRINE §2 / REFEREE_CONFINEMENT §3).
            if _mandatory_anchors_enabled() and anchor_lookup:
                classes = classify_claim(claim.assertion or "")
                passing_anchors = [
                    anchor_lookup[e.anchor_id] for e in passed if e.anchor_id in anchor_lookup
                ]
                if not _confirmable_under_doctrine(classes, passing_anchors):
                    status, confidence = "PARTIAL", 0.5
                    remediation = (
                        "Adjacent anchors only — class(es) "
                        + ", ".join(sorted(classes))
                        + " require a mandatory non-adjacent anchor "
                        + "(ANCHOR_DOCTRINE §3: --is-ancestor / build-identity json_get / "
                        "first-party read) before CONFIRMED is legal."
                    )
        elif passed and unverifiable:
            status, confidence = "PARTIAL", 0.5
            remediation = "Manually confirm: " + ", ".join(e.anchor_id for e in unverifiable)
        elif unverifiable:
            status, confidence = "UNVERIFIABLE", 0.2
            remediation = "Manually confirm: " + ", ".join(e.anchor_id for e in unverifiable)
        else:
            status, confidence = "UNVERIFIABLE", 0.0
            remediation = "No anchors could be derived or probed for this claim; needs human review."

        return Verdict(
            claim_id=claim.claim_id,
            status=status,
            confidence=confidence,
            rationale=rationale,
            anchors=[a.to_dict() for a in anchor_lookup.values()],
            evidence=[e.to_dict() for e in evidence],
            remediation=remediation,
            verified_at=datetime.now(timezone.utc).isoformat(),
        )


class InjectedReasoner(Reasoner):
    """Uses a pre-computed anchor map (claim_id -> [Anchor, ...]),
    typically hand-authored/verified by a frontier model reviewing the
    claim text. Falls back to RuleReasoner.decompose() for any claim not
    present in the map. Adjudication is always delegated to
    RuleReasoner.adjudicate() — this class never scores anything itself,
    it only supplies better anchors."""

    def __init__(self, anchor_map: Optional[Dict[str, List[Anchor]]] = None):
        self.anchor_map = anchor_map or {}
        self._rule = RuleReasoner()
        self._last_anchors: Dict[str, List[Anchor]] = {}

    def decompose(self, claim: Claim) -> List[Anchor]:
        anchors = self.anchor_map.get(claim.claim_id)
        if anchors is None:
            anchors = self._rule._decompose_anchors(claim)
        self._last_anchors[claim.claim_id] = anchors
        return anchors

    def adjudicate(self, claim: Claim, evidence: List[Evidence]) -> Verdict:
        anchors = self._last_anchors.get(claim.claim_id)
        return self._rule.adjudicate(claim, evidence, anchors=anchors)


class LLMReasoner(Reasoner):
    """Frontier-model-backed decomposition, mirroring the LLM-with-fallback
    pattern in llm_intent_analyzer.py (LLMIntentAnalyzer.analyze /
    analyze_without_llm): ask the model to propose deterministic anchors
    for a claim, parse its JSON reply into Anchor objects, and fall back to
    RuleReasoner on ANY failure — no client configured, network error,
    malformed JSON, whatever. Adjudication is always delegated to
    RuleReasoner; the LLM only ever helps decompose, it never scores.

    Import-safety: this class must import (and instantiate) cleanly with
    zero environment configuration (no API keys). All LLM client access
    happens lazily inside decompose(), never at import or __init__ time,
    and is wrapped in a broad try/except — exactly like
    LLMIntentAnalyzer._get_client().
    """

    DECOMPOSITION_PROMPT = (
        "You are a ground-truth auditor for an AI agent operating system.\n"
        "Given a CLAIM the agent made about its own work, propose a small "
        "list of DETERMINISTIC, machine-checkable anchors that would "
        "confirm or refute it. Only propose anchors that can be checked "
        "without a human in the loop: a git commit existing, an HTTP "
        "endpoint returning a specific status/JSON value, a file "
        "existing/containing text. If nothing deterministic can be "
        "checked, return an empty anchors list.\n\n"
        "Respond with ONLY valid JSON (no markdown, no explanation):\n"
        '{"anchors": [{"kind": "git"|"http"|"fs"|"shell", '
        '"spec": {"op": "...", ...}, "description": "...", "critical": true}]}\n\n'
        "CLAIM:\n{assertion}\n"
    )

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("NUCLEUS_VERIFIER_MODEL", "gemini-2.0-flash-exp")
        self._rule = RuleReasoner()

    def decompose(self, claim: Claim) -> List[Anchor]:
        if self._llm_capable():
            try:
                anchors = self._decompose_via_llm(claim)
                if anchors:
                    return anchors
            except Exception as exc:  # pragma: no cover - defensive fail-open
                logger.debug("LLMReasoner: decompose fell back to RuleReasoner: %s", exc)
        return self._rule._decompose_anchors(claim)

    @staticmethod
    def _llm_capable() -> bool:
        """Fast precondition check mirroring LLMIntentAnalyzer._get_client()
        — avoids paying the resilient client's retry/backoff cost in the
        (common, in this repo's test/demo environment) case where no
        credentials are configured at all."""
        return bool(os.environ.get("GEMINI_API_KEY")) or bool(
            os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )

    def _decompose_via_llm(self, claim: Claim) -> List[Anchor]:
        # Lazy import — this is what keeps the module import-safe with zero
        # API keys configured. If llm_resilience (or its own transitive
        # deps) is missing/broken, this simply degrades to no LLM anchors.
        try:
            from .llm_resilience import get_resilient_llm_client
        except Exception:
            return []

        resilient = get_resilient_llm_client()
        prompt = self.DECOMPOSITION_PROMPT.format(assertion=claim.assertion or "")
        result = resilient.generate_json(
            prompt,
            model_override=self.model_name,
            fallback_fn=lambda _p: None,  # let decompose() do the RuleReasoner fallback
        )
        if not result:
            return []

        anchors: List[Anchor] = []
        for i, raw in enumerate(result.get("anchors", []) or []):
            if not isinstance(raw, dict):
                continue
            anchors.append(anchor_from_dict(raw, idx=i, prefix=f"llm-{claim.claim_id}"))
        return anchors

    def adjudicate(self, claim: Claim, evidence: List[Evidence]) -> Verdict:
        return self._rule.adjudicate(claim, evidence)


# ============================================================
# VERIFIER
# ============================================================

class Verifier:
    """Ties a Reasoner + ProbeEngine together into the full
    decompose -> probe -> adjudicate pipeline, with an optional (opt-in)
    write-back to a caller-supplied DecisionLedger.

    `record=True` NEVER writes anywhere by default — the caller must pass
    an explicit `ledger` (a DecisionLedger constructed against whatever
    brain_path the caller controls, e.g. a scratch directory for a demo,
    or the real ledger in a production audit job). Even then, only claims
    with source == 'ledger' (i.e. they came FROM that ledger via
    ingest_pending_ledger) are written back — a Verifier never invents new
    ledger entries.
    """

    def __init__(
        self,
        reasoner: Reasoner,
        probe_engine: ProbeEngine,
        ledger: Optional[DecisionLedger] = None,
        record: bool = False,
    ):
        self.reasoner = reasoner
        self.probe_engine = probe_engine
        self.ledger = ledger
        self.record = record

    def verify(self, claim: Claim) -> Verdict:
        anchors = self.reasoner.decompose(claim)
        evidence = [self.probe_engine.run_anchor(a) for a in anchors]
        verdict = self.reasoner.adjudicate(claim, evidence)

        if self.record and self.ledger is not None and claim.source == "ledger":
            try:
                self.ledger.update_audit_status(claim.claim_id, verdict.status, verdict.rationale)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Verifier: failed to record audit status for %s: %s", claim.claim_id, exc)

        return verdict

    def verify_all(self, claims: List[Claim]) -> List[Verdict]:
        return [self.verify(c) for c in claims]


# ============================================================
# INGEST HELPERS
# ============================================================

def ingest_relay(relay_dir: Union[str, Path]) -> List[Claim]:
    """Walk a relay directory for *.json message files and turn them into
    Claims. Recurses into peer subdirectories (e.g. .brain/relay/cowork/,
    .brain/relay/claude_code_main/) — the standard Nucleus relay layout is
    one subdirectory per peer, not flat files at the top level.

    One Claim per string entry in body.results (capped at 10 per file),
    PLUS one more Claim for body.conclusion (or, if absent, the top-level
    subject line) — the relay's headline claim.
    """
    relay_path = Path(relay_dir)
    claims: List[Claim] = []
    if not relay_path.exists():
        return claims

    for file_path in sorted(relay_path.rglob("*.json")):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("ingest_relay: skipping unparseable %s: %s", file_path, exc)
            continue
        if not isinstance(data, dict):
            continue

        claimant = data.get("from", "unknown")
        timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        body = data.get("body", {})
        if not isinstance(body, dict):
            body = {}
        stem = file_path.stem

        results = body.get("results")
        if isinstance(results, list):
            idx = 0
            for r in results[:10]:
                if not isinstance(r, str) or not r.strip():
                    continue
                claims.append(Claim(
                    claim_id=f"{stem}-result-{idx}",
                    source="relay",
                    claimant=claimant,
                    assertion=r,
                    evidence_refs=[],
                    timestamp=timestamp,
                    raw=data,
                ))
                idx += 1

        conclusion = body.get("conclusion")
        if isinstance(conclusion, str) and conclusion.strip():
            claims.append(Claim(
                claim_id=f"{stem}-conclusion",
                source="relay",
                claimant=claimant,
                assertion=conclusion,
                evidence_refs=[],
                timestamp=timestamp,
                raw=data,
            ))
        else:
            subject = data.get("subject")
            if isinstance(subject, str) and subject.strip():
                claims.append(Claim(
                    claim_id=f"{stem}-subject",
                    source="relay",
                    claimant=claimant,
                    assertion=subject,
                    evidence_refs=[],
                    timestamp=timestamp,
                    raw=data,
                ))

    return claims


def ingest_pending_ledger(ledger: DecisionLedger) -> List[Claim]:
    """Pull every PENDING DecisionEntry out of a DecisionLedger and turn it
    into a Claim (assertion = "<intent> :: <reasoning>"), ready to be
    verified and (optionally) written back via Verifier(record=True)."""
    claims: List[Claim] = []
    for entry in ledger.list_all():
        if entry.get("audit_status") != "PENDING":
            continue
        intent = entry.get("intent", "")
        reasoning = entry.get("reasoning", "")
        metadata = entry.get("metadata")
        claimant = "ledger"
        if isinstance(metadata, dict) and metadata.get("agent"):
            claimant = str(metadata["agent"])
        claims.append(Claim(
            claim_id=entry.get("decision_id", ""),
            source="ledger",
            claimant=claimant,
            assertion=f"{intent} :: {reasoning}",
            evidence_refs=[],
            timestamp=entry.get("timestamp", ""),
            raw=entry,
        ))
    return claims


def ingest_claims_file(path: Union[str, Path]) -> "tuple[List[Claim], Dict[str, List[Anchor]]]":
    """Load a curated claims file: a JSON array of claim dicts (or
    {"claims": [...]}). Each entry may embed an "anchors" list — a
    hand-authored (e.g. frontier-model-produced) set of Anchor specs for
    that exact claim, which the caller typically feeds straight into
    InjectedReasoner instead of relying on RuleReasoner's regex
    decomposition.

    Returns (claims, anchor_map) where anchor_map only contains entries
    for claims that embedded an "anchors" list.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("claims", [])
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array of claims (or {{'claims': [...]}})")

    claims: List[Claim] = []
    anchor_map: Dict[str, List[Anchor]] = {}

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id") or f"{p.stem}-{i}"
        claim = Claim(
            claim_id=claim_id,
            source=item.get("source", "pipeline"),
            claimant=item.get("claimant", "unknown"),
            assertion=item.get("assertion", ""),
            evidence_refs=item.get("evidence_refs", []) or [],
            timestamp=item.get("timestamp"),
            raw=item,
        )
        claims.append(claim)

        raw_anchors = item.get("anchors")
        if isinstance(raw_anchors, list) and raw_anchors:
            anchor_map[claim_id] = [
                anchor_from_dict(a, idx=j, prefix=f"{claim_id}-anchor")
                for j, a in enumerate(raw_anchors) if isinstance(a, dict)
            ]

    return claims, anchor_map


# ============================================================
# REPORTING
# ============================================================

def render_report(verdicts: List[Verdict]) -> str:
    """Fixed-width table: CLAIM | STATUS | CONF | RATIONALE (truncated),
    plus a summary line with counts per status."""
    col_claim, col_status, col_conf = 24, 12, 6
    header = f"{'CLAIM':<{col_claim}} {'STATUS':<{col_status}} {'CONF':<{col_conf}} RATIONALE"
    rule = "-" * len(header)

    lines = [header, rule]
    counts: Dict[str, int] = {}

    for v in verdicts:
        counts[v.status] = counts.get(v.status, 0) + 1
        claim_id = v.claim_id or ""
        short_id = claim_id if len(claim_id) <= col_claim else claim_id[: col_claim - 1] + "…"
        rationale = (v.rationale or "").replace("\n", " ")
        if len(rationale) > 90:
            rationale = rationale[:87] + "..."
        lines.append(f"{short_id:<{col_claim}} {v.status:<{col_status}} {v.confidence:<{col_conf}.2f} {rationale}")

    lines.append(rule)
    if counts:
        summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    else:
        summary = "(no claims)"
    lines.append(f"TOTAL={len(verdicts)}  {summary}")

    return "\n".join(lines)
