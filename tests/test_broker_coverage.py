"""Comprehensive tests for runtime/broker.py — ContextBroker, ContextListing,
ContextTransaction."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.broker import (
    ContextBroker,
    ContextListing,
    ContextTransaction,
)


# ── ContextListing ───────────────────────────────────────────────

class TestContextListing:
    def test_defaults(self):
        listing = ContextListing(
            id="list1",
            provider_id="agent1",
            topic="auth",
            description="auth patterns",
            content="jwt + refresh tokens",
            created_at="2026-01-01T00:00:00",
        )
        assert listing.id == "list1"
        assert listing.provider_id == "agent1"
        assert listing.topic == "auth"
        assert listing.description == "auth patterns"
        assert listing.content == "jwt + refresh tokens"
        assert listing.price == 0.0
        assert listing.type == "data"

    def test_with_price_and_type(self):
        listing = ContextListing(
            id="list2",
            provider_id="agent2",
            topic="deploy",
            description="deploy scripts",
            content="k8s manifests",
            price=5.0,
            type="service",
            created_at="2026-01-01T00:00:00",
        )
        assert listing.price == 5.0
        assert listing.type == "service"


# ── ContextTransaction ───────────────────────────────────────────

class TestContextTransaction:
    def test_defaults(self):
        tx = ContextTransaction(
            id="tx1",
            listing_id="list1",
            buyer_id="buyer1",
            seller_id="seller1",
            amount=1.5,
            timestamp="2026-01-01T00:00:00",
        )
        assert tx.id == "tx1"
        assert tx.listing_id == "list1"
        assert tx.buyer_id == "buyer1"
        assert tx.seller_id == "seller1"
        assert tx.amount == 1.5
        assert tx.content is None

    def test_with_content(self):
        tx = ContextTransaction(
            id="tx2",
            listing_id="list1",
            buyer_id="buyer1",
            seller_id="seller1",
            amount=0.0,
            timestamp="2026-01-01T00:00:00",
            content="delivered goods",
        )
        assert tx.content == "delivered goods"


# ── ContextBroker ────────────────────────────────────────────────

class TestContextBroker:
    @pytest.fixture
    def broker(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        return ContextBroker(brain)

    def test_init(self, tmp_path):
        brain = tmp_path / "brain"
        brain.mkdir()
        broker = ContextBroker(brain)
        assert broker.brain_path == brain
        assert broker.storage is not None

    def test_publish_listing(self, broker):
        listing_id = broker.publish_listing(
            provider_id="agent1",
            topic="auth",
            description="auth patterns",
            content="jwt tokens",
        )
        assert listing_id.startswith("list-")

    def test_publish_listing_with_price(self, broker):
        listing_id = broker.publish_listing(
            provider_id="agent1",
            topic="deploy",
            description="deploy scripts",
            content="k8s",
            price=10.0,
            type="service",
        )
        listing = broker.get_listing(listing_id)
        assert listing.price == 10.0
        assert listing.type == "service"

    def test_search_listings(self, broker):
        broker.publish_listing("a1", "auth", "auth desc", "content1")
        broker.publish_listing("a2", "deploy", "deploy desc", "content2")
        results = broker.search_listings("auth")
        assert len(results) == 1
        assert results[0].topic == "auth"

    def test_search_listings_empty_query(self, broker):
        broker.publish_listing("a1", "auth", "desc", "content")
        results = broker.search_listings("")
        assert len(results) == 1

    def test_search_listings_no_match(self, broker):
        broker.publish_listing("a1", "auth", "desc", "content")
        results = broker.search_listings("nonexistent")
        assert results == []

    def test_search_listings_with_limit(self, broker):
        for i in range(5):
            broker.publish_listing("a1", f"topic_{i}", f"desc_{i}", "content")
        results = broker.search_listings("topic", limit=2)
        assert len(results) == 2

    def test_search_listings_with_offset(self, broker):
        for i in range(5):
            broker.publish_listing("a1", f"topic_{i}", f"desc_{i}", "content")
        results = broker.search_listings("topic", limit=2, offset=2)
        assert len(results) == 2

    def test_get_listing(self, broker):
        listing_id = broker.publish_listing("a1", "test", "desc", "content")
        listing = broker.get_listing(listing_id)
        assert listing is not None
        assert listing.id == listing_id

    def test_get_listing_not_found(self, broker):
        result = broker.get_listing("nonexistent")
        assert result is None

    def test_count_listings(self, broker):
        broker.publish_listing("a1", "t1", "d1", "c1")
        broker.publish_listing("a2", "t2", "d2", "c2")
        assert broker.count_listings() == 2

    def test_count_listings_empty(self, broker):
        assert broker.count_listings() == 0

    def test_buy_context(self, broker):
        listing_id = broker.publish_listing(
            "seller1", "topic", "desc", "content", price=5.0
        )
        tx = broker.buy_context("buyer1", listing_id)
        assert tx is not None
        assert tx.buyer_id == "buyer1"
        assert tx.seller_id == "seller1"
        assert tx.amount == 5.0
        assert tx.content == "content"

    def test_buy_context_listing_not_found(self, broker):
        tx = broker.buy_context("buyer1", "nonexistent")
        assert tx is None

    def test_buy_context_free_listing(self, broker):
        listing_id = broker.publish_listing(
            "seller1", "topic", "desc", "content", price=0.0
        )
        tx = broker.buy_context("buyer1", listing_id)
        assert tx is not None
        assert tx.amount == 0.0

    def test_buy_context_multiple(self, broker):
        listing_id = broker.publish_listing("s1", "t", "d", "c", price=1.0)
        tx1 = broker.buy_context("b1", listing_id)
        tx2 = broker.buy_context("b2", listing_id)
        assert tx1 is not None
        assert tx2 is not None
        assert tx1.buyer_id == "b1"
        assert tx2.buyer_id == "b2"
