"""
Tests for Phase 71: LLM-Based Tool Calling Enforcement
=======================================================
Tests all four components:
- LLMIntentAnalyzer
- LLMToolValidator
- LLMToolEnforcer
- LLMPatternLearner
- EnforcementOps (MCP capability)
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from mcp_server_nucleus.runtime.llm_intent_analyzer import (
    LLMIntentAnalyzer, IntentAnalysisResult, get_intent_analyzer
)
from mcp_server_nucleus.runtime.llm_tool_validator import (
    LLMToolValidator, ValidationResult, get_tool_validator
)
from mcp_server_nucleus.runtime.llm_tool_enforcer import (
    LLMToolEnforcer, EnforcementResult, get_tool_enforcer
)
from mcp_server_nucleus.runtime.llm_pattern_learner import (
    LLMPatternLearner, LearnedPattern, get_pattern_learner
)
from mcp_server_nucleus.runtime.capabilities.enforcement_ops import EnforcementOps


# ============================================================
# SAMPLE DATA
# ============================================================

SAMPLE_TOOLS = [
    {"name": "nucleus_tasks", "description": "Task + depth management facade"},
    {"name": "nucleus_engrams", "description": "Memory, health, version, morning brief facade"},
    {"name": "nucleus_governance", "description": "Governance, lock, audit, hypervisor facade"},
    {"name": "nucleus_sessions", "description": "Session management facade"},
    {"name": "nucleus_sync", "description": "Multi-agent sync facade"},
    {"name": "nucleus_orchestration", "description": "Core orchestration facade"},
    {"name": "nucleus_telemetry", "description": "Telemetry and metering facade"},
    {"name": "nucleus_slots", "description": "Slot management and sprints facade"},
    {"name": "nucleus_infra", "description": "Infrastructure and deployment facade"},
    {"name": "nucleus_agents", "description": "Agent management and code ops facade"},
    {"name": "nucleus_features", "description": "Feature map, mounter, proofs facade"},
    {"name": "nucleus_federation", "description": "Federation networking facade"},
]


# ============================================================
# INTENT ANALYZER TESTS
# ============================================================

class TestIntentAnalysisResult:
    """Tests for IntentAnalysisResult data class."""
    
    def test_has_requirements_true(self):
        result = IntentAnalysisResult(
            required_tools=["nucleus_tasks"],
            optional_tools=[],
            reasoning="test"
        )
        assert result.has_requirements() is True
    
    def test_has_requirements_false(self):
        result = IntentAnalysisResult(
            required_tools=[],
            optional_tools=["nucleus_tasks"],
            reasoning="test"
        )
        assert result.has_requirements() is False
    
    def test_to_dict(self):
        result = IntentAnalysisResult(
            required_tools=["nucleus_tasks"],
            optional_tools=["nucleus_engrams"],
            reasoning="User wants to add a task"
        )
        d = result.to_dict()
        assert d["required_tools"] == ["nucleus_tasks"]
        assert d["optional_tools"] == ["nucleus_engrams"]
        assert d["reasoning"] == "User wants to add a task"


class TestLLMIntentAnalyzer:
    """Tests for LLMIntentAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return LLMIntentAnalyzer()
    
    def test_empty_request(self, analyzer):
        result = analyzer.analyze("", SAMPLE_TOOLS)
        assert not result.has_requirements()
        assert result.reasoning == "Empty request"
    
    def test_no_tools(self, analyzer):
        result = analyzer.analyze("Add a task", [])
        assert not result.has_requirements()
        assert result.reasoning == "No tools available"
    
    def test_build_tool_descriptions(self, analyzer):
        desc = analyzer._build_tool_descriptions(SAMPLE_TOOLS)
        assert "nucleus_tasks" in desc
        assert "nucleus_engrams" in desc
    
    def test_keyword_fallback_add_task(self, analyzer):
        result = analyzer.analyze_without_llm("add task: buy groceries", SAMPLE_TOOLS)
        assert "nucleus_tasks" in result.required_tools
    
    def test_keyword_fallback_list_task(self, analyzer):
        result = analyzer.analyze_without_llm("list task items", SAMPLE_TOOLS)
        assert "nucleus_tasks" in result.required_tools
    
    def test_keyword_fallback_write_engram(self, analyzer):
        result = analyzer.analyze_without_llm("write engram about this decision", SAMPLE_TOOLS)
        assert "nucleus_engrams" in result.required_tools
    
    def test_keyword_fallback_checkpoint(self, analyzer):
        result = analyzer.analyze_without_llm("checkpoint current progress", SAMPLE_TOOLS)
        assert "nucleus_sessions" in result.required_tools
    
    def test_keyword_fallback_deploy(self, analyzer):
        result = analyzer.analyze_without_llm("deploy the application", SAMPLE_TOOLS)
        assert "nucleus_infra" in result.required_tools
    
    def test_keyword_fallback_no_match(self, analyzer):
        result = analyzer.analyze_without_llm("hello world", SAMPLE_TOOLS)
        assert len(result.required_tools) == 0
    
    def test_keyword_fallback_budget(self, analyzer):
        result = analyzer.analyze_without_llm("check budget spending", SAMPLE_TOOLS)
        assert "nucleus_telemetry" in result.required_tools
    
    def test_keyword_fallback_health(self, analyzer):
        result = analyzer.analyze_without_llm("check system health", SAMPLE_TOOLS)
        assert "nucleus_engrams" in result.required_tools
    
    def test_singleton(self):
        a1 = get_intent_analyzer()
        a2 = get_intent_analyzer()
        assert a1 is a2


