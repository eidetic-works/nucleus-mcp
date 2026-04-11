"""Claim Survival Rate — the core metric.

A claim is made when the system asserts something works. A claim survives when
runtime verification (tests, CI, Tier 5, driver success) confirms it. CSR is
simply the ratio: survived / total.

CSR starts at 1 for a reason: the activation commit itself is the founding
claim, proven by hermetic tests. It is a founding claim, not a runtime claim.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def _csr_path(brain_path: Path) -> Path:
    return Path(brain_path) / "flywheel" / "csr.json"


def _ensure_flywheel_dir(brain_path: Path) -> Path:
    fw_dir = Path(brain_path) / "flywheel"
    fw_dir.mkdir(parents=True, exist_ok=True)
    return fw_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> Dict[str, Any]:
    return {
        "claims_total": 1,
        "claims_survived": 1,
        "claims_unsurvived": 0,
        "ratio": 1.0,
        "first_claim_at": _now_iso(),
        "last_updated": _now_iso(),
        "recent_claims": [],
    }


def read_csr(brain_path: Path) -> Dict[str, Any]:
    """Read CSR state, creating the founding claim if missing."""
    _ensure_flywheel_dir(brain_path)
    p = _csr_path(brain_path)
    if not p.exists():
        state = _default_state()
        p.write_text(json.dumps(state, indent=2))
        return state
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        # Corrupted → reset to founding state. Better than crashing the caller;
        # a corrupted CSR file is a disposable cache, not a sacred ledger.
        state = _default_state()
        p.write_text(json.dumps(state, indent=2))
        return state


def _write_csr(brain_path: Path, state: Dict[str, Any]) -> None:
    state["last_updated"] = _now_iso()
    total = max(state.get("claims_total", 0), 1)
    survived = state.get("claims_survived", 0)
    state["ratio"] = round(survived / total, 4)
    _csr_path(brain_path).write_text(json.dumps(state, indent=2))


def bump_survived(brain_path: Path, step: str = "unknown") -> Dict[str, Any]:
    """Record a survived claim. Returns the updated state."""
    state = read_csr(brain_path)
    state["claims_total"] = state.get("claims_total", 0) + 1
    state["claims_survived"] = state.get("claims_survived", 0) + 1
    recent = state.setdefault("recent_claims", [])
    recent.append({"at": _now_iso(), "step": step, "survived": True})
    state["recent_claims"] = recent[-50:]  # cap to last 50
    _write_csr(brain_path, state)
    return state


def bump_unsurvived(brain_path: Path, step: str, reason: str = "") -> Dict[str, Any]:
    """Record an unsurvived (failed) claim. Returns the updated state."""
    state = read_csr(brain_path)
    state["claims_total"] = state.get("claims_total", 0) + 1
    state["claims_unsurvived"] = state.get("claims_unsurvived", 0) + 1
    recent = state.setdefault("recent_claims", [])
    recent.append({"at": _now_iso(), "step": step, "survived": False, "reason": reason})
    state["recent_claims"] = recent[-50:]
    _write_csr(brain_path, state)
    return state
