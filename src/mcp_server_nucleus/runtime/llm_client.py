"""
Nucleus LLM Client
==================
Multi-Tier LLM Client with intelligent routing.
Primary: google-genai (v1.0+) with Vertex AI
Fallback: google-generativeai (Legacy) or API Key

MDR_010 Compliant: Ensures high availability and reliability.
"""

import os
import logging
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, field

# Configure logger
logger = logging.getLogger("nucleus.llm")

# ============================================================
# SDK AVAILABILITY FLAGS & ENVIRONMENT CONTROL
# ============================================================
# Environment variable to force SDK selection:
#   USE_NEW_GENAI=true  → Prefer google-genai (new SDK)
#   USE_NEW_GENAI=false → Prefer google.generativeai (legacy)
#   Default: Try new SDK first, fall back to legacy
# ============================================================

# Primary SDK: google-genai (v1.0+)
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
    logger.debug("✅ SDK: google-genai (new) available")
except ImportError:
    HAS_GENAI = False
    if os.environ.get("NUCLEUS_SKIP_AUTOSTART", "false").lower() != "true":
        logger.debug("⚠️ google-genai not installed. Falling back to legacy SDK.")

# Fallback SDK: google.generativeai (Legacy)
try:
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai_legacy
    HAS_LEGACY = True
except ImportError:
    HAS_LEGACY = False

def get_active_sdk() -> str:
    if HAS_GENAI: return "NEW"
    if HAS_LEGACY: return "LEGACY"
    return "NONE"

_active = get_active_sdk()
logger.debug(f"🎯 SDK Selection: Using {_active}")


# ============================================================
# TIER ROUTER: Intelligent Multi-Tier LLM Selection
# ============================================================

class LLMTier(Enum):
    """Available LLM pricing/capability tiers."""
    # --- Vertex AI / Paid tiers (for when billing is enabled) ---
    PREMIUM = "premium"           # gemini-3.1-pro-preview (Vertex), highest capability
    STANDARD = "standard"         # gemini-3.1-flash-lite-preview (Vertex), default production
    ECONOMY = "economy"           # gemini-2.5-flash (Vertex), background tasks
    # --- API Key tiers (free-tier / local dev) ---
    LOCAL_PAID = "local_paid"     # API Key with billing (Anthropic fallback)
    LOCAL_FREE = "local_free"     # API Key free tier


class TierRouter:
    """
    Intelligent router that selects the optimal LLM tier based on:
    - Job type (CRITICAL, RESEARCH, ORCHESTRATION, BACKGROUND, TESTING)
    - Budget mode (spartan, balanced, premium)
    - Quota availability (fallback on errors)
    
    Free-Tier Quota Reference (as of 2026-03-10):
      gemini-3-flash:                20 RPD
      gemini-2.5-flash:              20 RPD
      gemini-3.1-flash-lite-preview: 500 RPD  ← best for fuzzing/testing
      gemini-2.5-flash-lite:         20 RPD
    """

    TIER_CONFIGS = {
        # --- Vertex AI / Paid (preserved for when billing is enabled) ---
        # --- Vertex AI / Paid (Currently disabled/mapped to best free) ---
        LLMTier.PREMIUM: {
            "model": "gemini-3-flash-preview",
            "platform": "vertex",
            "cost_level": "high",
            "description": "Mapped to Gemini 3 Flash (Free)"
        },
        LLMTier.STANDARD: {
            "model": "gemini-3-flash-preview",
            "platform": "vertex",
            "cost_level": "medium",
            "description": "Mapped to Gemini 3 Flash (Free)"
        },
        LLMTier.ECONOMY: {
            "model": "gemini-2.5-flash-lite",
            "platform": "vertex",
            "cost_level": "low",
            "description": "Gemini 2.5 Flash Lite"
        },
        # --- API Key / Local ---
        LLMTier.LOCAL_PAID: {
            "model": "gemini-3.1-flash-lite-preview",
            "platform": "api_key",
            "cost_level": "medium",
            "description": "Paid-tier Gemini, massive quota (149.5K RPD)"
        },
        LLMTier.LOCAL_FREE: {
            "model": "gemini-3-flash-preview",
            "platform": "api_key",
            "cost_level": "free",
            "description": "Gemini 3 Flash (Free)"
        },
    }

    # Free-tier model cascade
    # Ordered by descending quota availability (based on Google AI Studio 2026 limits)
    FREE_TIER_CASCADE = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-flash-lite"
    ]

    # Highest intelligence cascade for Sovereign workflow (auto-rotation)
    SOVEREIGN_CASCADE = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-flash-lite"
    ]

    JOB_ROUTING = {
        "CRITICAL": LLMTier.PREMIUM,
        "RESEARCH": LLMTier.STANDARD,
        "ORCHESTRATION": LLMTier.STANDARD,
        "BACKGROUND": LLMTier.ECONOMY,
        "TESTING": LLMTier.LOCAL_FREE,
    }
    
    BUDGET_MODES = {
        "spartan": [LLMTier.LOCAL_FREE, LLMTier.ECONOMY, LLMTier.STANDARD],
        "balanced": [LLMTier.STANDARD, LLMTier.ECONOMY, LLMTier.LOCAL_PAID],
        "premium": [LLMTier.PREMIUM, LLMTier.STANDARD, LLMTier.ECONOMY],
    }
    
    FALLBACK_CHAIN = [
        LLMTier.PREMIUM,
        LLMTier.STANDARD,
        LLMTier.ECONOMY,
        LLMTier.LOCAL_PAID,
        LLMTier.LOCAL_FREE
    ]
    
    @classmethod
    def route(cls, job_type: str = "ORCHESTRATION", budget_mode: str = "balanced") -> LLMTier:
        """
        Route to optimal tier based on job type and budget.
        
        Args:
            job_type: CRITICAL, RESEARCH, ORCHESTRATION, BACKGROUND, TESTING
            budget_mode: spartan, balanced, premium
            
        Returns:
            The recommended LLMTier
        """
        # Check for forced tier (env var override)
        forced_tier = os.environ.get("NUCLEUS_LLM_TIER")
        if forced_tier:
            try:
                return LLMTier(forced_tier.lower())
            except ValueError:
                logger.warning(f"Invalid NUCLEUS_LLM_TIER: {forced_tier}")
        
        # Route based on job type
        job_upper = job_type.upper() if job_type else "ORCHESTRATION"
        base_tier = cls.JOB_ROUTING.get(job_upper, LLMTier.STANDARD)
        
        # CRITICAL jobs ALWAYS get their designated tier (premium)
        # Quality for important decisions overrides budget constraints
        if job_upper == "CRITICAL":
            logger.info("🎯 TierRouter: CRITICAL job - using premium tier regardless of budget")
            return LLMTier.PREMIUM
        
        # TESTING jobs ALWAYS use free tier to save costs
        if job_upper == "TESTING":
            return LLMTier.LOCAL_FREE
        
        # For other jobs, apply budget constraints
        budget_tiers = cls.BUDGET_MODES.get(budget_mode.lower(), cls.BUDGET_MODES["balanced"])
        
        # If base tier is in budget, use it; otherwise use first budget tier
        if base_tier in budget_tiers:
            return base_tier
        return budget_tiers[0]
    
    @classmethod
    def get_config(cls, tier: LLMTier) -> Dict[str, Any]:
        """Get configuration for a specific tier."""
        return cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS[LLMTier.STANDARD])
    
    @classmethod
    def get_fallback(cls, current_tier: LLMTier) -> Optional[LLMTier]:
        """Get next tier in fallback chain."""
        try:
            idx = cls.FALLBACK_CHAIN.index(current_tier)
            if idx < len(cls.FALLBACK_CHAIN) - 1:
                return cls.FALLBACK_CHAIN[idx + 1]
        except ValueError:
            pass
        return None

