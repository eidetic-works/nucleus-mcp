from __future__ import annotations
import inspect
import json
import logging
import os
import time
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from ..common import get_brain_path
from ..providers import coerce_to_tuple

logger = logging.getLogger("nucleus.relay")

_RELAY_ID_RE = re.compile(r"^relay_\d{8}_\d{6}_[a-f0-9]{8}")

def _is_shipped_artifact(ref: str) -> bool:
    head = str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()
    return bool(head) and not _RELAY_ID_RE.match(head)


# ── Poll daemon registry (relay_poll_start / stop / status) ──────────────────
# Keyed by recipient bucket name.  Each value is a _PollDaemon instance.
_poll_daemons: Dict[str, "_PollDaemon"] = {}
_poll_daemons_lock = threading.Lock()

_POLL_SIGNAL_FILENAME = "POLL_SIGNAL.json"


class _PollDaemon:
    """Background thread that polls a relay bucket and writes a signal file.

    Spawned by relay_poll_start(); stopped by relay_poll_stop().
    Writes .brain/relay/<recipient>/POLL_SIGNAL.json on every scan cycle
    so Cascade threads can call relay_poll_status() without any blocking.

    Does NOT ack or move files — relay_inbox / relay_ack own that.
    """

    def __init__(
        self,
        recipient: str,
        interval_s: int = 10,
        session_id: Optional[str] = None,
    ):
        self.recipient = recipient
        self.interval_s = interval_s
        self.session_id = session_id
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=f"relay-poll-{recipient}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=max(self.interval_s + 2, 5))

    def _signal_path(self) -> Path:
        return _get_relay_dir(self.recipient) / _POLL_SIGNAL_FILENAME

    def _scan(self) -> List[Dict[str, Any]]:
        """Return list of pending (unread) relay summaries for recipient."""
        # PR-A v0.1 swap-point: HTTP-mode poll via relay_transport.read_inbox
        # at the same self.interval_s cadence. Builds same summary shape.
        from ..relay_transport import is_http_mode, read_inbox as _transport_read
        if is_http_mode():
            try:
                messages = _transport_read(self.recipient, unread_only=True, limit=200)
            except Exception:
                return []
            return [
                {
                    "relay_id": m.get("id", ""),
                    "subject": m.get("subject", ""),
                    "from": m.get("from", ""),
                    "priority": m.get("priority", "normal"),
                    "in_reply_to": m.get("in_reply_to"),
                }
                for m in messages
                if not (self.session_id and m.get("to_session_id") and m.get("to_session_id") != self.session_id)
            ]

        relay_dir = _get_relay_dir(self.recipient)
        pending = []
        try:
            for fpath in sorted(relay_dir.glob("*.json")):
                if fpath.name == _POLL_SIGNAL_FILENAME:
                    continue
                if fpath.parent.name in ("processed", "acks"):
                    continue
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if data.get("read") is True:
                    continue
                # Optional session_id filter
                if self.session_id:
                    ts = data.get("to_session_id")
                    if ts and ts != self.session_id:
                        continue
                pending.append({
                    "relay_id": data.get("id", fpath.stem),
                    "subject": data.get("subject", ""),
                    "from": data.get("from", ""),
                    "priority": data.get("priority", "normal"),
                    "in_reply_to": data.get("in_reply_to"),
                })
        except Exception as exc:
            logger.debug(f"relay_poll scan error for {self.recipient}: {exc}")
        return pending

    def _write_signal(self, pending: List[Dict[str, Any]]) -> None:
        signal = {
            "running": True,
            "recipient": self.recipient,
            "interval_s": self.interval_s,
            "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pending": pending,
            "pending_count": len(pending),
        }
        try:
            path = self._signal_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(signal, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug(f"relay_poll signal write failed: {exc}")

    def _run(self) -> None:
        logger.info(f"relay_poll daemon started for bucket '{self.recipient}' (interval={self.interval_s}s)")
        while not self._stop_event.is_set():
            pending = self._scan()
            self._write_signal(pending)
            self._stop_event.wait(timeout=self.interval_s)
        # Mark signal file as stopped on clean exit
        try:
            path = self._signal_path()
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                data["running"] = False
                data["stopped_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        logger.info(f"relay_poll daemon stopped for bucket '{self.recipient}'")


class RelayWatchHandler:
    """Watches .brain/relay/ for new message files.

    When a new JSON file appears in any recipient's mailbox:
    1. Consolidates pending.json (atomic)
    2. Emits a relay_message_received event (feeds engram hooks)
    3. Logs the arrival

    Since Claude Code can't receive async push mid-turn, pending.json
    is the signal — the next session start or morning brief reads it.
    """

    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.relay_dir = brain_path / "relay"
        self._seen_files: set = set()
        self._debounce_seconds = 2.0
        self._last_consolidate = 0.0

        # Snapshot existing files so we only trigger on genuinely new ones
        for d in self.relay_dir.iterdir():
            if d.is_dir():
                for f in d.glob("*.json"):
                    self._seen_files.add(str(f))

    def on_created(self, event):
        """Handle new file creation in relay directory."""
        if event.is_directory:
            return
        src = str(event.src_path)
        if not src.endswith(".json") or src.endswith("pending.json") or src.endswith(".tmp"):
            return
        if src in self._seen_files:
            return
        self._seen_files.add(src)
        self._on_new_relay_message(Path(src))

    def on_modified(self, event):
        """Also catch modifications (some editors create then write)."""
        if event.is_directory:
            return
        src = str(event.src_path)
        if not src.endswith(".json") or src.endswith("pending.json") or src.endswith(".tmp"):
            return
        # Only process if not yet seen (new file written in two steps)
        if src not in self._seen_files:
            self._seen_files.add(src)
            self._on_new_relay_message(Path(src))

    def _on_new_relay_message(self, path: Path):
        """Process a newly arrived relay message."""
        import time
        now = time.time()

        # Debounce consolidation
        if now - self._last_consolidate < self._debounce_seconds:
            return
        self._last_consolidate = now

        try:
            msg = _parse_relay_message(path)
            sender = msg.get("from", "unknown")
            recipient = path.parent.name
            subject = msg.get("subject", "(no subject)")
            priority = msg.get("priority", "normal")

            logger.info(
                f"📬 New relay: [{sender} → {recipient}] "
                f"{subject} (priority={priority})"
            )

            # Consolidate pending.json
            relay_consolidate_pending()

            # Emit event for the hook system
            try:
                from .event_ops import _emit_event
                _emit_event(
                    event_type="relay_message_received",
                    emitter="relay_watcher",
                    data={
                        "message_id": msg.get("id"),
                        "from": sender,
                        "to": recipient,
                        "subject": subject,
                        "priority": priority,
                    },
                    description=f"Relay message from {sender} to {recipient}: {subject}",
                )
            except Exception:
                pass  # Never let event emission break the watcher

            # Autonomous delegation: urgent/high relays auto-create tasks
            if priority in ("high", "urgent"):
                try:
                    _auto_dispatch_relay(msg, recipient, brain_path=self.brain_path)
                except Exception as e:
                    logger.warning(f"Auto-dispatch failed for relay {msg.get('id', '?')}: {e}")

        except Exception as e:
            logger.error(f"Error processing relay message {path}: {e}")


def start_relay_watcher(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Start watching .brain/relay/ for new messages.

    Uses watchdog if available, otherwise returns gracefully.
    Called during MCP server initialization.
    """
    global _relay_observer

    if brain_path is None:
        brain_path = get_brain_path()

    relay_dir = brain_path / "relay"
    relay_dir.mkdir(parents=True, exist_ok=True)

    with _relay_observer_lock:
        if _relay_observer is not None:
            return {"status": "already_running"}

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            handler = RelayWatchHandler(brain_path)

            class WatchdogRelay(FileSystemEventHandler):
                def on_created(self, event):
                    handler.on_created(event)
                def on_modified(self, event):
                    handler.on_modified(event)

            _relay_observer = Observer()
            _relay_observer.schedule(WatchdogRelay(), str(relay_dir), recursive=True)
            _relay_observer.daemon = True
            _relay_observer.start()

            logger.info(f"📬 Relay watcher started for {relay_dir}")

            return {
                "status": "started",
                "watching": str(relay_dir),
                "handler": "watchdog",
            }

        except ImportError:
            logger.info("Relay watcher: watchdog not installed, skipping")
            return {
                "status": "skipped",
                "reason": "watchdog not installed",
                "hint": "pip install watchdog",
            }
        except Exception as e:
            logger.error(f"Relay watcher failed to start: {e}")
            return {
                "status": "error",
                "error": str(e),
            }


def stop_relay_watcher() -> Dict[str, Any]:
    """Stop the relay file watcher."""
    global _relay_observer

    with _relay_observer_lock:
        if _relay_observer is not None:
            try:
                _relay_observer.stop()
                _relay_observer.join(timeout=5)
            except Exception:
                pass
            _relay_observer = None
            return {"status": "stopped"}
        return {"status": "not_running"}


def relay_archive(
    recipient: Optional[str] = None,
    max_age_days: int = 7,
    max_count: int = 100,
    brain_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Archive relay messages beyond a retention window.

    Implements the relay-inbox retention policy from the agent org expansion
    plan: "keep last ``max_count`` or last ``max_age_days``, whichever is
    smaller; old relays archived to ``.brain/relay/<agent>/archive/<date>.jsonl``."

    The archive format is newline-delimited JSON (one relay per line), grouped
    by the relay's ``created_at`` date.  Original ``.json`` files are deleted
    after successful archival (unless ``dry_run=True``).

    Args:
        recipient: Relay bucket to archive (e.g. ``claude_code_main``).
            Auto-detected if omitted.
        max_age_days: Messages older than this many days are eligible for
            archival.  Default 7.
        max_count: Maximum number of messages to retain regardless of age.
            Default 100.
        brain_path: Override brain directory.
        dry_run: If True, compute what would be archived but don't move
            anything.

    Returns:
        Dict with ``archived``, ``kept``, ``archive_paths``, ``dry_run``.
    """
    brain = brain_path or get_brain_path()
    me = recipient or detect_session_role()
    bucket = brain / "relay" / me

    if not bucket.is_dir():
        return {
            "recipient": me,
            "archived": 0,
            "kept": 0,
            "archive_paths": [],
            "dry_run": dry_run,
            "error": f"Bucket directory not found: {bucket}",
        }

    # Collect all relay JSON files in the bucket (exclude archive subdir).
    relay_files: List[Path] = sorted(
        (f for f in bucket.glob("*.json") if f.is_file()),
        key=lambda p: p.name,
    )

    if not relay_files:
        return {
            "recipient": me,
            "archived": 0,
            "kept": len(relay_files),
            "archive_paths": [],
            "dry_run": dry_run,
        }

    # Parse created_at from each file to determine age.
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - (max_age_days * 86400)

    # Build list of (file, created_at_ts, relay_data) — newest last.
    entries: List[tuple] = []
    for f in relay_files:
        try:
            data = json.loads(f.read_text())
            created_str = data.get("created_at", "")
            if created_str:
                # Parse ISO timestamp — handle both Z and +00:00 suffixes.
                ts_str = created_str.replace("Z", "+00:00")
                try:
                    ts = datetime.fromisoformat(ts_str).timestamp()
                except (ValueError, TypeError):
                    ts = f.stat().st_mtime
            else:
                ts = f.stat().st_mtime
            entries.append((f, ts, data))
        except Exception:
            # Unparseable files are kept (not archived).
            continue

    # Sort newest-first for the keep/archive split.
    entries.sort(key=lambda e: e[1], reverse=True)

    # Determine which entries to archive:
    # Keep the newest ``max_count`` entries AND anything within ``max_age_days``.
    # Archive = entries that are BOTH beyond max_count AND older than cutoff.
    to_archive: List[tuple] = []
    to_keep: List[tuple] = []

    for idx, entry in enumerate(entries):
        _f, ts, _data = entry
        within_count = idx < max_count
        within_age = ts >= cutoff
        if within_count or within_age:
            to_keep.append(entry)
        else:
            to_archive.append(entry)

    if not to_archive:
        return {
            "recipient": me,
            "archived": 0,
            "kept": len(to_keep),
            "archive_paths": [],
            "dry_run": dry_run,
        }

    if dry_run:
        return {
            "recipient": me,
            "archived": len(to_archive),
            "kept": len(to_keep),
            "archive_paths": [],
            "dry_run": True,
        }

    # Group archived entries by date for JSONL output.
    archive_dir = bucket / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    by_date: Dict[str, List[dict]] = {}
    for _f, ts, data in to_archive:
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        by_date.setdefault(date_str, []).append(data)

    archive_paths: List[str] = []
    for date_str, relays in sorted(by_date.items()):
        archive_file = archive_dir / f"{date_str}.jsonl"
        # Append to existing archive for the same date (idempotent across runs).
        with archive_file.open("a") as fh:
            for relay in relays:
                fh.write(json.dumps(relay, default=str) + "\n")
        archive_paths.append(str(archive_file))

    # Delete originals after successful archival.
    deleted = 0
    for f, _ts, _data in to_archive:
        try:
            f.unlink()
            deleted += 1
        except OSError as exc:
            logger.warning(f"Failed to delete archived relay {f.name}: {exc}")

    return {
        "recipient": me,
        "archived": deleted,
        "kept": len(to_keep),
        "archive_paths": sorted(set(archive_paths)),
        "dry_run": False,
    }


def auto_start_relay_watcher(brain_path: Optional[Path] = None):
    """Auto-start relay watcher during MCP server init.

    Called from server.py or __init__.py during startup.
    Always-on — doesn't require sync.enabled config.
    """
    try:
        start_relay_watcher(brain_path)
    except Exception as e:
        logger.debug(f"Relay watcher auto-start failed (non-critical): {e}")


def relay_poll_start(
    recipient: str,
    interval_s: int = 10,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Start an autonomous background poll daemon for a relay bucket.

    The daemon scans `recipient`'s inbox every `interval_s` seconds and
    writes `.brain/relay/<recipient>/POLL_SIGNAL.json` with pending relay
    summaries.  Cascade threads call relay_poll_status() at turn start
    (instant, non-blocking) to check for new tasks — no paste, no VSIX
    injection needed.

    Idempotent: calling again while running returns already_running status.

    Args:
        recipient:   Relay bucket to watch (e.g. 'windsurf', 'claude_code_main').
        interval_s:  Scan frequency in seconds. Default 10.
        session_id:  If set, only surface relays addressed to this session.

    Returns:
        {status: 'started'|'already_running', recipient, interval_s}
    """
    with _poll_daemons_lock:
        existing = _poll_daemons.get(recipient)
        if existing is not None and existing._thread.is_alive():
            return {
                "status": "already_running",
                "recipient": recipient,
                "interval_s": existing.interval_s,
            }
        daemon = _PollDaemon(recipient=recipient, interval_s=interval_s, session_id=session_id)
        daemon.start()
        _poll_daemons[recipient] = daemon
        logger.info(f"relay_poll_start: daemon started for '{recipient}' interval={interval_s}s")
        return {
            "status": "started",
            "recipient": recipient,
            "interval_s": interval_s,
            "session_id": session_id,
            "signal_file": str(daemon._signal_path()),
        }


def relay_poll_stop(recipient: str) -> Dict[str, Any]:
    """Stop the poll daemon for a relay bucket.

    Args:
        recipient: Relay bucket name whose daemon to stop.

    Returns:
        {status: 'stopped'|'not_running', recipient}
    """
    with _poll_daemons_lock:
        daemon = _poll_daemons.pop(recipient, None)
    if daemon is None:
        return {"status": "not_running", "recipient": recipient}
    daemon.stop()
    return {"status": "stopped", "recipient": recipient}


def relay_poll_status(recipient: str) -> Dict[str, Any]:
    """Read the latest poll signal for a relay bucket (instant, non-blocking).

    Call this at the start of every turn to check for pending relays.
    If pending is non-empty, call relay_inbox to read the full messages.

    Args:
        recipient: Relay bucket to check (e.g. 'windsurf').

    Returns:
        {running: bool, pending: [{relay_id, subject, from, priority}], checked_at, pending_count}
        If daemon not started: {running: false, pending: [], hint: '...'}
    """
    with _poll_daemons_lock:
        daemon = _poll_daemons.get(recipient)
    running = daemon is not None and daemon._thread.is_alive()

    signal_path = _get_relay_dir(recipient) / _POLL_SIGNAL_FILENAME
    if signal_path.exists():
        try:
            data = json.loads(signal_path.read_text(encoding="utf-8"))
            data["running"] = running
            return data
        except Exception:
            pass

    return {
        "running": running,
        "recipient": recipient,
        "pending": [],
        "pending_count": 0,
        "checked_at": None,
        "hint": "Call relay_poll_start(recipient) once per session to begin autonomous polling.",
    }


def relay_wait(
    in_reply_to: str,
    recipient: str,
    timeout_s: int = 60,
    poll_interval_s: int = 5,
) -> Dict[str, Any]:
    """Poll recipient's inbox until a reply to `in_reply_to` arrives.

    Blocks synchronously for up to `timeout_s` seconds, polling every
    `poll_interval_s` seconds. Intended for cross-thread / cross-agent
    tandem coordination where one agent posts a relay and needs to wait
    for the other agent's reply before proceeding.

    Keep `timeout_s` short (30-60s) when called via MCP to avoid blocking
    the connection. Callers can retry on timed_out=True.

    Args:
        in_reply_to: The relay_id this function waits for a reply to.
        recipient:   The bucket to scan (e.g. 'windsurf', 'claude_code_main').
        timeout_s:   Max seconds to wait before returning timed_out=True.
        poll_interval_s: Seconds between inbox scans.

    Returns:
        {found: True,  relay_id: str, subject: str, waited_s: int}
        {found: False, timed_out: True, waited_s: int}
    """
    import time

    # GAP-4 swap-point: HTTP-mode scan via relay_transport.read_inbox —
    # same guard pattern as _PollDaemon._scan. Checked fresh each cycle so
    # an env flip mid-wait takes effect. unread_only=False mirrors the FS
    # branch, which matches replies regardless of read state.
    from ..relay_transport import is_http_mode, read_inbox as _transport_read

    relay_dir = _get_relay_dir(recipient)
    deadline = time.monotonic() + timeout_s
    waited = 0

    while True:
        if is_http_mode():
            try:
                messages = _transport_read(recipient, unread_only=False, limit=200)
            except Exception:
                messages = []
            for m in messages:
                if m.get("in_reply_to") == in_reply_to:
                    return {
                        "found": True,
                        "relay_id": m.get("id", ""),
                        "subject": m.get("subject", ""),
                        "from": m.get("from", ""),
                        "waited_s": waited,
                    }
        else:
            try:
                for fpath in sorted(relay_dir.glob("*.json")):
                    if fpath.parent.name in ("processed", "acks"):
                        continue
                    try:
                        data = json.loads(fpath.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if data.get("in_reply_to") == in_reply_to:
                        return {
                            "found": True,
                            "relay_id": data.get("id", fpath.stem),
                            "subject": data.get("subject", ""),
                            "from": data.get("from", ""),
                            "waited_s": waited,
                        }
            except Exception as exc:
                logger.debug(f"relay_wait: scan error: {exc}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"found": False, "timed_out": True, "waited_s": waited}

        sleep_for = min(poll_interval_s, remaining)
        time.sleep(sleep_for)
        waited += int(sleep_for)


def relay_listen(
    recipient: str,
    window_s: int = 60,
    poll_s: int = 5,
    in_reply_to: Optional[str] = None,
    known_ids: Optional[List[str]] = None,
    attempt: int = 1,
) -> Dict[str, Any]:
    """Block at the end of a turn waiting for the next inbound relay.

    Unlike relay_wait (which waits for a reply to a *specific* relay_id),
    relay_listen waits for *any* new relay that wasn't there when called.
    This is the "end-of-turn wait" primitive for the autonomous ping-pong loop:

        Agent A does work → relay_post to B → relay_listen(window_s=60)
        → when B's reply lands, A's next turn starts with the relay in hand.

    The function NEVER raises on timeout — it returns
    {found: False, call_again: True, known_ids: [...]} so the caller can
    retry in the next turn, incrementing attempt each time.
    Adaptive interval: actual poll frequency = min(poll_s * attempt, 30s)
    so long-running tasks get progressively gentler polling.

    Args:
        recipient:    Bucket to watch (e.g. 'windsurf').
        window_s:     Seconds to hold the connection open this call. Default 60.
                      Keep <=90s to avoid MCP connection timeouts.
                      Retry with call_again=True — relay_listen is stateless across calls.
        poll_s:       Base poll interval in seconds. Default 5.
        in_reply_to:  Optional relay_id to filter — only surface replies to this.
                      Omit to catch any new relay in the bucket.
        known_ids:    List of relay IDs already seen (from a prior call's response).
                      Pass this back on retry so arrivals during the gap aren't missed.
        attempt:      Retry count (1-based). Increases poll interval adaptively.
                      Pass attempt=next_attempt from the previous response on retry.

    Returns:
        Found:   {found: True,  relay: {relay_id, subject, from, priority, in_reply_to},
                  waited_s: int, recipient: str}
        Timeout: {found: False, call_again: True, waited_s: int, recipient: str,
                  known_ids: [str, ...], next_attempt: int, next_poll_s: int,
                  hint: "call relay_listen again with known_ids=... attempt=..."}
    """
    effective_poll = min(poll_s * max(attempt, 1), 30)
    relay_dir = _get_relay_dir(recipient)

    # GAP-4 swap-point: HTTP-mode scan via relay_transport.read_inbox —
    # same guard pattern as _PollDaemon._scan. unread_only=True for both
    # snapshot and poll: the FS branch skips read==True arrivals anyway,
    # and an already-unread message present at call time lands in `seen`
    # either way, so the surfaced set is equivalent.
    from ..relay_transport import is_http_mode, read_inbox as _transport_read

    # Snapshot existing IDs so we only surface truly new arrivals
    seen: set = set(known_ids or [])
    if not seen:
        if is_http_mode():
            try:
                for m in _transport_read(recipient, unread_only=True, limit=200):
                    if m.get("id"):
                        seen.add(m["id"])
            except Exception:
                pass
        else:
            try:
                for fpath in relay_dir.glob("*.json"):
                    if fpath.name == _POLL_SIGNAL_FILENAME:
                        continue
                    if fpath.parent.name in ("processed", "acks"):
                        continue
                    seen.add(fpath.stem)
            except Exception:
                pass

    deadline = time.monotonic() + window_s
    waited = 0

    while True:
        if is_http_mode():
            try:
                messages = _transport_read(recipient, unread_only=True, limit=200)
            except Exception:
                messages = []
            for m in messages:
                mid = m.get("id", "")
                if not mid or mid in seen:
                    continue
                # Filter by in_reply_to if specified
                if in_reply_to and m.get("in_reply_to") != in_reply_to:
                    seen.add(mid)
                    continue
                return {
                    "found": True,
                    "relay": {
                        "relay_id": mid,
                        "subject": m.get("subject", ""),
                        "from": m.get("from", ""),
                        "priority": m.get("priority", "normal"),
                        "in_reply_to": m.get("in_reply_to"),
                        "context": m.get("context") or {},
                        "is_convergence": bool((m.get("context") or {}).get("convergence")),
                    },
                    "waited_s": waited,
                    "recipient": recipient,
                }
        else:
            try:
                for fpath in sorted(relay_dir.glob("*.json")):
                    if fpath.name == _POLL_SIGNAL_FILENAME:
                        continue
                    if fpath.parent.name in ("processed", "acks"):
                        continue
                    stem = fpath.stem
                    if stem in seen:
                        continue
                    try:
                        data = json.loads(fpath.read_text(encoding="utf-8"))
                    except Exception:
                        seen.add(stem)
                        continue
                    if data.get("read") is True:
                        seen.add(stem)
                        continue
                    # Filter by in_reply_to if specified
                    if in_reply_to and data.get("in_reply_to") != in_reply_to:
                        seen.add(stem)
                        continue
                    return {
                        "found": True,
                        "relay": {
                            "relay_id": data.get("id", stem),
                            "subject": data.get("subject", ""),
                            "from": data.get("from", ""),
                            "priority": data.get("priority", "normal"),
                            "in_reply_to": data.get("in_reply_to"),
                            "context": data.get("context", {}),
                            "is_convergence": bool(data.get("context", {}).get("convergence")),
                        },
                        "waited_s": waited,
                        "recipient": recipient,
                    }
            except Exception as exc:
                logger.debug(f"relay_listen: scan error: {exc}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {
                "found": False,
                "call_again": True,
                "waited_s": waited,
                "recipient": recipient,
                "known_ids": list(seen),
                "next_attempt": attempt + 1,
                "next_poll_s": min(effective_poll * 2, 30),
                "hint": (
                    f"No new relay in {window_s}s. Call relay_listen again with "
                    f"known_ids=<this response's known_ids> attempt={attempt + 1} "
                    f"to continue waiting without missing arrivals."
                ),
            }

        sleep_for = min(effective_poll, remaining)
        time.sleep(sleep_for)
        waited += int(sleep_for)



# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .paths import *
from .core import *
from .instrumentation import *
from .pending import *
from .briefing import *
from .watcher import *
