"""
LLM API Resilience Layer
==========================
Phase 73.1: Production-Grade LLM Client Hardening

Provides:
1. Timeout handling (configurable, default 30s)
2. Retry with exponential backoff (3 retries, jitter)
3. Circuit breaker (open after N failures, half-open after cooldown)
4. Rate limit detection (429 handling with Retry-After)
5. Fallback chain (LLM → deterministic → graceful failure)
6. Structured error categorization
7. Response validation before JSON parsing

Target: 99.9% reliability across all environments.
"""

import json
import logging
import os
import random
import time
import threading
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("nucleus.llm_resilience")

T = TypeVar("T")


# ============================================================
# ERROR CATEGORIZATION
# ============================================================

class ErrorCategory(str, Enum):
    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    AUTH = "AUTH"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    MODEL_ERROR = "MODEL_ERROR"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    UNKNOWN = "UNKNOWN"


@dataclass
class ResilientError:
    """Structured error with category, code, and context."""
    category: ErrorCategory
    code: str
    message: str
    original_exception: Optional[Exception] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retry_after_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp,
            "retry_after_seconds": self.retry_after_seconds
        }


def categorize_exception(e: Exception) -> ResilientError:
    """Categorize an exception into a structured error."""
    msg = str(e).lower()

    # Check exception type first (more reliable than string matching)
    if isinstance(e, (json.JSONDecodeError, ValueError)) and "json" in type(e).__name__.lower():
        return ResilientError(ErrorCategory.INVALID_RESPONSE, "E600", str(e), e)

    # Timeout errors
    if any(kw in msg for kw in ["timeout", "timed out", "deadline exceeded", "read timed out"]):
        return ResilientError(ErrorCategory.TIMEOUT, "E100", str(e), e)

    # Rate limit errors
    if any(kw in msg for kw in ["429", "rate limit", "resource exhausted", "quota", "too many requests"]):
        retry_after = _extract_retry_after(msg)
        cat = ErrorCategory.QUOTA_EXCEEDED if "quota" in msg else ErrorCategory.RATE_LIMIT
        return ResilientError(cat, "E200", str(e), e, retry_after_seconds=retry_after)

    # Auth errors
    if any(kw in msg for kw in ["401", "403", "permission denied", "unauthorized", "forbidden", "api key"]):
        return ResilientError(ErrorCategory.AUTH, "E300", str(e), e)

    # Network errors
    if any(kw in msg for kw in ["connection", "network", "dns", "refused", "unreachable", "reset", "eof", "broken pipe"]):
        return ResilientError(ErrorCategory.NETWORK, "E400", str(e), e)

    # Model-specific errors
    if any(kw in msg for kw in ["model not found", "invalid model", "not supported", "safety", "blocked", "recitation"]):
        return ResilientError(ErrorCategory.MODEL_ERROR, "E500", str(e), e)

    # Invalid response
    if any(kw in msg for kw in ["json", "parse", "decode", "malformed", "invalid response"]):
        return ResilientError(ErrorCategory.INVALID_RESPONSE, "E600", str(e), e)

    return ResilientError(ErrorCategory.UNKNOWN, "E999", str(e), e)


def _extract_retry_after(msg: str) -> Optional[float]:
    """Extract retry-after seconds from error message."""
    import re
    match = re.search(r'retry.?after[:\s]*(\d+)', msg)
    if match:
        return float(match.group(1))
    return None


# ============================================================
# CIRCUIT BREAKER
# ============================================================

class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Rejecting requests
    HALF_OPEN = "HALF_OPEN" # Testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5         # Failures before opening
    recovery_timeout_s: float = 60.0   # Seconds before half-open
    half_open_max_calls: int = 2       # Test calls in half-open
    success_threshold: int = 2         # Successes to close from half-open


