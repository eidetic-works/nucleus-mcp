"""
Nucleus Governance Gateway
==========================
Parameterized traffic controller and model rotation layer.
Supports: Gemini (Google), Claude (Anthropic), OpenAI (Standard/Codex).

Strategic Role:
- Public: Ethical quota management and usage governance.
- Sovereign: High-availability multiplexing and automated fallback.
"""

import json
import logging
import ssl
import os
import re
import time
import socket
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("NucleusGateway")

# Avoid SSL warnings locally
import urllib3
urllib3.disable_warnings()

# ============================================================
# CONFIGURATION & PERSISTENCE
# ============================================================

DEFAULT_GATEWAY_CONFIG = {
    "port": 5056,
    "providers": {
        "gemini": {
            "keys": [k for k in os.environ.get("GEMINI_API_KEY_POOL", "").split(":") if k],
            "model_priority": [
                "gemini-3.1-pro-preview",
                "gemini-3-pro-preview",
                "gemini-2.5-pro",
                "gemini-3-flash-preview",
                "gemini-2.5-flash",
                "gemini-3.1-flash-lite-preview",
                "gemini-2.5-flash-lite"
            ]
        },
        "anthropic": {
            "keys": [],
            "models": ["claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"]
        },
        "openai": {
            "keys": [],
            "models": ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]
        }
    }
}

