"""Relay-sender anchor stone — PID-ancestry sender binding.

PRINCIPAL.md §G1 (0b): "relay-sender (PID-ancestry sender binding — closes
the census's forgeable ``from``)".

**Problem:** the relay envelope's ``from`` field is self-attested. A process
with a valid bearer token (stone-1.5) can post a relay claiming to be from
any session_id. The census (G1 crit-4) counts cross-vendor envelopes by
``from`` — a forgeable ``from`` means the census is gameable.

**Stone:** when ``NUCLEUS_RELAY_SENDER_ANCHOR=1``:
  - **Client-side** (:func:`stamp_sender_anchor`): before posting, look up
    the session registry for the current process's PID-ancestry. If a
    registered session is found, stamp the envelope with
    ``sender_anchor: {session_id, pid, create_time, role}``.
  - **Server-side** (:func:`verify_sender_anchor`): when the anchor is
    present, verify that ``sender_anchor.role`` matches the token owner
    (stone-1.5 already binds sender↔token; this binds sender↔session).
    When the anchor is absent and the flag is ON, reject (fail-closed).

**Flag-gated:** default OFF. When OFF, ``stamp_sender_anchor`` is a no-op
and ``verify_sender_anchor`` always returns True — byte-identical to
pre-stone behavior.

**Transport modes:**
  - **FS relay (same-machine):** client and server share the session
    registry. Full F1+F2+F3 verification — PID-ancestry is a kernel
    witness the server can re-check.
  - **HTTP relay (cross-machine):** client and server are on different
    machines. The server cannot verify the client's PID-ancestry (F2/F3)
    because it doesn't share the session registry. The bearer token
    (stone-1.5) closes the forgeable ``from`` cross-machine — F1 (role
    match) is the load-bearing check, enforced by relay_route.py before
    verify_sender_anchor is called. The client stamps
    ``sender_anchor.transport = "http"`` so the server knows to skip
    F2/F3 and rely on the bearer-token anchor.

**Forge angles (regression tests in test_relay_sender_anchor.py):**
  - F1: process with token for role A posts with ``from_session_id`` of a
    session registered to role B → rejected (role mismatch)
  - F2: process posts with a fabricated ``sender_anchor`` (no real session
    registered) → rejected (session not found in registry) [FS mode only]
  - F3: process posts with a recycled PID whose create_time doesn't match
    → rejected (create_time mismatch) [FS mode only]
  - F4: flag OFF → all envelopes accepted, no anchor required
  - F5: HTTP-mode anchor without ``sender_anchor`` → rejected (fail-closed)
  - F6: HTTP-mode anchor with role mismatch → rejected (F1 still applies)
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .registry import (
    _anchor_enabled,
    _caller_lineage,
    _pid_create_time,
    find_session_in_ancestry,
)

_ANCHOR_ENV = "NUCLEUS_RELAY_SENDER_ANCHOR"


def _sender_anchor_enabled() -> bool:
    """True when ``NUCLEUS_RELAY_SENDER_ANCHOR`` is set to a truthy value."""
    return os.environ.get(_ANCHOR_ENV, "").strip().lower() in {
        "1", "true", "on", "yes",
    }


def stamp_sender_anchor(payload: dict[str, Any]) -> dict[str, Any]:
    """Stamp a relay payload with the sender's session anchor.

    When the flag is OFF: no-op, returns payload unchanged (byte-identical).
    When the flag is ON: looks up the session registry for the current
    process's PID-ancestry. If a registered session is found, adds
    ``sender_anchor`` to the payload. If no session is found, the payload
    is returned without the anchor — the server will reject it (fail-closed).

    Args:
        payload: The relay envelope payload being prepared for POST.

    Returns:
        The payload, optionally with ``sender_anchor`` added.
    """
    if not _sender_anchor_enabled():
        return payload

    session = find_session_in_ancestry()
    if session is None:
        return payload  # no registered session — server will reject

    # Detect transport mode: if NUCLEUS_RELAY_URL is set, we're posting to
    # a remote HTTP server. The server can't verify our PID-ancestry (F2/F3)
    # cross-machine — the bearer token is the anchor in HTTP mode.
    transport = "http" if os.environ.get("NUCLEUS_RELAY_URL", "").strip() else "fs"

    anchor = {
        "session_id": session.get("session_id", ""),
        "pid": session.get("pid"),
        "create_time": session.get("create_time", ""),
        "role": session.get("role", ""),
        "transport": transport,
    }
    payload = dict(payload)
    payload["sender_anchor"] = anchor
    return payload


def verify_sender_anchor(
    payload: dict[str, Any],
    token_owner: str,
) -> tuple[bool, Optional[str]]:
    """Verify a relay payload's sender anchor server-side.

    When the flag is OFF: always returns ``(True, None)`` (byte-identical).
    When the flag is ON:
      - If ``sender_anchor`` is absent → reject (fail-closed).
      - If ``sender_anchor.role`` doesn't match ``token_owner`` (in canonical
        inbox space) → reject (role mismatch forge, F1).
      - If ``sender_anchor.session_id`` is not found in the registry → reject
        (fabricated anchor, F2).
      - If the registered session's ``create_time`` doesn't match the anchor's
        → reject (recycled PID, F3).

    Args:
        payload: The relay envelope payload from the POST body.
        token_owner: The role/sender that the bearer token maps to
            (from ``NUCLEUS_RELAY_TOKEN_MAP``).

    Returns:
        ``(ok, error_reason)`` — ``ok`` is True if the anchor is valid or
        the flag is OFF; ``error_reason`` is None on success or a string
        describing the rejection.
    """
    if not _sender_anchor_enabled():
        return True, None

    anchor = payload.get("sender_anchor")
    if not isinstance(anchor, dict):
        return False, "sender_anchor_missing"

    # F1: role mismatch — the anchor's role must match the token owner
    anchor_role = anchor.get("role", "")
    if not anchor_role:
        return False, "sender_anchor_missing_role"

    # Compare in canonical inbox space (same as relay_route.py line 601)
    from ..runtime.relay_inbox_canonical import resolve_canonical_inbox_name

    if resolve_canonical_inbox_name(anchor_role) != resolve_canonical_inbox_name(token_owner):
        return False, "sender_anchor_role_mismatch"

    # Transport mode: HTTP anchors come from remote clients whose PID-ancestry
    # can't be verified cross-machine. The bearer token (stone-1.5) closes the
    # forgeable `from` in HTTP mode — F1 above is the load-bearing check.
    # Skip F2/F3 (session registry + create_time) for HTTP-mode anchors.
    transport = anchor.get("transport", "fs")
    if transport == "http":
        return True, None  # bearer token is the anchor — F1 passed

    # F2: session must exist in the registry (FS mode — same-machine only)
    session_id = anchor.get("session_id", "")
    if not session_id:
        return False, "sender_anchor_missing_session_id"

    from .registry import _iter_envelopes

    registered = None
    for env in _iter_envelopes():
        if env.get("session_id") == session_id:
            registered = env
            break

    if registered is None:
        return False, "sender_anchor_session_not_found"

    # F3: create_time must match (kernel witness — same-machine only)
    anchor_ct = anchor.get("create_time", "")
    registered_ct = registered.get("create_time", "")
    if isinstance(registered_ct, str) and registered_ct:
        if anchor_ct != registered_ct:
            return False, "sender_anchor_create_time_mismatch"

    # F1 (deep): the registered session's role must also match
    if resolve_canonical_inbox_name(registered.get("role", "")) != resolve_canonical_inbox_name(token_owner):
        return False, "sender_anchor_session_role_mismatch"
    return True, None


__all__ = [
    "stamp_sender_anchor",
    "verify_sender_anchor",
    "_sender_anchor_enabled",
]
