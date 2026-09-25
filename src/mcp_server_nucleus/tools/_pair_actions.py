"""MCP action handlers for L3 Sonnet pair daemon — Nucleus-Delegate v0.1 facade.

Exposes pair lifecycle + audit as `nucleus_sync` actions:
  pair_register(lane, charter_path?)       — start the lane's daemon
  pair_status(lane?)                        — read PID + last heartbeat + busy%
  pair_stop(lane)                           — graceful shutdown
  pair_fire(lane, brief, model?, subject?)  — relay a [DELEGATE] to the pair
  audit_pair(window_hours?)                 — cost rollup (proxy_tokens + busy%)

Compound-before-build: every handler reuses existing primitives.

  pair_register / pair_stop  → invoke `scripts/start_sonnet_pair.sh`
                               and `scripts/stop_sonnet_pair.sh` as subprocesses.
  pair_status                → reads `.brain/daemon/sonnet_pair_<lane>.pid`,
                               `.session_id`, plus latest `pair_heartbeat`
                               event from `.brain/ledger/events.jsonl`.
  pair_fire                  → wraps `runtime.relay_ops.relay_post`, posting to
                               the `sonnet_<lane>` bucket with `[DELEGATE:<model>]`
                               subject prefix the daemon already parses.
  audit_pair                 → imports `summarize_by_pair` +
                               `summarize_pair_utilization` from
                               `scripts/audit_token_cost.py`.

Net new logic is plumbing only.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Discover repo root once. The MCP server runs at the repo root by convention.
_REPO_ROOT = Path.cwd()


def _brain_dir() -> Path:
    return _REPO_ROOT / ".brain"


def _daemon_dir() -> Path:
    return _brain_dir() / "daemon"


def _scripts_dir() -> Path:
    return _REPO_ROOT / "scripts"


def _events_path() -> Path:
    return _brain_dir() / "ledger" / "events.jsonl"


def _ok(data: Dict[str, Any]) -> str:
    return json.dumps({"ok": True, "data": data}, indent=2, default=str)


def _err(code: str, message: str, **extra: Any) -> str:
    payload = {"ok": False, "error": {"code": code, "message": message}, **extra}
    return json.dumps(payload, indent=2, default=str)


# ─── A8 daemon-health anchor (HANDOFF_BACKLOG.md §A8 / ADJACENCY_THEOREM.md) ──
#
# Hole: pair_status's liveness check was a bare `os.kill(pid, 0)` against a
# self-written `.pid` file, and audit_pair's >=40% utilization gate trusted
# the latest self-emitted `pair_heartbeat` event verbatim. Both are
# claimant-authority state (Regime-2 per ADJACENCY_THEOREM.md): `echo $$ >
# .brain/daemon/sonnet_pair_<lane>.pid` plus one fabricated `pair_heartbeat`
# line appended to events.jsonl satisfies both checks without the daemon
# ever having run.
#
# Fix (flag-gated on NUCLEUS_DAEMON_HEALTH_ANCHOR, default OFF): pair_register
# — the ONLY legitimate launch path — captures the newly-spawned process's
# kernel create_time immediately after the subprocess launcher reports
# success, and persists it to a companion `.create_time` file the daemon
# itself never writes (the "journal the daemon can't hand-write" from the
# backlog row). pair_status / audit_pair then require the *live* create_time
# of the claimed pid to match that spawn-time witness before treating the
# lane as alive or letting it clear the utilization gate. A forger who only
# replays the historical `echo $$ > x.pid` + fake-heartbeat exploit (without
# also independently fabricating a matching witness file) fails both checks.
#
# Residual (documented, not claimed fixed): this is a same-uid kernel-oracle
# cross-check, not the off-uid attester in HANDOFF_BACKLOG.md §B. An
# adaptive same-uid attacker who also reproduces the witness file (e.g. by
# probing their own forged pid's real create_time and writing it) is not
# defeated — that residue is exactly what item B is for.


def _daemon_health_anchor_enabled() -> bool:
    return os.environ.get("NUCLEUS_DAEMON_HEALTH_ANCHOR", "").strip().lower() in (
        "1", "true", "on", "yes",
    )


def _pid_create_time(pid: int) -> Optional[str]:
    """Kernel process-start timestamp for `pid`. None on any failure (fail-open probe).

    Prefers `psutil` (matching the sessions-identity anchor's create_time
    technique per HANDOFF_BACKLOG.md §A8) but psutil is not a pinned
    dependency of this package (see pyproject.toml) and is not guaranteed to
    be importable — falls back to the same POSIX `ps -p <pid> -o lstart=`
    shim `sessions/registry.py`'s identity-anchor (feat/anchor-sessions-
    identity) uses for the identical purpose, so the witness is stable
    across a given host regardless of which path is taken.
    """
    try:
        import psutil  # type: ignore

        return repr(psutil.Process(pid).create_time())
    except ImportError:
        pass
    except Exception:
        logger.debug("Swallowed exception in _pid_create_time", exc_info=True)
        return None
    try:
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True, text=True, timeout=2,
        )
        val = proc.stdout.strip()
        return val or None
    except Exception:
        logger.debug("Swallowed exception in _pid_create_time", exc_info=True)
        return None


def _create_time_witness_path(lane: str) -> Path:
    return _daemon_dir() / f"sonnet_pair_{lane}.create_time"


def _write_create_time_witness(lane: str, pid: int) -> Optional[str]:
    """Server-captured spawn witness: probe the OS process table for `pid`'s
    create_time immediately after pair_register observes a successful
    launch, and persist it next to the `.pid` file. Only pair_register calls
    this — the daemon process never writes its own witness.
    """
    ct = _pid_create_time(pid)
    if ct is None:
        return None
    try:
        _create_time_witness_path(lane).write_text(ct)
    except OSError:
        return None
    return ct


def _anchor_verify_alive(lane: str, pid: Optional[int]) -> bool:
    """True iff `pid` is alive AND its live create_time matches the
    spawn-time witness pair_register recorded for `lane`. Fails closed on
    any missing/mismatched/unreadable state.
    """
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    witness_path = _create_time_witness_path(lane)
    if not witness_path.exists():
        return False  # no spawn-time witness recorded — fail closed
    try:
        stored_ct = witness_path.read_text().strip()
    except OSError:
        return False
    if not stored_ct:
        return False
    live_ct = _pid_create_time(pid)
    if live_ct is None:
        return False  # kernel oracle unreachable right now — fail closed
    return live_ct == stored_ct


# ─── pair_register ────────────────────────────────────────────────────────


def pair_register(lane: str, charter_path: Optional[str] = None) -> str:
    """Start the L3 sonnet pair daemon for `lane`. Idempotent — refuses if a
    daemon is already running for that lane (caller should pair_stop first).

    Reuses `scripts/start_sonnet_pair.sh` for the actual subprocess launch so
    daemon lifecycle stays in one place. `charter_path` is informational here;
    the launcher script picks the canonical charter from `docs/org/charters/`
    based on lane.
    """
    if lane not in ("peer", "main"):
        return _err("INVALID_LANE", f"v0.1 supports lane=peer|main only; got {lane!r}")

    script = _scripts_dir() / "start_sonnet_pair.sh"
    if not script.exists():
        return _err("LAUNCHER_MISSING", f"expected {script}")

    pid_file = _daemon_dir() / f"sonnet_pair_{lane}.pid"
    if pid_file.exists():
        try:
            existing = int(pid_file.read_text().strip())
            os.kill(existing, 0)  # signal 0 = liveness probe
            return _err("ALREADY_RUNNING",
                        f"daemon for lane {lane} already running",
                        pid=existing)
        except (OSError, ValueError):
            pass  # stale pid file; launcher will clean up

    proc = subprocess.run(
        ["bash", str(script), lane],
        capture_output=True, text=True, timeout=30,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        return _err("LAUNCH_FAILED",
                    f"launcher exit code {proc.returncode}",
                    stderr=proc.stderr[:1000], stdout=proc.stdout[:1000])

    new_pid: Optional[int] = None
    try:
        new_pid = int(pid_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        pass

    sid_file = _daemon_dir() / f"sonnet_pair_{lane}.session_id"
    session_id = sid_file.read_text().strip() if sid_file.exists() else None

    result = {
        "lane": lane,
        "pid": new_pid,
        "session_id": session_id,
        "charter_path": charter_path or str(
            _REPO_ROOT / "docs" / "org" / "charters" / f"sonnet_pair_{lane}.md"
        ),
        "started": True,
    }
    if _daemon_health_anchor_enabled() and new_pid is not None:
        witness = _write_create_time_witness(lane, new_pid)
        result["create_time_witness_recorded"] = witness is not None

    return _ok(result)


# ─── pair_stop ────────────────────────────────────────────────────────────


def pair_stop(lane: str) -> str:
    """Graceful shutdown of the lane's daemon via SIGTERM."""
    if lane not in ("peer", "main"):
        return _err("INVALID_LANE", f"v0.1 supports lane=peer|main only; got {lane!r}")

    script = _scripts_dir() / "stop_sonnet_pair.sh"
    if not script.exists():
        return _err("LAUNCHER_MISSING", f"expected {script}")

    proc = subprocess.run(
        ["bash", str(script), lane],
        capture_output=True, text=True, timeout=30,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        return _err("STOP_FAILED", f"stop script failed with exit code {proc.returncode}",
                     stderr=proc.stderr[:500] if proc.stderr else None)
    return _ok({
        "lane": lane,
        "stopped": True,
        "stdout": proc.stdout[:500],
        "stderr": proc.stderr[:500] if proc.stderr else None,
    })


# ─── pair_status ──────────────────────────────────────────────────────────


def _latest_heartbeat(lane: str, max_age_s: int = 600) -> Optional[Dict[str, Any]]:
    """Walk events.jsonl backwards to find the latest pair_heartbeat for lane."""
    p = _events_path()
    if not p.exists():
        return None
    cutoff_ms = int((time.time() - max_age_s) * 1000)
    try:
        with open(p, "r", encoding="utf-8") as f:
            tail = f.readlines()[-2000:]  # only walk last 2000 lines
    except Exception:
        logger.debug("Swallowed exception in _latest_heartbeat", exc_info=True)
        return None
    for raw in reversed(tail):
        raw = raw.strip()
        if not raw or "pair_heartbeat" not in raw:
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "pair_heartbeat":
            continue
        data = ev.get("data") or {}
        if data.get("lane") != lane:
            continue
        if int(data.get("now_ms") or 0) < cutoff_ms:
            return None  # last heartbeat too old
        return {
            "session_id": data.get("session_id"),
            "busy_pct_1h": data.get("busy_pct_1h"),
            "events_in_window": data.get("events_in_window"),
            "pid": data.get("pid"),
            "now_ms": data.get("now_ms"),
            "started_at_ms": data.get("started_at_ms"),
        }
    return None


def _queue_depth(lane: str) -> int:
    bucket = _brain_dir() / "relay" / f"sonnet_{lane}"
    if not bucket.exists():
        return 0
    return len([p for p in bucket.glob("*.json") if p.parent == bucket])


def pair_status(lane: Optional[str] = None) -> str:
    """Return pid + session + busy% + queue depth for one lane (or all)."""
    lanes = [lane] if lane else ["peer", "main"]
    anchor_on = _daemon_health_anchor_enabled()
    out: List[Dict[str, Any]] = []
    for ln in lanes:
        if ln not in ("peer", "main"):
            return _err("INVALID_LANE", f"unknown lane {ln!r}")
        pid_file = _daemon_dir() / f"sonnet_pair_{ln}.pid"
        sid_file = _daemon_dir() / f"sonnet_pair_{ln}.session_id"
        running = False
        pid: Optional[int] = None
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                running = True
            except (OSError, ValueError):
                running = False
        row: Dict[str, Any] = {
            "lane": ln,
            "running": running,
            "pid": pid,
            "session_id": sid_file.read_text().strip() if sid_file.exists() else None,
            "queue_depth": _queue_depth(ln),
            "latest_heartbeat": _latest_heartbeat(ln),
            "log_path": str(_daemon_dir() / f"sonnet_pair_{ln}.log"),
        }
        if anchor_on:
            # §A8: a live pid alone is not the daemon — require the pid's
            # create_time to match the spawn-time witness pair_register
            # recorded. `echo $$ > sonnet_pair_<lane>.pid` yields a real,
            # live-but-unrelated pid with no matching witness -> anchor
            # fails -> running flips False even though os.kill(pid, 0)
            # succeeded above.
            anchor_verified = _anchor_verify_alive(ln, pid) if running else False
            row["anchor_verified"] = anchor_verified
            row["running"] = running and anchor_verified
        out.append(row)
    return _ok({"pairs": out})


# ─── pair_fire ────────────────────────────────────────────────────────────


def pair_fire(lane: str, brief: str, model: str = "sonnet",
              subject: Optional[str] = None,
              parent_session_id: Optional[str] = None) -> str:
    """Post a [DELEGATE] relay to the lane's bucket. Pair daemon picks it up
    on next poll (5s). Result returns asynchronously as [DELEGATE-RESULT] in
    the parent session's bucket — caller can `relay_inbox` to retrieve.
    """
    if lane not in ("peer", "main"):
        return _err("INVALID_LANE", f"v0.1 supports lane=peer|main only; got {lane!r}")
    if model not in ("haiku", "sonnet"):
        return _err("INVALID_MODEL",
                    f"model must be haiku|sonnet; got {model!r}")
    if not brief or not brief.strip():
        return _err("EMPTY_BRIEF", "brief cannot be empty")

    # Resolve sender lane from environment (CC_SESSION_ROLE) or fall back.
    role = os.environ.get("CC_SESSION_ROLE", "main")
    sender = f"claude_code_{role}" if role in ("peer", "main", "cc_tb") else "claude_code_main"

    title = subject.strip() if subject else brief.strip().split("\n", 1)[0][:120]
    full_subject = f"[DELEGATE:{model}] {title}" if model != "sonnet" else f"[DELEGATE] {title}"

    # Reuse existing relay_post primitive.
    try:
        from mcp_server_nucleus.runtime.relay_ops import relay_post
    except ImportError as e:
        return _err("IMPORT_FAILED", f"relay_post unavailable: {e}")

    try:
        result = relay_post(
            to=f"sonnet_{lane}",
            subject=full_subject,
            body=brief,
            priority="normal",
            sender=sender,
            from_session_id=parent_session_id or os.environ.get("CC_SESSION_UUID"),
        )
    except Exception as e:
        return _err("RELAY_FAILED", str(e))

    return _ok({
        "fired_to": f"sonnet_{lane}",
        "model": model,
        "subject": full_subject,
        "message_id": result.get("message_id"),
        "status": result.get("sent"),
        "next_step": (
            f"poll relay_inbox(recipient='{sender}') after ~30-60s for [DELEGATE-RESULT]"
        ),
    })


# ─── audit_pair ───────────────────────────────────────────────────────────


def _import_audit_module():
    """Import scripts/audit_token_cost.py at runtime (script, not package)."""
    script = _REPO_ROOT / "scripts" / "audit_token_cost.py"
    if not script.exists():
        raise FileNotFoundError(str(script))
    spec_root = str(_REPO_ROOT / "scripts")
    if spec_root not in sys.path:
        sys.path.insert(0, spec_root)
    import audit_token_cost  # type: ignore
    return audit_token_cost


def audit_pair(window_hours: float = 24.0) -> str:
    """Cost-pair rollup + L3 utilization across the requested window."""
    try:
        atc = _import_audit_module()
    except FileNotFoundError as e:
        return _err("AUDIT_MODULE_MISSING", str(e))

    events_path = _events_path()
    try:
        window_hours_f = float(window_hours)
    except (TypeError, ValueError):
        return _err("INVALID_WINDOW_HOURS",
                    f"window_hours must be a number; got {window_hours!r}")
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours_f)
    events, malformed = atc.read_events(events_path, since)

    by_pair = atc.summarize_by_pair(events)
    utilization = atc.summarize_pair_utilization(events)

    pair_rows = []
    for (parent, role), s in sorted(by_pair.items()):
        pair_rows.append({
            "parent": parent,
            "role": role,
            "tier": s.get("tier"),
            "spawns": s["spawns"],
            "returns": s["returns"],
            "orphans": s["orphans"],
            "prompt_chars": s["prompt_chars"],
            "response_chars": s["response_chars"],
            "duration_ms": s["duration_ms"],
        })

    anchor_on = _daemon_health_anchor_enabled()
    util_rows = []
    for lane, u in sorted(utilization.items()):
        gate_pass = (u.get("busy_pct_1h") or 0.0) >= 40.0
        row = {
            "lane": lane,
            "session_id": u.get("session_id"),
            "busy_pct_1h": u.get("busy_pct_1h"),
            "events_in_window": u.get("events_in_window"),
            "pid": u.get("pid"),
            "gate_pass_at_40_pct": gate_pass,
        }
        if anchor_on:
            # §A8: the utilization gate must not clear on a self-reported
            # busy_pct_1h from a `pair_heartbeat` event whose `pid` isn't
            # provably the daemon pair_register actually spawned for this
            # lane — a fabricated event line otherwise passes the gate for
            # free (the historical hole this row closes).
            anchor_verified = _anchor_verify_alive(lane, u.get("pid"))
            row["anchor_verified"] = anchor_verified
            row["gate_pass_at_40_pct"] = gate_pass and anchor_verified
        util_rows.append(row)

    return _ok({
        "window_hours": window_hours,
        "events_in_window": len(events),
        "malformed_lines_skipped": malformed,
        "pair_rollup": pair_rows,
        "utilization": util_rows,
    })
