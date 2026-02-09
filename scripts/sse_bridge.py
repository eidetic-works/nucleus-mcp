
import json
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.stdio_server import StdioServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nucleus.sse_bridge")

class MCPBridgeHandler(BaseHTTPRequestHandler):
    """
    Simple SSE Bridge for Model Context Protocol.
    Converts HTTP POST requests from clients like ChatGPT to JSON-RPC tool calls.
    """
    
    server_impl = StdioServer(os.getcwd())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/sse':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            logger.info("New SSE connection established")
            # In a real implementation, we would keep this open and push events
            # For a tool-only bridge, ChatGPT usually just needs the initial setup
            try:
                # Send endpoint event
                endpoint_msg = json.dumps({"type": "endpoint", "url": "/post"})
                self.wfile.write(f"event: endpoint\ndata: {endpoint_msg}\n\n".encode())
                self.wfile.flush()
            except Exception as e:
                logger.error(f"SSE Error: {e}")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/post' or self.path == '/sse':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                request = json.loads(post_data)
                logger.info(f"Request: {request.get('method')}")
                
                response = self.server_impl.handle_request(request)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                logger.error(f"POST Error: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def run(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, MCPBridgeHandler)
    logger.info(f"🚀 Nucleus SSE Bridge running on http://localhost:{port}/sse")
    logger.info("Connect from ChatGPT: Settings -> Apps -> Advanced -> Developer Mode")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
