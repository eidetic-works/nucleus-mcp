"""Dynamic Model Selection with Quota-Aware Fallback (Phase 7 §5).

Implements the 4-layer architecture from
``.brain/plans/design_dynamic_model_selection_20260805.md``:

  Layer 1 — Health Registry (ephemeral, per-process)
  Layer 2 — Quota classification (parse stderr → failure type → cooldown)
  Layer 3 — Task-aware strength scoring (static table per task type)
  Layer 4 — Dynamic discovery (query agy/devin for model lists at startup)
  Layer 5 — Composite score + fallback chain

When a model hits a quota limit mid-task, the previous behavior was:
  1. Retry the SAME model (same quota → same failure)
  2. Fall back to devin single-vendor mode (skips adversarial review)
  3. Never try agy's OTHER models (flash tiers, Claude models)

This module fixes that by tracking per-model health, classifying failures,
and building a dynamic fallback chain scored by task strength × availability
× freshness.

Boundary note: this is a **periphery** module. Heavy imports are function-local
so the module's own import stays stdlib-only.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.model_registry")

# ── Layer 2: Quota classification ─────────────────────────────────────────────

# Failure type constants
F_QUOTA = "quota"
F_RATE_LIMIT = "rate_limit"
F_AUTH = "auth"
F_TIMEOUT = "timeout"
F_UNKNOWN = "unknown"

# Cooldown durations (seconds)
_COOLDOWN_QUOTA = 3600          # 1 hour (conservative; real reset is often midnight)
_COOLDOWN_RATE_LIMIT = 60       # 1 minute
_COOLDOWN_AUTH = 86400          # 24 hours (needs operator re-auth)
_COOLDOWN_UNKNOWN = 300         # 5 minutes (conservative)
_COOLDOWN_INFERRED_QUOTA = 3600 # 3 consecutive empty outputs → inferred quota

# stderr patterns for classification
_QUOTA_PATTERNS = re.compile(
    r"quota|upgrade|billing|credit|exceeded.*limit|plan.*limit",
    re.IGNORECASE,
)
_RATE_PATTERNS = re.compile(
    r"rate.?limit|too many request|429|slow.?down|throttl",
    re.IGNORECASE,
)
_AUTH_PATTERNS = re.compile(
    r"unauthorized|401|forbidden|403|invalid.*key|auth.*fail|login.*required",
    re.IGNORECASE,
)
_TIMEOUT_PATTERNS = re.compile(
    r"timeout|timed.?out|deadline.*exceeded|context.*canceled",
    re.IGNORECASE,
)

# Consecutive empty-output threshold for inferred quota
_INFERRED_QUOTA_THRESHOLD = 3


def classify_failure(
    stderr: str,
    rc: int,
    stdout_empty: bool,
) -> str:
    """Classify a vendor dispatch failure into a failure type.

    Returns one of F_QUOTA, F_RATE_LIMIT, F_AUTH, F_TIMEOUT, F_UNKNOWN.
    Used by the health registry to set the appropriate cooldown duration.
    """
    if not stderr:
        stderr = ""
    if _AUTH_PATTERNS.search(stderr):
        return F_AUTH
    if _QUOTA_PATTERNS.search(stderr):
        return F_QUOTA
    if _RATE_PATTERNS.search(stderr):
        return F_RATE_LIMIT
    if _TIMEOUT_PATTERNS.search(stderr):
        return F_TIMEOUT
    # rc=0, empty stdout, no stderr → unknown (could be silent quota)
    if rc == 0 and stdout_empty and not stderr.strip():
        return F_UNKNOWN
    return F_UNKNOWN


def cooldown_for(failure_type: str) -> float:
    """Return cooldown duration in seconds for a failure type."""
    return {
        F_QUOTA: _COOLDOWN_QUOTA,
        F_RATE_LIMIT: _COOLDOWN_RATE_LIMIT,
        F_AUTH: _COOLDOWN_AUTH,
        F_TIMEOUT: _COOLDOWN_UNKNOWN,
        F_UNKNOWN: _COOLDOWN_UNKNOWN,
    }.get(failure_type, _COOLDOWN_UNKNOWN)


# ── Layer 1: Health Registry ──────────────────────────────────────────────────

@dataclass
class ModelHealth:
    """Per-model health state (ephemeral, per-process)."""
    key: str                           # "agy:gemini-3.1-pro-high"
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    failure_type: Optional[str] = None
    cooldown_until: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_empty: int = 0         # rc=0 + empty stdout (inferred quota)
    total_dispatches: int = 0
    total_successes: int = 0
    total_failures: int = 0
    recent_dispatch_times: List[float] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        """True if not in cooldown."""
        if self.cooldown_until is None:
            return True
        return time.time() >= self.cooldown_until

    @property
    def availability_score(self) -> float:
        """1.0 if healthy, 0.0 if in cooldown, linear ramp as cooldown expires."""
        if self.cooldown_until is None:
            return 1.0
        now = time.time()
        if now >= self.cooldown_until:
            return 1.0
        # Linear ramp: 0.0 at cooldown start → 1.0 at cooldown end
        # Use the last failure time as the start of cooldown
        start = self.last_failure or (self.cooldown_until - _COOLDOWN_QUOTA)
        if start >= self.cooldown_until:
            return 0.0
        progress = (now - start) / (self.cooldown_until - start)
        return max(0.0, min(1.0, progress))

    @property
    def freshness_score(self) -> float:
        """1.0 / (1 + recent_dispatches_last_5min) — spreads load."""
        now = time.time()
        cutoff = now - 300  # 5 minutes
        self.recent_dispatch_times = [t for t in self.recent_dispatch_times if t > cutoff]
        return 1.0 / (1.0 + len(self.recent_dispatch_times))

    def record_success(self) -> None:
        now = time.time()
        self.last_success = now
        self.consecutive_failures = 0
        self.consecutive_empty = 0
        self.cooldown_until = None  # clear cooldown on success
        self.total_dispatches += 1
        self.total_successes += 1
        self.recent_dispatch_times.append(now)

    def record_failure(
        self,
        failure_type: str,
        stderr: str = "",
        rc: int = 1,
        stdout_empty: bool = False,
    ) -> None:
        now = time.time()
        self.last_failure = now
        self.failure_type = failure_type
        self.consecutive_failures += 1
        self.total_dispatches += 1
        self.total_failures += 1
        self.recent_dispatch_times.append(now)

        # Track consecutive empty outputs for inferred quota
        if rc == 0 and stdout_empty:
            self.consecutive_empty += 1
        else:
            self.consecutive_empty = 0

        # Set cooldown
        if (self.consecutive_empty >= _INFERRED_QUOTA_THRESHOLD
                and failure_type == F_UNKNOWN):
            # Inferred quota: 3 consecutive empty outputs
            self.cooldown_until = now + _COOLDOWN_INFERRED_QUOTA
            self.failure_type = F_QUOTA  # reclassify
        else:
            self.cooldown_until = now + cooldown_for(failure_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "failure_type": self.failure_type,
            "cooldown_until": self.cooldown_until,
            "is_available": self.is_available,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_empty": self.consecutive_empty,
            "total_dispatches": self.total_dispatches,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
        }


class ModelHealthRegistry:
    """Ephemeral per-process registry of model health state."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelHealth] = {}

    def _key(self, vendor: str, model: str) -> str:
        return f"{vendor}:{model}"

    def get(self, vendor: str, model: str) -> ModelHealth:
        key = self._key(vendor, model)
        if key not in self._models:
            self._models[key] = ModelHealth(key=key)
        return self._models[key]

    def record_success(self, vendor: str, model: str) -> None:
        self.get(vendor, model).record_success()

    def record_failure(
        self,
        vendor: str,
        model: str,
        stderr: str = "",
        rc: int = 1,
        stdout_empty: bool = False,
    ) -> None:
        failure_type = classify_failure(stderr, rc, stdout_empty)
        self.get(vendor, model).record_failure(
            failure_type, stderr=stderr, rc=rc, stdout_empty=stdout_empty
        )

    def is_available(self, vendor: str, model: str) -> bool:
        return self.get(vendor, model).is_available

    def availability_score(self, vendor: str, model: str) -> float:
        return self.get(vendor, model).availability_score

    def freshness_score(self, vendor: str, model: str) -> float:
        return self.get(vendor, model).freshness_score

    def snapshot(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self._models.items()}

    def reset(self) -> None:
        self._models.clear()


