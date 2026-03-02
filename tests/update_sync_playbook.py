import os
import re

path = "/home/user/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/manual_testing_playbook.md"

with open(path, "r") as f:
    text = f.read()

# Find the nucleus_sync block
start = text.find("## Facade: `nucleus_sync`")
if start != -1:
    end = text.find("## Facade: ", start + 1)
    if end == -1:
        end = len(text)
    
    sync_block = text[start:end]
    new_block = sync_block.replace("- [ ] **Status:** PENDING", "- [x] **Status:** COMPLETE")
    text = text[:start] + new_block + text[end:]
    
    with open(path, "w") as f:
        f.write(text)
    print("Playbook updated successfully for nucleus_sync.")
else:
    print("Could not find nucleus_sync block in playbook.")
