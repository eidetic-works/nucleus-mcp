"""Feature tracking, proof, and mounter tools.

Super-Tools Facade: All 16 feature/proof/mounter actions exposed via a single
`nucleus_features(action, params)` MCP tool (async for mounter support).
"""

import json
from typing import Dict, List, Any, Optional

from ._dispatch import async_dispatch


def register(mcp, helpers):
    """Register the nucleus_features facade tool with the MCP server."""
    make_response = helpers["make_response"]

    from ..runtime.feature_ops import (
        _add_feature, _list_features, _get_feature,
        _update_feature, _mark_validated, _search_features
    )

    def _h_add(product, name, description, source, version, how_to_test,
               expected_result, status="development", tags=None):
        kwargs = {}
        if tags:
            kwargs["tags"] = tags
        return _add_feature(product, name, description, source, version,
                            how_to_test, expected_result, status, **kwargs)

    def _h_update(feature_id, status=None, description=None, version=None):
        updates = {}
        if status:
            updates["status"] = status
        if description:
            updates["description"] = description
        if version:
            updates["version"] = version
        if not updates:
            return {"error": "No updates provided"}
        return _update_feature(feature_id, **updates)

    async def _h_mount(name, command, args=[]):
        try:
            from ..runtime.mounter_ops import _brain_mount_server_impl
            return await _brain_mount_server_impl(name, command, args)
        except Exception as e:
            return f"Error mounting server: {e}"

    async def _h_thanos():
        try:
            from ..runtime.mounter_ops import _brain_thanos_snap_impl
            return await _brain_thanos_snap_impl()
        except Exception as e:
            return f"Error during Thanos Snap: {e}"

    async def _h_unmount(server_id):
        try:
            from ..runtime.mounter_ops import _brain_unmount_server_impl
            return await _brain_unmount_server_impl(server_id)
        except Exception as e:
            return f"Error unmounting server: {e}"

    async def _h_discover(server_id=None):
        try:
            from ..runtime.mounter_ops import _brain_discover_mounted_tools_impl
            return await _brain_discover_mounted_tools_impl(server_id)
        except Exception as e:
            return make_response(False, error=str(e))

    async def _h_invoke(server_id, tool_name, arguments={}):
        try:
            from ..runtime.mounter_ops import _brain_invoke_mounted_tool_impl
            return await _brain_invoke_mounted_tool_impl(server_id, tool_name, arguments)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    async def _h_traverse(root_mount_id):
        try:
            from ..runtime.mounter_ops import _brain_traverse_and_mount_impl
            return await _brain_traverse_and_mount_impl(root_mount_id)
        except Exception as e:
            return make_response(False, error=str(e))

    def _h_gen_proof(feature_id, thinking=None, deployed_url=None,
                     files_changed=None, risk_level="low", rollback_time="15 minutes"):
        from ..runtime.proof_ops import _brain_generate_proof_impl
        return _brain_generate_proof_impl(feature_id, thinking, deployed_url,
                                          files_changed or [], risk_level, rollback_time)

    def _h_list_mounted():
        try:
            from ..runtime.mounter_ops import _brain_list_mounted_impl
            return _brain_list_mounted_impl()
        except Exception as e:
            return make_response(False, error=str(e))

    ROUTER = {
        "add": _h_add,
        "list": lambda product=None, status=None, tag=None: _list_features(product, status, tag),
        "get": lambda feature_id: _get_feature(feature_id),
        "update": _h_update,
        "validate": lambda feature_id, result: _mark_validated(feature_id, result),
        "search": lambda query: _search_features(query),
        "mount_server": _h_mount,
        "thanos_snap": _h_thanos,
        "unmount_server": _h_unmount,
        "list_mounted": _h_list_mounted,
        "discover_tools": _h_discover,
        "invoke_tool": _h_invoke,
        "traverse_mount": _h_traverse,
        "generate_proof": _h_gen_proof,
        "get_proof": lambda feature_id: __import__('mcp_server_nucleus.runtime.proof_ops', fromlist=['_brain_get_proof_impl'])._brain_get_proof_impl(feature_id),
        "list_proofs": lambda: __import__('mcp_server_nucleus.runtime.proof_ops', fromlist=['_brain_list_proofs_impl'])._brain_list_proofs_impl(),
    }

    @mcp.tool()
    async def nucleus_features(action: str, params: dict = {}) -> str:
        """Feature tracking, proof generation & MCP server mounting.

Actions:
  add             - Add a feature. params: {product, name, description, source, version, how_to_test, expected_result, status?, tags?}
  list            - List features. params: {product?, status?, tag?}
  get             - Get feature by ID. params: {feature_id}
  update          - Update feature fields. params: {feature_id, status?, description?, version?}
  validate        - Mark feature validated. params: {feature_id, result}
  search          - Search features. params: {query}
  mount_server    - Mount external MCP server. params: {name, command, args?}
  thanos_snap     - Trigger Instance Fractal Aggregation
  unmount_server  - Unmount MCP server. params: {server_id}
  list_mounted    - List mounted MCP servers
  discover_tools  - Discover tools from mounted servers. params: {server_id?}
  invoke_tool     - Invoke tool on mounted server. params: {server_id, tool_name, arguments?}
  traverse_mount  - Recursively mount downstream servers. params: {root_mount_id}
  generate_proof  - Generate proof document. params: {feature_id, thinking?, deployed_url?, files_changed?, risk_level?, rollback_time?}
  get_proof       - Get proof for a feature. params: {feature_id}
  list_proofs     - List all proof documents
"""
        return await async_dispatch(action, params, ROUTER, "nucleus_features")

    return [("nucleus_features", nucleus_features)]
