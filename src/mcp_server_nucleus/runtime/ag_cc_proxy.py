import logging
logger = logging.getLogger(__name__)
import sys
import subprocess
import json
import os
import argparse
from pathlib import Path

# Models exposed by the local Antigravity proxy. These are returned on
# /v1/models when Antigravity cannot dynamically fetch its list, and are also
# written to Claude Code's availableModels so the /model picker shows them.
FALLBACK_MODELS = [
    "gemini-3.1-pro-high",
    "gemini-3.1-pro-low",
    "gemini-3.6-flash-high",
    "gemini-3.6-flash-medium",
    "gemini-3.6-flash-low",
    "gemini-3.5-flash-high",
    "gemini-3.5-flash-medium",
    "gemini-3.5-flash-low",
    "claude-opus-4-6-thinking",
    "claude-sonnet-4-6",
    "gpt-oss-120b-medium",
]

def main():
    if "--help" in sys.argv:
        print("Usage: nucleus-ag-cc-proxy [start|accounts add|...] [--port PORT] [--debug] [--fallback]")
        print("       nucleus-ag-cc-proxy configure-claude-code [--port PORT]")
        print("       nucleus-ag-cc-proxy use-local-agy")
        sys.exit(0)
    
    try:
        import antigravity_proxy
    except ImportError:
        print("Error: antigravity_proxy package is not installed.")
        print("Please install it, e.g., with 'pip install ag-cc-proxy' or ensure you've installed with 'nucleus-mcp[full]'")
        sys.exit(1)
        
    if len(sys.argv) > 1 and sys.argv[1] == "configure-claude-code":
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--port", type=int, default=int(os.environ.get("AG_CC_PROXY_PORT", "8080")))
        args, _ = parser.parse_known_args(sys.argv[2:])
        port = args.port
        
        settings_path = Path.home() / ".claude" / "settings.json"
        
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                settings = {}
                
        if "env" not in settings:
            settings["env"] = {}
            
        base_url = f"http://localhost:{port}"
        settings["env"]["ANTHROPIC_BASE_URL"] = base_url
        
        if "ANTHROPIC_API_KEY" not in settings["env"]:
            settings["env"]["ANTHROPIC_API_KEY"] = "dummy"

        settings["env"]["CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT"] = "1"
        # Gateway discovery ON — adds all proxy /v1/models (including gemini-*)
        # to the picker as "From gateway" entries alongside the defaults.
        settings["env"]["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"

        # Claude Code rejects non-claude- model names client-side, so we expose
        # Gemini/GPT-OSS models with claude- prefixed aliases and use
        # modelOverrides to map them to the real model IDs the proxy expects.
        # Default models (Opus 5, Sonnet 5, Haiku 4.5) are kept and mapped to
        # their agy equivalents so they work through the proxy.
        picker_models = [
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-haiku-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-6-thinking",
            "claude-gemini-3.1-pro-high",
            "claude-gemini-3.1-pro-low",
            "claude-gemini-3.6-flash-high",
            "claude-gemini-3.6-flash-medium",
            "claude-gemini-3.6-flash-low",
            "claude-gemini-3.5-flash-high",
            "claude-gemini-3.5-flash-medium",
            "claude-gemini-3.5-flash-low",
            "claude-gpt-oss-120b",
        ]

        model_overrides = {
            # Defaults → agy equivalents
            "claude-opus-5": "claude-opus-4-6-thinking",
            "claude-sonnet-5": "claude-sonnet-4-6",
            "claude-haiku-4-5": "gemini-3.6-flash-high",
            # agy Claude models (pass through)
            "claude-sonnet-4-6": "claude-sonnet-4-6",
            "claude-opus-4-6-thinking": "claude-opus-4-6-thinking",
            # Gemini aliases → real model IDs
            "claude-gemini-3.1-pro-high": "gemini-3.1-pro-high",
            "claude-gemini-3.1-pro-low": "gemini-3.1-pro-low",
            "claude-gemini-3.6-flash-high": "gemini-3.6-flash-high",
            "claude-gemini-3.6-flash-medium": "gemini-3.6-flash-medium",
            "claude-gemini-3.6-flash-low": "gemini-3.6-flash-low",
            "claude-gemini-3.5-flash-high": "gemini-3.5-flash-high",
            "claude-gemini-3.5-flash-medium": "gemini-3.5-flash-medium",
            "claude-gemini-3.5-flash-low": "gemini-3.5-flash-low",
            # GPT-OSS alias
            "claude-gpt-oss-120b": "gpt-oss-120b-medium",
        }

        # Don't set availableModels — let defaults + gateway discovery
        # populate the picker naturally. modelOverrides maps defaults to
        # agy equivalents so they work through the proxy.
        settings.pop("availableModels", None)
        settings["modelOverrides"] = model_overrides
        settings["model"] = "claude-sonnet-5"

        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

        print(f"Configured Claude Code settings at {settings_path}")
        print(f"Set ANTHROPIC_BASE_URL to {base_url}")
        print("Set ANTHROPIC_API_KEY to dummy")
        print("Set CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT to 1")
        print("Gateway discovery ON (picker shows defaults + all agy models)")
        print("Removed availableModels (no duplicates)")
        print(f"Set modelOverrides for {len(model_overrides)} model mappings")
        print(f"Set default model to claude-sonnet-5 (→ claude-sonnet-4-6 via agy)")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "use-local-agy":
        try:
            from antigravity_proxy.auth import get_auth_status
            auth_data = get_auth_status()
            if not auth_data:
                raise ValueError("No auth data returned")
        except Exception:
            print("Could not read Antigravity auth. Make sure agy is installed and you are logged in (run `agy login` if needed).")
            sys.exit(1)
            
        email = auth_data.get("email", "default@antigravity") if isinstance(auth_data, dict) else "default@antigravity"
        if not email:
            email = "default@antigravity"
            
        from antigravity_proxy.config import ACCOUNT_CONFIG_PATH
        from datetime import datetime
        import shutil
        
        config_path = Path(ACCOUNT_CONFIG_PATH)
        if config_path.exists() and config_path.is_file():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{ACCOUNT_CONFIG_PATH}.bak.{timestamp}"
            shutil.copy2(config_path, backup_path)
            
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "accounts": [
                {
                    "email": email,
                    "source": "database"
                }
            ],
            "settings": {},
            "activeIndex": 0
        }
        
        config_path.write_text(json.dumps(config_data, indent=2) + "\n", encoding="utf-8")
        
        print(f"Switched to local Antigravity single-account mode for {email}.")
        print(f"Config written to {ACCOUNT_CONFIG_PATH}.")
        print("Restart the proxy to use the new account.")
        sys.exit(0)

    import time
    import antigravity_proxy.cloudcode as cc
    import antigravity_proxy.server as server

    original_list_models = cc.list_models

    async def _list_models(token):
        try:
            result = await original_list_models(token)
            if isinstance(result, dict) and result.get("data"):
                # Prefix non-claude model IDs with "claude-" so Claude Code's
                # gateway discovery shows them in the /model picker. The
                # modelOverrides mapping in configure-claude-code maps them
                # back to the real IDs when sending messages.
                for m in result["data"]:
                    mid = m.get("id", "")
                    if not mid.startswith("claude-"):
                        m["id"] = f"claude-{mid}"
                return result
        except Exception:
            logger.debug("Swallowed exception in main", exc_info=True)
            pass

        created_time = int(time.time())
        data = [
            {
                "id": (m if m.startswith("claude-") else f"claude-{m}"),
                "object": "model",
                "created": created_time,
                "owned_by": "antigravity",
                "description": m
            }
            for m in FALLBACK_MODELS
        ]

        return {"object": "list", "data": data}

    cc.list_models = _list_models
    if hasattr(server, 'list_models'):
        server.list_models = _list_models

    # Strip the "claude-" prefix from non-Claude model IDs before the proxy
    # sends the request to Google. This reverses the prefix we added in
    # _list_models so gateway discovery shows Gemini/GPT-OSS models.
    original_send_message = cc.send_message
    original_send_message_stream = cc.send_message_stream

    def _strip_prefix(req):
        model = req.get("model", "")
        # Only strip if it's a prefixed non-Claude model (e.g.
        # "claude-gemini-3.1-pro-high" → "gemini-3.1-pro-high")
        if model.startswith("claude-gemini-") or model.startswith("claude-gpt-"):
            req["model"] = model[len("claude-"):]
        return req

    async def _send_message(req, *args, **kwargs):
        return await original_send_message(_strip_prefix(req), *args, **kwargs)

    async def _send_message_stream(req, *args, **kwargs):
        async for chunk in original_send_message_stream(_strip_prefix(req), *args, **kwargs):
            yield chunk

    cc.send_message = _send_message
    cc.send_message_stream = _send_message_stream
    if hasattr(server, 'send_message'):
        server.send_message = _send_message
    if hasattr(server, 'send_message_stream'):
        server.send_message_stream = _send_message_stream

    from antigravity_proxy.__main__ import main as ag_main
    sys.exit(ag_main())

if __name__ == "__main__":
    main()
