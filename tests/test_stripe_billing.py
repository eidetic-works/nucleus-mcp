"""Tests for runtime.stripe_billing — async Stripe REST client.

Uses httpx.MockTransport (built into httpx) so no external network or
pytest-httpx/respx dependency is required.

Target: ≥12 test cases.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import types
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")

# See test_license_elt.py for rationale — direct file imports avoid the heavy
# mcp_server_nucleus package __init__.
_RUNTIME_DIR = Path(__file__).resolve().parents[1] / "src" / "mcp_server_nucleus" / "runtime"


def _load(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


for name, path in [
    ("mcp_server_nucleus", _RUNTIME_DIR.parent),
    ("mcp_server_nucleus.runtime", _RUNTIME_DIR),
    ("mcp_server_nucleus.runtime.identity", _RUNTIME_DIR / "identity"),
]:
    if name not in sys.modules:
        m = types.ModuleType(name)
        m.__path__ = [str(path)]
        sys.modules[name] = m

_load("mcp_server_nucleus.runtime.identity.keygen", _RUNTIME_DIR / "identity" / "keygen.py")
license_mod = _load("mcp_server_nucleus.runtime.license", _RUNTIME_DIR / "license.py")
sb_mod = _load("mcp_server_nucleus.runtime.stripe_billing", _RUNTIME_DIR / "stripe_billing.py")

generate_keypair = license_mod.generate_keypair
verify_license = license_mod.verify_license
ACTIVE_STATUSES = sb_mod.ACTIVE_STATUSES
BillingClient = sb_mod.BillingClient
CustomerNotFound = sb_mod.CustomerNotFound
CustomerRecord = sb_mod.CustomerRecord
STRIPE_API_VERSION = sb_mod.STRIPE_API_VERSION
StripeAPIError = sb_mod.StripeAPIError
Subscription = sb_mod.Subscription
SubscriptionExpired = sb_mod.SubscriptionExpired
TIER_LABEL_BY_STATUS = sb_mod.TIER_LABEL_BY_STATUS
email_hash = sb_mod.email_hash

# Async tests are explicitly marked below; sync tests left unmarked.


# ── Helpers ────────────────────────────────────────────────────────────────
def make_customer(cid: str = "cus_TEST", email: str = "user@example.com"):
    return {
        "id": cid,
        "object": "customer",
        "email": email,
        "metadata": {},
    }


def make_subscription(
    sid: str = "sub_TEST",
    cid: str = "cus_TEST",
    status: str = "active",
    price_id: str = "price_pro_monthly",
    period_end: int = None,
    created: int = None,
):
    return {
        "id": sid,
        "object": "subscription",
        "customer": cid,
        "status": status,
        "current_period_end": period_end or int(time.time()) + 30 * 86400,
        "cancel_at_period_end": False,
        "created": created or int(time.time()),
        "items": {"data": [{"price": {"id": price_id}}]},
    }


def build_client(handler) -> BillingClient:
    """Build a BillingClient backed by an httpx.MockTransport."""
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return BillingClient(secret_key="sk_test_dummy", http_client=http)


# ── 1. get_customer happy path ─────────────────────────────────────────────
async def test_get_customer_happy_path():
    state = {"requests": []}

    def handler(req: httpx.Request) -> httpx.Response:
        state["requests"].append((req.method, str(req.url)))
        if req.url.path == "/v1/customers/cus_42":
            return httpx.Response(200, json=make_customer("cus_42", "x@y.com"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": [make_subscription(cid="cus_42")]})
        return httpx.Response(404, json={"error": "?"})

    async with build_client(handler) as c:
        cust = await c.get_customer("cus_42")
    assert isinstance(cust, CustomerRecord)
    assert cust.customer_id == "cus_42"
    assert cust.email == "x@y.com"
    assert cust.email_hash == email_hash("x@y.com")
    assert cust.tier == "pro"
    assert cust.status == "active"


# ── 2. get_customer 404 → None ─────────────────────────────────────────────
async def test_get_customer_404_returns_none():
    def handler(req):
        return httpx.Response(404, json={"error": "no such customer"})
    async with build_client(handler) as c:
        cust = await c.get_customer("cus_does_not_exist")
    assert cust is None


# ── 3. 5xx retry behavior ──────────────────────────────────────────────────
async def test_5xx_retry_then_succeed():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500, json={"error": "server"})
        if req.url.path == "/v1/customers/cus_R":
            return httpx.Response(200, json=make_customer("cus_R", "r@x.com"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404, json={"error": "?"})

    client = build_client(handler)
    # Reduce backoff so the test is fast
    client.__class__.__module__  # touch
    orig_base = sb_mod.RETRY_BACKOFF_BASE
    sb_mod.RETRY_BACKOFF_BASE = 0.001
    try:
        async with client as c:
            cust = await c.get_customer("cus_R")
    finally:
        sb_mod.RETRY_BACKOFF_BASE = orig_base
    assert cust is not None
    assert calls["n"] >= 3


# ── 4. 5xx retries exhausted → StripeAPIError ──────────────────────────────
async def test_5xx_retries_exhausted():
    def handler(req):
        return httpx.Response(500, json={"error": "always_500"})

    orig_base = sb_mod.RETRY_BACKOFF_BASE
    sb_mod.RETRY_BACKOFF_BASE = 0.001
    try:
        async with build_client(handler) as c:
            with pytest.raises(StripeAPIError) as exc_info:
                await c.get_customer("cus_X")
    finally:
        sb_mod.RETRY_BACKOFF_BASE = orig_base
    assert exc_info.value.status == 500


# ── 5. 429 rate-limit retry ─────────────────────────────────────────────────
async def test_429_rate_limit_retried():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": "rate"})
        if req.url.path == "/v1/customers/cus_429":
            return httpx.Response(200, json=make_customer("cus_429"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404, json={"error": "?"})

    orig_base = sb_mod.RETRY_BACKOFF_BASE
    sb_mod.RETRY_BACKOFF_BASE = 0.001
    try:
        async with build_client(handler) as c:
            cust = await c.get_customer("cus_429")
    finally:
        sb_mod.RETRY_BACKOFF_BASE = orig_base
    assert cust is not None
    assert calls["n"] == 3  # 429 + sub-list + customer fetch on retry sequence


# ── 6. Subscription status → tier mapping ──────────────────────────────────
@pytest.mark.parametrize("status,expected_tier", [
    ("active", "pro"),
    ("trialing", "pro"),
    ("past_due", "pro"),
    ("canceled", "free"),
    ("incomplete", "free"),
    ("incomplete_expired", "free"),
    ("unpaid", "free"),
    ("paused", "free"),
])
async def test_subscription_status_tier_mapping(status, expected_tier):
    def handler(req):
        if "customers/cus_S" in req.url.path:
            return httpx.Response(200, json=make_customer("cus_S"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": [make_subscription(status=status, cid="cus_S")]})
        return httpx.Response(404)

    async with build_client(handler) as c:
        cust = await c.get_customer("cus_S")
    if expected_tier == "pro":
        assert cust.tier == "pro"
        assert cust.status == status
    else:
        # Non-active statuses get filtered out → "free", status="no_subscription"
        assert cust.tier == "free"
        assert cust.status == "no_subscription"


# ── 7. No subscription → tier=free ─────────────────────────────────────────
async def test_no_subscription_returns_free_tier():
    def handler(req):
        if "customers/cus_NS" in req.url.path:
            return httpx.Response(200, json=make_customer("cus_NS"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404)

    async with build_client(handler) as c:
        cust = await c.get_customer("cus_NS")
    assert cust.tier == "free"
    assert cust.status == "no_subscription"
    assert cust.current_period_end is None


# ── 8. Stripe-Version header is sent ───────────────────────────────────────
async def test_stripe_version_header_sent():
    captured = {}

    def handler(req):
        captured["headers"] = dict(req.headers)
        return httpx.Response(200, json=make_customer())

    async with build_client(handler) as c:
        # Subscriptions returns 404 — we want to see only the first call's headers
        captured.clear()
        await c._request("GET", "/customers/cus_H")
    assert captured["headers"].get("stripe-version") == STRIPE_API_VERSION
    assert captured["headers"].get("authorization", "").startswith("Bearer ")


# ── 9. refresh_license round-trip ──────────────────────────────────────────
async def test_refresh_license_round_trip():
    priv_pem, pub_pem = generate_keypair()

    def handler(req):
        if "customers/cus_REF" in req.url.path:
            return httpx.Response(200, json=make_customer("cus_REF", "r@x.com"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": [make_subscription(cid="cus_REF")]})
        return httpx.Response(404)

    async with build_client(handler) as c:
        token = await c.refresh_license("cus_REF", private_key_pem=priv_pem)

    claims = verify_license(token, pub_pem)
    assert claims is not None
    assert claims["sub"] == "cus_REF"
    assert claims["tier"] == "pro"
    assert claims["email_hash"] == email_hash("r@x.com")


# ── 10. refresh_license on missing customer → CustomerNotFound ─────────────
async def test_refresh_license_missing_customer():
    priv_pem, _ = generate_keypair()

    def handler(req):
        return httpx.Response(404, json={"error": "no"})

    async with build_client(handler) as c:
        with pytest.raises(CustomerNotFound):
            await c.refresh_license("cus_GHOST", private_key_pem=priv_pem)


# ── 11. refresh_license on inactive subscription → SubscriptionExpired ─────
async def test_refresh_license_inactive_subscription():
    priv_pem, _ = generate_keypair()

    def handler(req):
        if "customers/cus_DEAD" in req.url.path:
            return httpx.Response(200, json=make_customer("cus_DEAD"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": [make_subscription(status="canceled", cid="cus_DEAD")]})
        return httpx.Response(404)

    async with build_client(handler) as c:
        with pytest.raises(SubscriptionExpired):
            await c.refresh_license("cus_DEAD", private_key_pem=priv_pem)


# ── 12. Subscription priority: prefer active over canceled ─────────────────
async def test_subscription_priority_active_over_canceled():
    """If a customer has both canceled + active subs, return the active one."""
    def handler(req):
        if "customers/cus_MULTI" in req.url.path:
            return httpx.Response(200, json=make_customer("cus_MULTI"))
        if req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"data": [
                make_subscription(sid="sub_canceled", status="canceled", cid="cus_MULTI"),
                make_subscription(sid="sub_active", status="active", cid="cus_MULTI"),
            ]})
        return httpx.Response(404)

    async with build_client(handler) as c:
        sub = await c.get_active_subscription("cus_MULTI")
    assert sub is not None
    assert sub.id == "sub_active"
    assert sub.tier == "pro"


# ── 13. email_hash determinism + privacy ───────────────────────────────────
def test_email_hash_deterministic():
    assert email_hash("foo@bar.com") == email_hash("foo@bar.com")
    assert email_hash("Foo@Bar.com") == email_hash("foo@bar.com")  # case-insensitive
    assert email_hash(" foo@bar.com ") == email_hash("foo@bar.com")  # trimmed
    assert email_hash("foo@bar.com") != email_hash("foo@baz.com")
    assert len(email_hash("foo@bar.com")) == 16


# ── 14. Subscription dataclass invariants ──────────────────────────────────
def test_subscription_is_active_and_tier():
    s = Subscription(id="s", status="active", current_period_end=0, customer_id="c")
    assert s.is_active and s.tier == "pro"
    s = Subscription(id="s", status="canceled", current_period_end=0, customer_id="c")
    assert not s.is_active and s.tier == "free"


# ── 15. BillingClient init validation ──────────────────────────────────────
def test_billing_client_requires_secret_key():
    with pytest.raises(ValueError):
        BillingClient(secret_key="")


# ── 16. ACTIVE_STATUSES sanity ─────────────────────────────────────────────
def test_active_statuses_contract():
    assert "active" in ACTIVE_STATUSES
    assert "trialing" in ACTIVE_STATUSES
    assert "past_due" in ACTIVE_STATUSES
    assert "canceled" not in ACTIVE_STATUSES
    assert "incomplete" not in ACTIVE_STATUSES
