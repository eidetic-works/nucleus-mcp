#!/usr/bin/env python3
import sys
from pathlib import Path

# EXACT REPLICATION OF stdio_server.py LOGIC
current_path = Path(__file__).resolve()
current_dir = current_path.parent

src_p = current_path
while src_p.name != 'src' and src_p.parent != src_p:
    src_p = src_p.parent

if src_p.name == 'src':
    print(f"✅ Found src directory: {src_p}")
else:
    print("❌ Could not find src directory using traversal")
    src_p = current_dir.parent.parent

src_root = str(src_p)
print(f"Calculated src_root: {src_root}")

if src_root not in sys.path:
    sys.path.insert(0, src_root)
    print(f"Injected {src_root} into sys.path")

print(f"sys.path[0]: {sys.path[0]}")

try:
    import mcp_server_nucleus
    print(f"✅ Successfully imported mcp_server_nucleus: {mcp_server_nucleus}")
    print(f"Package path: {mcp_server_nucleus.__file__}")
except ImportError as e:
    print(f"❌ Failed to import mcp_server_nucleus: {e}")

try:
    from mcp_server_nucleus.hypervisor.locker import Locker
    print("✅ Successfully imported Locker")
except ImportError as e:
    print(f"❌ Failed to import Locker: {e}")