class GatewayManager:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.config_path = brain_path / "config" / "gateway.json"
        self.metadata_path = brain_path / "metadata" / "gateway_state.json"
        self.config = self._load_config()
        self.state = self._load_state()
        
        # In-memory transient state (rate limits)
        self.exhausted_until = {} # key_id -> {model -> timestamp}

    def _load_config(self) -> Dict:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except Exception as e:
                logger.error(f"Failed to load gateway config: {e}")
        return DEFAULT_GATEWAY_CONFIG

    def _load_state(self) -> Dict:
        if self.metadata_path.exists():
            try:
                return json.loads(self.metadata_path.read_text())
            except: pass
        return {"keys": {}}

    def save_state(self):
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(json.dumps(self.state, indent=2))

    def get_working_keys(self, provider: str, model_name: str) -> List[str]:
        keys = self.config["providers"].get(provider, {}).get("keys", [])
        now = time.time()
        working = []
        for k in keys:
            until = self.exhausted_until.get(k, {}).get(model_name, 0)
            if now > until:
                working.append(k)
        return working

    def mark_exhausted(self, key: str, model: str, duration: int = 65):
        if key not in self.exhausted_until:
            self.exhausted_until[key] = {}
        self.exhausted_until[key][model] = time.time() + duration

    def render_dashboard(self) -> str:
        """Render a visual ASCII dashboard of model usage and key health."""
        now = time.time()
        output = []
        output.append("\n🛡️  Nucleus Governance Gateway | Sovereign View")
        output.append("=" * 60)
        
        # 1. Model Usage Bars
        output.append("\nModel Usage (Aggregate)")
        
        # Logic: Calculate % based on known free-tier limits (rough estimate for visualization)
        # In a real run, this would query the state for actual usage metadata.
        limits = {"pro": 20, "flash": 200, "lite": 1500} # RPD examples
        
        for model_type, limit in limits.items():
            # Estimate usage from current transient state (exhausted keys)
            exhausted_count = 0
            for key in self.config["providers"]["gemini"]["keys"]:
                for m in self.config["providers"]["gemini"]["model_priority"]:
                    if model_type in m and now < self.exhausted_until.get(key, {}).get(m, 0):
                        exhausted_count += 1
                        break
            
            total_keys = len(self.config["providers"]["gemini"]["keys"])
            usage_pct = int((exhausted_count / total_keys) * 100) if total_keys > 0 else 0
            
            bar_len = 30
            filled = int((usage_pct / 100) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            
            # Color coding (simulated via text label)
            status = "OK" if usage_pct < 80 else "CRITICAL"
            output.append(f"   {model_type.capitalize():10} [{bar}] {usage_pct:3}% | {status}")

        # 2. Key Governance HUD
        output.append("\nKey Health (Gemini Multiplexer)")
        for i, key in enumerate(self.config["providers"]["gemini"]["keys"]):
            state = self.state["keys"].get(key, {}).get("tier", "PAID")
            
            # Find the most recently used model for this key to show its remaining quota
            latest_rem = "N/A"
            for m in self.config["providers"]["gemini"]["model_priority"]:
                val = self.state["keys"].get(key, {}).get(f"remaining_{m}")
                if val: 
                    latest_rem = f"{val} reqs"
                    break

            # Check if ANY model is exhausted for this key
            is_rate_limited = False
            for m, until in self.exhausted_until.get(key, {}).items():
                if now < until:
                    is_rate_limited = True
                    break
            
            icon = "🔴" if is_rate_limited else "🟢"
            output.append(f"   Key {i+1}: {icon} {key[:8]}... [{state:4}] | Rem: {latest_rem}")

        output.append("\n" + "-" * 60)
        output.append(f"📍 API Discovery: http://127.0.0.1:{self.config['port']}")
        output.append(f"⏰ Next Refresh: {time.strftime('%H:%M:%S', time.localtime(now + 60))}")
        
        return "\n".join(output)

# ============================================================
# PROXY HANDLER
# ============================================================

class GovernanceGatewayHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    manager: GatewayManager = None

    def do_GET(self): self._handle_any('GET')
    def do_POST(self): self._handle_any('POST')
    def do_PUT(self): self._handle_any('PUT')

    def _handle_any(self, method: str):
        # 1. Determine Provider
        provider = self._detect_provider()
        
        # 2. Dispatch to provider-specific logic
        if provider == "gemini":
            self._proxy_gemini(method)
        elif provider == "anthropic":
            self._proxy_anthropic(method)
        elif provider == "openai":
            self._proxy_openai(method)
        else:
            self.send_error(400, f"Unsupported provider or path: {self.path}")

    def _detect_provider(self) -> str:
        if "generativelanguage.googleapis.com" in self.path or "models/gemini" in self.path:
            return "gemini"
        if "anthropic.com" in self.path or "/v1/messages" in self.path:
            return "anthropic"
        if "api.openai.com" in self.path or "/v1/chat/completions" in self.path:
            return "openai"
        return "unknown"

    # --- GEMINI IMPLEMENTATION (Sovereign Multiplexing) ---
    def _proxy_gemini(self, method: str):
        path = self.path
        base_path = path.split("?key=")[0] if "?key=" in path else path.split("?")[0]
        queryParams = path.split("?")[1] if "?" in path else ""
        
        # Extract requested model
        requested_model = "unknown"
        priority_list = self.manager.config["providers"]["gemini"]["model_priority"]
        for m in priority_list:
            if m in base_path:
                requested_model = m
                break
        
        fallback_models = priority_list
        if requested_model in priority_list:
            start_idx = priority_list.index(requested_model)
            fallback_models = priority_list[start_idx:]

        body = self._get_body()
        headers = self._get_filtered_headers()

        for current_model in fallback_models:
            working_keys = self.manager.get_working_keys("gemini", current_model)
            if not working_keys: continue

            for active_key in working_keys:
                # Pre-check tier for Pro models (Optimization)
                if "pro" in current_model:
                    tier = self.manager.state["keys"].get(active_key, {}).get("tier", "UNKNOWN")
                    if tier == "FREE": continue

                active_base_path = base_path
                if current_model != requested_model:
                    active_base_path = re.sub(r'models/gemini-[^:]+', f'models/{current_model}', base_path)

                req_url = f"https://generativelanguage.googleapis.com{active_base_path}?key={active_key}"
                parts = [p for p in queryParams.split("&") if not p.startswith("key=") and p]
                if parts: req_url += "&" + "&".join(parts)

                if self._execute_remote_call(req_url, method, body, headers, "gemini", active_key, current_model):
                    return

        self.send_error(503, "Nucleus Gateway: All Gemini resources exhausted.")

    # --- ANTHROPIC/OPENAI PLACEHOLDERS (To be expanded as keys are added) ---
    def _proxy_anthropic(self, method: str):
        self._proxy_standard("anthropic", "https://api.anthropic.com", method)

    def _proxy_openai(self, method: str):
        self._proxy_standard("openai", "https://api.openai.com", method)

    def _proxy_standard(self, provider: str, base_url: str, method: str):
        keys = self.manager.config["providers"][provider]["keys"]
        if not keys:
            # Pass-through if no keys configured in gateway
            req_url = f"{base_url}{self.path}"
            self._execute_remote_call(req_url, method, self._get_body(), self._get_filtered_headers(), provider, "pass-through")
            return

        body = self._get_body()
        headers = self._get_filtered_headers()
        
        for key in keys:
            req_url = f"{base_url}{self.path}"
            # Inject key into header
            if provider == "anthropic": headers["x-api-key"] = key
            if provider == "openai": headers["Authorization"] = f"Bearer {key}"
            
            if self._execute_remote_call(req_url, method, body, headers, provider, key):
                return
        
        self.send_error(503, f"Nucleus Gateway: All {provider} keys exhausted.")

    # --- SHARED UTILS ---

    def _get_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(content_length) if content_length > 0 else None

    def _get_filtered_headers(self):
        return {k: v for k, v in self.headers.items() if k.lower() not in ['host', 'connection', 'content-length', 'transfer-encoding']}

    def _record_usage_metrics(self, provider: str, model: str, req_body: bytes, resp_body: bytes, key_id: str, resp_headers: List = None):
        """Extract and record token usage and rate limits from the LLM response."""
        try:
            from .token_budget import get_budget_manager, estimate_tokens
            
            input_tokens = 0
            output_tokens = 0
            
            # 1. Parse Token Usage
            try:
                data = json.loads(resp_body)
                if provider == "gemini":
                    usage = data.get("usageMetadata", {})
                    input_tokens = usage.get("promptTokenCount", 0)
                    output_tokens = usage.get("candidatesTokenCount", 0)
                elif provider in ("openai", "anthropic"):
                    usage = data.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
                    output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
            except: pass

            # 2. Parse Rate Limit Headers
            if resp_headers:
                for k, v in resp_headers:
                    k = k.lower()
                    # Capture common rate limit headers
                    if any(x in k for x in ["ratelimit-remaining", "quota-remaining"]):
                        if "keys" not in self.manager.state: self.manager.state["keys"] = {}
                        if key_id not in self.manager.state["keys"]: self.manager.state["keys"][key_id] = {}
                        self.manager.state["keys"][key_id][f"remaining_{model}"] = v
                self.manager.save_state()

            # Fallback to estimation
            if input_tokens == 0 and req_body: 
                input_tokens = estimate_tokens(req_body.decode('utf-8', errors='ignore'))
            if output_tokens == 0 and resp_body: 
                output_tokens = estimate_tokens(resp_body.decode('utf-8', errors='ignore'))
            
            get_budget_manager().record_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                session_id=self.headers.get("NUCLEUS_SESSION_ID", "gateway_session"),
                agent_id=self.headers.get("NUCLEUS_AGENT_ID", "external_agent")
            )
        except Exception as e:
            logger.debug(f"Metrics recording failed: {e}")

    def _execute_remote_call(self, url: str, method: str, body: bytes, headers: Dict, provider: str, key_id: str, model: str = "any") -> bool:
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, context=ctx, timeout=60) as response:
                self.send_response(response.status)
                for k, v in response.getheaders():
                    if k.lower() not in ['transfer-encoding', 'content-encoding']:
                        self.send_header(k, v)
                self.end_headers()
                
                resp_data = response.read()
                self.wfile.write(resp_data)

                # DEBUG: Log all headers to find rate limit keys
                logger.info(f"🔍 Gateway Headers: {dict(response.getheaders())}")

                # Record usage metrics (with headers for rate limit tracking)
                self._record_usage_metrics(provider, model, body, resp_data, key_id, response.getheaders())
                
                logger.info(f"✅ [{provider}] {model} -> 200 OK (Key: {key_id[:8]}...)")
                return True
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            msg = ""
            try: msg = json.loads(resp_body).get("error", {}).get("message", "").lower()
            except: pass

            if e.code == 429 or "quota" in msg or "exhausted" in msg:
                self.manager.mark_exhausted(key_id, model)
                logger.warning(f"⚠️ [{provider}] Key Exhausted: {key_id[:8]} for {model}")
                return False # Try next
            
            if e.code == 403 and provider == "gemini" and "pro" in model:
                self.manager.state["keys"][key_id] = {"tier": "FREE"}
                self.manager.save_state()
                return False # Try next model
                
            # Real error - forward to client
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(resp_body)
            return True
        except Exception as e:
            logger.error(f"❌ Gateway Network Error: {e}")
            return False

# ============================================================
# LIFECYCLE
# ============================================================

def run_gateway(brain_path: Path, port: int = 5056):
    manager = GatewayManager(brain_path)
    GovernanceGatewayHandler.manager = manager
    
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, GovernanceGatewayHandler)
    
    # Register port for auto-discovery
    port_file = Path(tempfile.gettempdir()) / "gemini_proxy.port"
    port_file.write_text(str(port))
    
    logger.info(f"🚀 Nucleus Governance Gateway online at http://127.0.0.1:{port}")
    logger.info(f"📍 Discovery: {port_file}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Gateway shutting down...")
        port_file.unlink(missing_ok=True)
        httpd.server_close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", type=Path, default=Path("./.brain"))
    parser.add_argument("--port", type=int, default=5056)
    args = parser.parse_args()
    run_gateway(args.brain, args.port)
