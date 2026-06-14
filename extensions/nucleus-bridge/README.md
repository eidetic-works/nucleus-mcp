# Nucleus Agent OS — VS Code Bridge

Zero-click auto-awake bridge for [Nucleus MCP](https://github.com/eidetic-works/nucleus-mcp) — surfaces relay messages from sibling AI agents as inline VS Code notifications, so you don't have to babysit the terminal.

## What it does

When Nucleus MCP receives a relay message addressed to your session (from another Claude/Codex/Cursor instance, a `nucleus_relay` MCP call, or an autonomous-wake trigger), this extension surfaces it as a native VS Code notification. One click to dismiss; one click to act.

Works alongside any VS Code fork that ships the standard VS Code API (`^1.80.0`) — VS Code, Cursor, Windsurf, Trae, etc.

## Quickstart

1. Install this extension.
2. Run [`nucleus-mcp`](https://pypi.org/project/nucleus-mcp/) somewhere — typically as an MCP server configured in your editor's MCP settings, or via `npx nucleus-mcp`.
3. Open any workspace that contains a `.brain/` directory (or set `NUCLEUS_BRAIN_PATH`).
4. Done. Inbound relay messages appear as notifications within seconds.

## Commands

- `Nucleus Bridge: Status` — show current bridge state, role, watched inbox path.

## Privacy

This extension reads files from your local `.brain/relay/` directory only. No network calls, no telemetry, no remote storage. The underlying `nucleus-mcp` server has its own opt-in telemetry — see https://pypi.org/project/nucleus-mcp/ for details.

## Links

- 🌐 [nucleusos.dev](https://nucleusos.dev)
- 📦 [nucleus-mcp on PyPI](https://pypi.org/project/nucleus-mcp/)
- 📦 [nucleus-mcp on npm](https://www.npmjs.com/package/nucleus-mcp)
- 🐙 [Source on GitHub](https://github.com/eidetic-works/nucleus-mcp)
- 🪪 MIT licensed

---

Published by [Eidetic Works](https://nucleusos.dev) · support: hello@nucleusos.dev
