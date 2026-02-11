
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Nucleus MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio fallback mode")
    parser.add_argument("--workspace", type=str, default=os.getcwd(), help="Workspace root")
    args = parser.parse_args()

    # Check for FastMCP
    fastmcp_available = False
    try:
        from fastmcp import FastMCP  # noqa: F401
        fastmcp_available = True
    except ImportError:
        pass

    if args.stdio or not fastmcp_available:
        # Launch Stdio Fallback Server
        from .runtime.stdio_server import run
        run()
    else:
        # Launch FastMCP Server
        from . import mcp
        mcp.run()

if __name__ == "__main__":
    main()
