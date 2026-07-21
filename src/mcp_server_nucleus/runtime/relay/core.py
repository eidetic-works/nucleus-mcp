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

from ..common import get_brain_path, _project_spine_on
from ..providers import coerce_to_tuple
from ..relay_inbox_canonical import resolve_canonical_inbox_name

logger = logging.getLogger("nucleus.relay")

_RELAY_ID_RE = re.compile(r"^relay_\d{8}_\d{6}_[a-f0-9]{8}")

# Caller-supplied message_id policy (bridge push path). Filesystem-safe:
# no path separators, no whitespace, bounded length.
_CALLER_MID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

# ============================================================
# RELAY RECIPIENT CANONICALIZATION FLAG
# ============================================================
# Sender is canonicalized unconditionally at write time (resolve_canonical_
# inbox_name(sender) below), but recipient `to` historically was only
# sanitized/coerced (_sanitize_recipient, _coerce_legacy_bucket_target,
# _coerce_provider_to_role) and never run through the canonical role->inbox-dir
# map before _get_relay_dir() resolves the write directory. That gap means
# to="peer" lands in the bare .brain/relay/peer/ bucket instead of the
# canonical .brain/relay/claude_code_peer/ that watchers subscribe to (same
# class of bug for "tb" -> cc_tb and "ops" -> claude_code_operator_assistant).
#
# Default OFF: this changes live write-path routing for every role in the
# relay substrate, so it must not flip production behavior on merge. Someone
# with nucleus-lane merge authority reviews and deliberately enables it.
# Idiom mirrors NUCLEUS_PROJECT_SPINE (runtime/common.py:78-84).
_RELAY_CANONICALIZE_RECIPIENT_FLAG = "NUCLEUS_RELAY_CANONICALIZE_RECIPIENT"
_RELAY_CANONICALIZE_RECIPIENT_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _relay_canonicalize_recipient_on() -> bool:
    """True iff ``NUCLEUS_RELAY_CANONICALIZE_RECIPIENT`` is set truthy (default False)."""
    return os.environ.get(
        _RELAY_CANONICALIZE_RECIPIENT_FLAG, ""
    ).strip().lower() in _RELAY_CANONICALIZE_RECIPIENT_TRUTHY


def _is_shipped_artifact(ref: str) -> bool:
    head = str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()
    return bool(head) and not _RELAY_ID_RE.match(head)


# SHA-shaped artifact ref: 7–40 char lowercase hex (matches verify_gate._SHA_RE).
# Used only under NUCLEUS_RELAY_ARTIFACT_ANCHOR=1 to gate which refs are probeable.
_ANCHOR_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _is_shipped_artifact_anchored(ref: str, *, repo: Optional[str] = None) -> bool:
    """Anchored variant of ``_is_shipped_artifact`` (NUCLEUS_RELAY_ARTIFACT_ANCHOR=1).

    SHA-shaped refs are PROBED via ``verify_gate.consume_if_confirmed`` with
    predicate ``commit_exists`` — a fabricated/nonexistent SHA does NOT pass.
    Non-SHA refs (PR URLs, file paths) are unverifiable under anchor mode and
    do NOT count as shipped (the string check alone is insufficient evidence).

    Fails CLOSED: any probe error, UNVERIFIABLE, or REFUTED verdict → False.
    See AUDIT_FINDINGS.md row #4 (backlog D-fix seam #4).
    """
    head = str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()
    if not head or _RELAY_ID_RE.match(head):
        return False
    if not _ANCHOR_SHA_RE.match(head.lower()):
        # Non-SHA ref (PR URL, file path): unverifiable under anchor mode —
        # the string check alone is not proof of a shipped artifact.
        return False
    from ..verify_gate import consume_if_confirmed
    return consume_if_confirmed(
        assertion=f"artifact_ref {head} is a shipped commit",
        gate_predicate="commit_exists",
        evidence_refs=[head],
        repo=repo,
    )


# ── Core relay operations ─────────────────────────────────────────

def _find_message_by_id(recipient: str, msg_id: str, force_fs: bool = False) -> Optional[Path]:
    """Return the path of an existing inbox file carrying this message id, if any.

    Fast path: ids are embedded in filenames on write (``<ts>_<id>.json``), so a
    glob catches server-minted and bridge-pushed files alike. Fall back to a
    content scan for files named by other writers.
    """
    try:
        relay_dir = _get_relay_dir(recipient, force_fs=force_fs)
    except Exception:
        return None
    if not relay_dir.exists():
        return None
    # Filename match is a hint only — confirm the embedded id before declaring
    # a duplicate, else a coincidental filename tail causes a silent drop.
    hits = list(relay_dir.glob(f"*_{msg_id}.json")) + list(relay_dir.glob(f"{msg_id}.json"))
    for path in hits:
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("id") == msg_id:
                return path
        except Exception:
            continue
    for path in relay_dir.glob("*.json"):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("id") == msg_id:
                return path
        except Exception:
            continue
    return None


# ── ADR-0042 D3: relay project dimension (tag + read filter) ──────────
#
# Flag NUCLEUS_PROJECT_SPINE (default OFF). When OFF, none of these helpers
# run: writers add no `project` key (envelope bytes byte-identical to today)
# and readers evaluate no predicate (result set byte-identical). The lazy
# `runtime.project` import lives inside each helper body so the OFF path never
# touches the detection module — the same structural contract get_brain_path
# holds (XY-1 sentinel test).


