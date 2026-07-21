"""GET /fleet — fleet dashboard web UI (HTMX, no build step).

Authority: SPEC.md task ``g4_fleet_dashboard``. A single Starlette route that
returns a self-contained HTML page rendering the live fleet state:

  1. **Fleet status** — agents connected (read from ``.brain/fleet.json``
     if present, else discovered from relay bucket subdirectories).
  2. **Relay traffic** — recent messages across all relay buckets
     (``.brain/relay/<bucket>/*.json``), newest first, capped at 20.
  3. **Task progress** — PENDING / IN_PROGRESS / DONE / ESCALATED counts
     from the tasks store (SQLite ``.brain/nucleus.db`` if available,
     falling back to JSON ``.brain/ledger/tasks.json``).
  4. **Verification results** — confirmed / failed counts from the tasks
     store's ``verification_status`` column (SQLite) or JSON fallback.

The page auto-refreshes every 10s via an ``<meta http-equiv="refresh">`` tag
and an HTMX ``hx-trigger="every 10s"`` on the main panel — either mechanism
satisfies the "auto-refreshes every 10s via HTMX" acceptance. HTMX is loaded
from the public CDN (``unpkg.com/htmx.org``); no build step, no npm.

Wire-up mirrors ``relay_route`` / ``telemetry_route``: a ``Route`` object
exported as ``fleet_dashboard_route`` for the HTTP transport ``app.py`` to
insert into the fastmcp router. The route is registered in ``app.py`` in a
follow-up edit so the dashboard is reachable at ``GET /fleet`` on the
running cloud app.

The dashboard is **read-only** and **unauthenticated by default** — it
surfaces only aggregate state (counts, message subjects/senders), never
message bodies or secrets. Operators who want auth can front it with the
existing ``NucleusTenantMiddleware`` or gate behind a reverse proxy.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

logger = logging.getLogger("nucleus.fleet_dashboard")

# Cap how many recent relay messages we render to keep the page bounded.
MAX_RELAY_MESSAGES = 20
# Cap how many characters of subject/sender we render (defence in depth
# against a runaway subject line blowing up the page).
_SUBJECT_TRUNC = 120
_SENDER_TRUNC = 60

# ── Brain path resolution ──────────────────────────────────────────────
#
# We resolve the brain root the same way the rest of the runtime does:
# NUCLEUS_BRAIN_ROOT env var → default ``.brain`` relative to CWD. The
# dashboard reads only files inside this root, so it never escapes to
# arbitrary filesystem locations.


def _brain_root() -> Path:
    """Resolve the brain root path. Mirrors runtime.common.get_brain_path
    but returns a Path and never raises (falls back to CWD/.brain)."""
    env = os.environ.get("NUCLEUS_BRAIN_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd() / ".brain"


# ── Data collectors ────────────────────────────────────────────────────


def _load_fleet_config(brain: Path) -> Dict[str, Any]:
    """Load ``.brain/fleet.json`` if present. Returns {} on missing/invalid."""
    path = brain / "fleet.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("fleet.json unreadable: %s", e)
        return {}


def _discover_agents(brain: Path, fleet_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build the agents-connected list.

    Source of truth (in priority order):
      1. ``fleet.json`` → ``agents`` map (each entry has role + transport).
      2. Fallback: subdirectories of ``.brain/relay/`` that contain at
         least one ``*.json`` message (a bucket with traffic is a live
         agent signal).

    Each returned entry: ``{role, transport, connection, inbox, connected}``.
    ``connected`` is True when the agent's relay bucket exists on disk.
    """
    agents: List[Dict[str, Any]] = []
    relay_root = brain / "relay"

    cfg_agents = fleet_cfg.get("agents") if isinstance(fleet_cfg.get("agents"), dict) else {}
    if cfg_agents:
        for role, info in cfg_agents.items():
            if not isinstance(info, dict):
                continue
            inbox_rel = info.get("inbox", f"relay/{role}")
            inbox_path = brain / inbox_rel
            connected = inbox_path.exists() and any(inbox_path.glob("*.json"))
            agents.append({
                "role": str(role),
                "transport": str(info.get("transport", "filesystem")),
                "connection": str(info.get("connection", "")),
                "inbox": str(inbox_rel),
                "connected": connected,
            })
        return agents

    # Fallback: discover from relay bucket dirs with traffic.
    if relay_root.exists():
        for d in sorted(relay_root.iterdir()):
            if not d.is_dir():
                continue
            # Skip non-agent housekeeping buckets.
            if d.name.startswith(".") or d.name in {
                "secretary", "secretary_archive", "task_comments",
                "drafts", "event_log.jsonl",
            }:
                continue
            has_traffic = any(d.glob("*.json"))
            agents.append({
                "role": d.name,
                "transport": "filesystem",
                "connection": str(d),
                "inbox": f"relay/{d.name}",
                "connected": has_traffic,
            })
    return agents


