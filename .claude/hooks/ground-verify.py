#!/usr/bin/env python3
"""Claude Code hook: run GROUND Tier 1-2 on every edited file.

Nucleus guarding its own development. If this hook catches nothing,
the product isn't doing its job.
"""
import json
import sys
import os
import logging
import io
logging.disable(logging.CRITICAL)
os.environ["NUCLEUS_QUIET"] = "1"
# Suppress Nucleus init noise (prints to stderr)
_real_stderr = sys.stderr
sys.stderr = io.StringIO()

def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # no input = nothing to check

    file_path = input_data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Only check Python files (our codebase)
    if not file_path.endswith(".py"):
        sys.exit(0)

    # Skip test files from blocking (warn only)
    is_test = "/tests/" in file_path or file_path.endswith("_test.py")

    # Point to our project
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    venv_python = os.path.join(project_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    # Add src to path so we can import runtime
    src = os.path.join(project_root, "src")
    sys.path.insert(0, src)

    # Set brain path
    brain_path = os.path.join(os.path.dirname(project_root), ".brain")
    os.environ["NUCLEUS_BRAIN_PATH"] = brain_path
    os.environ["NUCLEAR_BRAIN_PATH"] = brain_path

    try:
        from mcp_server_nucleus.runtime.execution_verifier import (
            _tier1_syntax_check, _tier2_import_check,
        )
        from pathlib import Path

        root = Path(project_root)
        rel_path = file_path
        try:
            rel_path = str(Path(file_path).relative_to(root))
        except ValueError:
            pass

        signals = []
        signals.extend(_tier1_syntax_check([rel_path], root, 5))
        signals.extend(_tier2_import_check([rel_path], root, 5))

        failures = [s for s in signals if not s.get("passed", True)]

        if failures:
            reasons = "; ".join(
                f"{f.get('check', '?')}: {f.get('error', f.get('message', 'failed'))}"
                for f in failures
            )
            msg = f"GROUND Tier 1-2 failed on {os.path.basename(file_path)}: {reasons}"

            # Log to event stream
            try:
                from mcp_server_nucleus.runtime.event_ops import _emit_event
                _emit_event("ground_hook_failed", "claude_code_hook", {
                    "file": rel_path,
                    "failures": failures,
                    "tier": "1-2",
                })
            except Exception:
                pass

            # Emit as context so Claude sees the failure
            print(json.dumps({"additionalContext": f"[GROUND] {msg}"}))
            sys.exit(0)  # warn, don't block — let Claude fix it
        else:
            # Silent success — record evidence
            try:
                from mcp_server_nucleus.runtime.event_ops import _emit_event
                _emit_event("ground_hook_passed", "claude_code_hook", {
                    "file": rel_path,
                    "tier": "1-2",
                    "signals_count": len(signals),
                })
            except Exception:
                pass

    except Exception as e:
        # Hook itself broke — emit context, never block
        print(json.dumps({"additionalContext": f"[GROUND] Hook error: {e}"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
