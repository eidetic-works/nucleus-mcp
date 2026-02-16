# Auto-generated from monolith decomposition
# =============================================================================
# v0.6.0 PROTOCOL COUPLING FIX - Tiered Tool Registration
# =============================================================================
# This wrapper ensures only tier-appropriate tools are registered with FastMCP.
# Without this, ALL tools would be registered regardless of NUCLEUS_TOOL_TIER.
# See: TITAN_HANDOVER_PROTOCOL.md Section 0 (Registry Bloat Solution)

from ..tool_tiers import is_tool_allowed, tier_manager
import sys

# State flag to prevent recursion when FastMCP internally calls mcp.tool
_REGISTERING_TOOL = False
_original_mcp_tool = None

def _tiered_tool_wrapper(*args, **kwargs):
    """
    Wrapper around mcp.tool() that checks tier before registration.
    
    Handles both decorator styles:
    - @mcp.tool     (func passed directly)
    - @mcp.tool()   (func is None, returns decorator)
    """
    global _REGISTERING_TOOL, _original_mcp_tool
    
    if _original_mcp_tool is None:
        raise RuntimeError("Tiered tool registration not configured. Call configure_tiered_tool_registration(mcp) first.")

    # If we are already in the middle of a registration, use the original method
    if _REGISTERING_TOOL:
        return _original_mcp_tool(*args, **kwargs)

    func = None
    if len(args) == 1 and callable(args[0]):
        func = args[0]
        args = args[1:]

    def decorator(fn):
        global _REGISTERING_TOOL
        tool_name = fn.__name__
        allowed = is_tool_allowed(tool_name)
        if allowed:
            tier_manager.registered_tools.add(tool_name)
            
            # Set flag and call original method
            _REGISTERING_TOOL = True
            try:
                # Register and capture the FunctionTool return
                tool = _original_mcp_tool(*args, **kwargs)(fn)
                
                # Make the FunctionTool object callable by proxying to the original function
                if not callable(tool):
                    class CallableTool:
                        def __init__(self, tool, original_fn):
                            self._tool = tool
                            self._fn = original_fn
                            # Copy metadata
                            self.__name__ = original_fn.__name__
                            self.__doc__ = original_fn.__doc__
                            self.__module__ = original_fn.__module__
                            
                        def __call__(self, *args, **kwargs):
                            print(f"[NUCLEUS] Executing {self.__name__}...", file=sys.stderr)
                            return self._fn(*args, **kwargs)
                            
                        def __getattr__(self, name):
                            return getattr(self._tool, name)
                            
                        # Pydantic serialization helpers
                        def model_dump(self, *args, **kwargs):
                            return self._tool.model_dump(*args, **kwargs)
                            
                        def model_dump_json(self, *args, **kwargs):
                            return self._tool.model_dump_json(*args, **kwargs)
                            
                    return CallableTool(tool, fn)
                
                return tool
            except Exception as e:
                print(f"[NUCLEUS] ERROR registering {tool_name}: {e}", file=sys.stderr)
                raise e
            finally:
                _REGISTERING_TOOL = False
        else:
            tier_manager.filtered_tools.add(tool_name)
            # Return plain function - NOT registered with MCP
            return fn
    
    if func is not None:
        return decorator(func)
    
    return decorator

def configure_tiered_tool_registration(mcp_instance):
    """Initializes the tiered tool registration system for the given MCP instance."""
    global _original_mcp_tool
    _original_mcp_tool = mcp_instance.tool
    mcp_instance.tool = _tiered_tool_wrapper
    return mcp_instance