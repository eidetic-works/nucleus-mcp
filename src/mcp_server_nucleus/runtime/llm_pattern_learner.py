"""
LLM-Based Pattern Learner
===========================
Phase 71: Tool Calling Enforcement Layer

Uses LLM to analyze tool calling failures and generate system prompt improvements.
Learns from past failures to prevent future ones.

Stores learned patterns as engrams for persistent memory.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("nucleus.pattern_learner")

DEFAULT_LEARNING_MODEL = "gemini-2.0-flash-exp"

# Phase 73: Resilience imports (lazy)
def _get_resilient_client():
    from .llm_resilience import get_resilient_llm_client
    return get_resilient_llm_client()

def _get_file_ops():
    from .file_resilience import get_resilient_file_ops
    return get_resilient_file_ops()

def _get_telemetry():
    from .error_telemetry import get_error_telemetry
    return get_error_telemetry()

PATTERN_ANALYSIS_PROMPT = """You are analyzing tool calling failures in the Nucleus AI Agent OS.

Agents frequently fail to call required MCP tools. Your job is to find patterns in these failures and suggest system prompt improvements.

RECENT FAILURES (last {failure_count}):
{failure_summary}

Analyze these failures and identify:
1. Which tools are most frequently forgotten
2. What user phrases trigger the failures
3. Specific system prompt text that would prevent these failures

