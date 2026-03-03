import os
import json
import logging
import time
from pathlib import Path
import sys

# Logging setup
logger = logging.getLogger("nucleus.server")

# ============================================================
# MCP RESOURCES (Subscribable data)
# ============================================================

def register_resources(mcp, helpers):
    """Register all brain resources."""
    _get_state = helpers["get_state"]
    _read_events = helpers["read_events"]
    _get_triggers_impl = helpers.get("get_triggers_impl")
    _depth_show = helpers.get("depth_show")
    _resource_context_impl = helpers.get("resource_context_impl")

    @mcp.resource("brain://state")
    def resource_state() -> str:
        """Live state.json content - subscribable."""
        state = _get_state()
        return json.dumps(state, indent=2)

    @mcp.resource("brain://events")
    def resource_events() -> str:
        """Recent events - subscribable."""
        events = _read_events(limit=20)
        return json.dumps(events, indent=2)

    @mcp.resource("brain://triggers")
    def resource_triggers() -> str:
        """Trigger definitions - subscribable."""
        if _get_triggers_impl:
            triggers = _get_triggers_impl()
            return json.dumps(triggers, indent=2)
        return "{}"

    @mcp.resource("brain://depth")
    def resource_depth() -> str:
        """Current depth tracking state - subscribable. Shows where you are in the conversation tree."""
        if _depth_show:
            depth_state = _depth_show()
            return json.dumps(depth_state, indent=2)
        return "{}"

    @mcp.resource("brain://context")
    def resource_context() -> str:
        """Full context for cold start - auto-visible in sidebar. Click this first in any new session."""
        if _resource_context_impl:
            return _resource_context_impl()
        return "Context not available"

    @mcp.resource("brain://changes")
    def resource_changes() -> str:
        """Change ledger — poll THIS to detect staleness across all brain:// resources."""
        try:
            from .runtime.event_bus import get_change_ledger
            ledger = get_change_ledger()
            return json.dumps(ledger.get_snapshot(), indent=2)
        except Exception:
            return json.dumps({"global_version": 0, "uri_versions": {}, "recent_changes": []})

    @mcp.resource("brain://traces")
    def resource_traces() -> str:
        """Full list of recent DecisionMade traces - subscribable."""
        try:
            from .runtime.engram_ops import _dsor_query_decisions_impl
            return _dsor_query_decisions_impl(limit=50)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

# ============================================================
# MCP PROMPTS (Pre-built orchestration)
# ============================================================

def register_prompts(mcp, helpers):
    """Register all brain prompts."""
    _activate_synthesizer_prompt = helpers.get("activate_synthesizer_prompt")
    _start_sprint_prompt = helpers.get("start_sprint_prompt")
    _cold_start_prompt = helpers.get("cold_start_prompt")

    @mcp.prompt()
    def activate_synthesizer() -> str:
        """Activate Synthesizer agent to orchestrate the current sprint."""
        if _activate_synthesizer_prompt:
            return _activate_synthesizer_prompt()
        return "Prompt not available"

    @mcp.prompt()
    def start_sprint(goal: str = "MVP Launch") -> str:
        """Initialize a new sprint with the given goal."""
        if _start_sprint_prompt:
            return _start_sprint_prompt(goal)
        return "Prompt not available"

    @mcp.prompt()
    def cold_start() -> str:
        """Get instant context when starting a new session. Call this first in any new conversation."""
        if _cold_start_prompt:
            return _cold_start_prompt()
        return "Prompt not available"

def main():
    """Main entry point for the MCP server."""
    from . import mcp, get_brain_path, USE_STDIO_FALLBACK, __version__
    
    # Check for standalone/fallback mode
    if USE_STDIO_FALLBACK:
        from .runtime.stdio_server import StdioServer
        import logging
        import sys
        import asyncio
        
        # Configure logging to stderr to not corrupt stdout
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)
        
        server = StdioServer()
        asyncio.run(server.run())
        return

    # Helper to log to debug file
    def log_debug(msg):
        log_path = os.path.expanduser("~/.nucleus_mcp_debug.log")
        with open(log_path, "a", encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    
    # Phase 50: Initialize File Monitor for Native Sync (Tier 1-3)
    try:
        from .runtime.file_monitor import init_file_monitor, FileChangeEvent
        from .runtime.event_ops import _emit_event
        from .runtime.event_bus import get_event_bus, get_change_ledger, BrainFileEvent
        brain_path = get_brain_path()
        if brain_path and Path(brain_path).exists():
            # Wire ChangeLedger as EventBus subscriber for resource versioning
            _bus = get_event_bus()
            _ledger = get_change_ledger()
            _bus.subscribe("*", lambda evt: _ledger.record_change(evt.path, evt.event_type))
            log_debug("📋 ChangeLedger wired as EventBus subscriber")
            
            def _on_brain_file_change(event: FileChangeEvent):
                """Auto-emit brain events when .brain/ files change."""
                try:
                    rel_path = event.path.replace(brain_path, "").lstrip("/")
                    meaningful = ["tasks.json", "engrams.json", "state.json",
                                  "events.jsonl", "sessions/", "memory/", "ledger/",
                                  "commitments/", "config/"]
                    if any(m in rel_path for m in meaningful):
                        _emit_event(
                            f"file_{event.event_type}",
                            "FILE_MONITOR",
                            {"path": rel_path, "event_type": event.event_type},
                            f"Brain file {event.event_type}: {rel_path}"
                        )
                        # Publish to EventBus for subscriber distribution
                        _bus.publish(BrainFileEvent(
                            event_type=event.event_type,
                            path=rel_path,
                            source="FILE_MONITOR",
                        ))
                except Exception:
                    pass
            
            monitor = init_file_monitor(brain_path, on_change=_on_brain_file_change)
            monitor.start()
            log_debug(f"📡 File monitor initialized with event bridge for: {brain_path}")
    except ImportError as e:
        log_debug(f"File monitor not available: {e}")
    except Exception as e:
        log_debug(f"File monitor init failed: {e}")
    
    try:
        log_debug(f"Entering mcp.run() (Version {__version__})")
        mcp.run()
        log_debug("Exited mcp.run() normally")
    except Exception as e:
        log_debug(f"Exception in mcp.run(): {e}")
        import traceback
        log_path = os.path.expanduser("~/.nucleus_mcp_debug.log")
        with open(log_path, "a", encoding='utf-8') as f:
            traceback.print_exc(file=f)
        raise
