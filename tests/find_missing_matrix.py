import os
import re

tracker_path = "/Users/lokeshgarg/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/verification_tracker.md"
playbook_path = "/Users/lokeshgarg/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/manual_testing_playbook.md"

with open(tracker_path, "r") as f:
    tracker = f.read()

with open(playbook_path, "r") as f:
    playbook = f.read()

# Extract tools from playbook
playbook_tools = re.findall(r'### Action: `([^`]+)`', playbook)
print(f"Total tools in playbook: {len(playbook_tools)}")

# Extract tools from tracker table
# The table rows look like: | `tool_name` | ...
tracker_tools = re.findall(r'^\| `?([^`|]+)`? \|', tracker, re.MULTILINE)
# Remove header if matched
tracker_tools = [t.strip() for t in tracker_tools if t.strip() != 'Tool']
print(f"Total tools in tracker: {len(tracker_tools)}")

# Find missing
missing = set(playbook_tools) - set(tracker_tools)
print(f"Missing tools from tracker ({len(missing)}):")
for m in sorted(list(missing)):
    # Find which facade this belongs to in the playbook
    # Search backwards from the tool in the playbook for "## Facade: `facade_name`"
    # To do this, we can trace the playbook file
    pass

import collections
missing_by_facade = collections.defaultdict(list)

current_facade = "unknown"
for line in playbook.split('\n'):
    facade_match = re.match(r'## Facade: `([^`]+)`', line)
    if facade_match:
        current_facade = facade_match.group(1)
        
    tool_match = re.match(r'### Action: `([^`]+)`', line)
    if tool_match:
        t = tool_match.group(1)
        if t in missing:
            missing_by_facade[current_facade].append(t)

for facade, tools in missing_by_facade.items():
    print(f"\n{facade} ({len(tools)} missing):")
    for t in tools:
        print(f"  - {t}")
