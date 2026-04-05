"""Engram Operations — Cognitive memory ledger implementation.

Extracted from __init__.py (Engram Ledger / N-SOS V1).
Contains:
- _brain_write_engram_impl: Write engrams with security validation
- _brain_query_engrams_impl: Query engrams by context/intensity
- _brain_search_engrams_impl: Substring search across engrams
- _brain_governance_status_impl: Governance status reporting
"""

import json
import os
import re

from .common import get_brain_path, make_response
from .event_ops import _emit_event


def _brain_write_engram_impl(key: str, value: str, context: str, intensity: int) -> str:
    """Implementation for engram writing — MDR_014 ADUN Protocol.
    
    Uses the MemoryPipeline for deterministic ADD/UPDATE/DELETE/NOOP operations.
    
    Args:
        key: Alphanumeric identifier (min 2 chars, pattern: [a-zA-Z0-9_.-]+)
        value: The engram content text
        context: One of: Feature, Architecture, Brand, Strategy, Decision
        intensity: 1-10 scale (10 = highest importance)
    """
    try:
        # V9.1 Security Hardening: Key Validation
        if not key or len(key.strip()) < 2:
            import sys
            print("[NUCLEUS] SECURITY VIOLATION: Empty or short key detected", file=sys.stderr)
            return make_response(False, error="Security Violation: Key must be at least 2 characters")
            
        if not re.match(r"^[a-zA-Z0-9_.-]+$", key):
            import sys
            print("[NUCLEUS] SECURITY VIOLATION: Invalid key pattern detected", file=sys.stderr)
            return make_response(False, error="Security Violation: Key contains invalid characters")

        # Validate intensity
        if not 1 <= intensity <= 10:
            return make_response(False, error="Intensity must be between 1 and 10")
        
        # Validate context
        valid_contexts = ["Feature", "Architecture", "Brand", "Strategy", "Decision"]
        if context not in valid_contexts:
            return make_response(False, error=f"Context must be one of: {valid_contexts}")
        
        brain = get_brain_path()
        
        # MDR_014: Use ADUN Pipeline instead of raw append
        from .memory_pipeline import MemoryPipeline
        pipeline = MemoryPipeline(brain)
        result = pipeline.process(
            text=value,
            context=context,
            intensity=intensity,
            source_agent="brain_write_engram",
            key=key,
        )
        
        # Invalidate cache after write
        try:
            from .engram_cache import get_engram_cache
            get_engram_cache().invalidate()
        except Exception:
            pass

        # Emit event for audit trail
        _emit_event("engram_written", "brain_write_engram", {
            "key": key,
            "context": context,
            "intensity": intensity,
            "adun_result": {
                "added": result.get("added", 0),
                "updated": result.get("updated", 0),
                "skipped": result.get("skipped", 0),
                "mode": result.get("mode", "unknown"),
            }
        })
        
        return make_response(True, data={
            "key": key,
            "value": value,
            "context": context,
            "intensity": intensity,
            "adun": result,
            "message": f"Engram '{key}' processed via ADUN pipeline ({result.get('mode', 'unknown')})"
        })
    except Exception as e:
        from .error_sanitizer import sanitize_error
        return make_response(False, error=sanitize_error(e, "internal_error", "engram_write"))


def _brain_query_engrams_impl(context: str, min_intensity: int, limit: int = 50) -> str:
    """Implementation for engram querying.

    Args:
        context: Filter by context category (case-insensitive). None = all.
        min_intensity: Minimum intensity threshold (1-10).
        limit: Max engrams to return (default 50, max 500). Prevents context exhaustion.
    """
    try:
        # Clamp limit to safe range
        limit = max(1, min(int(limit), 500))

        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"

        if not engram_path.exists():
            return make_response(True, data={
                "engrams": [],
                "count": 0,
                "total_matching": 0,
                "truncated": False,
                "limit": limit,
                "message": "No engrams found. Use write_engram to create."
            })

        # Use in-memory cache for O(1) repeated reads (mtime-invalidated)
        from .engram_cache import get_engram_cache
        engrams, total_matching = get_engram_cache().query(
            engram_path, context=context, min_intensity=min_intensity, limit=limit
        )

        truncated = total_matching > limit

        return make_response(True, data={
            "engrams": engrams,
            "count": len(engrams),
            "total_matching": total_matching,
            "truncated": truncated,
            "limit": limit,
            "filters": {"context": context, "min_intensity": min_intensity}
        })
    except Exception as e:
        from .error_sanitizer import sanitize_error
        return make_response(False, error=sanitize_error(e, "internal_error", "engram_query"))


