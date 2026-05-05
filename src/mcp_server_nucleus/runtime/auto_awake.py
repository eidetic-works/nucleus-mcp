"""
Nucleus Auto-Awake Daemon — Tier 1 headless proxy worker (Sub-slice B).

Background poller that watches ``.brain/relay/<bucket>/`` inbox directories
for unread ``[DIRECTIVE]`` / ``[DIRECTIVE-ON-WAKE]`` relays, dispatches the
matching per-provider CLI (e.g. ``claude -p``, ``gemini -p``) as a
fire-and-forget subprocess that receives the full relay envelope on stdin,
and dedups by relay-id to guarantee at-most-once dispatch per envelope.

Primitive-gate axes (see feedback_nucleus_primitive_gate.md):

  - any-computer: all paths are env-driven or resolved relative to the
                  loaded ``NUCLEUS_BRAIN_PATH``; zero ``/Users/*`` hardcodes.
  - any-OS:       stdlib-only (``os``, ``json``, ``time``, ``signal``,
                  ``subprocess``, ``shlex``). Signal handlers guarded so
                  non-POSIX platforms still load the module.
  - any-user:     nothing in this module references a specific developer.
  - any-agent:    the bucket → provider mapping is loaded from
                  ``runtime/providers.yaml``; the per-provider CLI is
                  configured via ``NUCLEUS_AWAKE_CMD_<PROVIDER_UPPER>``.
                  Adding a 9th agent is a YAML entry + one env var.
  - any-LLM:      the dispatched worker is the LLM; this module is
                  LLM-invariant.

Env contract (all optional; daemon degrades gracefully when unset):

  NUCLEUS_BRAIN_PATH            — root brain dir. Falls back to the nearest
                                  ``.brain/`` ancestor of this file.
  NUCLEUS_AWAKE_DEDUP_PATH      — dedup-state file; default
                                  ``<brain>/state/auto_awake_dispatched.json``.
  NUCLEUS_AWAKE_POLL_SECS       — poll interval seconds (default 30).
  NUCLEUS_AWAKE_BUCKETS         — comma-separated bucket whitelist. If
                                  unset, every prefix in providers.yaml is
                                  a candidate bucket.
  NUCLEUS_AWAKE_SUBJECT_PREFIXES
                                — comma-separated subject prefixes that
                                  trigger dispatch. Default
                                  ``[DIRECTIVE],[DIRECTIVE-ON-WAKE]``.
  NUCLEUS_AWAKE_CMD_<PROVIDER>  — shlex-split CLI invoked per provider
                                  (e.g. ``NUCLEUS_AWAKE_CMD_ANTHROPIC_CLAUDE_CODE="claude -p"``).
                                  Missing env var is a quiet skip (the
                                  relay is recorded as ``no-cli-configured``
                                  in the dedup state so subsequent polls
                                  do not re-scan it).

Dispatch semantics: ``Popen`` with ``stdin=PIPE``; the relay envelope JSON
is piped on stdin, the pipe is closed immediately, and the daemon does NOT
wait on the worker. ``SIGCHLD`` is set to ``SIG_IGN`` on POSIX to auto-reap
zombies.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_DEFAULT_POLL_SECS = 30
_DEFAULT_SUBJECT_PREFIXES: Tuple[str, ...] = ("[DIRECTIVE]", "[DIRECTIVE-ON-WAKE]")
_ENV_BRAIN_PATH = "NUCLEUS_BRAIN_PATH"
_ENV_DEDUP_PATH = "NUCLEUS_AWAKE_DEDUP_PATH"
_ENV_POLL_SECS = "NUCLEUS_AWAKE_POLL_SECS"
_ENV_BUCKETS = "NUCLEUS_AWAKE_BUCKETS"
_ENV_SUBJECT_PREFIXES = "NUCLEUS_AWAKE_SUBJECT_PREFIXES"
_ENV_CMD_PREFIX = "NUCLEUS_AWAKE_CMD_"


class _Stop(Exception):
    """Raised by the signal handler to break the poll loop cleanly."""


# -----------------------------------------------------------------------------
# Env + path resolution
# -----------------------------------------------------------------------------


def _resolve_brain_path(explicit: Optional[Path] = None) -> Path:
    """Resolve ``<brain>``. Explicit arg > env var > ``.brain/`` ancestor."""
    if explicit is not None:
        return Path(explicit).resolve()
    env = os.environ.get(_ENV_BRAIN_PATH)
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".brain"
        if candidate.exists():
            return candidate.resolve()
    raise RuntimeError(
        f"{_ENV_BRAIN_PATH} not set and no .brain/ found above {__file__}"
    )


def _dedup_path(brain: Path) -> Path:
    override = os.environ.get(_ENV_DEDUP_PATH)
    if override:
        return Path(override).resolve()
    return brain / "state" / "auto_awake_dispatched.json"


def _subject_prefixes() -> Tuple[str, ...]:
    env = os.environ.get(_ENV_SUBJECT_PREFIXES)
    if not env:
        return _DEFAULT_SUBJECT_PREFIXES
    return tuple(p.strip() for p in env.split(",") if p.strip())


def _provider_env_key(provider: str) -> str:
    """Translate a provider token into its env-var key."""
    safe = "".join(c.upper() if c.isalnum() else "_" for c in provider)
    return f"{_ENV_CMD_PREFIX}{safe}"


def _command_for_provider(provider: str) -> Optional[List[str]]:
    raw = os.environ.get(_provider_env_key(provider))
    if not raw:
        return None
    return shlex.split(raw)


def _bucket_whitelist() -> Optional[Tuple[str, ...]]:
    env = os.environ.get(_ENV_BUCKETS)
    if not env:
        return None
    return tuple(b.strip() for b in env.split(",") if b.strip())


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


# -----------------------------------------------------------------------------
# Provider bucket map (Slice #3 config-registry, PR #138)
# -----------------------------------------------------------------------------


def _load_provider_bucket_map() -> Dict[str, str]:
    """
    Map bucket_name → provider using the Nucleus provider registry.

    The bucket name is the legacy ``agent_id`` prefix (e.g.
    ``claude_code_peer``) because that's what ``relay_ops._get_relay_dir``
    writes under. When multiple prefixes resolve to the same provider, the
    first YAML entry wins (matches ``coerce`` ordering semantics).
    """
    from mcp_server_nucleus.runtime.providers import list_providers

    mapping: Dict[str, str] = {}
    for entry in list_providers():
        bucket = entry["prefix"]
        if bucket not in mapping:
            mapping[bucket] = entry["provider"]
    return mapping


# -----------------------------------------------------------------------------
# Dedup state (atomic tmp+replace)
# -----------------------------------------------------------------------------


def _read_dedup(path: Path) -> Dict[str, Dict[str, object]]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_dedup(path: Path, state: Dict[str, Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


# -----------------------------------------------------------------------------
# Scan + dispatch
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Pending:
    bucket: str
    provider: str
    relay_path: Path
    envelope: Dict[str, object]


def _matches_prefix(subject: str, prefixes: Iterable[str]) -> bool:
    if not subject:
        return False
    return any(subject.startswith(p) for p in prefixes)


def _scan_bucket(
    bucket_dir: Path,
    prefixes: Iterable[str],
    dispatched: Dict[str, Dict[str, object]],
) -> List[Tuple[Path, Dict[str, object]]]:
    if not bucket_dir.exists():
        return []
    hits: List[Tuple[Path, Dict[str, object]]] = []
    for path in sorted(bucket_dir.glob("*.json")):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(envelope, dict):
            continue
        relay_id = str(envelope.get("id") or path.stem)
        if relay_id in dispatched:
            continue
        if not _matches_prefix(str(envelope.get("subject", "")), prefixes):
            continue
        hits.append((path, envelope))
    return hits


def _dispatch(
    cmd: List[str],
    envelope: Dict[str, object],
    *,
    cwd: Optional[Path] = None,
) -> subprocess.Popen:
    """Fire-and-forget Popen with envelope JSON piped on stdin."""
    kwargs: Dict[str, object] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "cwd": str(cwd) if cwd else None,
    }
    if os.name == "posix":
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)  # type: ignore[arg-type]
    try:
        if proc.stdin is not None:
            proc.stdin.write(json.dumps(envelope).encode("utf-8"))
            proc.stdin.close()
    except BrokenPipeError:
        pass
    return proc


# -----------------------------------------------------------------------------
# Poll loop
# -----------------------------------------------------------------------------


def _resolve_bucket_targets(
    brain: Path,
    provider_map: Dict[str, str],
    whitelist: Optional[Tuple[str, ...]],
) -> List[Tuple[str, str, Path]]:
    """Return ``[(bucket, provider, dir)]`` for buckets we're allowed to scan."""
    relay_root = brain / "relay"
    targets: List[Tuple[str, str, Path]] = []
    for bucket, provider in provider_map.items():
        if whitelist and bucket not in whitelist:
            continue
        targets.append((bucket, provider, relay_root / bucket))
    return targets


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _poll_once(
    brain: Path,
    targets: List[Tuple[str, str, Path]],
    prefixes: Tuple[str, ...],
    dedup_file: Path,
) -> int:
    """One poll pass. Returns the count of dispatched envelopes."""
    dispatched = _read_dedup(dedup_file)
    fired = 0
    for bucket, provider, bucket_dir in targets:
        pending = _scan_bucket(bucket_dir, prefixes, dispatched)
        if not pending:
            continue
        cmd = _command_for_provider(provider)
        if cmd is None:
            for path, envelope in pending:
                relay_id = str(envelope.get("id") or path.stem)
                dispatched[relay_id] = {
                    "bucket": bucket,
                    "provider": provider,
                    "relay_path": str(path),
                    "skipped": "no-cli-configured",
                    "dispatched_at": _now_iso(),
                }
            continue
        for path, envelope in pending:
            relay_id = str(envelope.get("id") or path.stem)
            proc = _dispatch(cmd, envelope, cwd=brain.parent)
            dispatched[relay_id] = {
                "bucket": bucket,
                "provider": provider,
                "relay_path": str(path),
                "pid": proc.pid,
                "dispatched_at": _now_iso(),
            }
            fired += 1
    _write_dedup(dedup_file, dispatched)
    return fired