# Module-level singleton (per-process)
_registry: Optional[ModelHealthRegistry] = None


def get_registry() -> ModelHealthRegistry:
    global _registry
    if _registry is None:
        _registry = ModelHealthRegistry()
    return _registry


# ── Layer 3: Task-Aware Strength Scoring ──────────────────────────────────────

# Task types mapped to model strength scores (0–1).
# Per-task-type, NOT per-computer. Encodes "pro > flash for reasoning"
# which is universally true.
TASK_STRENGTH: Dict[str, Dict[str, float]] = {
    "plan_author": {
        "swe-2-max": 0.94,
        "swe-2-high": 0.92,
        "swe-2-medium": 0.90,
        "glm-5-2": 0.88,
        "swe-1-7": 0.86,
        "gemini-3.1-pro-high": 0.82,
        "gemini-3.6-flash-high": 0.70,
        "gemini-3.5-flash-low": 0.40,
    },
    # OPERATOR ROUTING RULE (2026-09-10): devin (swe-2 / swe-1-7 / glm-5-2)
    # are the primary free lane on this host. SWE-2 Max leads plan_author:
    # it outperforms SWE-1.7 and GLM-5.2 on Terminal-Bench 2.1, DeepSWE 1.1
    # and FrontierCode 1.1. GLM-5.2 leads plan_reviewer, code_executor and
    # adversarial_review — it has stronger 1M-context / math / structured
    # review signals and operational history on those tasks. SWE-2 High and
    # Medium are scored just below Max. agy-gemini-3.1-pro-high is
    # quota-limited, so it is scored below the devin lane and used as a
    # fallback. agy-gemini flash and agy-claude stay in the table below the
    # devin models, with agy-claude last-resort only.
    #
    # GLM-5.2 FREEZE LIFTED (2026-09-02): glm-5-2 is confirmed free again
    # and restored to its pre-freeze task scores. The registry's composite
    # score (strength x availability x freshness) will pick the best available
    # model for each task.
    "plan_reviewer": {
        "glm-5-2": 0.92,
        "swe-2-max": 0.90,
        "swe-2-high": 0.87,
        "swe-2-medium": 0.84,
        "swe-1-7": 0.75,
        "gemini-3.1-pro-high": 0.74,
        "gemini-3.6-flash-high": 0.65,
        "claude-opus-4-6-thinking": 0.45,
        "claude-sonnet-4-6": 0.40,
    },
    "code_executor": {
        "glm-5-2": 0.95,
        "swe-2-max": 0.94,
        "swe-2-high": 0.92,
        "swe-2-medium": 0.90,
        "swe-1-7": 0.85,
        "gemini-3.1-pro-high": 0.75,
        "gemini-3.6-flash-high": 0.55,
    },
    "simple_read": {
        "gemini-3.6-flash-low": 0.90,
        "gemini-3.5-flash-low": 0.85,
        "swe-2-max": 0.82,
        "swe-2-high": 0.80,
        "swe-2-medium": 0.78,
        "glm-5-2": 0.76,
        "gemini-3.1-pro-high": 0.70,
    },
    # Same operator routing rule: devin (swe-2 / swe-1-7 / glm-5-2) first,
    # agy-gemini-3.1-pro-high fallback (limited quota), agy-claude last resort.
    # GLM-5.2 leads adversarial_review so a genuinely different family is
    # available when an SWE-2 author needs an independent reviewer.
    "adversarial_review": {
        "glm-5-2": 0.92,
        "swe-2-max": 0.88,
        "swe-2-high": 0.85,
        "swe-2-medium": 0.82,
        "swe-1-7": 0.75,
        "gemini-3.1-pro-high": 0.74,
        "gemini-3.6-flash-high": 0.65,
        "claude-opus-4-6-thinking": 0.45,
    },
}