Respond with ONLY valid JSON (no markdown):
{{
    "patterns": [
        {{
            "tool_name": "the frequently forgotten tool",
            "trigger_phrases": ["phrases that cause this failure"],
            "frequency": 3,
            "system_prompt_addition": "Exact text to add to system prompt to prevent this"
        }}
    ],
    "general_improvement": "A general system prompt improvement based on all patterns"
}}
"""


class LearnedPattern:
    """A pattern learned from tool calling failures."""
    
    def __init__(self, tool_name: str, trigger_phrases: List[str],
                 frequency: int, system_prompt_addition: str):
        self.tool_name = tool_name
        self.trigger_phrases = trigger_phrases
        self.frequency = frequency
        self.system_prompt_addition = system_prompt_addition
        self.learned_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "trigger_phrases": self.trigger_phrases,
            "frequency": self.frequency,
            "system_prompt_addition": self.system_prompt_addition,
            "learned_at": self.learned_at
        }


class LLMPatternLearner:
    """
    Learns from tool calling failures to improve future enforcement.
    
    Periodically analyzes failure logs and generates:
    1. Learned patterns (which tools are forgotten, when)
    2. System prompt improvements
    3. Engrams for persistent memory
    """
    
    def __init__(self, model_name: str = None, min_failures_for_analysis: int = 3):
        self.model_name = model_name or os.getenv(
            "NUCLEUS_LEARNER_MODEL", DEFAULT_LEARNING_MODEL
        )
        self.min_failures = min_failures_for_analysis
        self._client = None
        self._use_resilient = True  # Phase 73
        self._learned_patterns: List[LearnedPattern] = []
        self._patterns_path = Path(
            os.getenv("NUCLEAR_BRAIN_PATH", "./.brain")
        ) / "metrics" / "learned_patterns.json"
        
        # Load existing patterns
        self._load_patterns()
    
    def _get_client(self):
        """Lazy-init LLM client."""
        if self._client is not None:
            return self._client
        try:
            from google import genai
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self._client = genai.Client(api_key=api_key)
            else:
                project_id = os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
                if not project_id:
                    raise ValueError("GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT is required for Vertex AI mode.")
                self._client = genai.Client(vertexai=True, project=project_id, location="us-central1")
            return self._client
        except Exception as e:
            logger.warning(f"Failed to init genai client for learner: {e}")
            return None
    
    def _load_patterns(self):
        """Load previously learned patterns from disk (Phase 73: resilient read)."""
        try:
            data = _get_file_ops().read_json(self._patterns_path, default={})
            for p in data.get("patterns", []):
                self._learned_patterns.append(LearnedPattern(
                    tool_name=p.get("tool_name", "unknown"),
                    trigger_phrases=p.get("trigger_phrases", []),
                    frequency=p.get("frequency", 1),
                    system_prompt_addition=p.get("system_prompt_addition", "")
                ))
            if self._learned_patterns:
                logger.info(f"Loaded {len(self._learned_patterns)} learned patterns")
        except Exception as e:
            logger.warning(f"Failed to load learned patterns: {e}")
    
    def _save_patterns(self):
        """Save learned patterns to disk (Phase 73: atomic write)."""
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "pattern_count": len(self._learned_patterns),
            "patterns": [p.to_dict() for p in self._learned_patterns]
        }
        if not _get_file_ops().write_json(self._patterns_path, data):
            logger.warning(f"Failed to save learned patterns to {self._patterns_path}")
    
    def analyze_failures(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze failure log and learn patterns.
        
        Args:
            failures: List of failure records from LLMToolEnforcer
            
        Returns:
            Dict with learned patterns and general improvement
        """
        if len(failures) < self.min_failures:
            return {
                "status": "insufficient_data",
                "message": f"Need at least {self.min_failures} failures (have {len(failures)})",
                "patterns": []
            }
        
        # Build failure summary
        failure_lines = []
        for f in failures[-20:]:
            line = (
                f"Request: \"{f.get('user_request', 'unknown')[:100]}\" | "
                f"Required: {f.get('required_tools', [])} | "
                f"Called: {f.get('tools_called', [])} | "
                f"Success: {f.get('success', False)}"
            )
            failure_lines.append(line)
        
        failure_summary = "\n".join(failure_lines)
        
        prompt = PATTERN_ANALYSIS_PROMPT.format(
            failure_count=len(failures),
            failure_summary=failure_summary
        )
        
        try:
            # Phase 73: Use resilient client with deterministic fallback
            if self._use_resilient:
                resilient = _get_resilient_client()
                result = resilient.generate_json(
                    prompt,
                    model_override=self.model_name,
                    fallback_fn=lambda p: None
                )
                if result is None:
                    return self._analyze_deterministic(failures)
            else:
                client = self._get_client()
                if client is None:
                    return self._analyze_deterministic(failures)
                response = client.models.generate_content(
                    model=self.model_name, contents=prompt
                )
                text = getattr(response, 'text', '') or ''
                json_text = text.strip()
                if json_text.startswith("```"):
                    lines = json_text.split("\n")
                    json_lines = [l for l in lines if not l.strip().startswith("```")]
                    json_text = "\n".join(json_lines).strip()
                result = json.loads(json_text)
            
            # Store learned patterns
            new_patterns = []
            for p in result.get("patterns", []):
                pattern = LearnedPattern(
                    tool_name=p.get("tool_name", "unknown"),
                    trigger_phrases=p.get("trigger_phrases", []),
                    frequency=p.get("frequency", 1),
                    system_prompt_addition=p.get("system_prompt_addition", "")
                )
                new_patterns.append(pattern)
                self._learned_patterns.append(pattern)
            
            # Save to disk
            self._save_patterns()
            
            # Write engrams for persistent memory
            self._write_pattern_engrams(new_patterns)
            
            return {
                "status": "success",
                "patterns_learned": len(new_patterns),
                "general_improvement": result.get("general_improvement", ""),
                "patterns": [p.to_dict() for p in new_patterns]
            }
            
        except Exception as e:
            _get_telemetry().record_error("E603", f"Pattern learning: {e}", "llm_pattern_learner", exception=e)
            return self._analyze_deterministic(failures)
    
    def _analyze_deterministic(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback: Deterministic pattern analysis without LLM."""
        tool_miss_count: Dict[str, int] = {}
        
        for f in failures:
            for tool in f.get("required_tools", []):
                if tool not in f.get("tools_called", []):
                    tool_miss_count[tool] = tool_miss_count.get(tool, 0) + 1
        
        patterns = []
        for tool, count in sorted(tool_miss_count.items(), key=lambda x: -x[1]):
            pattern = LearnedPattern(
                tool_name=tool,
                trigger_phrases=[],
                frequency=count,
                system_prompt_addition=f"REMINDER: When the user's request requires {tool}, you MUST call it."
            )
            patterns.append(pattern)
            self._learned_patterns.append(pattern)
        
        self._save_patterns()
        
        return {
            "status": "deterministic_fallback",
            "patterns_learned": len(patterns),
            "general_improvement": "Ensure all required tools are called before responding.",
            "patterns": [p.to_dict() for p in patterns]
        }
    
    def _write_pattern_engrams(self, patterns: List[LearnedPattern]):
        """Write learned patterns as engrams (Phase 73: resilient append)."""
        brain_path = Path(os.getenv("NUCLEAR_BRAIN_PATH", "./.brain"))
        engrams_path = brain_path / "engrams" / "tool_patterns.jsonl"
        file_ops = _get_file_ops()
        
        for p in patterns:
            engram = {
                "key": f"tool_pattern_{p.tool_name}",
                "value": p.system_prompt_addition,
                "context": "Decision",
                "intensity": min(p.frequency, 10),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if not file_ops.append_jsonl(engrams_path, engram):
                logger.warning(f"Failed to write engram for {p.tool_name}")
    
    def get_system_prompt_enhancement(self) -> str:
        """
        Generate system prompt enhancement from all learned patterns.
        
        This should be injected into agent system prompts to prevent
        known failure patterns.
        """
        if not self._learned_patterns:
            return ""
        
        # Deduplicate by tool name (keep highest frequency)
        best_patterns: Dict[str, LearnedPattern] = {}
        for p in self._learned_patterns:
            if p.tool_name not in best_patterns or p.frequency > best_patterns[p.tool_name].frequency:
                best_patterns[p.tool_name] = p
        
        # Sort by frequency (most common failures first)
        sorted_patterns = sorted(best_patterns.values(), key=lambda p: -p.frequency)
        
        if not sorted_patterns:
            return ""
        
        lines = ["\nLEARNED TOOL CALLING PATTERNS (from past failures):"]
        for p in sorted_patterns[:10]:  # Top 10 patterns
            lines.append(f"- {p.system_prompt_addition}")
        
        return "\n".join(lines)
    
    def get_patterns(self) -> List[Dict[str, Any]]:
        """Get all learned patterns."""
        return [p.to_dict() for p in self._learned_patterns]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learner statistics."""
        return {
            "total_patterns": len(self._learned_patterns),
            "patterns_path": str(self._patterns_path),
            "unique_tools": len(set(p.tool_name for p in self._learned_patterns))
        }


# Singleton
_learner_instance: Optional[LLMPatternLearner] = None

def get_pattern_learner() -> LLMPatternLearner:
    """Get singleton pattern learner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = LLMPatternLearner()
    return _learner_instance
