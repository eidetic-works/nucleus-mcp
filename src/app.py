"""
src/app.py — backwards-compat shim for Docker / direct python src/app.py usage.
All logic has moved to mcp_server_nucleus.http_transport.app (installed package).
"""
import sys
from pathlib import Path

# Ensure the package is importable when run as `python src/app.py`
_src = Path(__file__).parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mcp_server_nucleus.http_transport.app import app, serve  # noqa: F401

if __name__ == "__main__":
    serve()
