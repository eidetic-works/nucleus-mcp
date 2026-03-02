"""Ingestion Operations — Task ingestion from various sources.

Extracted from __init__.py (NOP V3.1 Task Ingestion).
Contains:
- _get_ingestion_engine (singleton)
- _brain_ingest_tasks_impl
- _brain_rollback_ingestion_impl
- _brain_ingestion_stats_impl
"""

import os
import sys
from pathlib import Path

from .common import get_brain_path

_ingestion_engine = None


def _get_ingestion_engine():
    """Get or create TaskIngestionEngine singleton."""
    global _ingestion_engine
    if _ingestion_engine is None:
        try:
            # Add nop_v3_refactor to path if needed
            nop_path = Path(__file__).parent.parent.parent.parent.parent / "nop_v3_refactor"
            if str(nop_path) not in sys.path:
                sys.path.insert(0, str(nop_path))
            
            from nop_core.task_ingestion import TaskIngestionEngine
            _ingestion_engine = TaskIngestionEngine(brain_path=get_brain_path())
        except ImportError:
            _ingestion_engine = None
    return _ingestion_engine


def _brain_ingest_tasks_impl(
    source: str,
    source_type: str = "auto",
    session_id: str = None,
    auto_assign: bool = False,
    skip_dedup: bool = False,
    dry_run: bool = False,
) -> str:
    """Internal implementation of brain_ingest_tasks."""
    try:
        engine = _get_ingestion_engine()
        if engine is None:
            return "❌ TaskIngestionEngine not available. Install nop_v3_refactor."
        
        # Detect if source is a file path or raw content
        if os.path.exists(source):
            result = engine.ingest_from_file(
                source,
                source_type=source_type,
                session_id=session_id,
                auto_assign=auto_assign,
                skip_dedup=skip_dedup,
                dry_run=dry_run,
            )
        else:
            result = engine.ingest_from_text(
                source,
                source_type=source_type if source_type != "auto" else "manual",
                session_id=session_id,
                auto_assign=auto_assign,
                skip_dedup=skip_dedup,
                dry_run=dry_run,
            )
        
        # Format output
        from nop_core.task_ingestion import format_ingestion_result
        return format_ingestion_result(result)
        
    except Exception as e:
        return f"❌ Ingestion error: {str(e)}"


def _brain_rollback_ingestion_impl(batch_id: str, reason: str = None) -> str:
    """Internal implementation of brain_rollback_ingestion."""
    try:
        engine = _get_ingestion_engine()
        if engine is None:
            return "❌ TaskIngestionEngine not available."
        
        result = engine.rollback(batch_id, reason)
        
        if result.get("success"):
            return f"✅ Rollback complete\n   Batch: {batch_id}\n   Tasks removed: {result['tasks_removed']}"
        else:
            return f"❌ Rollback failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Rollback error: {str(e)}"


def _brain_ingestion_stats_impl() -> str:
    """Internal implementation of brain_ingestion_stats."""
    try:
        engine = _get_ingestion_engine()
        if engine is None:
            return "❌ TaskIngestionEngine not available."
        
        stats = engine.get_ingestion_stats()
        
        lines = [
            "📊 **Ingestion Statistics**",
            "=" * 40,
            f"   Total ingested: {stats['total_ingested']}",
            f"   Total skipped: {stats['total_skipped']}",
            f"   Total failed: {stats['total_failed']}",
            f"   Batches: {stats['batches_count']}",
            f"   Dedup cache: {stats['dedup_cache_size']}",
        ]
        
        if stats.get("by_source"):
            lines.append("\n📁 **By Source:**")
            for source, count in stats["by_source"].items():
                lines.append(f"   {source}: {count}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ Stats error: {str(e)}"
