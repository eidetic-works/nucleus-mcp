"""Seeded cross-project block instrument (PRINCIPAL G1 workstream 2).

Authority: docs/PRINCIPAL.md:67-73,149 (G1 workstream 2; named seeded-block
instrument). Immutable source: docs/PRINCIPAL.md@principal-v3.

Acceptance (rerunnable evidence, not narration):
  - A positive injected cross-project relay is asserted BLOCKED and
    conflict-logged.
  - The instrument is named, committed, rerunnable, and scheduled weekly.
  - Silence cannot satisfy the check.

Mechanism
---------
This instrument wires the EXISTING cross-project block in
``relay.core._project_visible`` (the "fashion-leak block", ADR-0042 D3): a
relay envelope stamped with project A's slug, read by a reader in project B
(different slug), is DROPPED — never surfaced. The instrument:

  1. Injects a positive cross-project relay envelope (writer in project A,
     addressed to a shared role bucket that project B's reader also reads).
  2. Reads the bucket from project B's cwd.
  3. Asserts the cross-project envelope is NOT surfaced (BLOCKED).
  4. Conflict-logs the event to a committed, append-only evidence log.

The block is the existing ``_project_visible`` returning ``(False, False)``
(DROP). This module does NOT re-implement the block — it instruments it.

Silence cannot satisfy the check: the instrument fails when (a) the
cross-project envelope is NOT blocked (leak), or (b) the same-project control
envelope is NOT surfaced (over-block). Both directions are asserted.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("NucleusJobs.seeded_block")

INSTRUMENT_NAME = "seeded_block_instrument"
CONFLICT_LOG_DIRNAME = "seeded_block_conflicts"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _conflict_log_path(brain_path: Optional[Path] = None) -> Path:
    """Append-only JSONL conflict log under the brain's evidence dir."""
    from .common import get_brain_path

    root = brain_path or get_brain_path()
    if not isinstance(root, Path):
        root = Path(root)
    d = root / "evidence" / CONFLICT_LOG_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d / "conflict_log.jsonl"


def _append_conflict_log(record: Dict[str, Any], brain_path: Optional[Path] = None) -> Path:
    """Append a conflict-log record. Returns the log path."""
    path = _conflict_log_path(brain_path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def _make_project_dir(base: Path, slug: str, remote: str) -> Path:
    """Create a minimal project dir with a git remote so resolve_project sees it."""
    import subprocess

    root = base / slug
    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", remote],
                   check=True, capture_output=True)
    return root


