"""Capture census — measured engram + relay capture by genuine vendor surface.

PRINCIPAL G1 workstream #0 instrument (docs/PRINCIPAL.md:39,67-69).
Resolves the GLM/Antigravity capture gap with rerunnable evidence: scans the
`.brain/` substrate and reports, per genuine vendor surface, how many relay
envelopes exist and how many engrams are attributable to that surface via the
relay->engram projection keys (`relay_projection_{relay_id}`).

A "genuine vendor surface" is a fleet member whose relay traffic is observable
in `.brain/relay/<bucket>/`. The bucket name + the envelope's `from`/`to`/`
`from_provider` fields are the attribution axes. Engrams are attributed to a
vendor surface ONLY via a relay projection key whose source envelope named
that surface in `from` or `to` — bare `auto_hook`/`brain_write_engram`
operation-type source_agents are NOT vendor attribution (they are the
capture gap itself).

Rerunnable from a clean checkout:
    python3 -m mcp_server_nucleus.runtime.capture_census \\
        --brain-path .brain --json > capture_census_<date>.json
    python3 -m mcp_server_nucleus.runtime.capture_census --brain-path .brain

Exit code 0 always (this is a measurement instrument, not a gate). The JSON
report is the load-bearing artifact; commit it under
`.brain/audits/capture_census/` for tamper-evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

# Vendor-surface classification. A bucket maps to a genuine vendor surface iff
# its traffic is produced BY that vendor's agent runtime (not merely routed
# THROUGH a claude_code coordinator). Classification is keyed on bucket-name
# stems + envelope from_provider; both are greppable/CI-lintable.
VENDOR_SURFACE_BY_BUCKET_STEM: Dict[str, str] = {
    "antigravity": "antigravity",
    "antigravity_gq": "antigravity",
    "antigravity_voice": "antigravity",
    "agy": "antigravity",  # agy = Antigravity's Gemini lane
    "agy_gq": "antigravity",
    "agy_voice": "antigravity",
    "glm_main_agent": "glm",
    "principal_g1_agy": "antigravity",
    "principal_g1_devin": "devin",
    "principal-g1-agy": "antigravity",
    "principal-g1-devin": "devin",
    "devin": "devin",
    "claude_code": "anthropic_claude_code",
    "claude_code_main": "anthropic_claude_code",
    "claude_code_peer": "anthropic_claude_code",
    "cc_main": "anthropic_claude_code",
    "cc_peer": "anthropic_claude_code",
    "cc_gq": "anthropic_claude_code",
    "cc_tb": "anthropic_claude_code",
    "cc_voice": "anthropic_claude_code",
    "cowork": "anthropic_claude_code",  # cowork runs on CC
    "claude_code_agy_gq": "anthropic_claude_code",
    "claude_code_agy_voice": "anthropic_claude_code",
    "claude_code_bespoq_cloud_cc": "anthropic_claude_code",
    "claude_code_cc_gq": "anthropic_claude_code",
    "principal": "anthropic_claude_code",
    "principal_control": "anthropic_claude_code",
    "secretary": "anthropic_claude_code",
    "secretary_archive": "anthropic_claude_code",
    "role_principal_g1": "anthropic_claude_code",
    "peer": "anthropic_claude_code",
    "coordinator": "anthropic_claude_code",
    "op_assistant": "anthropic_claude_code",
    "operator_assistant": "anthropic_claude_code",
    "board": "anthropic_claude_code",
    "main_debug": "anthropic_claude_code",
    "bespoq_cowork": "anthropic_claude_code",
    "claude_code_operator_assistant": "anthropic_claude_code",
    "claude_code_tb": "anthropic_claude_code",
    "claude_code_cc_tb": "anthropic_claude_code",
    "claude_code_ultraplan": "anthropic_claude_code",
    "claude_code_test_hold": "anthropic_claude_code",
    "devin_terminal_agent": "devin",
    "cross_vendor": "mixed",
}

# Test-fixture buckets (synthetic traffic, not genuine fleet surfaces).
TEST_FIXTURE_BUCKETS: Set[str] = {
    "acme_corp",
    "acme_corp_fail",
    "acme_corp_mixed",
}

# from_provider values that map to a vendor surface (when bucket is ambiguous).
VENDOR_SURFACE_BY_FROM_PROVIDER: Dict[str, str] = {
    "anthropic_claude_code": "anthropic_claude_code",
    "claude_code": "anthropic_claude_code",
    "antigravity": "antigravity",
    "google_antigravity": "antigravity",
    "gemini_antigravity": "antigravity",
    "glm": "glm",
    "zhipu_glm": "glm",
    "devin": "devin",
    "cognition_devin": "devin",
}

# Engram source_agent values that ARE vendor-attributing. Two paths:
#   (1) relay projection keys (relay_projection_{relay_id}) — attributed via the
#       source envelope's from/to vendor surface.
#   (2) direct vendor source_agent stamps (devin, agy, devin-swe, ...) — the
#       agent wrote the engram itself with its vendor identity.
# Everything else (auto_hook, brain_write_engram, human, morning_brief, ...) is
# operation-type attribution, NOT vendor surface, and is reported separately.
RELAY_PROJECTION_SOURCE_PREFIX = "relay_projection"
RELAY_PROJECTION_SOURCE = "relay_surface_projection"

# Direct vendor source_agent -> vendor surface map (for path 2).
DIRECT_VENDOR_SOURCE_AGENTS: Dict[str, str] = {
    "devin": "devin",
    "devin-swe": "devin",
    "agy": "antigravity",
    "antigravity": "antigravity",
    "glm": "glm",
    "zhipu_glm": "glm",
}


def _classify_vendor_surface(bucket: str, msg: Dict[str, Any]) -> str:
    """Classify a relay envelope's genuine vendor surface.

    Order: test-fixture check > from_provider (vendor-stamped) > bucket map >
    bucket stem > 'unknown'. Test fixtures are excluded from fleet counts.
    """
    if bucket in TEST_FIXTURE_BUCKETS:
        return "test_fixture"
    fp = msg.get("from_provider")
    if isinstance(fp, str) and fp:
        norm = fp.lower().strip()
        if norm in VENDOR_SURFACE_BY_FROM_PROVIDER:
            return VENDOR_SURFACE_BY_FROM_PROVIDER[norm]
        # heuristic: provider name contains a known vendor token
        for token, surface in VENDOR_SURFACE_BY_FROM_PROVIDER.items():
            if token in norm:
                return surface
    if bucket in VENDOR_SURFACE_BY_BUCKET_STEM:
        return VENDOR_SURFACE_BY_BUCKET_STEM[bucket]
    # bucket stem match (handles dynamic suffixes)
    stem = bucket.split("_")[0]
    if stem in VENDOR_SURFACE_BY_BUCKET_STEM:
        return VENDOR_SURFACE_BY_BUCKET_STEM[stem]
    return "unknown"


def _iter_relay_files(relay_root: Path) -> Iterable[Tuple[str, Path]]:
    """Yield (bucket, path) for every relay envelope file."""
    if not relay_root.is_dir():
        return
    for bucket_dir in sorted(relay_root.iterdir()):
        if not bucket_dir.is_dir():
            continue
        bucket = bucket_dir.name
        for f in sorted(bucket_dir.glob("*.json")):
            if f.name == "pending.json":
                continue
            yield bucket, f


def _scan_relays(relay_root: Path) -> Dict[str, Any]:
    """Scan all relay buckets; count envelopes by vendor surface + bucket."""
    by_surface: Counter = Counter()
    by_bucket: Counter = Counter()
    by_surface_bucket: Dict[str, Counter] = defaultdict(Counter)
    by_from_provider: Counter = Counter()
    errors = 0
    total = 0
    # Track which relay_ids name which vendor surfaces (for engram attribution).
    relay_id_to_surfaces: Dict[str, Set[str]] = defaultdict(set)
    # Track from->to edges by surface for the cross-vendor seam evidence.
    cross_vendor_edges: Counter = Counter()

    for bucket, f in _iter_relay_files(relay_root):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            errors += 1
            continue
        total += 1
        by_bucket[bucket] += 1
        surface = _classify_vendor_surface(bucket, msg)
        by_surface[surface] += 1
        by_surface_bucket[surface][bucket] += 1
        fp = msg.get("from_provider")
        if isinstance(fp, str) and fp:
            by_from_provider[fp] += 1
        rid = msg.get("id")
        if isinstance(rid, str):
            relay_id_to_surfaces[rid].add(surface)
        # cross-vendor edge: from-surface -> to-surface
        from_agent = str(msg.get("from") or "")
        to_agent = str(msg.get("to") or "")
        # classify from_agent by stem
        from_surface = _classify_vendor_surface(from_agent, msg) if from_agent else surface
        to_surface = _classify_vendor_surface(to_agent, msg) if to_agent else "unknown"
        if from_surface != to_surface and from_surface != "unknown" and to_surface != "unknown":
            cross_vendor_edges[f"{from_surface}->{to_surface}"] += 1

    return {
        "total_envelopes": total,
        "by_vendor_surface": dict(by_surface.most_common()),
        "by_bucket": dict(by_bucket.most_common()),
        "by_surface_bucket": {s: dict(c.most_common()) for s, c in by_surface_bucket.items()},
        "by_from_provider": dict(by_from_provider.most_common()),
        "cross_vendor_edges": dict(cross_vendor_edges.most_common()),
        "errors": errors,
        "relay_id_to_surfaces_count": len(relay_id_to_surfaces),
        "_relay_id_to_surfaces": {k: sorted(v) for k, v in relay_id_to_surfaces.items()},
    }


def _scan_engrams(engram_dir: Path, relay_id_to_surfaces: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Scan engram op-log; attribute relay-projection + direct-vendor engrams.

    Scans history.jsonl (the append-only op-log where relay_projection_* keys
    and direct vendor source_agent stamps land). ledger.jsonl is a snapshot view
    that does not contain projection keys; history.jsonl is the source of truth
    for capture evidence.
    """
    history = engram_dir / "history.jsonl"
    total = 0
    by_source_agent: Counter = Counter()
    by_vendor_surface: Counter = Counter()
    relay_projection_count = 0
    direct_vendor_count = 0
    unattributed = 0
    errors = 0

    # Build projection-key -> relay_id index from relay_id_to_surfaces.
    projection_key_to_surfaces: Dict[str, Set[str]] = {
        f"relay_projection_{rid}": surfaces for rid, surfaces in relay_id_to_surfaces.items()
    }

    if not history.is_file():
        return {
            "total_engrams": 0,
            "relay_projection_engrams": 0,
            "direct_vendor_engrams": 0,
            "engrams_by_vendor_surface": {},
            "engrams_by_source_agent": {},
            "unattributed_projections": 0,
            "errors": 0,
            "source_file": "history.jsonl (not found)",
        }

    try:
        with open(history, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    errors += 1
                    continue
                snap = d.get("snapshot", d)
                total += 1
                sa = snap.get("source_agent")
                if isinstance(sa, str) and sa:
                    by_source_agent[sa] += 1
                key = snap.get("key")
                attributed = False
                # Path 1: relay projection key -> vendor surface via envelope.
                if isinstance(key, str) and key.startswith("relay_projection_"):
                    relay_projection_count += 1
                    surfaces = projection_key_to_surfaces.get(key)
                    if surfaces:
                        for s in surfaces:
                            by_vendor_surface[s] += 1
                        attributed = True
                    else:
                        # projection key without a matching relay envelope
                        # (relay archived/renamed, or pre-LIVE_BUCKETS expansion).
                        by_vendor_surface["unknown_projection"] += 1
                        unattributed += 1
                        attributed = True
                # Path 2: direct vendor source_agent stamp.
                if isinstance(sa, str) and sa in DIRECT_VENDOR_SOURCE_AGENTS:
                    direct_vendor_count += 1
                    by_vendor_surface[DIRECT_VENDOR_SOURCE_AGENTS[sa]] += 1
                    attributed = True
                # Note: non-vendor source_agents (auto_hook, brain_write_engram,
                # human, morning_brief, ...) are operation-type attribution and
                # are NOT counted as vendor capture (counted in by_source_agent).
    except Exception as exc:
        errors += 1

    return {
        "total_engrams": total,
        "relay_projection_engrams": relay_projection_count,
        "direct_vendor_engrams": direct_vendor_count,
        "engrams_by_vendor_surface": dict(by_vendor_surface.most_common()),
        "engrams_by_source_agent": dict(by_source_agent.most_common()),
        "unattributed_projections": unattributed,
        "errors": errors,
        "source_file": str(history),
    }


def run_census(brain_path: Path) -> Dict[str, Any]:
    """Run the full capture census. Returns the report dict."""
    relay_root = brain_path / "relay"
    engram_dir = brain_path / "engrams"

    relay_report = _scan_relays(relay_root)
    relay_id_to_surfaces = {
        k: set(v) for k, v in relay_report["_relay_id_to_surfaces"].items()
    }
    engram_report = _scan_engrams(engram_dir, relay_id_to_surfaces)

    # The load-bearing verdict: which genuine vendor surfaces have BOTH relay
    # envelopes AND engram projection capture wired?
    surfaces_with_relay = set(relay_report["by_vendor_surface"].keys())
    surfaces_with_engram_projection = {
        s for s in engram_report["engrams_by_vendor_surface"] if s != "unknown_projection"
    }
    surfaces_captured = surfaces_with_relay & surfaces_with_engram_projection
    surfaces_relay_only = surfaces_with_relay - surfaces_with_engram_projection
    surfaces_engram_only = surfaces_with_engram_projection - surfaces_with_relay

    # Known fleet surfaces per PRINCIPAL thesis (claude_code, cursor, glm, antigravity, devin, codex).
    known_fleet = {"anthropic_claude_code", "cursor", "glm", "antigravity", "devin", "codex"}
    missing_capture = sorted(known_fleet - surfaces_captured)

    # Drop the large internal index from the public report.
    public_relay = {k: v for k, v in relay_report.items() if k != "_relay_id_to_surfaces"}

    return {
        "instrument": "capture_census",
        "instrument_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "brain_path": str(brain_path),
        "principal_authority": "docs/PRINCIPAL.md:39,67-69 (G1 workstream 0)",
        "relay": public_relay,
        "engram": engram_report,
        "verdict": {
            "surfaces_with_relay_traffic": sorted(surfaces_with_relay),
            "surfaces_with_engram_projection": sorted(surfaces_with_engram_projection),
            "surfaces_fully_captured": sorted(surfaces_captured),
            "surfaces_relay_only_no_engram_projection": sorted(surfaces_relay_only),
            "surfaces_engram_only_no_relay": sorted(surfaces_engram_only),
            "known_fleet_surfaces": sorted(known_fleet),
            "missing_capture_for_known_fleet": missing_capture,
            "cross_vendor_seam_present": bool(relay_report["cross_vendor_edges"]),
        },
    }


def _format_human(report: Dict[str, Any]) -> str:
    v = report["verdict"]
    r = report["relay"]
    e = report["engram"]
    lines = []
    lines.append(f"=== Capture Census @ {report['captured_at_utc']} ===")
    lines.append(f"brain_path: {report['brain_path']}")
    lines.append("")
    lines.append("RELAY capture by vendor surface:")
    for surf, n in r["by_vendor_surface"].items():
        lines.append(f"  {n:6d}  {surf}")
    lines.append(f"  total envelopes: {r['total_envelopes']}")
    lines.append("")
    lines.append("ENGRAM capture by vendor surface (relay projection + direct vendor stamp):")
    for surf, n in e["engrams_by_vendor_surface"].items():
        lines.append(f"  {n:6d}  {surf}")
    lines.append(f"  total engrams (op-log): {e['total_engrams']}")
    lines.append(f"  relay-projection engrams: {e['relay_projection_engrams']}")
    lines.append(f"  direct-vendor-stamp engrams: {e['direct_vendor_engrams']}")
    lines.append(f"  unattributed projections: {e['unattributed_projections']}")
    lines.append("")
    lines.append("Engrams by source_agent (operation-type, NOT vendor):")
    for sa, n in list(e["engrams_by_source_agent"].items())[:10]:
        lines.append(f"  {n:6d}  {sa}")
    lines.append("")
    lines.append("Cross-vendor edges (from_surface -> to_surface):")
    for edge, n in r["cross_vendor_edges"].items():
        lines.append(f"  {n:6d}  {edge}")
    lines.append("")
    lines.append("VERDICT:")
    lines.append(f"  fully captured surfaces:     {v['surfaces_fully_captured']}")
    lines.append(f"  relay-only (no engram proj): {v['surfaces_relay_only_no_engram_projection']}")
    lines.append(f"  known fleet:                 {v['known_fleet_surfaces']}")
    lines.append(f"  MISSING capture for fleet:   {v['missing_capture_for_known_fleet']}")
    lines.append(f"  cross-vendor seam present:   {v['cross_vendor_seam_present']}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--brain-path", default=".brain", help="Path to .brain directory")
    p.add_argument("--json", action="store_true", help="Emit JSON report instead of human-readable")
    p.add_argument("--save", default=None, help="Also write the JSON report to this path")
    args = p.parse_args()

    brain = Path(args.brain_path)
    if not brain.is_dir():
        print(f"ERROR: brain path not found: {brain}", file=sys.stderr)
        return 2

    report = run_census(brain)

    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        # emit the path on stderr so callers can capture it
        print(f"report saved: {out}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(_format_human(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
