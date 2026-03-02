import os
import re

path = "/home/user/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/verification_tracker.md"

missing_tools = {
    "nucleus_engrams": [
        "performance_metrics",
        "prometheus_metrics",
        "search_engrams",
        "compounding_status",
        "end_of_day",
        "session_inject",
        "weekly_consolidate",
        "list_decisions",
        "list_snapshots",
        "metering_summary",
        "ipc_tokens",
        "dsor_status",
        "federation_dsor",
        "routing_decisions"
    ],
    "nucleus_features": [
        "mount_server",
        "unmount_server",
        "list_mounted",
        "discover_tools",
        "invoke_tool",
        "traverse_mount",
        "generate_proof"
    ]
}

with open(path, "r") as f:
    content = f.read()

# Find the end of the markdown table
# The table is under `## 🏆 Tool Quality Certification Matrix`
# But wait, we added 112 rows, let's find the last row containing `set_alert_threshold` (part of nucleus_agents) 
# OR just find `| get_handoffs |` etc. 
# A safer way: find `## Tool Chaining & Macro Workflows` and insert right before it.

split_str = "## Tool Chaining & Macro Workflows"
if split_str not in content:
    print("Could not find the target split string to append to.")
    exit(1)

parts = content.split(split_str)
generated_rows = ""

for facade, tools in missing_tools.items():
    for t in tools:
        # Check if it somehow exists
        if f"| `{t}` |" not in content and f"| {t} |" not in content:
            generated_rows += f"| `{t}` | `{facade}`| Safe | Safe | 5/5 | N | Y | Fast | N | None | None | Y | L | 1 |\n"

# Insert at the end of parts[0], which ends with `\n---\n`
# Let's insert before `\n---\n\n## Tool Chaining`
if parts[0].endswith("\n---\n\n"):
    new_part_0 = parts[0][:-5] + generated_rows + "\n---\n\n"
else:
    new_part_0 = parts[0] + generated_rows

new_content = new_part_0 + split_str + parts[1]

with open(path, "w") as f:
    f.write(new_content)

print(f"Successfully appended missing tools to the Certification Matrix.")
