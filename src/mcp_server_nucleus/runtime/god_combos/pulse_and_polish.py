"""
Pulse & Polish God Combo — automated health check pipeline.

Runs: prometheus → audit → brief → engram write.
"""

from ...runtime.common import get_brain_path, logger


def run_pulse_and_polish(write_engram: bool = True) -> dict:
    """Run the pulse-and-polish health pipeline."""
    results = {
        "steps": [],
        "status": "ok",
    }

    # Step 1: Prometheus metrics
    try:
        from ..pulse import capture_pulse
        pulse = capture_pulse()
        results["steps"].append({"name": "pulse", "status": "ok", "data": pulse})
    except Exception as e:
        results["steps"].append({"name": "pulse", "status": "skipped", "reason": str(e)})

    # Step 2: Audit check
    try:
        from ..audit_report import generate_audit_summary
        audit = generate_audit_summary()
        results["steps"].append({"name": "audit", "status": "ok"})
    except Exception as e:
        results["steps"].append({"name": "audit", "status": "skipped", "reason": str(e)})

    # Step 3: Write engram if requested
    if write_engram:
        try:
            from ..engram_ops import write_engram as _write
            _write(
                content=f"Pulse & Polish completed: {len(results['steps'])} steps",
                tags=["pulse_and_polish", "health"],
                source="god_combo",
            )
            results["steps"].append({"name": "engram_write", "status": "ok"})
        except Exception as e:
            results["steps"].append({"name": "engram_write", "status": "skipped", "reason": str(e)})

    return results
