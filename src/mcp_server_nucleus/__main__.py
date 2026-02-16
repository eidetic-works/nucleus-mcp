"""Entry point for running mcp-server-nucleus as a module."""
try:
    from mcp_server_nucleus import main
except ImportError:
    # Fallback for Python 3.9 / No FastMCP
    from mcp_server_nucleus.runtime.stdio_server import main

if __name__ == "__main__":
    main()
