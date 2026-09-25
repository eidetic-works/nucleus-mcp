"""Tests for ELT (Eidetic License Token) — Ed25519 license signing/verify.

Covers the JWT-style API added by the A1 lane in runtime/license.py:
generate_keypair, sign_license, verify_license. Existing NUC-PRO tests
(if any) live elsewhere and are not duplicated here.

Target: ≥15 test cases.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

# Direct-file import to avoid pulling in the entire mcp_server_nucleus package
# (which depends on `core.tool_registration_impl` etc. that aren't part of the
# A1 lane sparse checkout). The license module itself only imports stdlib +
# .identity.keygen, which we load the same way.
_RUNTIME_DIR = Path(__file__).resolve().parents[1] / "src" / "mcp_server_nucleus" / "runtime"


def _load(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Wire up the .identity.keygen import that license.py uses internally.
# We register the identity sub-package as a namespace, then load keygen into it
# under the same dotted name `mcp_server_nucleus.runtime.identity.keygen` that
# the license module expects via `from .identity.keygen import KeyManager`.
import types as _types
_pkg_root = _types.ModuleType("mcp_server_nucleus")
_pkg_root.__path__ = [str(_RUNTIME_DIR.parent)]
sys.modules.setdefault("mcp_server_nucleus", _pkg_root)
_pkg_runtime = _types.ModuleType("mcp_server_nucleus.runtime")
_pkg_runtime.__path__ = [str(_RUNTIME_DIR)]
sys.modules.setdefault("mcp_server_nucleus.runtime", _pkg_runtime)
_pkg_identity = _types.ModuleType("mcp_server_nucleus.runtime.identity")
_pkg_identity.__path__ = [str(_RUNTIME_DIR / "identity")]
sys.modules.setdefault("mcp_server_nucleus.runtime.identity", _pkg_identity)
_keygen = _load("mcp_server_nucleus.runtime.identity.keygen", _RUNTIME_DIR / "identity" / "keygen.py")
license_mod = _load("mcp_server_nucleus.runtime.license", _RUNTIME_DIR / "license.py")

ELT_CLOCK_SKEW_FUTURE = license_mod.ELT_CLOCK_SKEW_FUTURE
ELT_CLOCK_SKEW_PAST = license_mod.ELT_CLOCK_SKEW_PAST
ELT_HEADER = license_mod.ELT_HEADER
_b64url_decode = license_mod._b64url_decode
_b64url_encode = license_mod._b64url_encode
_sign_license_raw = license_mod._sign_license_raw
generate_keypair = license_mod.generate_keypair
sign_license = license_mod.sign_license
verify_license = license_mod.verify_license
VALID_TIERS = license_mod.VALID_TIERS
LEGACY_DEFAULT_TIER = license_mod.LEGACY_DEFAULT_TIER
_default_seat_count = license_mod._default_seat_count


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def keypair():
    priv, pub = generate_keypair()
    return priv, pub


@pytest.fixture(scope="module")
def other_keypair():
    return generate_keypair()


@pytest.fixture
def base_payload():
    return {
        "sub": "cus_TestExample123",
        "tier": "pro",
        "email_hash": "abc123def456",
    }


# ── 1. Keypair generation ────────────────────────────────────────────────────
def test_generate_keypair_returns_bytes():
    priv, pub = generate_keypair()
    assert isinstance(priv, bytes)
    assert isinstance(pub, bytes)
    assert b"PRIVATE KEY" in priv
    assert b"PUBLIC KEY" in pub


def test_generate_keypair_produces_unique_keys():
    p1, _ = generate_keypair()
    p2, _ = generate_keypair()
    assert p1 != p2


# ── 2. Round-trip: sign → verify → claims match ─────────────────────────────
def test_sign_verify_round_trip(keypair, base_payload):
    priv, pub = keypair
    token = sign_license(base_payload, priv, ttl_seconds=3600)
    claims = verify_license(token, pub)
    assert claims is not None
    assert claims["sub"] == base_payload["sub"]
    assert claims["tier"] == "pro"
    assert claims["email_hash"] == base_payload["email_hash"]
    assert "iat" in claims and "exp" in claims
    assert claims["exp"] - claims["iat"] == 3600


def test_sign_default_ttl_is_24h(keypair, base_payload):
    priv, _ = keypair
    token = sign_license(base_payload, priv)
    parts = token.split(".")
    claims = json.loads(_b64url_decode(parts[1]).decode())
    assert claims["exp"] - claims["iat"] == 86400


def test_token_is_url_safe(keypair, base_payload):
    priv, _ = keypair
    token = sign_license(base_payload, priv)
    # url-safe base64 uses - and _, no + or /, no padding (=)
    assert "+" not in token
    assert "/" not in token
    assert "=" not in token
    assert token.count(".") == 2


# ── 3. Header format ────────────────────────────────────────────────────────
def test_header_alg_and_typ(keypair, base_payload):
    priv, _ = keypair
    token = sign_license(base_payload, priv)
    header_b64 = token.split(".")[0]
    header = json.loads(_b64url_decode(header_b64).decode())
    assert header["alg"] == "EdDSA"
    assert header["typ"] == "ELT"


def test_jwt_lookalike_rejected(keypair, base_payload):
    """A token with typ=JWT must be rejected even if signed correctly."""
    priv, pub = keypair
    # Forge a token with typ=JWT (still signed by us)
    KeyManager = _keygen.KeyManager
    km = KeyManager()
    forged_header = json.dumps({"alg": "EdDSA", "typ": "JWT"}, separators=(",", ":"), sort_keys=True)
    header_b64 = _b64url_encode(forged_header.encode())
    claims = {**base_payload, "iat": int(time.time()), "exp": int(time.time()) + 3600}
    claims_b64 = _b64url_encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    sig = km.sign(priv.decode(), f"{header_b64}.{claims_b64}".encode())
    token = f"{header_b64}.{claims_b64}.{_b64url_encode(sig)}"
    assert verify_license(token, pub) is None


# ── 4. Expiry handling ──────────────────────────────────────────────────────
def test_expired_token_rejected(keypair, base_payload):
    priv, pub = keypair
    now = int(time.time())
    claims = {**base_payload, "iat": now - 2 * 86400, "exp": now - 86400}
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


def test_within_clock_skew_past_accepted(keypair, base_payload):
    """A token expired 10s ago should still verify (skew = 30s)."""
    priv, pub = keypair
    now = int(time.time())
    claims = {**base_payload, "iat": now - 100, "exp": now - 10}
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is not None


def test_outside_clock_skew_past_rejected(keypair, base_payload):
    """A token expired 60s ago must be rejected (> 30s skew)."""
    priv, pub = keypair
    now = int(time.time())
    claims = {**base_payload, "iat": now - 100, "exp": now - 60}
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


def test_iat_with_small_future_drift_ok(keypair, base_payload):
    """iat = now + 30s should still verify (future skew = 60s)."""
    priv, pub = keypair
    now = int(time.time())
    claims = {**base_payload, "iat": now + 30, "exp": now + 3600}
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is not None


def test_iat_with_large_future_drift_fails(keypair, base_payload):
    """iat = now + 90s must be rejected (> 60s skew)."""
    priv, pub = keypair
    now = int(time.time())
    claims = {**base_payload, "iat": now + 90, "exp": now + 3600}
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


# ── 5. Tamper resistance ────────────────────────────────────────────────────
def test_tampered_signature_rejected(keypair, base_payload):
    priv, pub = keypair
    token = sign_license(base_payload, priv)
    parts = token.split(".")
    sig_bytes = bytearray(_b64url_decode(parts[2]))
    sig_bytes[0] ^= 0xFF  # flip first byte
    tampered = f"{parts[0]}.{parts[1]}.{_b64url_encode(bytes(sig_bytes))}"
    assert verify_license(tampered, pub) is None


def test_tampered_payload_rejected(keypair, base_payload):
    """Decoding claims, modifying, re-encoding without re-signing must fail."""
    priv, pub = keypair
    token = sign_license(base_payload, priv)
    parts = token.split(".")
    claims = json.loads(_b64url_decode(parts[1]).decode())
    claims["tier"] = "team"  # privilege escalation attempt
    new_claims_b64 = _b64url_encode(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
    )
    tampered = f"{parts[0]}.{new_claims_b64}.{parts[2]}"
    assert verify_license(tampered, pub) is None


def test_wrong_public_key_rejected(keypair, other_keypair, base_payload):
    priv, _ = keypair
    _, wrong_pub = other_keypair
    token = sign_license(base_payload, priv)
    assert verify_license(token, wrong_pub) is None


# ── 6. Malformed tokens ─────────────────────────────────────────────────────
@pytest.mark.parametrize("bad_token", [
    "",
    "only-one-segment",
    "two.segments",
    "four.segments.are.bad",
    "...",
    "!!!.!!!.!!!",  # invalid base64
    "aGVhZGVy.cGF5bG9hZA.c2lnbmF0dXJl",  # valid b64 but not real ELT
])
def test_malformed_token_rejected(keypair, bad_token):
    _, pub = keypair
    assert verify_license(bad_token, pub) is None


def test_non_string_token_rejected(keypair):
    _, pub = keypair
    assert verify_license(None, pub) is None
    assert verify_license(b"bytes-not-string", pub) is None
    assert verify_license(12345, pub) is None


def test_non_bytes_pubkey_rejected(keypair, base_payload):
    priv, pub = keypair
    token = sign_license(base_payload, priv)
    assert verify_license(token, pub.decode("utf-8")) is None
    assert verify_license(token, None) is None


def test_sign_requires_bytes_pubkey(base_payload, keypair):
    priv, _ = keypair
    with pytest.raises(TypeError):
        sign_license(base_payload, priv.decode("utf-8"))


# ── 7. Missing required claim fields handled gracefully ─────────────────────
def test_claims_missing_exp_rejected(keypair, base_payload):
    priv, pub = keypair
    claims = {**base_payload, "iat": int(time.time())}  # no exp
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


def test_claims_missing_iat_rejected(keypair, base_payload):
    priv, pub = keypair
    claims = {**base_payload, "exp": int(time.time()) + 3600}  # no iat
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


# ── 8. Extra claims pass through (forward-compat) ───────────────────────────
def test_extra_claims_preserved(keypair, base_payload):
    priv, pub = keypair
    payload = {**base_payload, "custom_field": "future-feature-flag"}
    token = sign_license(payload, priv)
    claims = verify_license(token, pub)
    assert claims is not None
    assert claims["custom_field"] == "future-feature-flag"


# ── 9. E2 tier-aware claims (Team SKU + annual + tier-aware license) ────────
def test_tier_default_is_pro_when_unspecified(keypair, base_payload):
    """Caller passes no tier arg, payload has no tier → defaults to pro."""
    priv, pub = keypair
    payload = {"sub": base_payload["sub"], "email_hash": base_payload["email_hash"]}
    token = sign_license(payload, priv)
    claims = verify_license(token, pub)
    assert claims is not None
    assert claims["tier"] == "pro"
    assert claims["seat_count"] == 1


@pytest.mark.parametrize("tier,expected_default_seat", [
    ("free", 0),
    ("pro", 1),
    ("team", 1),
    ("founder", 1),
])
def test_sign_per_tier_default_seat_count(keypair, base_payload, tier, expected_default_seat):
    """Each valid tier gets the correct default seat_count when not supplied."""
    priv, pub = keypair
    token = sign_license(base_payload, priv, tier=tier)
    claims = verify_license(token, pub)
    assert claims is not None
    assert claims["tier"] == tier
    assert claims["seat_count"] == expected_default_seat


def test_team_tier_with_explicit_seat_count(keypair, base_payload):
    """Team tier accepts a multi-seat count override."""
    priv, pub = keypair
    token = sign_license(base_payload, priv, tier="team", seat_count=5)
    claims = verify_license(token, pub)
    assert claims is not None
    assert claims["tier"] == "team"
    assert claims["seat_count"] == 5


def test_legacy_token_without_tier_defaults_to_pro_on_verify(keypair, base_payload):
    """Tokens issued pre-E2 (no tier claim signed) → verify backfills tier=pro."""
    priv, pub = keypair
    now = int(time.time())
    # Sign a raw token with NO tier field (the pre-E2 shape from worker).
    claims_no_tier = {
        "sub": base_payload["sub"],
        "email_hash": base_payload["email_hash"],
        "iat": now,
        "exp": now + 3600,
    }
    token = _sign_license_raw(claims_no_tier, priv)
    verified = verify_license(token, pub)
    assert verified is not None
    assert verified["tier"] == LEGACY_DEFAULT_TIER == "pro"
    # seat_count is also backfilled via tier-default
    assert verified["seat_count"] == 1


def test_invalid_tier_string_rejected_at_sign(keypair, base_payload):
    """sign_license raises ValueError for an unknown tier string."""
    priv, _ = keypair
    with pytest.raises(ValueError, match="invalid tier"):
        sign_license(base_payload, priv, tier="enterprise")


def test_unknown_tier_in_signed_token_rejected_at_verify(keypair, base_payload):
    """A signed token whose tier claim is outside VALID_TIERS verifies as None.

    Protects against a future-tier value (e.g. a partner token with tier='alpha')
    causing the daemon to fall-open. Better to reject the whole token than
    silently treat it as Pro.
    """
    priv, pub = keypair
    now = int(time.time())
    claims = {
        "sub": base_payload["sub"],
        "tier": "alpha-tier-from-future",
        "email_hash": base_payload["email_hash"],
        "iat": now,
        "exp": now + 3600,
    }
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


def test_negative_seat_count_rejected_at_sign(keypair, base_payload):
    """seat_count must be >= 0."""
    priv, _ = keypair
    with pytest.raises(ValueError, match="seat_count"):
        sign_license(base_payload, priv, tier="team", seat_count=-1)


def test_negative_seat_count_in_signed_token_rejected_at_verify(keypair, base_payload):
    """Signed token with a negative seat_count claim → verify returns None."""
    priv, pub = keypair
    now = int(time.time())
    claims = {
        "sub": base_payload["sub"],
        "tier": "team",
        "seat_count": -3,
        "email_hash": base_payload["email_hash"],
        "iat": now,
        "exp": now + 3600,
    }
    token = _sign_license_raw(claims, priv)
    assert verify_license(token, pub) is None


def test_sign_tier_arg_overrides_payload_tier(keypair, base_payload):
    """If tier in payload AND tier= kwarg, kwarg wins."""
    priv, pub = keypair
    payload = {**base_payload, "tier": "pro"}
    token = sign_license(payload, priv, tier="team", seat_count=3)
    claims = verify_license(token, pub)
    assert claims is not None
    assert claims["tier"] == "team"
    assert claims["seat_count"] == 3
