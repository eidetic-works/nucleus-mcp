import os
import uvicorn
from starlette.applications import Starlette
from mcp_server_nucleus.http_transport.relay_route import relay_route

app = Starlette(routes=[relay_route])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
