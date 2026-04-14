"""
Nucleus HTTP Cloud Entrypoint — nucleus-mcp-cloud
===================================================
Importable entrypoint for the Cloud Run / container ASGI app.
This module re-exports `serve()` from src/app.py in an
installable-package-compatible way.

Usage:
  nucleus-mcp-cloud              # starts on PORT (default 8080)
  CMD=http in Docker             # via deploy/entrypoint.sh
"""

import os
import sys


def serve():
    """
    Start the Cloud Run compatible HTTP server.
    Delegates to src/app.py::serve() with the correct sys.path.
    """
    import sys
    from pathlib import Path

    # Ensure src/ is on path so app.py is importable
    src = Path(__file__).parent.parent.parent
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    import app as cloud_app
    cloud_app.serve()


if __name__ == "__main__":
    serve()
