"""Store — load/append .brain/engrams/history.jsonl using the existing record shape.

Record shape (matches ``auto_hook`` writers so both can coexist):

    {
      "key": <str>,
      "op_type": <str>,
      "timestamp": <ISO-8601>,
      "snapshot": {
        "key": <str>,            # duplicated for snapshot self-containment
        "value": <str>,          # primary content body
        "context": <str>,        # kind / taxonomy label
        "intensity": <int 1-10>,
        "version": <int>,
        "source_agent": <str>,
        "op_type": <str>,
        "timestamp": <ISO-8601>,
        "deleted": <bool>,
        "signature": <str|None>
      }
    }
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from nucleus_wedge.role_normalize import _normalize_role

logger = logging.getLogger("nucleus_wedge.store")

# --- Move 2 batch 2: dual-write shim (wedge append -> unified SoR facade) -----
# Flag-gated on NUCLEUS_MEMORY_SOR. Kept as a self-contained env check (no import
# of ``mcp_server_nucleus.memory.*``) so the flag-OFF path stays a byte-for-byte
# no-op and ``nucleus_wedge`` remains importable stand-alone (see server.py
# docstring — it ships without the parent package in some deployments). Truthy
# set mirrors ``memory.facade._TRUTHY`` on purpose.
_SOR_FLAG = "NUCLEUS_MEMORY_SOR"
_SOR_TRUTHY = frozenset({"1", "true", "yes", "on"})
# Process-wide log-once latch for mirror failures (fault isolation must not spam).
_sor_mirror_warned = False


def _sor_flag_on() -> bool:
    """True iff ``NUCLEUS_MEMORY_SOR`` is set truthy (default False)."""
    return os.environ.get(_SOR_FLAG, "").strip().lower() in _SOR_TRUTHY


# --- A11 (recall provenance anchoring): server-stamped role/source + HMAC ----
# Flag-gated on NUCLEUS_RECALL_PROVENANCE_ANCHOR (default OFF). Off is
# byte-identical to pre-A11 behavior: ``source_agent`` and any ``role:<x>`` tag
# stay whatever the caller passed, ``signature`` stays None. See
# docs/verifier/HANDOFF_BACKLOG.md §A11. Mirrors A3's engram-insert anchoring
# (runtime/memory_pipeline.py) for the wedge ``history.jsonl`` write path:
# recall's read-freshness facet (mtime+rowcount in recall_cmd.py::
# _ensure_populated) is already Regime-1-anchored and is NOT touched here —
# this closes the separate hole where the provenance / role-tag on a recalled
# record is caller-controlled and the ``signature`` slot is hardcoded None.
_PROVENANCE_FLAG = "NUCLEUS_RECALL_PROVENANCE_ANCHOR"
_PROVENANCE_TRUTHY = frozenset({"1", "true", "yes", "on"})

# The exact snapshot field set the A11 signature covers — mirrors A3's
# ``_ANCHOR_CANONICAL_FIELDS``, excluding ``signature`` itself.
_PROVENANCE_CANONICAL_FIELDS = (
    "key", "value", "context", "intensity", "version",
    "source_agent", "op_type", "timestamp", "deleted",
)


def _provenance_anchor_flag_on() -> bool:
    """True iff ``NUCLEUS_RECALL_PROVENANCE_ANCHOR`` is set truthy (default False)."""
    return os.environ.get(_PROVENANCE_FLAG, "").strip().lower() in _PROVENANCE_TRUTHY


def _canonical_provenance_payload(snapshot: dict) -> dict:
    """Deterministic subset of snapshot fields the A11 signature is computed over."""
    return {field: snapshot.get(field) for field in _PROVENANCE_CANONICAL_FIELDS}


def _derive_server_role(caller_value: str) -> str:
    """Server-side identity derivation — the A11 fix for "role-tag / source_agent
    is caller-controlled". Mirrors ``memory_pipeline.py::_derive_source_agent``
    (A3): the caller-supplied value is IGNORED (a claimant-controlled field is
    exactly what Regime-2 forbids trusting) and replaced with the same
    ancestry-registry role resolution the relay-sender (A2) / engram-insert
    (A3) paths use.

    Deviation note (same as A3): ``detect_session_role()`` still honors a
    same-process ``NUCLEUS_SESSION_ROLE`` env override ahead of the registry
    lookup (A1 — sessions-identity hardening — is a separate, not-yet-landed
    backlog item). Falls back to the caller-supplied value only if detection
    raises or yields nothing, so a write is never silently dropped for lack of
    ancestry data. Lazy/absolute import (not relative) because ``nucleus_wedge``
    ships importable stand-alone in some deployments (see module docstring in
    ``server.py``) — a missing ``mcp_server_nucleus`` package degrades to the
    fallback rather than raising.
    """
    try:
        from mcp_server_nucleus.runtime.relay.session import detect_session_role

        role = detect_session_role()
        if role and role != "unknown":
            return _normalize_role(role)
    except Exception:
        pass
    return caller_value or "unknown"


def verify_record(snapshot: dict, brain_path: Path | None = None) -> bool:
    """Read-side verify: recompute the A11 HMAC over ``snapshot``'s canonical
    fields and compare against the stored ``signature``.

    Returns False for: no signature (legacy/pre-A11/forged-blank), or any
    mismatch — including a tampered ``source_agent`` / ``role:<x>`` tag
    (forged provenance) or a tampered ``context``/``timestamp``, since all are
    covered canonical fields. Fault-isolated: any import/guard error is
    treated as "not verified" rather than raised, so a read never breaks on a
    missing secret file or a standalone (no ``mcp_server_nucleus``) deployment.
    """
    sig = snapshot.get("signature")
    if not sig:
        return False
    try:
        from mcp_server_nucleus.runtime.auth.signature_guard import get_signature_guard

        guard = get_signature_guard(brain_path)
        return guard.verify_dict(_canonical_provenance_payload(snapshot), sig)
    except Exception:
        return False


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_tags(tags: list[str] | None) -> list[str] | None:
    """Apply `role:<x>` canonicalization at write-time.

    Per ADR-0033 v3 §B: normalize the value half of any `role:<x>` tag through
    `_normalize_role` so doublet drift (`cc_gq` vs `gq`, `antigravity` vs `agy`)
    cannot split a single agent's activity engrams across two tag spellings.
    Non-role tags pass through unchanged.
    """
    if not tags:
        return tags
    out: list[str] = []
    for tag in tags:
        if isinstance(tag, str) and tag.startswith("role:"):
            value = tag[len("role:") :]
            out.append(f"role:{_normalize_role(value)}")
        else:
            out.append(tag)
    return out


class Store:
    """Append-only reader/writer over ``.brain/engrams/history.jsonl``."""

    def __init__(self, brain_path: Path | None = None):
        self._brain_path = Path(brain_path) if brain_path else self.brain_path()
        self._history = self._brain_path / "engrams" / "history.jsonl"
        self._history.parent.mkdir(parents=True, exist_ok=True)
        self._history.touch(exist_ok=True)
        # Lazy MemoryFacade for the SoR dual-write mirror (Move 2 batch 2). Never
        # constructed while NUCLEUS_MEMORY_SOR is off — keeps flag-OFF a true no-op.
        self._sor_facade = None
        # Lazy derived-index sink for the SoR mirror (Move 2 batch B2). Same
        # flag-OFF contract as ``_sor_facade`` — never built until the flag-ON
        # branch of ``_mirror_to_sor`` runs.
        self._sor_vector_sink = None

    @staticmethod
    def brain_path(flag: Path | str | None = None) -> Path:
        """Resolve ``.brain`` path per ``week2_init_flow_spec.md`` §3a.

        Order: explicit ``flag`` → ``NUCLEUS_BRAIN_PATH``/``NUCLEAR_BRAIN_PATH`` env →
        cwd contains ``.brain/`` → cwd contains ``.git/`` (greenfield, returned path
        not yet created) → abort. No silent walk-up across cwd ancestors (gap 1a:
        cwd-binding hazard from `feedback_relay_post_cross_worktree.md`).
        """
        if flag is not None:
            return Path(flag)
        env = os.environ.get("NUCLEUS_BRAIN_PATH") or os.environ.get("NUCLEAR_BRAIN_PATH")
        if env:
            return Path(env)
        cwd = Path.cwd()
        if (cwd / ".brain").exists():
            return cwd / ".brain"
        if (cwd / ".git").exists():
            return cwd / ".brain"
        raise ValueError(
            "nucleus init: cannot resolve brain path.\n"
            "  Either: pass --brain-path /absolute/path\n"
            "      or: export NUCLEUS_BRAIN_PATH=/absolute/path\n"
            "      or: run from a directory containing .git/ or .brain/"
        )

    @property
    def history_file(self) -> Path:
        return self._history

    def rows(self) -> Iterator[dict]:
        """Stream raw records from history.jsonl."""
        with self._history.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def keys_present(self) -> set[str]:
        """Top-level keys currently in history — used by ``seed.ensure_seeds`` for idempotence."""
        return {r.get("key") for r in self.rows() if r.get("key")}

    def append(
        self,
        value: str,
        kind: str = "note",
        tags: list[str] | None = None,
        intensity: int = 5,
        source_agent: str = "nucleus-wedge",
        key: str | None = None,
        op_type: str = "ADD",
    ) -> dict:
        """Append one record. Returns ``{key, timestamp}``."""
        ts = _iso_now()
        if not key:
            key = f"remember_{ts.replace(':', '').replace('-', '').replace('.', '')[:19]}_{uuid.uuid4().hex[:8]}"
        tags = _normalize_tags(tags)
        if _provenance_anchor_flag_on():
            source_agent, tags = self._anchor_stamp(source_agent, tags)
        context = kind if not tags else f"{kind} [#{','.join(tags)}]"
        record = {
            "key": key,
            "op_type": op_type,
            "timestamp": ts,
            "snapshot": {
                "key": key,
                "value": value,
                "context": context,
                "intensity": intensity,
                "version": 1,
                "source_agent": source_agent,
                "op_type": op_type,
                "timestamp": ts,
                "deleted": False,
                "signature": None,
            },
        }
        if _provenance_anchor_flag_on():
            record["snapshot"]["signature"] = self._sign_snapshot(record["snapshot"])
        with self._history.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        # Dual-write: after the authoritative history.jsonl append, ALSO mirror
        # into the unified SoR (flag-gated, fault-isolated). Never alters or
        # gates the return above — reads are untouched in this batch.
        self._mirror_to_sor(
            key=key,
            value=value,
            kind=kind,
            tags=tags,
            ts=ts,
            source_agent=source_agent,
            op_type=op_type,
        )
        return {"key": key, "timestamp": ts}

    # ── A11: recall provenance anchoring (NUCLEUS_RECALL_PROVENANCE_ANCHOR) ──

    def _anchor_stamp(
        self, source_agent: str, tags: list[str] | None
    ) -> tuple[str, list[str] | None]:
        """Server-stamp ``source_agent`` and any ``role:<x>`` tag, ignoring the
        caller's asserted values. Only replaces a ``role:<x>`` tag if one is
        already present (never invents a role claim the caller didn't make);
        ``source_agent`` is always server-derived when the flag is on.
        """
        derived = _derive_server_role(source_agent)
        if not tags:
            return derived, tags
        out: list[str] = []
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("role:"):
                out.append(f"role:{derived}")
            else:
                out.append(tag)
        return derived, out

    def _sign_snapshot(self, snapshot: dict) -> str | None:
        """Compute the A11 HMAC signature over ``snapshot``'s canonical fields.
        Fault-isolated: returns None (leaves the slot dead) rather than raising
        on a missing secret/guard, matching ``verify_record``'s posture.
        """
        try:
            from mcp_server_nucleus.runtime.auth.signature_guard import get_signature_guard

            guard = get_signature_guard(self._brain_path)
            return guard.sign_dict(_canonical_provenance_payload(snapshot))
        except Exception:
            return None

    def _mirror_to_sor(
        self,
        *,
        key: str,
        value: str,
        kind: str,
        tags: list[str] | None,
        ts: str,
        source_agent: str,
        op_type: str,
    ) -> None:
        """Best-effort mirror of this append into the unified SoR (Move 2 batch 2).

        Dual-write shim: by the time this runs, the authoritative write to
        ``history.jsonl`` has already succeeded; here we ADD the same record to
        the ``MemoryFacade`` SoR so the two stores converge. Properties:

          * Flag-gated — ``NUCLEUS_MEMORY_SOR`` off (default) short-circuits to a
            pure no-op: no import of ``mcp_server_nucleus.memory.*``, no facade,
            nothing persisted. The history append above is byte-for-byte the
            pre-batch-2 behavior.
          * Fault-isolated — a SoR/facade failure must NEVER break the operator's
            live capture, so every error is swallowed after a single warning
            (process-wide log-once latch).
          * Stable-keyed — the SoR record reuses the history ``key`` and shares
            the ``ts``, so the later backfill (manifest batch 6, dedup-by-key)
            converges dual-written rows instead of duplicating them.

        Reads are unchanged in this batch (recall still reads history — the read
        repoint is manifest batch 4).
        """
        if not _sor_flag_on():
            return
        global _sor_mirror_warned
        try:
            if self._sor_facade is None:
                from mcp_server_nucleus.memory.facade import MemoryFacade

                self._sor_facade = MemoryFacade(brain_path=self._brain_path, enabled=True)
            # Derived-index sink (Move 2 batch B2): keep the vector index warm so
            # the optional recall re-rank sees freshly-mirrored engrams. Mirrors
            # runtime/memory_pipeline.py's construction-isolated sink pattern:
            #   * lazily imported inside this flag-ON branch — no import of
            #     ``runtime.vector_store`` on the flag-OFF path (Move 1 lazy
            #     contract; the parent package is only pulled in under the flag);
            #   * cached on ``self`` after first use — one VectorStore per Store;
            #   * construction-isolated — a sink-build/import failure degrades to
            #     a sink-less mirror (the SoR row still lands) rather than aborting
            #     the mirror. ``facade.capture`` itself wraps ``sink.index()``
            #     best-effort, so an index failure never breaks the primary write
            #     (already completed above).
            sink = self._sor_vector_sink
            if sink is None:
                try:
                    from mcp_server_nucleus.runtime.vector_store import VectorStore

                    sink = self._sor_vector_sink = VectorStore()
                except Exception:  # noqa: BLE001 — derived-index sink is best-effort
                    sink = None
            self._sor_facade.capture(
                surface=source_agent,
                payload=value,
                kind=kind,
                tags=tags,
                ts=ts,
                key=key,
                meta={"op_type": op_type},
                vector_sink=sink,
            )
        except Exception as exc:  # noqa: BLE001 — fault isolation is the whole point
            if not _sor_mirror_warned:
                logger.warning(
                    "nucleus_wedge SoR mirror failed; primary history write "
                    "unaffected (suppressing further mirror warnings this "
                    "process): %s",
                    exc,
                )
                _sor_mirror_warned = True

    @staticmethod
    def extract(row: dict) -> dict:
        """Flatten one row into ``{key, value, context, timestamp, kind}`` for ranking/return."""
        snap = row.get("snapshot") or {}
        return {
            "key": row.get("key"),
            "value": snap.get("value") or row.get("value") or "",
            "context": snap.get("context") or row.get("context") or "",
            "timestamp": snap.get("timestamp") or row.get("timestamp") or "",
            "kind": snap.get("context") or "",
            "source_agent": snap.get("source_agent") or "",
        }
