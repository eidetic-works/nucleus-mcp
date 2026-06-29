"""
Rabbit-Hole Depth Tracker - core store and logic.

A self-contained, stdlib-only module. No network, no daemon, no external
services. All state lives in a single local SQLite file. Every public
function takes an open sqlite3.Connection so callers (the MCP server, the
optional hook, the tests) can point at any database they like, including a
throwaway temp file.

Concepts
--------
- depth stack : a literal push/pop stack of "what I'm diving into now".
                Going one level deeper is a push; resurfacing is a pop.
- context switches : every time you jump to a different subtask we stamp it.
                If you thrash (too many switches inside a short window) we
                hand back a gentle nudge.
- open loops : started-but-unfinished things you externalise so they stop
                living rent-free in your head.

Data directory
--------------
SQLite store lives at $XDG_DATA_HOME/rabbithole/store.db
(fallback: ~/.local/share/rabbithole/store.db)
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Defaults (all overridable via environment variables)
# ---------------------------------------------------------------------------

DEFAULT_MAX_DEPTH = 4
DEFAULT_SWITCH_WINDOW_MINUTES = 30
DEFAULT_SWITCH_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def data_dir() -> Path:
    """Resolve the data directory, honouring XDG_DATA_HOME."""
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        d = Path(base).expanduser() / "rabbithole"
    else:
        d = Path.home() / ".local" / "share" / "rabbithole"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_db_path() -> Path:
    """Path to the default on-disk store."""
    return data_dir() / "store.db"


# ---------------------------------------------------------------------------
# Connection / schema
# ---------------------------------------------------------------------------

def connect(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite store and ensure the schema."""
    if db_path is None:
        db_path = default_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Under concurrent tool calls (multiple PostToolUse hooks firing in one
    # turn), SQLite's default busy behaviour is to raise OperationalError
    # immediately on lock contention. That races the hook's increment/reset
    # and silently loses depth counts. A 5s busy_timeout makes writers wait
    # instead of failing — depth undercounts less, nudge fires on time.
    conn.execute("PRAGMA busy_timeout = 5000")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS frames (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            topic      TEXT NOT NULL,
            depth      INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at   TEXT,
            active     INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS switches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            to_context  TEXT NOT NULL,
            switched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS loops (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'open',
            created_at  TEXT NOT NULL,
            closed_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS hook_state (
            session_id  TEXT PRIMARY KEY,
            depth       INTEGER NOT NULL DEFAULT 0,
            streak      TEXT    NOT NULL DEFAULT '[]',
            updated_at  TEXT    NOT NULL
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _meta_get(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def current_session(conn: sqlite3.Connection) -> str:
    """Return the current session id, creating one on first use."""
    sid = _meta_get(conn, "current_session")
    if not sid:
        sid = "sess-" + str(int(time.time()))
        _meta_set(conn, "current_session", sid)
    return sid


def _env_int(name: str, fallback: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return fallback
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback


def config() -> Dict[str, int]:
    """Resolve tunables from the environment, falling back to defaults."""
    return {
        "max_depth": _env_int("RABBITHOLE_MAX_DEPTH", DEFAULT_MAX_DEPTH),
        "switch_window_minutes": _env_int(
            "RABBITHOLE_SWITCH_WINDOW_MINUTES", DEFAULT_SWITCH_WINDOW_MINUTES
        ),
        "switch_threshold": _env_int(
            "RABBITHOLE_SWITCH_THRESHOLD", DEFAULT_SWITCH_THRESHOLD
        ),
    }


def _active_frames(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    sid = current_session(conn)
    return conn.execute(
        "SELECT * FROM frames WHERE session_id = ? AND active = 1 "
        "ORDER BY depth ASC",
        (sid,),
    ).fetchall()


def _depth_status(depth: int, max_depth: int) -> str:
    if depth >= max_depth:
        return "RABBIT HOLE"
    if depth >= max_depth - 1:
        return "DANGER ZONE"
    if depth >= max(2, max_depth - 2):
        return "CAUTION"
    return "OK"


def _indicator(depth: int, max_depth: int) -> str:
    filled = min(depth, max_depth)
    bar = "#" * filled + "." * max(0, max_depth - filled)
    flag = " (!)" if depth >= max_depth else ""
    return "[" + bar + "]" + flag


# ---------------------------------------------------------------------------
# Depth stack
# ---------------------------------------------------------------------------

def depth_push(conn: sqlite3.Connection, topic: str) -> Dict[str, Any]:
    """Push a sub-dive onto the stack. Warn if it gets too deep."""
    topic = (topic or "").strip()
    if not topic:
        return {"error": "topic must be a non-empty string"}

    cfg = config()
    max_depth = cfg["max_depth"]
    sid = current_session(conn)

    current = len(_active_frames(conn))
    new_depth = current + 1

    conn.execute(
        "INSERT INTO frames(session_id, topic, depth, started_at, active) "
        "VALUES(?, ?, ?, ?, 1)",
        (sid, topic, new_depth, _iso(_now())),
    )
    conn.commit()

    frames = _active_frames(conn)
    breadcrumbs = " > ".join(f["topic"] for f in frames)
    status = _depth_status(new_depth, max_depth)

    warning = None
    if new_depth >= max_depth:
        warning = (
            f"RABBIT HOLE: you are {new_depth} levels deep "
            f"(max {max_depth}). Consider resurfacing to '{frames[0]['topic']}'."
        )
    elif status == "DANGER ZONE":
        warning = f"Deep dive: level {new_depth}/{max_depth}. You are near the edge."
    elif status == "CAUTION":
        warning = f"Getting deep: level {new_depth}/{max_depth}."

    return {
        "current_depth": new_depth,
        "max_depth": max_depth,
        "topic": topic,
        "breadcrumbs": breadcrumbs,
        "status": status,
        "warning": warning,
        "indicator": _indicator(new_depth, max_depth),
    }


def depth_pop(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Pop the deepest dive and return what you were on before it."""
    cfg = config()
    max_depth = cfg["max_depth"]
    frames = _active_frames(conn)

    if not frames:
        return {
            "current_depth": 0,
            "message": "Already at the root. Nothing to pop.",
            "indicator": _indicator(0, max_depth),
        }

    popped = frames[-1]
    conn.execute(
        "UPDATE frames SET active = 0, ended_at = ? WHERE id = ?",
        (_iso(_now()), popped["id"]),
    )
    conn.commit()

    remaining = _active_frames(conn)
    new_depth = len(remaining)
    returned_to = remaining[-1]["topic"] if remaining else "(root)"
    breadcrumbs = " > ".join(f["topic"] for f in remaining) if remaining else "(root)"

    return {
        "current_depth": new_depth,
        "popped_topic": popped["topic"],
        "returned_to": returned_to,
        "breadcrumbs": breadcrumbs,
        "message": f"Resurfaced from '{popped['topic']}'. Back to: {returned_to}.",
        "indicator": _indicator(new_depth, max_depth),
    }


def depth_show(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Show the live stack, top (root) to bottom (current)."""
    cfg = config()
    max_depth = cfg["max_depth"]
    frames = _active_frames(conn)
    current = len(frames)

    lines: List[str] = []
    if not frames:
        lines.append("(at root - no active dives)")
    else:
        for i, f in enumerate(frames):
            indent = "  " * i
            here = "  <- here" if i == len(frames) - 1 else ""
            lines.append(f"{indent}{i + 1}. {f['topic']}{here}")

    breadcrumbs = " > ".join(f["topic"] for f in frames) if frames else "(root)"

    return {
        "current_depth": current,
        "max_depth": max_depth,
        "status": _depth_status(current, max_depth),
        "breadcrumbs": breadcrumbs,
        "tree": "\n".join(lines),
        "indicator": _indicator(current, max_depth),
    }


def depth_map(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Render the full tangent path for the current session.

    Unlike depth_show (live stack only), this includes dives you have
    already resurfaced from, so you can see the whole shape of the session.
    """
    cfg = config()
    max_depth = cfg["max_depth"]
    sid = current_session(conn)
    frames = conn.execute(
        "SELECT * FROM frames WHERE session_id = ? ORDER BY id ASC", (sid,)
    ).fetchall()

    if not frames:
        return {
            "node_count": 0,
            "map": "START (no dives yet this session)",
            "message": "You are at the root. No exploration path yet.",
        }

    lines = ["START"]
    for f in frames:
        indent = "  " * f["depth"]
        state = "active" if f["active"] else "resurfaced"
        marker = "*" if f["active"] else "-"
        depth_flag = "  [deep]" if f["depth"] >= max_depth else ""
        lines.append(f"{indent}{marker} {f['topic']} ({state}){depth_flag}")

    active_path = " > ".join(
        f["topic"] for f in frames if f["active"]
    ) or "(root)"

    return {
        "node_count": len(frames),
        "map": "\n".join(lines),
        "active_path": active_path,
        "max_depth": max_depth,
        "message": (
            f"{len(frames)} dives this session; "
            f"current live path: {active_path}"
        ),
    }


# ---------------------------------------------------------------------------
# Context switches (thrash detector)
# ---------------------------------------------------------------------------

def switch_context(conn: sqlite3.Connection, to: str) -> Dict[str, Any]:
    """Record a subtask switch and flag thrashing inside a short window."""
    to = (to or "").strip()
    if not to:
        return {"error": "destination context must be a non-empty string"}

    cfg = config()
    window = cfg["switch_window_minutes"]
    threshold = cfg["switch_threshold"]
    sid = current_session(conn)

    # De-duplicate: switching to the same context you are already on is a no-op.
    last = conn.execute(
        "SELECT to_context FROM switches WHERE session_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (sid,),
    ).fetchone()
    was_switch = not (last and last["to_context"] == to)

    if was_switch:
        conn.execute(
            "INSERT INTO switches(session_id, to_context, switched_at) "
            "VALUES(?, ?, ?)",
            (sid, to, _iso(_now())),
        )
        conn.commit()

    cutoff = _iso(_now() - timedelta(minutes=window))
    recent = conn.execute(
        "SELECT to_context, switched_at FROM switches "
        "WHERE session_id = ? AND switched_at >= ? ORDER BY id ASC",
        (sid, cutoff),
    ).fetchall()
    window_count = len(recent)

    signal = None
    if window_count > threshold:
        signal = (
            f"You've switched {window_count} times in the last {window} min "
            f"(threshold {threshold}). Worth pausing to pick one thing?"
        )

    recent_contexts = [r["to_context"] for r in recent[-5:]]

    return {
        "current_context": to,
        "was_switch": was_switch,
        "window_minutes": window,
        "switches_in_window": window_count,
        "threshold": threshold,
        "recent_contexts": recent_contexts,
        "signal": signal,
    }


# ---------------------------------------------------------------------------
# Open loops
# ---------------------------------------------------------------------------

def add_loop(conn: sqlite3.Connection, desc: str) -> Dict[str, Any]:
    """Externalise an open loop (a started-but-unfinished thing)."""
    desc = (desc or "").strip()
    if not desc:
        return {"error": "description must be a non-empty string"}

    cur = conn.execute(
        "INSERT INTO loops(description, status, created_at) "
        "VALUES(?, 'open', ?)",
        (desc, _iso(_now())),
    )
    conn.commit()
    return {
        "id": cur.lastrowid,
        "description": desc,
        "status": "open",
        "message": f"Loop #{cur.lastrowid} opened: {desc}",
    }


def list_loops(conn: sqlite3.Connection, include_closed: bool = False) -> Dict[str, Any]:
    """List open loops (optionally including closed ones)."""
    if include_closed:
        rows = conn.execute(
            "SELECT * FROM loops ORDER BY (status = 'closed'), id ASC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM loops WHERE status = 'open' ORDER BY id ASC"
        ).fetchall()

    loops = [
        {
            "id": r["id"],
            "description": r["description"],
            "status": r["status"],
            "created_at": r["created_at"],
            "closed_at": r["closed_at"],
        }
        for r in rows
    ]
    open_count = sum(1 for loop in loops if loop["status"] == "open")
    return {"count": len(loops), "open_count": open_count, "loops": loops}


def close_loop(conn: sqlite3.Connection, loop_id: int) -> Dict[str, Any]:
    """Close an open loop by id."""
    try:
        loop_id = int(loop_id)
    except (TypeError, ValueError):
        return {"error": "loop_id must be an integer"}

    row = conn.execute("SELECT * FROM loops WHERE id = ?", (loop_id,)).fetchone()
    if row is None:
        return {"error": f"no loop with id {loop_id}"}
    if row["status"] == "closed":
        return {
            "id": loop_id,
            "status": "closed",
            "message": f"Loop #{loop_id} was already closed.",
        }

    conn.execute(
        "UPDATE loops SET status = 'closed', closed_at = ? WHERE id = ?",
        (_iso(_now()), loop_id),
    )
    conn.commit()
    return {
        "id": loop_id,
        "description": row["description"],
        "status": "closed",
        "message": f"Loop #{loop_id} closed: {row['description']}",
    }


# ---------------------------------------------------------------------------
# Weekly review
# ---------------------------------------------------------------------------

def weekly_review(conn: sqlite3.Connection, days: int = 7) -> Dict[str, Any]:
    """Summarise the last `days` days into a short written narrative."""
    cutoff_dt = _now() - timedelta(days=days)
    cutoff = _iso(cutoff_dt)

    touched_rows = conn.execute(
        "SELECT DISTINCT topic FROM frames WHERE started_at >= ? ORDER BY id ASC",
        (cutoff,),
    ).fetchall()
    touched = [r["topic"] for r in touched_rows]

    switch_count = conn.execute(
        "SELECT COUNT(*) AS c FROM switches WHERE switched_at >= ?", (cutoff,)
    ).fetchone()["c"]

    distinct_contexts = conn.execute(
        "SELECT COUNT(DISTINCT to_context) AS c FROM switches "
        "WHERE switched_at >= ?",
        (cutoff,),
    ).fetchone()["c"]

    open_rows = conn.execute(
        "SELECT id, description FROM loops WHERE status = 'open' ORDER BY id ASC"
    ).fetchall()
    closed_count = conn.execute(
        "SELECT COUNT(*) AS c FROM loops "
        "WHERE status = 'closed' AND closed_at >= ?",
        (cutoff,),
    ).fetchone()["c"]

    active = _active_frames(conn)

    # ---- compose narrative ----
    parts: List[str] = []
    parts.append(f"Weekly review (last {days} days)")
    parts.append("=" * 32)

    if touched:
        preview = ", ".join(touched[:8])
        more = f" (+{len(touched) - 8} more)" if len(touched) > 8 else ""
        parts.append(
            f"You went down {len(touched)} distinct thread(s): {preview}{more}."
        )
    else:
        parts.append("No dives recorded this week.")

    if switch_count:
        thrash = (
            "a lot"
            if distinct_contexts and switch_count / max(1, distinct_contexts) > 2
            else "some"
        )
        parts.append(
            f"You switched context {switch_count} time(s) across "
            f"{distinct_contexts} subtask(s) - that's {thrash} bouncing."
        )
    else:
        parts.append("No context switches recorded - nicely focused.")

    if open_rows:
        parts.append(f"Still open: {len(open_rows)} loop(s):")
        for r in open_rows[:10]:
            parts.append(f"  - #{r['id']} {r['description']}")
        if len(open_rows) > 10:
            parts.append(f"  ...and {len(open_rows) - 10} more")
    else:
        parts.append("No open loops - guilt-free.")

    parts.append(f"Closed {closed_count} loop(s) this week.")

    if active:
        parts.append(
            "Heads up: you have an unfinished dive still on the stack: "
            + " > ".join(f["topic"] for f in active)
        )

    return {
        "days": days,
        "threads_touched": touched,
        "switch_count": switch_count,
        "distinct_contexts": distinct_contexts,
        "open_loops": [
            {"id": r["id"], "description": r["description"]} for r in open_rows
        ],
        "closed_this_week": closed_count,
        "active_stack": [f["topic"] for f in active],
        "narrative": "\n".join(parts),
    }


# ---------------------------------------------------------------------------
# Hook state — auto-depth tracker (used by rabbithole/hook.py)
# ---------------------------------------------------------------------------

_HOOK_STREAK_CAP = 20  # keep the last N targets in the streak list


def hook_get_state(conn: sqlite3.Connection, session_id: str) -> Dict[str, Any]:
    """Return current auto-depth hook state for *session_id*.

    Returns ``{"depth": int, "streak": list[str]}``.
    """
    row = conn.execute(
        "SELECT depth, streak FROM hook_state WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        return {"depth": 0, "streak": []}
    return {"depth": row["depth"], "streak": json.loads(row["streak"])}


def hook_increment(
    conn: sqlite3.Connection, session_id: str, target: str
) -> Dict[str, Any]:
    """Atomically increment the read-depth counter and append *target* to the streak.

    Uses a single UPSERT so concurrent invocations on the same *session_id*
    are serialised by SQLite and never corrupt the counter.

    Returns ``{"depth": int, "streak": list[str]}`` with the *updated* values.
    """
    row = conn.execute(
        "SELECT depth, streak FROM hook_state WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    if row is None:
        new_depth = 1
        new_streak: List[str] = [target]
    else:
        new_depth = row["depth"] + 1
        old_streak: List[str] = json.loads(row["streak"])
        new_streak = (old_streak + [target])[-_HOOK_STREAK_CAP:]

    conn.execute(
        """
        INSERT INTO hook_state(session_id, depth, streak, updated_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE
          SET depth      = excluded.depth,
              streak     = excluded.streak,
              updated_at = excluded.updated_at
        """,
        (session_id, new_depth, json.dumps(new_streak), _iso(_now())),
    )
    conn.commit()
    return {"depth": new_depth, "streak": new_streak}


def hook_reset(conn: sqlite3.Connection, session_id: str) -> None:
    """Reset the auto-depth counter to zero for *session_id*.

    Called when an Edit, Write, or write/run Bash is observed — a sign that
    real progress was made, so the rabbit-hole counter should start fresh.
    """
    conn.execute(
        """
        INSERT INTO hook_state(session_id, depth, streak, updated_at)
        VALUES(?, 0, '[]', ?)
        ON CONFLICT(session_id) DO UPDATE
          SET depth      = 0,
              streak     = '[]',
              updated_at = excluded.updated_at
        """,
        (session_id, _iso(_now())),
    )
    conn.commit()
