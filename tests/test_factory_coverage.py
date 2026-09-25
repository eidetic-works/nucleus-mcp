"""Comprehensive tests for factory module."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import factory
from mcp_server_nucleus.runtime.factory import (
    ESCALATION_KEYWORDS,
    PERSONAS,
    INTENT_KEYWORDS,
    _should_escalate_tier,
    classify_intent,
    get_persona_for_intent,
    ContextFactory,
)


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Create a temporary brain path."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    (bp / "agents").mkdir(exist_ok=True)
    (bp / "ledger").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


# ── _should_escalate_tier ────────────────────────────────────────

class TestShouldEscalateTier:
    def test_empty_intent(self):
        assert _should_escalate_tier("") is False

    def test_none_intent(self):
        assert _should_escalate_tier(None) is False

    def test_critical_keyword(self):
        assert _should_escalate_tier("This is CRITICAL") is True

    def test_security_keyword(self):
        assert _should_escalate_tier("security audit needed") is True

    def test_urgent_keyword(self):
        assert _should_escalate_tier("URGENT fix required") is True

    def test_emergency_keyword(self):
        assert _should_escalate_tier("emergency deployment") is True

    def test_high_priority_keyword(self):
        assert _should_escalate_tier("HIGH-PRIORITY task") is True

    def test_audit_keyword(self):
        assert _should_escalate_tier("AUDIT the system") is True

    def test_no_escalation(self):
        assert _should_escalate_tier("implement a feature") is False

    def test_case_insensitive(self):
        assert _should_escalate_tier("critical issue") is True
        assert _should_escalate_tier("Critical issue") is True
        assert _should_escalate_tier("CRITICAL issue") is True


# ── classify_intent ──────────────────────────────────────────────

class TestClassifyIntent:
    def test_orchestrate(self):
        assert classify_intent("start sprint for the team") == "orchestrate"

    def test_review(self):
        assert classify_intent("review the code") == "review"

    def test_implement(self):
        assert classify_intent("implement the feature") == "implement"

    def test_research(self):
        assert classify_intent("research the topic") == "research"

    def test_design(self):
        assert classify_intent("design the architecture") == "design"

    def test_strategy(self):
        assert classify_intent("decide on strategy") == "strategy"

    def test_deploy(self):
        assert classify_intent("deploy the service") == "deploy"

    def test_admin(self):
        assert classify_intent("add a task") == "admin"

    def test_groom(self):
        assert classify_intent("groom the backlog") == "groom"

    def test_retrieve(self):
        # "search memory" matches both "research" (search) and "retrieve" (search memory)
        # "search" appears in research keywords, "search memory" in retrieve
        # Both get 1 point, but research also has "find" - no, "search memory" has "search memory"
        # Actually "search" is in research keywords, and "search memory" is in retrieve
        # So "search memory for context" matches research (via "search") and retrieve (via "search memory")
        # Both get 1 match. max() returns first one encountered with max score.
        result = classify_intent("search memory for context")
        assert result in ("retrieve", "research")

    def test_no_match_defaults_admin(self):
        assert classify_intent("xyz random text") == "admin"

    def test_empty_string(self):
        assert classify_intent("") == "admin"

    def test_multiple_matches_picks_highest(self):
        # "review and audit" matches both review and admin
        result = classify_intent("review and audit")
        assert result in ("review", "admin")


# ── get_persona_for_intent ───────────────────────────────────────

class TestGetPersonaForIntent:
    def test_orchestrate(self):
        p = get_persona_for_intent("orchestrate")
        assert p["name"] == "Synthesizer"

    def test_review(self):
        p = get_persona_for_intent("review")
        assert p["name"] == "Critic"

    def test_implement(self):
        p = get_persona_for_intent("implement")
        assert p["name"] == "Developer"

    def test_research(self):
        p = get_persona_for_intent("research")
        assert p["name"] == "Researcher"

    def test_design(self):
        p = get_persona_for_intent("design")
        assert p["name"] == "Architect"

    def test_strategy(self):
        p = get_persona_for_intent("strategy")
        assert p["name"] == "Strategist"

    def test_deploy(self):
        p = get_persona_for_intent("deploy")
        assert p["name"] == "DevOps"

    def test_admin(self):
        p = get_persona_for_intent("admin")
        assert p["name"] == "Librarian"

    def test_retrieve(self):
        p = get_persona_for_intent("retrieve")
        assert p["name"] == "Librarian"

    def test_groom(self):
        p = get_persona_for_intent("groom")
        assert p["name"] == "Product Manager"

    def test_unknown_defaults_librarian(self):
        p = get_persona_for_intent("unknown_intent")
        assert p["name"] == "Librarian"


# ── ContextFactory ───────────────────────────────────────────────

class TestContextFactory:
    def test_init(self, brain_path):
        cf = ContextFactory(brain_path)
        assert cf._brain_path == brain_path
        assert cf._auditor is not None
        assert cf._plugin_loader is not None
        assert len(cf._registry) > 0

    def test_init_default_brain_path(self, brain_path, monkeypatch):
        # BRAIN_PATH was a module constant that froze NUCLEUS_BRAIN_PATH at
        # import; it is now resolved per call, so set the environment the
        # function actually reads rather than patching a frozen value.
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        cf = ContextFactory()
        assert cf._brain_path == brain_path

    def test_default_brain_path_is_read_live_not_frozen(self, tmp_path, monkeypatch):
        """OPPOSED: two different env values in one process must yield two
        different defaults. With the old module constant the second assert
        failed, which is the whole reason a test-collection-time import could
        own NUCLEUS_BRAIN_PATH for an entire session."""
        a, b = tmp_path / "a", tmp_path / "b"
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(a))
        assert ContextFactory()._brain_path == a
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
        assert ContextFactory()._brain_path == b

    def test_register(self, brain_path):
        cf = ContextFactory(brain_path)
        mock_cap = MagicMock()
        mock_cap.name = "test_cap"
        cf.register(mock_cap)
        assert "test_cap" in cf._registry

    def test_get_persona(self, brain_path):
        cf = ContextFactory(brain_path)
        p = cf.get_persona("librarian")
        assert p is not None
        assert p["name"] == "Librarian"

    def test_get_persona_case_insensitive(self, brain_path):
        cf = ContextFactory(brain_path)
        p = cf.get_persona("LIBRARIAN")
        assert p is not None
        assert p["name"] == "Librarian"

    def test_get_persona_not_found(self, brain_path):
        cf = ContextFactory(brain_path)
        assert cf.get_persona("nonexistent") is None

    def test_list_personas(self, brain_path):
        cf = ContextFactory(brain_path)
        personas = cf.list_personas()
        assert len(personas) > 0
        assert all("name" in p for p in personas)
        assert all("mode" in p for p in personas)

    def test_list_capabilities(self, brain_path):
        cf = ContextFactory(brain_path)
        caps = cf.list_capabilities()
        assert len(caps) > 0
        assert "brain_ops" in caps

    def test_clear_cache(self, brain_path):
        cf = ContextFactory(brain_path)
        cf._agent_cache["test"] = "value"
        cf.clear_cache()
        assert cf._agent_cache == {}

    def test_load_agent_prompt_not_found(self, brain_path):
        cf = ContextFactory(brain_path)
        result = cf.load_agent_prompt("nonexistent.md")
        assert result is None

    def test_load_agent_prompt_with_sections(self, brain_path):
        agent_file = brain_path / "agents" / "test.md"
        agent_file.write_text("""## IDENTITY
