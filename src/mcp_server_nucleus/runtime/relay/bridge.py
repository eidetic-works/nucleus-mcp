"""Relay bridge daemon — bidirectional FS↔HTTP inbox mirror (v0.2).

Mac sessions stay FS-mode forever; this daemon mirrors the OCI relay
service's inboxes into local ``.brain/relay/<canonical>/`` and pushes
local-originated messages up, so the ``NUCLEUS_RELAY_URL`` per-session
flip is never needed on the Mac. watch-relay.sh / fsnotify watchers keep
working untouched because files still land locally.

Compound-on inventory (no new formats, no new registries):
  bus      = existing POST/GET/ACK routes (http_transport/relay_route.py)
  registry = CANONICAL_ROLE_TO_INBOX_DIR (relay_inbox_canonical.py SSOT)
  format   = the relay/v1 envelope JSON written by relay_post (core.py)
  handler  = _get_relay_dir(force_fs=True) local-write path
  reader   = unchanged FS consumers (watchers, hooks, relay_inbox)

Sync semantics per inbox, per cycle:
  PULL  GET /relay/{inbox}?unread_only=false&limit=200 with the bridge
        bearer (GET/ACK are token-valid-only, one token reads all).
        Missing ids are written verbatim under the server filename
        (``_file``). Read-state merges monotonically: coarse ``read`` is
        OR'd, ``read_by_sessions`` is unioned, in both directions.
        Local read=true & server read=false → POST /ack server-ward.
  PUSH  Local ids absent from the server window and not in pushed-state
        are POSTed with the *sender's* bearer (sender-binding 403s
        otherwise) resolved from ``<token_dir>/relay_token_<role>``.
        ``body.id`` carries the local id (server preserves it per the
        v0.2 amendment) and ``Idempotency-Key`` doubles as in-flight
        dedup. Successful/duplicate pushes are recorded in the state
        file so a server restart (in-memory idempotency cache lost)
        cannot cause re-push.

Known limit (flagged in the v0.2 spike verdict): GET has no pagination
cursor — the mirror window is the newest 200 messages per inbox per
cycle. Older local files outside the window are protected from re-push
by pushed-state, and by the max-age guard for pre-bridge history.

Never crashes: transport errors back off exponentially (cap 300s); the
Mac works offline and syncs on recovery.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..relay_inbox_canonical import (
    CANONICAL_ROLE_TO_INBOX_DIR,
    resolve_canonical_inbox_name,
)
from .paths import _get_relay_dir

logger = logging.getLogger("nucleus.relay.bridge")

DEFAULT_INTERVAL_S = 5.0
BACKOFF_MAX_S = 300.0
PULL_LIMIT = 200
HTTP_TIMEOUT_S = 15
STATE_MAX_IDS = 2000
# Local files older than this are never push-candidates: they predate the
# bridge (server never saw them) and re-publishing weeks-old history would
# fire wake side-effects for stale mail.
PUSH_MAX_AGE_S = float(os.environ.get("NUCLEUS_BRIDGE_PUSH_MAX_AGE_S", str(48 * 3600)))

# ── Engram sync (background, slower cadence than relay messages) ──────
# Enabled when NUCLEUS_BRIDGE_ENGRAM_SYNC=1 OR when NUCLEUS_SYNC_URL is
# explicitly set. The engram sync endpoint is heavier than the relay
# message bus (full ledger scan + ADUN apply), so it runs on its own
# interval — default 300s (5 min) — separate from the 5s relay loop.
DEFAULT_ENGRAM_SYNC_INTERVAL_S = float(
    os.environ.get("NUCLEUS_BRIDGE_ENGRAM_SYNC_INTERVAL_S", str(300))
)

_VALID_MID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


# ── Config ────────────────────────────────────────────────────────────


def _relay_url() -> str:
    return os.environ.get("NUCLEUS_RELAY_URL", "").rstrip("/")


def _bridge_bearer() -> str:
    return os.environ.get("NUCLEUS_RELAY_BEARER", "").strip()


def _token_dir() -> Path:
    return Path(
        os.environ.get("NUCLEUS_BRIDGE_TOKEN_DIR", str(Path.home() / ".tb"))
    )


def _state_dir() -> Path:
    d = Path(
        os.environ.get(
            "NUCLEUS_BRIDGE_STATE_DIR",
            str(Path.home() / ".claude" / "state" / "nucleus-relay-bridge"),
        )
    )
    d.mkdir(parents=True, exist_ok=True)
    return d


def bridge_inboxes() -> List[str]:
    """Inbox dirs to mirror: canonical SSOT values + env extras.

    ``NUCLEUS_BRIDGE_INBOXES`` (comma-separated) replaces the set when it
    starts with ``=`` (e.g. ``=cc_tb,board``) and extends it otherwise
    (e.g. ``bespoq,bespoq_cowork`` for non-fleet lanes).
    """
    canonical = sorted(set(CANONICAL_ROLE_TO_INBOX_DIR.values()))
    raw = os.environ.get("NUCLEUS_BRIDGE_INBOXES", "").strip()
    if not raw:
        return canonical
    names = [n.strip() for n in raw.lstrip("=").split(",") if n.strip()]
    if raw.startswith("="):
        return sorted(set(names))
    return sorted(set(canonical) | set(names))


# ── HTTP (stdlib urllib only — same constraint as relay_transport) ───


def _http(
    method: str,
    url: str,
    token: str,
    body: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """One HTTP call. Returns (status, parsed_json). (0, {}) on transport error."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if idempotency_key:
        req.add_header("Idempotency-Key", idempotency_key)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            payload = {}
        return e.code, payload
    except Exception as e:
        logger.warning("bridge transport error %s %s: %s", method, url, e)
        return 0, {}


