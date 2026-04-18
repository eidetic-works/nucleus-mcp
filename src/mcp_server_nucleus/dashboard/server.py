"""
Nucleus Sovereign Agent OS — Governance Dashboard Server
=========================================================
A lightweight HTTP server exposing the Nucleus runtime modules
(sovereign_status, compliance_config, trace_viewer, kyc_demo)
as JSON API endpoints, plus serving a single-page dashboard UI.

Zero external dependencies. Uses only Python stdlib http.server.
"""

import os
import json
import socket
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class GovernanceDashboardHandler(SimpleHTTPRequestHandler):
    """
    Handles both static file serving (the dashboard SPA)
    and JSON API routes for Nucleus runtime data.
    """

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "static"
            )
        super().__init__(*args, directory=directory, **kwargs)

    # Suppress the default access log spam
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api_get(parsed)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/kyc/demo":
            self._handle_kyc_post(parsed)
        else:
            self._send_json(404, {"error": "Not found"})

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ------------------------------------------------------------------
    # API routing
    # ------------------------------------------------------------------

    def _handle_api_get(self, parsed):
        brain = Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain"))

        try:
            if parsed.path == "/api/sovereign":
                from mcp_server_nucleus.runtime.sovereign_status import (
                    generate_sovereign_status,
                )
                self._send_json(200, generate_sovereign_status(brain))

            elif parsed.path == "/api/compliance":
                from mcp_server_nucleus.runtime.compliance_config import (
                    generate_compliance_report,
                )
                self._send_json(200, generate_compliance_report(brain))

            elif parsed.path == "/api/traces":
                from mcp_server_nucleus.runtime.trace_viewer import list_traces
                self._send_json(200, list_traces(brain))

            elif parsed.path.startswith("/api/traces/"):
                from mcp_server_nucleus.runtime.trace_viewer import get_trace
                trace_id = parsed.path.split("/")[-1]
                result = get_trace(brain, trace_id)
                code = 404 if "error" in result else 200
                self._send_json(code, result)

            elif parsed.path == "/api/health":
                self._send_json(200, {
                    "status": "ok",
                    "brain_path": str(brain),
                    "brain_exists": brain.exists(),
                })

            else:
                self._send_json(404, {"error": "Unknown API endpoint"})

        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _handle_kyc_post(self, parsed):
        brain = Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain"))
        qs = parse_qs(parsed.query)
        app_id = qs.get("id", ["APP-001"])[0]

        try:
            from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
            review = run_kyc_review(app_id, brain, write_dsor=True)
            self._send_json(200, review)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send_json(self, status_code, data):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ReusableTCPServer(HTTPServer):
    """HTTPServer subclass with SO_REUSEADDR to avoid 'Address already in use'."""

    allow_reuse_address = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


def run_dashboard_server(port=8080, brain_path=None):
    """Boot the dashboard on the given port."""
    if brain_path:
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain_path)

    static_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "static"
    )
    os.makedirs(static_dir, exist_ok=True)

    print()
    print("=" * 60)
    print("🛡️  Nucleus Sovereign Agent OS — Compliance Dashboard")
    print("=" * 60)
    print(f"  Port     : {port}")
    print(f"  URL      : http://localhost:{port}")
    print(f"  Brain    : {os.environ.get('NUCLEUS_BRAIN_PATH', '(auto)')}")
    print("=" * 60)
    print("  Press Ctrl+C to stop.\n")

    httpd = ReusableTCPServer(("0.0.0.0", port), GovernanceDashboardHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped.")
        httpd.server_close()
