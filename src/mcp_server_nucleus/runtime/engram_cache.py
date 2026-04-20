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

# Maximum engrams to hold in memory. When the ledger exceeds this,
# only the most recent entries are cached (oldest are dropped).
MAX_CACHED_ENGRAMS = 10_000


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
        self._total_on_disk: int = 0
        self._capped: bool = False
        # Independent state for history.jsonl (Store-shape projection store).
        # Tracked separately so a write to one file does not invalidate the other.
        self._history_engrams: List[Dict] = []
        self._history_last_mtime: float = 0.0
        self._history_last_path: Optional[str] = None
        self._history_load_count: int = 0
        self._history_total_on_disk: int = 0
        self._history_capped: bool = False

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

            total_on_disk = len(engrams)
            capped = total_on_disk > MAX_CACHED_ENGRAMS
            if capped:
                # Keep only the most recent entries (tail of file)
                engrams = engrams[-MAX_CACHED_ENGRAMS:]
                by_key = {e.get("key", ""): e for e in engrams if e.get("key")}
                by_context = {}
                for e in engrams:
                    ctx = e.get("context", "").lower()
                    if ctx not in by_context:
                        by_context[ctx] = []
                    by_context[ctx].append(e)
                logger.info(f"EngramCache capped: {total_on_disk} on disk, {MAX_CACHED_ENGRAMS} cached")

            self._engrams = engrams
            self._by_key = by_key
            self._by_context = by_context
            self._total_on_disk = total_on_disk
            self._capped = capped
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

    @staticmethod
    def _normalize_history_row(row: Dict) -> Optional[Dict]:
        """Flatten a Store-shape history row into ledger-shape.

        history.jsonl wraps each record as ``{key, op_type, timestamp, snapshot:
        {key, value, context, intensity, version, source_agent, op_type,
        timestamp, deleted, signature}}``. Search consumers expect the flat
        ledger shape ``{key, value, context, intensity, timestamp, signature}``.
        Returns None for malformed rows or rows marked deleted.
        """
        if "snapshot" not in row:
            return None
        snap = row.get("snapshot")
        if not isinstance(snap, dict):
            return None
        if snap.get("deleted") is True:
            return None
        key = snap.get("key") or row.get("key")
        if not key:
            return None
        return {
            "key": key,
            "value": snap.get("value", "") or "",
            "context": snap.get("context", "") or "",
            "intensity": snap.get("intensity", 5),
            "timestamp": snap.get("timestamp") or row.get("timestamp", ""),
            "signature": snap.get("signature"),
            "source_agent": snap.get("source_agent", ""),
        }

    def _needs_reload_history(self, history_path: Path) -> bool:
        try:
            current_mtime = history_path.stat().st_mtime
            return (
                str(history_path) != self._history_last_path
                or current_mtime != self._history_last_mtime
            )
        except OSError:
            return True

    def _load_history(self, history_path: Path) -> None:
        """Reload the history-side cache from history.jsonl (Store shape)."""
        history_engrams: List[Dict] = []
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        raw = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    flat = self._normalize_history_row(raw)
                    if flat is not None:
                        history_engrams.append(flat)

            total_on_disk = len(history_engrams)
            capped = total_on_disk > MAX_CACHED_ENGRAMS
            if capped:
                history_engrams = history_engrams[-MAX_CACHED_ENGRAMS:]
                logger.info(
                    f"EngramCache (history) capped: {total_on_disk} on disk, "
                    f"{MAX_CACHED_ENGRAMS} cached"
                )

            self._history_engrams = history_engrams
            self._history_total_on_disk = total_on_disk
            self._history_capped = capped
            self._history_last_mtime = history_path.stat().st_mtime
            self._history_last_path = str(history_path)
            self._history_load_count += 1
        except OSError as e:
            logger.debug(f"EngramCache history load failed: {e}")
            self._history_engrams = []

    def _ensure_loaded_history(self, history_path: Path) -> None:
        if not history_path.exists():
            self._history_engrams = []
            self._history_last_mtime = 0.0
            self._history_last_path = str(history_path)
            return
        if self._needs_reload_history(history_path):
            self._load_history(history_path)

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

    def search_dual(
        self,
        ledger_path: Path,
        history_path: Path,
        query: str,
        case_sensitive: bool = False,
        limit: int = 50,
    ) -> Tuple[List[Dict], int]:
        """Substring search across both ledger.jsonl and history.jsonl.

        Per Cowork directive d70e01bf: read-side fix for store-divergence.
        Adds a 'source' field ('ledger' or 'history') to every result row so
        consumers can see substrate-handoff topology. Dedup policy: if the
        same key appears in both files, the ledger version wins and the
        history version is dropped (debug log emitted on dedup hit).
        """
        with self._lock:
            self._ensure_loaded(ledger_path)
            self._ensure_loaded_history(history_path)

            search_q = query if case_sensitive else query.lower()
            matches: List[Dict] = []
            seen_keys: Dict[str, str] = {}

            def _scan(records: List[Dict], source: str) -> None:
                for e in records:
                    key = e.get("key", "")
                    value = e.get("value", "")
                    key_s = key if case_sensitive else key.lower()
                    value_s = value if case_sensitive else value.lower()
                    match_in = []
                    if search_q in key_s:
                        match_in.append("key")
                    if search_q in value_s:
                        match_in.append("value")
                    if not match_in:
                        continue
                    if key and key in seen_keys:
                        logger.debug(
                            f"EngramCache.search_dual dedup: key={key!r} "
                            f"present in {seen_keys[key]} and {source}; "
                            f"keeping {seen_keys[key]}"
                        )
                        continue
                    result = dict(e)
                    result["_match_in"] = match_in
                    result["source"] = source
                    matches.append(result)
                    if key:
                        seen_keys[key] = source

            _scan(self._engrams, "ledger")
            _scan(self._history_engrams, "history")

            matches.sort(key=lambda x: x.get("intensity", 5), reverse=True)
            total = len(matches)
            return matches[:limit], total

    def get_by_key(self, ledger_path: Path, key: str) -> Optional[Dict]:
        """O(1) lookup by engram key."""
        with self._lock:
            self._ensure_loaded(ledger_path)
            return self._by_key.get(key)

    def invalidate(self) -> None:
        """Force cache invalidation (e.g., after a write).

        Invalidates BOTH ledger and history caches — write paths may land
        in either file (write_engram → ledger, relay projection → history),
        so a write event must invalidate both to keep search consistent.
        """
        with self._lock:
            self._last_mtime = 0.0
            self._last_path = None
            self._history_last_mtime = 0.0
            self._history_last_path = None

    @property
    def stats(self) -> Dict:
        """Cache statistics for diagnostics."""
        with self._lock:
            return {
                "cached_engrams": len(self._engrams),
                "total_on_disk": self._total_on_disk,
                "capped": self._capped,
                "max_cached": MAX_CACHED_ENGRAMS,
                "contexts": list(self._by_context.keys()),
                "unique_keys": len(self._by_key),
                "load_count": self._load_count,
                "last_path": self._last_path,
                "history_cached_engrams": len(self._history_engrams),
                "history_total_on_disk": self._history_total_on_disk,
                "history_capped": self._history_capped,
                "history_load_count": self._history_load_count,
                "history_last_path": self._history_last_path,
            }


# Global singleton
_cache = EngramCache()


def get_engram_cache() -> EngramCache:
    """Get the global engram cache instance."""
    return _cache
