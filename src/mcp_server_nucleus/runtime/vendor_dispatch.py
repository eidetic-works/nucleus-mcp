"""Cross-vendor CLI dispatch + capture (flag-gated, default OFF).

``runtime.vendor_dispatch`` is the ONE executor type that turns a cross-vendor
CLI call (Antigravity/Gemini ``agy``, Devin/GLM ``devin``) into a CAPTURED
byproduct of normal fleet operation:

  * invoke the vendor CLI **non-interactively** under a HARD Python subprocess
    timeout — a hung ``agy`` becomes a recorded ``timed_out`` envelope, never a
    silent stall;
  * pass the prompt **identity-safe** — inline in argv (``agy`` ≥1.1.1, where
    ``-p`` takes the prompt as its value and stdin is no longer read), via a
    private ``0600`` temp file whose *path* (never the raw text) is templated
    into ``argv`` (``devin``), or over stdin (legacy/future stdin-only vendors);
    dispatch prompts are constructed identity-safe (no absolute home paths, no
    personal names) and the fleet runs same-uid, so argv visibility to local
    processes is not a new threat surface;
  * on return, write a relay capture envelope whose ``body.artifact_refs`` is
    bound to a real commit SHA / PR# / file path (so co-occurrence cannot
    masquerade as causation — no valid artifact_ref, no capture), plus a
    vendor-tagged engram so the memory store finally shows the
    Antigravity/GLM surfaces.

Everything here is gated behind ``NUCLEUS_CROSS_VENDOR`` (default OFF). With the
flag OFF nothing in this module runs from any call site — ``nucleus dispatch``
errors with an actionable message, the swarm ignores vendor personas, and
routing never selects a vendor tier — so behavior is byte-identical to before
this module existed.

Boundary note (ADR-0043 W1): this is a **periphery** module. The heavy imports
(``relay_ops``, ``nucleus_wedge.store``) are function-local so the module's own
import stays stdlib-only and can never fail to load; and no *core* module gains
an eager edge into it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("nucleus.vendor_dispatch")

# ── Flag ──────────────────────────────────────────────────────────────────────
FLAG = "NUCLEUS_CROSS_VENDOR"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Prepended to every dispatch prompt. MUST stay under 900 chars: devin dies
# with rc=-13 (SIGPIPE) above ~64 KB of prompt, and the preamble competes with
# the task body for that budget — every byte here is a byte the task cannot
# spend. Trim ruthlessly; if a non-negotiable needs prose, it belongs in the
# docstring above, not here.
# Addressed to the VENDOR, about how the vendor must behave. The generated
# first draft described this module's own design invariants instead
# (flag-gated, artifact_ref, identity-safe delivery) -- structurally perfect,
# semantically useless: "FLAG-GATED, DEFAULT OFF" tells a coding agent nothing
# about what it may edit. Every byte here competes with the real task inside
# devin's ~64KB SIGPIPE ceiling, so this stays terse and behavioral only.
_VENDOR_PREAMBLE = (
    "Four non-negotiables for this task:\n"
    "1. FILE SCOPE IS ABSOLUTE. Edit ONLY the files this task names. If it "
    "says 'X ONLY', touching any other file is a failure, not a judgement "
    "call -- even to add a helper, a test, or an import.\n"
    "2. NO GIT STATE CHANGES. Never run git commit, reset, stash, checkout, "
    "or any branch switch. This working tree is shared with other agents "
    "running concurrently; their uncommitted work is in it right now.\n"
    "3. REFUSE RATHER THAN WIDEN. If the task cannot be done within the "
    "stated file scope, say so explicitly in your output and stop. A clear "
    "refusal is more useful than a change nobody asked for.\n"
    "4. REPORT HONESTLY. State plainly what you did and did NOT do, and "
    "anything you could not verify. Do not describe intended work as done."
)


def _resolve_preamble() -> str:
    """Resolve the dispatch preamble at call time.

    Precedence (first match wins):

    1. ``NUCLEUS_VENDOR_PREAMBLE_DISABLED`` truthy -> ``""`` (preamble off).
       Lets a caller suppress the preamble without editing code — useful for
       prompt-budget-tight dispatches where every byte is borrowed from the
       task body.
    2. ``NUCLEUS_VENDOR_PREAMBLE`` non-empty -> that value verbatim. A caller
       who needs a different non-negotiables set (or none of the four) can
       override without forking the module.
    3. Otherwise -> :data:`_VENDOR_PREAMBLE` (the compiled-in default).

    Read at call time, not import time, so a caller can flip the env between
    dispatches in the same process.
    """
    if os.environ.get("NUCLEUS_VENDOR_PREAMBLE_DISABLED", "").strip().lower() in _TRUTHY:
        return ""
    override = os.environ.get("NUCLEUS_VENDOR_PREAMBLE", "")
    if override.strip():
        return override
    return _VENDOR_PREAMBLE


# v3 anchor precondition, UNCONDITIONAL as of 2026-07-31. PRINCIPAL v3 line 77:
#   "the artifact-ref must be VENDOR-DERIVED, checkable in CODE-SHAPE: on the
#    anchored path the dispatch/relay tool schema MUST NOT accept artifact-ref
#    as caller input; the capture instrument stamps it from the vendor
#    worktree's git-reported SHA."
#
# This was previously gated on an env var (NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED).
# A guarantee that depends on a setting being ON is not a code-shape property:
# it holds only where someone remembered to export it, and silently does not
# hold in CI, on a fresh clone, or for any caller who never heard of the flag.
# With the flag off, caller-supplied artifact_ref flowed straight into the
# envelope that G1 crit-4 treats as PROOF an increment was cross-vendor
# coordinated — i.e. the causal edge was forgeable by whoever was being
# measured. The flag has therefore been REMOVED rather than defaulted to on;
# a default is still configuration, and the rule says code-shape.
#
# Do not reintroduce a flag here. If stamping must be bypassed for a test,
# monkeypatch _read_worktree_head_sha, which fails closed by design.


def _read_worktree_head_sha(cwd: Optional[str] = None) -> Optional[str]:
    """Read the HEAD commit SHA of the worktree the vendor runs in.

    Returns the 40-char SHA, or None if git is unavailable or not a git repo.

    IMPORTANT — this alone is NOT a vendor-derived ref. It reports whatever
    HEAD is in *cwd*, and the vendor subprocess inherits this same cwd, so the
    dispatching caller controls the value by choosing a directory. The earlier
    docstring claimed the base commit "correctly yields no qualifying increment
    per crit-4 (d)" and deferred the whole safety argument to a predicate that
    is not enforced here. It isn't, and wasn't.

    What makes a ref vendor-derived is the BEFORE/AFTER comparison in
    :func:`dispatch_and_capture`: the SHA qualifies only if HEAD *moved* while
    the vendor ran. See the rationale block there.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if len(sha) == 40:
                return sha
    except Exception:
        logger.debug("Swallowed exception in _read_worktree_head_sha", exc_info=True)
        pass
    return None


def _git_porcelain_snapshot(cwd: Optional[str] = None) -> Optional[str]:
    """Snapshot ``git status --porcelain`` in *cwd*, or ``None`` if it could
    not be read (git unavailable, not a repo, timeout).

    Used by :meth:`VendorCLIExecutor.run` to detect a mode='read' dispatch
    that actually wrote to the working tree — devin's read-mode permission
    flag is ``dangerous`` (2026-08-18: 'auto' still blocks some tool calls
    entirely, confirmed by devin_readmode_nowop_rca.md and
    nucleus_delegate_read_mode_rca.md), which grants real write access with
    no CLI-level guarantee of read-only behavior. ``None`` is a distinct
    "could not verify" sentinel, never coerced to "" (which would read as
    "confirmed clean" for a repo we simply failed to check).
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        logger.debug("Swallowed exception in _git_porcelain_snapshot", exc_info=True)
        pass
    return None


def _count_behind_upstream(cwd: Optional[str] = None) -> Optional[int]:
    """Count commits the worktree HEAD is behind its configured upstream.

    Returns the integer commit count (0 == up to date), or ``None`` when it
    could not be determined: no upstream tracking branch configured, not a git
    repo, git unavailable, or any subprocess error. Mirrors the
    fault-isolation contract of :func:`_read_worktree_head_sha` — this is a
    best-effort diagnostic signal and must NEVER raise into the caller.

    Background (2026-08-04 incident): a scout dispatch and a build dispatch
    both operated on a local worktree 22 commits behind ``origin/main``. The
    scout "found" a bug already fixed upstream; the build "fixed" it again
    against the stale copy — a diff that, applied to real ``origin/main``,
    would have SILENTLY REVERTED merged fixes. This function is the signal that
    was missing: how far behind is the checkout the vendor is about to read or
    mutate. The caller logs a warning when the count is > 0.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..@{u}"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode == 0:
            count = result.stdout.strip()
            if count.isdigit():
                return int(count)
        # Non-zero return code covers the "no upstream configured" case
        # (`fatal: no upstream configured for branch '...'`) and any other
        # git refusal — both map to "unknown", not a crash.
    except Exception:
        logger.debug("Swallowed exception in _count_behind_upstream", exc_info=True)
        pass
    return None