def _brain_search_engrams_impl(query: str, case_sensitive: bool = False, limit: int = 50) -> str:
    """Implementation for engram substring search.

    Args:
        query: Substring to search for in engram keys and values.
        case_sensitive: Whether to match case. Default False.
        limit: Max engrams to return (default 50, max 500). Prevents context exhaustion.
    """
    try:
        limit = max(1, min(int(limit), 500))

        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"

        if not engram_path.exists():
            return make_response(True, data={
                "engrams": [],
                "count": 0,
                "total_matching": 0,
                "truncated": False,
                "limit": limit,
                "query": query,
                "message": "No engrams found. Use write_engram to create."
            })

        # Use in-memory cache for O(1) repeated reads (mtime-invalidated)
        from .engram_cache import get_engram_cache
        matches, total_matching = get_engram_cache().search(
            engram_path, query=query, case_sensitive=case_sensitive, limit=limit
        )

        truncated = total_matching > limit

        return make_response(True, data={
            "engrams": matches,
            "count": len(matches),
            "total_matching": total_matching,
            "truncated": truncated,
            "limit": limit,
            "query": query,
            "case_sensitive": case_sensitive
        })
    except Exception as e:
        from .error_sanitizer import sanitize_error
        return make_response(False, error=sanitize_error(e, "internal_error", "engram_search"))


def _brain_governance_status_impl() -> str:
    """Implementation for governance status."""
    try:
        brain = get_brain_path()
        
        # Check audit log
        audit_path = brain / "ledger" / "interaction_log.jsonl"
        audit_count = 0
        if audit_path.exists():
            with open(audit_path, "r", encoding="utf-8") as f:
                audit_count = sum(1 for line in f if line.strip())
        
        # Check engrams
        engram_path = brain / "engrams" / "ledger.jsonl"
        engram_count = 0
        if engram_path.exists():
            with open(engram_path, "r", encoding="utf-8") as f:
                engram_count = sum(1 for line in f if line.strip())
        
        # Check events
        events_path = brain / "ledger" / "events.jsonl"
        events_count = 0
        if events_path.exists():
            with open(events_path, "r", encoding="utf-8") as f:
                events_count = sum(1 for line in f if line.strip())
        
        # Security config
        v9_security = os.environ.get("NUCLEUS_V9_SECURITY", "false").lower() == "true"
        
        governance = {
            "policies": {
                "default_deny": True,  # Always enforced
                "isolation_boundaries": True,  # Always enforced
                "immutable_audit": v9_security,
                "cryptographic_hashing": v9_security
            },
            "statistics": {
                "audit_log_entries": audit_count,
                "engram_count": engram_count,
                "events_logged": events_count
            },
            "configuration": {
                "v9_security_enabled": v9_security,
                "brain_path": str(brain)
            },
            "status": "ENFORCED" if v9_security else "PARTIAL"
        }
        
        return make_response(True, data=governance)
    except Exception as e:
        from .error_sanitizer import sanitize_error
        return make_response(False, error=sanitize_error(e, "internal_error", "governance_status"))

def _dsor_query_decisions_impl(limit: int = 50) -> str:
    """Implementation for querying the DSoR decision ledger."""
    try:
        limit = max(1, min(int(limit), 500))
        brain = get_brain_path()
        decisions_path = brain / "ledger" / "decisions" / "decisions.jsonl"
        
        if not decisions_path.exists():
            return make_response(True, data={
                "decisions": [],
                "count": 0,
                "message": "No decisions found. DSoR ledger is empty."
            })
            
        decisions = []
        with open(decisions_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        e = json.loads(line)
                        decisions.append(e)
                    except json.JSONDecodeError:
                        continue
                        
        # Reverse chronologically
        decisions.reverse()
        total_matching = len(decisions)
        truncated = total_matching > limit
        decisions = decisions[:limit]
        
        return make_response(True, data={
            "decisions": decisions,
            "count": len(decisions),
            "total_matching": total_matching,
            "truncated": truncated
        })
    except Exception as e:
        from .error_sanitizer import sanitize_error
        return make_response(False, error=sanitize_error(e, "internal_error", "dsor_query_decisions"))

def _dsor_get_trace_impl(decision_id: str) -> str:
    """Implementation for visualizing a specific decision trace."""
    try:
        brain = get_brain_path()
        decisions_path = brain / "ledger" / "decisions" / "decisions.jsonl"
        
        target_decision = None
        if decisions_path.exists():
            with open(decisions_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            e = json.loads(line)
                            if e.get("decision_id") == decision_id:
                                target_decision = e
                                break
                        except json.JSONDecodeError:
                            continue
        
        if not target_decision:
            return make_response(False, error=f"Decision ID {decision_id} not found in ledger.")
            
        trace = {
            "decision": target_decision,
            "context_snapshot": None
        }
        
        # Retrieve the context snapshot matching the decision's context_hash
        snapshots_dir = brain / "ledger" / "snapshots"
        if snapshots_dir.exists():
            for snap_file in snapshots_dir.glob("*.json"):
                try:
                    sdata = json.loads(snap_file.read_text())
                    if sdata.get("state_hash") == target_decision.get("context_hash"):
                        trace["context_snapshot"] = sdata
                        break
                except Exception:
                    continue
                    
        return make_response(True, data={"trace": trace})
    except Exception as e:
        from .error_sanitizer import sanitize_error
        return make_response(False, error=sanitize_error(e, "internal_error", "dsor_get_trace"))
