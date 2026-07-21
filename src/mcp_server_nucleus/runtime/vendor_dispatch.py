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
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nucleus.vendor_dispatch")

# ── Flag ──────────────────────────────────────────────────────────────────────
FLAG = "NUCLEUS_CROSS_VENDOR"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

# v3 anchor precondition: when ON, artifact_ref is vendor-derived (stamped from
# the worktree's git HEAD SHA), NOT accepted as caller input. This closes the
# crit-4 v3 gap: "the dispatch/relay tool schema MUST NOT accept artifact-ref
# as caller input; the capture instrument stamps it from the vendor worktree's
# git-reported SHA."
ARTIFACT_REF_VENDOR_DERIVED_FLAG = "NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED"


def _artifact_ref_vendor_derived() -> bool:
    """True when artifact_ref must be vendor-derived (stamped from worktree SHA)."""
    return os.environ.get(ARTIFACT_REF_VENDOR_DERIVED_FLAG, "").strip().lower() in _TRUTHY


def _read_worktree_head_sha() -> Optional[str]:
    """Read the current HEAD commit SHA from the worktree.

    Returns the 40-char SHA, or None if git is unavailable or not a git repo.
    This is the vendor-derived artifact_ref: after the vendor runs, the
    worktree's HEAD is the increment the vendor produced (or the base commit
    if the vendor didn't commit — which correctly yields no qualifying
    increment per crit-4 (d)).
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if len(sha) == 40:
                return sha
    except Exception:
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
    model: str             # underlying model family: "gemini" | "glm"
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
        models=("gemini-3.1-pro-high",),
        model_flag="--model",
    ),
    # devin → GLM. Prompt delivered via a private 0600 temp file whose path is
    # substituted for {prompt_file}. REAL-CLI VERIFIED (2026-07-09): `devin -p --`
    # (stdin, the old template) drops into REPL mode and PANICS (rc=101,
    # 'Option::unwrap() on None' in chisel/src/repl_mode.rs) — devin does NOT read
    # the prompt from stdin. `devin -p --prompt-file <FILE>` returns rc=0 and the
    # real answer, identity-safe (prompt in a file, not argv/stdin).
    "devin": VendorSpec(
        vendor="devin",
        model="glm",
        binary="devin",
        sender="devin",
        to_default="cross_vendor",
        engram_tags=("vendor:glm", "surface:devin"),
        argv_template=("devin", "-p", "--prompt-file", "{prompt_file}"),
        read_flags=(),
        write_flags=("--permission-mode", "dangerous"),
        default_model="glm-5.2",
        models=("glm-5.2", "swe-1.7"),
        model_flag="--model",
    ),
    # devin-swe → SWE-1.7 model on devin CLI. Same binary, different model.
    # Free tier alongside glm-5.2. Used for SWE-bench-style coding tasks.
    "devin-swe": VendorSpec(
        vendor="devin-swe",
        model="swe",
        binary="devin",
        sender="devin-swe",
        to_default="cross_vendor",
        engram_tags=("vendor:swe", "surface:devin"),
        argv_template=("devin", "-p", "--prompt-file", "{prompt_file}"),
        read_flags=(),
        write_flags=("--permission-mode", "dangerous"),
        default_model="swe-1.7",
        models=("swe-1.7",),
        model_flag="--model",
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
class VendorResult:
    """Outcome of one non-interactive vendor CLI invocation."""

    vendor: str
    model: str
    rc: Optional[int]
    status: str           # ok | empty_output | error | timed_out | not_found | budget_rejected
    result: str
    duration: float
    model_id: str = ""            # resolved SELECTABLE id (e.g. "glm-5.2")
    redacted: int = 0             # count of secret redactions applied to result

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
    vs ``error``. An rc=0 run with blank output is ``empty_output`` — the silent
    no-op signal this module surfaces explicitly instead of mislabeling ``ok``."""
    if returncode != 0:
        return "error"
    return "ok" if (output and output.strip()) else "empty_output"


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
        timeout_s: int = 300,
        budget_usd: float = 0.0,
        model: Optional[str] = None,
        mode: str = DEFAULT_MODE,
    ) -> None:
        if vendor not in VENDOR_SPECS:
            raise ValueError(
                f"unknown vendor {vendor!r}; expected one of {sorted(VENDOR_SPECS)}"
            )
        self.spec = VENDOR_SPECS[vendor]
        self.vendor = vendor
        self.prompt = prompt or ""
        # A timeout of 0 means NO timeout — let the agent run as long as it needs.
        # A timeout of at least 1s — the hard bound is the Python subprocess
        # timeout, independent of any CLI-internal --print-timeout.
        self.timeout_s = 0 if timeout_s == 0 else max(1, int(timeout_s))
        self.budget_usd = float(budget_usd)
        self.mode = normalize_mode(mode)          # raises on bad mode
        self.model = resolve_model(vendor, model) # raises on bad/cross-wired model

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

    def run(self) -> VendorResult:
        if not self._budget_ok():
            return VendorResult(
                self.vendor, self.spec.model, None, "budget_rejected",
                f"negative budget_usd={self.budget_usd}", 0.0,
                model_id=self.model,
            )

        binary = shutil.which(self.spec.binary)
        if binary is None:
            return VendorResult(
                self.vendor, self.spec.model, None, "not_found",
                f"vendor CLI {self.spec.binary!r} not found on PATH", 0.0,
                model_id=self.model,
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

            proc = subprocess.run(
                argv,
                input=stdin_input,          # IDENTITY-SAFE: stdin (or None in prompt-file/inline-argv mode)
                capture_output=True,
                text=True,
                timeout=None if self.timeout_s == 0 else self.timeout_s,  # 0 = no timeout
                check=False,
            )
            duration = time.perf_counter() - start
            out = _as_text(proc.stdout)
            err = _as_text(proc.stderr)
            if proc.returncode != 0 and err:
                out = (out + "\n" + err).strip() if out else err.strip()
            out, nredacted = _redact_secrets(out)   # secret-hygiene backstop
            status = _classify_completed(proc.returncode, out)
            return VendorResult(
                self.vendor, self.spec.model, proc.returncode, status, out, duration,
                model_id=self.model, redacted=nredacted,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start
            # subprocess.run has already killed and reaped the child; salvage any
            # partial output it managed to emit before the kill.
            partial = _as_text(exc.stdout) or _as_text(exc.stderr)
            partial, npredacted = _redact_secrets(partial)   # secret-hygiene backstop
            logger.warning(
                "vendor %s timed out after %.1fs (hard kill); partial=%d bytes",
                self.vendor, duration, len(partial),
            )
            return VendorResult(
                self.vendor, self.spec.model, None, "timed_out", partial, duration,
                model_id=self.model, redacted=npredacted,
            )
        except Exception as exc:  # noqa: BLE001 — a dispatch bug must never stall
            duration = time.perf_counter() - start
            logger.warning("vendor %s dispatch failure: %s", self.vendor, exc)
            return VendorResult(
                self.vendor, self.spec.model, None, "error",
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
    """
    body = json.dumps(
        {
            "vendor": spec.vendor,
            "model": spec.model,
            "model_id": result.model_id,
            "prompt_digest": prompt_digest,
            "result": result.result[:3000],
            "rc": result.rc,
            "status": result.status,
            "produced_output": result.produced_output,
            "redacted": result.redacted,
            "effect": effect,
            "duration": round(result.duration, 3),
            "artifact_refs": [artifact_ref],
        },
        ensure_ascii=False,
    )

    relay_res: Dict[str, Any]
    try:
        from . import relay_ops  # periphery→core, lazy (import-safety)

        relay_res = relay_ops.relay_post(
            to=to_role,
            subject=f"[cross-vendor] {spec.vendor}/{spec.model} {result.status}",
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

        tags = list(spec.engram_tags) + [
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


def dispatch_and_capture(
    vendor: str,
    prompt: str,
    artifact_ref: str,
    *,
    to_role: Optional[str] = None,
    model: Optional[str] = None,
    mode: str = DEFAULT_MODE,
    expect_paths: Optional[List[str]] = None,
    timeout_s: int = 300,
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
    result = VendorCLIExecutor(
        vendor, prompt, timeout_s=timeout_s, budget_usd=budget_usd,
        model=model, mode=canon,
    ).run()
    effect, changed_paths = "unknown", []
    if expect_paths:                                 # only when caller opted in (issue #682: was `if pre:` which fails on empty dict)
        post = _snapshot_paths(expect_paths)
        changed_paths = [p for p in expect_paths if pre.get(p) != post.get(p)]
        effect = "files_touched" if changed_paths else "no_files_touched"

    # v3: when vendor-derived mode is ON, stamp artifact_ref from the
    # worktree's git HEAD SHA — NOT from caller input. The caller's
    # artifact_ref is ignored. If git is unavailable, the capture fails
    # closed (no artifact_ref = no qualifying increment).
    if _artifact_ref_vendor_derived():
        stamped_sha = _read_worktree_head_sha()
        if stamped_sha:
            artifact_ref = stamped_sha
            logger.info("artifact_ref vendor-derived: %s", stamped_sha[:12])
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
            return out

    digest = _prompt_digest(prompt)
    capture = _capture(spec, result, digest, artifact_ref, to_role,
                       force_fs=force_fs, effect=effect)

    out = result.to_dict()
    out.update({
        "prompt_digest": digest, "artifact_ref": artifact_ref, "to": to_role,
        "mode": canon, "effect": effect, "changed_paths": changed_paths,
        "capture": capture,
    })
    if _artifact_ref_vendor_derived():
        out["artifact_ref_source"] = "vendor_derived"
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
    timeout_s: int = 300,
    budget_usd: float = 0.0,
) -> tuple[int, Dict[str, Any]]:
    """Backing logic for ``nucleus dispatch`` — returns ``(exit_code, payload)``.

    Flag gate lives here so the guarantee "flag OFF ⇒ no invocation" is a single
    testable seam. Exit codes:
      * 2 — usage / flag OFF (executor never invoked)
      * 3 — capture rejected (STRICT gate) or relay failed
      * 1 — vendor errored / timed out / empty_output / no_files_touched
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
    if not artifact_ref:
        return 2, {
            "error": "no_artifact_ref",
            "message": "--artifact-ref is required (commit SHA / PR# / file path)",
        }

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
    timeout_s: int = 300,
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
    "dispatch_cli",
    "run_swarm_vendor_persona",
    "normalize_mode",
    "resolve_model",
    "VENDOR_MODES",
    "DEFAULT_MODE",
]
