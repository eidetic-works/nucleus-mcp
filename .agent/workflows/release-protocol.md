---
description: Pre-release checklist for Nucleus MCP Server
---

# Nucleus Release Protocol

> ⚠️ **DO NOT SKIP ANY STEP.** The v0.3.1 incident happened because Layer 2 was skipped.

## Layer 1: Pre-Flight

```bash
# 1. Ensure clean state
git status  # Must show "nothing to commit"

# 2. Check version is bumped
grep "version" pyproject.toml
cat CHANGELOG.md | head -20
```

- [ ] Version in `pyproject.toml` is incremented
- [ ] CHANGELOG.md has entry for this version
- [ ] All new dependencies added to `pyproject.toml`

---

## Layer 2: The Build (MANDATORY)

```bash
# 3. Run ALL tests
// turbo
python3.11 -m pytest tests/ -v

# 4. Fresh install simulation
python3.11 -m venv /tmp/nucleus-test-venv
source /tmp/nucleus-test-venv/bin/activate
pip install -e .

# 5. Manual E2E test
nucleus-init /tmp/test-brain
cat /tmp/test-brain/ledger/tasks.json  # Verify seed tasks exist

# 6. Cleanup
deactivate
rm -rf /tmp/nucleus-test-venv /tmp/test-brain
```

- [ ] All tests pass
- [ ] Fresh install works
- [ ] E2E verification complete

---

## Layer 3: Launch

```bash
# 7. Build
python3.11 -m build

# 8. Upload (requires token)
python3.11 -m twine upload dist/mcp_server_nucleus-X.Y.Z*

# 9. Verify from PyPI (not local!)
pip install --upgrade mcp-server-nucleus
python3.11 -c "import mcp_server_nucleus; print('OK')"
```

- [ ] Package built successfully
- [ ] Uploaded to PyPI
- [ ] Verified installation from PyPI works

---

## Rollback Plan

If something goes wrong after release:

```bash
# Publish a patch version immediately
# Example: 0.3.2 broke? Release 0.3.3 with the fix.

# Users can pin to previous working version:
pip install mcp-server-nucleus==0.3.1
```
