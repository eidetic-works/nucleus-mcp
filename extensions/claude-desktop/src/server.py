"""Claude Desktop .mcpb entry point for nucleus-mcp (uv runtime).

The host launches this via ``uv run --directory <ext-dir> src/server.py``. uv
installs ``nucleus-mcp`` from PyPI per the bundle ``pyproject.toml`` (prebuilt
wheels — no compiled deps are bundled), then this shim hands off to the packaged
stdio server. No product source is bundled: the published wheel is the single
source of truth, so the bundle stays tiny and is always current.

Brain-path resolution is intentionally left to nucleus's own discovery order
(NUCLEUS_BRAIN_PATH env -> walk up from CWD -> $HOME/.nucleus/brain), so a
desktop install lands on the stable per-user brain rather than the ephemeral
extension directory.
"""

from mcp_server_nucleus import main

if __name__ == "__main__":
    main()
