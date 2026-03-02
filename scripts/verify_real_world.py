import asyncio
import json
import sys
import os
import shutil
from asyncio import subprocess

async def run_real_world_verification():
    # Path to python executable in venv
    venv_python = os.path.abspath(".venv/bin/python")
    
    # Check for npx
    npx_path = shutil.which("npx")
    if not npx_path:
        print("❌ 'npx' not found. Cannot verify Node.js based MCP servers.")
        return

    # We must run as module to support relative imports
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath("src")
    
    print(f"Launching Server Module: {venv_python} -m mcp_server_nucleus.runtime.stdio_server")
    
    process = await asyncio.create_subprocess_exec(
        venv_python, "-m", "mcp_server_nucleus.runtime.stdio_server",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        env=env
    )
    
    async def send_request(method, params=None, req_id=1):
        req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": req_id}
        line = json.dumps(req) + "\n"
        process.stdin.write(line.encode())
        await process.stdin.drain()
        
        while True:
            resp_line = await process.stdout.readline()
            if not resp_line:
                break
            try:
                resp = json.loads(resp_line.decode())
                return resp
            except json.JSONDecodeError:
                print(f"Ignored non-JSON: {resp_line}")
                continue

    try:
        # 1. Initialize
        print("\n--- Sending Initialize ---")
        await send_request("initialize", req_id=1)
        
        # 2. Mount Filesystem Server (Node.js)
        # Usage: npx -y @modelcontextprotocol/server-filesystem [path]
        print("\n--- Mounting Filesystem Server (npx) ---")
        test_dir = os.path.abspath("test_fs_mount")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "hello.txt"), "w") as f:
            f.write("Hello from Nucleus FS Mount!")
            
        mount_args = {
            "mount_id": "fs_server",
            "transport": "stdio",
            "command": npx_path,
            "args": ["-y", "@modelcontextprotocol/server-filesystem", test_dir],
            "env": os.environ.copy() # Inherit likely needed for node
        }
        resp = await send_request("tools/call", {
            "name": "brain_mount_server",
            "arguments": mount_args
        }, req_id=2)
        print(f"Mount Result: {json.dumps(resp, indent=2)}")
        
        if resp.get("error"):
            print("❌ Failed to mount filesystem server")
        else:
            print("✅ Filesystem server mounted")
            
            # List tools to confirm aggregation
            print("\n--- Listing Tools (expecting fs_server:read_file) ---")
            resp = await send_request("tools/list", req_id=3)
            tools = resp["result"]["tools"]
            tool_names = [t["name"] for t in tools]
            if "fs_server:read_file" in tool_names:
                print("✅ Found 'fs_server:read_file'")
                
                # Try reading a file
                print("\n--- Reading File via Mounted Server ---")
                resp = await send_request("tools/call", {
                    "name": "fs_server:read_file",
                    "arguments": {"path": os.path.join(test_dir, "hello.txt")}
                }, req_id=4)
                print(f"Read Result: {json.dumps(resp, indent=2)}")
                content = resp["result"]["content"][0]["text"]
                if "Hello from Nucleus FS Mount!" in content:
                     print("✅ File content verified!")
                else:
                     print("❌ File content mismatch")

            else:
                print(f"❌ 'fs_server:read_file' NOT found. Tools: {tool_names}")

        # 3. Mount Memory Server (npx)
        # Usage: npx -y @modelcontextprotocol/server-memory
        print("\n--- Mounting Memory Server (npx) ---")
        mount_args_mem = {
            "mount_id": "mem_server",
            "transport": "stdio",
            "command": npx_path,
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": os.environ.copy()
        }
        resp = await send_request("tools/call", {
            "name": "brain_mount_server",
            "arguments": mount_args_mem
        }, req_id=5)
        
        if not resp.get("error"):
             print("✅ Memory server mounted")
             # Verify tools
             resp = await send_request("tools/list", req_id=6)
             tools = resp["result"]["tools"]
             if any(t["name"].startswith("mem_server:") for t in tools):
                 print(f"✅ Found Memory tools: {[t['name'] for t in tools if t['name'].startswith('mem_server:')]}")
        else:
             print(f"❌ Failed to mount memory server: {resp}")

        # 4. Recursive Self-Mounting (Nucleus mounting Nucleus)
        # This proves we can nest servers.
        print("\n--- Recursive Self-Mounting (Nucleus -> Nucleus) ---")
        venv_python = os.path.abspath(".venv/bin/python")
        
        # We need to run the sub-server as a module too
        mount_args_sub = {
            "mount_id": "sub_nucleus",
            "transport": "stdio",
            "command": venv_python,
            "args": ["-m", "mcp_server_nucleus.runtime.stdio_server"],
            "env": env  # Pass the same PYTHONPATH
        }
        
        resp = await send_request("tools/call", {
            "name": "brain_mount_server",
            "arguments": mount_args_sub
        }, req_id=7)
        
        if not resp.get("error"):
             print("✅ Sub-Nucleus mounted")
             
             # List tools - should see 'sub_nucleus:brain_health' etc.
             resp = await send_request("tools/list", req_id=8)
             tools = resp["result"]["tools"]
             sub_tools = [t["name"] for t in tools if t["name"].startswith("sub_nucleus:")]
             
             if "sub_nucleus:brain_health" in sub_tools:
                 print(f"✅ Found Sub-Nucleus tools: {len(sub_tools)} tools detected")
                 
                 # Call a tool on the sub-server
                 print("\n--- Calling Tool on Sub-Nucleus ---")
                 resp = await send_request("tools/call", {
                     "name": "sub_nucleus:brain_health",
                     "arguments": {}
                 }, req_id=9)
                 print(f"Sub-Nucleus Health: {json.dumps(resp, indent=2)}")
                 if not resp.get("result", {}).get("isError"):
                     print("✅ Recursive tool call successful!")
                 else:
                     print("❌ Recursive tool call failed")
             else:
                 print(f"❌ 'sub_nucleus:brain_health' NOT found. Tools: {sub_tools}")
        else:
             print(f"❌ Failed to mount sub-nucleus: {resp}")

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback; traceback.print_exc()
    finally:
        process.terminate()
        await process.wait()
        if os.path.exists("test_fs_mount"):
            shutil.rmtree("test_fs_mount")

if __name__ == "__main__":
    asyncio.run(run_real_world_verification())
