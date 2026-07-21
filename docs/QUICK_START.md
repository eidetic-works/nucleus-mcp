# Nucleus Quick Start Guide
## Get Running in 5 Minutes
### v1.16.0

---

## Installation

```bash
pip install nucleus-mcp
```

Or from source:

```bash
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd nucleus-mcp
pip install -e .
```

---

## Setup

```bash
nucleus init
```

This seeds `.brain/` in your project and writes a local `.mcp.json` for Claude Code. Restart Claude Code and the `nucleus_*` tools are available.

For other clients (Cursor, Windsurf, Claude Desktop):

```bash
nucleus setup
```

Verify it's working:

```bash
nucleus doctor
```

---

## Using the tools

Nucleus exposes facade tools — each one takes an `action` and `params`. Here are the core ones:

### Memory — `nucleus_engrams`

Write a memory that persists across sessions:

```
nucleus_engrams(action="write", params={"key": "auth-design-decision", "content": "We chose JWT over session cookies because the API is stateless."})
```

Recall it later:

```
nucleus_engrams(action="recall", params={"query": "auth design"})
```

### Tasks — `nucleus_tasks`

Create a task:

```
nucleus_tasks(action="add", params={"description": "Fix the login bug", "priority": 1})
```

List tasks:

```
nucleus_tasks(action="list", params={"status": "pending"})
```

Claim and complete:

```
nucleus_tasks(action="claim", params={"task_id": "TASK-001", "agent_id": "claude-code"})
nucleus_tasks(action="update", params={"task_id": "TASK-001", "updates": {"status": "done"}})
```

### Sessions — `nucleus_sessions`

Save your context at the end of a session:

```
nucleus_sessions(action="save", params={"context": "Working on the auth refactor, 3 files left to update"})
```

Resume next time:

```
nucleus_sessions(action="resume", params={})
```

### Cross-vendor delegate — `nucleus_delegate`

Hand a task to another AI vendor (Gemini, Devin/GLM):

```
nucleus_delegate(action="dispatch", params={"vendor": "agy", "prompt": "Review src/auth.py for security issues", "artifact_ref": "src/auth.py", "mode": "read"})
```

Multi-round plan review loop (author drafts, reviewer audits, iterate until approved):

```
nucleus_delegate(action="plan_review_loop", params={"prompt": "Plan the migration from JWT to PASETO", "author_vendor": "agy", "reviewer_vendor": "devin", "max_rounds": 3})
```

Poll status:

```
nucleus_delegate(action="plan_review_loop_status", params={"plan_id": "plan_20260721_..."})
```

### Governance — `nucleus_governance`

Lock a file immutable:

```
nucleus_governance(action="lock", params={"path": "src/auth.py"})
```

Check security state:

```
nucleus_governance(action="status", params={})
```

---

## What's next

- **Full tool reference:** [docs/CLI_REFERENCE.md](CLI_REFERENCE.md)
- **Plan review loop:** [docs/PLAN_REVIEW_LOOP.md](PLAN_REVIEW_LOOP.md)
- **Engram specification:** [docs/ENGRAM_SPECIFICATION.md](ENGRAM_SPECIFICATION.md)
- **Governance policies:** [docs/GOVERNANCE_POLICIES.md](GOVERNANCE_POLICIES.md)
- **Security:** [docs/SECURITY_WHITEPAPER.md](SECURITY_WHITEPAPER.md)
