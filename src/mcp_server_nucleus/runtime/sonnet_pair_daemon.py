"""Sonnet-pair daemon (L3 always-on layer of Delegate-Down Stack).

One process per pair (peer / main). Polls `.brain/relay/sonnet_<lane>/` every
N seconds, gates inbound `[DELEGATE]` requests against the authority contract
(`.brain/plans/sonnet_pair_authority_contract.md`), spawns a Claude Code
subprocess on Sonnet for lateral-OK work, and replies via `relay_post` to the
parent Opus lane. Emits `agent_spawn` / `agent_return` / `pair_heartbeat`
events for cost-telemetry and the >=40% utilization gate.

Lifecycle: foreground process; PID written to
`.brain/daemon/sonnet_pair_<lane>.pid`. Stop via SIGTERM; idempotent shutdown.
Identity (own session UUID) generated at startup, persisted in
`.brain/daemon/sonnet_pair_<lane>.session_id`. Daemon restart = new identity
(matches charter's rotation contract).

Backend: `claude --print --append-system-prompt-file <charter>` subprocess by
default ($0 via Max sub). `SONNET_PAIR_BACKEND=sdk` reserved for future
escape-hatch; not implemented in v0.1.
"""

import asyncio
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .relay_ops import _iter_inbox_dirs, relay_post

LOG = logging.getLogger("sonnet_pair")

# ALWAYS-escalate keyword set, lifted verbatim from
# .brain/plans/sonnet_pair_authority_contract.md § "ALWAYS-escalate to Opus".
# A subject or brief that matches any of these (case-insensitive substring)
# triggers an [ESCALATE] reply WITHOUT spawning Sonnet. Anything else falls
# through the lateral-OK default.
ALWAYS_ESCALATE_KEYWORDS = (
    # Founder / sovereignty
    "founder", "sovereign", "sovereignty", "public sync", "guarded",
    # Disputes / convergence
    "dispute", "disagreement", "convergence", "2-of-3",
    # Architecture / scope
    "novel architecture", "new substrate", "new role-bucket", "new event type",
    "new policy", "scope change", "extend scope", "narrow scope",
    "decline", "refuse task",
    # Cost
    "cost-budget", "weekly burn", "budget breach",
    # Memos
    "feedback memo", "feedback-memo", "author memory", "write memory",
    "project memo", "user memo", "reference memo",
    # Irreversible writes
    "git push", "force push", "pr merge", "merge pr", "git reset",
    # Non-paired surface relays — match common verbs (relay/route/send/forward/fire) + target
    "to windsurf", "to antigravity", "to perplexity", "to gemini", "to cowork",
)


def _brain_root() -> Path:
    """Repo-relative .brain dir. Daemon assumes CWD = repo root."""
    return Path.cwd() / ".brain"


def _daemon_dir() -> Path:
    p = _brain_root() / "daemon"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _processed_dir(lane: str) -> Path:
    p = _brain_root() / "relay" / f"sonnet_{lane}" / "processed"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ensure_session_id(lane: str) -> str:
    """One UUID per daemon process lifetime. Restart = new identity."""
    f = _daemon_dir() / f"sonnet_pair_{lane}.session_id"
    sid = str(uuid.uuid4())
    f.write_text(sid)
    return sid


def _write_pid(lane: str) -> Path:
    f = _daemon_dir() / f"sonnet_pair_{lane}.pid"
    f.write_text(str(os.getpid()))
    return f


def _emit(event_type: str, emitter: str, data: Dict, description: str = "") -> None:
    """Best-effort event emission; never blocks daemon flow on failure."""
    try:
        from .event_ops import _emit_event
        _emit_event(event_type=event_type, emitter=emitter, data=data, description=description)
    except Exception as e:
        LOG.warning("event emit failed: %s", e)


def is_escalate(subject: str, body: str) -> bool:
    haystack = f"{subject}\n{body}".lower()
    return any(kw in haystack for kw in ALWAYS_ESCALATE_KEYWORDS)


