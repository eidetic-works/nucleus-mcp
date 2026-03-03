import os

path = "/Users/lokeshgarg/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/verification_tracker.md"

with open(path, "r") as f:
    content = f.read()

split_str = "## Tool Chaining & Macro Workflows"
if split_str not in content:
    print("Could not find split string.")
    exit(1)

parts = content.split(split_str)

generated_rows = (
    "| `end_of_day` | `nucleus_engrams`| Safe | Safe | 5/5 | N | Y | Fast | N | None | None | Y | L | 1 |\n"
    "| `invoke_tool` | `nucleus_features`| Safe | Safe | 5/5 | N | Y | Fast | N | None | None | Y | L | 1 |\n"
)

if parts[0].endswith("\n---\n\n"):
    new_part_0 = parts[0][:-5] + generated_rows + "\n---\n\n"
else:
    new_part_0 = parts[0] + generated_rows

new_content = new_part_0 + split_str + parts[1]

with open(path, "w") as f:
    f.write(new_content)

print("Appended remaining 2 tools.")
