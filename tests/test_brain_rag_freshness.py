"""Tests for the corpus freshness assertion (fw-1786166556).

Verifies that _check_corpus_freshness detects stale chunk kinds and
_format_freshness_warning produces a human-readable warning.
"""
import sqlite3
import sys
import time
import pytest
from pathlib import Path

# providers/brain_rag.py lives at the repo root, not inside mcp-server-nucleus
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def fresh_db(tmp_path):
    """Create a temp RAG DB with fresh and stale chunks."""
    db_path = tmp_path / "rag_index.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            content TEXT,
            embedding BLOB,
            content_hash TEXT,
            word_count INTEGER,
            priority_tier INTEGER,
            file_mtime REAL,
            indexed_at REAL,
            kind TEXT,
            source_archive TEXT,
            external_ts REAL,
            session_id TEXT,
            project TEXT,
            agent_role TEXT,
            confidentiality TEXT,
            topic_label TEXT,
            original_path TEXT
        )
    """)
    now = time.time()
    # Stale brain chunk (indexed 120 days ago) — the ONLY brain chunk
    conn.execute(
        "INSERT INTO chunks (content, indexed_at, kind) VALUES (?, ?, ?)",
        ("stale brain content", now - 120 * 86400, "brain"),
    )
    # Fresh conversation chunk
    conn.execute(
        "INSERT INTO chunks (content, indexed_at, kind) VALUES (?, ?, ?)",
        ("fresh conversation", now, "conversation"),
    )
    # Chunk with NULL kind
    conn.execute(
        "INSERT INTO chunks (content, indexed_at, kind) VALUES (?, ?, ?)",
        ("null kind chunk", now, None),
    )
    conn.commit()
    conn.close()
    return db_path


class TestCheckCorpusFreshness:
    def test_detects_stale_brain(self, fresh_db):
        from providers.brain_rag import _check_corpus_freshness
        conn = sqlite3.connect(str(fresh_db))
        freshness = _check_corpus_freshness(conn)
        conn.close()
        assert "brain" in freshness
        # max(indexed_at) for brain is the stale one (120 days ago)
        assert freshness["brain"]["stale"] is True
        assert freshness["brain"]["age_days"] > 100

    def test_fresh_conversation_not_stale(self, fresh_db):
        from providers.brain_rag import _check_corpus_freshness
        conn = sqlite3.connect(str(fresh_db))
        freshness = _check_corpus_freshness(conn)
        conn.close()
        assert "conversation" in freshness
        assert freshness["conversation"]["stale"] is False
        assert freshness["conversation"]["age_days"] < 1

    def test_null_kind_handled(self, fresh_db):
        from providers.brain_rag import _check_corpus_freshness
        conn = sqlite3.connect(str(fresh_db))
        freshness = _check_corpus_freshness(conn)
        conn.close()
        assert "unknown" in freshness

    def test_count_correct(self, fresh_db):
        from providers.brain_rag import _check_corpus_freshness
        conn = sqlite3.connect(str(fresh_db))
        freshness = _check_corpus_freshness(conn)
        conn.close()
        assert freshness["brain"]["count"] == 1
        assert freshness["conversation"]["count"] == 1

    def test_empty_db_returns_empty(self, tmp_path):
        from providers.brain_rag import _check_corpus_freshness
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE chunks (
                id INTEGER PRIMARY KEY,
                content TEXT,
                embedding BLOB,
                content_hash TEXT,
                word_count INTEGER,
                priority_tier INTEGER,
                file_mtime REAL,
                indexed_at REAL,
                kind TEXT,
                source_archive TEXT,
                external_ts REAL,
                session_id TEXT,
                project TEXT,
                agent_role TEXT,
                confidentiality TEXT,
                topic_label TEXT,
                original_path TEXT
            )
        """)
        conn.commit()
        freshness = _check_corpus_freshness(conn)
        conn.close()
        assert freshness == {}


class TestFormatFreshnessWarning:
    def test_no_stale_returns_empty(self):
        from providers.brain_rag import _format_freshness_warning
        freshness = {
            "brain": {"count": 100, "max_indexed_at": time.time(), "age_days": 0.5, "stale": False},
            "conversation": {"count": 50, "max_indexed_at": time.time(), "age_days": 0.1, "stale": False},
        }
        assert _format_freshness_warning(freshness) == ""

    def test_stale_produces_warning(self):
        from providers.brain_rag import _format_freshness_warning
        freshness = {
            "brain": {"count": 52333, "max_indexed_at": 1.0, "age_days": 119.4, "stale": True},
            "conversation": {"count": 50, "max_indexed_at": time.time(), "age_days": 0.1, "stale": False},
        }
        warning = _format_freshness_warning(freshness)
        assert "STALE CORPUS WARNING" in warning
        assert "brain" in warning
        assert "119.4d" in warning
        assert "conversation" not in warning  # fresh kind not in warning

    def test_multiple_stale_kinds(self):
        from providers.brain_rag import _format_freshness_warning
        freshness = {
            "brain": {"count": 100, "max_indexed_at": 1.0, "age_days": 119.0, "stale": True},
            "telegram": {"count": 50, "max_indexed_at": 1.0, "age_days": 90.0, "stale": True},
        }
        warning = _format_freshness_warning(freshness)
        assert "brain" in warning
        assert "telegram" in warning

    def test_empty_freshness_returns_empty(self):
        from providers.brain_rag import _format_freshness_warning
        assert _format_freshness_warning({}) == ""