def _resolve_project_slug() -> Optional[str]:
    """Writer-side project slug for cwd, or ``None`` when undetectable.

    Caller MUST guard with ``_project_spine_on()``. Returns ``None`` when cwd is
    not a detectable project (daemons, launchd-spawned processes). The writer
    then OMITS the ``project`` key entirely rather than stamping a sentinel:
    an absent key = legacy semantics by construction (surfaced + grace-warned,
    NEVER dropped). A ``"unknown"`` sentinel had no reader case → every
    project-tagged reader silently dropped it (Panel follow-up 2 refutation).
    """
    from mcp_server_nucleus.runtime.project import resolve_project

    proj = resolve_project(Path.cwd())
    return proj.slug if proj is not None else None


def _reader_project() -> Optional[str]:
    """Reader-side project slug for cwd, or ``None`` when undetectable.

    Caller MUST guard with ``_project_spine_on()``. ``None`` degrades the read
    predicate to surface-all (a reader that cannot name its own project must
    not drop anyone's mail) — never a silent cross-project block.
    """
    from mcp_server_nucleus.runtime.project import resolve_project

    proj = resolve_project(Path.cwd())
    return proj.slug if proj is not None else None


def _project_visible(
    env_project: Optional[str],
    my_project: Optional[str],
    reader_bucket: Optional[str],
) -> "tuple[bool, bool]":
    """(project, role) read predicate (ADR-0042 D3). Returns (surface, warn).

    * reader IS the board inbox                   -> surface, no warn
      (board is the cross-project broadcast inbox — no project filter). This
      check PRECEDES the legacy checks (XY-5 re-judge nit b) so an untagged
      board post surfaces WITHOUT a spurious 'legacy' grace-warn: the board is
      the broadcast channel, so an absent/foreign tag there is normal, not a
      migration signal worth warning on.
    * legacy untagged (``env_project is None``)  -> surface + warn (grace
      period; NEVER dropped — writers on old code still land here).
    * malformed tag (``""`` / int / list / …)    -> surface + warn (legacy).
      A well-formed tag is a non-empty string (a project slug or the ``"*"``
      broadcast sentinel). An empty/whitespace string, an int, a list, or any
      non-str is unmintable by any in-repo writer (writers stamp a slug str,
      ``"*"``, or omit the key), so an inbound one is hand-forged or corrupt.
      It carries no project identity, so it is treated as legacy — surfaced +
      grace-warned, NEVER routed to the mismatch-drop (XY-5 re-judge nit a).
      Same silent-drop class the ``"unknown"`` sentinel guards below.
    * sentinel ``"unknown"`` (foreign writer)    -> surface + warn (legacy).
      This seam never emits ``"unknown"`` (the writer omits the key instead),
      but a foreign/older writer might. It has no project identity, so it is
      treated as legacy: surfaced + grace-warned, NEVER routed to the
      mismatch-drop branch. "unknown" must never be droppable (Panel
      follow-up 2 — the empirically-reproduced silent-drop).
    * board broadcast (``env_project == "*"``)   -> surface, no warn.
    * reader has no project (``my_project None``) -> surface, no warn
      (cannot discriminate → safe degrade, never a silent drop).
    * same project                               -> surface, no warn.
    * otherwise (cross-project)                   -> DROP. The fashion-leak block.

    The genuine leak block (a valid slug that differs from the reader's valid
    slug) is unchanged by the nit-a/nit-b guards: both only re-route inputs no
    legitimate writer produces (board bucket, malformed tag) away from a silent
    drop — they never let a real cross-project slug through.
    """
    if reader_bucket == "board":
        return True, False
    if env_project is None:
        return True, True
    if not isinstance(env_project, str) or not env_project.strip():
        return True, True
    if env_project == "unknown":
        return True, True
    if env_project == "*":
        return True, False
    if my_project is None:
        return True, False
    if env_project == my_project:
        return True, False
    return False, False


# Process-lifetime seen-set so a busy inbox scanned on every read call doesn't
# spam the log with the same legacy envelope. Only touched on the flag-ON read
# path (via _warn_legacy_untagged); inert on the flag-OFF path.
_WARNED_LEGACY_IDS: "set[str]" = set()


def _warn_legacy_untagged(env_id: Optional[str]) -> None:
    """Grace-period warning for a surfaced legacy (untagged/unknown) envelope (D3).

    Rate-limited to once per envelope id per process (Panel follow-up 2 nit):
    the read helpers re-scan the whole bucket on every call, so an unrate-limited
    warning fired once per legacy envelope *per read call* — a busy inbox spams
    the log with the same id. The seen-set keys on the id (a fixed sentinel for
    the rare id-less envelope) so each distinct legacy envelope warns at most once.
    """
    key = env_id if env_id is not None else "<no-id>"
    if key in _WARNED_LEGACY_IDS:
        return
    _WARNED_LEGACY_IDS.add(key)
    logger.warning(
        "relay: surfacing legacy untagged envelope %s (no project field; "
        "ADR-0042 D3 grace period — surfaced, never dropped)",
        env_id,
    )


