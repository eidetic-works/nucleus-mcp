"""Declarative registry of scheduled work, keyed on the artifact that proves it ran.

WHY THIS EXISTS. Scheduled automation spans repos in different languages —
Python cron, launchd agents, JS Cloudflare Workers, Next.js cron routes. No
shared *library* can span them. What every one of them has in common is
narrower and more useful: each is scheduled, each produces an artifact, and
each can stop producing it silently.

WHAT IT ADDS OVER AUTO-DISCOVERY. ``nucleus alive`` can enumerate launchd and
crontab entries, but it cannot infer WHICH FILE proves a job did its job. That
gap is why a live run reports ``Healthy: 0`` — :func:`classify_liveness_item`
only returns HEALTHY when ``last_run`` is set, and nothing sets it. The
registry's ``proof`` field is precisely that missing input: name the artifact,
and freshness becomes computable.

Measured on this machine, all invisible before this existed: a cron scheduled
every 2 hours whose output directory had not changed in ~102 days; a daily
video pipeline logging "9 ok, 4 failed" that produced zero .mp4 files while an
hourly uploader retried a file that was never created; 10 launchd jobs at
non-zero exit.

THIS IS A REGISTRY, NOT A SCHEDULER. Nothing here executes, schedules,
retries, or migrates anyone's code. It declares what *should* be producing
what, so the gap between claim and artifact becomes visible.

Secrets: crontab carries ``KEY=value`` environment lines with live
credentials. No environment-assignment value is ever copied into a registry
entry or any output. A key has already been leaked publicly and auto-revoked
once; that is not repeated here.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.growth_registry")

REGISTRY_FILENAME = "growth_registry.yaml"

# Interval shorthand accepted in `schedule` when the job is not cron/launchd.
_INTERVAL_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhdw])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

# An entry is considered dead when its proof artifact is older than
# interval * this. Generous on purpose: a false "dead" trains people to ignore
# the report, which costs more than a late detection.
DEFAULT_MAX_AGE_MULTIPLIER = 3.0

# Environment-assignment lines in crontab. Never parsed as jobs, never echoed.
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*=")

# Locations the OS clears, so ABSENCE THERE PROVES NOTHING. A job logging to
# /tmp whose log is missing may have run perfectly and been wiped at reboot.
# Calling that DEAD is a false accusation; the honest verdict is that the job
# is unobservable by construction — which is itself worth reporting, because a
# job you can never verify is a job you will never notice dying. Three of five
# apparent deaths on this machine were exactly this.
_EPHEMERAL_PREFIXES = ("/tmp/", "/private/tmp/", "/var/tmp/", "/var/folders/")


def is_ephemeral_proof(proof: str) -> bool:
    """True when the proof target lives somewhere the OS periodically clears."""
    if not proof:
        return False
    expanded = os.path.expanduser(proof)
    return any(expanded.startswith(pfx) for pfx in _EPHEMERAL_PREFIXES)


@dataclass
class RegistryEntry:
    """One declared unit of scheduled work and the artifact that proves it ran."""

    id: str
    product: str = ""
    what: str = ""
    schedule: str = ""
    proof: str = ""
    max_age_seconds: Optional[float] = None
    owner: str = ""
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegistryLoad:
    """Result of loading a registry: what parsed, and what did not and why.

    Errors are RETURNED, not raised. One malformed entry must never cost you
    the rest of the file — and it must never be silent either, which is the
    failure this whole module family exists to prevent.
    """

    entries: List[RegistryEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    path: str = ""


def registry_path(brain_path: Optional[Path] = None) -> Path:
    """Resolve the registry file path."""
    if brain_path is None:
        try:
            from .common import get_brain_path

            resolved = get_brain_path()
            brain_path = Path(resolved) if resolved else Path.cwd() / ".brain"
        except Exception:  # noqa: BLE001
            brain_path = Path.cwd() / ".brain"
    return Path(brain_path) / REGISTRY_FILENAME


def parse_interval(text: str) -> Optional[float]:
    """Seconds for a shorthand interval like ``30m``/``2h``/``1d``. None if unparseable.

    Returning None rather than guessing is deliberate: an invented interval
    produces confident wrong staleness verdicts, which is worse than admitting
    the schedule is not understood.
    """
    if not text:
        return None
    m = _INTERVAL_RE.match(text)
    if not m:
        return None
    return float(m.group(1)) * _UNIT_SECONDS[m.group(2).lower()]


def _entry_from_dict(raw: Dict[str, Any], idx: int) -> Tuple[Optional[RegistryEntry], Optional[str]]:
    """Validate one raw mapping. Returns (entry, error) — exactly one is None."""
    if not isinstance(raw, dict):
        return None, f"entry #{idx}: not a mapping ({type(raw).__name__})"
    ident = str(raw.get("id") or "").strip()
    if not ident:
        return None, f"entry #{idx}: missing required field 'id'"

    max_age = raw.get("max_age_seconds")
    if max_age is None and raw.get("max_age"):
        max_age = parse_interval(str(raw.get("max_age")))
    if max_age is None:
        # Derive from the schedule when it is a plain interval; leave None for
        # cron/launchd forms so the caller can fall back to its own parser
        # rather than this module guessing at cron semantics.
        derived = parse_interval(str(raw.get("schedule") or ""))
        if derived:
            max_age = derived * DEFAULT_MAX_AGE_MULTIPLIER

    try:
        return RegistryEntry(
            id=ident,
            product=str(raw.get("product") or ""),
            what=str(raw.get("what") or ""),
            schedule=str(raw.get("schedule") or ""),
            proof=str(raw.get("proof") or ""),
            max_age_seconds=float(max_age) if max_age is not None else None,
            owner=str(raw.get("owner") or ""),
            enabled=bool(raw.get("enabled", True)),
        ), None
    except Exception as exc:  # noqa: BLE001
        return None, f"entry #{idx} ({ident}): {exc}"


def load_registry(path: Optional[Path] = None,
                  brain_path: Optional[Path] = None) -> RegistryLoad:
    """Load and validate the registry. Never raises."""
    p = path or registry_path(brain_path)
    out = RegistryLoad(path=str(p))
    if not p.exists():
        out.errors.append(f"no registry at {p}")
        return out
    try:
        import yaml
    except ImportError:
        out.errors.append("PyYAML not installed")
        return out
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        out.errors.append(f"unparseable registry: {exc}")
        return out

    raw_entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(raw_entries, list):
        out.errors.append("registry has no top-level 'entries' list")
        return out

    seen: set = set()
    for i, raw in enumerate(raw_entries):
        entry, err = _entry_from_dict(raw, i)
        if err:
            out.errors.append(err)
            continue
        if entry.id in seen:
            out.errors.append(f"entry #{i}: duplicate id '{entry.id}' — skipped")
            continue
        seen.add(entry.id)
        out.entries.append(entry)
    return out


def resolve_proof(proof: str, repo_root: Optional[Path] = None) -> Tuple[Optional[datetime], str]:
    """Newest mtime behind a proof spec: a file, a glob, or a directory.

    Returns ``(mtime_or_None, description)``. None means the artifact does not
    exist — which is a real finding (the job produced nothing), distinct from
    an empty ``proof`` field, which means nothing was ever declared.
    """
    if not proof:
        return None, "no proof declared"
    base = repo_root or Path.cwd()
    raw = os.path.expanduser(proof)
    p = Path(raw)
    if not p.is_absolute():
        p = base / p

    try:
        if any(ch in proof for ch in "*?["):
            matches = sorted(Path(p.anchor or base).glob(
                str(p.relative_to(p.anchor)) if p.is_absolute() else str(Path(raw))),
                key=lambda f: f.stat().st_mtime, reverse=True)
            matches = [m for m in matches if m.is_file()]
            if not matches:
                return None, f"glob matched nothing: {proof}"
            newest = matches[0]
            return (datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc),
                    f"newest of {len(matches)} match(es): {newest.name}")
        if p.is_dir():
            children = [c for c in p.rglob("*") if c.is_file()]
            if not children:
                return None, f"directory empty: {proof}"
            newest = max(children, key=lambda f: f.stat().st_mtime)
            return (datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc),
                    f"newest file in dir: {newest.name}")
        if p.exists():
            return (datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc),
                    f"file: {p.name}")
        return None, f"artifact missing: {proof}"
    except Exception as exc:  # noqa: BLE001
        return None, f"proof unresolvable ({proof}): {exc}"


def entry_to_liveness_item(entry: RegistryEntry,
                           repo_root: Optional[Path] = None):
    """Build a LivenessItem whose ``last_run`` comes from the proof artifact.

    This is the whole point of the registry. ``classify_liveness_item`` returns
    HEALTHY only when ``last_run`` is set, and auto-discovery cannot set it —
    which is why a live ``nucleus alive`` run reports ``Healthy: 0`` over 86
    jobs. Naming the artifact turns freshness into something computable.
    """
    from .liveness import LivenessItem, LivenessSource, LivenessStatus

    mtime, detail = resolve_proof(entry.proof, repo_root)
    interval = parse_interval(entry.schedule)
    if interval is None and entry.max_age_seconds:
        interval = entry.max_age_seconds / DEFAULT_MAX_AGE_MULTIPLIER

    # A declared-but-missing artifact is a FINDING, not ignorance. Set DEAD
    # explicitly so it cannot be read as "we could not tell" — the distinction
    # that kept a 102-day-dead cron looking merely UNKNOWN.
    status = LivenessStatus.UNKNOWN
    if entry.proof and mtime is None:
        # DEAD only when absence is INFORMATIVE. Under an ephemeral path the
        # artifact may have been wiped rather than never written, so the honest
        # answer is that we cannot tell — and the reason is recorded so the
        # unverifiable job is still visible as a problem to fix.
        if is_ephemeral_proof(entry.proof):
            status = LivenessStatus.UNKNOWN
            detail = (f"{detail} — proof target is under an OS-cleared path; "
                      f"absence proves nothing. Move it somewhere durable.")
        else:
            status = LivenessStatus.DEAD

    return LivenessItem(
        status=status,
        id=entry.id,
        name=entry.what or entry.id,
        source=LivenessSource.REGISTRY if hasattr(LivenessSource, "REGISTRY") else "registry",
        command=entry.proof,
        schedule=entry.schedule,
        interval_seconds=interval,
        last_run=mtime,
        enabled=entry.enabled,
        metadata={"product": entry.product, "owner": entry.owner,
                  "proof": entry.proof, "proof_detail": detail},
    )


def reconcile(discovered: List[Any], entries: List[RegistryEntry],
              repo_root: Optional[Path] = None) -> List[Any]:
    """Merge registry entries into auto-discovered items — never double-report.

    An entry whose id matches a discovered launchd label or cron id ENRICHES
    that item with its proof-derived ``last_run`` rather than appearing beside
    it as a duplicate. Entries matching nothing are appended as their own
    items, since a registry may legitimately describe work on another host.
    """
    by_id = {getattr(d, "id", None): d for d in discovered}
    out = list(discovered)
    for e in entries:
        mtime, detail = resolve_proof(e.proof, repo_root)
        existing = by_id.get(e.id)
        if existing is not None:
            # Registry supplies what discovery could not: the proof artifact.
            if mtime is not None:
                existing.last_run = mtime
            elif e.proof and not is_ephemeral_proof(e.proof):
                # Declared a proof, artifact absent, path durable: a real death.
                from .liveness import LivenessStatus as _LS
                existing.status = _LS.DEAD
            if e.max_age_seconds and not existing.interval_seconds:
                existing.interval_seconds = e.max_age_seconds / DEFAULT_MAX_AGE_MULTIPLIER
            meta = getattr(existing, "metadata", None)
            if isinstance(meta, dict):
                meta.update({"proof": e.proof, "proof_detail": detail,
                             "registry": True, "product": e.product})
            continue
        out.append(entry_to_liveness_item(e, repo_root))
    return out


def seed_entries_from_machine() -> List[RegistryEntry]:
    """Draft registry entries from the real crontab and launchd agents.

    ``proof`` is inferred ONLY from an explicit output target — a ``>>`` redirect
    or a plist StandardOutPath. Where none exists the field is left EMPTY rather
    than guessed: an invented proof path would manufacture confident wrong
    verdicts, which is the exact failure this module guards against.

    Environment-assignment lines are skipped entirely and their values are never
    read, echoed, or persisted.
    """
    from .liveness import enumerate_cron_jobs, enumerate_launchd_jobs

    entries: List[RegistryEntry] = []
    seen: set = set()

    for item in list(enumerate_cron_jobs()) + list(enumerate_launchd_jobs()):
        ident = getattr(item, "id", "") or ""
        if not ident or ident in seen:
            continue
        if _ENV_ASSIGNMENT_RE.match(ident):
            continue  # never a job; never inspected
        seen.add(ident)

        command = getattr(item, "command", "") or ""
        proof = ""
        m = re.search(r">>?\s*([^\s|&;]+)", command)
        if m:
            proof = m.group(1)
        else:
            meta = getattr(item, "metadata", None) or {}
            proof = str(meta.get("stdout_path") or meta.get("StandardOutPath") or "")

        entries.append(RegistryEntry(
            id=ident,
            product="",
            what=(getattr(item, "name", "") or "")[:120],
            schedule=getattr(item, "schedule", "") or "",
            proof=proof,
            max_age_seconds=None,
            owner="",
            enabled=bool(getattr(item, "enabled", True)),
        ))
    return entries


def render_registry_yaml(entries: List[RegistryEntry]) -> str:
    """Serialize entries to YAML, with a TODO marker where proof is unknown."""
    lines = [
        "# Nucleus growth/automation registry.",
        "# Declares what SHOULD be running and which artifact proves it ran.",
        "# `proof` is the load-bearing field: a file, a glob, or a directory.",
        "# An empty proof means liveness is UNKNOWABLE for that entry — fill it",
        "# in rather than leaving the job silently unverifiable.",
        "# NEVER put credentials or environment values in this file.",
        "entries:",
    ]
    for e in entries:
        lines.append(f"  - id: {e.id!r}")
        if e.what:
            lines.append(f"    what: {e.what!r}")
        if e.schedule:
            lines.append(f"    schedule: {e.schedule!r}")
        if e.proof:
            lines.append(f"    proof: {e.proof!r}")
        else:
            lines.append("    proof: ''    # TODO: name the artifact that proves this ran")
        if e.product:
            lines.append(f"    product: {e.product!r}")
        if not e.enabled:
            lines.append("    enabled: false")
    return "\n".join(lines) + "\n"
