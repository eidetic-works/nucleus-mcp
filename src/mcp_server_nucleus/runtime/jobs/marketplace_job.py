"""Marketplace Tier Promotion Loop (D5 §5).

Background task that walks ReputationSignals, recomputes TrustTier,
and updates CapabilityRegistry listings.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from mcp_server_nucleus.runtime.common import get_brain_path
from mcp_server_nucleus.runtime.marketplace import ReputationSignals, TrustTier, _get_registry_dir

logger = logging.getLogger("NucleusJobs.marketplace")


def run_tier_promotion_loop(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Walk all capabilities, recompute reputation, update tier if changed.

    Returns:
        Dict with stats on updated cards.
    """
    registry_dir = _get_registry_dir(brain_path)
    
    if not registry_dir.exists():
        logger.debug("tier_promotion_loop: registry dir absent, nothing to scan")
        return {"ok": True, "updated": 0, "total": 0}

    total_cards = 0
    updated_cards = 0

    for card_file in registry_dir.glob("*.json"):
        if not card_file.is_file():
            continue
            
        try:
            data = json.loads(card_file.read_text(encoding="utf-8"))
            address = data.get("address")
            if not address:
                continue
                
            total_cards += 1
            
            # Compute fresh signals
            metrics = ReputationSignals.compute_signals(address, brain_path=brain_path)
            
            # Evaluate tier
            current_tier = data.get("tier", TrustTier.UNVERIFIED)
            new_tier = TrustTier.evaluate(data, metrics)
            
            # Update connection count (often used for ranking even if tier stays same)
            old_conn_count = data.get("connection_count", 0)
            new_conn_count = metrics.get("connection_count", 0)
            
            changed = False
            if current_tier != new_tier:
                data["tier"] = new_tier
                data["tier_badge"] = TrustTier.get_display_badge(new_tier)
                changed = True
                try:
                    from mcp_server_nucleus.runtime.prometheus import (
                        inc_counter,
                        MARKETPLACE_TIER_CHANGED_TOTAL,
                    )
                    inc_counter(
                        MARKETPLACE_TIER_CHANGED_TOTAL,
                        {"address": address, "from": str(int(current_tier)), "to": str(int(new_tier))},
                    )
                except Exception:
                    pass  # telemetry is supplementary — never block promotion
                
            if old_conn_count != new_conn_count:
                data["connection_count"] = new_conn_count
                changed = True
                
            # Keep other metrics fresh too
            if data.get("avg_response_ms") != metrics.get("avg_response_ms"):
                data["avg_response_ms"] = metrics.get("avg_response_ms", 0)
                changed = True
            if data.get("success_rate") != metrics.get("success_rate"):
                data["success_rate"] = metrics.get("success_rate", 1.0)
                changed = True
            if data.get("last_seen_at") != metrics.get("last_seen_at") and metrics.get("last_seen_at"):
                data["last_seen_at"] = metrics.get("last_seen_at")
                changed = True

            if changed:
                card_file.write_text(json.dumps(data, indent=2))
                updated_cards += 1
                logger.debug(f"tier_promotion_loop: updated {address} (tier {current_tier} -> {new_tier})")
                
        except Exception as exc:
            logger.error(f"tier_promotion_loop: skip {card_file.name}: {exc}")

    return {"ok": True, "updated": updated_cards, "total": total_cards}