def relay_post(
    to: str,
    subject: str,
    body: str,
    priority: str = "normal",
    context: Optional[Dict[str, Any]] = None,
    sender: Optional[str] = None,
    to_session_id: Optional[str] = None,
    from_session_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    force_fs: bool = False,
    message_id: Optional[str] = None,
    task_id: Optional[str] = None,
    sender_anchor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Post a message to a target session type.

    Args:
        to: Recipient session type (e.g., "claude_code", "cowork")
        subject: Short subject line
        body: Full message body
        priority: "low", "normal", "high", "urgent"
        context: Optional structured context (file paths, task IDs, etc.)
        sender: Explicit sender identity. Required because the MCP server
                process can't distinguish which client is calling it.
                R6.1: when sender is None, raises ValueError by default.
                Set NUCLEUS_RELAY_INFER_SENDER=1 to restore the legacy
                detect_session_type() fallback (unreliable when multiple
                clients share one MCP server process — opt-in only).
        to_session_id: Optional session-ID filter. When set, only the matching
                client session will surface the message (others skip it).
                None = broadcast to all sessions of the recipient type.
        from_session_id: Optional originating session ID. Lets receivers tell
                live continuity from a stale queue.
        in_reply_to: Optional parent relay_id this message threads to.
                First-class envelope field — receivers read it off the envelope
                without parsing body JSON. Normalized on post; stored alongside
                from_session_id / to_session_id.
        message_id: Optional caller-supplied message id. Preserved verbatim
                when it matches the id charset/length policy; otherwise a
                fresh id is minted as before. If a message with the same id
                already exists in the recipient inbox, the post is a no-op
                and returns sent=True duplicate=True — this is what makes
                bridge re-push idempotent across server restarts (the
                in-memory Idempotency-Key cache does not survive restart).
        task_id: Optional task ID. When set, the message is routed to
                .brain/relay/task_comments/<task_id>/ instead of the
                recipient inbox. This makes it a task-scoped comment —
                visible to anyone working on the task, not just one agent.
                Threading via in_reply_to still works. When the task is
                DONE, the comment thread stays as a coordination record.

    Returns:
        Dict with message_id, status, and delivery path.
    """
    # PR-A v0.1 swap-point: HTTP-mode routes the entire post through
    # relay_transport.post_relay() instead of the local FS write below.
    # Spec note: wrap at top — env-var-driven mode is cleaner than threading
    # a transport argument through. Matches NUCLEUS_RELAY_STRICT pattern.
    # force_fs=True is the server-side self-recursion guard: http_transport
    # route handlers call this function, and a server process running with
    # NUCLEUS_RELAY_URL set would otherwise loop back into itself via HTTP.
    from ..relay_transport import is_http_mode, post_relay as _transport_post
    if not force_fs and is_http_mode():
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "priority": priority,
            "context": context,
            "sender": sender,
            "to_session_id": to_session_id,
            "from_session_id": from_session_id,
            "in_reply_to": in_reply_to,
            "task_id": task_id,
            "sender_anchor": sender_anchor,
        }
        if message_id:
            payload["id"] = message_id
        resp = _transport_post(payload)
        return {
            "id": resp.get("id", ""),
            "status": "sent" if resp.get("sent") else "transport_failure",
            "sent": resp.get("sent", False),
            "error": resp.get("error"),
            "to": to,
        }

    start_time = time.perf_counter()
    to = _sanitize_recipient(to)
    # Legacy-bucket intercept: coerce "claude_code" → "claude_code_main" before
    # any further processing. from_session_id may not be known yet (caller
    # passes it as a kwarg); we use what's available for log context only.
    to = _coerce_legacy_bucket_target(to, from_session_id=from_session_id)
    to = _coerce_provider_to_role(to, from_session_id=from_session_id)
    # Flag-gated recipient canonicalization (default OFF — see flag docblock
    # above). Mirrors the unconditional `sender = resolve_canonical_inbox_
    # name(sender)` call below, but for `to`: routes shorthand/alias vocab
    # ("peer", "tb", "ops") to the canonical inbox dir watchers subscribe to,
    # instead of writing into the bare-name bucket.
    if _relay_canonicalize_recipient_on():
        to = resolve_canonical_inbox_name(to) or to
    # R6.1 — provider-neutrality substrate: explicit sender is the default
    # contract. Legacy silent coercion is opt-in via env var so Gemini CLI,
    # Windsurf, Cursor, and other future clients must declare role explicitly
    # or consciously opt into inference.
    if sender is None:
        if os.environ.get("NUCLEUS_RELAY_INFER_SENDER") == "1":
            # R6.1-v2 (2026-04-24): the legacy fallback is known-unreliable
            # when multiple clients share one stdio pipe (antigravity
            # relay_20260424_053832_0fd9d451 was mis-attributed via this
            # exact path). Emit a WARNING so substrate-level mis-attribution
            # is audible in logs even on opt-in.
            caller = _caller_hint()
            sender = detect_session_role()
            logger.warning(
                "relay_post: sender coerced via detect_session_role() -> %r. "
                "NUCLEUS_RELAY_INFER_SENDER=1 is opt-in compat only; callers "
                "should pass sender= explicitly. Caller: %s",
                sender,
                caller,
            )
        else:
            raise ValueError(
                "relay_post: sender is required. Pass sender= explicitly "
                "(e.g. 'coordinator', 'worker', 'cowork', "
                "'primary', 'secondary'). Set NUCLEUS_RELAY_INFER_SENDER=1 "
                "to restore legacy detect_session_type() fallback."
            )
    # Normalize sender vocabulary at the write boundary. Unlike HTTP mode
    # (token-binding 403 backstop), FS mode has no sender validation at all,
    # so shorthand/alias vocab ('peer', 'ops', 'tb') landed raw in archives
    # and corrupted sender-keyed consumers. R6.1 unchanged: sender is still
    # required; unknown vocab passes through resolve unchanged.
    sender = resolve_canonical_inbox_name(sender)
    now = datetime.now(timezone.utc)
    if message_id and _CALLER_MID_RE.match(message_id):
        msg_id = message_id
        existing = _find_message_by_id(to, msg_id, force_fs=force_fs)
        if existing is not None:
            return {
                "sent": True,
                "duplicate": True,
                "message_id": msg_id,
                "from": sender,
                "to": to,
                "subject": subject,
                "priority": priority,
                "path": str(existing.relative_to(get_brain_path())),
            }
    else:
        if message_id:
            logger.warning(
                "relay_post: caller message_id %r rejected by id policy; minting fresh id",
                message_id,
            )
        msg_id = f"relay_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    if os.environ.get("NUCLEUS_RELAY_STRICT") == "1":
        try:
            parsed_body = json.loads(body) if isinstance(body, str) else body
            refs = parsed_body.get("artifact_refs") if isinstance(parsed_body, dict) else None
        except (json.JSONDecodeError, TypeError):
            refs = None
        if os.environ.get("NUCLEUS_RELAY_ARTIFACT_ANCHOR") == "1":
            # Anchor mode (D-fix seam #4): SHA-shaped refs must be PROBED via
            # consume_if_confirmed(commit_exists) — a fabricated SHA does NOT
            # pass. Non-SHA refs (PR URLs, file paths) are unverifiable under
            # anchor mode and do NOT count as shipped. See AUDIT_FINDINGS.md #4.
            _anchor_repo = os.environ.get("NUCLEUS_RELAY_ARTIFACT_REPO") or os.getcwd()
            _anchored = bool(refs) and any(
                _is_shipped_artifact_anchored(r, repo=_anchor_repo) for r in refs
            )
            if not _anchored:
                return {
                    "sent": False,
                    "error": "gate_rejected",
                    "reason": (
                        "NUCLEUS_RELAY_STRICT=1 + NUCLEUS_RELAY_ARTIFACT_ANCHOR=1 requires "
                        "body.artifact_refs to contain at least one commit SHA that is "
                        "CONFIRMED to exist in the repo (probed via git cat-file -e). "
                        "Non-SHA refs (PR URLs, file paths) are unverifiable under anchor "
                        "mode. Unset either env var to restore permissive behavior."
                    ),
                    "to": to,
                    "subject": subject,
                }
        elif not refs or not any(_is_shipped_artifact(r) for r in refs):
            return {
                "sent": False,
                "error": "gate_rejected",
                "reason": (
                    "NUCLEUS_RELAY_STRICT=1 requires body.artifact_refs to contain at least one "
                    "non-relay-id reference (commit SHA, PR #, or file path). "
                    "Unset the env var to restore default permissive behavior."
                ),
                "to": to,
                "subject": subject,
            }

    sender_tuple = coerce_to_tuple(sender)

    message = {
        "id": msg_id,
        "from": sender,
        "from_role": sender_tuple["role"],
        "from_provider": sender_tuple["provider"],
        "from_session_id": from_session_id or sender_tuple["session_id"],
        "to": to,
        "to_session_id": to_session_id,
        "in_reply_to": in_reply_to,
        "subject": subject,
        "body": body,
        "priority": priority,
        "context": context or {},
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "read": False,
        "read_at": None,
        "read_by": None,
        "task_id": task_id,
        # v3 anchor precondition: store the sender_anchor in the envelope so
        # the census can distinguish pre-anchor (forgeable) from post-anchor
        # (verified) envelopes. When None, the key is omitted (byte-identical
        # to pre-v3 behavior). When set, it carries the transport, session_id,
        # pid, create_time, and role that the server verified.
        **({"sender_anchor": sender_anchor} if sender_anchor else {}),
        # Phase A3: per-session ack tracker. Maps session_id → iso_ts of ack.
        # Shared buckets (multiple Cowork sessions, multiple CC-peer sessions)
        # need per-session unread to avoid one session hiding a relay from peers.
        # Legacy `read`/`read_at`/`read_by` remain for coarse-grained consumers
        # (relay_status, pending.json, morning brief) — they mean "any session
        # has acked this."
        "read_by_sessions": {},
    }

    # ADR-0042 D3 stamp (flag NUCLEUS_PROJECT_SPINE, default OFF). Adds the
    # `project` dimension so readers can filter (project, role). `board` is the
    # cross-project broadcast channel (project="*"). Flag OFF ⇒ this key is
    # never added ⇒ the envelope is byte-identical to pre-spine. FS is the
    # transport of record for repo-local project brains (D4); the HTTP client
    # leg short-circuits above (before this dict exists) and the remote server
    # re-stamps on FS landing via the force_fs re-entry.
    if _project_spine_on():
        if resolve_canonical_inbox_name(to) == "board":
            message["project"] = "*"
        else:
            slug = _resolve_project_slug()
            # No-sentinel rule (Panel follow-up 2): when cwd is not a detectable
            # project, OMIT the key. Absent key = legacy (surfaced + grace-warned,
            # never dropped). Stamping "unknown" here had no reader case and
            # silently dropped the envelope on every project-tagged reader.
            if slug is not None:
                message["project"] = slug

    # Metrics: count queued messages
    try:
        from ..prometheus import inc_relay_message
        inc_relay_message("queued")
    except Exception:
        pass

    # Write to recipient's mailbox. force_fs threads through so the server
    # (FS authority) still mkdirs even when it runs with NUCLEUS_RELAY_URL set.
    # When task_id is set, route to the task-scoped comment bucket instead of
    # the agent inbox — task comments are visible to anyone working on the task.
    if task_id:
        base = get_brain_path() / "relay" / "task_comments" / task_id
        if force_fs or not is_http_mode():
            base.mkdir(parents=True, exist_ok=True)
        relay_dir = base
    else:
        relay_dir = _get_relay_dir(to, force_fs=force_fs)
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{msg_id}.json"
    path = relay_dir / filename
    # Atomic write: stage to a sibling .tmp (never matches the readers' "*.json"
    # glob), then os.replace() — atomic on POSIX and Windows. Prevents a
    # subscriber from reading a half-written file and permanently dropping the
    # message on a parse failure.
    tmp_path = relay_dir / f".{filename}.tmp"
    tmp_path.write_text(json.dumps(message, indent=2, default=str), encoding="utf-8")
    os.replace(tmp_path, path)

    # Implicit ACK on Reply: mark parent message as read by the sender
    if in_reply_to:
        try:
            relay_ack(in_reply_to, recipient=sender, session_id=from_session_id)
        except Exception: pass

    # Coord-event capture (Phase B). Best-effort; never breaks relay flow.
    try:
        from . import coord_events as _ce
        _ce.emit(
            event_type="relay_fired",
            agent=sender or "unknown",
            session_id=from_session_id or "unknown",
            context_summary=f"relay to {to}: {subject[:80]}",
            chosen_option=msg_id,
            tags=[priority] if priority else [],
        )
    except Exception:
        pass

    # Marketplace reputation capture (Atom 1). Best-effort — never blocks relay.
    try:
        if sender:
            from ..marketplace import ReputationSignals
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            ReputationSignals.record_interaction(
                to_address=f"{sender}@nucleus",
                from_address="relay_bus",
                latency_ms=elapsed_ms,
                success=True,
            )
    except Exception as _rep_exc:
        logger.warning("relay_post: reputation record skipped for %s: %s", sender, _rep_exc)

    return {
        "sent": True,
        "message_id": msg_id,
        "from": sender,
        "to": to,
        "subject": subject,
        "priority": priority,
        "path": str(path.relative_to(get_brain_path())),
    }


def relay_inbox(
    unread_only: bool = True,
    limit: int = 20,
    recipient: Optional[str] = None,
    session_id: Optional[str] = None,
    force_fs: bool = False,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read messages addressed to the current session type.

    Args:
        unread_only: If True, only return unread messages.
        limit: Max messages to return (newest first).
        recipient: Override auto-detected session type.
        session_id: Per-session unread filter (Phase A3). When provided AND
            `unread_only=True`, a message is considered unread if THIS session
            hasn't acked it — read_by_sessions[session_id] is absent. This
            prevents one session from hiding a relay from its peers in a
            shared bucket (e.g., two Cowork sessions). When omitted, legacy
            coarse-grained `read` flag is used (back-compat).
        task_id: When set, read from the task-scoped comment bucket
            (.brain/relay/task_comments/<task_id>/) instead of the
            agent inbox. Returns all comments for the task, newest first.
            unread_only is ignored for task comments (all comments returned).

    Returns:
        Dict with messages list and metadata.
    """
    me = recipient or detect_session_role()

    # Task-scoped comment bucket: read from .brain/relay/task_comments/<task_id>/
    # Returns all comments (unread_only ignored — comments are coordination
    # records, not notifications to ack).
    if task_id:
        comment_dir = get_brain_path() / "relay" / "task_comments" / task_id
        if not comment_dir.exists():
            return {
                "messages": [],
                "count": 0,
                "task_id": task_id,
                "unread_only": False,
            }
        candidates = sorted(comment_dir.glob("*.json"), key=lambda p: p.name, reverse=True)
        messages = []
        for f in candidates:
            if len(messages) >= limit:
                break
            try:
                msg = _parse_relay_message(f)
                msg["_file"] = f.name
                messages.append(msg)
            except Exception:
                continue
        return {
            "messages": messages,
            "count": len(messages),
            "task_id": task_id,
            "unread_only": False,
        }

    # PR-A v0.1 swap-point: HTTP-mode bypasses the FS glob loop entirely.
    # relay_transport.read_inbox handles canonical resolution at the boundary;
    # returns a list of envelope dicts in same shape the FS path constructs
    # via _parse_relay_message. Defensive empty list on transport failure.
    # force_fs=True is the server-side self-recursion guard (see relay_post).
    from ..relay_transport import is_http_mode, read_inbox as _transport_read
    if not force_fs and is_http_mode():
        messages = _transport_read(me, unread_only=unread_only, limit=limit)
        return {
            "messages": messages,
            "count": len(messages),
            "recipient": me,
            "unread_only": unread_only,
            "transport": "http",
            # Truth-in-signaling: surface InboxResult attributes so callers
            # can tell an empty inbox from truncation / backoff / failure.
            "has_more": getattr(messages, "has_more", False),
            "rate_limited": getattr(messages, "rate_limited", False),
            "transport_error": getattr(messages, "transport_error", False),
        }

    dirs = _iter_inbox_dirs(me)

    # Collect candidate files across all dirs (main dual-reads legacy bucket)
    candidates: List[Path] = []
    for d in dirs:
        candidates.extend(d.glob("*.json"))
    candidates.sort(key=lambda p: p.name, reverse=True)

    # ADR-0042 D3 (flag-gated): compute the reader's project once so the
    # (project, role) predicate can drop cross-project envelopes that share this
    # role bucket (the fashion-leak block). Flag OFF ⇒ never computed, predicate
    # never evaluated, result set byte-identical to today.
    _spine_on = _project_spine_on()
    _my_proj = _reader_project() if _spine_on else None
    _reader_bucket = resolve_canonical_inbox_name(me) if _spine_on else None

    messages = []
    for f in candidates:
        if len(messages) >= limit:
            break
        try:
            msg = _parse_relay_message(f)
            if _spine_on:
                surface, warn = _project_visible(
                    msg.get("project"), _my_proj, _reader_bucket
                )
                if warn:
                    _warn_legacy_untagged(msg.get("id"))
                if not surface:
                    continue
            if unread_only:
                if session_id:
                    # Per-session filter: unread iff THIS session hasn't acked.
                    read_by_sessions = msg.get("read_by_sessions") or {}
                    if session_id in read_by_sessions:
                        continue
                else:
                    # Legacy coarse-grained filter.
                    if msg.get("read", False):
                        continue
            msg["_file"] = f.name
            messages.append(msg)
        except Exception:
            continue

    return {
        "recipient": me,
        "messages": messages,
        "count": len(messages),
        "unread_only": unread_only,
        "session_id": session_id,
    }


def relay_context_sync(
    recipient: Optional[str] = None,
    max_cycles: int = 3,
) -> Dict[str, Any]:
    """Checkpoint-optimized relay loader for session-start sync.
    
    Mitigates context window fragmentation as the org scales to 7+ agents by
    slicing full relay history down to a bounded context window.
    
    A 'cycle' is approximated by a calendar day of activity (YYYYMMDD) parsed
    from the relay message filename (e.g., 20260427_170505...).
    
    Args:
        recipient: Override auto-detected session type.
        max_cycles: Number of distinct activity cycles (days) to load history for.
        
    Returns:
        Dict with 'active_decisions' and 'recent_history' messages.
    """
    me = recipient or detect_session_role()

    # PR-A v0.1 swap-point: HTTP-mode reads via relay_transport with broader
    # unread_only=False to capture history (mirror relay_inbox pattern).
    # Limit 200 per spec note. Session-start sync degenerates to a flat
    # recent_history list when no FS-based cycle bucketing is available.
    # NOT force_fs-threaded: no HTTP route dispatches relay_context_sync
    # (MCP tools/sync.py only). If a future route handler calls this,
    # thread force_fs first or the server self-recurses over HTTP.
    from ..relay_transport import is_http_mode, read_inbox as _transport_read
    if is_http_mode():
        messages = _transport_read(me, unread_only=False, limit=200)
        return {
            "active_decisions": [],
            "recent_history": messages,
            "cycles_loaded": 0,
            "recipient": me,
            "transport": "http",
            # Truth-in-signaling: previously the server clamped limit below
            # this 200 ask and the truncation was silent. has_more is now
            # surfaced so session-start sync can tell "complete history"
            # from "server returned a truncated page".
            "has_more": getattr(messages, "has_more", False),
            "transport_error": getattr(messages, "transport_error", False),
        }

    dirs = _iter_inbox_dirs(me)

    # Collect candidate files across all dirs
    candidates: List[Path] = []
    for d in dirs:
        candidates.extend(d.glob("*.json"))
    candidates.sort(key=lambda p: p.name, reverse=True)

    active_decisions = []
    recent_history = []

    seen_cycles = set()

    # ADR-0042 D3 (flag-gated): same (project, role) predicate as relay_inbox so
    # the session-start history loader can't replay cross-project envelopes.
    _spine_on = _project_spine_on()
    _my_proj = _reader_project() if _spine_on else None
    _reader_bucket = resolve_canonical_inbox_name(me) if _spine_on else None

    for f in candidates:
        try:
            msg = _parse_relay_message(f)
            if _spine_on:
                surface, warn = _project_visible(
                    msg.get("project"), _my_proj, _reader_bucket
                )
                if warn:
                    _warn_legacy_untagged(msg.get("id"))
                if not surface:
                    continue
            msg["_file"] = f.name

            # Identify active decisions (high signal, always load)
            subject = str(msg.get("subject", "")).lower()
            tags = msg.get("tags", [])
            body = msg.get("body", {})
            if isinstance(body, dict):
                tags.extend(body.get("tags", []))
            tags_lower = [str(t).lower() for t in tags]
            
            # Active decisions are typically unread directives or explicit decisions
            is_active_decision = (
                "decision" in subject or 
                "directive" in subject or 
                "decision" in tags_lower or 
                "directive" in tags_lower
            ) and not msg.get("read", False)
            
            # Determine cycle (date-based: YYYYMMDD from filename)
            # Standard relay filename: relay_YYYYMMDD_HHMMSS_id.json or YYYYMMDD_HHMMSS_...json
            parts = f.name.split("_")
            cycle_id = "unknown"
            for part in parts:
                if part.isdigit() and len(part) == 8:
                    cycle_id = part
                    break
            
            # Add to active decisions if flagged
            if is_active_decision:
                active_decisions.append(msg)
            
            # Add to recent history if within cycle limit
            if cycle_id not in seen_cycles:
                if len(seen_cycles) >= max_cycles and cycle_id != "unknown":
                    continue  # We hit the limit for known cycles
                if cycle_id != "unknown":
                    seen_cycles.add(cycle_id)
            
            if len(seen_cycles) <= max_cycles or cycle_id == "unknown":
                recent_history.append(msg)
            
        except Exception:
            continue

    return {
        "status": "success",
        "active_decisions": active_decisions,
        "recent_history": recent_history,
        "cycles_loaded": len(seen_cycles),
        "total_messages": len(active_decisions) + len(recent_history),
        "recipient": me,
    }


def relay_read(
    message_id: str,
    recipient: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read a specific message and mark it as read.

    Args:
        message_id: The ID of the relay message to read.
        recipient: Override auto-detected session type.
        session_id: Per-session ack (Phase A3).
    """
    me = recipient or detect_session_role()

    # PR-A v0.1 swap-point: HTTP-mode routes the ack through
    # relay_transport.mark_seen with a single-element list. Returns a
    # shape-matching dict so callers don't branch.
    # NOT force_fs-threaded: no HTTP route dispatches relay_read (MCP
    # tools/sync.py only). If a future route handler calls this, thread
    # force_fs first or the server self-recurses over HTTP.
    from ..relay_transport import is_http_mode, mark_seen as _transport_ack
    if is_http_mode():
        resp = _transport_ack(me, [message_id])
        return {
            "id": message_id,
            "read": resp.get("acked", 0) > 0,
            "acked_via": "http",
            "error": resp.get("error"),
        }

    for d in _iter_inbox_dirs(me):
        for f in d.glob("*.json"):
            try:
                msg = _parse_relay_message(f)
                if msg.get("id") == message_id:
                    # ADR-0042 D3 belt (flag-gated): a cross-project envelope
                    # sharing this bucket is not in *my* inbox — skip so an
                    # id-targeted fetch can't reach across projects.
                    if _project_spine_on():
                        surface, warn = _project_visible(
                            msg.get("project"),
                            _reader_project(),
                            resolve_canonical_inbox_name(me),
                        )
                        if warn:
                            _warn_legacy_untagged(msg.get("id"))
                        if not surface:
                            continue
                    # Mark as read
                    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    msg["read"] = True
                    msg["read_at"] = now_iso
                    msg["read_by"] = me
                    if session_id:
                        read_by_sessions = msg.get("read_by_sessions") or {}
                        read_by_sessions[session_id] = now_iso
                        msg["read_by_sessions"] = read_by_sessions
                    
                    f.write_text(json.dumps(msg, indent=2, default=str), encoding="utf-8")

                    # Project to engram
                    try:
                        from .relay_engram_projection import project_relay_to_engram
                        project_relay_to_engram(msg)
                    except Exception: pass

                    # Coord-event capture (Phase B receive-side). Closes ack-latency loop
                    # for cross-trio observability dashboard. Best-effort.
                    try:
                        from . import coord_events as _ce
                        _ce.emit(
                            event_type="relay_processed",
                            agent=me or "unknown",
                            session_id=session_id or "unknown",
                            context_summary=f"relay processed: {str(msg.get('subject',''))[:80]}",
                            chosen_option=message_id,
                            tags=["read_message"],
                        )
                    except Exception: pass

                    return {
                        "success": True,
                        "message": msg,
                        "acknowledged": True
                    }
            except Exception:
                continue

    return {"success": False, "error": f"Message {message_id} not found in {me} inbox"}


def relay_ack(
    message_id: str,
    recipient: Optional[str] = None,
    session_id: Optional[str] = None,
    force_fs: bool = False,
) -> Dict[str, Any]:
    """Acknowledge / mark a message as read.

    Args:
        message_id: The relay message ID to acknowledge.
        recipient: Override auto-detected session type.
        session_id: Per-session ack (Phase A3). When provided, records this
            session's ack in `read_by_sessions[session_id]` so peer sessions
            sharing the bucket still see the message as unread. The legacy
            coarse-grained `read`/`read_at`/`read_by` fields are always
            updated too, so `relay_status`, `pending.json`, and the morning
            brief continue to report "any-session acked" semantics.

    Returns:
        Dict with acknowledgment status.
    """
    me = recipient or detect_session_role()

    # PR-A v0.1 swap-point: HTTP-mode routes via relay_transport.mark_seen
    # with single-element list (same as relay_read swap). Returns shape-
    # matching dict; FS path unchanged.
    # force_fs=True is the server-side self-recursion guard (see relay_post).
    from ..relay_transport import is_http_mode, mark_seen as _transport_ack
    if not force_fs and is_http_mode():
        resp = _transport_ack(me, [message_id])
        return {
            "id": message_id,
            "acked": resp.get("acked", 0) > 0,
            "acked_via": "http",
            "error": resp.get("error"),
        }

    # Dual-read: main can ack messages that landed in legacy claude_code/ bucket
    for d in _iter_inbox_dirs(me):
        for f in d.glob("*.json"):
            try:
                msg = _parse_relay_message(f)
                if msg.get("id") == message_id:
                    # ADR-0042 D3 belt (flag-gated): don't ack another project's
                    # envelope that happens to share this role bucket.
                    if _project_spine_on():
                        surface, warn = _project_visible(
                            msg.get("project"),
                            _reader_project(),
                            resolve_canonical_inbox_name(me),
                        )
                        if warn:
                            _warn_legacy_untagged(msg.get("id"))
                        if not surface:
                            continue
                    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    msg["read"] = True
                    msg["read_at"] = now_iso
                    msg["read_by"] = me
                    if session_id:
                        read_by_sessions = msg.get("read_by_sessions") or {}
                        read_by_sessions[session_id] = now_iso
                        msg["read_by_sessions"] = read_by_sessions
                    f.write_text(json.dumps(msg, indent=2, default=str), encoding="utf-8")
                    # Metrics: count acked messages
                    try:
                        from ..prometheus import inc_relay_message
                        inc_relay_message("acked")
                    except Exception:
                        pass
                    try:
                        from .relay_engram_projection import project_relay_to_engram
                        project_relay_to_engram(msg)
                    except Exception as exc:
                        logger.debug("relay engram projection skipped: %s", exc)

                    # Coord-event capture (Phase B receive-side). Best-effort.
                    try:
                        from . import coord_events as _ce
                        _ce.emit(
                            event_type="relay_processed",
                            agent=me or "unknown",
                            session_id=session_id or "unknown",
                            context_summary=f"relay processed: {str(msg.get('subject',''))[:80]}",
                            chosen_option=message_id,
                            tags=["relay_ack"],
                        )
                    except Exception: pass

                    return {
                        "acknowledged": True,
                        "message_id": message_id,
                        "read_by": me,
                        "session_id": session_id,
                    }
            except Exception:
                continue

    return {
        "acknowledged": False,
        "message_id": message_id,
        "error": f"Message not found in {me} inbox",
    }


def relay_status(force_fs: bool = False) -> Dict[str, Any]:
    """Get relay status across all session types.

    Shows pending/unread counts per recipient, recent activity,
    and detected session types with messages.
    """
    # PR-A swap-point (v0.2): per spec §"Swap points" table — "http_mode:
    # call GET /relay/{role}/status per known role". Known roles come from
    # the canonical SSOT (CANONICAL_ROLE_TO_INBOX_DIR values, deduped), so
    # HTTP-mode status covers the canonical fleet inboxes. FS-mode scans ALL
    # on-disk dirs including non-canonical legacy variants; the narrower
    # canonical universe here is deliberate.
    # force_fs=True is the server-side self-recursion guard (see relay_post):
    # the server's own /relay/{role}/status route needs the authoritative FS
    # stats below, not this HTTP fan-out (which would recurse).
    from ..relay_transport import is_http_mode, get_status
    if not force_fs and is_http_mode():
        from ..relay_inbox_canonical import CANONICAL_ROLE_TO_INBOX_DIR

        status: Dict[str, Any] = {
            "current_session_type": detect_session_role(),
            "mailboxes": {},
            "total_messages": 0,
            "total_unread": 0,
            "transport": "http",
        }
        errors = 0
        for canonical in sorted(set(CANONICAL_ROLE_TO_INBOX_DIR.values())):
            result = get_status(canonical)
            if not result.get("ok"):
                # Connection-level failure hits every subsequent role too —
                # bail after the first so a dead server costs one timeout,
                # not one per fleet inbox.
                if result.get("error") == "transport_failure":
                    status["transport_error"] = True
                    break
                errors += 1
                continue
            total = int(result.get("queue_depth", 0) or 0)
            unread = int(result.get("unread", 0) or 0)
            status["mailboxes"][canonical] = {
                "total": total,
                "unread": unread,
                # Server /status doesn't expose per-message timestamps;
                # keep the FS mailbox shape with an honest None.
                "latest_message_at": None,
            }
            status["total_messages"] += total
            status["total_unread"] += unread
        if errors:
            status["status_errors"] = errors
        return status

    # force_fs threads through so base.iterdir() below can't hit a missing
    # dir on a server running with NUCLEUS_RELAY_URL set (mkdir is skipped
    # in plain HTTP-mode).
    base = _get_relay_dir(force_fs=force_fs)
    status: Dict[str, Any] = {
        "current_session_type": detect_session_role(),
        "mailboxes": {},
        "total_messages": 0,
        "total_unread": 0,
    }

    # ADR-0042 D3 (flag-gated): count only what this reader can see, else the
    # pending/unread totals leak cross-project. Flag OFF ⇒ no predicate, counts
    # byte-identical to today.
    _spine_on = _project_spine_on()
    _my_proj = _reader_project() if _spine_on else None

    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        recipient = d.name
        total = 0
        unread = 0
        latest = None
        _reader_bucket = (
            resolve_canonical_inbox_name(recipient) if _spine_on else None
        )

        for f in d.glob("*.json"):
            try:
                msg = _parse_relay_message(f)
                if _spine_on:
                    surface, warn = _project_visible(
                        msg.get("project"), _my_proj, _reader_bucket
                    )
                    if warn:
                        _warn_legacy_untagged(msg.get("id"))
                    if not surface:
                        continue
                total += 1
                if not msg.get("read", False):
                    unread += 1
                created = msg.get("created_at", "")
                if latest is None or created > latest:
                    latest = created
            except Exception:
                total += 1  # count but can't parse

        status["mailboxes"][recipient] = {
            "total": total,
            "unread": unread,
            "latest_message_at": latest,
        }
        status["total_messages"] += total
        status["total_unread"] += unread

    return status


def relay_clear(
    recipient: Optional[str] = None,
    older_than_hours: int = 168,  # 7 days default
) -> Dict[str, Any]:
    """Clean up old relay messages.

    Args:
        recipient: Target mailbox to clean (None = all).
        older_than_hours: Delete messages older than this (default 7 days).

    Returns:
        Dict with cleanup results.
    """
    base = _get_relay_dir()
    cutoff = datetime.now(timezone.utc).timestamp() - (older_than_hours * 3600)
    deleted = 0
    errors = 0

    dirs = [base / recipient] if recipient else [d for d in base.iterdir() if d.is_dir()]

    for d in dirs:
        for f in d.glob("*.json"):
            try:
                msg = _parse_relay_message(f)
                created = msg.get("created_at", "")
                if created:
                    msg_time = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                    if msg_time < cutoff:
                        f.unlink()
                        deleted += 1
            except Exception:
                errors += 1

    return {
        "deleted": deleted,
        "errors": errors,
        "older_than_hours": older_than_hours,
    }





# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .paths import *
from .instrumentation import *
from .pending import *
from .briefing import *
from .watcher import *
from .daemon import *
