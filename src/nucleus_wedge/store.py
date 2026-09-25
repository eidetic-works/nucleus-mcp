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

import hashlib
import json
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from nucleus_wedge.role_normalize import _normalize_role

logger = logging.getLogger("nucleus_wedge.store")

# ── Compare-and-swap write gate ────────────────────────────────────────────
# history.jsonl is append-only, which made concurrent edits silent: two agents
# both read a memory, both append, and the second simply becomes the head. The
# first agent's reasoning is gone and nothing anywhere reports it. The cure is
# the standard optimistic-concurrency round trip — hash before the edit, pass
# that hash back at write time, refuse if the head moved underneath.
#
# Opt-in by construction: ``expected_hash=None`` is the pre-existing behaviour
# exactly, so no existing caller changes. Only a caller that asks to be guarded
# can be refused.

#: ``head_hash`` result for a key that has no live record, and the value to pass
#: as ``expected_hash`` to assert "I am creating this, it must not exist yet".
ABSENT = "absent"

#: Snapshot fields the hash covers. Deliberately the fields a competing writer
#: would change — not ``signature`` (derived) or ``origin`` (writer identity,
#: which differs between two agents making the *same* edit).
_CAS_FIELDS = ("key", "value", "context", "intensity", "op_type", "timestamp", "deleted")


#: Write tiers. The talk's prescription: org-wide context read-only to agents,
#: a scratchpad writable. Reads are NEVER gated -- org context exists to be read
#: by everyone; it is the WRITE that scales a mistake to every agent.
SCOPE_ORG = "org"
SCOPE_AGENT = "agent"
_SCOPES = (SCOPE_ORG, SCOPE_AGENT)

#: Writers permitted to create or modify an org-scoped memory.
_ORG_WRITERS = ("operator", "unrestricted")


class PermissionDenied(RuntimeError):
    """Raised when a writer may not write at a memory's scope.

    Names the scope, the writer and the key, because a refusal nobody can
    diagnose is a refusal that gets switched off.
    """

    def __init__(self, key: str, scope: str, writer: str, detail: str = ""):
        self.key, self.scope, self.writer = key, scope, writer
        super().__init__(
            f"write refused: {key!r} is {scope!r}-scoped and the writer is "
            f"{writer!r}. {detail}".strip()
        )


class MemoryConflict(RuntimeError):
    """Raised when a guarded write finds the head moved since it was read.

    Carries both hashes: a refusal a human cannot diagnose is a refusal that
    gets switched off.
    """

    def __init__(self, key: str, expected: str, actual: str):
        self.key = key
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"memory write refused: key {key!r} changed since it was read "
            f"(expected head {expected}, found {actual}). Re-read the memory, "
            f"re-apply the edit on top of the current value, and retry."
        )


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


# Resolved once per process. Deriving the repo means a `git rev-parse`
# subprocess, and this store takes ~19k appends — paying that per write would
# make remember() dominated by process spawns.
_ORIGIN_CACHE: dict | None = None


_TRUSTWORTHY = "explicit"
_ENV_DERIVED = "env"

# Whether this process is a server that outlives the session which spawned it.
# A short-lived process -- a CLI invocation from a tool call -- inherits a
# CURRENT environment, so its ``CLAUDE_CODE_SESSION_ID`` is the session that is
# really writing. A long-lived server inherited its environment once, possibly
# days ago, and then went on serving other sessions; measured 2026-09-20, the
# running MCP server held an id 8.6h stale. Servers set this at startup via
# :func:`mark_long_lived` and thereby give up env attribution.
_LONG_LIVED = False


def mark_long_lived() -> None:
    """Declare that this process outlives the session that spawned it.

    Called by any server whose environment is frozen at startup. After this,
    an env-derived session id is recorded but never presented as trustworthy,
    so a consumer counting distinct sessions reports INSUFFICIENT instead of
    collapsing every row onto one stale id.
    """
    global _LONG_LIVED
    _LONG_LIVED = True


