"""RelayClient — minimal client for the relay envelope protocol.

Three methods (spec task g4_relay_sdk_python):
    - ``post(to, subject, body, priority="normal")`` — build + write an envelope
    - ``read(bucket=None)`` — list messages in a bucket
    - ``ack(message_id)`` — mark a message read

The default transport is the filesystem mailbox (spec §3.1): envelopes are
written atomically to ``<brain>/relay/<recipient>/<ts>_<id>.json``. The
client is transport-agnostic at the API surface — a future HTTP transport
can be slotted in behind the same three methods.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .envelope import build_envelope, validate_envelope, EnvelopeError

__all__ = ["RelayClient"]


def _default_brain_path() -> Path:
    """Resolve the brain path from env or fall back to repo-local ``.brain``.

    Honors ``NUCLEUS_BRAIN_PATH`` (matches the rest of the nucleus stack).
    Falls back to ``./.brain`` relative to CWD so the SDK works standalone
    in any repo that follows the relay mailbox convention.
    """
    env = os.environ.get("NUCLEUS_BRAIN_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd() / ".brain"


class RelayClient:
    """Minimal client for the relay envelope protocol.

    Args:
        sender: Sender identity string (spec ``from``). Required — the
            MCP server process cannot infer which client is calling.
        brain_path: Optional override for the brain root. Defaults to
            ``NUCLEUS_BRAIN_PATH`` env var or ``./.brain``.
        from_role / from_provider / from_session_id: Optional sender
            metadata stamped onto every envelope built by this client.
    """

    def __init__(
        self,
        sender: str,
        *,
        brain_path: Optional[os.PathLike] = None,
        from_role: Optional[str] = None,
        from_provider: Optional[str] = None,
        from_session_id: Optional[str] = None,
    ) -> None:
        if not sender or not str(sender).strip():
            raise ValueError("RelayClient: sender is required")
        self.sender = str(sender)
        self.from_role = from_role
        self.from_provider = from_provider
        self.from_session_id = from_session_id
        self.brain_path = Path(brain_path).resolve() if brain_path else _default_brain_path()

    # ------------------------------------------------------------------ post

    def post(
        self,
        to: str,
        subject: str,
        body: str,
        priority: str = "normal",
        *,
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a valid envelope and atomically write it to the recipient inbox.

        Returns a dict with ``id``, ``status="sent"``, ``sent=True``, and
        ``path`` (the on-disk envelope path). Raises :class:`EnvelopeError`
        if the envelope fails validation.
        """
        envelope = build_envelope(
            sender=self.sender,
            to=to,
            subject=subject,
            body=body,
            priority=priority,
            message_id=message_id,
            from_role=self.from_role,
            from_provider=self.from_provider,
            from_session_id=self.from_session_id,
            in_reply_to=in_reply_to,
            context=context,
            task_id=task_id,
        )
        ok, errors = validate_envelope(envelope)
        if not ok:
            raise EnvelopeError("; ".join(errors))

        path = self._write_envelope(envelope)
        return {
            "id": envelope["id"],
            "status": "sent",
            "sent": True,
            "to": to,
            "path": str(path),
            "envelope": envelope,
        }

    # ------------------------------------------------------------------ read

    def read(self, bucket: Optional[str] = None) -> List[Dict[str, Any]]:
        """List messages in a bucket (recipient inbox).

        Args:
            bucket: Recipient inbox name (e.g. ``"claude_code_main"``).
                When ``None``, lists every envelope across all buckets
                under ``<brain>/relay/``.

        Returns:
            A list of envelope dicts, newest-first by filename (which
            encodes the timestamp per spec §3.1).
        """
        if bucket:
            inbox_dir = self.brain_path / "relay" / bucket
            return self._read_dir(inbox_dir)
        # No bucket → scan all recipient inboxes.
        relay_root = self.brain_path / "relay"
        if not relay_root.exists():
            return []
        out: List[Dict[str, Any]] = []
        for sub in sorted(relay_root.iterdir()):
            if sub.is_dir():
                out.extend(self._read_dir(sub))
        # Sort by filename desc (newest first).
        out.sort(key=lambda m: m.get("_filename", ""), reverse=True)
        return out

    # ------------------------------------------------------------------ ack

    def ack(self, message_id: str) -> Dict[str, Any]:
        """Mark a message as read (coarse-grained ack, spec §2.1 ``read``).

        Updates ``read=True``, ``read_at`` (ISO-8601 UTC), ``read_by`` (this
        client's sender). Idempotent — acking an already-read message is a
        no-op that still returns ``acked=True``.

        Returns a dict with ``acked=True`` and the updated envelope, or
        ``acked=False`` with an ``error`` if the message was not found.
        """
        from datetime import datetime, timezone

        found_path: Optional[Path] = None
        found_env: Optional[Dict[str, Any]] = None
        for env in self.read():
            if env.get("id") == message_id:
                found_env = env
                found_path = Path(env.get("_path", ""))
                break

        if not found_path or not found_path.exists() or found_env is None:
            return {"acked": False, "error": f"message {message_id!r} not found"}

        # Idempotent: if already read by us, no-op.
        if found_env.get("read") and found_env.get("read_by") == self.sender:
            return {"acked": True, "message_id": message_id, "envelope": found_env, "noop": True}

        found_env["read"] = True
        if not found_env.get("read_at"):
            found_env["read_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        if not found_env.get("read_by"):
            found_env["read_by"] = self.sender
        # Per-session tracker.
        rbs = found_env.get("read_by_sessions") or {}
        rbs[self.sender] = found_env["read_at"]
        found_env["read_by_sessions"] = rbs

        # Strip internal keys before persisting.
        persist_env = {k: v for k, v in found_env.items() if not k.startswith("_")}
        self._atomic_write_json(found_path, persist_env)
        return {"acked": True, "message_id": message_id, "envelope": persist_env}

    # ----------------------------------------------------------- internals

    def _read_dir(self, inbox_dir: Path) -> List[Dict[str, Any]]:
        if not inbox_dir.exists() or not inbox_dir.is_dir():
            return []
        out: List[Dict[str, Any]] = []
        for f in sorted(inbox_dir.iterdir(), reverse=True):
            if not f.is_file() or not f.name.endswith(".json"):
                continue
            try:
                env = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            env["_path"] = str(f)
            env["_filename"] = f.name
            out.append(env)
        return out

    def _write_envelope(self, envelope: Dict[str, Any]) -> Path:
        """Atomically write an envelope to the recipient inbox.

        Spec §3.1: stage to ``.tmp`` then ``os.replace`` so a subscriber
        never reads a half-written file.
        """
        recipient = envelope["to"]
        # Sanitize recipient for filesystem use (no path traversal).
        recipient = re.sub(r"[^A-Za-z0-9._-]", "_", recipient)
        inbox_dir = self.brain_path / "relay" / recipient
        inbox_dir.mkdir(parents=True, exist_ok=True)

        ts = envelope["created_at"].replace(":", "").replace("-", "").split(".")[0]
        # ts looks like 20260718T091557123456Z — strip trailing Z for filename.
        ts_safe = ts.rstrip("Z")
        fname = f"{ts_safe}_{envelope['id']}.json"
        target = inbox_dir / fname
        self._atomic_write_json(target, envelope)
        return target

    @staticmethod
    def _atomic_write_json(target: Path, payload: Dict[str, Any]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(target.parent),
            prefix=target.stem + ".",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, target)
