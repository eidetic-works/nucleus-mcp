"""Cold-start acceptance endpoint instrument (PRINCIPAL G1 criterion 2).

Authority: docs/PRINCIPAL.md:71-74 (G1 criterion 2 — "Cold-start ≤5 min to the
acceptance ENDPOINT (config provably written + seed engram recalled on screen —
not a stopwatch on a no-op)"). Immutable source: docs/PRINCIPAL.md@principal-v3.

Acceptance (rerunnable evidence, not narration):
  - Instrument proves config written (project-local ``.mcp.json`` with the
    nucleus server entry) AND seed engram recalled on screen (the recall
    output is captured into the verdict — the printout IS the proof memory
    survives, mirroring ``_finish_init_with_value``'s self-test).
  - Wall time is measured to the acceptance ENDPOINT (init → config write →
    engram write → engram recall), not a stopwatch on a no-op. The clock
    stops the instant the seed engram is recalled successfully.
  - The clean-environment recipe is committed and rerunnable: a fresh temp
    project dir + fresh ``.brain`` via the EXISTING ``init_brain_default``,
    no hand-editing.

Mechanism
---------
This instrument wires THREE existing nucleus capabilities end-to-end and
measures the wall time across the join:

  1. ``cli.init_brain_default`` — the EXISTING brain scaffold (creates
     ledger/sessions/slots/agents/memory/config dirs + seed files). This is
     the same function ``nucleus init`` calls; the instrument does NOT
     re-implement scaffolding.
  2. The project-local ``.mcp.json`` config write — the EXISTING pattern from
     ``cli._finish_init_with_value`` step (a): write
     ``{"mcpServers": {"nucleus": {"command": "nucleus-mcp"}}}``. The
     instrument asserts the file exists and parses with the nucleus entry.
  3. ``engram_ops._brain_write_engram_impl`` + ``_brain_search_engrams_impl``
     — the EXISTING engram write + substring search. The instrument writes a
     ``nucleus_init`` seed engram, searches "initialized", and asserts the
     seed is recalled. The recalled value is captured into the verdict
     (on-screen proof).

Silence cannot satisfy the check: the instrument FAILS when (a) the config
file is missing or lacks the nucleus entry, (b) the engram write returns an
error, or (c) the engram search returns zero hits for "initialized". A
no-op (init skipped, engram never written) cannot pass.

The wall clock starts before ``init_brain_default`` and stops after the
engram recall succeeds — the full cold-start-to-acceptance-endpoint path.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("NucleusJobs.cold_start")

INSTRUMENT_NAME = "cold_start_instrument"
EVIDENCE_DIRNAME = "cold_start_runs"
ACCEPTANCE_ENDPOINT_QUERY = "initialized"
SEED_ENGRAM_KEY = "nucleus_init"
SEED_ENGRAM_CONTEXT = "Decision"
SEED_ENGRAM_INTENSITY = 5
NUCLEUS_MCP_COMMAND = "nucleus-mcp"
COLD_START_BUDGET_SECONDS = 300  # G1 criterion 2: ≤5 min


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evidence_log_path(brain_path: Optional[Path] = None) -> Path:
    """Append-only JSONL run log under the brain's evidence dir."""
    from .common import get_brain_path

    root = brain_path or get_brain_path()
    d = root / "evidence" / EVIDENCE_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d / "run_log.jsonl"


def _append_run_log(record: Dict[str, Any], brain_path: Optional[Path] = None) -> Path:
    path = _evidence_log_path(brain_path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def _write_project_mcp_config(project_dir: Path) -> Dict[str, Any]:
    """Write the project-local .mcp.json — mirrors cli._finish_init_with_value (a).

    Returns a dict describing what was written so the instrument can assert it.
    """
    mcp_path = project_dir / ".mcp.json"
    config = {"mcpServers": {"nucleus": {"command": NUCLEUS_MCP_COMMAND}}}
    mcp_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(mcp_path),
        "content": config,
        "nucleus_entry_present": True,
    }