def _resolve_session(origin: dict, session: str | None) -> dict:
    """Attach the session half of an origin, and say where it came from.

    Two sources, and they are NOT interchangeable:

    ``explicit``
        The caller named the session for THIS write. Trustworthy, because a
        per-call value cannot go stale.
    ``env``
        Read from the environment of whatever process happens to be writing.
        Recorded, but marked, because a long-lived writer's environment was
        frozen when it spawned. Measured 2026-09-20: the live MCP server was
        8.6 hours old and carried a *different* session's id, while two others
        were 3 days old and carried none. Stamping every row with that one id
        would collapse a distinct-session count to 1 -- a confident wrong
        number in place of an honest blank. Consumers decide whether to count
        it; :mod:`mcp_server_nucleus.flywheel.prevalence` refuses to.

    This is never cached. The session is a property of the call, not of the
    process.
    """
    if session:
        origin["session"] = session
        origin["session_source"] = _TRUSTWORTHY
        return origin
    env = (
        # The variable Claude Code actually exports. The old code read
        # ``CLAUDE_SESSION_ID``, which nothing sets -- which is why 30,787 of
        # 30,813 rows in the live corpus carry no session at all.
        os.environ.get("CLAUDE_CODE_SESSION_ID")
        or os.environ.get("NUCLEUS_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or None
    )
    origin["session"] = env or None
    if not env:
        origin["session_source"] = None
    elif _LONG_LIVED:
        origin["session_source"] = _ENV_DERIVED
    else:
        # Short-lived writer: the environment was handed to it by the session
        # that is writing right now, so this id is as good as an explicit one.
        origin["session_source"] = _TRUSTWORTHY
    return origin


def _origin(session: str | None = None) -> dict:
    """Best-effort ``{repo, session}`` for the current writer.

    ``repo`` is the basename of the git top-level containing the CWD, so
    memories written from different repos into a shared brain stay
    distinguishable. ``session`` comes from the harness session id when it is
    exported.

    Every field is optional and any failure yields ``None`` rather than raising
    — origin is metadata about a memory, and failing to determine it must never
    prevent the memory from being written.
    """
    global _ORIGIN_CACHE
    if _ORIGIN_CACHE is not None:
        # Only ``repo`` is cached -- it costs a subprocess and cannot change
        # for the life of the process. The session must not be cached: see
        # ``_resolve_session``.
        return _resolve_session(dict(_ORIGIN_CACHE), session)

    repo = None
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            repo = Path(out.stdout.strip()).name
    except Exception:  # noqa: BLE001 — origin is never worth failing a write over
        repo = None

    _ORIGIN_CACHE = {"repo": repo}
    return _resolve_session(dict(_ORIGIN_CACHE), session)


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

    def __init__(self, brain_path: Path | None = None, writer: str = "unrestricted"):
        # ``writer`` defaults to "unrestricted" so every existing caller -- and
        # the 30,744 records already on disk -- behaves exactly as before. A
        # guard that breaks the existing corpus gets deleted, and then there is
        # no guard. Callers that want the tiers opt in by naming themselves.
        self._writer = writer
        self._brain_path = Path(brain_path) if brain_path else self.brain_path()
        self._history = self._brain_path / "engrams" / "history.jsonl"
        # Deliberately does NOT create anything. This used to mkdir+touch, so
        # merely constructing a Store to READ materialised an empty store
        # wherever the process was standing — and since .brain/engrams/ is
        # gitignored, the created file never showed up in `git status` to give
        # the game away. The caller then got zero rows and could not tell
        # "this brain has no store" from "this store is empty". Creation now
        # happens on the write path only (see ``append``).
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

    @property
    def exists(self) -> bool:
        """Whether an engram store is actually present.

        The distinction this restores: ``exists is False`` means ABSENT (no
        store here — most likely the wrong brain), while ``exists is True`` with
        no rows means EMPTY (a real store, nothing written yet). Both read as
        zero rows, and conflating them is how a recall against the wrong
        directory reports "no memories" instead of "no memory store".
        """
        return self._history.exists()

    def rows(self) -> Iterator[dict]:
        """Stream raw records from history.jsonl.

        Yields nothing when the store is absent rather than raising — but see
        :attr:`exists` before treating that emptiness as an answer.
        """
        if not self._history.exists():
            return
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

    def head_hash(self, key: str) -> str:
        """Hash of the current head record for ``key``, or :data:`ABSENT`.

        This is the read half of the compare-and-swap round trip: take it
        before editing, hand it back to :meth:`append` as ``expected_hash``.
        Stable across repeated reads while nothing writes; different after any
        write to that key.
        """
        head = None
        for row in self.rows():
            if row.get("key") == key:
                head = row
        if head is None:
            return ABSENT
        snap = head.get("snapshot") or {}
        if snap.get("deleted"):
            return ABSENT
        payload = json.dumps(
            {f: snap.get(f) for f in _CAS_FIELDS}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _records_for(self, key: str) -> list:
        """Every record written under ``key``, oldest first."""
        return [r for r in self.rows() if r.get("key") == key]

    def _scope_of(self, key: str) -> str | None:
        """The scope this key was created at, or None if it has never been
        written. A record with no ``scope`` field predates tiers entirely and
        reads as permissive -- the same way a missing ``origin`` means unknown,
        not "other repo"."""
        for r in self._records_for(key):
            sc = (r.get("snapshot") or {}).get("scope")
            if sc:
                return sc
        return None

    def _next_version(self, key: str) -> int:
        return len(self._records_for(key)) + 1

    def head_value(self, key: str):
        """Value of the most recent record for ``key``, or None."""
        recs = self._records_for(key)
        return (recs[-1].get("snapshot") or {}).get("value") if recs else None

    def rollback(self, key: str, to_version: int) -> dict:
        """Restore an earlier value for ``key`` by APPENDING it again.

        Deliberately not a deletion. History is the evidence; an undo that
        erases the mistake erases the record of the mistake, which is the
        opposite of an audit trail. The restored value therefore arrives as a
        new record with ``op_type="ROLLBACK"`` and the next version number, so
        the undo is itself auditable and can itself be rolled back.
        """
        recs = self._records_for(key)
        if not recs:
            raise ValueError(
                f"cannot roll back {key!r}: no record of it. A rollback to a key "
                "that was never written would invent history."
            )
        match = next(
            (r for r in recs if (r.get("snapshot") or {}).get("version") == to_version),
            None,
        )
        if match is None:
            seen = sorted(
                v for v in ((r.get("snapshot") or {}).get("version") for r in recs)
                if v is not None
            )
            raise ValueError(
                f"cannot roll back {key!r} to version {to_version}: no such version. "
                f"Versions on record: {seen}."
            )
        snap = match.get("snapshot") or {}
        return self.append(
            value=snap.get("value", ""),
            kind=(snap.get("context") or "note").split(" [#")[0],
            key=key,
            op_type="ROLLBACK",
        )

    def append(
        self,
        value: str,
        kind: str = "note",
        tags: list[str] | None = None,
        intensity: int = 5,
        source_agent: str = "nucleus-wedge",
        key: str | None = None,
        op_type: str = "ADD",
        expected_hash: str | None = None,
        scope: str | None = None,
        session: str | None = None,
    ) -> dict:
        """Append one record. Returns ``{key, timestamp}``.

        ``expected_hash`` opts this write into the compare-and-swap gate: pass
        the :meth:`head_hash` taken before the edit and the append is refused
        with :class:`MemoryConflict` if the head moved in the meantime. Pass
        :data:`ABSENT` to assert the key must not exist yet. Omit it and the
        write behaves exactly as it always has.
        """
        if expected_hash is not None and not key:
            raise ValueError(
                "expected_hash requires an explicit key — a compare-and-swap "
                "over a key the caller has not named cannot refer to anything."
            )
        ts = _iso_now()
        caller_key = key or None
        if not key:
            key = f"remember_{ts.replace(':', '').replace('-', '').replace('.', '')[:19]}_{uuid.uuid4().hex[:8]}"
        # ── write scope ────────────────────────────────────────────────
        # The scope is FIXED AT KEY CREATION and inherited by every later write.
        # If a writer could choose the scope per write, the guard would be
        # theatre: an agent would simply relabel an org key as its own, or
        # declare a new key org-scoped. So an agent can neither escalate nor
        # downgrade, and only an org-writer may create an org key.
        existing_scope = self._scope_of(key)
        if existing_scope is None:
            effective = (scope or SCOPE_AGENT).lower()
            if effective not in _SCOPES:
                raise ValueError(f"unknown scope {scope!r}; expected one of {_SCOPES}")
            if effective == SCOPE_ORG and self._writer not in _ORG_WRITERS:
                raise PermissionDenied(
                    key, SCOPE_ORG, self._writer,
                    "Only an org writer may create org-wide context.",
                )
        else:
            effective = existing_scope
            if scope is not None and scope.lower() != existing_scope:
                raise PermissionDenied(
                    key, existing_scope, self._writer,
                    f"its scope is fixed at {existing_scope!r} and cannot be "
                    f"changed to {scope!r} by a write.",
                )
            if existing_scope == SCOPE_ORG and self._writer not in _ORG_WRITERS:
                raise PermissionDenied(
                    key, SCOPE_ORG, self._writer,
                    "Org-wide context is read-only to agents: an incorrect "
                    "write here reaches every agent that reads it.",
                )

        if expected_hash is not None:
            actual = self.head_hash(key)
            if actual != expected_hash:
                raise MemoryConflict(key, expected_hash, actual)
        # `version` used to be the literal 1 on every record, forever -- a field
        # the record shape advertises and never maintained, which is worse than
        # no field at all: an absent field prompts a question, a field that is
        # always 1 answers it wrongly. The history was never missing, only
        # unnumbered: this log is append-only, so every write for a key is
        # already a row in order. Numbering costs one scan, and only for an
        # explicit key -- an auto-generated key is unique by construction and is
        # always version 1, which keeps the common `remember` path free.
        version = 1 if caller_key is None else self._next_version(key)
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
                "version": version,
                "scope": effective,
                "source_agent": source_agent,
                "op_type": op_type,
                "timestamp": ts,
                "deleted": False,
                "signature": None,
                # Where this memory came from (fw-1786153512 defect 3). Until
                # now the only attribution was source_agent, which records WHO
                # wrote ("auto_hook", "devin") and never WHERE FROM — so every
                # agent in every repo wrote into one undifferentiated pool and
                # recall could not express "what did agents in THIS repo learn".
                # Rows written before this exist with no origin at all; readers
                # must treat a missing origin as UNKNOWN and therefore
                # permissive, never as a reason to exclude.
                "origin": _origin(session),
            },
        }
        if _provenance_anchor_flag_on():
            record["snapshot"]["signature"] = self._sign_snapshot(record["snapshot"])
        # Lazy creation: the store comes into being on first write, never on a
        # read. Greenfield init still works — this is the only place that makes
        # the file.
        self._history.parent.mkdir(parents=True, exist_ok=True)
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
