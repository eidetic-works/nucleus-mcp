"""
nucleus-rabbithole — Rabbit-Hole Depth Tracker.

A self-contained MCP server that ships inside the nucleus-mcp package but is
deliberately import-independent: it imports ONLY stdlib and the ``mcp``
package. Nothing from sibling ``mcp_server_nucleus`` modules is imported here
or in any other file within this subpackage.

Console entry-point: ``nucleus-rabbithole``
Module entry-point:  ``python -m mcp_server_nucleus.rabbithole``
"""

__version__ = "0.1.0"

from . import store

__all__ = ["store", "__version__"]
