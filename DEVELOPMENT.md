# Development Workflow

## Branch Strategy

```
main (protected)
  └── dev (integration branch)
       ├── feature/xxx
       └── fix/xxx
```

### Branches

| Branch | Purpose | Merges To |
|--------|---------|-----------|
| `main` | Production-ready, PyPI releases | - |
| `dev` | Integration, testing | `main` (via PR) |
| `feature/*` | New features | `dev` (via PR) |
| `fix/*` | Bug fixes | `dev` (via PR) |

## Development Setup

```bash
# Clone
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd nucleus-mcp

# Create dev branch (if not exists)
git checkout -b dev
git push -u origin dev

# Create feature branch
git checkout dev
git pull origin dev
git checkout -b feature/my-feature

# Work on feature...
git add .
git commit -m "feat: description"
git push -u origin feature/my-feature

# Create PR to dev branch
```

## Local Testing

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting
ruff check src/
```

## Release Process

1. Ensure all features merged to `dev`
2. Create PR from `dev` → `main`
3. Review and merge
4. Tag release: `git tag v1.x.x && git push --tags`
5. Publish to PyPI:
   ```bash
   python -m build
   twine upload dist/*
   ```

## Internal Work Separation

### What Goes in This Repo (PUBLIC)
- Core MCP server code (`src/`)
- Tests (`tests/`)
- Examples (`examples/`)
- Public documentation (`docs/DEMO_SCRIPT.md`)
- Standard files (README, LICENSE, etc.)

### What Stays Local (NEVER COMMIT)
- Launch strategy docs (keep in a separate local folder, NOT in this repo)
- Internal roadmaps
- GTM documents
- Outreach plans
- Any `.md` matching patterns in `.gitignore`

## Pre-Push Checklist

```bash
# Before pushing, always verify:
git status                    # No unwanted files staged
git diff --cached --name-only # Review what's being committed
```

## Protected Files (via .gitignore)

The following patterns are blocked from commits:
- `docs/*LAUNCH*.md`
- `docs/*STRATEGY*.md`
- `*_INTERNAL.md`
- `*_PRIVATE.md`
- `GTM*.md`
- `OUTREACH*.md`