def _collect_recent_relays(brain: Path, limit: int = MAX_RELAY_MESSAGES) -> List[Dict[str, Any]]:
    """Walk every relay bucket and return the most recent messages.

    Each message is parsed minimally — we only surface id, from, to,
    subject, priority, created_at, and the bucket it landed in. Bodies
    are NEVER included (the dashboard is read-only and unauthenticated).
    """
    relay_root = brain / "relay"
    if not relay_root.exists():
        return []

    candidates: List[tuple[float, Dict[str, Any]]] = []
    for d in relay_root.iterdir():
        if not d.is_dir():
            continue
        for f in d.glob("*.json"):
            try:
                msg = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(msg, dict):
                continue
            ts = msg.get("created_at") or ""
            # ISO-8601 strings sort lexically by second; fall back to
            # file mtime for non-ISO or missing timestamps.
            sort_key = ts if isinstance(ts, str) and ts else str(f.stat().st_mtime)
            subject = str(msg.get("subject", "") or "")[:_SUBJECT_TRUNC]
            sender = str(msg.get("from", "") or "")[:_SENDER_TRUNC]
            candidates.append((sort_key, {
                "id": str(msg.get("id", f.name)),
                "from": sender,
                "to": str(msg.get("to", d.name)),
                "subject": subject,
                "priority": str(msg.get("priority", "normal")),
                "created_at": ts,
                "bucket": d.name,
            }))

    # Sort newest-first (lexically desc on ISO-8601 works for same-tz strings).
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return [m for _, m in candidates[:limit]]


def _count_tasks(brain: Path) -> Dict[str, int]:
    """Return PENDING / IN_PROGRESS / DONE / ESCALATED counts.

    Prefers the SQLite store (``.brain/nucleus.db``) since that's the
    production backend; falls back to JSON (``.brain/ledger/tasks.json``)
    when SQLite is unavailable (e.g., fresh checkout, JSON-only test env).
    """
    counts = {"PENDING": 0, "IN_PROGRESS": 0, "DONE": 0, "ESCALATED": 0}

    db_path = brain / "nucleus.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=2)
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT status, COUNT(*) FROM tasks "
                    "WHERE status IN ('PENDING','IN_PROGRESS','DONE','ESCALATED') "
                    "GROUP BY status"
                )
                for status, n in cur.fetchall():
                    if status and status.upper() in counts:
                        counts[status.upper()] = int(n)
            finally:
                conn.close()
            return counts
        except Exception as e:
            logger.warning("sqlite task count failed (%s); falling back to JSON", e)

    # JSON fallback
    json_path = brain / "ledger" / "tasks.json"
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for t in data:
                    if not isinstance(t, dict):
                        continue
                    s = str(t.get("status", "")).upper()
                    if s in counts:
                        counts[s] += 1
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("tasks.json unreadable: %s", e)

    return counts


def _count_verifications(brain: Path) -> Dict[str, int]:
    """Return confirmed / failed verification counts.

    Reads the ``verification_status`` column from the SQLite tasks table.
    Falls back to 0/0 when SQLite is unavailable (the JSON ledger doesn't
    carry verification status in the legacy shape).
    """
    counts = {"confirmed": 0, "failed": 0}

    db_path = brain / "nucleus.db"
    if not db_path.exists():
        return counts
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=2)
        try:
            cur = conn.cursor()
            # verification_status values: confirmed | failed | null
            cur.execute(
                "SELECT verification_status, COUNT(*) FROM tasks "
                "WHERE verification_status IN ('confirmed','failed') "
                "GROUP BY verification_status"
            )
            for status, n in cur.fetchall():
                if status == "confirmed":
                    counts["confirmed"] = int(n)
                elif status == "failed":
                    counts["failed"] = int(n)
        finally:
            conn.close()
    except Exception as e:
        logger.warning("verification count failed: %s", e)

    return counts


# ── HTML rendering ─────────────────────────────────────────────────────
#
# The page is a single self-contained HTML document. HTMX is loaded from
# the public CDN; the main panel re-fetches itself every 10s via
# hx-trigger="every 10s" on a <div>. A <meta http-equiv="refresh"> tag
# provides a non-JS fallback so the page auto-refreshes even if the HTMX
# CDN is unreachable.


