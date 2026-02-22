"""
ContextBroker: The Economy Engine.
Facilitates the exchange of information (context) negotiation between agents.

Roles:
1. MARKETPLACE: Where agents list what they know.
2. CLEARING HOUSE: Records transactions (who bought what).
3. SETTLEMENT: (Future) Handles credit transfers.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Literal
from pathlib import Path
from pydantic import BaseModel


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
        from .db import get_storage_backend
        self.storage = get_storage_backend(brain_path)

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
        
        self.storage.create_listing(listing)
        
        logger.info(f"📢 Listing Published: {topic} by {provider_id} ({listing_id})")
        return listing_id

    def search_listings(self, query: str, limit: int = 20, offset: int = 0) -> List[ContextListing]:
        """
        Find listings by topic or description.

        SCALABILITY FIX (MASTER_STRATEGY §1.2):
        Added limit/offset for pagination. At 1000+ listings, loading
        everything into memory for a string search is unacceptable.

        Args:
            query: Search string (matches topic or description).
            limit: Max results to return (default 20).
            offset: Number of results to skip (for pagination).

        Returns:
            List of matching ContextListing objects.
        """
        return self.storage.search_listings(query, limit, offset)

    def get_listing(self, listing_id: str) -> Optional[ContextListing]:
        """
        Get a single listing by ID without loading all listings into the caller.

        Args:
            listing_id: The listing ID to retrieve.

        Returns:
            ContextListing or None if not found.
        """
        return self.storage.get_listing(listing_id)

    def count_listings(self) -> int:
        """
        Get the total number of active listings.

        O(n) file read but avoids deserializing content fields in the future
        when we move to a database backend.

        Returns:
            Number of listings in the marketplace.
        """
        return self.storage.count_listings()


    def buy_context(self, buyer_id: str, listing_id: str) -> Optional[ContextTransaction]:
        """Execute a context transaction."""
        listing = self.storage.get_listing(listing_id)
        
        if not listing:
            logger.error(f"❌ Transaction Failed: Listing {listing_id} not found")
            return None
            
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
        
        # Append to ledger via storage backend
        self.storage.create_transaction(tx)
                
        logger.info(f"💰 Sold: {listing.topic} from {listing.provider_id} to {buyer_id}")
        return tx