def parse_envelope(path: Path) -> Optional[Dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        LOG.warning("malformed envelope %s: %s", path.name, e)
        return None


def list_pending(lane: str) -> List[Path]:
    """Unread .json files in the pair's bucket (skip processed/, acks/, dotfiles)."""
    out: List[Path] = []
    for d in _iter_inbox_dirs(f"sonnet_{lane}"):
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            if p.parent.name in ("processed", "acks") or p.name.startswith("."):
                continue
            out.append(p)
    return out


def archive(path: Path, lane: str) -> None:
    """Move source envelope into processed/ so we don't re-read it."""
    target = _processed_dir(lane) / path.name
    try:
        path.replace(target)
    except Exception as e:
        LOG.warning("archive failed %s: %s", path.name, e)


def parent_lane_for(envelope: Dict) -> str:
    """Map source surface back to the Opus principal that owns this pair."""
    sender = (envelope.get("from") or "").lower()
    if sender.startswith("claude_code_"):
        return sender
    return "claude_code_main"


def _spawn_via_claude_code(charter_path: Path, brief: str, *, timeout_s: int = 300) -> Tuple[bool, str]:
    """Run Sonnet via Claude Code subprocess. $0 via Max sub.

    Returns (success, output_or_error). NOT using --bare — that flag disables
    keychain reads and forces ANTHROPIC_API_KEY auth, breaking the
    $0-via-Max-sub assumption. The trade-off is CLAUDE.md / plugins / hooks
    load in the subprocess; the appended charter dominates behavior in practice.

    Subprocess env: ANTHROPIC_BASE_URL is explicitly stripped so the pair hits
    Anthropic directly rather than inheriting a measurement-proxy URL from the
    parent shell. Daemons that DO want proxied calls can re-set the env var on
    the parent before launching the daemon — the strip is in-subprocess only.
    """
    cmd = [
        "claude", "--print",
        "--model", "claude-sonnet-4-6",
        "--append-system-prompt-file", str(charter_path),
        "--no-session-persistence",
        brief,
    ]
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_BASE_URL"}
    LOG.info("subprocess.run claude --print (brief=%dch, charter=%s, timeout=%ds)",
             len(brief), charter_path.name, timeout_s)
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=timeout_s,
            cwd=str(Path.cwd()),
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        LOG.warning("subprocess timeout after %ds", timeout_s)
        return False, f"<timeout after {timeout_s}s>"
    except FileNotFoundError:
        return False, "<claude binary not found on PATH>"
    dt = time.time() - t0
    LOG.info("subprocess returned rc=%d in %.1fs (stdout=%dch, stderr=%dch)",
             proc.returncode, dt, len(proc.stdout), len(proc.stderr))
    if proc.returncode != 0:
        LOG.warning("claude stderr: %s", proc.stderr[:500])
        return False, f"<claude rc={proc.returncode}> stderr: {proc.stderr[:500]}"
    return True, proc.stdout.strip()


class _BusyTracker:
    """Rolling 1-hour busy% counter for pair_heartbeat telemetry."""

    def __init__(self) -> None:
        self.events: List[Tuple[float, float]] = []  # (start_unix, duration_s)

    def add(self, start_unix: float, duration_s: float) -> None:
        self.events.append((start_unix, duration_s))

    def busy_pct(self, now: Optional[float] = None, window_s: int = 3600) -> float:
        now = now if now is not None else time.time()
        cutoff = now - window_s
        self.events = [(t, d) for (t, d) in self.events if t + d >= cutoff]
        busy = sum(min(d, now - t) - max(0, cutoff - t) for (t, d) in self.events)
        busy = max(0.0, busy)
        return round(100.0 * busy / window_s, 2)


async def handle_one(envelope: Dict, lane: str, charter_path: Path,
                     pair_session_id: str, pair_sender: str,
                     busy: _BusyTracker) -> None:
    """One-message work cycle: gate, spawn, reply, telemetry."""
    subject = envelope.get("subject", "") or ""
    body_raw = envelope.get("body", "") or ""
    body_str = body_raw if isinstance(body_raw, str) else json.dumps(body_raw)
    source_id = envelope.get("id")
    parent = parent_lane_for(envelope)

    # Subject filter — only these prefixes are work for the pair.
    if not (subject.startswith("[DELEGATE]") or subject.startswith("[ESCALATE-CHECK]")):
        LOG.info("skip non-delegate subject: %s", subject[:60])
        return

    # Authority gate.
    if is_escalate(subject, body_str):
        LOG.info("ESCALATE: %s", subject[:80])
        relay_post(
            to=parent,
            subject=f"[ESCALATE] {subject.removeprefix('[DELEGATE]').removeprefix('[ESCALATE-CHECK]').strip()}",
            body=json.dumps({
                "reason": "matched authority-contract ALWAYS-escalate keyword",
                "source_id": source_id,
                "subject": subject,
            }),
            priority="high",
            sender=pair_sender,
            from_session_id=pair_session_id,
            in_reply_to=source_id,
        )
        return

    # Lateral-OK path: spawn Sonnet via Claude Code subprocess.
    spawn_id = f"spawn_{int(time.time())}_{secrets.token_hex(4)}"
    started = time.time()
    started_ms = int(started * 1000)
    _emit("agent_spawn", emitter=pair_sender, data={
        "spawn_id": spawn_id,
        "role": f"sonnet_pair_{lane}",
        "model": "claude-sonnet-4-6",
        "parent": parent,
        "session_id": pair_session_id,
        "source_relay_id": source_id,
        "brief_chars": len(body_str),
        "charter_path": str(charter_path),
        "started_at_ms": started_ms,
    }, description=f"{pair_sender} spawned sonnet_pair_{lane} for {source_id}")

    # Synthesize the brief: parent context + subject + body.
    brief = f"From: {parent}\nSubject: {subject}\n\n{body_str}"
    success, output = await asyncio.to_thread(
        _spawn_via_claude_code, charter_path, brief
    )
    duration_s = time.time() - started
    busy.add(started, duration_s)

    _emit("agent_return", emitter=pair_sender, data={
        "spawn_id": spawn_id,
        "role": f"sonnet_pair_{lane}",
        "model": "claude-sonnet-4-6",
        "parent": parent,
        "session_id": pair_session_id,
        "duration_ms": int(duration_s * 1000),
        "response_chars": len(output),
        "success": success,
        "orphan": False,
    }, description=f"agent_return for {spawn_id}")

    relay_post(
        to=parent,
        subject=f"[DELEGATE-RESULT] {subject.removeprefix('[DELEGATE]').removeprefix('[ESCALATE-CHECK]').strip()}",
        body=output if success else f"<delegation failed>\n{output}",
        priority="normal" if success else "high",
        sender=pair_sender,
        from_session_id=pair_session_id,
        in_reply_to=source_id,
    )


async def heartbeat_loop(lane: str, pair_sender: str, pair_session_id: str,
                        busy: _BusyTracker, started_at_ms: int) -> None:
    while True:
        await asyncio.sleep(30)
        _emit("pair_heartbeat", emitter=pair_sender, data={
            "lane": lane,
            "session_id": pair_session_id,
            "pid": os.getpid(),
            "busy_pct_1h": busy.busy_pct(),
            "events_in_window": len(busy.events),
            "started_at_ms": started_at_ms,
            "now_ms": int(time.time() * 1000),
        }, description=f"sonnet_pair_{lane} heartbeat")


async def poll_loop(lane: str, charter_path: Path, pair_sender: str,
                   pair_session_id: str, busy: _BusyTracker,
                   poll_interval_s: int = 5) -> None:
    while True:
        try:
            for path in list_pending(lane):
                env = parse_envelope(path)
                if env is None:
                    archive(path, lane)
                    continue
                try:
                    await handle_one(env, lane, charter_path, pair_session_id,
                                    pair_sender, busy)
                except Exception as e:
                    LOG.exception("handler failed for %s: %s", path.name, e)
                finally:
                    archive(path, lane)
        except Exception as e:
            LOG.exception("poll cycle error: %s", e)
        await asyncio.sleep(poll_interval_s)


def _ops_queue_dir() -> Path:
    """Persistent queue for OPS-HANDOFF briefs awaiting the founder's attention."""
    p = _brain_root() / "ops_queue"
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_pending_ops() -> List[Path]:
    """Unread [OPS-HANDOFF] .json files in the operator_assistant bucket."""
    out: List[Path] = []
    from .relay_ops import _get_relay_dir
    d = _get_relay_dir("claude_code_operator_assistant")
    if not d.exists():
        return out
    for p in sorted(d.glob("*.json")):
        if p.parent.name in ("processed", "acks") or p.name.startswith("."):
            continue
        out.append(p)
    return out


def _archive_ops(path: Path) -> None:
    """Move OPS-HANDOFF envelope to processed/ so it isn't re-surfaced."""
    proc = path.parent / "processed"
    proc.mkdir(exist_ok=True)
    try:
        path.replace(proc / path.name)
    except Exception as e:
        LOG.warning("archive ops failed %s: %s", path.name, e)


def _notify_macos(title: str, message: str) -> None:
    """Best-effort macOS notification. Noop on Linux/Windows (no osascript)."""
    import platform
    import shutil
    if platform.system() != "Darwin":
        return
    if not shutil.which("osascript"):
        return
    try:
        import subprocess as _sp
        _sp.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}"'],
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass


