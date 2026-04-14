"""
nucleus-mcp-cloud entrypoint
==============================
Thin shim so pyproject.toml scripts can point at a stable importable path.
All logic lives in app.py (same package).
"""

from mcp_server_nucleus.http_transport.app import serve, app

__all__ = ["serve", "app"]

if __name__ == "__main__":
    serve()