def _install_signal_handlers() -> None:
    def _stop_handler(signum, frame):  # noqa: ARG001
        raise _Stop()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _stop_handler)
        except (ValueError, OSError):
            pass

    sigchld = getattr(signal, "SIGCHLD", None)
    if sigchld is not None:
        try:
            signal.signal(sigchld, signal.SIG_IGN)
        except (ValueError, OSError):
            pass


def run(
    brain: Optional[Path] = None,
    *,
    poll_secs: Optional[float] = None,
    max_iters: Optional[int] = None,
) -> int:
    """Main poll loop. Returns the total count of envelopes dispatched."""
    brain_path = _resolve_brain_path(brain)
    provider_map = _load_provider_bucket_map()
    whitelist = _bucket_whitelist()
    targets = _resolve_bucket_targets(brain_path, provider_map, whitelist)
    prefixes = _subject_prefixes()
    dedup_file = _dedup_path(brain_path)
    interval = (
        poll_secs
        if poll_secs is not None
        else _env_float(_ENV_POLL_SECS, _DEFAULT_POLL_SECS)
    )

    _install_signal_handlers()

    total = 0
    iters = 0
    try:
        while True:
            total += _poll_once(brain_path, targets, prefixes, dedup_file)
            iters += 1
            if max_iters is not None and iters >= max_iters:
                break
            time.sleep(max(0.0, interval))
    except _Stop:
        pass
    return total


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="auto-awake",
        description="Nucleus auto-awake daemon (Tier 1 headless proxy).",
    )
    parser.add_argument("--brain", type=Path, default=None)
    parser.add_argument("--poll-secs", type=float, default=None)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll pass and exit.",
    )
    args = parser.parse_args(argv)
    fired = run(
        brain=args.brain,
        poll_secs=args.poll_secs,
        max_iters=1 if args.once else None,
    )
    print(f"auto-awake dispatched={fired}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
