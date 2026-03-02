import os
import ast
import re

TOOLS_DIR = "/path/to/your/project/mcp-server-nucleus/src/mcp_server_nucleus/tools"
TRACKER_PATH = "/home/user/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/verification_tracker.md"
PLAYBOOK_PATH = "/home/user/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/manual_testing_playbook.md"

def extract_tools_from_python():
    """Extract all tool action keys defined in ROUTER dictionaries across all modules."""
    tools = set()
    for filename in os.listdir(TOOLS_DIR):
        if not filename.endswith(".py") or filename.startswith("__"):
            continue
            
        filepath = os.path.join(TOOLS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
            except Exception as e:
                print(f"AST Error in {filename}: {e}")
                continue
            
            for node in ast.walk(tree):
                # Look for an assignment `ROUTER = { ... }` or `*_ROUTER = { ... }`
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and "ROUTER" in target.id:
                            # Extract keys from the dictionary
                            if isinstance(node.value, ast.Dict):
                                for key in node.value.keys:
                                    if isinstance(key, ast.Constant):
                                        tools.add(key.value)
    return tools

def main():
    print("--- DEEP AUDIT IN PROGRESS ---\n")
    source_tools = extract_tools_from_python()
    print(f"[AST] Found {len(source_tools)} unique action routers in source code.\n")
    
    with open(PLAYBOOK_PATH, "r") as f:
        playbook = f.read()
    
    playbook_tools = set(re.findall(r'### Action: `([^`]+)`', playbook))
    print(f"[PLAYBOOK] Found {len(playbook_tools)} actions documented in manual_testing_playbook.md.")
    
    with open(TRACKER_PATH, "r") as f:
        tracker = f.read()
        
    tracker_tools = set([t.strip() for t in re.findall(r'^\| `?([^`|]+)`? \|', tracker, re.MULTILINE)])
    tracker_tools = set([t for t in tracker_tools if t != 'Tool' and len(t) > 1])
    print(f"[TRACKER] Found {len(tracker_tools)} valid action rows in verification_tracker.md Certification Matrix.\n")

    missing_playbook = source_tools - playbook_tools
    print(f"\n--- MISSING FROM PLAYBOOK ({len(missing_playbook)}) ---")
    for t in sorted(list(missing_playbook)):
        print(f"  - {t}")
        
    missing_tracker = source_tools - tracker_tools
    print(f"\n--- MISSING FROM TRACKER ({len(missing_tracker)}) ---")
    for t in sorted(list(missing_tracker)):
        print(f"  - {t}")
        
    playbook_extra = playbook_tools - source_tools
    print(f"\n--- IN PLAYBOOK BUT NOT IN SOURCE (Ghost Actions) ({len(playbook_extra)}) ---")
    for t in sorted(list(playbook_extra)):
        print(f"  - {t}")
        
    tracker_extra = tracker_tools - source_tools
    print(f"\n--- IN TRACKER BUT NOT IN SOURCE (Ghost Actions) ({len(tracker_extra)}) ---")
    for t in sorted(list(tracker_extra)):
        print(f"  - {t}")

if __name__ == "__main__":
    main()