You are a test agent.

## CORE FUNCTIONS
- Do X
- Do Y

## CONSTRAINTS
- Don't do Z
""")
        cf = ContextFactory(brain_path)
        result = cf.load_agent_prompt("test.md")
        assert result is not None
        assert "test agent" in result
        assert "Do X" in result
        assert "Don't do Z" in result

    def test_load_agent_prompt_with_permissions_section(self, brain_path):
        agent_file = brain_path / "agents" / "test.md"
        agent_file.write_text("""## IDENTITY
Test agent

## PERMISSIONS
- Can read
- Can write
""")
        cf = ContextFactory(brain_path)
        result = cf.load_agent_prompt("test.md")
        assert result is not None
        assert "Can read" in result

    def test_load_agent_prompt_no_sections_returns_full(self, brain_path):
        agent_file = brain_path / "agents" / "test.md"
        agent_file.write_text("Just some text without sections")
        cf = ContextFactory(brain_path)
        result = cf.load_agent_prompt("test.md")
        assert result is not None
        assert "Just some text" in result

    def test_load_agent_prompt_cached(self, brain_path):
        agent_file = brain_path / "agents" / "test.md"
        agent_file.write_text("## IDENTITY\nTest")
        cf = ContextFactory(brain_path)
        result1 = cf.load_agent_prompt("test.md")
        # Modify file but should get cached result
        agent_file.write_text("## IDENTITY\nModified")
        result2 = cf.load_agent_prompt("test.md")
        assert result1 == result2

    def test_load_external_agent_exists(self, brain_path, tmp_path):
        ext_file = tmp_path / "external.md"
        ext_file.write_text("External agent definition")
        cf = ContextFactory(brain_path)
        result = cf.load_external_agent(str(ext_file))
        assert result == "External agent definition"

    def test_load_external_agent_not_found(self, brain_path):
        cf = ContextFactory(brain_path)
        result = cf.load_external_agent("/nonexistent/path.md")
        assert result is None

    def test_load_external_agent_exception(self, brain_path):
        cf = ContextFactory(brain_path)
        result = cf.load_external_agent(None)
        assert result is None

    def test_create_context(self, brain_path):
        cf = ContextFactory(brain_path)
        ctx = cf.create_context("session1", "implement the feature")
        assert ctx["session_id"] == "session1"
        assert ctx["intent"] == "implement the feature"
        assert ctx["intent_category"] == "implement"
        assert ctx["persona"] == "Developer"
        assert "tools" in ctx
        assert "system_prompt" in ctx
        assert "tool_count" in ctx

    def test_create_context_with_escalation(self, brain_path):
        cf = ContextFactory(brain_path)
        ctx = cf.create_context("session1", "CRITICAL security issue")
        assert ctx["job_type"] == "CRITICAL"

    def test_create_context_for_persona(self, brain_path):
        cf = ContextFactory(brain_path)
        ctx = cf.create_context_for_persona("session1", "critic", "review the code")
        assert ctx["persona"] == "Critic"
        assert ctx["intent_category"] == "direct"

    def test_create_context_for_persona_with_escalation(self, brain_path):
        cf = ContextFactory(brain_path)
        ctx = cf.create_context_for_persona("session1", "librarian", "URGENT task")
        assert ctx["job_type"] == "CRITICAL"

    def test_create_context_for_persona_unknown(self, brain_path):
        cf = ContextFactory(brain_path)
        ctx = cf.create_context_for_persona("session1", "nonexistent", "do something")
        assert ctx["persona"] == "Librarian"  # fallback

    def test_create_context_for_persona_with_external_prompt(self, brain_path):
        cf = ContextFactory(brain_path)
        ctx = cf.create_context_for_persona("session1", "critic", "review", external_prompt="Custom prompt")
        assert "Custom prompt" in ctx["system_prompt"]

    def test_generate_system_prompt_fast_mode(self, brain_path):
        cf = ContextFactory(brain_path)
        persona = PERSONAS["devops"]
        prompt = cf._generate_system_prompt("test intent", persona, ["render_ops"])
        assert "DevOps" in prompt
        assert "test intent" in prompt

    def test_generate_system_prompt_rich_mode(self, brain_path):
        agent_file = brain_path / "agents" / "test_rich.md"
        agent_file.write_text("## IDENTITY\nRich agent")
        cf = ContextFactory(brain_path)
        persona = {
            "name": "TestRich",
            "mode": "rich",
            "agent_file": "test_rich.md",
            "system_prompt_fragment": None,
        }
        prompt = cf._generate_system_prompt("test", persona, ["brain_ops"])
        assert "TestRich" in prompt
        assert "Rich agent" in prompt

    def test_generate_system_prompt_no_caps(self, brain_path):
        cf = ContextFactory(brain_path)
        persona = PERSONAS["devops"]
        prompt = cf._generate_system_prompt("test", persona, [])
        assert "None (Files Only)" in prompt

    def test_resolve_dynamic_context_no_rules(self, brain_path):
        cf = ContextFactory(brain_path)
        # context_rules.json may or may not exist
        result = cf._resolve_dynamic_context("test intent")
        assert isinstance(result, str)

    def test_resolve_dynamic_context_with_rules(self, brain_path, tmp_path):
        # Create context_rules.json in the package directory
        rules_path = Path(factory.__file__).parent / "context_rules.json"
        original_content = None
        if rules_path.exists():
            original_content = rules_path.read_text()
        try:
            rules_path.write_text(json.dumps([
                {"keywords": ["test"], "inject": ["test_doc.md"]}
            ]))
            # Create the doc file
            doc_path = brain_path.parent / "test_doc.md"
            doc_path.write_text("Test documentation content")
            cf = ContextFactory(brain_path)
            result = cf._resolve_dynamic_context("test something")
            assert "Test documentation" in result
        finally:
            if original_content is not None:
                rules_path.write_text(original_content)
            else:
                rules_path.unlink(missing_ok=True)

    def test_resolve_dynamic_context_truncation(self, brain_path, tmp_path):
        import json as json_mod
        rules_path = Path(factory.__file__).parent / "context_rules.json"
        original_content = None
        if rules_path.exists():
            original_content = rules_path.read_text()
        try:
            rules_path.write_text(json_mod.dumps([
                {"keywords": ["test"], "inject": ["big_doc.md"]}
            ]))
            doc_path = brain_path.parent / "big_doc.md"
            doc_path.write_text("x" * 20000)
            cf = ContextFactory(brain_path)
            result = cf._resolve_dynamic_context("test something")
            assert "TRUNCATED" in result
        finally:
            if original_content is not None:
                rules_path.write_text(original_content)
            else:
                rules_path.unlink(missing_ok=True)


# ── PERSONAS ─────────────────────────────────────────────────────

class TestPersonas:
    def test_all_personas_have_required_fields(self):
        for name, persona in PERSONAS.items():
            assert "name" in persona
            assert "mode" in persona
            assert "description" in persona
            assert "capabilities" in persona
            assert "job_type" in persona

    def test_persona_modes(self):
        for persona in PERSONAS.values():
            assert persona["mode"] in ("fast", "rich")

    def test_librarian_mode(self):
        assert PERSONAS["librarian"]["mode"] == "rich"

    def test_devops_mode(self):
        assert PERSONAS["devops"]["mode"] == "fast"

    def test_devops_has_fragment(self):
        assert PERSONAS["devops"]["system_prompt_fragment"] is not None

    def test_rich_personas_have_agent_file(self):
        for name, persona in PERSONAS.items():
            if persona["mode"] == "rich":
                assert persona["agent_file"] is not None
