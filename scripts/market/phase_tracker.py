#!/usr/bin/env python3
"""Market phase tracker — adoption telemetry + Prometheus gauge.

Detects which market entry phase Nucleus is in based on relay sender analysis:
- Phase 1: Founding team only (internal tools)
- Phase 2: First external tool connected
- Phase 3: Registry threshold (5+ external tools)
- Phase 4: Network flip (external-to-external relays >= external-to-internal)

Exports Prometheus metrics compatible with #238 /metrics endpoint.
"""

import os
import sys
import json
import glob
from dataclasses import dataclass
from typing import Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta

# Internal tools that don't count as "external"
INTERNAL_SENDERS = {
    "claude_code_main", "claude_code_peer", "claude_code_tb",
    "cowork", "windsurf", "antigravity", "gemini_cli",
    "perplexity", "cursor", "codex", "e2b"
}

PHASE_NAMES = {
    1: "founding_team",
    2: "first_external",
    3: "registry",
    4: "network_flip"
}


@dataclass
class PhaseMetrics:
    phase: int
    internal_tools: int
    external_tools: int
    external_to_external_7d: int
    external_to_internal_7d: int
    evidence: str


def get_relay_dirs(brain_path: Optional[str] = None) -> list:
    """Find all relay directories in .brain."""
    if brain_path is None:
        brain_path = os.path.expanduser("~/ai-mvp-backend/.brain")
    relay_base = os.path.join(brain_path, "relay")
    if not os.path.exists(relay_base):
        return []
    return [d for d in os.listdir(relay_base) if os.path.isdir(os.path.join(relay_base, d))]


