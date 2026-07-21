"""Standing cross-vendor seam-floor query (PRINCIPAL G1 criterion 3).

Authority: docs/PRINCIPAL.md:74,149 (G1 criterion 3; relay-log seam query).
Immutable source: docs/PRINCIPAL.md@principal-v3.

G1 criterion 3 (the thesis's own falsifier, adopted):
    relay envelopes spanning >=2 genuine vendor surfaces, >=25/rolling-7-days
    sustained 2 weeks (instrument: relay logs, standing query).

This is the standing query over the relay log. It is a pure measurement
instrument (exit 0 always); the JSON report is the load-bearing artifact.

Acceptance (rerunnable evidence, not narration):
  1. Counts genuine vendor surfaces with a minimum of two vendors.
  2. Computes rolling seven-day envelope volume and two-week sustainment.
  3. Caller-authored vendor labels cannot satisfy the count.

How (3) is satisfied — the anchor gate:
  A relay envelope's `from`/`from_provider`/bucket name is caller-authorable
  (a lane can type any string into `sender=`). Per PRINCIPAL.md:83 (v3 anchor
  precondition), pre-anchor envelopes with forgeable `from`/attribution are
  NON-QUALIFYING. The relay-sender anchor (NUCLEUS_RELAY_SENDER_ANCHOR=1)
  stamps `from_verified=True` ONLY on a positive kernel-resolved ancestry
  match (pid + create_time), fail-closed on every unreadable/suppressed/
  mismatched oracle. This query counts ONLY envelopes with
  `from_verified is True`. An envelope whose caller typed a vendor label but
  whose kernel ancestry does not confirm it carries `from_verified=False`
  (or the key is absent when the anchor flag is OFF) and is EXCLUDED. So a
  caller-authored vendor label cannot move the gated count — the count is
  bound to a kernel oracle outside the claimant's authority
  (PRINCIPAL.md:49, Ground-Truth Anchor invariant).

  When the anchor flag is OFF (no `from_verified` key on any envelope), the
  query reports 0 qualifying envelopes and `anchor_active=False` — this is
  the correct fail-closed state, not a bug. The seam floor cannot be
  declared met until the anchor is ON and genuine cross-vendor traffic
  flows under it.

Rerunnable from a clean checkout:
    python3 -m mcp_server_nucleus.runtime.seam_query \\
        --brain-path .brain --json > seam_query_<date>.json
    python3 -m mcp_server_nucleus.runtime.seam_query --brain-path .brain

The JSON report should be committed under `.brain/audits/seam_query/` for
tamper-evidence (same convention as capture_census).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reuse the existing vendor-surface classifier (capture_census is the G1
# workstream-0 instrument; its classification table is the canonical map).
# Wiring an existing module rather than duplicating the table.
from .capture_census import _classify_vendor_surface, _iter_relay_files

# G1 criterion 3 defaults (PRINCIPAL.md:74). Parameterized so the chief can
# re-run with a different threshold without editing code.
DEFAULT_VENDOR_FLOOR = 2          # ">=2 genuine vendor surfaces"
DEFAULT_ROLLING_WINDOW_DAYS = 7   # "rolling-7-days"
DEFAULT_SUSTAIN_WEEKS = 2         # "sustained 2 weeks"
DEFAULT_VOLUME_THRESHOLD = 25     # ">=25/rolling-7-days"


def _parse_created_at(raw: Any) -> Optional[datetime]:
    """Parse an envelope's `created_at` into an aware UTC datetime.

    The relay writer stamps ISO-8601 with a trailing ``Z`` (see
    relay/core.py: ``now.isoformat().replace("+00:00", "Z")``). Tolerate
    both ``Z`` and explicit offsets; return None on any unparseable value
    so the envelope is excluded from time-windowed counts (fail-closed).
    """
    if not isinstance(raw, str) or not raw:
        return None
    s = raw.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        # Naive timestamp: assume UTC (relay writer is UTC-stamped).
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_anchor_verified(msg: Dict[str, Any]) -> bool:
    """True ONLY when the envelope carries a positive anchor verdict.

    `from_verified` is stamped by the relay-sender anchor
    (NUCLEUS_RELAY_SENDER_ANCHOR=1) on a kernel-resolved ancestry match.
    Absent key (anchor flag OFF) or explicit False -> NOT verified.
    This is the gate that makes caller-authored vendor labels unable to
    satisfy the count (acceptance criterion 3).
    """
    return msg.get("from_verified") is True


def _scan_qualifying_envelopes(
    relay_root: Path,
    *,
    anchor_required: bool = True,
) -> Dict[str, Any]:
    """Scan relay buckets; collect anchor-verified, vendor-attributed envelopes.

    Returns per-envelope (surface, ts) for qualifying envelopes plus summary
    counters. ``anchor_required=False`` is supported for a "what would the
    count be without the anchor gate" diagnostic — NEVER used for the gated
    verdict (the gated verdict always requires the anchor).
    """
    qualifying: List[Tuple[str, datetime]] = []
    by_surface_all: Counter = Counter()
    by_surface_anchored: Counter = Counter()
    anchor_present_count = 0
    anchor_true_count = 0
    anchor_false_count = 0
    anchor_absent_count = 0
    unparseable_ts = 0
    total = 0
    errors = 0

    for bucket, f in _iter_relay_files(relay_root):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            errors += 1
            continue
        total += 1
        surface = _classify_vendor_surface(bucket, msg)
        # Exclude test fixtures and unknown surfaces from vendor counts.
        if surface in ("test_fixture", "unknown"):
            continue
        by_surface_all[surface] += 1

        anchored = _is_anchor_verified(msg)
        if "from_verified" in msg:
            anchor_present_count += 1
            if anchored:
                anchor_true_count += 1
                by_surface_anchored[surface] += 1
            else:
                anchor_false_count += 1
        else:
            anchor_absent_count += 1

        if anchor_required and not anchored:
            continue
        ts = _parse_created_at(msg.get("created_at"))
        if ts is None:
            unparseable_ts += 1
            continue
        qualifying.append((surface, ts))

    return {
        "total_envelopes_scanned": total,
        "qualifying_envelope_count": len(qualifying),
        "by_surface_all": dict(by_surface_all.most_common()),
        "by_surface_anchored": dict(by_surface_anchored.most_common()),
        "anchor_present_count": anchor_present_count,
        "anchor_true_count": anchor_true_count,
        "anchor_false_count": anchor_false_count,
        "anchor_absent_count": anchor_absent_count,
        "unparseable_timestamps": unparseable_ts,
        "errors": errors,
        "_qualifying": qualifying,
    }


def _rolling_window_volume(
    qualifying: List[Tuple[str, datetime]],
    *,
    window_days: int,
    as_of: datetime,
) -> int:
    """Count qualifying envelopes within ``[as_of - window_days, as_of]``."""
    cutoff = as_of - timedelta(days=window_days)
    return sum(1 for _surf, ts in qualifying if cutoff <= ts <= as_of)


def _sustainment_weeks(
    qualifying: List[Tuple[str, datetime]],
    *,
    window_days: int,
    threshold: int,
    sustain_weeks: int,
    as_of: datetime,
) -> Dict[str, Any]:
    """Check the rolling-window volume has met ``threshold`` for ``sustain_weeks``
    consecutive weeks, ending at ``as_of``.

    Each week ``k`` (k=0..sustain_weeks-1) covers the trailing ``window_days``
    window ending at ``as_of - 7*k days``. Sustained = every weekly window
    met the threshold. Returns per-week volumes + the sustained verdict.
    """
    weeks: List[Dict[str, Any]] = []
    sustained = True
    for k in range(sustain_weeks):
        week_as_of = as_of - timedelta(days=7 * k)
        vol = _rolling_window_volume(
            qualifying, window_days=window_days, as_of=week_as_of
        )
        met = vol >= threshold
        weeks.append({
            "week_index": k,
            "window_end_utc": week_as_of.isoformat(),
            "window_days": window_days,
            "volume": vol,
            "threshold": threshold,
            "met_threshold": met,
        })
        if not met:
            sustained = False
    return {"sustained": sustained, "weeks": weeks}


def run_seam_query(
    brain_path: Path,
    *,
    vendor_floor: int = DEFAULT_VENDOR_FLOOR,
    rolling_window_days: int = DEFAULT_ROLLING_WINDOW_DAYS,
    volume_threshold: int = DEFAULT_VOLUME_THRESHOLD,
    sustain_weeks: int = DEFAULT_SUSTAIN_WEEKS,
    as_of: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Run the standing cross-vendor seam-floor query. Returns the report dict.

    The gated verdict requires ALL of:
      (a) anchor_active (>=1 envelope carries from_verified=True — proves the
          anchor is ON, so the count is not over forgeable inputs);
      (b) >=vendor_floor distinct genuine vendor surfaces among anchored
          qualifying envelopes;
      (c) rolling-7-day volume >= volume_threshold;
      (d) sustained for sustain_weeks consecutive weeks.
    """
    relay_root = brain_path / "relay"
    scan = _scan_qualifying_envelopes(relay_root, anchor_required=True)
    qualifying = scan["_qualifying"]
    now = as_of or datetime.now(timezone.utc)

    anchored_surfaces = sorted({s for s, _ts in qualifying})
    distinct_vendor_count = len(anchored_surfaces)
    anchor_active = scan["anchor_true_count"] > 0

    rolling_volume = _rolling_window_volume(
        qualifying, window_days=rolling_window_days, as_of=now
    )
    sustainment = _sustainment_weeks(
        qualifying,
        window_days=rolling_window_days,
        threshold=volume_threshold,
        sustain_weeks=sustain_weeks,
        as_of=now,
    )

    min_two_vendors_met = distinct_vendor_count >= vendor_floor
    rolling_volume_met = rolling_volume >= volume_threshold
    sustained_met = sustainment["sustained"]

    seam_floor_met = bool(
        anchor_active
        and min_two_vendors_met
        and rolling_volume_met
        and sustained_met
    )

    # Diagnostic: what would the counts be WITHOUT the anchor gate? This
    # surfaces the forgeable-input exposure (how many envelopes a caller
    # could have moved by typing a vendor label). NEVER used for the verdict.
    diag_scan = _scan_qualifying_envelopes(relay_root, anchor_required=False)
    diag_qualifying = diag_scan["_qualifying"]
    diag_surfaces = sorted({s for s, _ts in diag_qualifying})
    diag_rolling = _rolling_window_volume(
        diag_qualifying, window_days=rolling_window_days, as_of=now
    )

    return {
        "instrument": "seam_query",
        "instrument_version": 1,
        "principal_authority": "docs/PRINCIPAL.md:74,149 (G1 criterion 3; relay-log seam query)",
        "principal_source_tag": "principal-v3",
        "queried_at_utc": now.isoformat(),
        "brain_path": str(brain_path),
        "parameters": {
            "vendor_floor": vendor_floor,
            "rolling_window_days": rolling_window_days,
            "volume_threshold": volume_threshold,
            "sustain_weeks": sustain_weeks,
        },
        "anchor": {
            "anchor_active": anchor_active,
            "anchor_present_count": scan["anchor_present_count"],
            "anchor_true_count": scan["anchor_true_count"],
            "anchor_false_count": scan["anchor_false_count"],
            "anchor_absent_count": scan["anchor_absent_count"],
            "note": (
                "anchor_active=False means NUCLEUS_RELAY_SENDER_ANCHOR is OFF "
                "or no envelope carries from_verified=True; per PRINCIPAL.md:83 "
                "pre-anchor envelopes are non-qualifying -> seam floor NOT met."
            ),
        },
        "vendor_surfaces": {
            "distinct_anchored_vendor_count": distinct_vendor_count,
            "anchored_vendor_surfaces": anchored_surfaces,
            "min_two_vendors_met": min_two_vendors_met,
            "by_surface_anchored": scan["by_surface_anchored"],
            "by_surface_all_including_unanchored": scan["by_surface_all"],
        },
        "rolling_window": {
            "window_days": rolling_window_days,
            "window_end_utc": now.isoformat(),
            "qualifying_volume": rolling_volume,
            "threshold": volume_threshold,
            "met_threshold": rolling_volume_met,
        },
        "sustainment": sustainment,
        "diagnostic_unanchored_exposure": {
            "purpose": (
                "Counts WITHOUT the anchor gate — shows the forgeable-input "
                "exposure. A caller could have moved these by typing a vendor "
                "label. NEVER used for the gated verdict."
            ),
            "distinct_vendor_count_unanchored": len(diag_surfaces),
            "vendor_surfaces_unanchored": diag_surfaces,
            "rolling_volume_unanchored": diag_rolling,
        },
        "scan_stats": {
            "total_envelopes_scanned": scan["total_envelopes_scanned"],
            "qualifying_envelope_count": scan["qualifying_envelope_count"],
            "unparseable_timestamps": scan["unparseable_timestamps"],
            "errors": scan["errors"],
        },
        "verdict": {
            "seam_floor_met": seam_floor_met,
            "criteria": {
                "anchor_active": anchor_active,
                "min_two_vendors": min_two_vendors_met,
                "rolling_volume_threshold": rolling_volume_met,
                "sustained_two_weeks": sustained_met,
            },
            "fail_closed_reason": (
                "anchor not active" if not anchor_active
                else "fewer than 2 vendor surfaces" if not min_two_vendors_met
                else "rolling volume below threshold" if not rolling_volume_met
                else "not sustained 2 weeks" if not sustained_met
                else "all criteria met"
            ),
        },
    }


