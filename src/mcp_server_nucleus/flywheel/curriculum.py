"""Curriculum refresh — close the compound loop.

Walks pending DPO pairs written by file_ticket() and tries to fill their
`chosen` field from subsequent fixes (heuristically: if a ticket's step is
followed by a survived claim for the same step, the pair is marked ready).

This is the mechanism that turns failures into training data without a
human in the loop.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .csr import read_csr


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def curriculum_refresh(brain_path: Path) -> Dict[str, Any]:
    """Walk the pending pairs and mark ready any whose step has since survived.

    Returns a summary dict:
        {
            "scanned": int,
            "ready": int,           # had chosen filled
            "still_pending": int,
            "output": path,
        }
    """
    bp = Path(brain_path)
    training_dir = bp / "training" / "exports"
    pending_path = training_dir / "unified_dpo_pending.jsonl"
    if not pending_path.exists():
        return {"scanned": 0, "ready": 0, "still_pending": 0, "output": str(pending_path)}

    # Build a set of steps that have survived claims
    csr = read_csr(bp)
    survived_steps: set = set()
    for claim in csr.get("recent_claims", []):
        if claim.get("survived"):
            step = claim.get("step", "")
            # step may be "phase:step" — extract the step component
            survived_steps.add(step.split(":", 1)[-1] if ":" in step else step)
            survived_steps.add(step)  # also add the full label

    # Rewrite the pending file, promoting ready pairs
    ready_path = training_dir / "unified_dpo_ready.jsonl"
    still_pending: List[Dict[str, Any]] = []
    ready_count = 0
    scanned = 0

    with open(pending_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            scanned += 1
            try:
                pair = json.loads(line)
            except json.JSONDecodeError:
                continue

            step_key = (pair.get("prompt", "") or "").split("\n", 1)[0]
            step_key = step_key.replace("Step: ", "").strip()

            if step_key in survived_steps and not pair.get("chosen"):
                pair["chosen"] = (
                    f"Resolved: the `{step_key}` step now survives verification. "
                    "See flywheel recent_claims for the survival signal."
                )
                pair["quality"] = "curriculum"
                pair["promoted_at"] = _now_iso()
                with open(ready_path, "a") as ready_f:
                    ready_f.write(json.dumps(pair) + "\n")
                ready_count += 1
            else:
                still_pending.append(pair)

    # Overwrite pending with the still-pending set
    with open(pending_path, "w") as f:
        for pair in still_pending:
            f.write(json.dumps(pair) + "\n")

    return {
        "scanned": scanned,
        "ready": ready_count,
        "still_pending": len(still_pending),
        "output": str(ready_path),
    }
