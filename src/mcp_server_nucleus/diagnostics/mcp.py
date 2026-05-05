"""MCP server import + tool-registration diagnostic.

Verifies that ``mcp_server_nucleus`` imports cleanly, exposes an ``mcp``
object, and that a known-required tool pair is registered. Uses a demo
workspace for live tool invocation — path resolves through env:

- ``NUCLEUS_DEMO_ROOT`` wins.
- Fallback: ``<NUCLEUS_ROOT>/output/demos`` via ``paths.nucleus_root``.

Usage: ``python -m mcp_server_nucleus.diagnostics.mcp``
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from mcp_server_nucleus.paths import nucleus_root


def _demo_root() -> Path:
    env = os.environ.get("NUCLEUS_DEMO_ROOT")
    if env:
        return Path(env)
    return nucleus_root() / "output" / "demos"


def main() -> int:
    demo = _demo_root()
    if "NUCLEUS_BRAIN_PATH" not in os.environ:
        os.environ["NUCLEUS_BRAIN_PATH"] = str(demo / ".brain")

    print("Nucleus MCP Server Diagnostic")
    print("=" * 50)

    print("\n[1/4] module import...")
    try:
        import mcp_server_nucleus
        print(f"OK: imported v{mcp_server_nucleus.__version__}")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    print("\n[2/4] mcp object...")
    try:
        from mcp_server_nucleus import mcp
        print(f"OK: {type(mcp).__name__}")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("\n[3/4] tool registration...")
    target_tools = ("nucleus_list_directory", "nucleus_delete_file")
    try:
        if hasattr(mcp, "_tools"):
            tools = mcp._tools
            print(f"found {len(tools)} registered tools")
            for name in target_tools:
                status = "OK" if name in tools else "MISSING"
                print(f"  {status}: {name}")
        else:
            print("(FastMCP: direct import fallback)")
            from mcp_server_nucleus import nucleus_delete_file, nucleus_list_directory
            _ = (nucleus_delete_file, nucleus_list_directory)
            print("OK: functions importable")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)

    print("\n[4/4] live tool calls...")
    try:
        from mcp_server_nucleus import nucleus_delete_file, nucleus_list_directory

        result = nucleus_list_directory(str(demo))
        print(f"nucleus_list_directory({demo}):")
        print(result)

        env_file = demo / ".env"
        result = nucleus_delete_file(str(env_file))
        print(f"\nnucleus_delete_file({env_file}) — expect block:")
        print(result)
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    print("\n" + "=" * 50)
    print("Diagnosis complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