async def handle_ops_handoff(envelope: Dict, pair_session_id: str) -> None:
    """Operator-assistant lane: persist brief to ops_queue; notify; do not spawn."""
    subject = envelope.get("subject", "") or ""
    body_raw = envelope.get("body", "") or ""
    body_str = body_raw if isinstance(body_raw, str) else json.dumps(body_raw)
    source_id = envelope.get("id") or f"unknown_{int(time.time())}"
    frm = envelope.get("from") or "?"

    if not (subject.startswith("[OPS-HANDOFF]") or subject.startswith("[OPS-RESULT]")):
        LOG.info("ops lane: skip non-OPS subject: %s", subject[:60])
        return

    ts = int(time.time())
    safe_id = source_id.replace("/", "_")[:60]
    queue_file = _ops_queue_dir() / f"{ts}_{safe_id}.md"

    brief_title = subject.removeprefix("[OPS-HANDOFF]").removeprefix("[OPS-RESULT]").strip()
    content = (
        f"# {subject}\n"
        f"**From:** {frm}  **ID:** {source_id}  **Received:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{body_str}\n"
    )
    try:
        queue_file.write_text(content, encoding="utf-8")
        LOG.info("ops_queue: wrote %s", queue_file.name)
    except Exception as e:
        LOG.warning("ops_queue write failed: %s", e)

    _emit("ops_handoff_queued", emitter="sonnet_operator_assistant", data={
        "source_id": source_id,
        "queue_file": str(queue_file),
        "session_id": pair_session_id,
    }, description=f"OPS-HANDOFF queued: {brief_title[:80]}")

    _notify_macos(
        title="Nucleus — OPS brief pending",
        message=brief_title[:120] if brief_title else subject[:120],
    )


