"""Stripe Billing Client — Subscription State Management.

Wraps Stripe's Customer + Subscription model behind a small async client.
Use to ask "is this customer's subscription still active?" from the daemon
or any backend surface that needs to gate Pro-tier features.

Distinct from runtime.billing which tracks INTERNAL usage cost units; this
module tracks EXTERNAL Stripe subscription billing.

Implementation notes:
- We do NOT use the `stripe` Python SDK. Direct httpx calls to api.stripe.com
  with Bearer auth keep the surface portable (the same patterns are used in
  the Cloudflare Worker; PR #320 confirmed `stripe` npm pulls Node-only deps
  that fail on Workers V8 isolates — same logic applies to constraining the
  Python footprint).
- Stripe-Version pinned to 2024-06-20 (matches PR #320 convention).
- Retries on 5xx + 429 with exponential backoff (max 3 retries).
- Customer-ID-keyed; if Stripe lookups by email become needed, add a wrapper.

Reference: https://docs.stripe.com/api
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Iterable

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    httpx = None  # type: ignore

logger = logging.getLogger("STRIPE_BILLING")

STRIPE_API_BASE = "https://api.stripe.com/v1"
STRIPE_API_VERSION = "2024-06-20"
DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # seconds (0.5, 1.0, 2.0, ...)

# Stripe subscription status → internal tier mapping.
# Anything not in ACTIVE_STATUSES degrades to "free".
ACTIVE_STATUSES = frozenset({"active", "trialing", "past_due"})
TIER_LABEL_BY_STATUS = {
    "active":   "pro",
    "trialing": "pro",
    "past_due": "pro",       # grace period — still serve, alert separately
    "canceled": "free",
    "incomplete": "free",
    "incomplete_expired": "free",
    "unpaid":   "free",
    "paused":   "free",
}


class StripeAPIError(Exception):
    """Raised on non-2xx response from Stripe API after retries exhausted."""
    def __init__(self, status: int, body: str):
        super().__init__(f"Stripe API error {status}: {body[:200]}")
        self.status = status
        self.body = body


class CustomerNotFound(StripeAPIError):
    """Raised when Stripe returns 404 for a customer lookup."""
    def __init__(self, customer_id: str, body: str = ""):
        super().__init__(404, body or f"customer {customer_id} not found")
        self.customer_id = customer_id


class SubscriptionExpired(Exception):
    """Raised when a customer has no active subscription."""
    def __init__(self, customer_id: str, status: Optional[str] = None):
        super().__init__(f"subscription expired for {customer_id} (status={status})")
        self.customer_id = customer_id
        self.status = status


def email_hash(email: str) -> str:
    """Stable SHA-256 hash of lowercased, trimmed email. First 16 hex chars.

    Matches PR #320 webhook convention (`email_hash` short form). Used as a
    privacy-preserving identifier in license claims.
    """
    norm = (email or "").strip().lower().encode("utf-8")
    return hashlib.sha256(norm).hexdigest()[:16]


@dataclass
class Subscription:
    """A minimal projection of a Stripe Subscription object."""
    id: str
    status: str
    current_period_end: int  # unix timestamp
    customer_id: str
    price_id: Optional[str] = None
    cancel_at_period_end: bool = False

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def tier(self) -> str:
        return TIER_LABEL_BY_STATUS.get(self.status, "free")


@dataclass
class CustomerRecord:
    """A minimal projection of a Stripe Customer object enriched with tier."""
    customer_id: str
    email: str
    email_hash: str
    tier: str
    status: str  # "active" / "past_due" / "canceled" / etc. or "no_subscription"
    current_period_end: Optional[int] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class BillingClient:
    """Async Stripe REST client. Use as `async with BillingClient(secret) as c:`.

    Args:
        secret_key: Stripe secret API key (sk_test_... or sk_live_...).
        api_version: Stripe-Version header value. Default 2024-06-20.
        timeout: Per-request timeout (seconds). Default 10.
        max_retries: Number of retry attempts on 5xx/429. Default 3.
        http_client: Optional pre-built httpx.AsyncClient (mostly for tests).
    """
    def __init__(
        self,
        secret_key: str,
        *,
        api_version: str = STRIPE_API_VERSION,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        http_client: Optional["httpx.AsyncClient"] = None,
    ):
        if not _HAS_HTTPX:
            raise ImportError(
                "httpx is required for stripe_billing. "
                "Install with: pip install httpx"
            )
        if not secret_key:
            raise ValueError("secret_key is required")
        self.secret_key = secret_key
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> "BillingClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Low-level request with retry ────────────────────────────────
    async def _request(self, method: str, path: str, *, params: Optional[dict] = None) -> dict:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._owns_client = True

        url = f"{STRIPE_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Stripe-Version": self.api_version,
        }
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._client.request(
                    method, url, headers=headers, params=params,
                )
            except httpx.HTTPError as exc:  # network errors retryable
                last_exc = exc
                if attempt == self.max_retries:
                    raise StripeAPIError(0, f"network error: {exc}") from exc
                await asyncio.sleep(RETRY_BACKOFF_BASE * (2 ** attempt))
                continue

            if resp.status_code == 404:
                raise CustomerNotFound(path, resp.text)
            if 500 <= resp.status_code < 600 or resp.status_code == 429:
                if attempt == self.max_retries:
                    raise StripeAPIError(resp.status_code, resp.text)
                await asyncio.sleep(RETRY_BACKOFF_BASE * (2 ** attempt))
                continue
            if not (200 <= resp.status_code < 300):
                raise StripeAPIError(resp.status_code, resp.text)
            try:
                return resp.json()
            except Exception as exc:
                raise StripeAPIError(resp.status_code, resp.text) from exc

        # Should be unreachable; satisfies type checker.
        raise StripeAPIError(0, f"exhausted retries: {last_exc}")

    # ── Public API ──────────────────────────────────────────────────
    async def get_customer(self, customer_id: str) -> Optional[CustomerRecord]:
        """Fetch a customer by Stripe ID. Returns None on 404 (CustomerNotFound)."""
        try:
            data = await self._request("GET", f"/customers/{customer_id}")
        except CustomerNotFound:
            return None

        sub = await self.get_active_subscription(customer_id)
        return CustomerRecord(
            customer_id=customer_id,
            email=data.get("email") or "",
            email_hash=email_hash(data.get("email") or ""),
            tier=sub.tier if sub else "free",
            status=sub.status if sub else "no_subscription",
            current_period_end=sub.current_period_end if sub else None,
            metadata=data.get("metadata") or {},
        )

    async def get_active_subscription(self, customer_id: str) -> Optional[Subscription]:
        """Return the most recent active subscription for a customer, else None.

        We do NOT filter on `status` server-side; we fetch up to 10 subs and
        prefer the most-recently-created active one. This handles edge cases
        like a customer with a canceled + new active subscription.
        """
        try:
            data = await self._request(
                "GET",
                "/subscriptions",
                params={"customer": customer_id, "limit": 10, "status": "all"},
            )
        except CustomerNotFound:
            return None

        items = data.get("data") or []
        if not items:
            return None

        # Prefer active over trialing over past_due over canceled
        priority = {"active": 0, "trialing": 1, "past_due": 2, "canceled": 9}
        items.sort(key=lambda s: (priority.get(s.get("status"), 5), -int(s.get("created", 0))))
        sub = items[0]
        if sub.get("status") not in ACTIVE_STATUSES:
            return None

        # Stripe items.data[0].price.id — defensive nested access
        price_id: Optional[str] = None
        sub_items = (sub.get("items") or {}).get("data") or []
        if sub_items:
            price_id = ((sub_items[0].get("price") or {}).get("id"))

        return Subscription(
            id=sub.get("id") or "",
            status=sub.get("status") or "",
            current_period_end=int(sub.get("current_period_end") or 0),
            customer_id=customer_id,
            price_id=price_id,
            cancel_at_period_end=bool(sub.get("cancel_at_period_end")),
        )

    async def list_active_pro_customers(self, *, limit: int = 100) -> list[CustomerRecord]:
        """List customers with an active 'pro' tier subscription.

        For admin dashboards / daemon-side bulk validation. NOT for hot paths
        — paginates through customers (up to `limit` returned).
        """
        data = await self._request("GET", "/customers", params={"limit": limit})
        out: list[CustomerRecord] = []
        for cust in data.get("data") or []:
            cid = cust.get("id")
            if not cid:
                continue
            sub = await self.get_active_subscription(cid)
            if sub and sub.tier == "pro":
                out.append(
                    CustomerRecord(
                        customer_id=cid,
                        email=cust.get("email") or "",
                        email_hash=email_hash(cust.get("email") or ""),
                        tier=sub.tier,
                        status=sub.status,
                        current_period_end=sub.current_period_end,
                        metadata=cust.get("metadata") or {},
                    )
                )
        return out

    async def refresh_license(
        self,
        customer_id: str,
        *,
        private_key_pem: bytes,
        ttl_seconds: int = 86400,
    ) -> str:
        """Issue a freshly-signed ELT for a customer's current state.

        Raises CustomerNotFound if Stripe doesn't know them; SubscriptionExpired
        if they have no active subscription. Otherwise returns a new ELT.
        """
        cust = await self.get_customer(customer_id)
        if cust is None:
            raise CustomerNotFound(customer_id)
        if cust.tier == "free":
            raise SubscriptionExpired(customer_id, status=cust.status)

        from .license import sign_license
        payload = {
            "sub": customer_id,
            "tier": cust.tier,
            "email_hash": cust.email_hash,
        }
        return sign_license(payload, private_key_pem, ttl_seconds=ttl_seconds)


__all__ = [
    "BillingClient",
    "CustomerRecord",
    "Subscription",
    "StripeAPIError",
    "CustomerNotFound",
    "SubscriptionExpired",
    "ACTIVE_STATUSES",
    "TIER_LABEL_BY_STATUS",
    "STRIPE_API_VERSION",
    "email_hash",
]
