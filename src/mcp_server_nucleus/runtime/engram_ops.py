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
from datetime import datetime
from pathlib import Path

from .common import get_brain_path, make_response
from .event_ops import _emit_event


def _brain_write_engram_impl(key: str, value: str, context: str, intensity: int) -> str:
    """Implementation for engram writing — MDR_014 ADUN Protocol.
    
    Uses the MemoryPipeline for deterministic ADD/UPDATE/DELETE/NOOP operations.
    """
    try:
        # V9.1 Security Hardening: Key Validation
        if not key or len(key.strip()) < 2:
            import sys
            print(f"[NUCLEUS] SECURITY VIOLATION: Empty or short key detected", file=sys.stderr)
            return make_response(False, error="Security Violation: Key must be at least 2 characters")
            
        if not re.match(r"^[a-zA-Z0-9_.-]+$", key):
            import sys
            print(f"[NUCLEUS] SECURITY VIOLATION: Invalid key pattern detected", file=sys.stderr)
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
        return make_response(False, error=f"Error writing engram: {e}")


def _brain_query_engrams_impl(context: str, min_intensity: int) -> str:
    """Implementation for engram querying."""
    try:
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"
        
        if not engram_path.exists():
            return make_response(True, data={
                "engrams": [],
                "count": 0,
                "message": "No engrams found. Use brain_write_engram() to create."
            })
        
        engrams = []
        with open(engram_path, "r") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    # Filter by context if specified
                    if context and e.get("context", "").lower() != context.lower():
                        continue
                    # Filter by minimum intensity
                    if e.get("intensity", 5) < min_intensity:
                        continue
                    engrams.append(e)
        
        # Sort by intensity (highest first)
        engrams.sort(key=lambda x: x.get("intensity", 5), reverse=True)
        
        return make_response(True, data={
            "engrams": engrams,
            "count": len(engrams),
            "filters": {"context": context, "min_intensity": min_intensity}
        })
    except Exception as e:
        return make_response(False, error=f"Error querying engrams: {e}")


def _brain_search_engrams_impl(query: str, case_sensitive: bool = False) -> str:
    """Implementation for engram substring search."""
    try:
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"
        
        if not engram_path.exists():
            return make_response(True, data={
                "engrams": [],
                "count": 0,
                "query": query,
                "message": "No engrams found. Use brain_write_engram() to create."
            })
        
        search_query = query if case_sensitive else query.lower()
        matches = []
        
        with open(engram_path, "r") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    key = e.get("key", "")
                    value = e.get("value", "")
                    
                    key_search = key if case_sensitive else key.lower()
                    value_search = value if case_sensitive else value.lower()
                    
                    if search_query in key_search or search_query in value_search:
                        e["_match_in"] = []
                        if search_query in key_search:
                            e["_match_in"].append("key")
                        if search_query in value_search:
                            e["_match_in"].append("value")
                        matches.append(e)
        
        matches.sort(key=lambda x: x.get("intensity", 5), reverse=True)
        
        return make_response(True, data={
            "engrams": matches,
            "count": len(matches),
            "query": query,
            "case_sensitive": case_sensitive
        })
    except Exception as e:
        return make_response(False, error=f"Error searching engrams: {e}")


def _brain_governance_status_impl() -> str:
    """Implementation for governance status."""
    try:
        brain = get_brain_path()
        
        # Check audit log
        audit_path = brain / "ledger" / "interaction_log.jsonl"
        audit_count = 0
        if audit_path.exists():
            with open(audit_path, "r") as f:
                audit_count = sum(1 for line in f if line.strip())
        
        # Check engrams
        engram_path = brain / "engrams" / "ledger.jsonl"
        engram_count = 0
        if engram_path.exists():
            with open(engram_path, "r") as f:
                engram_count = sum(1 for line in f if line.strip())
        
        # Check events
        events_path = brain / "ledger" / "events.jsonl"
        events_count = 0
        if events_path.exists():
            with open(events_path, "r") as f:
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
        return make_response(False, error=f"Error checking governance: {e}")
