"""DualEngineLLM smoke test — confirms RESEARCH-tier inference round-trips.

Paths and env vars resolve through ``mcp_server_nucleus.paths`` so the
diagnostic is portable. ``NUCLEUS_BRAIN`` wins if set; otherwise it's derived
from ``NUCLEUS_ROOT`` (non-strict fallback = invoking user's home).

Usage: ``python -m mcp_server_nucleus.diagnostics.core``
"""

from __future__ import annotations

import logging
import os
import sys
import traceback

from mcp_server_nucleus.paths import brain_path


def main() -> int:
    if "NUCLEUS_BRAIN_PATH" not in os.environ:
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain_path())
    os.environ.setdefault("FORCE_VERTEX", "0")

    logging.basicConfig(level=logging.INFO)

    try:
        from mcp_server_nucleus.runtime.llm_client import DualEngineLLM
    except ImportError as e:
        print(f"FAIL import DualEngineLLM: {e}", file=sys.stderr)
        return 1

    try:
        print("Testing DualEngineLLM (RESEARCH tier)...")
        model = DualEngineLLM(job_type="RESEARCH")
        print(f"engine={model.engine} tier={model.tier} model={model.model_name}")

        print("Calling generate_content...")
        response = model.generate_content(
            "Hello, this is a diagnostic test. Please respond with 'OK'."
        )
        if response:
            print(f"OK: {response.text}")
            return 0
        print("FAIL: inference returned None", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
