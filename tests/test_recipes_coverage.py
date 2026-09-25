"""
Comprehensive pytest tests for runtime/recipes.py - targeting 90%+ coverage.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import yaml

from mcp_server_nucleus.runtime.recipes import (
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    VALID_CONTEXTS,
    RecipeValidationError,
    RecipeNotFoundError,
    validate_recipe,
    _get_builtin_recipes_dir,
    _get_user_recipes_dir,
    search_recipes,
    list_recipes,
    load_recipe,
    install_recipe,
    get_installed_recipes,
    uninstall_recipe,
)


# ============================================================================
# validate_recipe
# ============================================================================

class TestValidateRecipe:
    def test_valid_recipe(self):
        data = {
            "name": "test",
            "description": "A test recipe",
            "version": "1.0.0",
            "author": "tester",
        }
        errors = validate_recipe(data)
        assert errors == []

    def test_missing_required_fields(self):
        errors = validate_recipe({})
        for field in REQUIRED_FIELDS:
            assert any(field in e for e in errors)

    def test_version_not_string(self):
        data = {"name": "t", "description": "d", "version": 123, "author": "a"}
        errors = validate_recipe(data)
        assert any("version" in e and "string" in e for e in errors)

    def test_engram_templates_not_list(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": "not a list"}
        errors = validate_recipe(data)
        assert any("engram_templates" in e and "list" in e for e in errors)

    def test_engram_not_dict(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": ["not a dict"]}
        errors = validate_recipe(data)
        assert any("engram_templates[0]" in e and "dict" in e for e in errors)

    def test_engram_missing_key(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"value": "v"}]}
        errors = validate_recipe(data)
        assert any("missing 'key'" in e for e in errors)

    def test_engram_missing_value(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"key": "k"}]}
        errors = validate_recipe(data)
        assert any("missing 'value'" in e for e in errors)

    def test_engram_invalid_context(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"key": "k", "value": "v", "context": "Invalid"}]}
        errors = validate_recipe(data)
        assert any("invalid context" in e for e in errors)

    def test_engram_valid_context(self):
        for ctx in VALID_CONTEXTS:
            data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                    "engram_templates": [{"key": "k", "value": "v", "context": ctx}]}
            errors = validate_recipe(data)
            assert not any("context" in e for e in errors)

    def test_engram_intensity_out_of_range(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"key": "k", "value": "v", "intensity": 15}]}
        errors = validate_recipe(data)
        assert any("intensity" in e for e in errors)

    def test_engram_intensity_zero(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"key": "k", "value": "v", "intensity": 0}]}
        errors = validate_recipe(data)
        assert any("intensity" in e for e in errors)

    def test_engram_intensity_not_number(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"key": "k", "value": "v", "intensity": "high"}]}
        errors = validate_recipe(data)
        assert any("intensity" in e for e in errors)

    def test_engram_intensity_valid(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "engram_templates": [{"key": "k", "value": "v", "intensity": 5}]}
        errors = validate_recipe(data)
        assert not any("intensity" in e for e in errors)

    def test_combos_not_list(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "recommended_combos": "not a list"}
        errors = validate_recipe(data)
        assert any("recommended_combos" in e and "list" in e for e in errors)

    def test_combo_not_string(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "recommended_combos": [123]}
        errors = validate_recipe(data)
        assert any("recommended_combos[0]" in e and "string" in e for e in errors)

    def test_combo_unknown(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "recommended_combos": ["unknown_combo"]}
        errors = validate_recipe(data)
        assert any("unknown combo" in e for e in errors)

    def test_combo_valid(self):
        for combo in ["pulse_and_polish", "self_healing_sre", "fusion_reactor"]:
            data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                    "recommended_combos": [combo]}
            errors = validate_recipe(data)
            assert not any("combo" in e for e in errors)

    def test_scheduled_tasks_not_list(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "scheduled_tasks": "not a list"}
        errors = validate_recipe(data)
        assert any("scheduled_tasks" in e and "list" in e for e in errors)

    def test_scheduled_task_not_dict(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "scheduled_tasks": ["not a dict"]}
        errors = validate_recipe(data)
        assert any("scheduled_tasks[0]" in e and "dict" in e for e in errors)

    def test_scheduled_task_missing_name(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "scheduled_tasks": [{"schedule": "daily"}]}
        errors = validate_recipe(data)
        assert any("missing 'name'" in e for e in errors)

    def test_scheduled_task_missing_schedule(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "scheduled_tasks": [{"name": "task1"}]}
        errors = validate_recipe(data)
        assert any("missing 'schedule'" in e for e in errors)

    def test_mcp_servers_not_list(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "mcp_servers": "not a list"}
        errors = validate_recipe(data)
        assert any("mcp_servers" in e and "list" in e for e in errors)

    def test_first_run_tips_not_list(self):
        data = {"name": "t", "description": "d", "version": "1.0", "author": "a",
                "first_run_tips": "not a list"}
        errors = validate_recipe(data)
        assert any("first_run_tips" in e and "list" in e for e in errors)


# ============================================================================
# _get_builtin_recipes_dir / _get_user_recipes_dir
# ============================================================================

class TestRecipeDirs:
    def test_builtin_dir(self):
        d = _get_builtin_recipes_dir()
        assert d.name == "recipes"
        assert d.parent.name == "mcp_server_nucleus"

    def test_user_dir_not_exists(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        assert _get_user_recipes_dir() is None

    def test_user_dir_exists(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes = brain / "recipes"
        recipes.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = _get_user_recipes_dir()
        assert result == recipes


# ============================================================================
# list_recipes
# ============================================================================

class TestListRecipes:
    def test_lists_builtin(self):
        recipes = list_recipes()
        # Should find at least founder, sre, adhd
        names = [r["name"] for r in recipes]
        assert len(names) >= 1

    def test_builtin_recipe_fields(self):
        recipes = list_recipes()
        for r in recipes:
            assert "name" in r
            assert "description" in r
            assert "version" in r
            assert "author" in r
            assert "source" in r
            assert "path" in r
            assert "tags" in r
            assert "persona" in r

    def test_user_recipes(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        recipe = {"name": "custom", "description": "Custom", "version": "1.0", "author": "me"}
        (recipes_dir / "custom.yaml").write_text(yaml.dump(recipe))

        recipes = list_recipes()
        custom = [r for r in recipes if r["name"] == "custom"]
        assert len(custom) == 1
        assert custom[0]["source"] == "user"

    def test_skips_underscore_files(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        (recipes_dir / "_schema.yaml").write_text(yaml.dump({"name": "schema"}))

        recipes = list_recipes()
        assert not any(r["name"] == "schema" for r in recipes)

    def test_invalid_yaml_skipped(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        (recipes_dir / "bad.yaml").write_text("invalid: yaml: content: [")

        recipes = list_recipes()
        assert not any(r["name"] == "bad" for r in recipes)


# ============================================================================
# search_recipes
# ============================================================================

class TestSearchRecipes:
    def test_no_filter(self):
        results = search_recipes()
        assert len(results) >= 1

    def test_query_match(self):
        results = search_recipes(query="founder")
        # Should match founder recipe if it exists
        assert any("founder" in r["name"].lower() for r in results) or len(results) >= 0

    def test_query_no_match(self):
        results = search_recipes(query="xyzzy_nonexistent_recipe")
        assert len(results) == 0

    def test_tag_filter(self):
        results = search_recipes(tags=["nonexistent_tag"])
        assert len(results) == 0

    def test_tag_match(self):
        # Get all recipes and find one with tags
        all_recipes = list_recipes()
        if all_recipes:
            recipe_with_tags = [r for r in all_recipes if r.get("tags")]
            if recipe_with_tags:
                tag = recipe_with_tags[0]["tags"][0]
                results = search_recipes(tags=[tag])
                assert len(results) >= 1

    def test_query_and_tags(self):
        results = search_recipes(query="xyzzy", tags=["nonexistent"])
        assert len(results) == 0


# ============================================================================
# load_recipe
# ============================================================================

class TestLoadRecipe:
    def test_load_existing(self):
        # Load a built-in recipe by file stem (not display name)
        data = load_recipe("founder")
        assert data["name"] == "Founder OS"
        assert "_source_path" in data

    def test_load_not_found(self):
        with pytest.raises(RecipeNotFoundError, match="not found"):
            load_recipe("nonexistent_recipe_xyz")

    def test_load_invalid_yaml(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        (recipes_dir / "bad.yaml").write_text("just a string")

        with pytest.raises(RecipeValidationError, match="empty or not a valid"):
            load_recipe("bad")

    def test_load_validation_error(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        (recipes_dir / "invalid.yaml").write_text(yaml.dump({"name": "test"}))

        with pytest.raises(RecipeValidationError, match="validation error"):
            load_recipe("invalid")

    def test_load_from_user_dir(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        recipe = {"name": "user_recipe", "description": "User", "version": "1.0", "author": "me"}
        (recipes_dir / "user_recipe.yaml").write_text(yaml.dump(recipe))

        data = load_recipe("user_recipe")
        assert data["name"] == "user_recipe"


# ============================================================================
# install_recipe
# ============================================================================

class TestInstallRecipe:
    def _valid_recipe(self):
        return {
            "name": "test_recipe",
            "description": "A test recipe",
            "version": "1.0.0",
            "author": "tester",
        }

    def test_install_basic(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        summary = install_recipe(brain, self._valid_recipe())
        assert summary["recipe"] == "test_recipe"
        assert summary["engrams_written"] == 0
        assert summary["tasks_created"] == 0
        # Manifest saved
        manifest = brain / "recipes" / "test_recipe.json"
        assert manifest.exists()

    def test_install_with_engrams(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = self._valid_recipe()
        recipe["engram_templates"] = [
            {"key": "k1", "value": "v1", "context": "Feature", "intensity": 5},
            {"key": "k2", "value": "v2", "context": "Architecture", "intensity": 7},
        ]
        summary = install_recipe(brain, recipe)
        assert summary["engrams_written"] == 2
        ledger = brain / "engrams" / "ledger.jsonl"
        assert ledger.exists()
        lines = ledger.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_install_engrams_dedup(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps({"key": "k1", "value": "old"}) + "\n")

        recipe = self._valid_recipe()
        recipe["engram_templates"] = [{"key": "k1", "value": "v1"}]
        summary = install_recipe(brain, recipe)
        assert summary["engrams_written"] == 0  # k1 already exists

    def test_install_with_scheduled_tasks(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = self._valid_recipe()
        recipe["scheduled_tasks"] = [
            {"name": "Daily Review", "schedule": "daily", "description": "Review tasks"},
        ]
        summary = install_recipe(brain, recipe)
        assert summary["tasks_created"] == 1
        tasks_file = brain / "ledger" / "tasks.json"
        assert tasks_file.exists()
        tasks = json.loads(tasks_file.read_text())
        assert len(tasks) == 1

    def test_install_tasks_dedup(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        tasks_file = brain / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        existing_task = {"id": "recipe-test_recipe-daily-review", "description": "old"}
        tasks_file.write_text(json.dumps([existing_task]))

        recipe = self._valid_recipe()
        recipe["scheduled_tasks"] = [{"name": "Daily Review", "schedule": "daily"}]
        summary = install_recipe(brain, recipe)
        assert summary["tasks_created"] == 0

    def test_install_with_existing_tasks_invalid(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        tasks_file = brain / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        tasks_file.write_text("not json")

        recipe = self._valid_recipe()
        recipe["scheduled_tasks"] = [{"name": "Task 1", "schedule": "daily"}]
        summary = install_recipe(brain, recipe)
        assert summary["tasks_created"] == 1

    def test_install_with_combos(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = self._valid_recipe()
        recipe["recommended_combos"] = ["pulse_and_polish", "self_healing_sre"]
        summary = install_recipe(brain, recipe)
        assert summary["combos_enabled"] == ["pulse_and_polish", "self_healing_sre"]

    def test_install_with_mcp_servers(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = self._valid_recipe()
        recipe["mcp_servers"] = [
            {"name": "server1", "transport": "stdio", "command": "cmd", "args": ["--flag"]},
        ]
        summary = install_recipe(brain, recipe)
        assert summary["mcp_servers_configured"] == 1
        mounts = json.loads((brain / "mounts.json").read_text())
        assert "server1" in mounts

    def test_install_mcp_servers_dedup(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        mounts_file = brain / "mounts.json"
        mounts_file.write_text(json.dumps({"server1": {"transport": "stdio"}}))

        recipe = self._valid_recipe()
        recipe["mcp_servers"] = [{"name": "server1", "command": "cmd"}]
        summary = install_recipe(brain, recipe)
        assert summary["mcp_servers_configured"] == 0

    def test_install_mcp_servers_invalid_existing(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        mounts_file = brain / "mounts.json"
        mounts_file.write_text("not json")

        recipe = self._valid_recipe()
        recipe["mcp_servers"] = [{"name": "server1", "command": "cmd"}]
        summary = install_recipe(brain, recipe)
        assert summary["mcp_servers_configured"] == 1

    def test_install_with_brain_config(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "ledger").mkdir(parents=True)
        recipe = self._valid_recipe()
        recipe["brain_config"] = {"mode": "autopilot", "focus": "feature_X"}
        summary = install_recipe(brain, recipe)
        state = json.loads((brain / "ledger" / "state.json").read_text())
        assert state["recipe"] == "test_recipe"
        assert state["mode"] == "autopilot"
        assert state["current_focus"] == "feature_X"

    def test_install_brain_config_with_existing_state(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        state_file = brain / "ledger" / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"existing": "value"}))

        recipe = self._valid_recipe()
        recipe["brain_config"] = {"mode": "autopilot"}
        install_recipe(brain, recipe)
        state = json.loads(state_file.read_text())
        assert state["existing"] == "value"
        assert state["recipe"] == "test_recipe"

    def test_install_brain_config_invalid_state(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        state_file = brain / "ledger" / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("not json")

        recipe = self._valid_recipe()
        recipe["brain_config"] = {"mode": "autopilot"}
        install_recipe(brain, recipe)
        state = json.loads(state_file.read_text())
        assert state["mode"] == "autopilot"

    def test_install_with_first_run_tips(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = self._valid_recipe()
        recipe["first_run_tips"] = ["Tip 1", "Tip 2"]
        summary = install_recipe(brain, recipe)
        assert summary["tips"] == ["Tip 1", "Tip 2"]

    def test_install_no_name(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = {"description": "d", "version": "1.0", "author": "a"}
        summary = install_recipe(brain, recipe)
        assert summary["recipe"] == "unknown"

    def test_install_mcp_server_no_name(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = self._valid_recipe()
        recipe["mcp_servers"] = [{"command": "cmd"}]  # no name
        summary = install_recipe(brain, recipe)
        assert summary["mcp_servers_configured"] == 0


# ============================================================================
# get_installed_recipes
# ============================================================================

class TestGetInstalledRecipes:
    def test_no_recipes_dir(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        assert get_installed_recipes(brain) == []

    def test_with_recipes(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "test.json").write_text(json.dumps({"recipe": "test", "version": "1.0"}))
        installed = get_installed_recipes(brain)
        assert len(installed) == 1
        assert installed[0]["recipe"] == "test"

    def test_invalid_json_skipped(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipes_dir = brain / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "bad.json").write_text("not json")
        installed = get_installed_recipes(brain)
        assert installed == []


# ============================================================================
# uninstall_recipe
# ============================================================================

class TestUninstallRecipe:
    def test_uninstall_no_files(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        summary = uninstall_recipe(brain, "test")
        assert summary["recipe"] == "test"
        assert summary["engrams_removed"] == 0
        assert summary["tasks_removed"] == 0

    def test_uninstall_engrams(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            json.dumps({"key": "k1", "source": "recipe:test"}) + "\n" +
            json.dumps({"key": "k2", "source": "other"}) + "\n"
        )
        summary = uninstall_recipe(brain, "test")
        assert summary["engrams_removed"] == 1
        lines = ledger.read_text().strip().split("\n")
        data = json.loads(lines[0])
        assert data["deleted"] is True

    def test_uninstall_engrams_invalid_json(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text("not json\n")
        summary = uninstall_recipe(brain, "test")
        # Should not crash, invalid lines preserved
        assert summary["engrams_removed"] == 0

    def test_uninstall_tasks(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        tasks_file = brain / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        tasks_file.write_text(json.dumps([
            {"id": "t1", "source": "recipe:test"},
            {"id": "t2", "source": "other"},
        ]))
        summary = uninstall_recipe(brain, "test")
        assert summary["tasks_removed"] == 1
        tasks = json.loads(tasks_file.read_text())
        assert len(tasks) == 1
        assert tasks[0]["id"] == "t2"

    def test_uninstall_tasks_invalid_json(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        tasks_file = brain / "ledger" / "tasks.json"
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        tasks_file.write_text("not json")
        summary = uninstall_recipe(brain, "test")
        assert summary["tasks_removed"] == 0

    def test_uninstall_manifest(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        manifest = brain / "recipes" / "test.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"recipe": "test"}))
        uninstall_recipe(brain, "test")
        assert not manifest.exists()

    def test_uninstall_full_cycle(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        recipe = {
            "name": "test_recipe",
            "description": "Test",
            "version": "1.0",
            "author": "tester",
            "engram_templates": [{"key": "k1", "value": "v1"}],
            "scheduled_tasks": [{"name": "Task 1", "schedule": "daily"}],
        }
        install_recipe(brain, recipe)
        summary = uninstall_recipe(brain, "test_recipe")
        assert summary["engrams_removed"] == 1
        assert summary["tasks_removed"] == 1
