"""
ContextBroker: The Economy Engine.
Facilitates the exchange of information (context) negotiation between agents.

Roles:
1. MARKETPLACE: Where agents list what they know.
2. CLEARING HOUSE: Records transactions (who bought what).
3. SETTLEMENT: (Future) Handles credit transfers.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Literal
from pathlib import Path
from pydantic import BaseModel

from .locking import get_lock

logger = logging.getLogger("BROKER")

class ContextListing(BaseModel):
    id: str
    provider_id: str
    topic: str
    description: str
    content: str # In MVP, content is stored directly. In prod, this is a pointer.
    price: float = 0.0
    type: Literal["data", "service"] = "data"
    created_at: str

class ContextTransaction(BaseModel):
    id: str
    listing_id: str
    buyer_id: str
    seller_id: str
    amount: float
    timestamp: str
    content: Optional[str] = None # The delivered goods

class ContextBroker:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.listings_path = brain_path / "ledger" / "listings.json"
        self.ledger_path = brain_path / "ledger" / "transactions.jsonl"
        
        # Ensure dirs
        self.listings_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_listings(self) -> Dict[str, ContextListing]:
        with get_lock("broker", self.brain_path).section():
            if not self.listings_path.exists():
                return {}
            try:
                data = json.loads(self.listings_path.read_text())
                return {k: ContextListing(**v) for k, v in data.items()}
            except Exception:
                return {}

    def _save_listings(self, listings: Dict[str, ContextListing]):
        with get_lock("broker", self.brain_path).section():
            data = {k: v.model_dump() for k, v in listings.items()}
            self.listings_path.write_text(json.dumps(data, indent=2))

    def publish_listing(self, provider_id: str, topic: str, description: str, content: str, price: float = 0.0, type: Literal["data", "service"] = "data") -> str:
        """Create a new context listing."""
        listing_id = f"list-{uuid.uuid4().hex[:8]}"
        listing = ContextListing(
            id=listing_id,
            provider_id=provider_id,
            topic=topic,
            description=description,
            content=content,
            price=price,
            type=type,
            created_at=datetime.now().isoformat()
        )
        
        listings = self._load_listings()
        listings[listing_id] = listing
        self._save_listings(listings)
        
        logger.info(f"📢 Listing Published: {topic} by {provider_id} ({listing_id})")
        return listing_id

    def search_listings(self, query: str) -> List[ContextListing]:
        """Find listings by topic or description."""
        listings = self._load_listings()
        query = query.lower()
        results = []
        for lst in listings.values():
            if query in lst.topic.lower() or query in lst.description.lower():
                results.append(lst)
        return results

    def buy_context(self, buyer_id: str, listing_id: str) -> Optional[ContextTransaction]:
        """Execute a context transaction."""
        listings = self._load_listings()
        
        if listing_id not in listings:
            logger.error(f"❌ Transaction Failed: Listing {listing_id} not found")
            return None
            
        listing = listings[listing_id]
        
        # In a real economy, check budget here.
        
        tx_id = f"tx-{uuid.uuid4().hex[:8]}"
        tx = ContextTransaction(
            id=tx_id,
            listing_id=listing.id,
            buyer_id=buyer_id,
            seller_id=listing.provider_id,
            amount=listing.price,
            timestamp=datetime.now().isoformat(),
            content=listing.content # Deliver the goods
        )
        
        # Append to ledger
        with get_lock("ledger", self.brain_path).section():
            with open(self.ledger_path, "a") as f:
                f.write(tx.model_dump_json() + "\n")
                
        logger.info(f"💰 Sold: {listing.topic} from {listing.provider_id} to {buyer_id}")
        return tx
