# Nucleus Architecture Reference

## MCP vs. IDE Extensions: Why both?

> [!NOTE]
> This section captures the architectural reasoning for the division of labor between the Nucleus MCP server and the VS Code Bridge Extension.

**Query**: Can what the Nucleus extension is doing be done by MCP alone?

**Answer**: 
No, not entirely. While MCP is excellent for moving data and executing tools, the Nucleus Bridge Extension is necessary for three specific reasons that MCP cannot currently handle alone:

### 1. UI Sovereignty (The "Hardened Wake")
MCP servers run as isolated child processes. They have no "motor skills" inside the IDE—they cannot reach out and force a sidebar to open, trigger a specific VS Code command, or split the editor to show a "Virtual Doc." Only code running within the IDE's extension host has the permissions to manipulate the UI.

### 2. Autonomous Event Subscriptions
While the Agent receives cursor and file metadata during a turn, the extension performs **Passive Siphoning**. It subscribes to internal IDE events like `onDidChangeTextEditorSelection` to update the `.brain/context/ide_state.json` in real-time, even when no agent is active. MCP servers cannot "listen" to these IDE-native events.

### 3. The "Bridge" Role
MCP is essentially a **Conduit** for data, but the Extension is the **Adapter**. 
*   **MCP** provides the "Logic" (the relay mailbox system).
*   **The Extension** provides the "Senses" (watching your tabs) and the "Body" (opening the panel when an urgent message arrives).

Without the extension, Nucleus would be "blind" to your real-time IDE movements and "paralyzed" when it needs to grab your attention.

## Atomic Session IDs (T3.11)

To prevent notification bloat and enable precise targeting, Nucleus uses a deterministic session ID schema:

`[agent_type]:[project_slug]:[pid]`

Example: `windsurf:ai-mvp-backend:86814`

### Isolation Guard Protocol
1.  **Sticky Targeting**: If a relay contains `to_session_id`, the global Watchdog **bypasses** event emission and `pending.json` consolidation.
2.  **Recipient Lockdown**: Only the IDE Bridge matching the target `session_id` will display a notification (via the **Graceful Nudge** system).
3.  **Ancestry Awareness**: The MCP server detects its host IDE by walking up the process tree to find a registered heartbeat PID.

## Richer Engrams: The "Force Multiplier" Effect

The existence of the extension actually **increases** the potential for rich engrams rather than limiting them. 

*   **High-Fidelity Context**: The extension provides a continuous stream of "Sensory" data (cursor movements, active tabs, visible ranges) that a standalone MCP server cannot access. 
*   **Cognitive Synthesis**: The Nucleus MCP server acts as the "Mind," taking this raw sensory stream and synthesizing it into deep, cross-referenced **Engrams**. 
*   **Visibility**: By separating "Presence" (Extension) from "Intelligence" (MCP), we allow the Brain to become an infinitely expandable repository of knowledge that isn't bogged down by UI management.

### 3. Graceful UI Degradation (The "Hardened Wake")
Proprietary VS Code forks (Windsurf, Cursor) heavily sandbox their AI UI panels, actively blocking third-party extensions from natively injecting text and submitting prompts (unlike Antigravity, which exposes `antigravity.sendPromptToAgentPanel`).

To ensure zero task loss across any host, the bridge must implement a multi-tier degradation loop:
- **Tier 1 (Native Injection):** If the host exposes a native command that accepts arguments (e.g. `antigravity.sendPromptToAgentPanel`), execute and auto-submit.
- **Tier 2 (Clipboard + Focus Focus):** If native injection is sandboxed (e.g. Windsurf), copy the prompt to the OS Clipboard and execute the host's native focus command (e.g. `windsurf.cascadePanel.focus`) without arguments to pop the panel smoothly. The user pastes via `Cmd+V`.
- **Tier 3 (Virtual Document):** If the UI panel commands are completely absent or crash, fall back to opening an ephemeral, read-only VS Code text document (`nucleus-prompt:`) displaying the payload.

## Future Architecture: Dynamic API Surface Discovery

As proprietary forks continuously update their sandboxed APIs, hardcoding command strings (like `windsurf.cascadePanel.focus`) inside the extension bridge introduces fragility. 

To solve this, the Nucleus installer can implement **Dynamic Manifest Parsing** at install time. By locating the internal, proprietary extension bundles shipped within the application package, the installer can read the `package.json` manifest and map the exact command registry for that specific version.

**Known Manifest Paths (macOS):**
- **Windsurf:** `/Applications/Windsurf.app/Contents/Resources/app/extensions/windsurf/package.json`
- **Cursor:** `/Applications/Cursor.app/Contents/Resources/app/extensions/cursor/package.json`