# ============================================================
# TOOL VALIDATOR TESTS
# ============================================================

class TestValidationResult:
    """Tests for ValidationResult data class."""
    
    def test_passed(self):
        result = ValidationResult(
            passed=True,
            missing_tools=[],
            hallucinated_actions=[],
            reasoning="All tools called"
        )
        assert result.passed is True
        assert len(result.missing_tools) == 0
    
    def test_failed(self):
        result = ValidationResult(
            passed=False,
            missing_tools=["nucleus_tasks"],
            hallucinated_actions=["claimed to add task"],
            reasoning="Agent didn't call nucleus_tasks"
        )
        assert result.passed is False
        assert "nucleus_tasks" in result.missing_tools
    
    def test_to_dict(self):
        result = ValidationResult(
            passed=False,
            missing_tools=["nucleus_tasks"],
            hallucinated_actions=[],
            reasoning="Missing tool"
        )
        d = result.to_dict()
        assert d["validation_passed"] is False
        assert "nucleus_tasks" in d["missing_tools"]
        assert "timestamp" in d


class TestLLMToolValidator:
    """Tests for LLMToolValidator."""
    
    @pytest.fixture
    def validator(self):
        return LLMToolValidator()
    
    def test_no_requirements_passes(self, validator):
        result = validator.validate(
            user_request="hello",
            required_tools=[],
            tools_called=[],
            agent_response="Hello!"
        )
        assert result.passed is True
    
    def test_all_tools_called_passes(self, validator):
        result = validator.validate(
            user_request="add task",
            required_tools=["nucleus_tasks"],
            tools_called=["nucleus_tasks"],
            agent_response="Task added"
        )
        assert result.passed is True
    
    def test_missing_tools_fails(self, validator):
        # Force deterministic validation (no LLM)
        result = validator.validate_deterministic(
            required_tools=["nucleus_tasks"],
            tools_called=[]
        )
        assert result.passed is False
        assert "nucleus_tasks" in result.missing_tools
    
    def test_partial_tools_fails(self, validator):
        result = validator.validate_deterministic(
            required_tools=["nucleus_tasks", "nucleus_engrams"],
            tools_called=["nucleus_tasks"]
        )
        assert result.passed is False
        assert "nucleus_engrams" in result.missing_tools
        assert "nucleus_tasks" not in result.missing_tools
    
    def test_extra_tools_passes(self, validator):
        result = validator.validate_deterministic(
            required_tools=["nucleus_tasks"],
            tools_called=["nucleus_tasks", "nucleus_engrams"]
        )
        assert result.passed is True
    
    def test_singleton(self):
        v1 = get_tool_validator()
        v2 = get_tool_validator()
        assert v1 is v2


# ============================================================
# TOOL ENFORCER TESTS
# ============================================================

