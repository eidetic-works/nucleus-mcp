"""
Tests for the interactive onboarding wizard.

Tests project detection, persona selection, context seeding,
and configuration output.
"""

import json
import os
import sys
import types
import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Isolated import ──────────────────────────────────────────────

SRC = Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "runtime"


def _load_onboarding():
    spec = importlib.util.spec_from_file_location("onboarding", str(SRC / "onboarding.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


onboarding = _load_onboarding()


# ── Project Detection ────────────────────────────────────────────

class TestDetectProject:
    def test_detects_python_project(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
        result = onboarding.detect_project(tmp_path)
        assert "python" in result["languages"]
        assert result["name"] == "myapp"

    def test_detects_node_project(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "my-node-app"}')
        result = onboarding.detect_project(tmp_path)
        assert "node" in result["languages"]
        assert result["name"] == "my-node-app"

    def test_detects_rust_project(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "my-crate"\n')
        result = onboarding.detect_project(tmp_path)
        assert "rust" in result["languages"]
        assert result["name"] == "my-crate"

    def test_detects_go_project(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/mymod\n")
        result = onboarding.detect_project(tmp_path)
        assert "go" in result["languages"]

    def test_detects_multiple_languages(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "multi"\n')
        (tmp_path / "package.json").write_text('{"name": "multi"}')
        result = onboarding.detect_project(tmp_path)
        assert "python" in result["languages"]
        assert "node" in result["languages"]

    def test_no_language_detected(self, tmp_path):
        result = onboarding.detect_project(tmp_path)
        assert result["languages"] == []
        assert result["name"] == tmp_path.name

    def test_detects_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = onboarding.detect_project(tmp_path)
        assert result["git"] is True

    def test_no_git(self, tmp_path):
        result = onboarding.detect_project(tmp_path)
        assert result["git"] is False


# ── Extract Project Name ─────────────────────────────────────────

class TestExtractProjectName:
    def test_from_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "cool-app"\n')
        assert onboarding._extract_project_name(tmp_path) == "cool-app"

    def test_from_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "@scope/pkg"}')
        assert onboarding._extract_project_name(tmp_path) == "@scope/pkg"

    def test_from_cargo_toml(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "rustlib"\n')
        assert onboarding._extract_project_name(tmp_path) == "rustlib"

    def test_returns_none_when_no_manifest(self, tmp_path):
        assert onboarding._extract_project_name(tmp_path) is None


# ── Seed Project Context ─────────────────────────────────────────

class TestSeedProjectContext:
    def test_creates_context_md(self, tmp_path):
        brain = tmp_path / "test_brain"
        brain.mkdir()
        (brain / "memory").mkdir()
        (brain / "memory" / "engrams.json").write_text("[]")

        config = {
            "project_name": "test-proj",
            "project_description": "A test project for testing",
            "languages": ["python", "node"],
            "persona": "developer",
            "git_remote": "https://github.com/test/test",
        }
        onboarding.seed_project_context(brain, config)

        context = (brain / "memory" / "context.md").read_text()
        assert "test-proj" in context
        assert "A test project" in context
        assert "Python" in context
        assert "Node.js" in context
        assert "github.com" in context

    def test_creates_engram(self, tmp_path):
        brain = tmp_path / "test_brain"
        brain.mkdir()
        (brain / "memory").mkdir()
        (brain / "memory" / "engrams.json").write_text("[]")

        config = {
            "project_name": "engram-test",
            "project_description": "",
            "languages": ["rust"],
            "persona": "sre",
        }
        onboarding.seed_project_context(brain, config)

        engrams = json.loads((brain / "memory" / "engrams.json").read_text())
        assert len(engrams) == 1
        assert "engram-test" in engrams[0]["content"]
        assert "onboarding" in engrams[0]["tags"]

    def test_appends_to_existing_engrams(self, tmp_path):
        brain = tmp_path / "test_brain"
        brain.mkdir()
        (brain / "memory").mkdir()
        existing = [{"id": "existing", "content": "old", "tags": []}]
        (brain / "memory" / "engrams.json").write_text(json.dumps(existing))

        config = {
            "project_name": "append-test",
            "project_description": "",
            "languages": [],
            "persona": "developer",
        }
        onboarding.seed_project_context(brain, config)

        engrams = json.loads((brain / "memory" / "engrams.json").read_text())
        assert len(engrams) == 2
        assert engrams[0]["id"] == "existing"


# ── Personas ─────────────────────────────────────────────────────

class TestPersonas:
    def test_all_personas_have_required_keys(self):
        for key, persona in onboarding.PERSONAS.items():
            assert "label" in persona
            assert "description" in persona
            assert "template" in persona
            assert persona["template"] in ("default", "solo")

    def test_developer_is_default(self):
        assert "developer" in onboarding.PERSONAS

    def test_researcher_uses_solo_template(self):
        assert onboarding.PERSONAS["researcher"]["template"] == "solo"


# ── Ask Functions (non-interactive) ──────────────────────────────

class TestAskFunctions:
    def test_ask_choice_returns_default_non_interactive(self):
        options = [
            {"key": "a", "label": "Option A"},
            {"key": "b", "label": "Option B"},
        ]
        # stdin.isatty() returns False in tests
        result = onboarding._ask_choice("Pick one", options, default=1)
        assert result == "b"

    def test_ask_text_returns_default_non_interactive(self):
        result = onboarding._ask_text("Enter something", default="fallback")
        assert result == "fallback"
