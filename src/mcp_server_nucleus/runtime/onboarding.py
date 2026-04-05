"""
Interactive onboarding wizard for `nucleus init`.

Detects the project environment, asks the user a few questions,
and tailors the .brain setup accordingly. The goal: make the first
30 seconds impressive.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone


# ── Project Detection ────────────────────────────────────────────

PROJECT_SIGNATURES = {
    "python": {
        "files": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"],
        "label": "Python",
        "icon": "🐍",
    },
    "node": {
        "files": ["package.json"],
        "label": "Node.js / JavaScript",
        "icon": "⬢",
    },
    "rust": {
        "files": ["Cargo.toml"],
        "label": "Rust",
        "icon": "🦀",
    },
    "go": {
        "files": ["go.mod"],
        "label": "Go",
        "icon": "🐹",
    },
    "ruby": {
        "files": ["Gemfile"],
        "label": "Ruby",
        "icon": "💎",
    },
    "java": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "label": "Java / Kotlin",
        "icon": "☕",
    },
    "dotnet": {
        "files": ["*.csproj", "*.fsproj", "*.sln"],
        "label": ".NET",
        "icon": "🔷",
    },
}

PERSONAS = {
    "developer": {
        "label": "Developer",
        "description": "Building software — tasks, code context, session memory",
        "recipe": None,
        "template": "default",
    },
    "founder": {
        "label": "Founder / PM",
        "description": "Strategy, roadmaps, decision logs, stakeholder context",
        "recipe": "founder",
        "template": "default",
    },
    "sre": {
        "label": "SRE / DevOps",
        "description": "Incident tracking, runbooks, deployment governance",
        "recipe": "sre",
        "template": "default",
    },
    "researcher": {
        "label": "Researcher / Student",
        "description": "Knowledge management, literature notes, writing projects",
        "recipe": None,
        "template": "solo",
    },
}


def detect_project(cwd: Path = None) -> dict:
    """Detect project type, name, and useful metadata from the working directory."""
    cwd = cwd or Path.cwd()
    result = {
        "name": cwd.name,
        "path": str(cwd),
        "languages": [],
        "git": False,
        "git_remote": None,
        "description": None,
    }

    # Git detection
    if (cwd / ".git").exists():
        result["git"] = True
        try:
            import subprocess
            r = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5, cwd=str(cwd),
            )
            if r.returncode == 0 and r.stdout.strip():
                result["git_remote"] = r.stdout.strip()
        except Exception:
            pass

    # Language detection
    for lang_id, sig in PROJECT_SIGNATURES.items():
        for pattern in sig["files"]:
            if "*" in pattern:
                if list(cwd.glob(pattern)):
                    result["languages"].append(lang_id)
                    break
            elif (cwd / pattern).exists():
                result["languages"].append(lang_id)
                break

    # Try to extract project name/description from common files
    result["name"] = _extract_project_name(cwd) or cwd.name

    return result


def _extract_project_name(cwd: Path) -> str | None:
    """Try to pull a project name from manifest files."""
    # pyproject.toml
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.strip().startswith("name"):
                    # name = "something"
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
        except Exception:
            pass

    # package.json
    pkg = cwd / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            return data.get("name")
        except Exception:
            pass

    # Cargo.toml
    cargo = cwd / "Cargo.toml"
    if cargo.exists():
        try:
            text = cargo.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.strip().startswith("name"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
        except Exception:
            pass

    return None


# ── Interactive Prompts ──────────────────────────────────────────

def _ask_choice(prompt: str, options: list[dict], default: int = 0) -> str:
    """Present a numbered choice. Each option is {key, label, description?}.
    Returns the selected key. Non-interactive falls back to default."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options):
        marker = ">" if i == default else " "
        desc = f" — {opt['description']}" if opt.get("description") else ""
        print(f"  {marker} [{i + 1}] {opt['label']}{desc}")

    if not sys.stdin.isatty():
        print(f"  (non-interactive, using default: {options[default]['label']})")
        return options[default]["key"]

    while True:
        try:
            raw = input(f"\nChoose [1-{len(options)}] (default {default + 1}): ").strip()
            if not raw:
                return options[default]["key"]
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]["key"]
            print(f"  Please enter a number between 1 and {len(options)}")
        except (ValueError, EOFError):
            return options[default]["key"]


def _ask_text(prompt: str, default: str = "") -> str:
    """Ask for free text input. Returns default if non-interactive."""
    if not sys.stdin.isatty():
        return default
    try:
        hint = f" [{default}]" if default else ""
        raw = input(f"{prompt}{hint}: ").strip()
        return raw or default
    except (EOFError, KeyboardInterrupt):
        return default


# ── Wizard ───────────────────────────────────────────────────────