class TestEnforcementResult:
    """Tests for EnforcementResult data class."""
    
    def test_success(self):
        result = EnforcementResult(
            success=True,
            tools_required=["nucleus_tasks"],
            tools_called=["nucleus_tasks"],
            attempts=1
        )
        assert result.success is True
        assert result.attempts == 1
    
    def test_to_dict(self):
        result = EnforcementResult(
            success=False,
            tools_required=["nucleus_tasks"],
            tools_called=[],
            attempts=3
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["attempts"] == 3
        assert "timestamp" in d


class TestLLMToolEnforcer:
    """Tests for LLMToolEnforcer."""
    
    @pytest.fixture
    def enforcer(self):
        return LLMToolEnforcer(max_retries=2)
    
    def test_generate_enforcement_prompt_empty(self, enforcer):
        intent = IntentAnalysisResult([], [], "no requirements")
        prompt = enforcer.generate_enforcement_prompt(intent)
        assert prompt == ""
    
    def test_generate_enforcement_prompt_with_tools(self, enforcer):
        intent = IntentAnalysisResult(
            ["nucleus_tasks"], 
            ["nucleus_engrams"], 
            "User wants to add task"
        )
        prompt = enforcer.generate_enforcement_prompt(intent)
        assert "nucleus_tasks" in prompt
        assert "MUST" in prompt
        assert "REJECTED" in prompt
    
    def test_generate_retry_prompt_first(self, enforcer):
        validation = ValidationResult(
            passed=False,
            missing_tools=["nucleus_tasks"],
            hallucinated_actions=[],
            reasoning="Didn't call tool"
        )
        prompt = enforcer.generate_retry_prompt(validation, attempt=1)
        assert "REJECTED" in prompt
        assert "nucleus_tasks" in prompt
    
    def test_generate_retry_prompt_final(self, enforcer):
        validation = ValidationResult(
            passed=False,
            missing_tools=["nucleus_tasks"],
            hallucinated_actions=[],
            reasoning="Didn't call tool"
        )
        prompt = enforcer.generate_retry_prompt(validation, attempt=2)
        assert "FINAL WARNING" in prompt
        assert "LAST chance" in prompt
    
    def test_post_flight_passes(self, enforcer):
        result = enforcer.post_flight(
            user_request="add task",
            required_tools=["nucleus_tasks"],
            tools_called=["nucleus_tasks"],
            agent_response="Done"
        )
        assert result.passed is True
    
    def test_post_flight_no_requirements(self, enforcer):
        result = enforcer.post_flight(
            user_request="hello",
            required_tools=[],
            tools_called=[],
            agent_response="Hello!"
        )
        assert result.passed is True
    
    def test_record_outcome_success(self, enforcer):
        intent = IntentAnalysisResult(["nucleus_tasks"], [], "test")
        enforcer.record_outcome("add task", intent, ["nucleus_tasks"], True, 1)
        stats = enforcer.get_stats()
        assert stats["successes"] >= 1
    
    def test_record_outcome_failure(self, enforcer):
        intent = IntentAnalysisResult(["nucleus_tasks"], [], "test")
        enforcer.record_outcome("add task", intent, [], False, 2)
        stats = enforcer.get_stats()
        assert stats["failures"] >= 1
        assert len(enforcer.get_failure_log()) >= 1
    
    def test_get_stats(self, enforcer):
        stats = enforcer.get_stats()
        assert "total_enforcements" in stats
        assert "successes" in stats
        assert "failures" in stats
        assert "success_rate" in stats
    
    def test_singleton(self):
        e1 = get_tool_enforcer()
        e2 = get_tool_enforcer()
        assert e1 is e2


# ============================================================
# PATTERN LEARNER TESTS
# ============================================================

class TestLearnedPattern:
    """Tests for LearnedPattern data class."""
    
    def test_creation(self):
        p = LearnedPattern(
            tool_name="nucleus_tasks",
            trigger_phrases=["add task", "create task"],
            frequency=5,
            system_prompt_addition="When user says 'add task', call nucleus_tasks"
        )
        assert p.tool_name == "nucleus_tasks"
        assert p.frequency == 5
        assert "learned_at" in p.to_dict()
    
    def test_to_dict(self):
        p = LearnedPattern("nucleus_tasks", ["add task"], 3, "prompt text")
        d = p.to_dict()
        assert d["tool_name"] == "nucleus_tasks"
        assert d["frequency"] == 3


class TestLLMPatternLearner:
    """Tests for LLMPatternLearner."""
    
    @pytest.fixture
    def learner(self):
        # Use temp dir for patterns
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            learner = LLMPatternLearner(min_failures_for_analysis=2)
            learner._patterns_path = Path(tmpdir) / "metrics" / "learned_patterns.json"
            yield learner
            os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    
    def test_insufficient_data(self, learner):
        result = learner.analyze_failures([
            {"user_request": "add task", "required_tools": ["nucleus_tasks"], 
             "tools_called": [], "success": False}
        ])
        assert result["status"] == "insufficient_data"
    
    def test_deterministic_analysis(self, learner):
        failures = [
            {"user_request": "add task", "required_tools": ["nucleus_tasks"], 
             "tools_called": [], "success": False},
            {"user_request": "add another task", "required_tools": ["nucleus_tasks"],
             "tools_called": [], "success": False},
            {"user_request": "list tasks", "required_tools": ["nucleus_tasks"],
             "tools_called": [], "success": False},
        ]
        result = learner._analyze_deterministic(failures)
        assert result["status"] == "deterministic_fallback"
        assert result["patterns_learned"] >= 1
        
        # Check that nucleus_tasks pattern has higher frequency
        patterns = result["patterns"]
        tasks_pattern = [p for p in patterns if p["tool_name"] == "nucleus_tasks"]
        assert len(tasks_pattern) == 1
        assert tasks_pattern[0]["frequency"] == 3
    
    def test_system_prompt_enhancement_empty(self, learner):
        prompt = learner.get_system_prompt_enhancement()
        assert prompt == ""
    
    def test_system_prompt_enhancement_with_patterns(self, learner):
        learner._learned_patterns.append(LearnedPattern(
            "nucleus_tasks", ["add task"], 5, "Call nucleus_tasks for task additions"
        ))
        prompt = learner.get_system_prompt_enhancement()
        assert "nucleus_tasks" in prompt
        assert "LEARNED TOOL CALLING PATTERNS" in prompt
    
    def test_save_and_load_patterns(self, learner):
        learner._learned_patterns.append(LearnedPattern(
            "nucleus_tasks", ["add task"], 3, "test prompt"
        ))
        learner._save_patterns()
        
        # Create new learner to test loading
        new_learner = LLMPatternLearner(min_failures_for_analysis=2)
        new_learner._patterns_path = learner._patterns_path
        new_learner._learned_patterns = []
        new_learner._load_patterns()
        
        assert len(new_learner._learned_patterns) == 1
        assert new_learner._learned_patterns[0].tool_name == "nucleus_tasks"
    
    def test_get_patterns(self, learner):
        learner._learned_patterns.append(LearnedPattern(
            "nucleus_tasks", ["add task"], 3, "test"
        ))
        patterns = learner.get_patterns()
        assert len(patterns) == 1
        assert patterns[0]["tool_name"] == "nucleus_tasks"
    
    def test_get_stats(self, learner):
        stats = learner.get_stats()
        assert "total_patterns" in stats
        assert "unique_tools" in stats
    
    def test_singleton(self):
        l1 = get_pattern_learner()
        l2 = get_pattern_learner()
        assert l1 is l2


# ============================================================
# ENFORCEMENT OPS (MCP CAPABILITY) TESTS
# ============================================================

class TestEnforcementOps:
    """Tests for EnforcementOps MCP capability."""
    
    @pytest.fixture
    def ops(self):
        return EnforcementOps()
    
    def test_get_tools(self, ops):
        tools = ops.get_tools()
        assert len(tools) == 4
        names = [t["name"] for t in tools]
        assert "brain_enforcement_stats" in names
        assert "brain_enforcement_patterns" in names
        assert "brain_enforcement_analyze" in names
        assert "brain_enforcement_test" in names
    
    def test_name_property(self, ops):
        assert ops.name == "enforcement_ops"
    
    def test_description_property(self, ops):
        assert "enforcement" in ops.description.lower()
    
    def test_stats(self, ops):
        result = ops.execute("brain_enforcement_stats", {})
        assert "enforcer" in result
        assert "learner" in result
    
    def test_patterns(self, ops):
        result = ops.execute("brain_enforcement_patterns", {})
        assert "patterns" in result
        assert "pattern_count" in result
    
    def test_analyze_no_failures(self, ops):
        result = ops.execute("brain_enforcement_analyze", {})
        assert result["status"] == "no_failures"
    
    def test_test_intent_add_task(self, ops):
        result = ops.execute("brain_enforcement_test", {"request": "add task: buy groceries"})
        assert "nucleus_tasks" in result["required_tools"]
    
    def test_test_intent_empty(self, ops):
        result = ops.execute("brain_enforcement_test", {"request": ""})
        assert "error" in result
    
    def test_test_intent_health(self, ops):
        result = ops.execute("brain_enforcement_test", {"request": "check system health"})
        assert "nucleus_engrams" in result["required_tools"]
    
    def test_unknown_tool(self, ops):
        result = ops.execute("brain_unknown_tool", {})
        assert "error" in result


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestEnforcementIntegration:
    """Integration tests for the full enforcement flow."""
    
    def test_full_enforcement_flow_pass(self):
        """Test: Intent analysis → enforcement prompt → validation passes."""
        enforcer = LLMToolEnforcer()
        
        # Step 1: Analyze intent (using keyword fallback)
        analyzer = LLMIntentAnalyzer()
        intent = analyzer.analyze_without_llm("add task: test item", SAMPLE_TOOLS)
        assert "nucleus_tasks" in intent.required_tools
        
        # Step 2: Generate enforcement prompt
        prompt = enforcer.generate_enforcement_prompt(intent)
        assert "nucleus_tasks" in prompt
        
        # Step 3: Simulate agent calling the tool
        tools_called = ["nucleus_tasks"]
        
        # Step 4: Post-flight validation
        validation = enforcer.post_flight(
            user_request="add task: test item",
            required_tools=intent.required_tools,
            tools_called=tools_called,
            agent_response="Task added successfully"
        )
        assert validation.passed is True
        
        # Step 5: Record outcome
        enforcer.record_outcome("add task: test item", intent, tools_called, True, 1)
    
    def test_full_enforcement_flow_fail_then_retry(self):
        """Test: Intent analysis → enforcement → validation fails → retry prompt."""
        enforcer = LLMToolEnforcer()
        
        # Step 1: Analyze intent
        analyzer = LLMIntentAnalyzer()
        intent = analyzer.analyze_without_llm("add task: test item", SAMPLE_TOOLS)
        
        # Step 2: Simulate agent NOT calling the tool
        tools_called = []
        
        # Step 3: Post-flight validation (should fail)
        validation = enforcer.post_flight(
            user_request="add task: test item",
            required_tools=intent.required_tools,
            tools_called=tools_called,
            agent_response="I've added the task"
        )
        assert validation.passed is False
        
        # Step 4: Generate retry prompt
        retry_prompt = enforcer.generate_retry_prompt(validation, attempt=1)
        assert "REJECTED" in retry_prompt
        assert "nucleus_tasks" in retry_prompt
        
        # Step 5: Simulate retry (agent calls tool this time)
        tools_called_retry = ["nucleus_tasks"]
        validation_retry = enforcer.post_flight(
            user_request="add task: test item",
            required_tools=intent.required_tools,
            tools_called=tools_called_retry,
            agent_response="Task added"
        )
        assert validation_retry.passed is True
    
    def test_pattern_learning_from_failures(self):
        """Test: Record failures → learn patterns → generate prompt enhancement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            learner = LLMPatternLearner(min_failures_for_analysis=2)
            learner._patterns_path = Path(tmpdir) / "metrics" / "learned_patterns.json"
            
            failures = [
                {"user_request": "add task: item 1", "required_tools": ["nucleus_tasks"],
                 "tools_called": [], "success": False},
                {"user_request": "add task: item 2", "required_tools": ["nucleus_tasks"],
                 "tools_called": [], "success": False},
                {"user_request": "add task: item 3", "required_tools": ["nucleus_tasks"],
                 "tools_called": [], "success": False},
            ]
            
            result = learner._analyze_deterministic(failures)
            assert result["patterns_learned"] >= 1
            
            # Get system prompt enhancement
            prompt = learner.get_system_prompt_enhancement()
            assert "nucleus_tasks" in prompt
            
            os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    
    def test_enforcement_stats_tracking(self):
        """Test: Stats are tracked correctly across multiple enforcements."""
        enforcer = LLMToolEnforcer()
        intent = IntentAnalysisResult(["nucleus_tasks"], [], "test")
        
        # Record 3 successes and 2 failures
        for _ in range(3):
            enforcer.record_outcome("add task", intent, ["nucleus_tasks"], True, 1)
        for _ in range(2):
            enforcer.record_outcome("add task", intent, [], False, 2)
        
        stats = enforcer.get_stats()
        assert stats["successes"] >= 3
        assert stats["failures"] >= 2
        assert stats["success_rate"] > 0