async def poll_loop_operator_assistant(pair_session_id: str,
                                       poll_interval_s: int = 10) -> None:
    while True:
        try:
            for path in list_pending_ops():
                env = parse_envelope(path)
                if env is None:
                    _archive_ops(path)
                    continue
                try:
                    await handle_ops_handoff(env, pair_session_id)
                except Exception as e:
                    LOG.exception("ops handler failed for %s: %s", path.name, e)
                finally:
                    _archive_ops(path)
        except Exception as e:
            LOG.exception("ops poll cycle error: %s", e)
        await asyncio.sleep(poll_interval_s)


async def run(lane: str) -> int:
    """Main entrypoint. Blocks until SIGTERM/SIGINT."""
    if lane == "operator_assistant":
        return await _run_operator_assistant()

    if lane not in ("peer", "main"):
        LOG.error("v0.1 supports lane=peer|main|operator_assistant; got %r", lane)
        return 2

    charter_path = Path.cwd() / "docs" / "org" / "charters" / f"sonnet_pair_{lane}.md"
    if not charter_path.exists():
        LOG.error("missing charter: %s", charter_path)
        return 3

    _write_pid(lane)
    pair_session_id = _ensure_session_id(lane)
    pair_sender = f"sonnet_{lane}"
    started_at_ms = int(time.time() * 1000)
    busy = _BusyTracker()

    LOG.info("sonnet_pair_%s starting — session=%s pid=%d charter=%s",
             lane, pair_session_id, os.getpid(), charter_path)

    stop = asyncio.Event()

    def _on_sig(*_a):
        LOG.info("signal received; shutting down")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _on_sig)
        except NotImplementedError:
            pass

    poll_task = asyncio.create_task(
        poll_loop(lane, charter_path, pair_sender, pair_session_id, busy)
    )
    hb_task = asyncio.create_task(
        heartbeat_loop(lane, pair_sender, pair_session_id, busy, started_at_ms)
    )

    await stop.wait()
    poll_task.cancel()
    hb_task.cancel()
    for t in (poll_task, hb_task):
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass

    LOG.info("sonnet_pair_%s exited", lane)
    return 0


async def _run_operator_assistant() -> int:
    """Operator-assistant daemon: watches claude_code_operator_assistant bucket,
    writes [OPS-HANDOFF] briefs to .brain/ops_queue/ so they survive session
    restarts and surface in the SessionStart hook greeting."""
    _write_pid("operator_assistant")
    pair_session_id = _ensure_session_id("operator_assistant")
    LOG.info("sonnet_pair_operator_assistant starting — session=%s pid=%d",
             pair_session_id, os.getpid())

    stop = asyncio.Event()

    def _on_sig(*_a):
        LOG.info("signal received; shutting down operator_assistant daemon")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _on_sig)
        except NotImplementedError:
            pass

    poll_task = asyncio.create_task(
        poll_loop_operator_assistant(pair_session_id)
    )

    await stop.wait()
    poll_task.cancel()
    try:
        await poll_task
    except (asyncio.CancelledError, Exception):
        pass

    LOG.info("sonnet_pair_operator_assistant exited")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: python -m mcp_server_nucleus.runtime.sonnet_pair_daemon <lane>", file=sys.stderr)
        print("  lane: peer | main | operator_assistant", file=sys.stderr)
        return 1
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(run(argv[0]))


if __name__ == "__main__":
    sys.exit(main())
