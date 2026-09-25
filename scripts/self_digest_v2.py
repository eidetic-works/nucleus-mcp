#!/usr/bin/env python3
"""Weekly self-digest — the substrate reports on itself (PRINCIPAL Standing
Workflow Library: "self-digest + census: substrate reports on itself").

Emits four signals, each DEGRADING GRACEFULLY to "n/a" — this script must never
crash (it runs unattended on a weekly schedule):

  * recall_hit_rate_proxy   — engram-store reachability / size (memory recall).
  * paste_count_proxy       — relay envelopes in the trailing window (automation
                              that displaces manual founder pastes).
  * cold_start_proxy        — wall time to import the census + build a snapshot.
  * anti_circularity_delta  — current census outside_share vs the frozen baseline
                              (the crit-4 substrate-attributed production delta).

It reuses census_v2 for the anti-circularity signal — the census is the single
source of truth; the digest only frames it. It does NOT overload the unrelated
Prometheus telemetry digest (infra/telemetry/digest.log).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

NA = "n/a"


def _safe(fn, default=NA):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — the digest never crashes
        return f"{default} ({type(exc).__name__})"


def _iter_brains(roots: List[Path]) -> List[Path]:
    out: List[Path] = []
    seen = set()
    for root in roots:
        root = root.resolve()
        for cand in [root] + ([c for c in root.iterdir() if c.is_dir()] if root.is_dir() else []):
            b = cand / ".brain"
            if b.is_dir() and b.resolve() not in seen and ".claude/worktrees" not in str(b):
                seen.add(b.resolve())
                out.append(b)
    return out


def recall_hit_rate_proxy() -> Any:
    """Engram-store reachability + size as a recall proxy."""
    try:
        from nucleus_wedge.store import Store  # type: ignore
        store = Store()
        n = None
        for attr in ("count", "size", "__len__"):
            if hasattr(store, attr):
                try:
                    n = getattr(store, attr)() if callable(getattr(store, attr)) else getattr(store, attr)
                    break
                except Exception:
                    continue
        return {"store": "reachable", "engrams": n if n is not None else "unknown"}
    except Exception:
        return {"store": NA}


def paste_count_proxy(roots: List[Path], window_days: int = 7) -> Any:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    total = 0
    recent = 0
    for brain in _iter_brains(roots):
        relay = brain / "relay"
        if not relay.is_dir():
            continue
        for f in relay.glob("*/*.json"):
            total += 1
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                ts = d.get("created_at", "")
                if ts and datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff:
                    recent += 1
            except Exception:
                continue
    return {"relay_envelopes_total": total, f"relay_envelopes_last_{window_days}d": recent,
            "note": "higher automation displaces manual pastes"}


def cold_start_proxy(roots: List[Path]) -> Any:
    t0 = time.perf_counter()
    import census_v2 as C  # noqa: F401
    import_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    try:
        tax = C.load_taxonomy(C._default_taxonomy_path())
        snap = C.capture_snapshot(roots, tax, capturer="digest",
                                  capture_commit="digest", resolve_build=False)
        n_units = len(snap["units"])
    except Exception:
        n_units = NA
    capture_s = time.perf_counter() - t1
    return {"import_s": round(import_s, 4), "capture_s": round(capture_s, 4), "spine_units": n_units}


def anti_circularity_delta(roots: List[Path], baseline_path: Optional[Path]) -> Any:
    import census_v2 as C
    tax = C.load_taxonomy(C._default_taxonomy_path())
    snap = C.capture_snapshot(roots, tax, capturer="digest",
                              capture_commit="digest", resolve_build=False)
    if baseline_path and baseline_path.exists():
        frozen = json.loads(baseline_path.read_text(encoding="utf-8"))
        params = C.Params.from_dict(frozen["derived_params"])
        frozen_share = frozen.get("baseline_outside_share") or 0.0
        freezable = frozen.get("freezable", False)
    else:
        measured = C.measure_baseline(snap)
        params = C.derive_params(measured)
        frozen_share = 0.0
        freezable = C.validate_stringency(params)[0]
    res = C.evaluate(snap, params, frozen_share)
    share = res["outside_share"]
    delta = None if share is None else round(share - frozen_share, 6)
    return {
        "outside_share": share if share is not None else NA,
        "frozen_baseline": frozen_share,
        "delta_vs_baseline": delta if delta is not None else NA,
        "denominator": res["denominator"],
        "numerator": res["numerator"],
        "inconclusive": res["inconclusive"],
        "baseline_freezable": freezable,
        "pass": res["pass"],
    }


def build_digest(roots: List[Path], baseline_path: Optional[Path]) -> Dict[str, Any]:
    return {
        "schema": "self-digest-v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "roots": [str(r) for r in roots],
        "recall_hit_rate_proxy": _safe(recall_hit_rate_proxy),
        "paste_count_proxy": _safe(lambda: paste_count_proxy(roots)),
        "cold_start_proxy": _safe(lambda: cold_start_proxy(roots)),
        "anti_circularity_delta": _safe(lambda: anti_circularity_delta(roots, baseline_path)),
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Weekly substrate self-digest")
    p.add_argument("--roots", nargs="+", default=None)
    p.add_argument("--baseline", default=None, help="frozen baseline JSON (optional)")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    roots = [Path(r) for r in (args.roots or [os.getcwd()])]
    baseline_path = Path(args.baseline) if args.baseline else None
    try:
        digest = build_digest(roots, baseline_path)
    except Exception as exc:  # noqa: BLE001 — never crash the scheduler
        digest = {"schema": "self-digest-v2", "error": f"{type(exc).__name__}: {exc}",
                  "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    text = json.dumps(digest, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
