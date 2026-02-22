import sys
import os
from pathlib import Path
sys.path.insert(0, "/Users/lokeshgarg/ai-mvp-backend/mcp-server-nucleus/src")
os.environ["NUCLEAR_BRAIN_PATH"] = str(Path.cwd() / ".brain")
from mcp_server_nucleus.runtime.session_ops import _brain_session_start_impl
print(_brain_session_start_impl())