def run_onboarding_wizard(brain_path: str = ".brain") -> dict:
    """Run the interactive onboarding wizard.

    Returns a config dict:
        {
            "brain_path": str,
            "template": "default" | "solo",
            "persona": str,
            "recipe": str | None,
            "project_name": str,
            "project_description": str,
            "languages": [str],
            "auto_setup_ide": bool,
        }
    """
    print()
    print("=" * 60)
    print("  NUCLEUS — Sovereign Agent OS")
    print("  Interactive Setup Wizard")
    print("=" * 60)

    # Step 1: Detect environment
    project = detect_project()
    print(f"\n📂 Detected project: {project['name']}")
    if project["languages"]:
        lang_labels = []
        for lang_id in project["languages"]:
            sig = PROJECT_SIGNATURES[lang_id]
            lang_labels.append(f"{sig['icon']} {sig['label']}")
        print(f"   Languages: {', '.join(lang_labels)}")
    if project["git"]:
        print(f"   Git: yes" + (f" ({project['git_remote']})" if project["git_remote"] else ""))
    else:
        print("   Git: no")

    # Step 2: Persona selection
    persona_options = [
        {"key": k, "label": v["label"], "description": v["description"]}
        for k, v in PERSONAS.items()
    ]
    persona_key = _ask_choice(
        "What's your primary use case?",
        persona_options,
        default=0,
    )
    persona = PERSONAS[persona_key]

    # Step 3: Project description (for seeding context)
    project_desc = _ask_text(
        "\nDescribe your project in one line (or press Enter to skip)",
        default="",
    )

    # Step 4: IDE auto-configuration
    ide_choice = _ask_choice(
        "Auto-configure your AI IDEs (Claude Desktop, Cursor, Windsurf)?",
        [
            {"key": "yes", "label": "Yes (recommended)", "description": "detect and patch IDE configs"},
            {"key": "no", "label": "No", "description": "I'll configure manually"},
        ],
        default=0,
    )

    config = {
        "brain_path": brain_path,
        "template": persona["template"],
        "persona": persona_key,
        "recipe": persona.get("recipe"),
        "project_name": project["name"],
        "project_description": project_desc,
        "languages": project["languages"],
        "auto_setup_ide": ide_choice == "yes",
        "git": project["git"],
        "git_remote": project.get("git_remote"),
    }

    print(f"\n✅ Configuration:")
    print(f"   Brain path: {brain_path}")
    print(f"   Template:   {persona['template']} ({persona['label']})")
    if persona.get("recipe"):
        print(f"   Recipe:     {persona['recipe']}")
    print()

    return config


def seed_project_context(brain_path: Path, config: dict):
    """Write a tailored context.md and first engram based on wizard answers."""
    context_file = brain_path / "memory" / "context.md"
    (brain_path / "memory").mkdir(parents=True, exist_ok=True)

    # Build context document
    lines = [f"# {config['project_name']}"]
    if config.get("project_description"):
        lines.append(f"\n{config['project_description']}")
    lines.append("")

    if config["languages"]:
        lang_strs = []
        for lang_id in config["languages"]:
            sig = PROJECT_SIGNATURES.get(lang_id, {})
            lang_strs.append(sig.get("label", lang_id))
        lines.append(f"**Tech stack:** {', '.join(lang_strs)}")

    if config.get("git_remote"):
        lines.append(f"**Repository:** {config['git_remote']}")

    persona = PERSONAS.get(config.get("persona", "developer"), {})
    lines.append(f"\n**Workflow:** {persona.get('label', 'Developer')} — {persona.get('description', '')}")
    lines.append("")

    context_file.write_text("\n".join(lines), encoding="utf-8")

    # Seed a first engram about the project
    engrams_file = brain_path / "memory" / "engrams.json"
    now = datetime.now(timezone.utc).isoformat()
    engrams = []
    if engrams_file.exists():
        try:
            engrams = json.loads(engrams_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    project_engram = {
        "id": f"engram_{now.replace(':', '').replace('-', '').replace('.', '')[:18]}",
        "content": f"Project '{config['project_name']}' initialized with Nucleus. "
                   f"Persona: {persona.get('label', 'Developer')}. "
                   + (f"Stack: {', '.join(config['languages'])}. " if config["languages"] else "")
                   + (f"Description: {config['project_description']}" if config.get("project_description") else ""),
        "tags": ["project", "onboarding", config.get("persona", "developer")],
        "source": "nucleus_init",
        "created_at": now,
    }
    engrams.append(project_engram)
    engrams_file.write_text(json.dumps(engrams, indent=2), encoding="utf-8")


def print_post_init_summary(config: dict):
    """Print a persona-tailored 'what to do next' section."""
    persona_key = config.get("persona", "developer")

    print("\n" + "=" * 60)
    print("🚀 YOU'RE READY")
    print("=" * 60)

    # Universal first step
    if config.get("auto_setup_ide"):
        print("\n① Restart your AI client to pick up the new config")
    else:
        print("\n① Add the MCP config to your AI client (printed above)")

    # Persona-specific quick wins
    print("\n② Try these first commands:")

    if persona_key == "founder":
        print("   → \"Write an engram about our current strategy\"")
        print("   → \"Create a task: define Q2 roadmap\"")
        print("   → \"Show me the satellite view\"")
    elif persona_key == "sre":
        print("   → \"Run a health check on this brain\"")
        print("   → \"Create a task: set up deployment monitoring\"")
        print("   → \"Show the system dashboard\"")
    elif persona_key == "researcher":
        print("   → \"Write an engram about my research topic\"")
        print("   → \"Create a task: literature review for [topic]\"")
        print("   → \"Search my memory for [keyword]\"")
    else:  # developer
        print("   → \"Show me all tasks\"")
        print("   → \"Write an engram about the architecture of this project\"")
        print("   → \"Start a session with goal: implement [feature]\"")

    print("\n③ Explore:")
    print("   nucleus status          → Brain health")
    print("   nucleus doctor          → Diagnose setup")
    print("   nucleus recipe list     → Browse workflow packs")

    print(f"\n📚 Docs: https://github.com/eidetic-works/nucleus-mcp")
    print()
