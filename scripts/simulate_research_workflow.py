import asyncio
import json
import sys
import os
import shutil
from asyncio import subprocess

async def run_simulation():
    # Path to python executable in venv
    venv_python = os.path.abspath(".venv/bin/python")
    
    # Check for npx
    npx_path = shutil.which("npx")
    if not npx_path:
        print("❌ 'npx' not found. Cannot verify Node.js based MCP servers.")
        return

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath("src")
    
    print(f"🚀 Launching Nucleus for Research Simulation...")
    
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
        await send_request("initialize", req_id=1)
        
        # 2. Setup Data
        test_dir = os.path.abspath("simulation_data")
        os.makedirs(test_dir, exist_ok=True)
        data_file = os.path.join(test_dir, "project_notes.txt")
        with open(data_file, "w") as f:
            f.write("Project: Apollo\nStatus: Active\nLead: Sarah Connor\nPriority: High")
            
        print("\n--- Phase 1: Mounting Tools ---")
        
        # Mount Filesystem
        print("Mounting Filesystem...")
        await send_request("tools/call", {
            "name": "brain_mount_server",
            "arguments": {
                "mount_id": "fs",
                "transport": "stdio",
                "command": npx_path,
                "args": ["-y", "@modelcontextprotocol/server-filesystem", test_dir],
                "env": os.environ.copy()
            }
        }, req_id=2)

        # Mount Memory
        print("Mounting Memory...")
        await send_request("tools/call", {
            "name": "brain_mount_server",
            "arguments": {
                "mount_id": "mem",
                "transport": "stdio",
                "command": npx_path,
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": os.environ.copy()
            }
        }, req_id=3)
        
        print("✅ Tools Mounted.")

        print("\n--- Phase 2: Execution (The 'Research' Loop) ---")
        
        # Step A: Read File
        print("1. Agent reads file from Filesystem...")
        resp = await send_request("tools/call", {
            "name": "fs:read_file",
            "arguments": {"path": data_file}
        }, req_id=4)
        
        content = resp["result"]["content"][0]["text"]
        print(f"   > Content Read: {content.replace(chr(10), ' | ')}")
        
        # Step B: "Think" (Simulated extraction)
        print("2. Agent extracts entities (Simulation)...")
        entities = []
        for line in content.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                entities.append({"name": k.strip(), "kind": "Attribute", "observation": v.strip()})
        print(f"   > Extracted {len(entities)} entities.")

        # Step C: Store in Memory
        print("3. Agent stores knowledge in Memory API...")
        # Create entities
        resp = await send_request("tools/call", {
            "name": "mem:create_entities",
            "arguments": {"entities": [{"name": "Apollo Project", "entityType": "Project", "observations": ["Initial creation"]}]}
        }, req_id=5)
        print(f"   > Create Entity Response: {json.dumps(resp, indent=2)}")
        if resp.get("result", {}).get("isError"):
             print("❌ Entity Creation Failed")
             return
        
        # Add observations
        observations = [{"entityName": "Apollo Project", "contents": [e["name"] + ": " + e["observation"]]} for e in entities]
        resp = await send_request("tools/call", {
            "name": "mem:add_observations",
            "arguments": {"observations": observations}
        }, req_id=6)
        
        if not resp.get("result", {}).get("isError"):
            print("✅ Knowledge Stored in Memory Graph.")
        else:
            print(f"❌ Storage Failed: {resp}")

        print("\n--- Phase 3: Verification (Querying Memory) ---")
        resp = await send_request("tools/call", {
            "name": "mem:read_graph",
            "arguments": {}
        }, req_id=7)
        
        graph = resp["result"]["content"][0]["text"]
        # print("Graph Snapshot:", graph[:200] + "...")
        if "Apollo Project" in graph:
             print("✅ Confirmed: 'Apollo Project' exists in Knowledge Graph.")
        else:
             print("❌ Failed to find entity in graph.")

    except Exception as e:
        print(f"\nSIMULATION FAILED: {e}")
        import traceback; traceback.print_exc()
    finally:
        process.terminate()
        await process.wait()
        if os.path.exists("simulation_data"):
            shutil.rmtree("simulation_data")

if __name__ == "__main__":
    asyncio.run(run_simulation())