def _verify_project_mcp_config(project_dir: Path) -> Dict[str, Any]:
    """Re-read .mcp.json from disk and assert the nucleus entry survived."""
    mcp_path = project_dir / ".mcp.json"
    if not mcp_path.exists():
        return {"exists": False, "nucleus_entry_present": False, "error": "missing"}
    try:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"exists": True, "nucleus_entry_present": False, "error": f"unparseable: {e}"}
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    has_nucleus = isinstance(servers, dict) and "nucleus" in servers
    return {
        "exists": True,
        "nucleus_entry_present": has_nucleus,
        "nucleus_command": (servers or {}).get("nucleus", {}).get("command") if has_nucleus else None,
    }


def _recall_seed_engram(brain_path: Path, project_slug: str) -> Dict[str, Any]:
    """Write the seed engram and recall it — mirrors cli._finish_init_with_value (b).

    Returns the recall result so the instrument can assert the seed survived
    and capture the recalled value (on-screen proof).
    """
    from .engram_ops import _brain_search_engrams_impl, _brain_write_engram_impl
    from ..cli_output import parse_runtime_response

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    seed_value = f"Nucleus initialized {stamp} in {project_slug}"

    write_raw = _brain_write_engram_impl(
        SEED_ENGRAM_KEY, seed_value, SEED_ENGRAM_CONTEXT, SEED_ENGRAM_INTENSITY
    )
    w_ok, _w_data, w_err = parse_runtime_response(write_raw)
    if not w_ok:
        return {
            "written": False,
            "write_error": w_err,
            "recalled": False,
            "recall_ms": None,
            "recalled_value": None,
            "hits": 0,
        }

    t0 = time.perf_counter()
    search_raw = _brain_search_engrams_impl(
        ACCEPTANCE_ENDPOINT_QUERY, case_sensitive=False, limit=5
    )
    recall_ms = int((time.perf_counter() - t0) * 1000)
    s_ok, s_data, s_err = parse_runtime_response(search_raw)
    if not s_ok:
        return {
            "written": True,
            "recalled": False,
            "recall_error": s_err,
            "recall_ms": recall_ms,
            "recalled_value": None,
            "hits": 0,
        }

    hits: list = []
    if isinstance(s_data, list):
        hits = s_data
    elif isinstance(s_data, dict):
        hits = s_data.get("engrams") or s_data.get("results") or []

    recalled_value = None
    if hits and isinstance(hits[0], dict):
        recalled_value = hits[0].get("value")

    return {
        "written": True,
        "recalled": bool(hits),
        "recall_ms": recall_ms,
        "recalled_value": recalled_value,
        "hits": len(hits),
        "seed_value": seed_value,
    }


