import os

path = "/Users/lokeshgarg/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/manual_testing_playbook.md"

tools = [
    "identify_agent", "sync_status", "sync_now", "sync_auto", "sync_resolve", 
    "read_artifact", "write_artifact", "list_artifacts", "trigger_agent", 
    "get_triggers", "evaluate_triggers", "start_deploy_poll", "check_deploy", 
    "complete_deploy", "smoke_test"
]

content = "\n## Facade: `nucleus_sync`\n\n"
for t in tools:
    content += f"### Action: `{t}`\n- [ ] **Status:** PENDING\n\n"

with open(path, "a") as f:
    f.write(content)

print(f"Appended {len(tools)} tools to playbook.")