# Default task type when caller doesn't specify
DEFAULT_TASK_TYPE = "plan_author"


def strength_score(model: str, task_type: str = DEFAULT_TASK_TYPE) -> float:
    """Get the task-specific strength score for a model.

    Returns 0.0 if the model isn't in the strength table for this task type
    (unknown models are never selected — they must be explicitly added).
    """
    table = TASK_STRENGTH.get(task_type, TASK_STRENGTH[DEFAULT_TASK_TYPE])
    return table.get(model, 0.0)


# ── Layer 4: Dynamic Discovery ────────────────────────────────────────────────

@dataclass
class ModelSpec:
    """A discovered model from a vendor CLI."""
    vendor: str
    model_id: str
    available: bool = True


def _query_agy_models() -> List[str]:
    """Query `agy models` for the current model list.

    Returns an empty list if agy is not installed or the command fails.
    """
    if not shutil.which("agy"):
        return []
    try:
        result = subprocess.run(
            ["agy", "models"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("agy models returned rc=%d: %s", result.returncode, result.stderr[:200])
            return []
        # Parse output — one model per line, strip whitespace
        models = []
        for line in result.stdout.strip().splitlines():
            model_id = line.strip()
            if model_id and not model_id.startswith("#"):
                models.append(model_id)
        return models
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning("agy models discovery failed: %s", e)
        return []


def _query_devin_models() -> List[str]:
    """Query devin for its model list.

    Devin doesn't have a `models` subcommand, so we return the known list
    from VENDOR_SPECS. Future: if devin adds a models command, query it.
    """
    # Import here to avoid circular import at module load
    try:
        from .vendor_dispatch import VENDOR_SPECS
        spec = VENDOR_SPECS.get("devin")
        if spec and spec.models:
            return list(spec.models)
    except Exception:
        logger.debug("Swallowed exception in _query_devin_models", exc_info=True)
        pass
    # SWE-2 FREE TIER (2026-09-10): SWE-2 Max/High/Medium are free and are
    # the preferred default. GLM-5.2 FREEZE LIFTED (2026-09-02): include
    # glm-5-2 alongside the SWE-1.7 tiers so model_registry can discover it
    # even when the VENDOR_SPECS import path is unavailable.
    return ["swe-2-max", "swe-2-high", "swe-2-medium", "swe-1-7", "swe-1-7-medium", "glm-5-2"]


def discover_models() -> List[ModelSpec]:
    """Discover all available models across all vendor CLIs.

    Called at process startup (or lazily on first dispatch). Computer-portable:
    a machine without agy doesn't discover agy models.
    """
    models: List[ModelSpec] = []

    for model_id in _query_agy_models():
        models.append(ModelSpec(vendor="agy", model_id=model_id))
    for model_id in _query_devin_models():
        models.append(ModelSpec(vendor="devin", model_id=model_id))

    logger.info("discovered %d models: %s", len(models),
                [f"{m.vendor}:{m.model_id}" for m in models])
    return models


# ── Layer 5: Composite Score + Fallback Chain ─────────────────────────────────

# ε-greedy exploration probability (5%)
_EPSILON = float(os.environ.get("TB_MODEL_EPSILON", "0.05"))


@dataclass
class ScoredModel:
    """A model with its composite score and component scores."""
    vendor: str
    model_id: str
    strength: float
    availability: float
    freshness: float
    score: float

    @property
    def key(self) -> str:
        return f"{self.vendor}:{self.model_id}"


def composite_score(
    vendor: str,
    model_id: str,
    task_type: str = DEFAULT_TASK_TYPE,
    registry: Optional[ModelHealthRegistry] = None,
) -> ScoredModel:
    """Compute the composite score for a model.

    score = strength × availability × freshness
    """
    reg = registry or get_registry()
    s = strength_score(model_id, task_type)
    a = reg.availability_score(vendor, model_id)
    f = reg.freshness_score(vendor, model_id)
    return ScoredModel(
        vendor=vendor,
        model_id=model_id,
        strength=s,
        availability=a,
        freshness=f,
        score=s * a * f,
    )


def build_fallback_chain(
    task_type: str = DEFAULT_TASK_TYPE,
    discovered: Optional[List[ModelSpec]] = None,
    registry: Optional[ModelHealthRegistry] = None,
    epsilon: Optional[float] = None,
) -> List[ScoredModel]:
    """Build an ordered fallback chain of models for a task type.

    1. Discover available models (or use provided list)
    2. Score each: strength × availability × freshness
    3. Sort descending by score
    4. Filter out models with strength=0 (unknown for this task)
    5. ε-greedy: with probability ε, shuffle the top 3 to explore alternatives
    """
    import random

    reg = registry or get_registry()
    eps = epsilon if epsilon is not None else _EPSILON

    if discovered is None:
        discovered = discover_models()

    # Score all discovered models
    scored = [
        composite_score(m.vendor, m.model_id, task_type, reg)
        for m in discovered
        if m.available
    ]

    # Filter out models with zero strength (unknown for this task type)
    scored = [s for s in scored if s.strength > 0]

    # Sort descending by score
    scored.sort(key=lambda s: s.score, reverse=True)

    # ε-greedy exploration: with probability ε, shuffle top 3
    if eps > 0 and len(scored) >= 3 and random.random() < eps:
        top3 = scored[:3]
        random.shuffle(top3)
        scored = top3 + scored[3:]
        logger.info("ε-greedy: shuffled top 3 for task=%s", task_type)

    return scored


def select_model(
    task_type: str = DEFAULT_TASK_TYPE,
    discovered: Optional[List[ModelSpec]] = None,
    registry: Optional[ModelHealthRegistry] = None,
) -> Optional[ScoredModel]:
    """Select the best model for a task, or None if no models are available.

    This is the main entry point for dispatch code. After a dispatch succeeds
    or fails, call registry.record_success/record_failure to update health.
    """
    chain = build_fallback_chain(task_type, discovered, registry)
    if not chain:
        return None
    # Return the first available model (highest score after ε-greedy shuffle)
    for model in chain:
        if model.availability > 0:
            return model
    # All in cooldown — return the one with the highest availability score
    # (closest to coming out of cooldown)
    return chain[0] if chain else None


def next_model_after_failure(
    vendor: str,
    model_id: str,
    task_type: str = DEFAULT_TASK_TYPE,
    discovered: Optional[List[ModelSpec]] = None,
    registry: Optional[ModelHealthRegistry] = None,
) -> Optional[ScoredModel]:
    """Get the next model to try after a failure.

    Records the failure in the health registry, then rebuilds the fallback
    chain excluding the just-failed model (it's now in cooldown).
    """
    reg = registry or get_registry()
    # The caller should have already called record_failure, but we don't
    # re-record here — we just rebuild the chain and skip the failed model.
    chain = build_fallback_chain(task_type, discovered, reg)
    failed_key = f"{vendor}:{model_id}"
    for model in chain:
        if model.key != failed_key and model.availability > 0:
            return model
    # No alternative available — return the least-bad option
    for model in chain:
        if model.key != failed_key:
            return model
    return None
