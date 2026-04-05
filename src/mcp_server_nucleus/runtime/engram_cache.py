"""
Engram Cache — In-memory index for JSONL ledger reads.
======================================================
Eliminates O(n) full-file scans on every query/search by maintaining
an in-memory cache with file-modification-time invalidation.

Thread-safe. Falls back gracefully to direct file reads on any error.
"""

import json
import os
import threading
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.engram_cache")


class EngramCache:
    """In-memory cache for the engram JSONL ledger.

    Provides O(1) lookups by key and fast filtered queries by context
    and intensity, avoiding repeated full-file scans.

    Invalidation: Checks file mtime before each access. If the file
    changed since last load, re-reads it. This is a single stat() call
    per access (microseconds) vs reading potentially thousands of lines.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._engrams: List[Dict] = []
        self._by_key: Dict[str, Dict] = {}
        self._by_context: Dict[str, List[Dict]] = {}
        self._last_mtime: float = 0.0
        self._last_path: Optional[str] = None
        self._load_count: int = 0

    def _needs_reload(self, ledger_path: Path) -> bool:
        """Check if cache is stale (file modified since last load)."""
        try:
            current_mtime = ledger_path.stat().st_mtime
            return (
                str(ledger_path) != self._last_path
                or current_mtime != self._last_mtime
            )
        except OSError:
            return True

    def _load(self, ledger_path: Path) -> None:
        """Reload the cache from the JSONL file."""
        engrams = []
        by_key = {}
        by_context: Dict[str, List[Dict]] = {}

        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        e = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue

                    if e.get("deleted", False) or e.get("quarantined", False):
                        continue

                    engrams.append(e)
                    key = e.get("key", "")
                    if key:
                        by_key[key] = e
                    ctx = e.get("context", "").lower()
                    if ctx not in by_context:
                        by_context[ctx] = []
                    by_context[ctx].append(e)

            self._engrams = engrams
            self._by_key = by_key
            self._by_context = by_context
            self._last_mtime = ledger_path.stat().st_mtime
            self._last_path = str(ledger_path)
            self._load_count += 1
        except OSError as e:
            logger.debug(f"EngramCache load failed: {e}")
            self._engrams = []
            self._by_key = {}
            self._by_context = {}

    def _ensure_loaded(self, ledger_path: Path) -> None:
        """Ensure cache is fresh (reload if stale)."""
        if self._needs_reload(ledger_path):
            self._load(ledger_path)

    def query(self, ledger_path: Path, context: Optional[str] = None,
              min_intensity: int = 1, limit: int = 50) -> Tuple[List[Dict], int]:
        """Query engrams with optional context and intensity filters.

        Returns:
            Tuple of (engrams list limited to `limit`, total_matching count).
        """
        with self._lock:
            self._ensure_loaded(ledger_path)

            if context:
                candidates = self._by_context.get(context.lower(), [])
            else:
                candidates = self._engrams

            filtered = [e for e in candidates if e.get("intensity", 5) >= min_intensity]
            filtered.sort(key=lambda x: x.get("intensity", 5), reverse=True)

            total = len(filtered)
            return filtered[:limit], total

    def search(self, ledger_path: Path, query: str,
               case_sensitive: bool = False, limit: int = 50) -> Tuple[List[Dict], int]:
        """Substring search across engram keys and values.

        Returns:
            Tuple of (matched engrams with _match_in metadata, total_matching count).
        """
        with self._lock:
            self._ensure_loaded(ledger_path)

            search_q = query if case_sensitive else query.lower()
            matches = []

            for e in self._engrams:
                key = e.get("key", "")
                value = e.get("value", "")
                key_s = key if case_sensitive else key.lower()
                value_s = value if case_sensitive else value.lower()

                match_in = []
                if search_q in key_s:
                    match_in.append("key")
                if search_q in value_s:
                    match_in.append("value")

                if match_in:
                    result = dict(e)
                    result["_match_in"] = match_in
                    matches.append(result)

            matches.sort(key=lambda x: x.get("intensity", 5), reverse=True)
            total = len(matches)
            return matches[:limit], total

    def get_by_key(self, ledger_path: Path, key: str) -> Optional[Dict]:
        """O(1) lookup by engram key."""
        with self._lock:
            self._ensure_loaded(ledger_path)
            return self._by_key.get(key)

    def invalidate(self) -> None:
        """Force cache invalidation (e.g., after a write)."""
        with self._lock:
            self._last_mtime = 0.0
            self._last_path = None

    @property
    def stats(self) -> Dict:
        """Cache statistics for diagnostics."""
        with self._lock:
            return {
                "cached_engrams": len(self._engrams),
                "contexts": list(self._by_context.keys()),
                "unique_keys": len(self._by_key),
                "load_count": self._load_count,
                "last_path": self._last_path,
            }


# Global singleton
_cache = EngramCache()


def get_engram_cache() -> EngramCache:
    """Get the global engram cache instance."""
    return _cache
