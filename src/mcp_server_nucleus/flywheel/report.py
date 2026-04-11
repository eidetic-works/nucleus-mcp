"""Weekly flywheel report generator.

Reads the current week's pending_issues.jsonl + CSR state and produces a
markdown summary. Safe to run repeatedly — it overwrites the week file's
header/summary block but preserves the append-only ticket log below it.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .csr import read_csr, _ensure_flywheel_dir


def _week_index(when: Optional[datetime] = None) -> int:
    when = when or datetime.now(timezone.utc)
    return when.isocalendar()[1]


def _read_tickets(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return out
    return out


def generate_week_report(brain_path: Path, week: Optional[int] = None) -> Path:
    """Write week-N.md and return its path."""
    bp = Path(brain_path)
    fw_dir = _ensure_flywheel_dir(bp)
    w = week or _week_index()
    out_path = fw_dir / f"week-{w}.md"

    csr = read_csr(bp)
    tickets = _read_tickets(fw_dir / "pending_issues.jsonl")

    # Scope tickets to the current week (loose match on ticket_id timestamp)
    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    while week_start.isocalendar()[1] == w and week_start.weekday() > 0:
        week_start = week_start.replace(day=week_start.day - 1)

    by_step: Dict[str, int] = {}
    for t in tickets:
        step = t.get("step", "unknown")
        by_step[step] = by_step.get(step, 0) + 1

    lines: List[str] = [
        f"# Flywheel — Week {w}",
        "",
        f"_Generated {now.isoformat()[:19]}Z_",
        "",
        "## CSR",
        "",
        f"- **Claims total:** {csr.get('claims_total', 0)}",
        f"- **Survived:** {csr.get('claims_survived', 0)}",
        f"- **Unsurvived:** {csr.get('claims_unsurvived', 0)}",
        f"- **Ratio:** {round(csr.get('ratio', 0) * 100, 2)}%",
        "",
        "## Tickets",
        "",
        f"- **Open total:** {len(tickets)}",
        "",
    ]

    if by_step:
        lines += ["### By step", ""]
        for step, count in sorted(by_step.items(), key=lambda x: -x[1]):
            lines.append(f"- `{step}`: {count}")
        lines.append("")

    if tickets:
        lines += [
            "### Recent tickets",
            "",
            "| Time | Step | Phase | Error |",
            "|------|------|-------|-------|",
        ]
        for t in tickets[-20:]:
            ts = t.get("at", "")[:19]
            step = t.get("step", "?")[:40]
            phase = t.get("phase", "")[:20]
            err = (t.get("error", "") or "")[:80].replace("|", "-")
            lines.append(f"| {ts} | {step} | {phase} | {err} |")
        lines.append("")

    lines += [
        "## Recent Claims",
        "",
    ]
    recent = csr.get("recent_claims", [])[-10:]
    if recent:
        for r in recent:
            status = "✓" if r.get("survived") else "✗"
            lines.append(
                f"- {status} `{r.get('step', '?')}` at {r.get('at', '')[:19]}"
            )
    else:
        lines.append("_No claims recorded yet._")
    lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path
