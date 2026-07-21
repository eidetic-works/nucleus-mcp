"""Relay envelope builder + validator.

Implements the envelope format defined in
``docs/spec/relay_envelope_spec.md`` §2 (Required fields + Optional fields).

The envelope is a JSON object carrying coordination signals between
independent agent runtimes. This module is transport-agnostic — it only
handles the canonical JSON shape. The :class:`RelayClient` in ``client.py``
wraps the filesystem transport on top of this.
"""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "REQUIRED_FIELDS",
    "OPTIONAL_FIELDS",
    "VALID_PRIORITIES",
    "ID_PATTERN",
    "EnvelopeError",
    "build_envelope",
    "validate_envelope",
    "mint_message_id",
]

# §2.1 Required fields. Order preserved for readability.
REQUIRED_FIELDS: Tuple[str, ...] = (
    "id",
    "from",
    "to",
    "subject",
    "body",
    "priority",
    "created_at",
    "read",
    "read_at",
    "read_by",
)

# §2.2 Optional fields (with their defaults).
OPTIONAL_FIELDS: Dict[str, Any] = {
    "from_role": None,
    "from_provider": None,
    "from_session_id": None,
    "to_session_id": None,
    "in_reply_to": None,
    "context": {},
    "task_id": None,
    "project": None,
    "read_by_sessions": {},
}

# §2.1 priority enum.
VALID_PRIORITIES: Tuple[str, ...] = (
    "low",
    "normal",
    "high",
    "urgent",
    "critical",
)

# §2.1 id policy: caller-supplied ids are preserved verbatim when they match
# this charset/length window; otherwise a fresh server-minted id is produced.
ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

# §2.1 subject policy: ≤256 chars, no newlines.
_MAX_SUBJECT_LEN = 256


class EnvelopeError(ValueError):
    """Raised when an envelope is malformed (missing/invalid fields)."""


def _now_iso() -> str:
    """ISO-8601 UTC timestamp with ``Z`` suffix (spec §2.1 created_at)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def mint_message_id() -> str:
    """Mint a server-format message id: ``relay_<YYYYMMDD>_<HHMMSS>_<8hex>``.

    Matches the spec §2.1 server-minted format.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"relay_{ts}_{secrets.token_hex(4)}"


def _normalize_id(message_id: Optional[str]) -> str:
    """Return a valid envelope id.

    Caller-supplied ids that match :data:`ID_PATTERN` are preserved verbatim;
    anything else (None, empty, bad charset, wrong length) gets a fresh
    server-minted id. Matches spec §2.1.
    """
    if message_id and ID_PATTERN.match(message_id):
        return message_id
    return mint_message_id()


def build_envelope(
    *,
    sender: str,
    to: str,
    subject: str,
    body: str,
    priority: str = "normal",
    message_id: Optional[str] = None,
    from_role: Optional[str] = None,
    from_provider: Optional[str] = None,
    from_session_id: Optional[str] = None,
    to_session_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a relay envelope dict matching spec §2.

    The caller MUST supply ``sender`` (the MCP server process cannot infer
    which client is calling — spec §2.1 ``from`` is required). All other
    optional fields default to spec-compliant values.

    Args:
        sender: Sender identity string (spec ``from``).
        to: Recipient identity string.
        subject: One-line summary, ≤256 chars, no newlines.
        body: Full message body (MAY be a JSON-encoded string).
        priority: One of :data:`VALID_PRIORITIES`. Default ``normal``.
        message_id: Optional caller-supplied id. Preserved verbatim when it
            matches :data:`ID_PATTERN`; otherwise a fresh id is minted.
        from_role / from_provider / from_session_id: Optional sender metadata.
        to_session_id: Optional session-id filter.
        in_reply_to: Optional parent id this message threads to.
        context: Optional free-form structured context. Default ``{}``.
        task_id: Optional task-scoped routing key.
        project: Optional project slug for cross-project filtering.

    Returns:
        A dict containing all required + supplied optional fields, with
        server-stamped ``created_at`` and ack fields initialized to
        ``read=False, read_at=None, read_by=None, read_by_sessions={}``.

    Raises:
        EnvelopeError: If a required argument is empty or priority is invalid.
    """
    if not sender or not str(sender).strip():
        raise EnvelopeError("envelope: 'from' (sender) is required")
    if not to or not str(to).strip():
        raise EnvelopeError("envelope: 'to' is required")
    if subject is None:
        raise EnvelopeError("envelope: 'subject' is required")
    subject = str(subject)
    if "\n" in subject or "\r" in subject:
        raise EnvelopeError("envelope: 'subject' must not contain newlines")
    if len(subject) > _MAX_SUBJECT_LEN:
        raise EnvelopeError(
            f"envelope: 'subject' exceeds {_MAX_SUBJECT_LEN} chars"
        )
    if body is None:
        raise EnvelopeError("envelope: 'body' is required")
    if priority not in VALID_PRIORITIES:
        raise EnvelopeError(
            f"envelope: priority '{priority}' not in {VALID_PRIORITIES}"
        )

    env: Dict[str, Any] = {
        "id": _normalize_id(message_id),
        "from": str(sender),
        "to": str(to),
        "subject": subject,
        "body": str(body),
        "priority": priority,
        "created_at": _now_iso(),
        "read": False,
        "read_at": None,
        "read_by": None,
        # Optional fields with defaults
        "from_role": from_role,
        "from_provider": from_provider,
        "from_session_id": from_session_id,
        "to_session_id": to_session_id,
        "in_reply_to": in_reply_to,
        "context": context if context is not None else {},
        "task_id": task_id,
        "project": project,
        "read_by_sessions": {},
    }
    return env


def validate_envelope(envelope: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a dict against the relay envelope spec §2.

    Returns a tuple ``(ok, errors)``. ``ok`` is True iff the envelope has
    every required field with a non-null value of the right shape, the
    priority is in the allowed enum, and the subject has no newlines and
    is ≤256 chars. ``errors`` is the list of human-readable violations
    (empty when ``ok`` is True).

    This is the validator referenced by the SDK acceptance test
    "Envelope validator rejects missing required fields".
    """
    errors: List[str] = []
    if not isinstance(envelope, dict):
        return False, ["envelope: must be a JSON object"]

    # Required fields — must be present and non-null.
    for field in REQUIRED_FIELDS:
        if field not in envelope:
            errors.append(f"envelope: missing required field '{field}'")
            continue
        val = envelope[field]
        # read_at / read_by may legitimately be None — only require presence.
        if field in ("read_at", "read_by"):
            continue
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"envelope: required field '{field}' is empty")

    # Priority enum.
    prio = envelope.get("priority")
    if prio is not None and prio not in VALID_PRIORITIES:
        errors.append(
            f"envelope: priority '{prio}' not in {VALID_PRIORITIES}"
        )

    # Subject shape.
    subj = envelope.get("subject")
    if isinstance(subj, str):
        if "\n" in subj or "\r" in subj:
            errors.append("envelope: 'subject' must not contain newlines")
        if len(subj) > _MAX_SUBJECT_LEN:
            errors.append(
                f"envelope: 'subject' exceeds {_MAX_SUBJECT_LEN} chars"
            )

    # read must be boolean.
    if "read" in envelope and not isinstance(envelope["read"], bool):
        errors.append("envelope: 'read' must be a boolean")

    # created_at must be a string.
    ca = envelope.get("created_at")
    if ca is not None and not isinstance(ca, str):
        errors.append("envelope: 'created_at' must be an ISO-8601 string")

    return (len(errors) == 0), errors