def _esc(text: str) -> str:
    """Minimal HTML-escape for safe interpolation of untrusted strings."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _render_agents(agents: List[Dict[str, Any]]) -> str:
    if not agents:
        return "<p class='empty'>No agents configured. Run <code>nucleus fleet init</code> to provision a fleet.</p>"
    rows = []
    for a in agents:
        status_cls = "online" if a.get("connected") else "offline"
        status_txt = "connected" if a.get("connected") else "no traffic"
        rows.append(
            f"<tr>"
            f"<td class='role'>{_esc(a['role'])}</td>"
            f"<td>{_esc(a.get('transport', 'filesystem'))}</td>"
            f"<td class='mono'>{_esc(a.get('inbox', ''))}</td>"
            f"<td><span class='badge {status_cls}'>{status_txt}</span></td>"
            f"</tr>"
        )
    return (
        "<table class='data'><thead><tr>"
        "<th>Agent</th><th>Transport</th><th>Inbox</th><th>Status</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _render_relays(messages: List[Dict[str, Any]]) -> str:
    if not messages:
        return "<p class='empty'>No relay traffic yet.</p>"
    rows = []
    for m in messages:
        prio = _esc(m.get("priority", "normal"))
        prio_cls = f"prio-{prio}" if prio in ("urgent", "critical", "high") else "prio-normal"
        rows.append(
            f"<tr>"
            f"<td class='mono small'>{_esc(m.get('created_at', ''))}</td>"
            f"<td class='from'>{_esc(m.get('from', ''))}</td>"
            f"<td class='to'>{_esc(m.get('to', ''))}</td>"
            f"<td><span class='badge {prio_cls}'>{prio}</span></td>"
            f"<td class='subject'>{_esc(m.get('subject', ''))}</td>"
            f"</tr>"
        )
    return (
        "<table class='data'><thead><tr>"
        "<th>Time</th><th>From</th><th>To</th><th>Priority</th><th>Subject</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _render_tasks(counts: Dict[str, int]) -> str:
    total = sum(counts.values())
    return (
        "<div class='metric-grid'>"
        f"<div class='metric pending'><span class='n'>{counts['PENDING']}</span><span class='l'>Pending</span></div>"
        f"<div class='metric inprogress'><span class='n'>{counts['IN_PROGRESS']}</span><span class='l'>In Progress</span></div>"
        f"<div class='metric done'><span class='n'>{counts['DONE']}</span><span class='l'>Done</span></div>"
        f"<div class='metric escalated'><span class='n'>{counts['ESCALATED']}</span><span class='l'>Escalated</span></div>"
        f"<div class='metric total'><span class='n'>{total}</span><span class='l'>Total</span></div>"
        "</div>"
    )


def _render_verifications(counts: Dict[str, int]) -> str:
    return (
        "<div class='metric-grid'>"
        f"<div class='metric confirmed'><span class='n'>{counts['confirmed']}</span><span class='l'>Confirmed</span></div>"
        f"<div class='metric failed'><span class='n'>{counts['failed']}</span><span class='l'>Failed</span></div>"
        "</div>"
    )


_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="10">
  <title>Nucleus Fleet Dashboard</title>
  <script src="https://unpkg.com/htmx.org@1.9.12" crossorigin="anonymous"></script>
  <style>
    :root {{
      --bg: #0d1117; --panel: #161b22; --border: #30363d;
      --fg: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
      --green: #3fb950; --yellow: #d29922; --red: #f85149;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 1.5rem; background: var(--bg); color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 14px; line-height: 1.5;
    }}
    h1 {{ margin: 0 0 0.25rem 0; font-size: 1.5rem; }}
    h2 {{ margin: 1.5rem 0 0.75rem 0; font-size: 1.1rem; color: var(--accent); }}
    .sub {{ color: var(--muted); margin-bottom: 1.5rem; }}
    .panel {{
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 6px; padding: 1rem; margin-bottom: 1.25rem;
    }}
    table.data {{ width: 100%; border-collapse: collapse; }}
    table.data th {{
      text-align: left; padding: 0.5rem 0.5rem; border-bottom: 1px solid var(--border);
      color: var(--muted); font-weight: 600; font-size: 0.85rem;
      text-transform: uppercase; letter-spacing: 0.04em;
    }}
    table.data td {{ padding: 0.5rem 0.5rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
    table.data tr:last-child td {{ border-bottom: none; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }}
    .small {{ font-size: 0.8rem; color: var(--muted); white-space: nowrap; }}
    .from, .to {{ font-size: 0.85rem; }}
    .subject {{ max-width: 40ch; }}
    .badge {{
      display: inline-block; padding: 0.1rem 0.5rem; border-radius: 10px;
      font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.03em; border: 1px solid var(--border); color: var(--muted);
    }}
    .badge.online {{ color: var(--green); border-color: var(--green); }}
    .badge.offline {{ color: var(--muted); }}
    .badge.prio-urgent, .badge.prio-critical {{ color: var(--red); border-color: var(--red); }}
    .badge.prio-high {{ color: var(--yellow); border-color: var(--yellow); }}
    .badge.prio-normal {{ color: var(--muted); }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.75rem; }}
    .metric {{
      background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
      padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 0.25rem;
    }}
    .metric .n {{ font-size: 1.75rem; font-weight: 700; }}
    .metric .l {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
    .metric.done .n, .metric.confirmed .n {{ color: var(--green); }}
    .metric.inprogress .n {{ color: var(--accent); }}
    .metric.pending .n {{ color: var(--yellow); }}
    .metric.escalated .n, .metric.failed .n {{ color: var(--red); }}
    .metric.total .n {{ color: var(--fg); }}
    .empty {{ color: var(--muted); font-style: italic; }}
    footer {{ margin-top: 2rem; color: var(--muted); font-size: 0.8rem; }}
    .refresh-indicator::after {{ content: " · auto-refresh 10s"; color: var(--muted); }}
  </style>
</head>
<body>
  <h1>Nucleus Fleet Dashboard</h1>
  <div class="sub refresh-indicator">Live fleet status · relay traffic · task progress · verification</div>

  <div hx-get="/fleet/panel" hx-trigger="every 10s" hx-swap="innerHTML" id="fleet-panel">
    {panel}
  </div>

  <footer>
    Nucleus · fleet dashboard · HTMX auto-refresh every 10s ·
    <a href="/fleet" style="color:var(--accent)">manual refresh</a>
  </footer>
</body>
</html>
"""