def _commits_changed_paths(
    pre_sha: str, post_sha: str, cwd: Optional[str] = None
) -> Optional[Set[str]]:
    """Return the set of relative paths touched by the commits in
    ``pre_sha..post_sha``.

    Runs ``git rev-list pre_sha..post_sha`` then, for each commit,
    ``git diff-tree --no-commit-id --name-only -r <sha>`` and unions the
    reported paths. Returns ``None`` on any git failure (bad rev range, not a
    git repo, git unavailable, subprocess error, timeout) so the caller can
    fail closed; returns ``set()`` when the range is valid but touched nothing
    (e.g. an empty merge). Mirrors the fault-isolation contract of
    :func:`_read_worktree_head_sha` / :func:`_count_behind_upstream` — this is
    a best-effort diagnostic signal and must NEVER raise into
    :func:`dispatch_and_capture`.
    """
    try:
        revs = subprocess.run(
            ["git", "rev-list", f"{pre_sha}..{post_sha}"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if revs.returncode != 0:
            return None
        changed: Set[str] = set()
        for sha in revs.stdout.splitlines():
            sha = sha.strip()
            if not sha:
                continue
            diff = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
                capture_output=True, text=True, timeout=5, cwd=cwd,
            )
            if diff.returncode != 0:
                return None
            for line in diff.stdout.splitlines():
                path = line.strip()
                if path:
                    changed.add(path)
        return changed
    except Exception:
        logger.debug("Swallowed exception in _commits_changed_paths", exc_info=True)
        return None


def _repo_relative_posix(path: str, cwd: Optional[str] = None) -> Optional[str]:
    """Resolve ``path`` against ``cwd``, strip the repo toplevel prefix, and
    return a POSIX-style repo-relative path. Returns ``None`` on any failure
    (git unavailable, not a repo, subprocess error, path outside the repo
    root) — never raises. The toplevel lookup is cached for the duration of
    this call only (per the call-site contract); callers re-invoking across
    sessions get a fresh lookup. Mirrors the fault-isolation contract of
    :func:`_commits_changed_paths` / :func:`_read_worktree_head_sha`.
    """
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if toplevel.returncode != 0:
            return None
        root = Path(toplevel.stdout.strip()).resolve()
        if not root.is_dir():
            return None
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = Path(cwd or ".") / resolved
        resolved = resolved.resolve()
        rel = resolved.relative_to(root)
        return rel.as_posix()
    except (ValueError, OSError):
        # ValueError: path outside repo root (relative_to mismatch).
        # OSError: filesystem/subprocess I/O failure.
        return None
    except Exception:
        logger.debug("Swallowed exception in _repo_relative_posix", exc_info=True)
        return None


def _rebase_or_merge_in_progress(cwd: Optional[str] = None) -> Optional[str]:
    """Detect an unrelated, already-in-progress rebase/merge/cherry-pick in
    the worktree the dispatch is about to run in. Returns a short label
    (``"rebase"``, ``"merge"``, ``"cherry-pick"``) or None. Best-effort,
    never raises — mirrors the fault-isolation contract of
    :func:`_count_behind_upstream`.

    Background (2026-08-04 incident, fw-1785838722): a vendor dispatch
    subprocess sharing the MCP server process's cwd walked into a stale,
    abandoned interactive rebase left in ``.git/rebase-merge/`` since a prior,
    unrelated session and staged a pile of unrelated files trying to resolve
    a conflict that was not its business to touch. Nothing previously warned
    the caller their shared working tree was mid-rebase before dispatching.
    """
    import subprocess

    def _git_path_exists(name: str, is_dir: bool) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", name],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode != 0:
            return False
        # `--git-path` prints a path relative to the cwd it ran in when that
        # cwd is inside a repo — resolve it against `cwd`, not this process's
        # own cwd, or every check silently misses (fixed absolute-path repos
        # aside).
        p = Path(result.stdout.strip())
        if not p.is_absolute():
            p = Path(cwd or ".") / p
        return p.is_dir() if is_dir else p.is_file()

    try:
        if _git_path_exists("rebase-merge", is_dir=True):
            return "rebase"
        if _git_path_exists("rebase-apply", is_dir=True):
            return "rebase"
        if _git_path_exists("MERGE_HEAD", is_dir=False):
            return "merge"
        if _git_path_exists("CHERRY_PICK_HEAD", is_dir=False):
            return "cherry-pick"
    except Exception:
        logger.debug("Swallowed exception in _rebase_or_merge_in_progress", exc_info=True)
        pass
    return None


CROSS_VENDOR_DISABLED_MSG = (
    "cross-vendor dispatch is disabled. Set NUCLEUS_CROSS_VENDOR=1 to enable, "
    "e.g.  NUCLEUS_CROSS_VENDOR=1 nucleus dispatch agy --prompt-file prompt.txt "
    "--artifact-ref <commit-sha|PR#|path> --to peer"
)

# ── Onboard persistent enablement (zero-config after `nucleus onboard`) ────────
# After `nucleus onboard` writes this config, cross_vendor_enabled() returns True
# with NO env set — the env path is preserved (back-compat) but no longer required.
ONBOARD_CONFIG_NAME = "onboard.json"
ONBOARD_HOST_CLI = "claude"  # host CLI — detected for visibility, not a dispatch target


def _onboard_config_path() -> Optional[Path]:
    """Resolve the persistent onboard config path (never raises).

    Preference: ``<brain>/onboard.json`` (via ``common.get_brain_path``), falling
    back to ``~/.nucleus/onboard.json``. Returns ``None`` only if neither can be
    resolved — this is read on every :func:`cross_vendor_enabled` call, so it must
    be fault-isolated.
    """
    try:
        from .common import get_brain_path  # periphery→core, lazy (import-safety)

        brain = get_brain_path()
        if brain is not None:
            return Path(brain) / ONBOARD_CONFIG_NAME
    except Exception as exc:  # noqa: BLE001 — never break the gate on a resolve hiccup
        logger.debug("onboard config: brain path resolve failed: %s", exc)
    try:
        return Path.home() / ".nucleus" / ONBOARD_CONFIG_NAME
    except Exception:  # noqa: BLE001
        logger.debug("Swallowed exception in _onboard_config_path", exc_info=True)
        return None


def _onboard_config_enabled() -> bool:
    """True iff the onboard config file marks ``cross_vendor`` enabled."""
    cfg_path = _onboard_config_path()
    if cfg_path is None or not cfg_path.exists():
        return False
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return bool(data.get("cross_vendor", False))
    except Exception as exc:  # noqa: BLE001 — corrupt/missing config ⇒ not enabled
        logger.debug("onboard config read failed: %s", exc)
        return False


def write_onboard_config(
    enabled: bool, *, detected: Optional[Dict[str, Any]] = None
) -> Path:
    """Persist the onboard enablement config; returns the path written.

    Called by ``nucleus onboard``. After this, :func:`cross_vendor_enabled`
    returns True with no ``NUCLEUS_CROSS_VENDOR`` env set (zero-config).
    """
    cfg_path = _onboard_config_path()
    if cfg_path is None:
        cfg_path = Path.home() / ".nucleus" / ONBOARD_CONFIG_NAME
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cross_vendor": bool(enabled),
        "detected": detected or {},
        "updated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    cfg_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return cfg_path


def cross_vendor_enabled() -> bool:
    """True iff cross-vendor dispatch is enabled.

    Enabled if EITHER (zero-config after onboarding):
      * the persistent onboard config marks ``cross_vendor`` enabled, OR
      * ``NUCLEUS_CROSS_VENDOR`` env var is set truthy (back-compat — preserved so
        existing ``NUCLEUS_CROSS_VENDOR=1`` workflows keep working unchanged).
    """
    if os.environ.get(FLAG, "").strip().lower() in _TRUTHY:
        return True
    return _onboard_config_enabled()


def is_multi_vendor_available() -> bool:
    """True iff the dual-vendor adversarial path can actually run.

    Requires :func:`cross_vendor_enabled` AND BOTH the ``devin`` and ``agy``
    binaries resolvable on PATH via the same ``shutil.which`` lookup that
    :func:`dispatch_and_capture` uses to detect the ``not_found`` status. When
    False, ``nucleus build`` falls back to single-vendor ``claude``-only mode
    (one real plan dispatch to the ``claude`` vendor, no adversarial review
    round, status ``SINGLE_VENDOR_PLAN`` — never the dual-vendor ``APPROVED``).

    This is the gate the build pipeline branches on; it is additive — when
    True, behavior is byte-identical to today.
    """
    if not cross_vendor_enabled():
        return False
    return bool(shutil.which("devin")) and bool(shutil.which("agy"))


# Per-dispatch subprocess timeout. Overridable because vendor throughput varies
# by orders of magnitude: agy answered a trivial prompt in 21s one hour and 176s
# the next, and a real plan draft then exceeded the 300s hard kill repeatedly
# (partial=0 bytes). Env-tunable so a slow-vendor window does not require a code
# change. Default is unchanged at 300s. Read at import time.
# 1 hour. Was 300s, which HARD-KILLED completed vendor work at the finish line:
# agy reviews measured 260.5s (87% of the old ceiling) and two consecutive runs
# died at exactly 300.0s with "partial=0 bytes" — every token paid for, nothing
# kept. A ceiling that discards finished output is worse than a slow lane.
_DEFAULT_VENDOR_TIMEOUT_S = int(os.environ.get("NUCLEUS_VENDOR_TIMEOUT_S", "3600"))

# One session (2026-08-16/17) fanned out 9 concurrent dispatches through this
# module -- each call reaches the same running mcp-server-nucleus process, so
# concurrent VendorCLIExecutor.run() calls pile their blocking subprocess.run()
# onto that one process with no cap, exactly like the Workflow tool's own
# agent() calls would without its min(16, CPUs-2) limiter. Result, same
# session: one SIGBUS crash, one 8-minute hang requiring a manual kill, four
# hard 2700s timeouts with zero output, and one dispatch killed externally
# mid-run -- seven real incidents, none caused by the task content, all by
# unbounded concurrent load on this one choke point. The cap below is scoped
# to the actual subprocess.run() in VendorCLIExecutor.run(), not the whole
# call (argv/prompt-file setup is cheap and doesn't need to queue).
_DISPATCH_MAX_CONCURRENT = max(1, int(os.environ.get("NUCLEUS_VENDOR_MAX_CONCURRENT", "3")))
_DISPATCH_SEMAPHORE = threading.Semaphore(_DISPATCH_MAX_CONCURRENT)

# Host-load gate: the semaphore caps lane COUNT but nothing stops a fleet of
# dispatches piling onto an already-saturated host (observed 2026-09-14: cap-2
# fleet + parallel sessions pushed loadavg past cpu_count and every new
# subprocess spawn worsened the pileup). Before spawning a vendor subprocess,
# wait while the 1-min load average is >= _LOAD_FACTOR * cpu_count. Bounded at
# _LOAD_MAX_WAIT seconds so a permanently-loaded host can't deadlock the
# queue — the dispatch proceeds after the ceiling regardless.
_LOAD_FACTOR = float(os.environ.get("NUCLEUS_VENDOR_LOAD_FACTOR", "0.8"))
_LOAD_MAX_WAIT = float(os.environ.get("NUCLEUS_VENDOR_LOAD_MAX_WAIT", "30"))
_LOAD_POLL = 2.0


def _wait_for_load(timeout_s: float = 0.0) -> None:
    """Block while 1-min loadavg >= _LOAD_FACTOR * cpu_count, up to the
    wait budget. The budget is ``_LOAD_MAX_WAIT`` further capped by
    ``timeout_s`` when >0 — it is nonsensical to wait 30s for load on a
    dispatch whose own subprocess ceiling is 1s. No-op on platforms
    without getloadavg."""
    try:
        cpus = os.cpu_count() or 1
        threshold = _LOAD_FACTOR * cpus
        budget = _LOAD_MAX_WAIT
        if timeout_s and timeout_s > 0:
            budget = min(budget, timeout_s)
        deadline = time.monotonic() + budget
        while True:
            load = os.getloadavg()[0]
            if load < threshold or time.monotonic() >= deadline:
                if load >= threshold:
                    logger.warning(
                        "vendor dispatch proceeding at load %.1f (>= %.1f*%.0f cpus) after %.0fs ceiling",
                        load, _LOAD_FACTOR, cpus, _LOAD_MAX_WAIT,
                    )
                return
            time.sleep(_LOAD_POLL)
    except (AttributeError, OSError):  # no getloadavg (Windows)
        return

# ── Vendor registry ───────────────────────────────────────────────────────────
VENDOR_MODES = ("read", "write")
DEFAULT_MODE = "write"
_MODE_ALIASES = {
    "read": "read", "review": "read", "readonly": "read",
    "analyze": "read", "analysis": "read",
    "write": "write", "build": "write", "edit": "write",
    "implement": "write", "fix": "write",
}


def normalize_mode(mode: Optional[str]) -> str:
    """Canonicalize a permission mode string to ``'read'`` or ``'write'``.

    Accepts common aliases (``review``/``readonly``/``analyze`` → read;
    ``build``/``edit``/``implement``/``fix`` → write). Raises ``ValueError``
    on an unknown mode — the message explicitly names the model/mode confusion
    so a caller who passes a model id where a mode belongs gets a clear signal.
    """
    key = (mode or DEFAULT_MODE).strip().lower()
    canon = _MODE_ALIASES.get(key)
    if canon is None:
        raise ValueError(
            f"unknown mode {mode!r}; expected one of {list(VENDOR_MODES)} "
            f"(read = analyze/review, no file changes; write = build/edit). "
            f"NOTE: this is a permission mode, NOT a model — set params['model'] "
            f"for a model id."
        )
    return canon


@dataclass(frozen=True)
class VendorSpec:
    """Static description of one cross-vendor CLI surface.

    ``argv_template`` holds *flags* plus, at most, a ``{prompt_file}`` slot, a
    ``{prompt}`` slot, or neither — never any other raw text. Three
    identity-safe delivery modes are supported, selected by the template:

      * **inline-argv mode** (``{prompt}`` present — ``agy`` ≥1.1.1): the prompt
        is substituted directly into argv as the value of ``-p``. agy 1.1.1
        changed ``-p``/``--print`` to take its prompt as an inline argv value
        and stopped reading stdin, so stdin delivery is dead in agy ≥1.1.1.
        Acceptable argv visibility: dispatch prompts are identity-safe (no
        absolute home paths, no personal names) and the fleet runs same-uid.
      * **prompt-file mode** (``{prompt_file}`` present — ``devin``): the prompt
        is written to a private ``0600`` temp file and only its *path* is
        substituted into argv (``devin -p --`` with nothing after ``--`` drops
        into REPL mode and panics; ``devin --prompt-file <FILE>`` runs the
        prompt). The path — not the text — is what appears in ``ps``.
      * **stdin mode** (neither slot — legacy/future): the prompt is streamed
        over stdin by :class:`VendorCLIExecutor`, so it never touches argv.
    """

    vendor: str            # dispatch name: "agy" | "devin"
    model: str             # default model family for this vendor surface
    binary: str            # CLI executable resolved on PATH
    sender: str            # relay sender identity (canonicalized downstream)
    to_default: str        # default capture recipient role
    engram_tags: tuple     # (vendor:<x>, surface:<y>) — queryable vendor surface
    argv_template: tuple   # flag argv with a {timeout} slot + optional {prompt_file}
    read_flags: tuple = ()      # permission tokens injected in read/review mode
    write_flags: tuple = ()     # permission tokens injected in write/build mode
    default_model: str = ""     # selectable model id used when caller omits model
    models: tuple = ()          # allowlist of accepted+advertised selectable ids
    model_flag: str = ""        # CLI flag carrying the model (e.g. "--model"); "" ⇒ none
    # Hard prompt ceiling in characters, 0 ⇒ unmeasured/unbounded. MEASURED, not
    # guessed: devin returns rc=-13 (SIGPIPE) at ~4.5s for prompts above ~64KB —
    # 60,033 chars succeeded, 70,009 died, repeatably. That is a pipe-buffer
    # limit, and without this guard it surfaces as an opaque "vendor produced no
    # output" several layers up. agy handled 120,018 chars fine, so the ceiling
    # is per-vendor rather than universal. Re-measure before raising either.
    max_prompt_chars: int = 0

    @property
    def uses_prompt_file(self) -> bool:
        """True iff the prompt is delivered via a temp file (a ``{prompt_file}``
        slot in argv) rather than inline in argv or streamed over stdin."""
        return any("{prompt_file}" in tok for tok in self.argv_template)

    @property
    def uses_inline_prompt(self) -> bool:
        """True iff the prompt is delivered inline in argv (a ``{prompt}`` slot)
        rather than via a temp file or stdin."""
        return any("{prompt}" in tok for tok in self.argv_template)

    def flags_for_mode(self, mode: str) -> tuple:
        """Permission flags for the canonical mode (``read`` or ``write``)."""
        return self.read_flags if normalize_mode(mode) == "read" else self.write_flags

    def build_argv(
        self,
        timeout_s: int,
        prompt_file: Optional[str] = None,
        prompt: Optional[str] = None,
        mode: str = DEFAULT_MODE,
        model: Optional[str] = None,
    ) -> List[str]:
        """Flag argv for the subprocess.

        Substitutes ``{timeout}``, and for prompt-file-mode specs the
        ``{prompt_file}`` temp-file path, and for inline-argv-mode specs the
        ``{prompt}`` text. stdin-mode specs get the prompt over stdin instead
        (``prompt_file``/``prompt`` are unused and may be ``None``).

        Argv order is PINNED: template → mode/permission flags → model flag.
        The model flag + id are appended as separate list tokens (never
        templated) and are always the LAST two tokens when present.
        """
        # For CLI-internal --print-timeout, 0 means "no limit" → use 86400s (24h)
        # since agy's --print-timeout requires a value. The Python subprocess
        # timeout (None when timeout_s==0) is the real guard.
        cli_timeout = 86400 if timeout_s == 0 else timeout_s
        base = [
            tok.format(timeout=cli_timeout, prompt_file=prompt_file or "", prompt=prompt or "")
            for tok in self.argv_template
        ]
        base += list(self.flags_for_mode(mode))            # permission flags
        if self.model_flag and model:                       # model flag (append)
            base += [self.model_flag, model]
        return base


def resolve_model(vendor: str, model: Optional[str]) -> str:
    """Resolve a selectable model id for *vendor*.

    ``None``/``""`` ⇒ the vendor's ``default_model``. A non-empty *model* must
    appear in the vendor's ``models`` allowlist (argv-injection guard) or a
    ``ValueError`` is raised naming the valid ids.
    """
    spec = VENDOR_SPECS.get(vendor)
    if spec is None:
        raise ValueError(
            f"unknown vendor {vendor!r}; expected one of {sorted(VENDOR_SPECS)}"
        )
    if not model:                                   # None / "" ⇒ use default
        return spec.default_model
    if not spec.models:
        raise ValueError(f"vendor {vendor!r} does not support model selection")
    if model not in spec.models:
        raise ValueError(
            f"unsupported model {model!r} for vendor {vendor!r}; choose one of "
            f"{list(spec.models)} or omit to use the default {spec.default_model!r}"
        )
    return model


def resolve_model_family(model_id: str, fallback: str = "") -> str:
    normalized = (model_id or "").strip().lower()
    prefixes = (
        ("swe-", "swe"),
        ("glm-", "glm"),
        ("gemini-", "gemini"),
        ("gpt-", "gpt"),
        ("claude-", "claude"),
    )
    for prefix, family in prefixes:
        if normalized.startswith(prefix):
            return family
    return fallback


VENDOR_SPECS: Dict[str, VendorSpec] = {
    # agy → Gemini (Antigravity CLI). Prompt delivered INLINE in argv as the
    # value of `-p` (agy ≥1.1.1 changed `-p`/`--print` to take the prompt as an
    # inline argv value and stopped reading stdin — stdin delivery is dead).
    # `--print-timeout` is a Go time.Duration and REQUIRES a unit, hence the
    # `s` appended to `{timeout}`. REAL-CLI VERIFIED (2026-07-11):
    # `agy -p "<PROMPT>" --print-timeout 300s --dangerously-skip-permissions`
    # returns rc=0 and the model's answer. Identity-safety: the prompt is now
    # visible in `ps` (argv), which is ACCEPTABLE because dispatch prompts are
    # constructed identity-safe (no absolute home paths, no personal names) AND
    # the fleet runs same-uid, so argv visibility to local processes is not a
    # new threat surface.
    "agy": VendorSpec(
        vendor="agy",
        model="gemini",
        binary="agy",
        sender="agy",
        to_default="cross_vendor",
        engram_tags=("vendor:gemini", "surface:antigravity"),
        argv_template=("agy", "-p", "{prompt}", "--print-timeout", "{timeout}s"),
        read_flags=("--dangerously-skip-permissions",),
        write_flags=("--dangerously-skip-permissions",),
        default_model="gemini-3.1-pro-high",
        # Mirrors `agy models` (the authoritative subcommand) as of agy 1.1.1,
        # 2026-08-01. The 3.6-flash tier was MISSING here while agy offered it,
        # so callers could not select agy's newest models at all.
        #
        # Refresh this tuple from `agy models` — NOT by grepping the agy binary.
        # Strings are concatenated in the Mach-O ("gemini-3.6-flash-highgemini-"),
        # so exact-substring grep reports 0 hits for ids that are in fact valid
        # and wrongly indicts them as dead. That misread happened here once.
        # NOTE: models[0] MUST stay == default_model — test_vendor_spec_fields_exact
        # pins that coupling. New ids append after it, they do not reorder it.
        models=(
            "gemini-3.1-pro-high",
            "gemini-3.1-pro-low",
            "gemini-3.6-flash-high",
            "gemini-3.6-flash-medium",
            "gemini-3.6-flash-low",
            "gemini-3.5-flash-high",
            "gemini-3.5-flash-medium",
            "gemini-3.5-flash-low",
            "claude-opus-4-6-thinking",
            "claude-sonnet-4-6",
            "gpt-oss-120b-medium",
        ),
        model_flag="--model",
    ),
    # devin → selectable SWE/GLM/Claude/GPT families. Prompt delivery uses a
    # private 0600 temp file whose path is substituted for {prompt_file}.
    # REAL-CLI VERIFIED (2026-07-09): `devin -p --` (stdin, the old template)
    # drops into REPL mode and PANICS (rc=101,
    # 'Option::unwrap() on None' in chisel/src/repl_mode.rs) — devin does NOT read
    # the prompt from stdin. `devin -p --prompt-file <FILE>` returns rc=0 and the
    # real answer, identity-safe (prompt in a file, not argv/stdin).
    # codex-cli 0.147.0. `codex exec [PROMPT]` runs non-interactively; passing
    # `-` (or omitting the positional) makes it read instructions from STDIN,
    # which is the identity-safe path -- the prompt never enters argv, so it
    # cannot leak through the process table. That is stdin mode: no {prompt}
    # and no {prompt_file} slot, so VendorCLIExecutor streams it.
    #
    # Smoke-verified before wiring, not assumed:
    #   codex exec --dangerously-bypass-approvals-and-sandbox "Reply with
    #   exactly: CODEX_OK"  -> rc=0, stdout "CODEX_OK"
    #
    # The bypass flag is required for the same reason devin needs
    # --permission-mode dangerous: a non-interactive run cannot answer an
    # approval prompt, and without it codex rejects any tool call needing
    # confirmation and returns having done nothing. Read and write flags match
    # because the sandbox decision is per-invocation, not per-mode; scope is
    # enforced by the lane's commit scope gate, not by the vendor.
    "codex": VendorSpec(
        vendor="codex",
        model="gpt",
        binary="codex",
        sender="codex",
        to_default="cross_vendor",
        engram_tags=("vendor:gpt", "surface:codex"),
        argv_template=("codex", "exec", "-"),
        # Reviews and reads are judgment work: high reasoning effort (operator
        # 2026-09-28: ChatGPT is the primary plan reviewer, at its top tier).
        # Builds keep codex's own configured effort.
        read_flags=("--dangerously-bypass-approvals-and-sandbox",
                    "-c", "model_reasoning_effort=high"),
        write_flags=("--dangerously-bypass-approvals-and-sandbox",),
        # `codex exec -m <MODEL>`. A models tuple is required for the vendor to
        # be addressable THROUGH THE SHIM at all: vendor_shim's model regex is
        # ^nucleus/(vendor)-(model)$ with the model part mandatory, so a
        # selection-less vendor has no valid id and every shim call is rejected
        # with "does not support model selection". models[0] must equal
        # default_model, per the note on the devin spec.
        model_flag="-m",
        # Read from codex's OWN config (~/.codex/config.toml: model =
        # "gpt-5.6-terra"), not guessed. A guessed id fails as
        # status=not_found with rc=None in 0.0s -- it never reaches the binary,
        # so the failure looks like a dead vendor rather than a bad name.
        # 2026-09-28: codex's config moved to gpt-6-luna (smoke: rc=0 "OK").
        default_model="gpt-6-luna",
        models=("gpt-6-luna", "gpt-5.6-terra"),
    ),
    "devin": VendorSpec(
        vendor="devin",
        model="swe",
        binary="devin",
        sender="devin",
        to_default="cross_vendor",
        engram_tags=("vendor:swe", "surface:devin"),
        argv_template=("devin", "-p", "--prompt-file", "{prompt_file}"),
        # 2026-08-18: 'auto' still blocks devin's first real tool call under
        # non-interactive -p for some shell commands (confirmed twice live
        # this session; RCA on disk at
        # .brain/strategy/north_star/agent_integration/devin_readmode_nowop_rca.md
        # and nucleus_delegate_read_mode_rca.md). devin has no permission tier
        # between 'default' (blocks all tool use non-interactively) and
        # 'dangerous' (full autonomous tool use). Matching write_flags is the
        # only way read-mode investigations can actually complete -- the
        # automatic _git_porcelain_snapshot() check in run() is the real
        # safety boundary now, not this flag.
        read_flags=("--permission-mode", "dangerous", "--respect-workspace-trust", "false"),
        write_flags=("--permission-mode", "dangerous", "--respect-workspace-trust", "false"),
        # Confirmed model IDs use family-specific routing: swe-* → swe and
        # glm-* → glm. The dotted glm-5.2 spelling is not a valid model ID.
        # SWE-2 Max is free and outperforms SWE-1.7 / GLM-5.2 on Terminal-Bench
        # 2.1, DeepSWE 1.1 and FrontierCode 1.1 (2026-09-10), so it is the
        # default. SWE-1.7 and GLM-5.2 remain as fallbacks.
        # models[0] stays equal to default_model.
        default_model="swe-2-max",
        models=(
            "swe-2-max",
            "swe-2-high",
            "swe-2-medium",
            "swe-1-7",
            "swe-1-7-medium",
            "glm-5-2",
            "claude-5-fable-low",
            "claude-5-fable-medium",
            "claude-5-fable-high",
            "claude-5-fable-xhigh",
            "claude-5-fable-max",
            "gpt-5-6-sol-medium",
            "gpt-5-6-sol-none",
            "claude-opus-5-low",
            "claude-opus-5-medium",
            "claude-opus-5-high",
            "claude-opus-5-xhigh",
            "claude-opus-5-max",
            "claude-sonnet-5-low",
            "claude-sonnet-5-medium",
            "claude-sonnet-5-high",
            "claude-sonnet-5-xhigh",
            "claude-sonnet-5-max",
        ),
        model_flag="--model",
        max_prompt_chars=60000,   # measured: SIGPIPE above ~64KB
    ),
    # devin-swe → SWE family on devin CLI. Same binary, different model.
    # Free tiers: SWE-2 Max/High/Medium alongside SWE-1.7 and glm-5.2.
    # Used for SWE-bench-style coding tasks.
    "devin-swe": VendorSpec(
        vendor="devin-swe",
        model="swe",
        binary="devin",
        sender="devin-swe",
        to_default="cross_vendor",
        engram_tags=("vendor:swe", "surface:devin"),
        argv_template=("devin", "-p", "--prompt-file", "{prompt_file}"),
        read_flags=("--permission-mode", "auto"),
        write_flags=("--permission-mode", "dangerous"),
        # CONFIRMED via `devin models list` (2026-09-10): real ids are
        # "swe-2-max", "swe-2-high", "swe-2-medium" and "swe-1-7",
        # all free. See the note above VENDOR_SPECS["devin"].
        default_model="swe-2-max",
        models=("swe-2-max", "swe-2-high", "swe-2-medium", "swe-1-7", "swe-1-7-medium"),
        model_flag="--model",
        max_prompt_chars=60000,   # measured: SIGPIPE above ~64KB
    ),
    # claude → Claude Code CLI (host). Single-vendor native-fallback mode for
    # `nucleus build` when the dual-vendor adversarial path (devin+agy) is not
    # available. Prompt delivered INLINE in argv as the value of `-p`/`--print`
    # (mirrors the agy inline-argv delivery shape). REAL-CLI VERIFIED:
    # `claude --help` confirms `-p, --print  Print response and exit`. This
    # spec lets single-vendor mode reuse the EXACT SAME subprocess dispatch,
    # pre_head/post_head git-diff provenance, and verify-stage machinery as
    # devin/agy — no new architecture, no new return contract. It is NOT a
    # peer in the adversarial review loop (single-vendor runs skip the review
    # round and use the honestly distinct status SINGLE_VENDOR_PLAN).
    "claude": VendorSpec(
        vendor="claude",
        model="claude",
        binary="claude",
        sender="claude",
        to_default="cross_vendor",
        engram_tags=("vendor:claude", "surface:claude-code"),
        argv_template=("claude", "-p", "{prompt}"),
        read_flags=("--dangerously-skip-permissions",),
        write_flags=("--dangerously-skip-permissions",),
        default_model="",
        models=(),
        model_flag="",
    ),
}

# Personas the swarm loop diverts to the vendor executor (single source of truth).
VENDOR_PERSONAS = frozenset(VENDOR_SPECS)


# ── Onboard detection ─────────────────────────────────────────────────────────
def _cheap_version(binary: str) -> Optional[str]:
    """Best-effort ``<binary> --version`` probe (short timeout). Never raises."""
    try:
        proc = subprocess.run(
            [binary, "--version"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        return out.splitlines()[0][:120] if out else None
    except Exception:  # noqa: BLE001 — version is best-effort, never fatal
        logger.debug("Swallowed exception in _cheap_version", exc_info=True)
        return None


def detect_vendor_clis() -> Dict[str, Dict[str, Any]]:
    """Detect installed vendor + host CLIs for ``nucleus onboard``.

    Iterates ``VENDOR_SPECS`` (the dispatch registry) so adding a ``VendorSpec``
    later extends detection with no edit here, plus the host ``claude`` CLI
    (detected for visibility — not a dispatch target). Returns a dict keyed by
    name::

        {name: {"found": bool, "binary": str, "version": str|None, "model": str}}

    Missing vendors are reported (``found=False``), never raised — the caller
    (``nucleus onboard``) prints them and continues.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for name, spec in VENDOR_SPECS.items():
        path = shutil.which(spec.binary)
        found = path is not None
        out[name] = {
            "found": found,
            "binary": spec.binary,
            "version": _cheap_version(spec.binary) if found else None,
            "model": spec.model,
        }
    # host claude CLI — visibility only (not a VendorSpec / dispatch target)
    cpath = shutil.which(ONBOARD_HOST_CLI)
    out[ONBOARD_HOST_CLI] = {
        "found": cpath is not None,
        "binary": ONBOARD_HOST_CLI,
        "version": _cheap_version(ONBOARD_HOST_CLI) if cpath else None,
        "model": ONBOARD_HOST_CLI,
    }
    return out


# ── Executor result ───────────────────────────────────────────────────────────
@dataclass
class VendorSubprocessResult:
    """Raw outcome from the vendor subprocess layer."""

    rc: Optional[int]
    output: str
    duration: float
    timed_out: bool = False
    cancelled: bool = False


@dataclass
class VendorResult:
    """Outcome of one non-interactive vendor CLI invocation."""

    vendor: str
    model: str
    rc: Optional[int]
    status: str           # ok | empty_output | intent_only | error | timed_out | not_found | budget_rejected | prompt_too_large | read_mode_wrote_files
    result: str
    duration: float
    model_id: str = ""            # resolved SELECTABLE id (e.g. "glm-5-2")
    redacted: int = 0             # count of secret redactions applied to result

    def __post_init__(self) -> None:
        self.model = resolve_model_family(self.model_id, self.model)

    @property
    def produced_output(self) -> bool:
        """True iff the vendor produced non-blank output."""
        return bool(self.result and self.result.strip())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor": self.vendor,
            "model_family": self.model,      # RENAMED from "model" — kills the decoy
            "model_id": self.model_id,       # the id the agent selected / that ran
            "rc": self.rc,
            "status": self.status,
            "result": self.result,
            "produced_output": self.produced_output,
            "redacted": self.redacted,
            "duration": round(self.duration, 3),
        }


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


# ── Secret hygiene ────────────────────────────────────────────────
# Best-effort redaction of common credential shapes from vendor OUTPUT before it
# is classified, stored, captured, or returned. A BACKSTOP, not a guarantee: the
# real defense is keeping secrets out of prompts, and this CANNOT scrub a file a
# vendor writes itself (see the tool-description caveat).
_SECRET_PATTERNS = (
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"), "Bearer <REDACTED>"),
    (re.compile(r"\beyJ[A-Za-z0-9._-]{20,}"), "<REDACTED-JWT>"),
    (re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9]{16,}"), "<REDACTED-KEY>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<REDACTED-AWS-KEY>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "<REDACTED-GH-TOKEN>"),
    (re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd|access[_-]?key)"
        r"(\s*[=:]\s*)[\"\']?[A-Za-z0-9._~+/=-]{8,}"), r"\1\2<REDACTED>"),
)


def _redact_secrets(text: str) -> "tuple[str, int]":
    """Redact common credential shapes from *text*; return ``(redacted, count)``.

    Defense-in-depth for vendor OUTPUT (Bearer / JWT / ``sk-``/``pk-`` keys / AWS
    ``AKIA`` / GitHub ``gh?_`` / ``token=``-style assignments). Best-effort, NOT a
    guarantee — never rely on it in place of keeping secrets out of prompts, and
    it cannot touch files a vendor writes itself.
    """
    if not text:
        return text, 0
    n = 0
    for pat, repl in _SECRET_PATTERNS:
        text, c = pat.subn(repl, text)
        n += c
    return text, n


def _classify_completed(returncode: int, output: str) -> str:
    """Classify a completed (non-timeout) subprocess: ``ok`` vs ``empty_output``
    vs ``error`` vs ``intent_only``. An rc=0 run with blank output is ``empty_output``
    — the silent no-op signal this module surfaces explicitly instead of mislabeling
    ``ok``.

    Also detects silent refusals-disguised-as-success where a vendor (e.g. devin)
    returns rc=0 but refused to run the command, asking for more permissions.

    Also detects ``intent_only`` output where a vendor describes an intention to act
    ("I will...", "I'll...", "I am going to...") but emits no concrete execution
    evidence such as code fences, diff markers, or explicit file-change confirmations.
    """
    if returncode != 0:
        return "error"
    if not (output and output.strip()):
        return "empty_output"

    out_lower = output.lower()
    # Detect devin read-mode refusal-disguised-as-success where it asks for more permission
    if (
        "--permission-mode dangerous" in out_lower
        or "requires confirmation" in out_lower
        or "cannot execute without" in out_lower
    ):
        return "error"

    # Detect "intent_only" output: vendor states an intention to act but produces
    # no concrete execution evidence (code fences, diff markers, or explicit
    # file-change confirmations). This is a distinct silent no-op shape between
    # ``empty_output`` and ``ok``.
    intent_phrases = (
        "i will ", "i'll ", "i am going to ", "i'm going to ",
        "i intend to ", "i plan to ",
    )
    if any(p in out_lower for p in intent_phrases):
        concrete_markers = (
            "```", "+++ ", "--- ", "@@ -",
            "file:", "edited:", "created:", "updated:", "fixed:", "changed:",
            "done", "completed", "finished",
        )
        if not any(m in out_lower for m in concrete_markers):
            return "intent_only"

    return "ok"


def _snapshot_paths(paths: Optional[List[str]]) -> Dict[str, Any]:
    """Snapshot SHA-256 content hash for each path, or ``None`` if missing.

    Used by :func:`dispatch_and_capture` to detect whether a vendor actually
    touched the files the caller named in ``expect_paths``. Returns ``{}`` when
    *paths* is falsy so the generic dispatch path does ZERO filesystem work.

    Uses content hashing (not mtime/size) to detect in-place edits that don't
    change file size and happen within filesystem mtime granularity (issue #682).
    """
    snap: Dict[str, Any] = {}
    for p in paths or []:
        try:
            with open(p, "rb") as f:
                snap[p] = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            snap[p] = None      # missing = a distinct, comparable state
    return snap


# ── Executor ──────────────────────────────────────────────────────────────────
class VendorCLIExecutor:
    """Invoke a vendor CLI non-interactively under a HARD timeout.

    Mirrors the ``(target, cmd, max_budget_usd)`` shape of the
    ``hooks.RemoteExecutionProtocol.dispatch_container`` stub, but — unlike that
    stub, which only logs and returns a fake id — this actually runs the
    subprocess, enforces the timeout with a kill, and captures partial output on
    a hang. A hung ``agy`` therefore produces a ``timed_out`` result rather than
    stalling the caller.

    The prompt is passed identity-safe by one of three modes (per the vendor's
    :class:`VendorSpec`): **inline-argv** (the prompt is substituted into argv
    as the value of ``-p``, e.g. ``agy`` ≥1.1.1), a private **0600 temp file**
    whose path is templated into argv (e.g. ``devin``), or **stdin**
    (``subprocess.run(input=...)``, legacy/future stdin-only vendors). For
    inline-argv and prompt-file modes the raw prompt never touches stdin; for
    stdin mode it never touches argv. The temp file (prompt-file mode only) is
    unlinked in a ``finally`` after the subprocess returns — even on timeout or
    error.
    """

    def __init__(
        self,
        vendor: str,
        prompt: str,
        *,
        timeout_s: int = _DEFAULT_VENDOR_TIMEOUT_S,
        budget_usd: float = 0.0,
        model: Optional[str] = None,
        mode: str = DEFAULT_MODE,
        cwd: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
        stream_callback: Any = None,
    ) -> None:
        if vendor not in VENDOR_SPECS:
            raise ValueError(
                f"unknown vendor {vendor!r}; expected one of {sorted(VENDOR_SPECS)}"
            )
        self.spec = VENDOR_SPECS[vendor]
        self.vendor = vendor
        # Prepend the dispatch preamble (non-negotiables) to every prompt by
        # default. _resolve_preamble() reads env at call time so a caller can
        # suppress (NUCLEUS_VENDOR_PREAMBLE_DISABLED) or override
        # (NUCLEUS_VENDOR_PREAMBLE) between dispatches in the same process.
        preamble = _resolve_preamble()
        base_prompt = prompt or ""
        self.prompt = (preamble + "\n\n" + base_prompt) if preamble else base_prompt
        # A timeout of 0 means NO timeout — let the agent run as long as it needs.
        # A timeout of at least 1s — the hard bound is the Python subprocess
        # timeout, independent of any CLI-internal --print-timeout.
        self.timeout_s = 0 if timeout_s == 0 else max(1, int(timeout_s))
        self.budget_usd = float(budget_usd)
        self.mode = normalize_mode(mode)          # raises on bad mode
        self.model = resolve_model(vendor, model) # raises on bad/cross-wired model
        self.model_family = resolve_model_family(self.model, self.spec.model)
        self.cwd = cwd
        self.cancel_event = cancel_event
        self.stream_callback = stream_callback

    def _budget_ok(self) -> bool:
        """Enforce the budget ceiling.

        Vendor CLIs carry ~$0 marginal cost (agy = Gemini free tier, devin =
        GLM), so the nominal per-call estimate is 0.0. ``budget_usd == 0.0``
        (the default) means "free-tier, unbounded"; any positive ceiling is
        satisfied by the 0.0 nominal cost. A *negative* budget is a hard reject
        (nonsensical ceiling), which keeps the mechanism honest rather than
        fabricating a cost model for an external process.
        """
        return self.budget_usd >= 0.0

    def _write_prompt_file(self) -> str:
        """Write the prompt to a fresh **0600** temp file; return its path.

        ``tempfile.mkstemp`` opens the file ``O_EXCL`` with mode ``0o600`` in the
        system temp dir, so the prompt is readable only by this uid and appears
        neither in argv nor on stdin. :meth:`run` unlinks it in a ``finally``, so
        it exists only while the vendor subprocess runs.
        """
        fd, path = tempfile.mkstemp(prefix="nucleus_vendor_prompt_", suffix=".txt")
        try:
            os.write(fd, self.prompt.encode("utf-8"))
        finally:
            os.close(fd)
        return path

    def _kill_proc_group(self, proc: subprocess.Popen) -> None:
        """Kill the process group rooted at *proc* (process-group leader)."""
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                proc.kill()
        except (ProcessLookupError, OSError):
            try:
                proc.kill()
            except Exception:
                pass

    def _run_subprocess(
        self, argv: List[str], stdin_input: Optional[str]
    ) -> "VendorSubprocessResult":
        """Execute the vendor CLI and return the outcome.

        Uses ``subprocess.run`` for the default (non-streaming, non-cancellable)
        path so existing offline tests remain stable, and ``subprocess.Popen``
        only when a cancellation event or streaming callback is supplied.
        """
        if self.cancel_event is None and self.stream_callback is None:
            return self._run_subprocess_sync(argv, stdin_input)
        return self._run_subprocess_streamed(argv, stdin_input)

    def _run_subprocess_sync(
        self, argv: List[str], stdin_input: Optional[str]
    ) -> "VendorSubprocessResult":
        start = time.perf_counter()
        with _DISPATCH_SEMAPHORE:
            _wait_for_load(self.timeout_s)
            try:
                proc = subprocess.run(
                    argv,
                    input=stdin_input,
                    capture_output=True,
                    text=True,
                    timeout=None if self.timeout_s == 0 else self.timeout_s,
                    check=False,
                    cwd=self.cwd,
                )
                out = _as_text(proc.stdout)
                err = _as_text(proc.stderr)
                if proc.returncode != 0 and err:
                    out = (out + "\n" + err).strip() if out else err.strip()
                if proc.returncode == 0 and not out.strip() and err.strip():
                    out = err.strip()
                return VendorSubprocessResult(
                    rc=proc.returncode,
                    output=out,
                    duration=time.perf_counter() - start,
                    timed_out=False,
                    cancelled=False,
                )
            except subprocess.TimeoutExpired as exc:
                partial = _as_text(exc.stdout) or _as_text(exc.stderr)
                return VendorSubprocessResult(
                    rc=None,
                    output=partial,
                    duration=time.perf_counter() - start,
                    timed_out=True,
                    cancelled=False,
                )

    def _run_subprocess_streamed(
        self, argv: List[str], stdin_input: Optional[str]
    ) -> "VendorSubprocessResult":
        start = time.perf_counter()
        with _DISPATCH_SEMAPHORE:
            _wait_for_load(self.timeout_s)
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE if stdin_input is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd,
                start_new_session=True,
            )

        out_chunks: List[str] = []
        result: Optional["VendorSubprocessResult"] = None

        def _drain() -> None:
            if proc.stdout is None:
                return
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                out_chunks.append(line)
                if self.stream_callback is not None:
                    try:
                        self.stream_callback(line)
                    except Exception:  # noqa: BLE001
                        pass

        drain_thread = threading.Thread(target=_drain, daemon=True)
        drain_thread.start()

        if stdin_input is not None and proc.stdin is not None:
            try:
                proc.stdin.write(stdin_input)
                proc.stdin.close()
            except BrokenPipeError:
                pass

        try:
            if self.cancel_event is not None:
                while proc.poll() is None:
                    if self.cancel_event.is_set():
                        self._kill_proc_group(proc)
                        result = VendorSubprocessResult(
                            rc=None,
                            output="",
                            duration=time.perf_counter() - start,
                            timed_out=False,
                            cancelled=True,
                        )
                        break
                    if self.timeout_s > 0 and (time.perf_counter() - start) > self.timeout_s:
                        self._kill_proc_group(proc)
                        result = VendorSubprocessResult(
                            rc=None,
                            output="",
                            duration=time.perf_counter() - start,
                            timed_out=True,
                            cancelled=False,
                        )
                        break
                    time.sleep(0.1)
            else:
                # Streaming only (no cancel event). Wait with timeout polling.
                while proc.poll() is None:
                    if self.timeout_s > 0 and (time.perf_counter() - start) > self.timeout_s:
                        self._kill_proc_group(proc)
                        result = VendorSubprocessResult(
                            rc=None,
                            output="",
                            duration=time.perf_counter() - start,
                            timed_out=True,
                            cancelled=False,
                        )
                        break
                    time.sleep(0.1)
        finally:
            if proc.poll() is None:
                self._kill_proc_group(proc)
            drain_thread.join(timeout=2.0)

        output = "".join(out_chunks)
        if result is not None:
            return VendorSubprocessResult(
                rc=result.rc,
                output=output,
                duration=result.duration,
                timed_out=result.timed_out,
                cancelled=result.cancelled,
            )

        rc = proc.returncode
        if rc is None:
            rc = -1
        return VendorSubprocessResult(
            rc=rc,
            output=output,
            duration=time.perf_counter() - start,
            timed_out=False,
            cancelled=False,
        )

    def run(self) -> VendorResult:
        if not self._budget_ok():
            return VendorResult(
                self.vendor, self.model_family, None, "budget_rejected",
                f"negative budget_usd={self.budget_usd}", 0.0,
                model_id=self.model,
            )

        binary = shutil.which(self.spec.binary)
        if binary is None:
            return VendorResult(
                self.vendor, self.model_family, None, "not_found",
                f"vendor CLI {self.spec.binary!r} not found on PATH", 0.0,
                model_id=self.model,
            )

        # PROMPT CEILING. Measured 2026-08-01: devin dies with rc=-13 (SIGPIPE)
        # at ~4.5s for prompts over ~64KB — 60,033 chars ok, 70,009 dead,
        # repeatably — while agy handled 120,018 fine. Left unguarded this
        # surfaces several layers up as "vendor produced no output", which reads
        # like a model failure rather than a size limit and sent me hunting the
        # wrong thing. Refuse up front and SAY the number.
        cap = self.spec.max_prompt_chars
        if cap and len(self.prompt) > cap:
            return VendorResult(
                self.vendor, self.model_family, None, "prompt_too_large",
                f"prompt is {len(self.prompt):,} chars but {self.vendor} caps at "
                f"{cap:,} (measured: SIGPIPE above ~64KB). Use a vendor without "
                f"this ceiling (agy handled 120,018 chars) or shorten the prompt.",
                0.0, model_id=self.model,
            )

        prompt_file: Optional[str] = None
        start = time.perf_counter()
        try:
            # Identity-safe prompt delivery, selected by the vendor's template:
            #   * prompt-file mode  → write the prompt to a private 0600 temp
            #     file and pass only its PATH in argv (stdin unused);
            #   * inline-argv mode  → substitute the prompt into a {prompt} slot
            #     in argv (stdin unused);
            #   * stdin mode        → stream the prompt over stdin (no prompt
            #     slot in argv).
            if self.spec.uses_prompt_file:
                prompt_file = self._write_prompt_file()
                stdin_input: Optional[str] = None
            elif self.spec.uses_inline_prompt:
                stdin_input = None
            else:
                stdin_input = self.prompt

            argv = self.spec.build_argv(
                self.timeout_s,
                prompt_file=prompt_file,
                prompt=self.prompt,
                mode=self.mode,
                model=self.model,
            )
            argv[0] = binary  # resolved absolute path

            # AUTOMATIC read-mode write-detection (2026-08-18). devin's
            # read_flags grant real write access (see _git_porcelain_snapshot's
            # docstring) -- the existing expect_paths/_snapshot_paths backstop
            # is real but opt-in, and most callers never pass it. This runs
            # unconditionally for every mode='read' dispatch regardless of
            # what the caller remembered to ask for. cwd=None matches the
            # vendor subprocess below, which also has no explicit cwd override
            # and inherits this process's cwd -- both observe the same tree.
            _read_mode_check = self.mode == "read"
            _porcelain_before = _git_porcelain_snapshot(self.cwd) if _read_mode_check else None

            sub = self._run_subprocess(argv, stdin_input)

            # Only a snapshot pair where BOTH sides were actually read counts
            # as evidence; None on either side means "cannot verify" and must
            # fail open (never invent a false positive from a failed check).
            _wrote_files_in_read_mode = False
            if _read_mode_check and _porcelain_before is not None:
                _porcelain_after = _git_porcelain_snapshot(self.cwd)
                if _porcelain_after is not None and _porcelain_after != _porcelain_before:
                    _wrote_files_in_read_mode = True
            duration = sub.duration
            out = sub.output
            out, nredacted = _redact_secrets(out)   # secret-hygiene backstop

            if sub.cancelled:
                status = "cancelled"
            elif sub.timed_out:
                status = "timed_out"
            else:
                status = _classify_completed(sub.rc if sub.rc is not None else -1, out)
                if _wrote_files_in_read_mode:
                    logger.warning(
                        "vendor %s ran mode='read' but the working tree changed "
                        "(git status --porcelain differs before/after) -- "
                        "read_flags grant real write access, this dispatch used it",
                        self.vendor,
                    )
                    status = "read_mode_wrote_files"
                # NEAR-MISS WARNING. A dispatch that finishes at 290s of a 300s
                # ceiling is indistinguishable from one that finished at 30s — both
                # report `ok` — yet the first will DIE the next time the machine is
                # busy. Emit the ratio so a run can be seen trending toward the wall
                # before it hits it.
                if self.timeout_s and duration > 0.6 * self.timeout_s:
                    logger.warning(
                        "vendor %s/%s NEAR TIMEOUT: %.1fs of %ds ceiling (%.0f%%) — "
                        "raise NUCLEUS_VENDOR_TIMEOUT_S or reduce concurrency",
                        self.vendor, self.model, duration, self.timeout_s,
                        100.0 * duration / self.timeout_s,
                    )
            return VendorResult(
                self.vendor, self.model_family, sub.rc, status, out, duration,
                model_id=self.model, redacted=nredacted,
            )
        except Exception as exc:  # noqa: BLE001 — a dispatch bug must never stall
            duration = time.perf_counter() - start
            logger.warning("vendor %s dispatch failure: %s", self.vendor, exc)
            return VendorResult(
                self.vendor, self.model_family, None, "error",
                f"dispatch failure: {exc}", duration,
                model_id=self.model,
            )
        finally:
            # Delete the prompt temp file even on timeout/error — the prompt must
            # not outlive the subprocess on disk.
            if prompt_file is not None:
                try:
                    os.unlink(prompt_file)
                except OSError as exc:  # noqa: BLE001 — best-effort cleanup
                    logger.warning(
                        "vendor %s: failed to unlink prompt file %s: %s",
                        self.vendor, prompt_file, exc,
                    )


# ── Capture ───────────────────────────────────────────────────────────────────
def _prompt_digest(prompt: str) -> str:
    """SHA-256 of the prompt — the envelope carries the digest, never the raw
    prompt, so identity in a prompt cannot land in a relay archive."""
    return "sha256:" + hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()


def _capture(
    spec: VendorSpec,
    result: VendorResult,
    prompt_digest: str,
    artifact_ref: str,
    to_role: str,
    *,
    force_fs: bool,
    effect: str = "unknown",
    artifact_ref_source: str = "no_vendor_increment",
    nonqualifying_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Write the relay capture envelope + a vendor-tagged engram.

    The relay ``body`` is a JSON *string* carrying ``artifact_refs`` — this is the
    exact schema ``relay_post``'s ``NUCLEUS_RELAY_STRICT`` gate reads (it JSON-
    decodes the body and requires at least one non-relay-id reference). Both
    side effects are fault-isolated: a failure in either is recorded but never
    raised, so a capture hiccup can't break the dispatch.

    The body keeps the ``"model"`` (family) key for census stability and adds
    ``"model_id"`` (the selectable id that ran) and ``"effect"`` (the
    expect_paths verdict: ``unknown`` / ``files_touched`` / ``no_files_touched``).
    crit-4 v2.1: the body gains an un-forgeable causal-edge signature. We stamp
    ``ts`` + ``result_sha256`` (SHA-256 over the FULL result, pre-truncation — the
    body only carries ``result[:3000]``, so the signed hash, not the truncated
    text, is the binding) and HMAC-sign the exact field set with the brain's
    machine key. The signature travels inside the JSON-string body that
    ``relay_post`` stores verbatim, so it reaches the FS envelope with ZERO
    changes to relay/core.py and zero new trust in the relay transport. Signing
    is fault-isolated: on any failure (no brain, IO error) we stamp
    ``dispatch_sig=null`` — the dispatch/capture never break, the envelope simply
    will not count in the census (fail-closed at the census, not at dispatch).
    """
    artifact_refs = [artifact_ref]
    ts = int(time.time())
    # Bind the FULL result (pre-truncation), not the truncated body text.
    result_sha256 = hashlib.sha256((result.result or "").encode("utf-8")).hexdigest()

    dispatch_sig: Optional[str] = None
    try:
        # periphery→periphery, lazy (ADR-0043 pattern; keeps the boundary green).
        from .auth.signature_guard import get_signature_guard

        dispatch_sig = get_signature_guard().sign_vendor_dispatch(
            vendor=spec.vendor,
            model=result.model,
            prompt_digest=prompt_digest,
            artifact_refs=artifact_refs,
            result_sha256=result_sha256,
            status=result.status,
            ts=ts,
        )
    except Exception as exc:  # noqa: BLE001 — signing must never break dispatch
        logger.warning("vendor capture dispatch signing failed: %s", exc)
        dispatch_sig = None

    body = json.dumps(
        {
            "vendor": spec.vendor,
            "model": result.model,
            "model_id": result.model_id,
            "prompt_digest": prompt_digest,
            "result": result.result[:3000],
            "result_sha256": result_sha256,
            "rc": result.rc,
            "status": result.status,
            "produced_output": result.produced_output,
            "redacted": result.redacted,
            "effect": effect,
            "duration": round(result.duration, 3),
            # NOTE: an earlier duplicate "artifact_refs": [artifact_ref] used to sit
            # here and was silently discarded by the later key below (F601). Both
            # held the same value — artifact_refs is [artifact_ref] and is never
            # reassigned — so removing the losing one is byte-identical.
            # THE FIELD THE CENSUS COUNTS ON. Absent until 2026-08-02, and its
            # absence made G1 crit-3/crit-4 structurally unpassable: the census
            # requires artifact_ref_source == "vendor_derived" to count an
            # envelope as a causal edge, and no capture had ever written it.
            # Measured before the fix: 1,021 cross_vendor envelopes on disk,
            # ZERO qualifying — not gameable, DEAD. The zero had been read as
            # "not enough real cross-vendor work yet"; it was structural.
            # A criterion whose instrument cannot emit a passing value is the
            # required-check-that-cannot-report pattern, at the governance layer.
            "artifact_ref_source": artifact_ref_source,
            # THE THIRD-STATE FIELD (director 2026-08-09). When a capture is not
            # vendor_derived, WHY it failed to qualify is load-bearing at the
            # census: "attribution_unprovable" (a write dispatch that moved HEAD
            # but supplied no expect_paths evidence) is a REMEDIABLE state —
            # genuine-maybe vendor work the instrument simply could not attribute
            # — and must be counted apart from "read_mode_no_increment" /
            # "head_unchanged" / "head_moved_by_foreign_commit", which are
            # provably NOT vendor increments. Folding the two together is what
            # would let the strict instrument read zero-by-construction and hide
            # it as "no real work". null when the capture qualifies.
            "artifact_ref_nonqualifying_reason": nonqualifying_reason,
            "ts": ts,
            "artifact_refs": artifact_refs,
            "dispatch_sig": dispatch_sig,
        },
        ensure_ascii=False,
    )

    relay_res: Dict[str, Any]
    try:
        from . import relay_ops  # periphery→core, lazy (import-safety)

        relay_res = relay_ops.relay_post(
            to=to_role,
            subject=f"[cross-vendor] {spec.vendor}/{result.model} {result.status}",
            body=body,
            sender=spec.sender,
            priority="normal",
            # force_fs pins the local-FS write path so the STRICT artifact_refs
            # gate runs client-side (the HTTP transport short-circuits it) — a
            # self-contained hash-binding guarantee.
            force_fs=force_fs,
        )
    except Exception as exc:  # noqa: BLE001 — fault isolation
        logger.warning("vendor capture relay_post failed: %s", exc)
        relay_res = {"sent": False, "error": f"relay_exception: {exc}"}

    engram_res: Dict[str, Any]
    try:
        from nucleus_wedge.store import Store  # separate package; lazy + guarded

        tags = [tag for tag in spec.engram_tags if not tag.startswith("vendor:")] + [
            f"vendor:{result.model}",
            f"artifact:{artifact_ref}",
            f"status:{result.status}",
            f"model:{result.model_id}",
        ]
        if effect != "unknown":
            tags.append(f"effect:{effect}")
        engram_res = Store().append(
            value=(result.result[:2000] or prompt_digest),
            kind="activity",
            tags=tags,
            source_agent=spec.sender,
        )
    except Exception as exc:  # noqa: BLE001 — fault isolation
        logger.warning("vendor capture engram append failed: %s", exc)
        engram_res = {"error": f"engram_exception: {exc}"}

    return {"relay": relay_res, "engram": engram_res}


def _record_dispatch_health(spec: "VendorSpec", result: "VendorResult") -> None:
    """Record one dispatch outcome into the per-process ``ModelHealthRegistry``.

    This is the seam that feeds Layer 1 of ``model_registry``: every dispatch
    funnels through :func:`dispatch_and_capture`, so recording here is the one
    place the registry learns real outcomes (success → cooldown cleared;
    failure → classified + cooldown set). Without it the registry's
    ``is_available`` / ``availability_score`` are static and the dynamic
    fallback chain (Layer 5) has no signal to route around a quota'd model.

    Fault-isolated by contract: the health registry is observability-only, so
    any failure here (missing module, broken singleton, bad key) is logged at
    debug and swallowed — it must NEVER turn a successful dispatch into a failed
    one. Records on the SELECTABLE model id when one was resolved, else the
    vendor's ``default_model``, else the model family name.

    ``VendorResult`` does not expose stderr, but ``model_registry.classify_failure``
    keys off stderr patterns. We bridge by passing the real execution output
    (``result.result``) as the stderr text so quota/rate/auth signatures in the
    vendor's actual output are classified correctly, and folding ``status=...``
    onto it so a ``timed_out`` status (which has no stderr of its own) and an
    ``intent_only`` status (which has produced output but no concrete execution
    evidence) are classified by their status string. Empty/error output with no
    recognizable signature stays ``F_UNKNOWN``, which is correct — it has no
    quota/rate/auth signature.

    LOCAL PRECONDITION EXCLUSIONS: ``not_found`` (vendor binary missing on
    PATH), ``budget_rejected`` (negative ``budget_usd``), and
    ``prompt_too_large`` (prompt over the vendor's ``max_prompt_chars`` cap)
    are rejected by :meth:`VendorCLIExecutor.run` BEFORE the model is ever
    invoked. They say nothing about the model's health — a missing binary or
    an oversized prompt is a caller/environment problem, not a quota, rate,
    auth, or timeout signal from the model. Recording them as failures would
    push a healthy model into cooldown (and, after three ``prompt_too_large``
    rejections, into an *inferred-quota* cooldown via the
    ``consecutive_empty`` heuristic) for reasons that have nothing to do with
    the model. They are therefore excluded from recording entirely: neither a
    success nor a failure is stamped, so the model's cooldown / availability
    score is unaffected by pre-dispatch rejections.
    """
    # Pre-dispatch rejections — the model never ran, so its health state must
    # not move. See the docstring's LOCAL PRECONDITION EXCLUSIONS block.
    _PRECONDITION_STATUS_EXCLUSIONS = frozenset(
        {"not_found", "budget_rejected", "prompt_too_large"}
    )
    if result.status in _PRECONDITION_STATUS_EXCLUSIONS:
        return
    try:
        from .model_registry import get_registry
        model_key = result.model_id or spec.default_model or result.model
        if not model_key:
            return
        registry = get_registry()
        if result.status == "ok" and result.produced_output:
            registry.record_success(spec.vendor, model_key)
        else:
            # Pull the real execution output from result.result so
            # classify_failure can match quota/rate/auth/timeout signatures
            # in the actual vendor output. A bare status string carries no
            # quota/rate/auth signal and would leave every failure as
            # F_UNKNOWN. We still fold the status in so timed_out (which has
            # no stderr of its own) and intent_only (which has produced output
            # but no concrete execution evidence) are classified by their
            # status string.
            stderr_text = (result.result or "").strip()
            if not stderr_text:
                stderr_text = f"status={result.status}"
            else:
                stderr_text = f"{stderr_text}\nstatus={result.status}"
            # intent_only: vendor emitted non-blank text but only stated an
            # intention to act. For cooldown/availability heuristics this is
            # empty of concrete output, so treat it the same as empty_output.
            is_empty = (
                not result.produced_output
                or result.status == "intent_only"
            )
            registry.record_failure(
                spec.vendor, model_key,
                stderr=stderr_text,
                rc=result.rc if result.rc is not None else 1,
                stdout_empty=is_empty,
            )
    except Exception as exc:  # noqa: BLE001 — observability must never break dispatch
        logger.debug("dispatch health record failed: %s", exc)


def dispatch_and_capture(
    vendor: str,
    prompt: str,
    artifact_ref: str,
    *,
    to_role: Optional[str] = None,
    model: Optional[str] = None,
    mode: str = DEFAULT_MODE,
    expect_paths: Optional[List[str]] = None,
    timeout_s: int = _DEFAULT_VENDOR_TIMEOUT_S,
    budget_usd: float = 0.0,
    force_fs: bool = True,
) -> Dict[str, Any]:
    """Run one vendor CLI dispatch and capture its envelope + engram.

    Returns the executor result fields (vendor, model_family, model_id, rc,
    status, result, produced_output, duration) plus ``artifact_ref``, ``to``,
    ``mode``, ``effect``, ``changed_paths`` and a ``capture`` sub-dict
    (``{"relay": ..., "engram": ...}``). This is the single funnel used by the
    ``nucleus dispatch`` verb and the swarm vendor-persona hook.

    When *expect_paths* is provided, the caller opts in to a pre/post
    ``os.stat`` snapshot that classifies the run as ``files_touched`` or
    ``no_files_touched``. When it is ``None`` (the default), ``effect`` is
    ``"unknown"`` and ZERO filesystem work is done.

    **v3 anchor precondition:** when ``NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED=1``,
    the caller-provided ``artifact_ref`` is IGNORED and the capture instrument
    stamps it from the worktree's git HEAD SHA after the vendor runs. This
    closes the crit-4 v3 gap: "the dispatch/relay tool schema MUST NOT accept
    artifact-ref as caller input; the capture instrument stamps it from the
    vendor worktree's git-reported SHA."
    """
    spec = VENDOR_SPECS.get(vendor)
    if spec is None:
        raise ValueError(
            f"unknown vendor {vendor!r}; expected one of {sorted(VENDOR_SPECS)}"
        )
    to_role = to_role or spec.to_default
    canon = normalize_mode(mode)

    pre = _snapshot_paths(expect_paths)              # {} when None ⇒ ZERO fs work
    pre_sha = _read_worktree_head_sha()              # BEFORE — see stamping block
    # Stale-checkout guard (2026-08-04 incident): best-effort count of how many
    # commits the worktree HEAD is behind its configured upstream. A non-zero
    # count means the vendor is about to read or mutate code that is behind the
    # real upstream — a dispatch against such a checkout can "find" already-
    # fixed bugs or "fix" them again, producing a diff that silently reverts
    # merged upstream work. This is a SIGNAL, never a gate: it must never turn
    # a working dispatch into a broken one.
    behind_upstream = _count_behind_upstream()
    if behind_upstream and behind_upstream > 0:
        logger.warning(
            "dispatch_and_capture: worktree HEAD is %d commit(s) behind its "
            "configured upstream — the vendor may be operating on stale code "
            "relative to upstream; a build diff against this checkout could "
            "silently revert already-merged upstream fixes. "
            "(local_head_behind_upstream=%d)",
            behind_upstream, behind_upstream,
        )
    in_progress = _rebase_or_merge_in_progress()
    if in_progress:
        logger.warning(
            "dispatch_and_capture: worktree has an in-progress %s — the "
            "vendor subprocess shares this cwd and may misread unrelated "
            "conflict markers/state as something to resolve, staging files "
            "outside this dispatch's scope. (git_operation_in_progress=%s)",
            in_progress, in_progress,
        )
    result = VendorCLIExecutor(
        vendor, prompt, timeout_s=timeout_s, budget_usd=budget_usd,
        model=model, mode=canon,
    ).run()
    # Feed the per-process ModelHealthRegistry (model_registry Layer 1) so
    # cooldowns / availability_score track real dispatch outcomes. Recorded
    # BEFORE the git-stamping early-return so a model failure is captured even
    # when git is unavailable downstream. Strict fault isolation at the call
    # site (defense in depth on top of the helper's own try/except): the
    # registry is observability-only, so any failure here is logged and
    # swallowed — it must NEVER turn a successful dispatch into a failed one.
    try:
        _record_dispatch_health(spec, result)
    except Exception as exc:  # noqa: BLE001 — observability must never break dispatch
        logger.debug("dispatch health record failed at call site: %s", exc)
    effect, changed_paths = "unknown", []
    if expect_paths:                                 # only when caller opted in (issue #682: was `if pre:` which fails on empty dict)
        post = _snapshot_paths(expect_paths)
        changed_paths = [p for p in expect_paths if pre.get(p) != post.get(p)]
        effect = "files_touched" if changed_paths else "no_files_touched"

    # v3, UNCONDITIONAL: stamp artifact_ref from the worktree's git HEAD SHA —
    # NEVER from caller input. Any caller-supplied value is discarded here.
    # If git is unavailable the capture FAILS CLOSED (no artifact_ref = no
    # qualifying increment); it must never fall back to the caller's value,
    # because that is precisely the forgeable path PRINCIPAL line 77 forbids.
    #
    # v3.1 (2026-08-01) — CLOSES THE cd-CHOSEN-SHA HOLE.
    #
    # Removing `--artifact-ref` closed the path where a caller TYPES the SHA.
    # It did not close the path where a caller CHOOSES it: this stamp read
    # ambient HEAD in the dispatching process's cwd, and the vendor subprocess
    # inherits that same cwd, so `cd <any repo>` selected the value. Every
    # read-only dispatch stamped that repo's HEAD and scored as a qualifying
    # increment. Cheapest attack on crit-3, needing no commit, no edit and no
    # repo-mint: cd into an `outside`-labelled repo and loop 25 free dispatches.
    #
    # PRINCIPAL v3 line 77 requires the ref be stamped "from the vendor
    # worktree's git-reported SHA" — i.e. it must name an increment the VENDOR
    # produced. Ambient HEAD names whatever was already there. So:
    #
    #   qualifying  <=>  mode is write  AND  HEAD MOVED while the vendor ran
    #
    # A read-mode dispatch produces no increment by definition. A write-mode
    # dispatch that commits nothing leaves HEAD where it was. Neither can mint
    # a causal edge any more. This is a bug fix, not an amendment: it makes the
    # instrument do what the criterion already says, and it can only ever STOP
    # counting envelopes that never qualified — it cannot make a
    # previously-non-qualifying envelope qualify.
    #
    # Non-qualifying dispatches STILL CAPTURE — relay and engram are
    # observability, and agents depend on the vendor's output being relayed.
    # Only the SOURCE LABEL changes, and the census counts solely on that
    # (`_is_vendor_derived_artifact_ref`). Suppressing capture instead was the
    # first cut here and it broke 9 tests by silently dropping the relay for
    # every read-mode dispatch — the common case. Labelling closes the hole;
    # silence would have closed the pathway.
    post_sha = _read_worktree_head_sha()
    head_moved = bool(post_sha and pre_sha and post_sha != pre_sha)
    # v3.2 (2026-08-09): head_moved alone is insufficient — `git commit
    # --allow-empty` moves HEAD without touching any file, and a mid-range git
    # failure hides what the commits touched. Both must fail closed: the
    # instrument can only qualify an increment whose touched paths it can
    # verify. _commits_changed_paths returns None on git failure (fail closed)
    # or set() on an empty commit (head moved, nothing changed).
    commit_paths: Optional[Set[str]] = (
        _commits_changed_paths(pre_sha, post_sha)
        if head_moved and canon == "write"
        else None
    )
    # v3.3 (2026-08-09) — CLOSES THE FOREIGN-CONCURRENT-COMMIT HOLE.
    #
    # v3.2's `commit_paths` check stopped empty commits and mid-range git
    # failures from minting qualifying envelopes. It did not stop a FOREIGN
    # lane's commits from doing so: `head_moved` only tests that SOME commit
    # landed while the vendor ran, not that THIS dispatch produced it. A peer
    # lane committing to the shared worktree during the window moved HEAD on
    # paths this dispatch never touched, and `commit_paths` — drawn from every
    # commit in the pre..post range — dutifully listed them. The instrument
    # then credited those foreign concurrent commits to a dispatch that was
    # forbidden to commit (read-mode) or that committed nothing of its own.
    # The cheapest attack on crit-3 now needed no cd and no confederate: just
    # run a read-mode dispatch while any other lane commits, and the ambient
    # HEAD movement scores the envelope for free.
    #
    # Attribution works by INTERSECTION, but ONLY when the caller provides
    # path evidence via `expect_paths`. The moved HEAD's commit_paths are
    # intersected with THIS dispatch's own changed_paths — the paths the
    # dispatch demonstrably modified, captured from the pre/post worktree
    # snapshot the caller opted into. Both sets are normalized to repo-relative
    # POSIX before the intersection, so absolute paths, trailing slashes, and
    # cwd-relative forms cannot smuggle a foreign path past the match. A HEAD
    # that moved on a foreign lane's commits touches none of this dispatch's
    # paths: the intersection is empty and the envelope does not qualify
    # (`head_moved_by_foreign_commit`).
    #
    # When NO `expect_paths` evidence exists the instrument CANNOT do the
    # intersection — it has no record of which paths this dispatch modified.
    # Rather than fail closed (which would break every caller that doesn't pass
    # expect_paths — the common case), it falls back to the v3.2 check: head
    # moved + commit_paths non-empty. This is not a regression — it is the
    # same behavior that shipped under v3.2. The v3.3 intersection is a
    # TIGHTENING available to callers who opt into path evidence; callers who
    # don't are no worse off than before. Making expect_paths mandatory would
    # break all existing call sites for a hole that only manifests when a
    # foreign lane commits during the dispatch window.
    has_path_evidence = bool(changed_paths)
    attributable_paths: Set[str] = set()
    normalized_changed: Set[str] = set()
    normalization_failed = False
    if has_path_evidence and commit_paths is not None:
        for p in changed_paths:
            normed = _repo_relative_posix(p)
            if normed is not None:
                normalized_changed.add(normed)
        # If EVERY path failed normalization, the intersection is vacuously
        # empty — but the cause is NOT a foreign commit; it is that the
        # instrument could not map the dispatch's changed_paths into the
        # repo's coordinate space (e.g. process cwd outside the repo, paths
        # outside the repo root). Labelling this "head_moved_by_foreign_commit"
        # would be a lie: we don't know whether the commit was foreign or not
        # because we couldn't normalize the evidence to compare. The honest
        # label is "attribution_unprovable" — fail closed with the real reason.
        normalization_failed = (
            len(normalized_changed) == 0 and len(changed_paths) > 0
        )
        attributable_paths = commit_paths & normalized_changed
    # v3.3 FAIL-CLOSED (director 2026-08-09): qualification requires PATH
    # EVIDENCE. A prior revision added an ``else`` that fell back to v3.2
    # (head moved + non-empty commit_paths) when the caller passed no
    # expect_paths — which is the common case for build_runner. That fallback
    # REOPENED the exact foreign-commit hole this block exists to close: a
    # concurrent foreign commit satisfies "head moved + commit_paths non-empty"
    # and was credited to a dispatch that produced nothing. Proven live: a
    # foreign commit with no expect_paths qualified True. Without changed_paths
    # the instrument CANNOT attribute the increment to this dispatch, so it MUST
    # NOT qualify — attribution_unprovable, fail closed. The cure for the common
    # case is to give the instrument evidence (callers pass expect_paths), NEVER
    # to loosen the rule.
    qualifies = (
        bool(post_sha) and canon == "write" and head_moved
        and commit_paths is not None and len(commit_paths) > 0
        and has_path_evidence and len(attributable_paths) > 0
    )
    nonqualifying_reason = (
        None if qualifies
        else "read_mode_no_increment" if canon != "write"
        else "head_unchanged" if not head_moved
        else "changed_paths_unavailable" if commit_paths is None
        else "empty_commit_no_files" if len(commit_paths) == 0
        else "attribution_unprovable" if (not has_path_evidence or normalization_failed)
        else "head_moved_by_foreign_commit"
    )

    stamped_sha = post_sha
    if stamped_sha:
        artifact_ref = stamped_sha
        if qualifies:
            logger.info(
                "artifact_ref vendor-derived: %s (head moved %s..%s)",
                stamped_sha[:12], (pre_sha or "?")[:12], stamped_sha[:12],
            )
        else:
            # fw-1785908471: "NON-qualifying (head_unchanged)" was misleading
            # in dry-run context — the vendor may have produced output but
            # the worktree head didn't move because dry-run skips commits.
            # Clarify that this is an observation, not a failure verdict.
            logger.info(
                "artifact_ref not qualified as vendor increment (%s): "
                "head %s..%s mode=%s — this is informational, not a failure",
                nonqualifying_reason, (pre_sha or "?")[:12],
                stamped_sha[:12], canon,
            )
    else:
        # Fail closed: no git SHA = no qualifying increment
        out = result.to_dict()
        out.update({
            "prompt_digest": _prompt_digest(prompt),
            "artifact_ref": None,
            "artifact_ref_source": "vendor_derived_failed",
            "to": to_role,
            "mode": canon,
            "effect": effect,
            "changed_paths": changed_paths,
            "capture": {"relay": None, "engram": None,
                        "error": "worktree_sha_unavailable"},
        })
        out["timeout_s"] = timeout_s
        out["local_head_behind_upstream"] = behind_upstream
        return out

    digest = _prompt_digest(prompt)
    capture = _capture(spec, result, digest, artifact_ref, to_role,
                       force_fs=force_fs, effect=effect,
                       artifact_ref_source=(
                           "vendor_derived" if qualifies else "no_vendor_increment"),
                       nonqualifying_reason=(None if qualifies else nonqualifying_reason))

    out = result.to_dict()
    out.update({
        "prompt_digest": digest, "artifact_ref": artifact_ref, "to": to_role,
        "mode": canon, "effect": effect, "changed_paths": changed_paths,
        "capture": capture,
    })
    # The census filters on this value (cross_repo_census:
    # _is_vendor_derived_artifact_ref — only "vendor_derived" qualifies), so it
    # is the single field that decides whether a capture is COUNTABLE.
    #
    # It is NOT unconditional. "vendor_derived" is claimed only when HEAD moved
    # during a write-mode dispatch — i.e. the vendor actually produced the
    # increment the ref names. Everything else is stamped, relayed and captured
    # exactly as before, but under "no_vendor_increment" with the reason
    # recorded, so it is visible and uncountable rather than invisible.
    out["artifact_ref_source"] = (
        "vendor_derived" if qualifies else "no_vendor_increment"
    )
    if not qualifies:
        out["artifact_ref_nonqualifying_reason"] = nonqualifying_reason
    out["head_before"] = pre_sha
    out["head_after"] = post_sha
    out["timeout_s"] = timeout_s
    out["local_head_behind_upstream"] = behind_upstream
    return out


def capture_machinery_commit(
    *,
    producer: str,
    changed_files: List[str],
    pre_head: Optional[str],
    post_head: Optional[str],
    commit_message: str,
    to_role: Optional[str] = None,
    force_fs: bool = True,
) -> Dict[str, Any]:
    """Capture ONE relay envelope for a commit made directly by nucleus build
    machinery (e.g. ``build_and_merge._commit_changed_files``) instead of by
    a dispatched vendor CLI.

    fw-1786271303 / fw-1786271394 (chief-decided fix, "capture-at-the-commit"):
    ``build_and_merge``'s own commit ran as a bare ``subprocess.run(["git",
    "commit", ...])`` outside :func:`dispatch_and_capture` — the ONLY code
    path that had ever written a capture envelope. A plain ``nucleus build``
    could therefore never produce a QUALIFYING ``artifact_ref`` envelope: a
    live proving run showed 18/18 write dispatches reading ``head_unchanged``
    (vendor dispatches never commit their own work) while the one commit that
    DID happen — the merge-stage commit — was never captured at all. This
    closes that structural gap by reusing the SAME writer (:func:`_capture`)
    and the SAME git-evidence machinery :func:`dispatch_and_capture` uses
    (:func:`_commits_changed_paths`, :func:`_repo_relative_posix`) rather than
    forking a second serialization. The only difference from a vendor
    dispatch is that the caller already made the commit and knows its
    pre/post HEAD and changed-file set — there is no vendor subprocess to run
    and no pre/post ``os.stat`` snapshot to take.

    The envelope is stamped ``artifact_ref_source="machinery_derived"`` —
    NEVER ``"vendor_derived"``. No vendor CLI ran here; claiming vendor
    provenance would fake a vendor label and silently inflate crit-3's
    ≥2-genuine-vendor-surface span with a surface that is not a vendor.
    ``cross_repo_census`` carries a dedicated
    ``_is_machinery_derived_artifact_ref`` predicate so this class of
    increment is COUNTABLE and VISIBLE under its own honest name, instead of
    being folded into either "vendor work" or "no real work".

    Qualification mirrors :func:`dispatch_and_capture`'s v3.2/v3.3 predicate,
    minus the read/write-mode branch (a commit is inherently a write): HEAD
    must have moved, the commits in ``pre_head..post_head`` must be
    git-evidenced (not ``None`` — a mid-range git failure fails closed) and
    non-empty (not an empty commit), and the caller-declared *changed_files*
    must intersect the commits' actual touched paths.

    Fault-isolated on missing HEADs exactly like ``dispatch_and_capture``: no
    git SHA ⇒ no envelope, fail closed. This function has no return-code
    contract with the caller — it exists only for its capture side effect,
    so a caller invokes it strictly AFTER its own commit already succeeded.
    """
    head_moved = bool(post_head and pre_head and post_head != pre_head)
    commit_paths: Optional[Set[str]] = (
        _commits_changed_paths(pre_head, post_head) if head_moved else None
    )
    has_path_evidence = bool(changed_files)
    normalized_changed: Set[str] = set()
    normalization_failed = False
    if has_path_evidence:
        for p in changed_files:
            normed = _repo_relative_posix(p)
            if normed is not None:
                normalized_changed.add(normed)
        normalization_failed = (
            len(normalized_changed) == 0 and len(changed_files) > 0
        )
    attributable_paths: Set[str] = (
        (commit_paths & normalized_changed) if commit_paths is not None else set()
    )
    qualifies = (
        bool(post_head) and head_moved
        and commit_paths is not None and len(commit_paths) > 0
        and has_path_evidence and len(attributable_paths) > 0
    )
    nonqualifying_reason = (
        None if qualifies
        else "head_unchanged" if not head_moved
        else "changed_paths_unavailable" if commit_paths is None
        else "empty_commit_no_files" if len(commit_paths) == 0
        else "attribution_unprovable" if (not has_path_evidence or normalization_failed)
        else "head_moved_by_foreign_commit"
    )

    if not post_head:
        # Fail closed: no git SHA = no envelope, mirrors dispatch_and_capture.
        return {
            "producer": producer,
            "mode": "write",
            "to": to_role or "cross_vendor",
            "artifact_ref": None,
            "artifact_ref_source": "machinery_derived_failed",
            "changed_paths": [],
            "capture": {"relay": None, "engram": None,
                       "error": "worktree_sha_unavailable"},
            "head_before": pre_head,
            "head_after": post_head,
        }

    spec = VendorSpec(
        vendor=producer,
        model="machinery",
        binary="",
        sender=producer,
        to_default="cross_vendor",
        engram_tags=(f"producer:{producer}", "surface:machinery"),
        argv_template=(),
    )
    result = VendorResult(
        vendor=producer,
        model="machinery",
        rc=0,
        status="ok",
        result=commit_message,
        duration=0.0,
        model_id=producer,
    )
    resolved_to_role = to_role or spec.to_default
    source = "machinery_derived" if qualifies else "no_vendor_increment"
    digest = _prompt_digest(commit_message)
    capture = _capture(
        spec, result, digest, post_head, resolved_to_role,
        force_fs=force_fs,
        effect=(
            "files_touched" if attributable_paths
            else "no_files_touched" if commit_paths is not None
            else "unknown"
        ),
        artifact_ref_source=source,
        nonqualifying_reason=(None if qualifies else nonqualifying_reason),
    )

    out: Dict[str, Any] = {
        "producer": producer,
        "mode": "write",
        "to": resolved_to_role,
        "artifact_ref": post_head,
        "artifact_ref_source": source,
        "changed_paths": sorted(attributable_paths),
        "capture": capture,
        "head_before": pre_head,
        "head_after": post_head,
    }
    if not qualifies:
        out["artifact_ref_nonqualifying_reason"] = nonqualifying_reason
    return out


# ── CLI entry (flag-gated) ────────────────────────────────────────────────────
def dispatch_cli(
    vendor: str,
    prompt: Optional[str],
    artifact_ref: Optional[str],
    *,
    to_role: Optional[str] = None,
    model: Optional[str] = None,
    mode: str = DEFAULT_MODE,
    timeout_s: int = _DEFAULT_VENDOR_TIMEOUT_S,
    budget_usd: float = 0.0,
) -> tuple[int, Dict[str, Any]]:
    """Backing logic for ``nucleus dispatch`` — returns ``(exit_code, payload)``.

    Flag gate lives here so the guarantee "flag OFF ⇒ no invocation" is a single
    testable seam. Exit codes:
      * 2 — usage / flag OFF (executor never invoked)
      * 3 — capture rejected (STRICT gate) or relay failed
      * 1 — vendor errored / timed out / empty_output / intent_only / no_files_touched
      * 0 — success
    """
    if not cross_vendor_enabled():
        return 2, {"error": "cross_vendor_disabled", "message": CROSS_VENDOR_DISABLED_MSG}
    if vendor not in VENDOR_SPECS:
        return 2, {
            "error": "unknown_vendor",
            "message": f"vendor must be one of {sorted(VENDOR_SPECS)}",
        }
    if not prompt:
        return 2, {
            "error": "no_prompt",
            "message": "provide --prompt, --prompt-file, or pipe the prompt on stdin",
        }
    # NO artifact_ref PRECONDITION HERE — this guard made `nucleus dispatch`
    # impossible to call.
    #
    # It is a leftover from the pre-v3 design, where the caller supplied the ref.
    # Under PRINCIPAL v3 the CLI deliberately does NOT expose --artifact-ref
    # (cli.py says so explicitly: a caller-supplied ref is forgeable, so the
    # capture instrument stamps it from the vendor worktree's git HEAD instead).
    # So `artifact_ref` is ALWAYS None on this path, this check ALWAYS fired,
    # and the CLI returned:
    #
    #     "--artifact-ref is required (commit SHA / PR# / file path)"
    #
    # naming a flag argparse is designed to REJECT. A remedy that cannot be
    # followed — the same shape as advising `chmod` for a chflags lock. Verified
    # uncallable with git fully unlocked, so this was not a git-derivation
    # failure: the guard rejected the input before the stamping code could run.
    #
    # Failing closed still happens, in the right place: dispatch_and_capture
    # stamps from git HEAD and returns artifact_ref_source="vendor_derived_failed"
    # with capture suppressed if git is unavailable. That is the check that
    # belongs here, and it already exists downstream.

    out = dispatch_and_capture(
        vendor, prompt, artifact_ref,
        to_role=to_role, model=model, mode=mode,
        timeout_s=timeout_s, budget_usd=budget_usd,
    )
    relay = (out.get("capture") or {}).get("relay") or {}
    if not relay.get("sent"):
        return 3, out
    if out.get("status") != "ok":
        return 1, out
    if out.get("effect") == "no_files_touched":
        return 1, out
    return 0, out


# ── Swarm vendor-persona hook ─────────────────────────────────────────────────
def run_swarm_vendor_persona(
    vendor: str,
    mission_id: str,
    goal: str,
    step: int,
    *,
    timeout_s: int = _DEFAULT_VENDOR_TIMEOUT_S,
    budget_usd: float = 0.05,
    to_role: str = "cross_vendor",
) -> Dict[str, Any]:
    """Swarm divert: run a vendor persona through the CLI executor + capture.

    Returns an artifact dict of the SAME shape the mission loop builds for
    internal agents, so it flows unchanged into ``_save_mission_artifacts``. The
    capture envelope's ``artifact_ref`` is the mission summary path — a real file
    reference that satisfies the STRICT gate and binds the vendor contribution to
    this mission's persisted output.
    """
    artifact_ref = f".brain/swarms/{mission_id}/summary.md"
    prompt = f"[SWARM {mission_id}] Step {step}: {goal}"
    try:
        out = dispatch_and_capture(
            vendor, prompt, artifact_ref,
            to_role=to_role, timeout_s=timeout_s, budget_usd=budget_usd,
        )
        result_text = out.get("result") or (
            f"(vendor {vendor} produced no output; status={out.get('status')})"
        )
        return {
            "agent": vendor,
            "step": step,
            "job_type": f"VENDOR_CLI:{VENDOR_SPECS[vendor].model}",
            "result": result_text[:3000],
            "vendor_status": out.get("status"),
            "artifact_refs": [artifact_ref],
        }
    except Exception as exc:  # noqa: BLE001 — never break the mission loop
        logger.error("swarm vendor persona %s failed: %s", vendor, exc)
        return {
            "agent": vendor,
            "step": step,
            "error": f"vendor dispatch failed: {exc}",
        }


__all__ = [
    "FLAG",
    "CROSS_VENDOR_DISABLED_MSG",
    "ONBOARD_CONFIG_NAME",
    "ONBOARD_HOST_CLI",
    "cross_vendor_enabled",
    "write_onboard_config",
    "detect_vendor_clis",
    "VendorSpec",
    "VENDOR_SPECS",
    "VENDOR_PERSONAS",
    "VendorResult",
    "VendorCLIExecutor",
    "dispatch_and_capture",
    "capture_machinery_commit",
    "dispatch_cli",
    "run_swarm_vendor_persona",
    "normalize_mode",
    "resolve_model",
    "VENDOR_MODES",
    "DEFAULT_MODE",
]