class CircuitBreaker:
    """
    Circuit breaker pattern for LLM API calls.
    
    CLOSED → (failures >= threshold) → OPEN
    OPEN → (timeout elapsed) → HALF_OPEN
    HALF_OPEN → (success) → CLOSED
    HALF_OPEN → (failure) → OPEN
    """

    def __init__(self, name: str = "llm", config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
        self._state_change_callbacks: List[Callable] = []

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN and self._last_failure_time:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.config.recovery_timeout_s:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                    logger.info(f"Circuit '{self.name}' → HALF_OPEN after {elapsed:.1f}s cooldown")
            return self._state

    def can_execute(self) -> bool:
        """Check if a call is allowed."""
        s = self.state
        if s == CircuitState.CLOSED:
            return True
        if s == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
        return False  # OPEN

    def record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit '{self.name}' → CLOSED (recovered)")
            else:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self, error: Optional[ResilientError] = None):
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit '{self.name}' → OPEN (half-open test failed)")
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit '{self.name}' → OPEN after {self._failure_count} failures"
                )

    def reset(self):
        """Force reset to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout_s": self.config.recovery_timeout_s,
            }
        }


# ============================================================
# RETRY WITH EXPONENTIAL BACKOFF
# ============================================================

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    jitter: bool = True
    retry_on_categories: tuple = (
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.INVALID_RESPONSE,
        ErrorCategory.UNKNOWN,
    )
    # Non-retryable: AUTH, QUOTA_EXCEEDED, MODEL_ERROR, CIRCUIT_OPEN


def compute_backoff(attempt: int, config: RetryConfig, retry_after: Optional[float] = None) -> float:
    """Compute delay with exponential backoff + jitter."""
    if retry_after and retry_after > 0:
        return min(retry_after, config.max_delay_s)
    delay = min(config.base_delay_s * (2 ** attempt), config.max_delay_s)
    if config.jitter:
        delay = delay * (0.5 + random.random())
    return delay


# ============================================================
# RESPONSE VALIDATOR
# ============================================================

def validate_llm_response(response: Any) -> Optional[str]:
    """
    Validate and extract text from an LLM response object.
    Handles: google-genai, vertex AI, and mock responses.
    Returns extracted text or None.
    """
    if response is None:
        return None

    # Direct text attribute
    text = getattr(response, 'text', None)
    if text is not None:
        return text

    # Try candidates (Vertex AI / google-genai)
    candidates = getattr(response, 'candidates', None)
    if candidates and len(candidates) > 0:
        candidate = candidates[0]
        content = getattr(candidate, 'content', None)
        if content:
            parts = getattr(content, 'parts', None)
            if parts and len(parts) > 0:
                part_text = getattr(parts[0], 'text', None)
                if part_text:
                    return part_text

    # Try dict-like response
    if isinstance(response, dict):
        return response.get('text', response.get('content', None))

    # String response
    if isinstance(response, str):
        return response

    return None


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract JSON from LLM response text.
    Handles: bare JSON, markdown-wrapped, multiple JSON blocks, trailing commas.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks
    import re
    # Match ```json ... ``` or ``` ... ```
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                # Try fixing trailing commas
                cleaned = re.sub(r',\s*([}\]])', r'\1', match.group(1).strip())
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue

    # Try finding first { ... } block
    brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            cleaned = re.sub(r',\s*([}\]])', r'\1', brace_match.group(0))
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    return None


# ============================================================
# RESILIENT LLM CLIENT
# ============================================================

class ResilientLLMClient:
    """
    Production-grade LLM client with:
    - Timeout handling
    - Retry with exponential backoff
    - Circuit breaker
    - Rate limit detection
    - Response validation
    - Fallback chain
    - Error telemetry
    
    This wraps raw LLM client calls and provides 99.9% reliability.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        timeout_s: float = 30.0,
        retry_config: Optional[RetryConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
    ):
        self.model_name = model_name or os.getenv("NUCLEUS_INTENT_MODEL", "gemini-2.0-flash-exp")
        self.timeout_s = float(os.getenv("NUCLEUS_LLM_TIMEOUT", str(timeout_s)))
        self.retry_config = retry_config or RetryConfig()
        self._circuit = CircuitBreaker("llm_resilient", circuit_config)
        self._raw_client = None
        self._engine: Optional[str] = None
        self._lock = threading.Lock()

        # Telemetry
        self._total_calls = 0
        self._success_calls = 0
        self._failed_calls = 0
        self._retry_calls = 0
        self._circuit_rejections = 0
        self._fallback_calls = 0
        self._errors_by_category: Dict[str, int] = {}

    def _init_client(self):
        """Lazy-init underlying LLM client with proper error handling."""
        if self._raw_client is not None:
            return self._raw_client, self._engine

        with self._lock:
            if self._raw_client is not None:
                return self._raw_client, self._engine

            try:
                from google import genai
                api_key = os.environ.get("GEMINI_API_KEY")
                if api_key:
                    self._raw_client = genai.Client(api_key=api_key)
                    self._engine = "api_key"
                else:
                    project_id = os.environ.get(
                        "GCP_PROJECT_ID",
                        os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0894185576")
                    )
                    self._raw_client = genai.Client(
                        vertexai=True, project=project_id, location="us-central1"
                    )
                    self._engine = "vertex"
                return self._raw_client, self._engine
            except ImportError:
                logger.error("google-genai package not installed")
                return None, None
            except Exception as e:
                logger.error(f"Failed to init LLM client: {e}")
                return None, None

    def generate(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        timeout_override: Optional[float] = None,
        fallback_fn: Optional[Callable[[str], Optional[str]]] = None,
    ) -> Optional[str]:
        """
        Generate text from LLM with full resilience stack.
        
        Args:
            prompt: The prompt to send
            model_override: Override the default model
            timeout_override: Override the default timeout
            fallback_fn: Fallback function if LLM fails entirely
            
        Returns:
            Generated text or None
        """
        self._total_calls += 1
        model = model_override or self.model_name
        timeout = timeout_override or self.timeout_s
        last_error: Optional[ResilientError] = None

        # Circuit breaker check
        if not self._circuit.can_execute():
            self._circuit_rejections += 1
            logger.warning(f"Circuit breaker OPEN, rejecting call")
            if fallback_fn:
                self._fallback_calls += 1
                return fallback_fn(prompt)
            return None

        # Retry loop
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                result = self._execute_with_timeout(prompt, model, timeout)
                text = validate_llm_response(result)

                if text is None:
                    raise ValueError("LLM returned None/empty response")

                self._circuit.record_success()
                self._success_calls += 1
                return text

            except Exception as e:
                last_error = categorize_exception(e)
                self._record_error(last_error)

                # Non-retryable errors
                if last_error.category not in self.retry_config.retry_on_categories:
                    logger.warning(
                        f"Non-retryable error ({last_error.category}): {last_error.message}"
                    )
                    self._circuit.record_failure(last_error)
                    break

                # Last attempt
                if attempt >= self.retry_config.max_retries:
                    logger.warning(
                        f"All {self.retry_config.max_retries + 1} attempts exhausted"
                    )
                    self._circuit.record_failure(last_error)
                    break

                # Compute backoff and retry
                delay = compute_backoff(attempt, self.retry_config, last_error.retry_after_seconds)
                self._retry_calls += 1
                logger.info(
                    f"Retry {attempt + 1}/{self.retry_config.max_retries} "
                    f"after {delay:.1f}s ({last_error.category})"
                )
                time.sleep(delay)

        # All attempts failed — try fallback
        self._failed_calls += 1
        if fallback_fn:
            self._fallback_calls += 1
            logger.info("Using fallback function after LLM failure")
            return fallback_fn(prompt)

        return None

    def _execute_with_timeout(self, prompt: str, model: str, timeout: float) -> Any:
        """Execute LLM call with timeout."""
        client, engine = self._init_client()
        if client is None:
            raise ConnectionError("LLM client not initialized (missing API key or package)")

        # Use threading for timeout (works cross-platform: Mac, Windows, Linux)
        result_container = [None]
        error_container = [None]

        def _call():
            try:
                result_container[0] = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
            except Exception as e:
                error_container[0] = e

        thread = threading.Thread(target=_call, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"LLM call timed out after {timeout}s")

        if error_container[0]:
            raise error_container[0]

        return result_container[0]

    def _record_error(self, error: ResilientError):
        """Record error for telemetry."""
        cat = error.category.value
        self._errors_by_category[cat] = self._errors_by_category.get(cat, 0) + 1

    def generate_json(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        fallback_fn: Optional[Callable[[str], Optional[Dict]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and parse JSON from LLM with full resilience.
        Handles markdown wrapping, trailing commas, malformed JSON.
        """
        text = self.generate(prompt, model_override=model_override)
        if text is None:
            if fallback_fn:
                return fallback_fn(prompt)
            return None

        result = extract_json_from_text(text)
        if result is not None:
            return result

        # JSON extraction failed — try fallback
        logger.warning("Failed to extract JSON from LLM response")
        if fallback_fn:
            return fallback_fn(prompt)
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive resilience statistics."""
        total = self._total_calls
        return {
            "total_calls": total,
            "success_calls": self._success_calls,
            "failed_calls": self._failed_calls,
            "retry_calls": self._retry_calls,
            "circuit_rejections": self._circuit_rejections,
            "fallback_calls": self._fallback_calls,
            "success_rate": self._success_calls / total if total > 0 else 0.0,
            "errors_by_category": dict(self._errors_by_category),
            "circuit_breaker": self._circuit.get_stats(),
            "model": self.model_name,
            "timeout_s": self.timeout_s,
        }

    def reset_circuit(self):
        """Force reset circuit breaker."""
        self._circuit.reset()

    @property
    def circuit_state(self) -> str:
        return self._circuit.state.value


# ============================================================
# SINGLETON
# ============================================================

_resilient_client: Optional[ResilientLLMClient] = None
_resilient_lock = threading.Lock()


def get_resilient_llm_client() -> ResilientLLMClient:
    """Get singleton resilient LLM client."""
    global _resilient_client
    if _resilient_client is None:
        with _resilient_lock:
            if _resilient_client is None:
                _resilient_client = ResilientLLMClient()
    return _resilient_client
