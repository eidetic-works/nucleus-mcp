"""HUD dashboard frontend-file verification.

Walks the expected React component tree under ``<HUD_ROOT>`` and checks for
required component files + a minimal content-sanity signature on AgentCard.

HUD root resolves through env:

- ``NUCLEUS_HUD_ROOT`` wins.
- Fallback: ``<NUCLEUS_ROOT>/tools/nucleus-hud`` via ``paths.nucleus_root``.

Usage: ``python -m mcp_server_nucleus.diagnostics.dashboard``
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from mcp_server_nucleus.paths import nucleus_root

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("VERIFY_DASHBOARD")


def _hud_root() -> Path:
    env = os.environ.get("NUCLEUS_HUD_ROOT")
    if env:
        return Path(env)
    return nucleus_root() / "tools" / "nucleus-hud"


def verify_files_exist(hud_root: Path) -> bool:
    logger.info("Step 1: check frontend files...")
    files = [
        hud_root / "app" / "components" / "marketplace" / "AgentCard.tsx",
        hud_root / "app" / "components" / "marketplace" / "MarketplaceGrid.tsx",
        hud_root / "app" / "marketplace" / "page.tsx",
    ]
    all_exist = True
    for f in files:
        if not f.exists():
            logger.error(f"MISSING: {f}")
            all_exist = False
        else:
            logger.info(f"FOUND: {f.name}")
    return all_exist


def verify_content(hud_root: Path) -> bool:
    logger.info("Step 2: verify content...")
    card = hud_root / "app" / "components" / "marketplace" / "AgentCard.tsx"
    if card.exists():
        content = card.read_text()
        if "interface Agent" not in content:
            logger.error("AgentCard missing interface definition")
            return False
        if "export default function AgentCard" not in content:
            logger.error("AgentCard missing export default")
            return False
    logger.info("content checks passed.")
    return True


def main() -> int:
    hud_root = _hud_root()
    if not hud_root.exists():
        logger.error(f"HUD root not found at {hud_root}")
        return 1
    if not verify_files_exist(hud_root):
        return 1
    if not verify_content(hud_root):
        return 1
    logger.info("ALL DASHBOARD CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