def run_cold_start_instrument(
    *,
    brain_path: Optional[Path] = None,
    project_slug: str = "cold_start_probe",
    template: str = "default",
) -> Dict[str, Any]:
    """Run the cold-start acceptance endpoint instrument in a clean environment.

    The instrument creates a fresh temp project dir + fresh ``.brain`` via the
    EXISTING ``init_brain_default``, writes the project ``.mcp.json``, writes a
    seed engram, and recalls it. Wall time is measured from the start of init
    to the successful engram recall — the full cold-start-to-acceptance-endpoint
    path, not a no-op.

    Returns a verdict dict:
      - ``config_written``: True iff ``.mcp.json`` exists with the nucleus entry.
      - ``seed_engram_recalled``: True iff the seed engram was written AND
        recalled by searching "initialized".
      - ``recalled_value``: the on-screen proof — the recalled engram value.
      - ``wall_time_seconds``: measured to the acceptance endpoint.
      - ``within_budget``: True iff wall_time ≤ 300s (G1 criterion 2 ≤5 min).
      - ``verdict``: "PASS" iff config_written AND seed_engram_recalled.
      - ``evidence_log_path``: append-only run log under the brain.
    """
    from .common import get_brain_path

    bp = brain_path or get_brain_path()
    run_id = f"cs_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    started_at = _utc_now_iso()

    # ── Clean environment: fresh temp project + fresh brain ──
    # init_brain_default is the EXISTING scaffold used by `nucleus init`.
    # We call it directly (not the CLI subprocess) so the instrument is
    # hermetic and rerunnable without spawning a process.
    from ..cli import init_brain_default

    wall_t0 = time.perf_counter()
    init_error: Optional[str] = None

    with tempfile.TemporaryDirectory(prefix="cold_start_") as tmp:
        tmp_path = Path(tmp)
        project_dir = tmp_path / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)
        fresh_brain = project_dir / ".brain"

        # Point the runtime at the fresh brain for the engram ops.
        os.environ["NUCLEUS_BRAIN_PATH"] = str(fresh_brain.absolute())

        # ── 1. init_brain_default (EXISTING scaffold) ──
        try:
            init_brain_default(fresh_brain)
        except Exception as e:
            init_error = f"init_brain_default crashed: {e}"

        # ── 2. write project .mcp.json (EXISTING pattern) ──
        config_written = False
        config_detail: Dict[str, Any] = {}
        if init_error is None:
            try:
                _write_project_mcp_config(project_dir)
                config_detail = _verify_project_mcp_config(project_dir)
                config_written = config_detail.get("nucleus_entry_present", False)
            except Exception as e:
                config_detail = {"error": f"config write/verify crashed: {e}"}

        # ── 3. seed engram write + recall (EXISTING engram_ops) ──
        recall: Dict[str, Any] = {}
        if init_error is None and config_written:
            try:
                recall = _recall_seed_engram(fresh_brain, project_slug)
            except Exception as e:
                recall = {"written": False, "recalled": False, "error": f"recall crashed: {e}"}

    wall_seconds = round(time.perf_counter() - wall_t0, 3)

    seed_recalled = bool(recall.get("recalled"))
    verdict = "PASS" if (config_written and seed_recalled and init_error is None) else "FAIL"

    record: Dict[str, Any] = {
        "run_id": run_id,
        "instrument": INSTRUMENT_NAME,
        "authority": "docs/PRINCIPAL.md:71-74",
        "immutable_source": "docs/PRINCIPAL.md@principal-v3",
        "started_at_utc": started_at,
        "finished_at_utc": _utc_now_iso(),
        "project_slug": project_slug,
        "template": template,
        "acceptance_endpoint": {
            "query": ACCEPTANCE_ENDPOINT_QUERY,
            "seed_engram_key": SEED_ENGRAM_KEY,
            "definition": "config written + seed engram recalled on screen",
        },
        "init_error": init_error,
        "config_written": config_written,
        "config_detail": config_detail,
        "seed_engram_written": recall.get("written", False),
        "seed_engram_recalled": seed_recalled,
        "recalled_value": recall.get("recalled_value"),
        "recall_hits": recall.get("hits", 0),
        "recall_ms": recall.get("recall_ms"),
        "wall_time_seconds": wall_seconds,
        "within_budget": wall_seconds <= COLD_START_BUDGET_SECONDS,
        "budget_seconds": COLD_START_BUDGET_SECONDS,
        "verdict": verdict,
    }
    if recall.get("error"):
        record["recall_error"] = recall["error"]
    if recall.get("write_error"):
        record["write_error"] = recall["write_error"]

    log_path = _append_run_log(record, brain_path=bp)

    out: Dict[str, Any] = {
        "config_written": config_written,
        "seed_engram_recalled": seed_recalled,
        "recalled_value": recall.get("recalled_value"),
        "seed_value": recall.get("seed_value"),
        "wall_time_seconds": wall_seconds,
        "within_budget": wall_seconds <= COLD_START_BUDGET_SECONDS,
        "verdict": verdict,
        "run_id": run_id,
        "evidence_log_path": str(log_path),
    }
    if init_error:
        out["error"] = init_error
    if not config_written and not init_error:
        out["error"] = (
            "CONFIG NOT WRITTEN: .mcp.json is missing or lacks the nucleus "
            "server entry — the cold-start config step failed."
        )
    if config_written and not seed_recalled and not init_error:
        out["error"] = (
            "SEED ENGRAM NOT RECALLED: the seed engram was written but the "
            "search for 'initialized' returned zero hits — memory did not "
            "survive the cold start."
        )
    return out


if __name__ == "__main__":
    result = run_cold_start_instrument()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("verdict") == "PASS" else 1)
