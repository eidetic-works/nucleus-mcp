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

To ensure zero task loss across any host, the bridge degrades through the
following chain. **The names and numbers below are the ones the shipped
extension actually uses** — `ExecutionTier` in `extension.ts`, as embedded in
every tracked `.vsix`. An earlier version of this section described a different
scheme (Tier 1 / 2 / 3, with clipboard-and-focus as a tier of its own) that no
released build has implemented (ledger CS-6).

- **`Tier 3A (Native)`** — the host exposes a command that accepts arguments
  (e.g. `antigravity.sendPromptToAgentPanel`): execute and auto-submit. The
  enum calls this `NativeChat`.
- **`Tier 3A (Copilot)`** — the same rung for a Copilot-style chat surface.
  `CopilotChat` in the enum, sharing Tier 3A's label deliberately: from the
  user's point of view both auto-submit.
- **`Tier 4 (Virtual Doc)`** — panel commands absent or crashing: open an
  ephemeral read-only document (`nucleus-prompt:`) with the payload.
  `VirtualDoc`, and the initial value of `activeTier`, so an unrecognised host
  degrades to this rather than to nothing.
- **Tier 4.5** — an unmissable toast, if even the virtual document fails.
  Not in the enum; it exists only as `triggerTier4Fallback`'s tail.

**Clipboard-and-focus is not a tier of its own.** Copying to the clipboard and
popping the host panel happens *inside* the Native and Copilot branches, as
their in-branch fallback when injection is sandboxed (Cursor and Windsurf both
take this path). Documenting it as a separate rung implied a host could land
there without first attempting native injection, which no build does.

The numbering starts at 3A because it is inherited from an earlier scheme; it is
recorded here as it is rather than renumbered, because the strings are
user-visible in the status bar.

## Future Architecture: Dynamic API Surface Discovery

As proprietary forks continuously update their sandboxed APIs, hardcoding command strings (like `windsurf.cascadePanel.focus`) inside the extension bridge introduces fragility. 

To solve this, the Nucleus installer can implement **Dynamic Manifest Parsing** at install time. By locating the internal, proprietary extension bundles shipped within the application package, the installer can read the `package.json` manifest and map the exact command registry for that specific version.

**Known Manifest Paths (macOS):**
- **Windsurf:** `/Applications/Windsurf.app/Contents/Resources/app/extensions/windsurf/package.json`
- **Cursor:** `/Applications/Cursor.app/Contents/Resources/app/extensions/cursor/package.json`