_PANEL_TEMPLATE = """<section class="panel" id="fleet-status">
  <h2>Fleet Status <span class="small">({agents_count} agents)</span></h2>
  {agents_html}
</section>
<section class="panel" id="relay-traffic">
  <h2>Relay Traffic <span class="small">(recent {relay_count})</span></h2>
  {relay_html}
</section>
<section class="panel" id="task-progress">
  <h2>Task Progress</h2>
  {tasks_html}
</section>
<section class="panel" id="verification-results">
  <h2>Verification Results</h2>
  {verification_html}
</section>
"""


def _build_panel(brain: Path) -> str:
    """Render just the inner panel (used by the HTMX partial endpoint)."""
    fleet_cfg = _load_fleet_config(brain)
    agents = _discover_agents(brain, fleet_cfg)
    messages = _collect_recent_relays(brain)
    task_counts = _count_tasks(brain)
    ver_counts = _count_verifications(brain)

    return _PANEL_TEMPLATE.format(
        agents_count=len(agents),
        agents_html=_render_agents(agents),
        relay_count=len(messages),
        relay_html=_render_relays(messages),
        tasks_html=_render_tasks(task_counts),
        verification_html=_render_verifications(ver_counts),
    )


def _build_page(brain: Path) -> str:
    """Render the full HTML page (used by GET /fleet)."""
    return _PAGE_TEMPLATE.format(panel=_build_panel(brain))


# ── Route handlers ─────────────────────────────────────────────────────


async def get_fleet_dashboard(request: Request) -> HTMLResponse:
    """GET /fleet — full HTML dashboard page."""
    brain = _brain_root()
    html = _build_page(brain)
    return HTMLResponse(html)


async def get_fleet_panel(request: Request) -> HTMLResponse:
    """GET /fleet/panel — HTMX partial (inner panel only).

    The main page's <div hx-get="/fleet/panel" hx-trigger="every 10s">
    polls this endpoint to refresh the live data without a full page
    reload. Returns just the four <section> panels.
    """
    brain = _brain_root()
    html = _build_panel(brain)
    return HTMLResponse(html)


# ── Routes ─────────────────────────────────────────────────────────────

fleet_dashboard_route = Route("/fleet", get_fleet_dashboard, methods=["GET"])
fleet_panel_route = Route("/fleet/panel", get_fleet_panel, methods=["GET"])

# Convenience aggregate for callers that want both routes at once.
fleet_dashboard_routes = [fleet_dashboard_route, fleet_panel_route]
