# Autonomous Lane — Guide for Other Agents

> The autonomous lane is a Nucleus OS feature that lets you run a self-sustaining
> task-execution loop in any git repository. It uses GLM-5.2 (via Devin CLI) or
> Gemini (via agy CLI) to autonomously complete tasks defined in a SPEC.md file.

## What It Does

The lane runs 3 daemons that work together:

1. **Control watcher** — reads your SPEC.md, projects tasks into the task store, and dispatches them to executor lanes via relay
2. **Executor daemon** — claims a task, invokes the vendor CLI (`devin --model glm-5.2`), and marks it DONE with the commit SHA
3. **Secretary daemon** — independently verifies DONE tasks by running focused pytest, records CONFIRMED only on pass

The loop continues until all tasks in the SPEC.md are DONE/CONFIRMED.

## Quick Start

### Option 1: CLI (recommended)

```bash
# Install nucleus-mcp
pip install nucleus-mcp

# Go to your repo
cd /path/to/your-repo

# Initialize the lane
nucleus lane init

# Edit the generated SPEC.md with your tasks
# Then commit and re-pin
git add SPEC.md && git commit -m "Add lane spec"
nucleus lane init  # re-pin the spec

# Start the lane (background)
nucleus lane start --background

# Check status
nucleus lane status

# Stop
nucleus lane stop
```

### Option 2: pip package

```bash
pip install nucleus-autonomous-lane
cd /path/to/your-repo
nucleus-lane init
# Edit SPEC.md, commit
nucleus-lane start --background
nucleus-lane status
nucleus-lane stop
```

### Option 3: Template scripts

```bash
# Copy the template to your repo
cp -r /path/to/nucleus-mcp/templates/autonomous-lane/scripts/ /your-repo/scripts/

cd /your-repo
./scripts/lane-daemon.sh init
# Edit SPEC.md, commit
./scripts/lane-daemon.sh start
./scripts/lane-daemon.sh status
./scripts/lane-daemon.sh stop
```

### Option 4: MCP tools

From any MCP client (Devin, Claude Code, etc.):

```
nucleus_lane_init(repo_path="/path/to/your-repo")
# Edit SPEC.md, commit
nucleus_lane_start(repo_path="/path/to/your-repo")
nucleus_lane_status(repo_path="/path/to/your-repo")
nucleus_lane_stop(repo_path="/path/to/your-repo")
```

## SPEC.md Format

```markdown
# SPEC: Your Project Name

> This spec is pinned via git tag. Do not edit after pinning.

## Gate G1

### Task: your-g1_task_one
- **Title:** Human-readable title
- **Authority:** SPEC.md:10 (G1 criterion 1)
- **Acceptance:**
  - Criterion 1 (must be rerunnable evidence, not narration)
  - Criterion 2
- **Blocked by:** other_task_id  (optional)
- **Priority:** 1  (lower = higher priority, default: 2)

### Task: your-g1_task_two
- **Title:** Second task
- **Authority:** SPEC.md:20
- **Acceptance:**
  - Criterion 1
- **Blocked by:** your-g1_task_one
- **Priority:** 2
```

## Isolation

Each project gets its own `.brain/` directory:
- `.brain/nucleus.db` — task store (SQLite)
- `.brain/relay/` — relay messages between daemons
- `.brain/state/` — lane config and dispatch state
- `.brain/logs/` — daemon logs
- `.brain/feedback/` — feedback to the nucleus team

**No cross-project contamination.** The nucleus team's own brain is protected by an isolation guard.

## Requirements

- Python 3.10+
- `nucleus-mcp` pip package
- `devin` CLI installed (for GLM-5.2 executor) — https://cli.devin.ai
- Git

## Feedback

Submit bugs, enhancement requests, or observations to the nucleus team:

```bash
# CLI
nucleus lane feedback --type bug --subject "mktemp fails on Linux" --body "details..."

# MCP
nucleus_lane_feedback(feedback_type="bug", subject="...", body="...", reporter="your-name")
```

Feedback is stored in `.brain/feedback/lane_feedback.json`. The nucleus team reviews it periodically.

## Ownership and Maintenance

- **Core code** (`mcp_server_nucleus.runtime.lane`) is owned and maintained by the Nucleus team
- **Other agents** only use the surfaces (CLI, pip, template, MCP) — they do not modify core code
- **Feedback** flows one way: from users to the nucleus team via the feedback channel
- **Bug fixes and enhancements** are made by the nucleus team and released via pip updates

## How It Works (Architecture)

```
SPEC.md (pinned via git tag)
    ↓
SpecParser → WorkItem list
    ↓
ControlWatcher (watch loop)
    ↓ dispatches via relay
ExecutorDaemon (claims task, invokes devin CLI)
    ↓ marks DONE with commit SHA
SecretaryDaemon (runs focused pytest, records CONFIRMED)
    ↓
All tasks DONE/CONFIRMED → lane complete
```

The spec immutability gate (`verify_spec()`) checks the git tag, blob hash, and body SHA-256 before every dispatch cycle, preventing drift during long runs.

## Tips

- **Keep tasks small** — 15-25 min each is the sweet spot for GLM-5.2
- **Write clear acceptance criteria** — "rerunnable evidence, not narration"
- **Use dependencies** — `Blocked by:` ensures tasks run in the right order
- **Commit the SPEC.md before pinning** — the pin needs a git commit
- **Check status regularly** — `nucleus lane status` shows progress
- **Clear dispatch state if stuck** — if no new tasks dispatch, the dispatch records may be stale
