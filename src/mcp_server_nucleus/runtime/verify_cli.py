"""
DSoR Verifier CLI — demo/ad-hoc runner for verifier.py
=======================================================
Runnable as:

    python -m mcp_server_nucleus.runtime.verify_cli \\
        --relay .brain/relay/claude_code_main --repo . --limit 5

    python -m mcp_server_nucleus.runtime.verify_cli \\
        --claims curated_claims.json

    python -m mcp_server_nucleus.runtime.verify_cli \\
        --relay .brain/relay/claude_code_main \\
        --claims curated_claims.json \\
        --anchors overrides.json \\
        --repo . --limit 20

This is a read-only, non-destructive demo: it never records anything to a
DecisionLedger (Verifier is always constructed with record=False) and never
touches ~/.nucleus or any project's .brain — it only READS relay/claims/
anchor files the caller points it at and prints a report to stdout.

--relay <dir>     Ingest relay *.json messages from this directory as
                   Claims (see verifier.ingest_relay).
--claims <file>   Ingest a curated JSON array of claim dicts (see
                   verifier.ingest_claims_file). Each claim may embed an
                   "anchors" list — hand-authored anchors for that exact
                   claim — which take priority over regex decomposition.
--anchors <file>  A JSON object {claim_id: [anchor dict, ...]}. Anchors
                   here OVERRIDE any anchors embedded inline in --claims
                   for the same claim_id (an explicit override always wins
                   over an inline default).
--repo <path>     Default git repo used for git-kind anchors that don't
                   specify their own "repo" in spec.
--limit <N>       Cap the number of claims verified (applied after all
                   ingestion, before verification, in ingestion order).

If any anchor_map ends up non-empty (from --claims and/or --anchors), an
InjectedReasoner is used (falls back to RuleReasoner decomposition for any
claim without a pre-computed anchor list). Otherwise a plain RuleReasoner
is used for every claim.
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List

from .verifier import (
    Anchor,
    Claim,
    InjectedReasoner,
    ProbeEngine,
    RuleReasoner,
    Verifier,
    anchor_from_dict,
    ingest_claims_file,
    ingest_relay,
    render_report,
)


def _load_anchor_map_file(path: str) -> Dict[str, List[Anchor]]:
    """Load --anchors: {claim_id: [anchor dict, ...]}."""
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object of {{claim_id: [anchors]}}")

    anchor_map: Dict[str, List[Anchor]] = {}
    for claim_id, anchors in data.items():
        if not isinstance(anchors, list):
            continue
        anchor_map[claim_id] = [
            anchor_from_dict(a, idx=i, prefix=f"{claim_id}-anchor")
            for i, a in enumerate(anchors) if isinstance(a, dict)
        ]
    return anchor_map


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_cli",
        description="DSoR Verifier — ground-truth auditor demo CLI (read-only).",
    )
    parser.add_argument("--relay", type=str, default=None, help="Directory of relay *.json files to ingest as claims")
    parser.add_argument(
        "--claims", type=str, default=None,
        help="JSON file: array of claim dicts, each optionally embedding an 'anchors' list",
    )
    parser.add_argument(
        "--anchors", type=str, default=None,
        help="JSON file: {claim_id: [anchor dicts]} — overrides anchors embedded in --claims for matching claim_ids",
    )
    parser.add_argument("--repo", type=str, default=None, help="Default git repo path for git anchors")
    parser.add_argument("--limit", type=int, default=None, help="Max number of claims to verify")
    return parser


def main(argv: List[str] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.relay and not args.claims:
        parser.error("at least one of --relay or --claims is required")

    claims: List[Claim] = []
    inline_anchor_map: Dict[str, List[Anchor]] = {}

    if args.relay:
        claims.extend(ingest_relay(args.relay))

    if args.claims:
        file_claims, file_anchor_map = ingest_claims_file(args.claims)
        claims.extend(file_claims)
        inline_anchor_map.update(file_anchor_map)

    if args.limit is not None:
        claims = claims[: args.limit]

    anchor_map = dict(inline_anchor_map)
    if args.anchors:
        anchor_map.update(_load_anchor_map_file(args.anchors))

    reasoner = InjectedReasoner(anchor_map) if anchor_map else RuleReasoner()
    probe_engine = ProbeEngine(default_repo=args.repo)
    # record is always False here — this CLI never writes to a
    # DecisionLedger, real or scratch. It is a read-only report generator.
    verifier = Verifier(reasoner=reasoner, probe_engine=probe_engine, ledger=None, record=False)

    if not claims:
        print(f"No claims ingested (relay={args.relay!r}, claims={args.claims!r}).")
        return 0

    verdicts = verifier.verify_all(claims)
    print(render_report(verdicts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