# ── State (pushed/acked ids per inbox — survives restarts) ────────────


def _load_state(inbox: str) -> Dict[str, Any]:
    p = _state_dir() / f"{inbox}.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"pushed_ids": [], "acked_to_server": [], "acked_sessions": {}}


def _save_state(inbox: str, state: Dict[str, Any]) -> None:
    for key in ("pushed_ids", "acked_to_server"):
        state[key] = state.get(key, [])[-STATE_MAX_IDS:]
    sessions = state.get("acked_sessions", {})
    if len(sessions) > STATE_MAX_IDS:  # insertion-ordered: keep newest
        state["acked_sessions"] = dict(list(sessions.items())[-STATE_MAX_IDS:])
    p = _state_dir() / f"{inbox}.json"
    tmp = p.parent / (p.name + ".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, p)


# ── Local FS helpers ──────────────────────────────────────────────────


def _local_messages(inbox: str) -> Dict[str, Tuple[Path, Dict[str, Any]]]:
    """Parse local inbox dir → {message_id: (path, message)}. Skips unparseable."""
    out: Dict[str, Tuple[Path, Dict[str, Any]]] = {}
    d = _get_relay_dir(inbox, force_fs=True)
    for f in d.glob("*.json"):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(msg, dict) and msg.get("id"):
            out[str(msg["id"])] = (f, msg)
    return out


def _atomic_write(path: Path, msg: Dict[str, Any]) -> None:
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(msg, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _safe_filename(server_msg: Dict[str, Any]) -> str:
    """Prefer the server filename (faithful mirror); fall back to <id>.json."""
    name = str(server_msg.get("_file") or "")
    if name and "/" not in name and ".." not in name and name.endswith(".json"):
        return name
    mid = str(server_msg.get("id", ""))
    if _VALID_MID_RE.match(mid):
        return f"{mid}.json"
    return f"bridge_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"


def _merge_read_state(
    local: Dict[str, Any], remote: Dict[str, Any]
) -> Tuple[bool, bool]:
    """Monotonic merge of remote read-state into *local* (mutates local).

    Returns (local_changed, server_behind) where server_behind means the
    local copy carries read-state the server lacks (→ caller acks up).
    """
    changed = False
    if remote.get("read") and not local.get("read"):
        local["read"] = True
        local["read_at"] = remote.get("read_at") or local.get("read_at")
        local["read_by"] = remote.get("read_by") or local.get("read_by")
        changed = True
    local_sessions = dict(local.get("read_by_sessions") or {})
    remote_sessions = dict(remote.get("read_by_sessions") or {})
    for sid, ts in remote_sessions.items():
        if sid not in local_sessions:
            local_sessions[sid] = ts
            changed = True
    if changed:
        local["read_by_sessions"] = local_sessions
    server_behind = bool(local.get("read")) and not bool(remote.get("read"))
    server_behind = server_behind or any(
        sid not in remote_sessions for sid in local_sessions
    )
    return changed, server_behind


# ── Sender token resolution (push needs per-role bearers) ─────────────

_warned_senders: set = set()


def _token_for_sender(sender: str) -> Optional[str]:
    """Find the bearer for *sender* in token_dir; None if absent (skip+warn once)."""
    candidates = [sender]
    canonical = resolve_canonical_inbox_name(sender)
    candidates.append(canonical)
    for name in (sender, canonical):
        if name.startswith("claude_code_"):
            candidates.append(name[len("claude_code_"):])
    seen = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        p = _token_dir() / f"relay_token_{cand}"
        if p.is_file():
            token = p.read_text(encoding="utf-8").strip()
            if token:
                return token
    if sender not in _warned_senders:
        _warned_senders.add(sender)
        logger.warning(
            "bridge push: no bearer for sender=%r in %s; messages from this "
            "sender stay local-only", sender, _token_dir(),
        )
    return None


# ── Core sync ─────────────────────────────────────────────────────────


def sync_inbox(inbox: str) -> Dict[str, Any]:
    """One pull+merge+push pass for one inbox. Returns stats; never raises."""
    stats = {
        "inbox": inbox, "pulled": 0, "merged": 0,
        "acked_up": 0, "pushed": 0, "errors": 0, "transport_down": False,
    }
    url = _relay_url()
    bearer = _bridge_bearer()

    status, resp = _http(
        "GET", f"{url}/relay/{inbox}?unread_only=false&limit={PULL_LIMIT}", bearer
    )
    if status == 0:
        stats["transport_down"] = True
        return stats
    if status != 200:
        logger.warning("bridge pull %s: HTTP %d %s", inbox, status, resp.get("error"))
        stats["errors"] += 1
        return stats

    server_msgs = {
        str(m["id"]): m
        for m in resp.get("messages", [])
        if isinstance(m, dict) and m.get("id")
    }
    local_msgs = _local_messages(inbox)
    state = _load_state(inbox)
    state_dirty = False

    # PULL: write missing, merge read-state on overlap
    local_dir = _get_relay_dir(inbox, force_fs=True)
    ack_up: List[str] = []
    session_ack_up: List[Tuple[str, str]] = []  # (mid, sid)
    for mid, smsg in server_msgs.items():
        smsg = dict(smsg)
        if mid not in local_msgs:
            fname = _safe_filename(server_msgs[mid])
            clean = {k: v for k, v in smsg.items() if k != "_file"}
            target = local_dir / fname
            if target.exists():  # filename collision with different id
                target = local_dir / f"{mid}.json"
            _atomic_write(target, clean)
            stats["pulled"] += 1
        else:
            path, lmsg = local_msgs[mid]
            changed, _ = _merge_read_state(lmsg, smsg)
            if changed:
                _atomic_write(path, lmsg)
                stats["merged"] += 1
            # Lossless ack-up bookkeeping (peer crack-1 on PR #570): coarse
            # and per-session needs are tracked SEPARATELY so a session
            # marker that appears locally after the coarse ack still
            # propagates, and a failed per-session POST is retried next
            # cycle instead of being orphaned by the coarse record.
            if (
                lmsg.get("read")
                and not smsg.get("read")
                and mid not in state.get("acked_to_server", [])
            ):
                ack_up.append(mid)
            remote_sessions = smsg.get("read_by_sessions") or {}
            acked_sessions = state.get("acked_sessions", {}).get(mid, [])
            for sid in (lmsg.get("read_by_sessions") or {}):
                if sid not in remote_sessions and sid not in acked_sessions:
                    session_ack_up.append((mid, sid))

    # ACK-up: coarse read-state the server lacks
    if ack_up:
        status, resp = _http(
            "POST", f"{url}/relay/{inbox}/ack", bearer, {"message_ids": ack_up}
        )
        if status == 200:
            stats["acked_up"] += resp.get("acked", 0)
            state.setdefault("acked_to_server", []).extend(ack_up)
            state_dirty = True
        elif status == 0:
            stats["transport_down"] = True
        else:
            stats["errors"] += 1

    # ACK-up: per-session markers (v0.2 route amendment). Recorded only on
    # confirmed success so transient failures retry next cycle (lossless).
    for mid, sid in session_ack_up:
        if stats["transport_down"]:
            break
        status, resp = _http(
            "POST", f"{url}/relay/{inbox}/ack", bearer,
            {"message_ids": [mid], "session_id": sid},
        )
        if status == 200 and resp.get("acked", 0) >= 1:
            per_mid = state.setdefault("acked_sessions", {}).setdefault(mid, [])
            if sid not in per_mid:
                per_mid.append(sid)
            state_dirty = True
        elif status == 0:
            stats["transport_down"] = True
        else:
            stats["errors"] += 1

    # PUSH: local-originated ids the server doesn't have
    pushed_ids = set(state.get("pushed_ids", []))
    now = time.time()
    for mid, (path, lmsg) in local_msgs.items():
        if mid in server_msgs or mid in pushed_ids:
            continue
        try:
            if now - path.stat().st_mtime > PUSH_MAX_AGE_S:
                continue
        except OSError:
            continue
        sender = str(lmsg.get("from") or lmsg.get("from_role") or "")
        token = _token_for_sender(sender) if sender else None
        if not token:
            continue
        payload = {
            "id": mid,
            "subject": str(lmsg.get("subject", ""))[:256],
            "body": lmsg.get("body") if isinstance(lmsg.get("body"), str)
            else json.dumps(lmsg.get("body"), default=str),
            "sender": sender,
            "priority": lmsg.get("priority", "normal"),
            "context": lmsg.get("context") or None,
            "in_reply_to": lmsg.get("in_reply_to"),
            "to_session_id": lmsg.get("to_session_id"),
            "from_session_id": lmsg.get("from_session_id"),
        }
        status, resp = _http(
            "POST", f"{url}/relay/{inbox}", token, payload, idempotency_key=mid
        )
        if status == 202 or (status == 409 and resp.get("error") == "idempotency_replay"):
            state.setdefault("pushed_ids", []).append(mid)
            state_dirty = True
            stats["pushed"] += 1
        elif status == 0:
            stats["transport_down"] = True
            break
        else:
            logger.warning(
                "bridge push %s id=%s: HTTP %d %s",
                inbox, mid[:12], status, resp.get("error"),
            )
            stats["errors"] += 1

    if state_dirty:
        _save_state(inbox, state)
    return stats


def sync_all() -> Dict[str, Any]:
    """One full pass over every bridged inbox. Never raises."""
    totals = {"pulled": 0, "merged": 0, "acked_up": 0, "pushed": 0,
              "errors": 0, "transport_down": False}
    for inbox in bridge_inboxes():
        try:
            s = sync_inbox(inbox)
        except Exception as e:  # belt-and-braces: one bad inbox never stops the loop
            logger.warning("bridge sync_inbox(%s) crashed: %s", inbox, e)
            totals["errors"] += 1
            continue
        for k in ("pulled", "merged", "acked_up", "pushed", "errors"):
            totals[k] += s[k]
        totals["transport_down"] = totals["transport_down"] or s["transport_down"]
    return totals


# ── Engram sync (background, composed on the sync module) ─────────────


def _engram_sync_enabled() -> bool:
    """Engram sync is opt-in via env, auto-on when NUCLEUS_SYNC_URL is set."""
    flag = os.environ.get("NUCLEUS_BRIDGE_ENGRAM_SYNC", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    # Auto-on when the operator has explicitly set a sync URL
    return bool(os.environ.get("NUCLEUS_SYNC_URL", "").strip())


def sync_engrams() -> Dict[str, Any]:
    """One engram sync pass via the sync module. Returns stats; never raises.

    Composes ``sync.perform_sync_cycle`` (daemon-safe, no stdout). The
    engram sync endpoint is heavier than the relay message bus, so this
    runs on its own slower cadence (see ``DEFAULT_ENGRAM_SYNC_INTERVAL_S``)
    — not every relay cycle.
    """
    if not _engram_sync_enabled():
        return {"skipped": True, "reason": "disabled"}
    try:
        from ...sync import perform_sync_cycle
    except ImportError as e:
        logger.warning("bridge: sync module unavailable: %s", e)
        return {"skipped": True, "reason": "import_error"}
    try:
        stats = perform_sync_cycle()
    except Exception as e:  # never let engram sync crash the relay loop
        logger.warning("bridge: engram sync crashed: %s", e)
        return {"ok": False, "error": str(e), "transport_down": False}
    if stats.get("ok"):
        logger.info(
            "bridge engram sync: pushed=%d received=%d applied=%d conflicts=%d",
            stats.get("pushed", 0), stats.get("received", 0),
            stats.get("applied", 0), stats.get("conflicts", 0),
        )
    elif stats.get("error"):
        logger.warning("bridge engram sync error: %s", stats["error"])
    return stats


def run_loop(interval_s: float = DEFAULT_INTERVAL_S) -> None:
    """Poll-and-mirror forever. Exponential backoff while OCI is unreachable.

    Engram sync runs on its own slower cadence
    (``DEFAULT_ENGRAM_SYNC_INTERVAL_S``) interleaved with the relay loop.
    """
    backoff = interval_s
    last_engram_sync = 0.0
    engram_interval = DEFAULT_ENGRAM_SYNC_INTERVAL_S
    while True:
        totals = sync_all()
        if totals["transport_down"]:
            backoff = min(backoff * 2, BACKOFF_MAX_S)
            logger.info("bridge: relay unreachable; backing off %.0fs", backoff)
        else:
            if backoff != interval_s:
                logger.info("bridge: relay recovered; resuming %.0fs cadence", interval_s)
            backoff = interval_s
            if any(totals[k] for k in ("pulled", "merged", "acked_up", "pushed")):
                logger.info(
                    "bridge cycle: pulled=%d merged=%d acked_up=%d pushed=%d",
                    totals["pulled"], totals["merged"],
                    totals["acked_up"], totals["pushed"],
                )

        # Engram sync on its own cadence (not every relay cycle)
        now = time.time()
        if _engram_sync_enabled() and (now - last_engram_sync) >= engram_interval:
            es = sync_engrams()
            if es.get("transport_down"):
                # Don't reset the engram timer on transport failure —
                # retry next eligible cycle so a brief outage doesn't
                # push the next attempt out by a full interval.
                pass
            else:
                last_engram_sync = now

        time.sleep(backoff)


# ── Startup preflight: half-mirror / dead-remote detection (opt-in) ───
#
# Flag NUCLEUS_BRIDGE_PREFLIGHT (default OFF). The sync loop is deliberately
# offline-tolerant — a transient-unreachable remote just backs off and the Mac
# syncs on recovery (module docstring "Never crashes"). That same tolerance,
# though, silently swallows a genuinely MISCONFIGURED remote: with
# NUCLEUS_RELAY_URL set, relay_post routes over HTTP (core.relay_post →
# is_http_mode), so a dead URL or a bearer the remote rejects (401) is a
# one-way / half-mirror where local posts leave but are never reconciled —
# messages are black-holed with no signal. relay/paths.py:42 already records
# that the server IS the FS authority even under NUCLEUS_RELAY_URL; this gate
# is the client-side dual: when the operator opts in, probe the remote ONCE at
# startup and RAISE a hard, actionable error rather than ghost mail.
#
# Flag OFF ⇒ never called ⇒ startup byte-identical to today (the loop keeps its
# offline-tolerant contract). Flag ON is a conscious strictness opt-in.

_PREFLIGHT_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _preflight_enabled() -> bool:
    """True iff ``NUCLEUS_BRIDGE_PREFLIGHT`` is set truthy (default False)."""
    return os.environ.get("NUCLEUS_BRIDGE_PREFLIGHT", "").strip().lower() in _PREFLIGHT_TRUTHY


class BridgeConfigError(RuntimeError):
    """Startup config is a half-mirror / dead-remote that would black-hole mail."""


def preflight_check() -> None:
    """Probe the configured remote once; raise ``BridgeConfigError`` on a bad config.

    Called only when ``NUCLEUS_BRIDGE_PREFLIGHT`` is enabled, and only after
    the URL/bearer presence checks pass. Classifies one lightweight GET against
    the first bridged inbox — ``GET /relay/{inbox}`` returns 200 even for an
    empty inbox (http_transport/relay_route.get_relay), so an empty mailbox is
    never a false alarm:

      * transport error (status 0)  -> dead remote (unreachable).
      * 401 / 403                   -> bearer rejected: the pull/ack leg is
        dead, so this is a one-way / half-mirror where local posts leave over
        HTTP but are never reconciled and mail is silently ghosted.
      * any other non-200           -> the relay endpoint is misconfigured.

    Every message names which env var is set, what failed, and how to fix it,
    plus the escape hatch (unset the flag) — never a silent ghost.
    """
    url = _relay_url()
    bearer = _bridge_bearer()
    inboxes = bridge_inboxes()
    probe_inbox = inboxes[0] if inboxes else "board"
    status, resp = _http(
        "GET", f"{url}/relay/{probe_inbox}?unread_only=false&limit=1", bearer
    )
    if status == 200:
        return
    if status == 0:
        raise BridgeConfigError(
            f"relay preflight: NUCLEUS_RELAY_URL={url!r} is set but the remote is "
            f"UNREACHABLE (probe GET /relay/{probe_inbox} failed at the transport "
            f"layer). With NUCLEUS_RELAY_URL set, relay_post routes over HTTP to this "
            f"remote, so a dead remote silently black-holes every message. Fix: bring "
            f"the relay service up / confirm the URL is reachable, or unset "
            f"NUCLEUS_RELAY_URL to run FS-only. Unset NUCLEUS_BRIDGE_PREFLIGHT to keep "
            f"the offline-tolerant behavior (back off and sync on recovery)."
        )
    if status in (401, 403):
        raise BridgeConfigError(
            f"relay preflight: NUCLEUS_RELAY_URL={url!r} returned HTTP {status} to the "
            f"bridge bearer (NUCLEUS_RELAY_BEARER is "
            f"{'set but rejected' if bearer else 'MISSING'}). The pull/ack leg is dead — "
            f"this is a one-way / half-mirror config: local posts leave over HTTP but "
            f"are never reconciled, so mail is silently ghosted. Fix: set "
            f"NUCLEUS_RELAY_BEARER to a token the remote accepts for GET/ACK. Unset "
            f"NUCLEUS_BRIDGE_PREFLIGHT to skip this check."
        )
    raise BridgeConfigError(
        f"relay preflight: NUCLEUS_RELAY_URL={url!r} returned HTTP {status} "
        f"(error={resp.get('error')!r}) to probe GET /relay/{probe_inbox}. The relay "
        f"endpoint is misconfigured — the bridge cannot mirror and would black-hole "
        f"mail. Fix: verify NUCLEUS_RELAY_URL points at the relay service root. Unset "
        f"NUCLEUS_BRIDGE_PREFLIGHT to skip this check."
    )


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("NUCLEUS_BRIDGE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Nucleus relay FS<->HTTP bridge")
    parser.add_argument("--once", action="store_true", help="single sync pass, then exit")
    parser.add_argument("--with-engrams", action="store_true",
                        help="also run one engram sync pass (requires NUCLEUS_SYNC_URL or NUCLEUS_BRIDGE_ENGRAM_SYNC=1)")
    parser.add_argument("--interval", type=float,
                        default=float(os.environ.get("NUCLEUS_BRIDGE_INTERVAL_S",
                                                     str(DEFAULT_INTERVAL_S))))
    args = parser.parse_args()

    if not _relay_url():
        print("NUCLEUS_RELAY_URL is required for the bridge (it IS the HTTP side).")
        return 2
    if not _bridge_bearer():
        print("NUCLEUS_RELAY_BEARER is required (pull/ack bearer).")
        return 2

    # Opt-in startup preflight (default OFF, byte-identical when unset): detect a
    # half-mirror / dead-remote config and RAISE a hard error naming the failure,
    # instead of silently ghosting mail through the offline-tolerant loop.
    if _preflight_enabled():
        preflight_check()

    if args.once:
        totals = sync_all()
        result: Dict[str, Any] = dict(totals)
        if args.with_engrams:
            result["engram_sync"] = sync_engrams()
        print(json.dumps(result))
        return 1 if totals["transport_down"] else 0
    run_loop(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
