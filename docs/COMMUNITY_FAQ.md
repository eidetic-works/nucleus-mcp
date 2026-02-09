# Nucleus MCP: Community FAQ

## General Questions

### Q: What is Nucleus MCP?
**A:** Nucleus MCP is a Model Context Protocol (MCP) server that acts as a "Universal Brain" for AI agents. It provides a shared, persistent memory layer that works across multiple AI tools like Claude Desktop, Cursor, and Windsurf.

### Q: Why do I need it?
**A:** Most AI tools started from scratch with every new conversation. Nucleus allows you to save context (decisions, project state, tasks) in a local `.brain/` folder that survives session restarts and is shared across all your AI assistants.

---

## Tool Compatibility

### Q: How do I use it with ChatGPT?
**A:** ChatGPT now supports MCP in its **Developer Beta Mode** (Web Browser).
1. Go to ChatGPT Settings → Apps → Advanced.
2. Enable **Developer Mode**.
3. Use the Nucleus SSE Bridge (see below) to connect your local brain to the web interface.

**Note:** For a quick manual sync, you can always copy the contents of your `.brain/state.md` and paste it into ChatGPT.

### Q: Does it work with Cursor / Windsurf?
**A:** Yes! Nucleus is designed specifically for these tools. Running `nucleus-init` will automatically update your `project.json` or equivalent config files to register the Nucleus MCP server.

### Q: Is my data safe?
**A:** 100%. Nucleus is local-first. All your data stays in the `.brain/` folder on your own machine. There is no cloud storage, no telemetry, and no data tracking.

---

## Technical Questions

### Q: How do I install it?
**A:** 
```bash
pip install nucleus-mcp
nucleus-init
```

### Q: What's the difference between an "Engram" and a "Task"?
**A:** 
- **Engram:** Persistent knowledge or an architectural decision (long-term memory).
- **Task:** A specific actionable item (operational memory).
Nucleus manages both to give your AI a complete picture of your project's past and future.

---

*Found a bug or have a request? Open an issue on [GitHub](https://github.com/eidetic-works/nucleus-mcp)!*