class DualEngineLLM:
    """
    Unified LLM Client wrapper with intelligent tier routing.
    Transparently falls back to legacy SDK if V1 is not available.
    
    Supports:
    - Explicit tier selection: DualEngineLLM(tier=LLMTier.PREMIUM)
    - Job-based routing: DualEngineLLM(job_type="CRITICAL")
    - Budget modes: "spartan", "balanced", "premium"
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = None,
        tier: Optional[LLMTier] = None,
        job_type: Optional[str] = None,
        budget_mode: str = "balanced",
        system_instruction: Optional[str] = None, 
        api_key: Optional[str] = None
    ):
        # TIER ROUTING LOGIC
        self.tier = None
        self.tier_config = None
        
        if tier:
            # Explicit tier selection
            self.tier = tier
            self.tier_config = TierRouter.get_config(tier)
            model_name = model_name or self.tier_config["model"]
            logger.info(f"🎯 LLM: Using explicit tier '{tier.value}' → {model_name}")
        elif job_type:
            # Job-based routing
            self.tier = TierRouter.route(job_type, budget_mode)
            self.tier_config = TierRouter.get_config(self.tier)
            model_name = self.tier_config["model"]
            logger.info(f"🎯 LLM: Routed job '{job_type}' (budget={budget_mode}) → tier '{self.tier.value}' → {model_name}")
        else:
            # Default to standard tier
            self.tier = LLMTier.STANDARD
            self.tier_config = TierRouter.get_config(self.tier)
            model_name = model_name or self.tier_config["model"]
        
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = None
        self.engine = "NONE"
        self.budget_mode = budget_mode
        
        # Determine platform from tier config
        use_vertex = self.tier_config.get("platform", "vertex") == "vertex" if self.tier_config else True
        force_vertex_env = os.environ.get("FORCE_VERTEX", "0") == "1"
        
        # For local tiers, don't use vertex
        if self.tier in [LLMTier.LOCAL_PAID, LLMTier.LOCAL_FREE]:
            use_vertex = False
        else:
            use_vertex = use_vertex or force_vertex_env
        
        if not self.api_key and not use_vertex:
            raise ValueError("GEMINI_API_KEY is required for local tiers (or set FORCE_VERTEX=1).")

            
        # 1. Initialize google-genai (Primary)
        if HAS_GENAI:
            try:
                proxy_url = os.environ.get("GEMINI_API_BASE_URL")
                
                # Phase 14 Hardening: Auto-discovery of local proxy
                _proxy_port_file = Path(tempfile.gettempdir()) / "gemini_proxy.port"
                if not proxy_url and _proxy_port_file.exists():
                    try:
                        port = _proxy_port_file.read_text().strip()
                        proxy_url = f"http://127.0.0.1:{port}/v1"
                        logger.info(f"📍 Auto-discovered Gemini Proxy at {proxy_url}")
                    except Exception as e:
                        logger.debug(f"Proxy auto-discovery failed: {e}")

                if proxy_url:
                    logger.info(f"🔗 LLM Client: Proxy Mode ({proxy_url})")
                    # Force API Key mode for proxy, disable Vertex
                    self.client = genai.Client(
                        api_key=self.api_key or "sk-dummy", # Proxy handles keys
                        http_options={'base_url': proxy_url}
                    )
                elif use_vertex:
                    project_id = os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
                    if not project_id and os.environ.get("FORCE_VERTEX") == "1":
                         logger.warning("⚠️ Vertex AI requested but GCP_PROJECT_ID/GOOGLE_CLOUD_PROJECT not set.")
                         raise ValueError("GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT is required for Vertex AI mode.")
                    
                    location = os.environ.get("GCP_LOCATION", "us-central1")
                    
                    logger.info(f"🏢 LLM Client: Vertex AI Mode ({project_id})")
                    self.client = genai.Client(vertexai=True, project=project_id, location=location)
                else:
                    logger.info("🔑 LLM Client: API Key Mode")
                    # Use v1alpha for experimental features if needed, or stable v1
                    self.client = genai.Client(api_key=self.api_key)
                    
                self.engine = "NEW"
                return
            except Exception as e:
                logger.warning(f"⚠️ V1 Init failed: {e}")

        # 2. Try Legacy (Fallback)
        if HAS_LEGACY:
            try:
                genai_legacy.configure(api_key=self.api_key)
                # Map newer model names to legacy compatible ones if needed
                if "2.0" in model_name:
                    logger.warning(f"⚠️ Legacy SDK may not support {model_name}. Using gemini-1.5-flash.")
                    self.model_name = "gemini-1.5-flash"
                
                self.model = genai_legacy.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction
                )
                self.engine = "LEGACY"
                logger.info(f"✅ LLM Client: Initialized google-generativeai (Legacy) for {self.model_name}")
                return
            except Exception as e:
                logger.error(f"❌ LLM Client: Legacy Init failed: {e}")
                
        if self.engine == "NONE":
            raise ImportError("Could not initialize any Gemini SDK. Install google-genai or google-generativeai.")

    def _log_interaction(self, prompt: str, response: Any):
        """
        Automatic Capture (Brain Consolidation - Phase 1).
        Saves the raw interaction to disk for later mining/consolidation.
        """
        try:
            from .common import get_brain_path
            brain_path = get_brain_path()
            raw_path = brain_path / "raw"
            raw_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filename = raw_path / f"llm_interaction_{timestamp}.json"
            
            # Extract text from response (Best effort)
            response_text = self._safe_text(response) or "Unknown"
                
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "engine": self.engine,
                "model": self.model_name,
                "prompt": str(prompt)[:5000], # Truncate massive prompts 
                "response_text": response_text
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"Failed to log interaction: {e}")

    def generate_content(self, prompt: str, **kwargs) -> Any:
        try:
            # ── Token Budget Check (42-Round Audit: Round 14) ─────────
            try:
                from .token_budget import get_budget_manager, estimate_tokens
                budget = get_budget_manager()
                session_id = os.environ.get("NUCLEUS_SESSION_ID", "default")
                agent_id = kwargs.pop("_agent_id", "default")
                if not budget.can_execute(session_id=session_id, agent_id=agent_id):
                    raise RuntimeError(
                        f"Token budget exceeded for session={session_id}, agent={agent_id}. "
                        "Reset with NUCLEUS_SESSION_COST_LIMIT or wait for daily reset."
                    )
            except ImportError:
                session_id, agent_id = "default", "default"

            # Emit DSoR event for interaction start (Audit Trail)
            try:
                from .event_ops import _emit_event
                _emit_event(
                    event_type="LLM_GENERATE",
                    emitter="DualEngineLLM",
                    data={
                        "model": self.model_name,
                        "tier": self.tier.value if self.tier else "unknown",
                        "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt
                    },
                    description=f"Generating content using {self.model_name}"
                )
            except ImportError:
                pass # Fallback if event_ops not reachable

            if self.engine == "NEW":
                config_args = {}
                if self.system_instruction:
                    config_args['system_instruction'] = self.system_instruction
                    
                if 'tools' in kwargs:
                    tools_raw = kwargs['tools']
                    if isinstance(tools_raw, dict) and "function_declarations" in tools_raw:
                        config_args['tools'] = [tools_raw] 
                    else:
                        config_args['tools'] = tools_raw

                if 'tool_config' in kwargs:
                     config_args['tool_config'] = kwargs['tool_config']
                
                config = types.GenerateContentConfig(**config_args)
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                self._log_interaction(prompt, response)
                self._record_token_usage(prompt, response, session_id, agent_id)
                return response

            elif self.engine == "LEGACY":
                # Legacy SDK logic
                generation_config = {}
                # Legacy doesn't support tools same way here, basic text only for now or map tools manually
                # For Marketing Autopilot, we mostly use text.
                
                response = self.model.generate_content(prompt, generation_config=generation_config)
                self._log_interaction(prompt, response)
                self._record_token_usage(prompt, response, session_id, agent_id)
                return response

        except Exception as e:
            err_str = str(e)
            # Keep 429/403/quota errors concise — the sweeper logs the compact version
            if any(code in err_str for code in ("429", "403", "402", "RESOURCE_EXHAUSTED", "PERMISSION_DENIED", "BILLING_DISABLED", "credit_limit")):
                logger.debug(f"LLM blocked ({self.engine}/{self.model_name}): {err_str[:60]}")
            else:
                logger.error(f"❌ LLM Generate Content Failed ({self.engine}): {e}")
            raise

    def _record_token_usage(self, prompt: str, response: Any, session_id: str = "default", agent_id: str = "default"):
        """Record token usage to the BudgetManager after each LLM call."""
        try:
            from .token_budget import get_budget_manager, estimate_tokens
            input_tokens = estimate_tokens(str(prompt))
            response_text = getattr(response, 'text', '') or ''
            output_tokens = estimate_tokens(response_text)
            get_budget_manager().record_usage(
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                session_id=session_id,
                agent_id=agent_id,
            )
        except Exception as e:
            logger.debug(f"Token usage recording skipped: {e}")

    def embed_content(self, text: str, task_type: str = "retrieval_document", title: Optional[str] = None) -> Dict[str, Any]:
        try:
            if self.engine == "NEW":
                normalized_task_type = task_type.replace("retrieval_", "RETRIEVAL_").upper()
                config = {'task_type': normalized_task_type}
                if title:
                    config['title'] = title
                
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                    config=config
                )
                if hasattr(response, 'embeddings') and response.embeddings:
                    return {'embedding': response.embeddings[0].values}
                return {'embedding': []}
                
            elif self.engine == "LEGACY":
                # Legacy SDK
                # task_type mapping
                # content
                result = genai_legacy.embed_content(
                    model="models/gemini-embedding-001",
                    content=text,
                    task_type=task_type,
                    title=title
                )
                return result

        except Exception as e:
             logger.error(f"❌ LLM Embed Content Failed ({self.engine}): {e}")
             raise

    @staticmethod
    def _safe_text(obj) -> str:
        """Extract .text from a Gemini response/chunk, suppressing SDK warnings."""
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            return getattr(obj, 'text', None) or ""

    def stream_content(self, prompt: str, **kwargs):
        """
        Stream text from LLM, yielding chunks as they arrive.
        Falls back to non-streaming generate_content() if streaming unavailable.
        """
        if self.engine == "NEW":
            try:
                config_args = {}
                if self.system_instruction:
                    config_args['system_instruction'] = self.system_instruction
                config = types.GenerateContentConfig(**config_args)

                chunks = []
                for chunk in self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                ):
                    text = self._safe_text(chunk)
                    if text:
                        chunks.append(text)
                        yield text
                # Log the full interaction after streaming completes
                full_text = "".join(chunks)
                self._record_token_usage(prompt, type('R', (), {'text': full_text})(),
                                         os.environ.get("NUCLEUS_SESSION_ID", "default"), "default")
                return
            except Exception as e:
                logger.warning(f"Streaming failed, falling back to non-stream: {e}")

        # Fallback: non-streaming (LEGACY engine or stream failure)
        response = self.generate_content(prompt, **kwargs)
        text = self._safe_text(response) or str(response)
        if text:
            yield text

    @property
    def active_engine(self):
        return self.engine

    # Alias for legacy support and autonomous self-healer compatibility
    generate = generate_content


# ============================================================
# ANTHROPIC / CLAUDE PROVIDER
# ============================================================

@dataclass
class AnthropicResponse:
    """Minimal response wrapper matching the Gemini response interface (.text)."""
    text: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


class AnthropicLLM:
    """
    Minimal Anthropic/Claude client that exposes the same generate_content()
    interface as DualEngineLLM.  Text generation only (no tools, no streaming).
    """

    DEFAULT_MODEL = "claude-sonnet-4-6-20250514"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        # Accept (and ignore) Gemini-specific kwargs so callers don't break
        tier: Optional[LLMTier] = None,
        job_type: Optional[str] = None,
        budget_mode: str = "balanced",
        **_ignored,
    ):
        self.api_key = api_key or os.environ.get("NUCLEUS_ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic provider selected but NUCLEUS_ANTHROPIC_API_KEY is not set. "
                "Set this env var or pass api_key= explicitly."
            )

        self.base_url = base_url or os.environ.get("NUCLEUS_ANTHROPIC_BASE_URL")
        self.model_name = model_name or os.environ.get(
            "NUCLEUS_ANTHROPIC_MODEL", self.DEFAULT_MODEL
        )
        self.system_instruction = system_instruction
        self.engine = "ANTHROPIC"
        self.tier = tier
        self.budget_mode = budget_mode

        # Lazy-import so the dep is only required when actually selected
        try:
            import anthropic  # noqa: F811
        except ImportError:
            import sys as _sys
            raise ImportError(
                "Anthropic provider selected but the 'anthropic' package is not installed. "
                f"Run: {_sys.executable} -m pip install anthropic"
            )

        client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = anthropic.Anthropic(**client_kwargs)

        logger.info(
            f"🔮 LLM Client: Anthropic Mode → {self.model_name}"
            + (f" (base_url={self.base_url})" if self.base_url else "")
        )

    # ── Core interface (matches DualEngineLLM) ──────────────

    def generate_content(self, prompt: str, **kwargs) -> AnthropicResponse:
        """Generate text via Anthropic Messages API."""
        # ── Token Budget Check ──
        session_id = os.environ.get("NUCLEUS_SESSION_ID", "default")
        agent_id = kwargs.pop("_agent_id", "default")
        try:
            from .token_budget import get_budget_manager
            budget = get_budget_manager()
            if not budget.can_execute(session_id=session_id, agent_id=agent_id):
                raise RuntimeError(
                    f"Token budget exceeded for session={session_id}, agent={agent_id}."
                )
        except ImportError:
            pass

        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        msg_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.system_instruction:
            msg_kwargs["system"] = self.system_instruction

        try:
            raw = self._client.messages.create(**msg_kwargs)
        except Exception as e:
            err_str = str(e)
            if any(code in err_str for code in ("429", "402", "rate_limit", "credit_limit", "overloaded")):
                logger.debug(f"Anthropic rate limited: {err_str[:60]}")
            else:
                logger.error(f"❌ Anthropic generate failed: {e}")
            raise

        # Extract text from content blocks
        text_parts = [
            block.text for block in raw.content if getattr(block, "text", None)
        ]
        response = AnthropicResponse(
            text="\n".join(text_parts),
            model=raw.model,
            usage={
                "input_tokens": raw.usage.input_tokens,
                "output_tokens": raw.usage.output_tokens,
            },
        )

        self._log_interaction(prompt, response)
        self._record_token_usage(prompt, response, session_id, agent_id)
        return response

    def stream_content(self, prompt, **kwargs):
        """
        Stream text from Anthropic, yielding chunks as they arrive.

        ``prompt`` can be:
        - a plain string  (single-turn, backward-compatible)
        - a list of dicts  (native multi-turn: [{"role": "user", "content": "..."},
                            {"role": "assistant", "content": "..."},...])

        Falls back to non-streaming generate_content() if streaming unavailable.
        """
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        # Build messages list — accept string or native messages array
        if isinstance(prompt, list):
            messages = prompt
        else:
            messages = [{"role": "user", "content": prompt}]

        msg_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if self.system_instruction:
            msg_kwargs["system"] = self.system_instruction

        try:
            chunks = []
            with self._client.messages.stream(**msg_kwargs) as stream:
                for text in stream.text_stream:
                    chunks.append(text)
                    yield text
            full_text = "".join(chunks)
            prompt_str = str(prompt) if isinstance(prompt, list) else prompt
            self._record_token_usage(
                prompt_str,
                AnthropicResponse(text=full_text),
                os.environ.get("NUCLEUS_SESSION_ID", "default"), "default",
            )
            return
        except Exception as e:
            logger.warning(f"Anthropic streaming failed, falling back: {e}")

        # Fallback: non-streaming
        response = self.generate_content(str(prompt) if isinstance(prompt, list) else prompt, **kwargs)
        if response.text:
            yield response.text

    # ── Native Tool Calling ─────────────────────────────────

    TOOLS = [
        {
            "name": "shell_execute",
            "description": "Execute a shell command. Use for CLI commands, system operations, and nucleus CLI (e.g. 'nucleus task list', 'nucleus engram search Q').",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"},
                },
                "required": ["command"],
            },
        },
        {
            "name": "read_file",
            "description": "Read the contents of a file. Use to understand code before editing, check configs, or review any text file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (absolute or relative to cwd)"},
                    "offset": {"type": "integer", "description": "Start reading from this line number (1-based). Optional."},
                    "limit": {"type": "integer", "description": "Maximum number of lines to read. Optional, defaults to 500."},
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content. Use to create new files or completely rewrite existing ones.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "The full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "edit_file",
            "description": "Make a surgical edit to a file by finding and replacing an exact string. Use for targeted code changes — safer than rewriting the whole file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "The exact text to find (must match uniquely)"},
                    "new_string": {"type": "string", "description": "The replacement text"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
        {
            "name": "search_files",
            "description": "Find files by name pattern using glob. Use to locate files in the project (e.g. '**/*.py', 'src/**/test_*.py').",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')"},
                    "path": {"type": "string", "description": "Directory to search in. Defaults to cwd."},
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "search_code",
            "description": "Search file contents for a regex pattern (like grep/ripgrep). Use to find function definitions, imports, usage patterns, or any text in code.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "File or directory to search in. Defaults to cwd."},
                    "glob": {"type": "string", "description": "Filter files by glob (e.g. '*.py'). Optional."},
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "write_engram",
            "description": "Save a piece of knowledge to the Sovereign Brain's persistent memory. Use to remember important facts about the codebase, architecture decisions, user preferences, or anything that should persist across sessions. The brain remembers what you write here.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short identifier (alphanumeric + _.-). E.g. 'fastapi_pattern', 'db.schema', 'user-pref-testing'"},
                    "value": {"type": "string", "description": "The knowledge to store. Be specific and useful for future sessions."},
                    "context": {"type": "string", "enum": ["Feature", "Architecture", "Brand", "Strategy", "Decision"], "description": "Category. Use Architecture for code patterns, Feature for capabilities, Decision for choices made, Strategy for plans."},
                    "intensity": {"type": "integer", "description": "Importance 1-10 (10=critical). Default 5."},
                },
                "required": ["key", "value", "context"],
            },
        },
        {
            "name": "search_engrams",
            "description": "Search the Sovereign Brain's persistent memory for relevant knowledge. Use before making assumptions about the codebase, to recall past decisions, or to find context from previous sessions. Returns matching engrams sorted by importance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term to match against engram keys and values"},
                    "limit": {"type": "integer", "description": "Max results to return. Default 5."},
                },
                "required": ["query"],
            },
        },
        {
            "name": "list_tasks",
            "description": "List tasks from the Sovereign Brain's task backlog. Use to see what needs to be done, check task status, or find tasks to work on.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "DONE", "BLOCKED"], "description": "Filter by status. Optional — omit to list all."},
                },
                "required": [],
            },
        },
        {
            "name": "add_task",
            "description": "Create a new task in the Sovereign Brain's backlog. Use to track work that needs to be done, plan next steps, or create follow-ups from the current conversation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "What needs to be done. Be specific and actionable."},
                    "priority": {"type": "integer", "description": "1 (highest) to 5 (lowest). Default 3."},
                },
                "required": ["description"],
            },
        },
        {
            "name": "update_task",
            "description": "Update an existing task's status or fields. Use to mark tasks done, change priority, or update descriptions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID or exact description to find"},
                    "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "DONE", "BLOCKED"], "description": "New status"},
                    "priority": {"type": "integer", "description": "New priority (1-5)"},
                },
                "required": ["task_id"],
            },
        },
    ]

    def stream_with_tools(self, messages, **kwargs):
        """
        Stream from Anthropic with native tool calling.

        Yields text chunks as they arrive. After the stream completes, the caller
        should check `self.last_tool_calls` for any tool_use blocks.

        Args:
            messages: list of {"role": ..., "content": ...} dicts
        """
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        msg_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "messages": messages,
            "tools": self.TOOLS,
        }
        if self.system_instruction:
            msg_kwargs["system"] = self.system_instruction

        self.last_tool_calls = []  # Reset
        self.last_stop_reason = None

        try:
            text_chunks = []
            with self._client.messages.stream(**msg_kwargs) as stream:
                for event in stream:
                    # Text delta events
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_delta':
                            delta = event.delta
                            if hasattr(delta, 'text'):
                                text_chunks.append(delta.text)
                                yield delta.text
                # After stream ends, get the final message for tool_use blocks
                final = stream.get_final_message()
                self.last_stop_reason = final.stop_reason
                for block in final.content:
                    if block.type == "tool_use":
                        self.last_tool_calls.append({
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

            full_text = "".join(text_chunks)
            prompt_str = str(messages)[:5000]
            self._record_token_usage(
                prompt_str,
                AnthropicResponse(text=full_text, usage={
                    "input_tokens": final.usage.input_tokens,
                    "output_tokens": final.usage.output_tokens,
                }),
                os.environ.get("NUCLEUS_SESSION_ID", "default"), "default",
            )
        except Exception as e:
            err_str = str(e)
            if any(code in err_str for code in ("429", "402", "rate_limit", "credit_limit", "overloaded")):
                logger.debug(f"Anthropic rate limited: {err_str[:60]}")
            else:
                logger.warning(f"Anthropic stream_with_tools failed: {e}")
            raise

    # Alias
    generate = generate_content

    # ── Logging (mirrors DualEngineLLM) ─────────────────────

    def _log_interaction(self, prompt: str, response: AnthropicResponse):
        try:
            from .common import get_brain_path
            brain_path = get_brain_path()
            raw_path = brain_path / "raw"
            raw_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filename = raw_path / f"llm_interaction_{timestamp}.json"
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "engine": self.engine,
                "model": self.model_name,
                "prompt": str(prompt)[:5000],
                "response_text": response.text,
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to log interaction: {e}")

    def _record_token_usage(self, prompt: str, response: AnthropicResponse, session_id: str = "default", agent_id: str = "default"):
        try:
            from .token_budget import get_budget_manager, estimate_tokens
            input_tokens = response.usage.get("input_tokens") or estimate_tokens(str(prompt))
            output_tokens = response.usage.get("output_tokens") or estimate_tokens(response.text)
            get_budget_manager().record_usage(
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                session_id=session_id,
                agent_id=agent_id,
            )
        except Exception as e:
            logger.debug(f"Token usage recording skipped: {e}")

    @property
    def active_engine(self):
        return self.engine


# ============================================================
# PROVIDER FACTORY
# ============================================================

# ============================================================
# GROQ PROVIDER (OpenAI-compatible, free tier: 30 RPM)
# ============================================================

@dataclass
class GroqResponse:
    """Minimal response wrapper matching the Gemini response interface (.text)."""
    text: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


class GroqLLM:
    """
    Groq client using OpenAI-compatible API. Exposes same generate_content()
    interface as DualEngineLLM. Supports Llama, Mixtral, Gemma models at
    lightning speed with a generous free tier (30 RPM).

    Config env vars:
      NUCLEUS_GROQ_API_KEY    (required)
      NUCLEUS_GROQ_MODEL      (optional, default: llama-3.3-70b-versatile)
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_MAX_TOKENS = 4096
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        api_key: Optional[str] = None,
        # Accept (and ignore) Gemini-specific kwargs so callers don't break
        tier: Optional[LLMTier] = None,
        job_type: Optional[str] = None,
        budget_mode: str = "balanced",
        **_ignored,
    ):
        self.api_key = api_key or os.environ.get("NUCLEUS_GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq provider selected but NUCLEUS_GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com and set this env var."
            )

        self.model_name = model_name or os.environ.get(
            "NUCLEUS_GROQ_MODEL", self.DEFAULT_MODEL
        )
        self.system_instruction = system_instruction
        self.engine = "GROQ"
        self.tier = tier
        self.budget_mode = budget_mode

        # Use openai SDK with Groq's base_url
        try:
            from openai import OpenAI
        except ImportError:
            import sys as _sys
            raise ImportError(
                "Groq provider selected but the 'openai' package is not installed. "
                f"Run: {_sys.executable} -m pip install openai"
            )

        self._client = OpenAI(api_key=self.api_key, base_url=self.BASE_URL)

        logger.info(f"⚡ LLM Client: Groq Mode → {self.model_name}")

    # ── Core interface (matches DualEngineLLM) ──────────────

    def generate_content(self, prompt: str, **kwargs) -> GroqResponse:
        """Generate text via Groq's OpenAI-compatible chat completions."""
        session_id = os.environ.get("NUCLEUS_SESSION_ID", "default")
        agent_id = kwargs.pop("_agent_id", "default")
        try:
            from .token_budget import get_budget_manager
            budget = get_budget_manager()
            if not budget.can_execute(session_id=session_id, agent_id=agent_id):
                raise RuntimeError(
                    f"Token budget exceeded for session={session_id}, agent={agent_id}."
                )
        except ImportError:
            pass

        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        messages = []
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            raw = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
            )
        except Exception as e:
            err_str = str(e)
            if any(code in err_str for code in ("429", "402", "rate_limit", "credit_limit")):
                logger.debug(f"Groq rate limited: {err_str[:60]}")
            else:
                logger.error(f"❌ Groq generate failed: {e}")
            raise

        text = raw.choices[0].message.content if raw.choices else ""
        usage = {}
        if raw.usage:
            usage = {
                "input_tokens": raw.usage.prompt_tokens,
                "output_tokens": raw.usage.completion_tokens,
            }

        response = GroqResponse(text=text, model=raw.model, usage=usage)
        self._log_interaction(prompt, response)
        self._record_token_usage(prompt, response, session_id, agent_id)
        return response

    def stream_content(self, prompt, **kwargs):
        """
        Stream text from Groq, yielding chunks as they arrive.

        ``prompt`` can be:
        - a plain string  (single-turn, backward-compatible)
        - a list of dicts  (native multi-turn: [{"role": "user", "content": "..."},
                            {"role": "assistant", "content": "..."},...])
        """
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        # Build messages — accept string or native messages array
        if isinstance(prompt, list):
            messages = []
            if self.system_instruction:
                messages.append({"role": "system", "content": self.system_instruction})
            messages.extend(prompt)
        else:
            messages = []
            if self.system_instruction:
                messages.append({"role": "system", "content": self.system_instruction})
            messages.append({"role": "user", "content": prompt})

        try:
            chunks = []
            stream = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    chunks.append(delta.content)
                    yield delta.content
            full_text = "".join(chunks)
            prompt_str = str(prompt) if isinstance(prompt, list) else prompt
            self._record_token_usage(
                prompt_str,
                GroqResponse(text=full_text),
                os.environ.get("NUCLEUS_SESSION_ID", "default"), "default",
            )
            return
        except Exception as e:
            logger.warning(f"Groq streaming failed, falling back: {e}")

        # Fallback: non-streaming
        response = self.generate_content(str(prompt) if isinstance(prompt, list) else prompt, **kwargs)
        if response.text:
            yield response.text

    # ── Native Tool Calling (OpenAI-compatible function calling) ──

    TOOLS = [
        {"type": "function", "function": {
            "name": "shell_execute",
            "description": "Execute a shell command. Use for CLI commands, system operations, and nucleus CLI.",
            "parameters": {"type": "object", "properties": {
                "command": {"type": "string", "description": "The shell command to execute"},
            }, "required": ["command"]},
        }},
        {"type": "function", "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use to understand code before editing.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "File path (absolute or relative to cwd)"},
                "offset": {"type": "integer", "description": "Start line number (1-based). Optional."},
                "limit": {"type": "integer", "description": "Max lines to read. Optional, defaults to 500."},
            }, "required": ["path"]},
        }},
        {"type": "function", "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with given content.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string", "description": "Full file content to write"},
            }, "required": ["path", "content"]},
        }},
        {"type": "function", "function": {
            "name": "edit_file",
            "description": "Surgical edit: find exact old_string in file and replace with new_string.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "File path to edit"},
                "old_string": {"type": "string", "description": "Exact text to find (must match uniquely)"},
                "new_string": {"type": "string", "description": "Replacement text"},
            }, "required": ["path", "old_string", "new_string"]},
        }},
        {"type": "function", "function": {
            "name": "search_files",
            "description": "Find files by name pattern using glob (e.g. '**/*.py').",
            "parameters": {"type": "object", "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')"},
                "path": {"type": "string", "description": "Directory to search in. Defaults to cwd."},
            }, "required": ["pattern"]},
        }},
        {"type": "function", "function": {
            "name": "search_code",
            "description": "Search file contents for a regex pattern (like grep). Find functions, imports, usage.",
            "parameters": {"type": "object", "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "path": {"type": "string", "description": "File or directory to search. Defaults to cwd."},
                "glob": {"type": "string", "description": "Filter files by glob (e.g. '*.py'). Optional."},
            }, "required": ["pattern"]},
        }},
        {"type": "function", "function": {
            "name": "write_engram",
            "description": "Save knowledge to the Sovereign Brain's persistent memory. Survives across sessions.",
            "parameters": {"type": "object", "properties": {
                "key": {"type": "string", "description": "Short identifier (alphanumeric + _.-). E.g. 'fastapi_pattern', 'db.schema'"},
                "value": {"type": "string", "description": "The knowledge to store."},
                "context": {"type": "string", "enum": ["Feature", "Architecture", "Brand", "Strategy", "Decision"], "description": "Category."},
                "intensity": {"type": "integer", "description": "Importance 1-10 (10=critical). Default 5."},
            }, "required": ["key", "value", "context"]},
        }},
        {"type": "function", "function": {
            "name": "search_engrams",
            "description": "Search the Sovereign Brain's persistent memory for relevant knowledge from past sessions.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Search term to match against engram keys and values"},
                "limit": {"type": "integer", "description": "Max results. Default 5."},
            }, "required": ["query"]},
        }},
        {"type": "function", "function": {
            "name": "list_tasks",
            "description": "List tasks from the brain's backlog. See what needs doing.",
            "parameters": {"type": "object", "properties": {
                "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "DONE", "BLOCKED"], "description": "Filter by status. Optional."},
            }, "required": []},
        }},
        {"type": "function", "function": {
            "name": "add_task",
            "description": "Create a new task in the brain's backlog.",
            "parameters": {"type": "object", "properties": {
                "description": {"type": "string", "description": "What needs to be done."},
                "priority": {"type": "integer", "description": "1 (highest) to 5 (lowest). Default 3."},
            }, "required": ["description"]},
        }},
        {"type": "function", "function": {
            "name": "update_task",
            "description": "Update a task's status or priority.",
            "parameters": {"type": "object", "properties": {
                "task_id": {"type": "string", "description": "Task ID or description"},
                "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "DONE", "BLOCKED"], "description": "New status"},
                "priority": {"type": "integer", "description": "New priority (1-5)"},
            }, "required": ["task_id"]},
        }},
    ]

    def stream_with_tools(self, messages, **kwargs):
        """
        Stream from Groq with native function calling (OpenAI-compatible).

        Yields text chunks. After streaming, check self.last_tool_calls
        for any function calls.
        """
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        api_messages = []
        if self.system_instruction:
            api_messages.append({"role": "system", "content": self.system_instruction})
        if isinstance(messages, list):
            api_messages.extend(messages)
        else:
            api_messages.append({"role": "user", "content": messages})

        self.last_tool_calls = []
        self.last_stop_reason = None

        try:
            text_chunks = []
            tool_call_chunks = {}  # id -> {name, arguments_str}

            stream = self._client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                max_tokens=max_tokens,
                tools=self.TOOLS,
                stream=True,
            )

            for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue

                if choice.finish_reason:
                    self.last_stop_reason = choice.finish_reason

                delta = choice.delta
                # Text content
                if delta and delta.content:
                    text_chunks.append(delta.content)
                    yield delta.content

                # Tool call deltas
                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                "id": tc_delta.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc_delta.id:
                            tool_call_chunks[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_call_chunks[idx]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_call_chunks[idx]["arguments"] += tc_delta.function.arguments

            # Parse accumulated tool calls
            for idx in sorted(tool_call_chunks.keys()):
                tc = tool_call_chunks[idx]
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {"command": tc["arguments"]}
                self.last_tool_calls.append({
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": args,
                })

            full_text = "".join(text_chunks)
            self._record_token_usage(
                str(messages)[:5000],
                GroqResponse(text=full_text),
                os.environ.get("NUCLEUS_SESSION_ID", "default"), "default",
            )
        except Exception as e:
            err_str = str(e)
            if any(code in err_str for code in ("429", "402", "rate_limit", "credit_limit")):
                logger.debug(f"Groq rate limited: {err_str[:60]}")
            else:
                logger.warning(f"Groq stream_with_tools failed: {e}")
            raise

    # Alias
    generate = generate_content

    # ── Logging (mirrors DualEngineLLM) ─────────────────────

    def _log_interaction(self, prompt: str, response: GroqResponse):
        try:
            from .common import get_brain_path
            brain_path = get_brain_path()
            raw_path = brain_path / "raw"
            raw_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filename = raw_path / f"llm_interaction_{timestamp}.json"
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "engine": self.engine,
                "model": self.model_name,
                "prompt": str(prompt)[:5000],
                "response_text": response.text,
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to log interaction: {e}")

    def _record_token_usage(self, prompt: str, response: GroqResponse, session_id: str = "default", agent_id: str = "default"):
        try:
            from .token_budget import get_budget_manager, estimate_tokens
            input_tokens = response.usage.get("input_tokens") or estimate_tokens(str(prompt))
            output_tokens = response.usage.get("output_tokens") or estimate_tokens(response.text)
            get_budget_manager().record_usage(
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                session_id=session_id,
                agent_id=agent_id,
            )
        except Exception as e:
            logger.debug(f"Token usage recording skipped: {e}")

    @property
    def active_engine(self):
        return self.engine


def get_llm_client(
    provider: Optional[str] = None,
    **kwargs,
) -> Union[DualEngineLLM, AnthropicLLM, GroqLLM]:
    """
    Factory that returns the right LLM client based on provider selection.

    Resolution order for provider:
      1. Explicit `provider` argument
      2. NUCLEUS_LLM_PROVIDER env var
      3. Default: "gemini"

    Any extra **kwargs are forwarded to the underlying client constructor.
    """
    provider = (
        provider
        or os.environ.get("NUCLEUS_LLM_PROVIDER", "gemini")
    ).strip().lower()

    if provider == "gemini":
        return DualEngineLLM(**kwargs)

    if provider == "anthropic":
        return AnthropicLLM(**kwargs)

    if provider == "groq":
        return GroqLLM(**kwargs)

    if provider in ("local", "third-brother", "ollama"):
        try:
            from ..sovereign.local_llm import LocalLLM
            return LocalLLM(**kwargs)
        except ImportError:
            raise ValueError(
                "Local provider not available in this build. "
                "Supported values: 'gemini', 'anthropic', 'groq'."
            )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        "Supported values: 'gemini', 'anthropic', 'groq', 'local'."
    )
