"""EID-74 — opposed pairs for the two unbounded-growth caps.

- verification_log.jsonl: cap_log_file (runtime/common.py) tail-caps the
  append-only receipt log the GROUND hook writes every commit.
- rag_index.db: brain_rag._enforce_chunk_cap drops the oldest chunks beyond
  RAG_MAX_CHUNKS, inside _rebuild_fts (consistent FTS) and post-commit in the
  live session path (bound only).

Every case is a pair: over the cap gets trimmed; under the cap is untouched.
"""
import sqlite3
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_PKG_SRC = _REPO_ROOT / "mcp-server-nucleus" / "src"
if str(_PKG_SRC) not in sys.path:
    sys.path.insert(0, str(_PKG_SRC))


# ── cap_log_file ─────────────────────────────────────────────

def test_cap_log_file_trims_over_cap_keeps_tail(tmp_path):
    from mcp_server_nucleus.runtime.common import cap_log_file
    f = tmp_path / "verification_log.jsonl"
    tail = b'{"tail": true}\n'
    f.write_bytes(b"o" * 2048 + b"o" * 496 + tail)
    assert cap_log_file(f, max_bytes=1024, keep_bytes=512) is True
    data = f.read_bytes()
    assert len(data) == 512 and tail in data


def test_cap_log_file_leaves_under_cap_untouched(tmp_path):
    from mcp_server_nucleus.runtime.common import cap_log_file
    f = tmp_path / "verification_log.jsonl"
    payload = b'{"receipt": 1}\n' * 10
    f.write_bytes(payload)
    assert cap_log_file(f, max_bytes=1024, keep_bytes=512) is False
    assert f.read_bytes() == payload


def test_cap_log_file_never_raises(tmp_path):
    from mcp_server_nucleus.runtime.common import cap_log_file
    assert cap_log_file(tmp_path / "missing.jsonl") is False
    assert cap_log_file(tmp_path / "nope", max_bytes=1, keep_bytes=0) is False


# ── _enforce_chunk_cap ───────────────────────────────────────

def _mk_chunks_db(tmp_path, n):
    db = tmp_path / "rag_index.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, indexed_at REAL)")
    conn.executemany("INSERT INTO chunks (indexed_at) VALUES (?)",
                     [(float(i),) for i in range(n)])
    conn.commit()
    return conn


def test_chunk_cap_deletes_oldest_beyond_cap(tmp_path):
    from providers.brain_rag import _enforce_chunk_cap
    conn = _mk_chunks_db(tmp_path, 10)
    deleted = _enforce_chunk_cap(conn, max_rows=6)
    assert deleted == 4
    kept = [r[0] for r in conn.execute("SELECT indexed_at FROM chunks ORDER BY indexed_at")]
    assert kept == [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]  # newest survive
    conn.close()


def test_chunk_cap_under_cap_is_untouched(tmp_path):
    from providers.brain_rag import _enforce_chunk_cap
    conn = _mk_chunks_db(tmp_path, 5)
    assert _enforce_chunk_cap(conn, max_rows=6) == 0
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 5
    conn.close()


def test_chunk_cap_zero_disables(tmp_path):
    from providers.brain_rag import _enforce_chunk_cap
    conn = _mk_chunks_db(tmp_path, 10)
    assert _enforce_chunk_cap(conn, max_rows=0) == 0
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 10
    conn.close()


def test_rebuild_fts_enforces_cap_in_same_pass(tmp_path, monkeypatch):
    """_rebuild_fts is the shared rebuild point — cap must engage inside it."""
    from providers import brain_rag
    conn = _mk_chunks_db(tmp_path, 8)
    conn.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(content)")
    monkeypatch.setattr(brain_rag, "RAG_MAX_CHUNKS", 5)
    brain_rag._rebuild_fts(conn)
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 5
    conn.close()
