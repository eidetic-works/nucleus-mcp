"""GROUND — Execution verification that goes outside the formal system.

Dr. Mann = Gödel. The system can't verify itself from within.
GROUND goes outside — execution, reality, the tesseract.
That's not a feature. That's killing Mann.

Super-Tools Facade: verify + receipt actions via nucleus_ground(action, params).
"""

import json
from pathlib import Path

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_ground facade tool with the MCP server."""
    from ..runtime.ground import run_ground

    def _verify(project_root=None, python_path=None, tiers=None,
                timeout_s=30, pre_head=None):
        """Run GROUND verification on current git changes."""
        tier_list = None
        if tiers is not None:
            if isinstance(tiers, str):
                tier_list = [int(t.strip()) for t in tiers.split(",")]
            elif isinstance(tiers, list):
                tier_list = [int(t) for t in tiers]

        # run_ground() now handles receipt logging + event emission in runtime layer
        receipt = run_ground(
            project_root=project_root,
            python_path=python_path,
            tiers=tier_list,
            timeout_s=int(timeout_s),
            pre_head=pre_head,
        )

        return json.dumps(receipt, indent=2, default=str)

    def _receipt():
        """Get last GROUND verification receipt."""
        log_path = _get_log_path()
        if not log_path.exists():
            return json.dumps({"error": "No verification log found", "path": str(log_path)})

        # Read last line
        lines = log_path.read_text().strip().splitlines()
        if not lines:
            return json.dumps({"error": "Verification log is empty"})

        try:
            last = json.loads(lines[-1])
            return json.dumps(last, indent=2, default=str)
        except json.JSONDecodeError:
            return json.dumps({"error": "Could not parse last log entry"})

    def _get_log_path():
        """Find verification log via brain path (not CWD)."""
        from ..runtime.common import get_brain_path
        brain = get_brain_path()
        return brain / "verification_log.jsonl"

    def _hook(files=None, project_root=None, tiers=None):
        """Post-edit verification: run Tiers 1-2 on specific files.

        Designed for Claude Code hook integration — fast pass/fail on
        just the files that changed, not the whole git diff.
        """
        from ..runtime.execution_verifier import (
            _tier1_syntax_check, _tier2_import_check,
        )
        root = Path(project_root) if project_root else Path.cwd()
        file_list = files if isinstance(files, list) else []

        tier_list = [1, 2]
        if tiers is not None:
            if isinstance(tiers, str):
                tier_list = [int(t.strip()) for t in tiers.split(",")]
            elif isinstance(tiers, list):
                tier_list = [int(t) for t in tiers]

        signals = []
        if 1 in tier_list:
            signals.extend(_tier1_syntax_check(file_list, root, 10))
        if 2 in tier_list:
            py_files = [f for f in file_list if f.endswith(".py")]
            signals.extend(_tier2_import_check(py_files, root, 10))

        passed = all(s.get("passed", True) for s in signals)
        result = {
            "verified": passed,
            "signals": signals,
            "files_checked": file_list,
        }
        return json.dumps(result, indent=2, default=str)

    ROUTER = {
        "verify": lambda project_root=None, python_path=None, tiers=None,
                        timeout_s=30, pre_head=None: _verify(
            project_root, python_path, tiers, timeout_s, pre_head),
        "receipt": lambda: _receipt(),
        "hook": lambda files=None, project_root=None, tiers=None: _hook(
            files, project_root, tiers),
    }

    @mcp.tool()
    def nucleus_ground(action: str, params: dict = None) -> str:
        """GROUND — Execution verification. Goes outside the formal system.

Actions:
  verify   - Run tiered verification on current git changes. params: {project_root?, python_path?, tiers?, timeout_s?, pre_head?}
  receipt  - Get last verification receipt.
  hook     - Post-edit verification on specific files (for Claude Code hooks). params: {files: [paths], project_root?, tiers?}

Tiers:
  0 — Diff non-empty (did anything change?)
  1 — Syntax valid (py_compile, node --check, bash -n)
  2 — Imports work (python -c "import module")
  3 — Tests pass (pytest on related test files)
  4 — Runtime (start server, hit endpoints, verify responses)
"""
        params = params or {}
        return dispatch(action, params, ROUTER, "nucleus_ground")

    return [("nucleus_ground", nucleus_ground)]
