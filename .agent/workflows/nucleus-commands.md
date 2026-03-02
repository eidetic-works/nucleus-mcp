# Nucleus Command Protocol

> **ALWAYS consult this before suggesting Nucleus commands to the user.**

---

## ⚠️ CRITICAL: Safe Init vs Destructive Init

| Scenario | Command | Risk |
|:---------|:--------|:-----|
| Fresh project (no `.brain/`) | `nucleus-init` | ✅ Safe |
| Existing `.brain/` | **DO NOT use `nucleus-init`** | 🚨 Data loss! |
| Upgrade existing brain | Manual file addition (see below) | ✅ Safe |

---

## Upgrade Sequence (Existing Brain)

When user has an existing `.brain/` and needs new features:

```bash
# 1. Check what exists
ls -la .brain/ledger/

# 2. If tasks.json is missing, create it manually
cat > .brain/ledger/tasks.json << 'EOF'
[
  {
    "id": "upgrade-1",
    "description": "Brain upgraded to v0.3.1 - try 'Show me all tasks'",
    "status": "READY",
    "priority": 1,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": null,
    "source": "manual-upgrade",
    "escalation_reason": null,
    "created_at": "2026-01-04T00:00:00+0000",
    "updated_at": "2026-01-04T00:00:00+0000"
  }
]
EOF

# 3. Restart Claude Desktop
# Cmd+Q → Reopen
```

---

## Install/Upgrade Sequence

```bash
# Always use python3.11 (macOS default python3 is too old)
python3.11 -m pip install --upgrade mcp-server-nucleus

# Verify version
python3.11 -c "import mcp_server_nucleus; print('OK')"
```

---

## Commands That DO NOT EXIST

- ❌ `nucleus status` — Does not exist (mockup only)
- ❌ `nucleus upgrade` — Does not exist
- ❌ `pip install` — Use `python3.11 -m pip` instead

---

## 🔍 Debugging "Empty Tasks"

If user says "Tasks are empty" but files exist locally:

1. **Check Config Pointer immediately:**
   ```python
   # Run this to see where Claude is actually looking
   python3.11 -c "import json, os; print(json.load(open(os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json')))['mcpServers']['nucleus']['env']['NUCLEAR_BRAIN_PATH'])"
   ```
2. **Compare with CWD:**
   If config path != Current Working Directory + `/.brain`, that's the bug.
3. **Fix:**
   Update config JSON to match CWD.

---

## Commands That DO EXIST

- ✅ `nucleus-init` — Initialize new brain (DESTRUCTIVE if brain exists)
- ✅ `nucleus-init --template=solo` — Minimal template
- ✅ `nucleus-init --help` — Show help

---

## README-Worthy Content

The following should be added to the public README:

```markdown
### Upgrading an Existing Brain

If you have an existing `.brain/` directory and want to add V2 task support:

1. **Don't run `nucleus-init`** — it will overwrite your data
2. Manually create `.brain/ledger/tasks.json` with an empty array: `echo "[]" > .brain/ledger/tasks.json`
3. Restart your AI client
```