def extract_senders_from_relays(relay_dirs: list, brain_path: Optional[str] = None, days: int = 7) -> Tuple[Set[str], dict]:
    """Extract unique senders and relay patterns from recent relay files."""
    if brain_path is None:
        brain_path = os.path.expanduser("~/ai-mvp-backend/.brain")
    
    all_senders = set()
    relay_patterns = defaultdict(int)
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    for relay_bucket in relay_dirs:
        relay_path = os.path.join(brain_path, "relay", relay_bucket)
        json_files = glob.glob(os.path.join(relay_path, "*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Check timestamp if available
                created_at = data.get('created_at', '')
                if created_at:
                    try:
                        # Parse ISO format
                        ts = datetime.fromisoformat(created_at.replace('Z', '+00:00').replace('+00:00', ''))
                        if ts < cutoff:
                            continue
                    except:
                        pass
                
                sender = data.get('from', data.get('sender', ''))
                recipient = data.get('to', relay_bucket)
                
                if sender:
                    all_senders.add(sender)
                
                # Track external-to-external vs external-to-internal patterns
                is_sender_external = sender not in INTERNAL_SENDERS and sender not in {'windsurf', 'antigravity'}
                is_recipient_external = recipient not in INTERNAL_SENDERS and recipient not in {'windsurf', 'antigravity'}
                
                if is_sender_external:
                    if is_recipient_external:
                        relay_patterns['ext_to_ext'] += 1
                    else:
                        relay_patterns['ext_to_int'] += 1
                        
            except (json.JSONDecodeError, IOError):
                continue
    
    return all_senders, dict(relay_patterns)


def detect_phase(senders: Set[str], relay_patterns: dict) -> Tuple[int, str]:
    """Detect market phase based on sender composition and relay patterns."""
    external_senders = senders - INTERNAL_SENDERS
    internal_senders = senders & INTERNAL_SENDERS
    
    ext_count = len(external_senders)
    int_count = len(internal_senders)
    
    ext_to_ext = relay_patterns.get('ext_to_ext', 0)
    ext_to_int = relay_patterns.get('ext_to_int', 1)  # Avoid div by zero
    
    # Phase 4: Network flip — external-to-external >= external-to-internal
    if ext_count >= 2 and ext_to_ext >= ext_to_int:
        evidence = f"Network flip: {ext_to_ext} ext-to-ext >= {ext_to_int} ext-to-int relays (7d)"
        return 4, evidence
    
    # Phase 3: Registry threshold — 5+ external tools
    if ext_count >= 5:
        evidence = f"Registry: {ext_count} external tools connected (threshold: 5)"
        return 3, evidence
    
    # Phase 2: First external tool
    if ext_count >= 1:
        evidence = f"First external: {ext_count} external tool(s): {', '.join(list(external_senders)[:3])}"
        return 2, evidence
    
    # Phase 1: Founding team only
    evidence = f"Founding team: {int_count} internal tools, 0 external"
    return 1, evidence


def compute_metrics(brain_path: Optional[str] = None, days: int = 7) -> PhaseMetrics:
    """Compute full phase metrics from relay data."""
    relay_dirs = get_relay_dirs(brain_path)
    senders, patterns = extract_senders_from_relays(relay_dirs, brain_path, days)
    
    external_senders = senders - INTERNAL_SENDERS
    internal_senders = senders & INTERNAL_SENDERS
    
    phase, evidence = detect_phase(senders, patterns)
    
    return PhaseMetrics(
        phase=phase,
        internal_tools=len(internal_senders),
        external_tools=len(external_senders),
        external_to_external_7d=patterns.get('ext_to_ext', 0),
        external_to_internal_7d=patterns.get('ext_to_int', 0),
        evidence=evidence
    )


def output_prometheus(metrics: PhaseMetrics) -> str:
    """Generate Prometheus exposition format."""
    lines = [
        "# HELP nucleus_market_phase Current market entry phase (1=founding, 2=first_external, 3=registry, 4=network_flip)",
        "# TYPE nucleus_market_phase gauge",
        f"nucleus_market_phase {metrics.phase}",
        "",
        "# HELP nucleus_connected_tools_total Number of connected tools by type",
        "# TYPE nucleus_connected_tools_total counter",
        f'nucleus_connected_tools_total{{type="internal"}} {metrics.internal_tools}',
        f'nucleus_connected_tools_total{{type="external"}} {metrics.external_tools}',
        "",
        "# HELP nucleus_cross_tool_relay_events_total Cross-tool relay events in last 7 days",
        "# TYPE nucleus_cross_tool_relay_events_total counter",
        f'nucleus_cross_tool_relay_events_total{{direction="ext_to_ext"}} {metrics.external_to_external_7d}',
        f'nucleus_cross_tool_relay_events_total{{direction="ext_to_int"}} {metrics.external_to_internal_7d}',
    ]
    return "\n".join(lines)


def output_json(metrics: PhaseMetrics) -> str:
    """Generate JSON output."""
    return json.dumps({
        "phase": metrics.phase,
        "phase_name": PHASE_NAMES.get(metrics.phase, "unknown"),
        "internal_tools": metrics.internal_tools,
        "external_tools": metrics.external_tools,
        "external_to_external_7d": metrics.external_to_external_7d,
        "external_to_internal_7d": metrics.external_to_internal_7d,
        "evidence": metrics.evidence,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }, indent=2)


def output_human(metrics: PhaseMetrics) -> str:
    """Generate human-readable output."""
    lines = [
        f"=== Nucleus Market Phase ===",
        f"",
        f"Phase {metrics.phase}: {PHASE_NAMES.get(metrics.phase, 'unknown').replace('_', ' ').title()}",
        f"",
        f"Connected Tools:",
        f"  Internal: {metrics.internal_tools}",
        f"  External: {metrics.external_tools}",
        f"",
        f"7-Day Relay Patterns:",
        f"  External → External: {metrics.external_to_external_7d}",
        f"  External → Internal: {metrics.external_to_internal_7d}",
        f"",
        f"Evidence: {metrics.evidence}",
    ]
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Market phase tracker for Nucleus adoption")
    parser.add_argument("--brain-path", help="Path to .brain directory (default: ~/ai-mvp-backend/.brain)")
    parser.add_argument("--days", type=int, default=7, help="Days to look back for relay patterns (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--prometheus", action="store_true", help="Output Prometheus exposition format")
    args = parser.parse_args()
    
    brain_path = args.brain_path or os.path.expanduser("~/ai-mvp-backend/.brain")
    
    if not os.path.exists(brain_path):
        print(f"Error: Brain path not found: {brain_path}", file=sys.stderr)
        sys.exit(1)
    
    metrics = compute_metrics(brain_path, args.days)
    
    if args.prometheus:
        print(output_prometheus(metrics))
    elif args.json:
        print(output_json(metrics))
    else:
        print(output_human(metrics))


if __name__ == "__main__":
    main()
