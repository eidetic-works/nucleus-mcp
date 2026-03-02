---
description: Execute the established Precision Sync Protocol to safely mirror the active repository to the public release repository.
---

# Precision Source Code Sync

This workflow automates the transfer of code from the active development repository (`mcp-server-nucleus`) to the public release repository (`nucleus-mcp`) with absolute certainty that no private files, histories, ledgers, or uncommitted work leak into the public domain.

## Execution

1. Navigate to the `mcp-server-nucleus` directory where the syncing script is kept.
2. Ensure the active development repository is currently sitting on a stable branch without critical uncommitted work, as only committed work will be transferred.
3. Execute the precision sync script:
// turbo
4. Run `./scripts/sync_public_repo.sh`

## Verification

5. If successful, navigate to the `nucleus-mcp` directory and review the changes.
// turbo
6. Run `cd ../nucleus-mcp && git status`
7. Instruct the user to verify the changes if necessary.
8. If the user is satisfied, they can manually commit and push, or you can run `git commit -m "🚀 Sync: <message>" && git push origin HEAD` on their behalf.
