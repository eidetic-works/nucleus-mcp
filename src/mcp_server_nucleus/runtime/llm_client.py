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
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

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
    logger.info("✅ SDK: google-genai (new) available")
except ImportError:
    HAS_GENAI = False
    if os.environ.get("NUCLEUS_SKIP_AUTOSTART", "false").lower() != "true":
        logger.warning("⚠️ google-genai not installed. Falling back to legacy SDK.")

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
logger.info(f"🎯 SDK Selection: Using {_active}")


# ============================================================
# TIER ROUTER: Intelligent Multi-Tier LLM Selection
# ============================================================

class LLMTier(Enum):
    """Available LLM pricing/capability tiers."""
    PREMIUM = "premium"           # gemini-3-pro, highest capability
    STANDARD = "standard"         # gemini-2.5-flash, default production
    ECONOMY = "economy"           # gemini-2.5-flash-lite, background tasks
    LOCAL_PAID = "local_paid"     # API Key with billing
    LOCAL_FREE = "local_free"     # API Key free tier (100 req/day)


class TierRouter:
    """
    Intelligent router that selects the optimal LLM tier based on:
    - Job type (CRITICAL, RESEARCH, ORCHESTRATION, BACKGROUND, TESTING)
    - Budget mode (spartan, balanced, premium)
    - Quota availability (fallback on errors)
    """
    
    TIER_CONFIGS = {
        LLMTier.PREMIUM: {
            "model": "gemini-2.5-pro",  # Note: gemini-3-pro not yet in Vertex AI
            "platform": "vertex",
            "cost_level": "high",
            "description": "Advanced reasoning, complex architecture"
        },
        LLMTier.STANDARD: {
            "model": "gemini-2.5-flash",
            "platform": "vertex",
            "cost_level": "medium",
            "description": "Default production, 95% of work"
        },
        LLMTier.ECONOMY: {
            "model": "gemini-2.5-flash-lite",
            "platform": "vertex",
            "cost_level": "low",
            "description": "Background tasks, batch jobs"
        },
        LLMTier.LOCAL_PAID: {
            "model": "gemini-2.5-flash",
            "platform": "api_key",
            "cost_level": "medium",
            "description": "Fallback when Vertex fails"
        },
        LLMTier.LOCAL_FREE: {
            "model": "gemini-2.0-flash",
            "platform": "api_key",
            "cost_level": "free",
            "description": "Testing only, 100 req/day"
        },
    }
    
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
            model_name = self.tier_config["model"]
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
        force_vertex_env = os.environ.get("FORCE_VERTEX", "1") == "1"
        
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
                if use_vertex:
                    project_id = os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0894185576"))
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
            brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", "./.brain"))
            raw_path = brain_path / "raw"
            raw_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = raw_path / f"llm_interaction_{timestamp}.json"
            
            # Extract text from response (Best effort)
            response_text = "Unknown"
            if hasattr(response, 'text'):
                response_text = response.text
                
            data = {
                "timestamp": datetime.now().isoformat(),
                "engine": self.engine,
                "model": self.model_name,
                "prompt": str(prompt)[:5000], # Truncate massive prompts 
                "response_text": response_text
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to log interaction: {e}")

    def generate_content(self, prompt: str, **kwargs) -> Any:
        try:
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
                return response

            elif self.engine == "LEGACY":
                # Legacy SDK logic
                generation_config = {}
                # Legacy doesn't support tools same way here, basic text only for now or map tools manually
                # For Marketing Autopilot, we mostly use text.
                
                response = self.model.generate_content(prompt, generation_config=generation_config)
                self._log_interaction(prompt, response)
                return response

        except Exception as e:
            logger.error(f"❌ LLM Generate Content Failed ({self.engine}): {e}")
            raise

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
                    model="models/text-embedding-004", # Hardcoded or passed in
                    content=text,
                    task_type=task_type,
                    title=title
                )
                return result

        except Exception as e:
             logger.error(f"❌ LLM Embed Content Failed ({self.engine}): {e}")
             raise

    @property
    def active_engine(self):
        return self.engine
