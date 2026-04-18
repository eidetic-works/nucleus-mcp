"""
Recipe System for Nucleus Agent OS.

Recipes are YAML-based workflow packs that configure the brain for specific
personas and use cases. Each recipe bundles:
  - Starter engrams (contextual memory seeds)
  - Recommended combos (God Combo workflows)
  - Scheduled tasks (recurring workflows)
  - MCP server configs (recommended tool servers)

Usage:
  nucleus init --recipe founder   # Install Founder OS recipe
  nucleus init --recipe sre       # Install SRE Brain recipe
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# ============================================================================
# RECIPE SCHEMA
# ============================================================================

REQUIRED_FIELDS = {"name", "description", "version", "author"}
OPTIONAL_FIELDS = {
    "persona",
    "engram_templates",
    "recommended_combos",
    "scheduled_tasks",
    "mcp_servers",
    "brain_config",
    "tags",
    "first_run_tips",
}
VALID_CONTEXTS = {"Feature", "Architecture", "Brand", "Strategy", "Decision"}


class RecipeValidationError(Exception):
    """Raised when a recipe YAML fails schema validation."""
    pass


class RecipeNotFoundError(Exception):
    """Raised when a requested recipe does not exist."""
    pass


def validate_recipe(data: Dict[str, Any]) -> List[str]:
    """
    Validate a recipe dict against the schema.
    Returns list of errors (empty = valid).
    """
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    # Validate version format (semver-ish)
    version = data.get("version", "")
    if version and not isinstance(version, str):
        errors.append(f"'version' must be a string, got {type(version).__name__}")

    # Validate engram_templates
    engrams = data.get("engram_templates", [])
    if not isinstance(engrams, list):
        errors.append("'engram_templates' must be a list")
    else:
        for i, eng in enumerate(engrams):
            if not isinstance(eng, dict):
                errors.append(f"engram_templates[{i}] must be a dict")
                continue
            if "key" not in eng:
                errors.append(f"engram_templates[{i}] missing 'key'")
            if "value" not in eng:
                errors.append(f"engram_templates[{i}] missing 'value'")
            ctx = eng.get("context", "Feature")
            if ctx not in VALID_CONTEXTS:
                errors.append(
                    f"engram_templates[{i}] invalid context '{ctx}', "
                    f"must be one of {VALID_CONTEXTS}"
                )
            intensity = eng.get("intensity", 5)
            if not isinstance(intensity, (int, float)) or intensity < 1 or intensity > 10:
                errors.append(f"engram_templates[{i}] intensity must be 1-10")

    # Validate recommended_combos
    combos = data.get("recommended_combos", [])
    if not isinstance(combos, list):
        errors.append("'recommended_combos' must be a list")
    else:
        valid_combos = {"pulse_and_polish", "self_healing_sre", "fusion_reactor"}
        for i, combo in enumerate(combos):
            if not isinstance(combo, str):
                errors.append(f"recommended_combos[{i}] must be a string")
            elif combo not in valid_combos:
                errors.append(
                    f"recommended_combos[{i}] unknown combo '{combo}', "
                    f"valid: {valid_combos}"
                )

    # Validate scheduled_tasks
    tasks = data.get("scheduled_tasks", [])
    if not isinstance(tasks, list):
        errors.append("'scheduled_tasks' must be a list")
    else:
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"scheduled_tasks[{i}] must be a dict")
                continue
            if "name" not in task:
                errors.append(f"scheduled_tasks[{i}] missing 'name'")
            if "schedule" not in task:
                errors.append(f"scheduled_tasks[{i}] missing 'schedule'")

    # Validate mcp_servers
    servers = data.get("mcp_servers", [])
    if not isinstance(servers, list):
        errors.append("'mcp_servers' must be a list")

    # Validate first_run_tips
    tips = data.get("first_run_tips", [])
    if not isinstance(tips, list):
        errors.append("'first_run_tips' must be a list")

    return errors


# ============================================================================
# RECIPE LOADING
# ============================================================================

def _get_builtin_recipes_dir() -> Path:
    """Get the path to the built-in recipes directory."""
    return Path(__file__).parent.parent / "recipes"


def _get_user_recipes_dir() -> Optional[Path]:
    """Get the user's custom recipes directory (if it exists)."""
    brain_path = os.environ.get("NUCLEAR_BRAIN_PATH", ".brain")
    user_dir = Path(brain_path) / "recipes"
    if user_dir.exists():
        return user_dir
    return None


