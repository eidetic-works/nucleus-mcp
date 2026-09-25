#!/usr/bin/env python3
"""Nucleus surface census — which surfaces are actually used, from evidence.

Answers one question: over the last N days, which Nucleus surfaces did agents
really call, and how often. Counting is done here, deterministically, so that
the model running this on a schedule spends its tokens on interpretation
rather than on tallying thousands of files.

Two evidence sources, deliberately different in kind:

* **MCP tool calls** — ``tool_use`` blocks in Claude Code session transcripts
  under ``~/.claude/projects``. This is the only record of what an agent chose
  to invoke.
* **CLI runs** — ``nucleus build`` leaves one plan directory per run under
  ``.brain/plans/plan_<YYYYMMDD>_*``. The CLI never appears in the MCP
  transcript, so a census that only reads transcripts would score the busiest
  surface in the system at zero.

A COUNT IS NOT DEMAND. Some surfaces are called because a hook blocks progress
until they are (``nucleus_first_pretool.sh`` gates Read/Grep/Glob on
``nucleus_wedge__recall``). Those calls are enforced, not chosen. The report
marks them so the distinction survives into whatever reads it — an enforced
surface can look load-bearing while nothing actually depends on its output.

Usage::

    python3 surface_census.py                 # markdown table to stdout
    python3 surface_census.py --json          # machine-readable
    python3 surface_census.py --days 30
    python3 surface_census.py --out FILE      # write markdown, also print

Exit codes: 0 report produced, 2 no evidence found at all (which is a
finding, not a success — see ``_no_evidence``).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

# Matches the tool name inside a tool_use block. Session transcripts are JSONL
# with unpredictable key order, so this is a targeted scan rather than a full
# parse — parsing 1000+ multi-MB files to read one field is not worth it.
_TOOL_RE = re.compile(r'"name"\s*:\s*"((?:mcp__)?[a-z0-9_]*nucleus[a-z0-9_]*(?:__[a-z0-9_]+)?)"')

# Surfaces whose call count is produced by a hook that blocks the agent until
# it calls them. Their volume measures enforcement, not demand.
_ENFORCED = {
    "mcp__nucleus_wedge__recall": "nucleus_first_pretool.sh gates Read/Grep/Glob",
    "mcp__nucleus_wedge__remember": "stop_gates.sh end-of-turn gate",
}

_TIER_CORE = 100      # calls/period at or above which a surface is core
_TIER_ACTIVE = 13     # below this is long tail


def _iter_session_files(root: Path, days: int) -> List[Path]:
    cutoff = time.time() - days * 86400
    out: List[Path] = []
    if not root.is_dir():
        return out
    for p in root.rglob("*.jsonl"):
        try:
            if p.stat().st_mtime >= cutoff:
                out.append(p)
        except OSError:
            continue
    return out


def count_tool_calls(projects_root: Path, days: int) -> Tuple[Counter, int]:
    """Count nucleus tool invocations across recent session transcripts."""
    counts: Counter = Counter()
    files = _iter_session_files(projects_root, days)
    for p in files:
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        counts.update(_TOOL_RE.findall(text))
    return counts, len(files)


def count_build_runs(brain: Path, days: int) -> Tuple[int, Dict[str, int]]:
    """Count `nucleus build` runs by plan directory, and per-day breakdown.

    Uses the directory NAME (``plan_YYYYMMDD_...``) rather than mtime: a plan
    directory is written once and then read many times, so mtime drifts and
    would silently inflate recent days.
    """
    plans = brain / "plans"
    if not plans.is_dir():
        return 0, {}
    cutoff = time.strftime("%Y%m%d", time.localtime(time.time() - days * 86400))
    per_day: Counter = Counter()
    for d in plans.glob("plan_*"):
        if not d.is_dir():
            continue
        m = re.match(r"plan_(\d{8})_", d.name)
        if not m:
            continue
        day = m.group(1)
        if day >= cutoff:
            per_day[day] += 1
    return sum(per_day.values()), dict(sorted(per_day.items()))


def _tier(n: int) -> str:
    if n >= _TIER_CORE:
        return "core"
    if n >= _TIER_ACTIVE:
        return "active"
    return "long-tail"


def _no_evidence(tool_counts: Counter, build_runs: int) -> bool:
    """True when the census found nothing anywhere.

    Reported as a FAILURE rather than an empty table. Every previous instance
    of this shape in this codebase was an instrument pointed at the wrong path
    reading zero and being believed. Zero calls across every surface means the
    census is broken far more often than it means the system went idle.
    """
    return not tool_counts and build_runs == 0


def build_report(days: int, brain: Path, projects_root: Path) -> dict:
    tool_counts, n_files = count_tool_calls(projects_root, days)
    build_runs, per_day = count_build_runs(brain, days)

    rows = []
    if build_runs:
        vals = list(per_day.values())
        rows.append({
            "surface": "nucleus build (CLI)",
            "calls": build_runs,
            "detail": f"{min(vals)}-{max(vals)}/day over {len(per_day)} active days",
            "tier": _tier(build_runs),
            "enforced": None,
            "source": "plan dirs",
        })
    for name, n in tool_counts.most_common():
        rows.append({
            "surface": name,
            "calls": n,
            "detail": "",
            "tier": _tier(n),
            "enforced": _ENFORCED.get(name),
            "source": "session transcripts",
        })

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "window_days": days,
        "session_files_scanned": n_files,
        "build_runs": build_runs,
        "build_runs_per_day": per_day,
        "total_tool_calls": sum(tool_counts.values()),
        "distinct_surfaces": len(tool_counts) + (1 if build_runs else 0),
        "rows": rows,
        "no_evidence": _no_evidence(tool_counts, build_runs),
    }


def render_markdown(rep: dict, top: int = 12) -> str:
    lines = [
        f"# Nucleus surface census — {rep['generated_at'][:10]}",
        "",
        f"Window: last **{rep['window_days']} days** · "
        f"{rep['session_files_scanned']} session files scanned · "
        f"{rep['total_tool_calls']} tool calls · "
        f"{rep['build_runs']} build runs",
        "",
        "| Surface | Calls | Tier | Note |",
        "|---|---:|---|---|",
    ]
    shown = rep["rows"][:top]
    for r in shown:
        note = r["detail"]
        if r["enforced"]:
            note = (note + " · " if note else "") + f"**enforced** — {r['enforced']}"
        lines.append(f"| `{r['surface']}` | {r['calls']} | {r['tier']} | {note} |")

    rest = rep["rows"][top:]
    if rest:
        tail = ", ".join(f"{r['surface'].split('__')[-1]} {r['calls']}" for r in rest[:10])
        lines.append(f"| _{len(rest)} more_ | ≤{rest[0]['calls']} | long-tail | {tail} |")

    if rep["no_evidence"]:
        lines += ["", "> **NO EVIDENCE FOUND.** Treat this as a broken census, not an idle "
                  "system. Check that the brain path and projects root are correct."]
    else:
        enforced = [r for r in shown if r["enforced"]]
        if enforced:
            lines += ["", "> Surfaces marked **enforced** are called because a hook blocks the "
                      "agent until they are. Their volume measures enforcement, not demand — "
                      "do not read them as evidence that anything depends on their output."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--brain", type=Path,
                    default=Path(os.environ.get("NUCLEUS_BRAIN_PATH",
                                                Path.home() / "ai-mvp-backend" / ".brain")))
    ap.add_argument("--projects", type=Path, default=Path.home() / ".claude" / "projects")
    args = ap.parse_args(argv)

    rep = build_report(args.days, args.brain, args.projects)
    out = json.dumps(rep, indent=2) if args.json else render_markdown(rep)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_markdown(rep))
    print(out)
    return 2 if rep["no_evidence"] else 0


if __name__ == "__main__":
    sys.exit(main())
