# Nucleus OS - The Open Core

Nucleus OS is an open-source, sovereign Operating System for AI Agents. It provides the "One System Brain" architecture that allows multiple AI agents (across Cursor, Windsurf, Gemini CLI, and background crons) to share a single, unified memory and task graph without hallucinating or corrupting context.

## The Problem
If you have 4 projects and 3 AI agents, you end up with 12 fractured contexts. Your agents forget decisions, rewrite the same code, and step on each other's toes.

## The Solution: The "One System Brain"
Nucleus OS decouples the agent's memory from the local repository. By establishing a central `.brain` folder and a universal `nucleus` CLI, any agent in any folder can read and write to the same global ledger.

### 1. Install the Kernel
```bash
pip install nucleus-mcp
```

### 2. Initialize your Sovereign Brain
```bash
nucleus init
```

### 3. Connect your Agents
Add this to your `~/.zshrc` or `~/.bashrc`:
```bash
export NUCLEAR_BRAIN_PATH="/path/to/your/.brain"
```

Now, from *any* folder, you or your agents can run:
- `nucleus engram write "strategy" "Move all state to SQLite WAL" --intensity 10`
- `nucleus status`
- `nucleus task list`

## What's Included in the Open Source Core?
- **The CLI**: A universal interface (`nucleus engram`, `nucleus task`, `nucleus status`) designed specifically to output clean JSON for AI agent consumption (`--format json`).
- **The `.brain` Architecture**: The standard format for sovereign AI memory.
- **The MCP Server**: Hooks the brain directly into Cursor, Windsurf, and Claude Desktop.

## Pro Features (Coming Soon)
- **Nucleus Autopilot**: A self-healing daemon that wraps Gemini/Claude CLI to catch tracebacks, diagnose errors, and write fixes autonomously without human intervention.
- **Sovereign Studio**: A beautiful desktop UI for managing your brain graph.
- **Nucleus Cloud**: Multi-machine sync and multiplayer team brains.

## Get Started
Hook up Gemini CLI:
```bash
npm i -g @google/gemini-cli
gemini -p "You can run shell commands. Run 'nucleus status --format json' and tell me the health of my brain."
```