def run_seeded_block_instrument(
    *,
    brain_path: Optional[Path] = None,
    project_a_slug: str = "bespoq",
    project_a_remote: str = "https://github.com/eidetic-works/bespoq.git",
    project_b_slug: str = "fashion",
    project_b_remote: str = "https://github.com/eidetic-works/fashion.git",
    bucket: str = "claude_code_main",
    sender: str = "seeded_block_instrument",
) -> Dict[str, Any]:
    """Inject a cross-project relay, assert BLOCKED, conflict-log.

    Returns a verdict dict with:
      - ``blocked``: True iff the cross-project envelope was NOT surfaced to
        the foreign reader (the block held).
      - ``control_surfaced``: True iff the same-project control envelope WAS
        surfaced (proves the reader is alive — silence cannot pass).
      - ``conflict_logged``: True iff the conflict log was appended.
      - ``evidence``: the surfaced message ids per reader.
      - ``error``: present on failure.
    """
    import tempfile

    from .relay.core import relay_inbox, relay_post

    # The project spine flag MUST be ON for the cross-project block to fire.
    # The instrument sets it in-process; callers running outside should export
    # NUCLEUS_PROJECT_SPINE=1.
    os.environ["NUCLEUS_PROJECT_SPINE"] = "1"

    from .common import get_brain_path

    bp = brain_path or get_brain_path()

    run_id = f"sb_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    started_at = _utc_now_iso()

    _orig_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory(prefix="seeded_block_") as tmp:
            tmp_path = Path(tmp)
            # Shared brain relay root so both projects write into one bucket.
            shared_brain = tmp_path / "shared_brain"
            (shared_brain / "relay").mkdir(parents=True, exist_ok=True)
            os.environ["NUCLEUS_BRAIN_PATH"] = str(shared_brain)

            proj_a = _make_project_dir(tmp_path, project_a_slug, project_a_remote)
            proj_b = _make_project_dir(tmp_path, project_b_slug, project_b_remote)

            # ── 1. Inject a POSITIVE cross-project relay from project A ──
            os.chdir(proj_a)
            cross_subject = f"[SEEDED-BLOCK] cross-project probe {run_id}"
            cross_body = (
                f"Seeded cross-project relay from {project_a_slug} → {bucket}. "
                f"This envelope MUST be BLOCKED for {project_b_slug} readers. "
                f"run_id={run_id}"
            )
            r_cross = relay_post(
                to=bucket, subject=cross_subject, body=cross_body,
                sender=sender, priority="normal",
            )
            cross_id = r_cross.get("message_id", "")
            if not cross_id or not r_cross.get("sent"):
                return {"blocked": False, "error": f"cross-project post failed: {r_cross}",
                         "conflict_logged": False}

            # ── 2. Inject a SAME-project control relay from project B ──
            os.chdir(proj_b)
            ctrl_subject = f"[SEEDED-BLOCK] control probe {run_id}"
            ctrl_body = (
                f"Same-project control relay from {project_b_slug} → {bucket}. "
                f"This envelope MUST be surfaced for {project_b_slug} readers. "
                f"run_id={run_id}"
            )
            r_ctrl = relay_post(
                to=bucket, subject=ctrl_subject, body=ctrl_body,
                sender=sender, priority="normal",
            )
            ctrl_id = r_ctrl.get("message_id", "")
            if not ctrl_id or not r_ctrl.get("sent"):
                return {"blocked": False, "error": f"control post failed: {r_ctrl}",
                         "conflict_logged": False}

            # ── 3. Read the bucket from project B's cwd ──
            os.chdir(proj_b)
            inbox = relay_inbox(force_fs=True, recipient=bucket, unread_only=False)
            surfaced_ids = {
                m.get("id") for m in inbox.get("messages", []) if m.get("id")
            }

            cross_blocked = cross_id not in surfaced_ids
            control_surfaced = ctrl_id in surfaced_ids

            # ── 4. Conflict-log the event ──
            record = {
                "run_id": run_id,
                "instrument": INSTRUMENT_NAME,
                "authority": "docs/PRINCIPAL.md:67-73,149",
                "immutable_source": "docs/PRINCIPAL.md@principal-v3",
                "started_at_utc": started_at,
                "finished_at_utc": _utc_now_iso(),
                "project_a_slug": project_a_slug,
                "project_b_slug": project_b_slug,
                "bucket": bucket,
                "cross_project_envelope_id": cross_id,
                "control_envelope_id": ctrl_id,
                "cross_project_blocked": cross_blocked,
                "control_surfaced": control_surfaced,
                "surfaced_ids": sorted(surfaced_ids),
                "verdict": "PASS" if (cross_blocked and control_surfaced) else "FAIL",
            }
            log_path = _append_conflict_log(record, brain_path=bp)
    finally:
        os.chdir(_orig_cwd)

    verdict = {
        "blocked": cross_blocked,
        "control_surfaced": control_surfaced,
        "conflict_logged": True,
        "conflict_log_path": str(log_path),
        "run_id": run_id,
        "cross_project_envelope_id": cross_id,
        "control_envelope_id": ctrl_id,
        "verdict": record["verdict"],
    }
    if not cross_blocked:
        verdict["error"] = (
            "CROSS-PROJECT LEAK: the foreign envelope was surfaced to the "
            f"{project_b_slug} reader — the block failed."
        )
    elif not control_surfaced:
        verdict["error"] = (
            "OVER-BLOCK: the same-project control envelope was NOT surfaced — "
            "the reader is silent, which cannot satisfy the check."
        )
    return verdict


if __name__ == "__main__":
    result = run_seeded_block_instrument()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("verdict") == "PASS" else 1)
