import asyncio
import json
import sys
import os
from asyncio import subprocess

async def run_verification():
    # Path to python executable in venv
    venv_python = os.path.abspath(".venv/bin/python")
    
    mock_server_script = os.path.abspath("scripts/mock_mcp_server.py")
    
    # We must run as module to support relative imports
    # Set PYTHONPATH to include 'src'
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath("src")
    env["NUCLEAR_BRAIN_PATH"] = os.path.abspath("test_brain_verify")
    
    # Clean up previous test brain
    if os.path.exists("test_brain_verify"):
        import shutil
        shutil.rmtree("test_brain_verify")
    os.makedirs("test_brain_verify", exist_ok=True)
    
    print(f"Launching Server Module: {venv_python} -m mcp_server_nucleus.runtime.stdio_server")
    
    # Launch stdio_server.py as module
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
        
        # Read response
        while True:
            resp_line = await process.stdout.readline()
            if not resp_line:
                break
            try:
                resp = json.loads(resp_line.decode())
                return resp
            except json.JSONDecodeError:
                # Might be a debug log printed to stdout by accident (though we configured stderr)
                print(f"Ignored non-JSON: {resp_line}")
                continue

    try:
        # 1. Initialize
        print("\n--- Sending Initialize ---")
        resp = await send_request("initialize", req_id=1)
        print(json.dumps(resp, indent=2))
        assert resp["result"]["serverInfo"]["name"] == "nucleus-mcp"
        
        # 2. Mount Mock Server
        print("\n--- Mounting Mock Server ---")
        mount_args = {
            "mount_id": "mock1",
            "transport": "stdio",
            "command": venv_python,
            "args": [mock_server_script],
            "env": {"TEST_ENV": "1"}
        }
        resp = await send_request("tools/call", {
            "name": "brain_mount_server",
            "arguments": mount_args
        }, req_id=2)
        print(json.dumps(resp, indent=2))
        assert not resp["result"]["isError"]

        # 3. List Tools (Should see 'mock1:echo')
        print("\n--- Listing Tools ---")
        resp = await send_request("tools/list", req_id=3)
        # print(json.dumps(resp, indent=2))
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        print(f"Tools found: {tool_names}")
        assert "brain_mount_server" in tool_names
        assert "mock1:echo" in tool_names
        
        # 4. Call Mock Tool
        print("\n--- Calling mock1:echo ---")
        resp = await send_request("tools/call", {
            "name": "mock1:echo",
            "arguments": {"message": "Hello Nucleus!"}
        }, req_id=4)
        print(json.dumps(resp, indent=2))
        assert "Hello Nucleus!" in resp["result"]["content"][0]["text"]

        # 5. Traverse
        print("\n--- Traversing mock1 ---")
        resp = await send_request("tools/call", {
            "name": "brain_traverse_and_mount",
            "arguments": {"root_mount_id": "mock1"}
        }, req_id=5)
        print(json.dumps(resp, indent=2))
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "mock_mount" in content["potential_sub_servers"]

        print("\nALL TESTS PASSED!")

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback; traceback.print_exc()
    finally:
        process.terminate()
        await process.wait()

if __name__ == "__main__":
    asyncio.run(run_verification())