def _format_human(report: Dict[str, Any]) -> str:
    v = report["verdict"]
    a = report["anchor"]
    vs = report["vendor_surfaces"]
    rw = report["rolling_window"]
    su = report["sustainment"]
    p = report["parameters"]
    lines: List[str] = []
    lines.append(f"=== Seam-Floor Query @ {report['queried_at_utc']} ===")
    lines.append(f"authority: {report['principal_authority']}")
    lines.append(f"brain_path: {report['brain_path']}")
    lines.append(f"parameters: vendors>={p['vendor_floor']} "
                 f"window={p['rolling_window_days']}d "
                 f"threshold={p['volume_threshold']} "
                 f"sustain={p['sustain_weeks']}wk")
    lines.append("")
    lines.append("ANCHOR gate (caller-authored labels cannot satisfy count):")
    lines.append(f"  anchor_active:        {a['anchor_active']}")
    lines.append(f"  from_verified=True:   {a['anchor_true_count']}")
    lines.append(f"  from_verified=False:  {a['anchor_false_count']}")
    lines.append(f"  from_verified absent: {a['anchor_absent_count']}")
    lines.append("")
    lines.append("VENDOR SURFACES (anchored, qualifying):")
    lines.append(f"  distinct count: {vs['distinct_anchored_vendor_count']} "
                 f"(floor {p['vendor_floor']}) -> {vs['min_two_vendors_met']}")
    lines.append(f"  surfaces: {vs['anchored_vendor_surfaces']}")
    for surf, n in vs["by_surface_anchored"].items():
        lines.append(f"    {n:6d}  {surf}")
    lines.append("")
    lines.append("ROLLING WINDOW (anchored, qualifying):")
    lines.append(f"  {rw['qualifying_volume']} envelopes in last "
                 f"{rw['window_days']}d (threshold {rw['threshold']}) -> "
                 f"{rw['met_threshold']}")
    lines.append("")
    lines.append("SUSTAINMENT (2 consecutive weekly windows):")
    for w in su["weeks"]:
        lines.append(f"  week {w['week_index']}: {w['volume']} "
                     f"(end {w['window_end_utc']}) -> {w['met_threshold']}")
    lines.append(f"  sustained: {su['sustained']}")
    lines.append("")
    lines.append("VERDICT:")
    lines.append(f"  seam_floor_met: {v['seam_floor_met']}")
    lines.append(f"  criteria: {v['criteria']}")
    lines.append(f"  reason:    {v['fail_closed_reason']}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--brain-path", default=".brain", help="Path to .brain directory")
    p.add_argument("--json", action="store_true", help="Emit JSON report instead of human-readable")
    p.add_argument("--save", default=None, help="Also write the JSON report to this path")
    p.add_argument("--vendor-floor", type=int, default=DEFAULT_VENDOR_FLOOR)
    p.add_argument("--rolling-window-days", type=int, default=DEFAULT_ROLLING_WINDOW_DAYS)
    p.add_argument("--volume-threshold", type=int, default=DEFAULT_VOLUME_THRESHOLD)
    p.add_argument("--sustain-weeks", type=int, default=DEFAULT_SUSTAIN_WEEKS)
    args = p.parse_args()

    brain = Path(args.brain_path)
    if not brain.is_dir():
        print(f"ERROR: brain path not found: {brain}", file=sys.stderr)
        return 2

    report = run_seam_query(
        brain,
        vendor_floor=args.vendor_floor,
        rolling_window_days=args.rolling_window_days,
        volume_threshold=args.volume_threshold,
        sustain_weeks=args.sustain_weeks,
    )

    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"report saved: {out}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(_format_human(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