def search_recipes(query: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Search recipes by query string or filter by tags.
    
    Args:
        query: Optional search string (matches name, description, persona)
        tags: Optional list of tags to filter by (OR logic)
    
    Returns:
        List of matching recipes
    """
    all_recipes = list_recipes()
    
    if not query and not tags:
        return all_recipes
    
    results = []
    for recipe in all_recipes:
        # Tag filtering (OR logic - match any tag)
        if tags:
            recipe_tags = recipe.get("tags", [])
            if not any(tag in recipe_tags for tag in tags):
                continue
        
        # Query filtering (search in name, description, persona)
        if query:
            query_lower = query.lower()
            searchable = " ".join([
                recipe.get("name", ""),
                recipe.get("description", ""),
                recipe.get("persona", ""),
            ]).lower()
            if query_lower not in searchable:
                continue
        
        results.append(recipe)
    
    return results


def list_recipes() -> List[Dict[str, Any]]:
    """
    List all available recipes (built-in + user-defined).
    Returns list of {name, description, version, author, source, path, tags, persona}.
    """
    recipes = []

    # Built-in recipes
    builtin_dir = _get_builtin_recipes_dir()
    if builtin_dir.exists():
        for f in sorted(builtin_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue  # Skip schema files
            try:
                data = yaml.safe_load(f.read_text())
                if data and isinstance(data, dict):
                    recipes.append({
                        "name": data.get("name", f.stem),
                        "description": data.get("description", ""),
                        "version": data.get("version", "0.0.0"),
                        "author": data.get("author", "unknown"),
                        "source": "builtin",
                        "path": str(f),
                        "tags": data.get("tags", []),
                        "persona": data.get("persona", ""),
                    })
            except Exception as e:
                logger.warning(f"Failed to parse recipe {f}: {e}")

    # User-defined recipes
    user_dir = _get_user_recipes_dir()
    if user_dir:
        for f in sorted(user_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                data = yaml.safe_load(f.read_text())
                if data and isinstance(data, dict):
                    recipes.append({
                        "name": data.get("name", f.stem),
                        "description": data.get("description", ""),
                        "version": data.get("version", "0.0.0"),
                        "author": data.get("author", "unknown"),
                        "source": "user",
                        "tags": data.get("tags", []),
                        "persona": data.get("persona", ""),
                        "path": str(f),
                    })
            except Exception as e:
                logger.warning(f"Failed to parse user recipe {f}: {e}")

    return recipes


def load_recipe(name: str) -> Dict[str, Any]:
    """
    Load a recipe by name. Searches built-in first, then user recipes.
    Raises RecipeNotFoundError if not found.
    Raises RecipeValidationError if schema validation fails.
    """
    # Search built-in
    builtin_dir = _get_builtin_recipes_dir()
    recipe_path = builtin_dir / f"{name}.yaml"
    if not recipe_path.exists():
        # Search user recipes
        user_dir = _get_user_recipes_dir()
        if user_dir:
            recipe_path = user_dir / f"{name}.yaml"

    if not recipe_path.exists():
        available = [r["name"] for r in list_recipes()]
        raise RecipeNotFoundError(
            f"Recipe '{name}' not found. Available: {', '.join(available) or 'none'}"
        )

    data = yaml.safe_load(recipe_path.read_text())
    if not data or not isinstance(data, dict):
        raise RecipeValidationError(f"Recipe '{name}' is empty or not a valid YAML mapping")

    errors = validate_recipe(data)
    if errors:
        raise RecipeValidationError(
            f"Recipe '{name}' has {len(errors)} validation error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    data["_source_path"] = str(recipe_path)
    return data


# ============================================================================
# RECIPE INSTALLATION
# ============================================================================

def install_recipe(brain_path: Path, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Install a recipe into an existing .brain directory.
    Returns a summary dict of what was installed.
    """
    recipe_name = recipe_data.get("name", "unknown")
    now = datetime.now(tz=__import__('datetime').timezone.utc).isoformat()
    summary = {
        "recipe": recipe_name,
        "version": recipe_data.get("version", "0.0.0"),
        "installed_at": now,
        "engrams_written": 0,
        "tasks_created": 0,
        "combos_enabled": [],
        "mcp_servers_configured": 0,
        "tips": [],
    }

    # 1. Write engram templates to the canonical engram ledger (JSONL)
    engrams = recipe_data.get("engram_templates", [])
    if engrams:
        ledger_file = brain_path / "engrams" / "ledger.jsonl"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing keys to avoid duplicates
        existing_keys = set()
        if ledger_file.exists():
            with open(ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            existing_keys.add(json.loads(line).get("key", ""))
                        except Exception:
                            pass

        new_count = 0
        with open(ledger_file, "a", encoding="utf-8") as f:
            for eng in engrams:
                if eng["key"] not in existing_keys:
                    record = {
                        "key": eng["key"],
                        "value": eng["value"],
                        "context": eng.get("context", "Feature"),
                        "intensity": eng.get("intensity", 5),
                        "version": 1,
                        "timestamp": now,
                        "source": f"recipe:{recipe_name}",
                    }
                    f.write(json.dumps(record) + "\n")
                    new_count += 1

        summary["engrams_written"] = new_count

    # 2. Create scheduled tasks
    tasks = recipe_data.get("scheduled_tasks", [])
    if tasks:
        tasks_file = brain_path / "ledger" / "tasks.json"
        existing_tasks = []
        if tasks_file.exists():
            try:
                existing_tasks = json.loads(tasks_file.read_text())
                if not isinstance(existing_tasks, list):
                    existing_tasks = []
            except Exception:
                existing_tasks = []

        existing_ids = {t.get("id") for t in existing_tasks}
        new_tasks = []
        for task in tasks:
            task_id = f"recipe-{recipe_name}-{task['name'].lower().replace(' ', '-')}"
            if task_id not in existing_ids:
                new_tasks.append({
                    "id": task_id,
                    "description": task.get("description", task["name"]),
                    "status": "READY",
                    "priority": task.get("priority", 2),
                    "blocked_by": [],
                    "required_skills": [],
                    "claimed_by": None,
                    "source": f"recipe:{recipe_name}",
                    "escalation_reason": None,
                    "created_at": now,
                    "updated_at": now,
                    "schedule": task.get("schedule"),
                    "combo": task.get("combo"),
                })

        if new_tasks:
            all_tasks = existing_tasks + new_tasks
            tasks_file.parent.mkdir(parents=True, exist_ok=True)
            tasks_file.write_text(json.dumps(all_tasks, indent=2))
            summary["tasks_created"] = len(new_tasks)

    # 3. Enable recommended combos
    combos = recipe_data.get("recommended_combos", [])
    if combos:
        summary["combos_enabled"] = combos

    # 4. Configure MCP servers
    servers = recipe_data.get("mcp_servers", [])
    if servers:
        mounts_file = brain_path / "mounts.json"
        existing_mounts = {}
        if mounts_file.exists():
            try:
                existing_mounts = json.loads(mounts_file.read_text())
                if not isinstance(existing_mounts, dict):
                    existing_mounts = {}
            except Exception:
                existing_mounts = {}

        for srv in servers:
            srv_name = srv.get("name", "")
            if srv_name and srv_name not in existing_mounts:
                existing_mounts[srv_name] = {
                    "transport": srv.get("transport", "stdio"),
                    "command": srv.get("command", ""),
                    "args": srv.get("args", []),
                    "status": "configured",
                    "source": f"recipe:{recipe_name}",
                }
                summary["mcp_servers_configured"] += 1

        if summary["mcp_servers_configured"] > 0:
            mounts_file.write_text(json.dumps(existing_mounts, indent=2))

    # 5. Apply brain_config overrides
    brain_config = recipe_data.get("brain_config", {})
    if brain_config:
        state_file = brain_path / "ledger" / "state.json"
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except Exception:
                state = {}
        state["recipe"] = recipe_name
        state["recipe_version"] = recipe_data.get("version", "0.0.0")
        if "mode" in brain_config:
            state["mode"] = brain_config["mode"]
        if "focus" in brain_config:
            state["current_focus"] = brain_config["focus"]
        state_file.write_text(json.dumps(state, indent=2))

    # 6. Save recipe manifest
    manifest_dir = brain_path / "recipes"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "recipe": recipe_name,
        "version": recipe_data.get("version", "0.0.0"),
        "installed_at": now,
        "source": recipe_data.get("_source_path", "unknown"),
    }
    (manifest_dir / f"{recipe_name}.json").write_text(json.dumps(manifest, indent=2))

    # 7. Collect first-run tips
    summary["tips"] = recipe_data.get("first_run_tips", [])

    return summary


def get_installed_recipes(brain_path: Path) -> List[Dict[str, Any]]:
    """List recipes installed in a brain directory."""
    recipes_dir = brain_path / "recipes"
    if not recipes_dir.exists():
        return []

    installed = []
    for f in sorted(recipes_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            installed.append(data)
        except Exception:
            pass
    return installed


def uninstall_recipe(brain_path: Path, recipe_name: str) -> Dict[str, Any]:
    """
    Remove recipe artifacts from a brain.
    Returns summary of what was removed.
    """
    summary = {
        "recipe": recipe_name,
        "engrams_removed": 0,
        "tasks_removed": 0,
    }

    # Remove engrams sourced from this recipe (mark deleted in JSONL ledger)
    ledger_file = brain_path / "engrams" / "ledger.jsonl"
    if ledger_file.exists():
        try:
            source_tag = f"recipe:{recipe_name}"
            lines = []
            removed = 0
            with open(ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        e = json.loads(line)
                        if e.get("source") == source_tag:
                            e["deleted"] = True
                            removed += 1
                        lines.append(json.dumps(e) + "\n")
                    except json.JSONDecodeError:
                        lines.append(line)
            with open(ledger_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            summary["engrams_removed"] = removed
        except Exception:
            pass

    # Remove tasks sourced from this recipe
    tasks_file = brain_path / "ledger" / "tasks.json"
    if tasks_file.exists():
        try:
            tasks = json.loads(tasks_file.read_text())
            source_tag = f"recipe:{recipe_name}"
            before = len(tasks)
            tasks = [t for t in tasks if t.get("source") != source_tag]
            summary["tasks_removed"] = before - len(tasks)
            tasks_file.write_text(json.dumps(tasks, indent=2))
        except Exception:
            pass

    # Remove manifest
    manifest = brain_path / "recipes" / f"{recipe_name}.json"
    if manifest.exists():
        manifest.unlink()

    return summary
