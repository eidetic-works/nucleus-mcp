"""Native MCP notifications for relay-arrival events.

Operator FOUNDER-OVERRIDE 2026-05-31 (relay_20260531_152027_00d0da76): replace
bash polling daemons (watch-relay-agy.sh etc.) with server-initiated push.

Architecture:
    Per-agent: client calls `relay_subscribe_notifications` ONCE at session
    start (via SessionStart hook). The MCP server holds a long-poll
    subscription that watches the calling agent's role-specific inbox dir,
    and fires `ctx.info()` on each new file arrival until timeout. Client
    re-subscribes on timeout.

    Cross-process: writer (any agent) calls relay_post which writes a file
    under .brain/relay/<role>/. Recipient's MCP server process notices the
    file via watchdog (or 1s polling fallback) and pushes notification to
    its own client via Context.send_notification (info-level log message).

    Why ctx.info() not custom JSON-RPC notification: Claude Code's MCP
    client surfaces log messages natively; custom notification types
    require client-side handlers that aren't standard yet. info-level is
    the lowest-friction path that works across all MCP clients today.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastmcp import Context

_DEFAULT_TIMEOUT_S = 270  # under FastMCP context-cache TTL


def _resolve_inbox_dir(
    role: Optional[str] = None,
    inbox_filter: Optional[str] = None,
) -> Path:
    """Resolve the calling agent's own inbox dir.

    Per PR #1 (CCR-inversion-for-relay-pickup) fix to feedback_relay_arrival_invisible_midsession:
        Uses canonical role→inbox-dir map (relay_inbox_canonical.py) instead of
        prior hand-coded "main"/"peer" branching. Closes the 3-week-old bug where
        cc-tb role mapped to wrong inbox (e.g., `tb/` instead of canonical `cc_tb/`).

    Args:
        role: agent role (e.g., "tb", "cc_tb", "main"). Resolved via canonical map.
        inbox_filter: explicit inbox dir NAME override (e.g., "cc_tb").
            When provided, BYPASSES role detection entirely. Use for explicit
            cross-target subscriptions in test harnesses.
    """
    from .relay_ops import _get_relay_dir, detect_session_role
    from .relay_inbox_canonical import resolve_canonical_inbox_name

    if inbox_filter:
        # Explicit dir-name override (test harness or admin tools)
        return _get_relay_dir(inbox_filter.strip().lower())

    role = role or os.environ.get("CC_SESSION_ROLE", "").strip().lower() or detect_session_role()
    canonical_dir = resolve_canonical_inbox_name(role)
    return _get_relay_dir(canonical_dir or role)


def _envelope_summary(file_path: Path) -> dict[str, Any]:
    """Read minimal envelope fields without loading full body."""
    try:
        d = json.loads(file_path.read_text())
        return {
            "id": d.get("id"),
            "from": d.get("from"),
            "subject": (d.get("subject") or "")[:120],
            "priority": d.get("priority", "normal"),
            "in_reply_to": d.get("in_reply_to"),
            "created_at": d.get("created_at"),
            # ADR-0042 D3: carry the project tag so the poll loop can apply the
            # (project, role) filter. None on legacy untagged envelopes.
            "project": d.get("project"),
        }
    except (json.JSONDecodeError, OSError) as exc:
        return {"id": file_path.stem, "error": f"parse_failed: {exc}"}


async def relay_subscribe_notifications_impl(
    ctx: "Context",
    timeout_seconds: int = _DEFAULT_TIMEOUT_S,
    role: Optional[str] = None,
    inbox_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Long-poll subscription that fires ctx.info() on each new inbox file.

    Returns when timeout fires OR client disconnects. Client should re-call
    this in a loop (via SessionStart hook or recurring agent action) for
    persistent coverage. Default timeout 270s = under FastMCP context-cache
    TTL so re-subscribe doesn't burn cache.

    Args:
        timeout_seconds: max subscription duration. Capped 60..1800.
        role: override calling agent's role (default: env-detected).
        inbox_filter: explicit inbox dir NAME (e.g., "cc_tb") that BYPASSES
            role-based resolution. Per PR #1 CCR-inversion: lets a session
            subscribe to an EXPLICIT canonical inbox even if role detection
            is misconfigured. Closes feedback_relay_arrival_invisible_midsession.

    Returns:
        dict with: subscribed_dir, watched_seconds, events_fired, last_seen_id.

    KNOWN LIMITATION v0.1 (per cc-peer hole-poke verdict 2026-06-05 F4):
        Poller may transiently read a partial file mid-write. relay_post writes
        via Path.write_text directly (NOT atomic mv-rename — only pending.json
        consolidation uses os.replace at relay_ops.py:1216-1219). On JSON parse
        failure, _envelope_summary returns {'error': 'parse_failed: ...'},
        poller marks the filename as seen, and never retries. If the file
        becomes valid milliseconds later, the agent NEVER gets the proper
        notification.

        Window is small (<1ms typical for small JSON files due to write()
        syscall semantics for sub-4KB writes on Linux/macOS), but non-zero.
        Mitigation deferred to v0.2 atomic-write patch in relay_ops.py
        (relay_post should write `relay/<role>/<id>.json.tmp` then
        os.replace(tmp, final) — matches the pending.json pattern).

        For relay writers TODAY: ensure single-shot complete-write semantics
        (avoid streaming/partial-flush patterns). Per cc-peer 2026-06-05 lean,
        document-known-limitation is acceptable for v0.1 ship; do not gate.
    """
    # BURST MODE: timeout_seconds=0 returns immediately after one inbox scan
    # via persistent marker dir (PR #486). Use this at end-of-turn boundaries
    # for sub-second inbox-drain without blocking on a 270s long-poll. PR #487
    # added per operator empirical observation 2026-06-06: agy 270s windows
    # leave gap-latency too high for tight turn rhythms; burst gives instant
    # drain when agent calls it as a routine end-of-turn check.
    burst_mode = int(timeout_seconds) == 0
    if not burst_mode:
        timeout_seconds = max(60, min(1800, int(timeout_seconds)))
    inbox = _resolve_inbox_dir(role, inbox_filter=inbox_filter)

    # ADR-0042 D3 (flag NUCLEUS_PROJECT_SPINE, default OFF): the live-session
    # push path is the SECOND reader surface the fashion leak streams through
    # (alongside relay_inbox), so it must apply the same (project, role) filter.
    # Flag OFF ⇒ never computed, no predicate, notifications byte-identical to
    # today. FS-only per D4 (HTTP hosted tenancy isolation is deferred to D5),
    # so the HTTP poll branch below is intentionally left unfiltered.
    from .common import _project_spine_on

    _spine_on = _project_spine_on()
    _my_proj: Optional[str] = None
    _reader_bucket = inbox.name  # canonical inbox dir name (e.g. "claude_code_main", "board")
    _project_visible = None
    _warn_legacy_untagged = None
    if _spine_on:
        # Shared predicate + grace-warn helper live in relay/core.py and are
        # re-exported through relay_ops. Import lazily so the OFF path never
        # pulls them (and never touches runtime.project via _reader_project).
        from .relay_ops import _project_visible, _reader_project, _warn_legacy_untagged

        _my_proj = _reader_project()

    # Persistent marker dir per canonical inbox closes the BETWEEN-SUBSCRIBE
    # GAP empirically reported by agy 2026-06-06: arrivals landing while no
    # nucleus_ccr_arm was active (e.g., agy mid-tool-call between 270s windows)
    # were snapshotted into the in-memory `seen` set on next call and never
    # surfaced. Mirrors watch-relay.sh:78 + first-run pre-mark pattern.
    #
    # First-ever call for this canonical inbox: pre-mark all existing files as
    # seen (matches watch-relay.sh "first-run pre-marked N existing relays").
    # Subsequent calls: marker dir already populated for pre-existing; arrivals
    # since previous call have NO marker → surface them. Gap closed.
    state_root = Path(
        os.environ.get(
            "NUCLEUS_RELAY_STATE_DIR",
            str(Path.home() / ".claude" / "state" / "nucleus-relay"),
        )
    )
    seen_dir = state_root / f"server-seen-{inbox.name}"
    first_run = not seen_dir.exists()
    seen_dir.mkdir(parents=True, exist_ok=True)
    # PR-A v0.1 swap-point: HTTP-mode first-run pre-mark uses the HTTP
    # transport to list current inbox ids (rather than FS glob). Subsequent
    # polls in the main loop also use HTTP. Per spec: "at first-run,
    # GET ?unread_only=false and record returned ids into seen_dir;
    # main loop: GET ?unread_only=true and emit each id not yet in seen_dir."
    from .relay_transport import is_http_mode, read_inbox as _transport_read
    _http_mode = is_http_mode()
    
    events_fired = 0
    last_seen_id: Optional[str] = None
    
    if first_run:
        if _http_mode:
            try:
                # Surface unread messages on first run instead of pre-marking.
                # This closes the gap where a relay arrives while the agent
                # isn't subscribed — it gets ignored on next subscribe call.
                for env in _transport_read(inbox.name, unread_only=True, limit=200):
                    rid = env.get("id") or ""
                    if not rid:
                        continue
                    try:
                        (seen_dir / rid).mkdir()
                    except FileExistsError:
                        continue
                    except OSError:
                        continue
                    events_fired += 1
                    last_seen_id = rid
                    msg = (
                        f"[relay-arrival] from={env.get('from','?')} "
                        f"id={rid} priority={env.get('priority','normal')} "
                        f"subject={env.get('subject','')[:80]}"
                    )
                    await ctx.info(msg)
                # Now pre-mark any remaining read messages as seen
                for env in _transport_read(inbox.name, unread_only=False, limit=200):
                    rid = env.get("id") or ""
                    if rid:
                        try:
                            (seen_dir / rid).mkdir(exist_ok=True)
                        except OSError:
                            pass
            except Exception as exc:
                logger.warning("relay_notify first-run http exc: %s", exc)
        else:
            # FS mode: surface unread messages on first run
            from .relay.core import _parse_relay_message
            for fp in inbox.glob("*.json"):
                try:
                    msg_data = _parse_relay_message(fp)
                    if msg_data.get("read"):
                        # Already read — pre-mark as seen, don't surface
                        try:
                            (seen_dir / fp.name).mkdir(exist_ok=True)
                        except OSError:
                            pass
                        continue
                    # Unread — surface it
                    try:
                        (seen_dir / fp.name).mkdir()
                    except FileExistsError:
                        continue
                    except OSError:
                        continue
                    events_fired += 1
                    last_seen_id = msg_data.get("id", fp.name)
                    msg = (
                        f"[relay-arrival] from={msg_data.get('from','?')} "
                        f"id={msg_data.get('id', fp.name)} priority={msg_data.get('priority','normal')} "
                        f"subject={msg_data.get('subject','')[:80]}"
                    )
                    await ctx.info(msg)
                except Exception:
                    # Parse error — pre-mark to avoid retry loop
                    try:
                        (seen_dir / fp.name).mkdir(exist_ok=True)
                    except OSError:
                        pass

    await ctx.info(
        f"[relay-subscribe] watching {inbox} for {timeout_seconds}s "
        f"(role={inbox.name}, state={seen_dir.name}, first_run={first_run}, burst={burst_mode})"
    )

    deadline = time.monotonic() + timeout_seconds

    # 1s polling — lowest-dependency path. fsnotify/watchdog would add a
    # platform dep; polling at 1s gives sub-2s latency which beats the
    # prior bash-daemon's ~30s typical lag.
    #
    # The persistent marker dir means EVERY iteration: scan inbox, atomic-claim
    # marker via mkdir for any file whose marker doesn't yet exist, surface
    # the arrival. Gap-closure: arrivals during between-call windows have no
    # marker so they surface on next call's iteration.
    while True:
        try:
            if _http_mode:
                # PR-A v0.1 swap-point main loop: HTTP-mode polls
                # GET ?unread_only=true at same 1s cadence; surface any
                # id not yet in seen_dir.
                for env in _transport_read(inbox.name, unread_only=True, limit=200):
                    rid = env.get("id") or ""
                    if not rid:
                        continue
                    marker = seen_dir / rid
                    try:
                        marker.mkdir()
                    except FileExistsError:
                        continue
                    except OSError:
                        continue
                    events_fired += 1
                    last_seen_id = rid
                    msg = (
                        f"[relay-arrival] from={env.get('from','?')} "
                        f"id={rid} priority={env.get('priority','normal')} "
                        f"subject={env.get('subject','')}"
                    )
                    if env.get("priority") in ("high", "urgent"):
                        await ctx.warning(msg)
                    else:
                        await ctx.info(msg)
            else:
                for fp in sorted(inbox.glob("*.json")):
                    if _spine_on:
                        # Flag ON: read + filter BEFORE claiming the marker, so a
                        # cross-project envelope in a shared bucket is left
                        # unclaimed for its own project's reader (no marker
                        # collision, no lost notification). ADR-0042 D3.
                        env = _envelope_summary(fp)
                        surface, warn = _project_visible(
                            env.get("project"), _my_proj, _reader_bucket
                        )
                        if not surface:
                            continue
                        marker = seen_dir / fp.name
                        try:
                            marker.mkdir()  # atomic claim; fails if already seen
                        except FileExistsError:
                            continue
                        except OSError:
                            continue
                        if warn:
                            _warn_legacy_untagged(env.get("id"))
                    else:
                        # Flag OFF: unchanged ordering (claim → summary),
                        # byte-identical to pre-spine.
                        marker = seen_dir / fp.name
                        try:
                            marker.mkdir()  # atomic claim; fails if already seen
                        except FileExistsError:
                            continue
                        except OSError:
                            continue
                        env = _envelope_summary(fp)
                    events_fired += 1
                    last_seen_id = env.get("id") or fp.name
                    msg = (
                        f"[relay-arrival] from={env.get('from','?')} "
                        f"id={env.get('id','?')} priority={env.get('priority','normal')} "
                        f"subject={env.get('subject','')}"
                    )
                    if env.get("priority") in ("high", "urgent"):
                        await ctx.warning(msg)
                    else:
                        await ctx.info(msg)
        except Exception as exc:
            # Log + keep looping — don't kill subscription on transient FS errors
            logger.warning("relay_notify poll exception: %s", exc)
        if burst_mode:
            break  # burst: single inbox scan, return immediately
        if time.monotonic() >= deadline:
            break
        await asyncio.sleep(1.0)

    next_action = (
        "burst mode complete; call again with timeout_seconds=0 for next end-of-turn drain"
        if burst_mode
        else "client should re-call relay_subscribe_notifications to continue coverage"
    )
    return {
        "subscribed_dir": str(inbox),
        "watched_seconds": 0 if burst_mode else timeout_seconds,
        "events_fired": events_fired,
        "last_seen_id": last_seen_id,
        "burst_mode": burst_mode,
        "next_action": next_action,
    }
