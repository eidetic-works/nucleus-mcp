"""Flywheel dashboard — JSON and HTML renderers.

Reads CSR state + recent ticket files and projects them into a dashboard
suitable for MCP resource queries (JSON) and public consumption (HTML).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .csr import read_csr, _ensure_flywheel_dir


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with open(path) as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def render_dashboard_json(brain_path: Path) -> Dict[str, Any]:
    """Project flywheel state as a JSON-serializable dict."""
    bp = Path(brain_path)
    fw_dir = _ensure_flywheel_dir(bp)
    csr = read_csr(bp)

    tickets_open = _count_lines(fw_dir / "pending_issues.jsonl")
    tasks_open = _count_lines(fw_dir / "pending_tasks.jsonl")
    training_dir = bp / "training" / "exports"
    pairs_count = _count_lines(training_dir / "unified_dpo_pending.jsonl")

    return {
        "version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "csr": {
            "claims_total": csr.get("claims_total", 0),
            "claims_survived": csr.get("claims_survived", 0),
            "claims_unsurvived": csr.get("claims_unsurvived", 0),
            "ratio": csr.get("ratio", 0.0),
            "first_claim_at": csr.get("first_claim_at"),
            "last_updated": csr.get("last_updated"),
        },
        "tickets": {
            "open": tickets_open,
            "file": str(fw_dir / "pending_issues.jsonl"),
        },
        "tasks": {
            "open": tasks_open,
            "file": str(fw_dir / "pending_tasks.jsonl"),
        },
        "curriculum": {
            "pending_pairs": pairs_count,
            "file": str(training_dir / "unified_dpo_pending.jsonl"),
        },
        "recent_claims": csr.get("recent_claims", [])[-10:],
    }


def render_dashboard_html(brain_path: Path) -> str:
    """Render flywheel state as a single self-contained HTML page.

    No external CSS, no JS framework. One file that opens in any browser.
    """
    state = render_dashboard_json(brain_path)
    csr = state["csr"]
    ratio_pct = round(csr.get("ratio", 0) * 100, 2)
    recent = state.get("recent_claims", [])
    recent_rows = "\n".join(
        f"<tr><td>{r.get('at', '')[:19]}</td>"
        f"<td>{r.get('step', '')}</td>"
        f"<td class='{'ok' if r.get('survived') else 'fail'}'>"
        f"{'survived' if r.get('survived') else 'unsurvived'}</td></tr>"
        for r in recent
    ) or "<tr><td colspan='3'><em>No claims yet</em></td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Nucleus Flywheel</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 800px;
         margin: 40px auto; padding: 0 20px; color: #222; line-height: 1.5; }}
  h1 {{ font-size: 2.5em; margin-bottom: 0.2em; }}
  .subtitle {{ color: #666; margin-top: 0; }}
  .metric {{ background: #f5f5f7; padding: 20px; border-radius: 12px;
             margin: 20px 0; }}
  .metric h2 {{ margin: 0; font-size: 1em; color: #666; text-transform: uppercase;
                letter-spacing: 0.05em; }}
  .metric .value {{ font-size: 3em; font-weight: 700; margin: 0.2em 0; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f5f5f7; font-weight: 600; }}
  .ok {{ color: #1d7a2e; font-weight: 600; }}
  .fail {{ color: #a81818; font-weight: 600; }}
  footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;
            color: #888; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Nucleus Flywheel</h1>
<p class="subtitle">Claim Survival Rate — every claim the system makes, measured.</p>

<div class="metric">
  <h2>CSR (Claim Survival Rate)</h2>
  <div class="value">{ratio_pct}%</div>
  <p>{csr.get("claims_survived", 0)} survived of {csr.get("claims_total", 0)} total claims</p>
</div>

<div class="grid">
  <div class="metric">
    <h2>Open Tickets</h2>
    <div class="value">{state["tickets"]["open"]}</div>
  </div>
  <div class="metric">
    <h2>Open Tasks</h2>
    <div class="value">{state["tasks"]["open"]}</div>
  </div>
  <div class="metric">
    <h2>Curriculum Pairs</h2>
    <div class="value">{state["curriculum"]["pending_pairs"]}</div>
  </div>
</div>

<h2>Recent Claims</h2>
<table>
  <thead>
    <tr><th>Time</th><th>Step</th><th>Status</th></tr>
  </thead>
  <tbody>
    {recent_rows}
  </tbody>
</table>

<footer>
  Generated {state["generated_at"][:19]}Z by nucleus-flywheel v{state["version"]}.
  Source: <code>.brain/flywheel/</code>
</footer>
</body>
</html>
"""
