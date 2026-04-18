# nucleus-mcp

Sovereign Agent OS — Persistent Memory, Governance & Compliance for AI Agents.

114 MCP tools. Three reliability frontiers: GROUND (verify), ALIGN (correct), COMPOUND (learn).

## Install

### Native (one command per IDE)

| IDE | Command |
|-----|---------|
| **Claude Code** | `claude mcp add nucleus -- uvx nucleus-mcp` |
| **Cursor** | [Add to Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=nucleus&config=eyJuYW1lIjoibnVjbGV1cyIsInR5cGUiOiJjb21tYW5kIiwiY29tbWFuZCI6Im5weCIsImFyZ3MiOlsiLXkiLCJudWNsZXVzLW1jcCJdfQ==) |
| **Any IDE** | `pip install nucleus-mcp && nucleus init` |

### Manual Config

Pick your runtime:

**uvx** (zero install):
```json
{ "mcpServers": { "nucleus": { "command": "uvx", "args": ["nucleus-mcp"], "env": { "NUCLEUS_BRAIN_PATH": ".brain" } } } }
```

**npx** (zero install):
```json
{ "mcpServers": { "nucleus": { "command": "npx", "args": ["-y", "nucleus-mcp"], "env": { "NUCLEUS_BRAIN_PATH": ".brain" } } } }
```

**pip** (`pip install nucleus-mcp` first):
```json
{ "mcpServers": { "nucleus": { "command": "nucleus-mcp", "env": { "NUCLEUS_BRAIN_PATH": ".brain" } } } }
```

## Links

- [Full docs](https://github.com/eidetic-works/nucleus-mcp)
- [PyPI](https://pypi.org/project/nucleus-mcp/)
- [Discord](https://discord.gg/RJuBNNJ5MT)

## License

MIT
