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
        # Corrupted → preserve the evidence before resetting. CSR is the
        # trust scalar read before closing a session (per CLAUDE.md); a
        # corruption event is itself the strongest possible signal that
        # something broke, so silently presenting a perfect 1.0 with no
        # trace of the corrupted history is exactly backwards. Back the
        # corrupt file up for forensics, then reset so the caller still
        # gets a usable (if reset) state instead of crashing.
        try:
            backup = p.with_suffix(f".corrupt-{int(datetime.now(timezone.utc).timestamp())}.json")
            backup.write_text(p.read_text())
        except OSError:
            pass
        state = _default_state()
        state["corrupted_and_reset"] = True
        p.write_text(json.dumps(state, indent=2))
        return state


def _write_csr(brain_path: Path, state: Dict[str, Any]) -> None:
    state["last_updated"] = _now_iso()
    total = max(state.get("claims_total", 0), 1)
    survived = state.get("claims_survived", 0)
    state["ratio"] = round(survived / total, 4)
    _csr_path(brain_path).write_text(json.dumps(state, indent=2))


def _append_survived_log(brain_path: Path, step: str, survived: bool,
                         reason: str = "") -> None:
    """Append one line to flywheel/survived.jsonl.

    WHY THIS EXISTS (2026-08-16). `survived.jsonl` had accumulated 159 lines and
    had ZERO code references — nothing wrote it, nothing read it. It was appended
    by hand, by convention, while the machine-maintained metric (`csr.json`) went
    its own way. On 2026-08-14/15 roughly twenty closures were recorded into that
    file and the CSR never moved: ratio stayed 0.6375, last_updated frozen.

    A ledger nobody writes programmatically and nobody reads is not a ledger. It
    is a surface that LOOKS like evidence, which is strictly worse than nothing —
    the same "reported success while doing nothing" shape this whole substrate
    exists to name, found inside the substrate itself.

    So the convention becomes a mechanism: the same call that moves the metric
    also writes the log. Best-effort — a logging failure must never lose the
    metric bump, which is the load-bearing half.

    NOT BACKFILLED, deliberately. `bump_survived` increments BOTH claims_total
    and claims_survived, so replaying the 159 orphans would add 159 to each and
    push the ratio toward 1.0 — manufacturing exactly the false-green this
    guards against — while evicting all 50 genuine entries from recent_claims.
    The historical gap is left visible rather than papered over.
    """
    try:
        fw_dir = _ensure_flywheel_dir(brain_path)
        rec = {
            "phase": "unknown",
            "step": step,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "survived": survived,
            "reason": reason,
            "source": "bump",   # distinguishes machine-written from hand-appended
        }
        if ":" in step:                       # callers pass "phase:step"
            phase, _, tail = step.partition(":")
            rec["phase"], rec["step"] = phase, tail
        with (fw_dir / "survived.jsonl").open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass          # never let the log cost us the metric


def bump_survived(brain_path: Path, step: str = "unknown") -> Dict[str, Any]:
    """Record a survived claim. Returns the updated state."""
    state = read_csr(brain_path)
    state["claims_total"] = state.get("claims_total", 0) + 1
    state["claims_survived"] = state.get("claims_survived", 0) + 1
    recent = state.setdefault("recent_claims", [])
    recent.append({"at": _now_iso(), "step": step, "survived": True})
    state["recent_claims"] = recent[-50:]  # cap to last 50
    _write_csr(brain_path, state)
    _append_survived_log(brain_path, step, survived=True)
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
    _append_survived_log(brain_path, step, survived=False, reason=reason)
    return state
