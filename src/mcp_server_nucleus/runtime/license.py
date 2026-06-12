"""
Nucleus Pro License System — Offline Ed25519 License Keys

License keys are cryptographically signed tokens validated offline.
No cloud dependency. No phone-home. Local-first.

Format: NUC-PRO-<base64url(payload_json + "." + signature_hex)>

Payload: {"email": "...", "tier": "pro", "exp": "2027-03-30T00:00:00Z"}
Signature: Ed25519 sign(payload_json_bytes) using Nucleus issuer private key
"""

import base64
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, NamedTuple

logger = logging.getLogger("NUCLEUS_LICENSE")

# Nucleus Pro issuer public key (Ed25519).
# The private key is held server-side (Stripe webhook / key generation service).
# This public key is bundled in the package for offline validation.
_ISSUER_PUBLIC_KEY_PEM = """\
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAjh+XbpJRZrKtVQKXSiKp1a9r7L6yF4iL8R3kLwvS1mo=
-----END PUBLIC KEY-----
"""

_ISSUER_KEY_READY = True

LICENSE_DIR = Path.home() / ".nucleus"
LICENSE_FILE = LICENSE_DIR / "license.key"


class LicenseInfo(NamedTuple):
    valid: bool
    tier: str  # "pro", "trial", "free"
    email: str
    expires: Optional[datetime]
    error: Optional[str]


FREE = LicenseInfo(valid=False, tier="free", email="", expires=None, error=None)


def _decode_key(raw: str) -> tuple[dict, bytes]:
    """Decode a NUC-PRO-... key into (payload_dict, signature_bytes)."""
    if not raw.startswith("NUC-PRO-"):
        raise ValueError("Invalid key prefix")
    encoded = raw[8:]
    decoded = base64.urlsafe_b64decode(encoded + "==").decode("utf-8")
    payload_json, sig_hex = decoded.rsplit(".", 1)
    payload = json.loads(payload_json)
    signature = bytes.fromhex(sig_hex)
    return payload, signature


def _encode_key(payload: dict, signature: bytes) -> str:
    """Encode payload + signature into NUC-PRO-... format."""
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    combined = payload_json + "." + signature.hex()
    encoded = base64.urlsafe_b64encode(combined.encode("utf-8")).rstrip(b"=").decode("ascii")
    return f"NUC-PRO-{encoded}"


def generate_license_key(email: str, tier: str = "pro", days: int = 365,
                         private_key_pem: str = "") -> str:
    """Generate a signed license key. Requires the issuer private key.

    This runs server-side (Stripe webhook or manual generation), never on client.
    """
    from .identity.keygen import KeyManager
    km = KeyManager()

    exp = datetime.now(timezone.utc) + timedelta(days=days)
    payload = {
        "email": email,
        "tier": tier,
        "exp": exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = km.sign(private_key_pem, payload_json.encode("utf-8"))
    return _encode_key(payload, signature)


def generate_trial_key() -> str:
    """Generate a self-signed 14-day trial key (local, no server needed)."""
    from .identity.keygen import KeyManager
    km = KeyManager()
    kp = km.generate_keypair()

    exp = datetime.now(timezone.utc) + timedelta(days=14)
    payload = {
        "email": "trial@local",
        "tier": "trial",
        "exp": exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trial_pub": kp.public_key_pem,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = km.sign(kp.private_key_pem, payload_json.encode("utf-8"))
    return _encode_key(payload, signature)


def validate_license_key(raw: str) -> LicenseInfo:
    """Validate a license key offline. Returns LicenseInfo."""
    try:
        payload, signature = _decode_key(raw.strip())
    except Exception as e:
        return LicenseInfo(valid=False, tier="free", email="", expires=None,
                           error=f"Malformed key: {e}")

    tier = payload.get("tier", "")
    email = payload.get("email", "")
    exp_str = payload.get("exp", "")

    # Check expiry
    try:
        expires = datetime.strptime(exp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return LicenseInfo(valid=False, tier="free", email=email, expires=None,
                           error="Invalid expiry date")

    if datetime.now(timezone.utc) > expires:
        return LicenseInfo(valid=False, tier="free", email=email, expires=expires,
                           error="License expired")

    # Verify signature
    from .identity.keygen import KeyManager
    km = KeyManager()
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)

    if tier == "trial":
        # Trial keys are self-signed — verify against embedded public key
        pub_pem = payload.get("trial_pub", "")
        if not pub_pem:
            return LicenseInfo(valid=False, tier="free", email=email, expires=expires,
                               error="Trial key missing public key")
        ok = km.verify(pub_pem, signature, payload_json.encode("utf-8"))
    else:
        # Pro keys verified against bundled issuer public key
        if not _ISSUER_KEY_READY:
            # Until issuer key is generated, accept any structurally valid key
            # This lets development proceed. Remove this fallback before launch.
            logger.warning("Issuer key not configured — accepting key without signature check")
            ok = True
        else:
            ok = km.verify(_ISSUER_PUBLIC_KEY_PEM, signature, payload_json.encode("utf-8"))

    if not ok:
        return LicenseInfo(valid=False, tier="free", email=email, expires=expires,
                           error="Invalid signature")

    return LicenseInfo(valid=True, tier=tier, email=email, expires=expires, error=None)


def save_license(key: str) -> Path:
    """Save license key to ~/.nucleus/license.key."""
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(key.strip() + "\n")
    return LICENSE_FILE


def load_license() -> LicenseInfo:
    """Load and validate license from ~/.nucleus/license.key."""
    if not LICENSE_FILE.exists():
        return FREE
    raw = LICENSE_FILE.read_text().strip()
    if not raw:
        return FREE
    return validate_license_key(raw)


def is_pro() -> bool:
    """Quick check: does the user have a valid Pro or Trial license?"""
    info = load_license()
    return info.valid and info.tier in ("pro", "trial")


# ── Ed25519 ELT (Eidetic License Token) — JWT-style API ─────────────────────
# Distinct from NUC-PRO format above. Used by Cloudflare Workers + daemon for
# refreshable subscription-bound tokens. Aligns with A1 lane brief.
#
# Token format: base64url(header_json).base64url(claims_json).base64url(sig)
# Header:       {"alg": "EdDSA", "typ": "ELT"}
# Claims:       {"sub": customer_id, "tier": "free"|"pro"|"team"|"founder",
#                "seat_count": int, "iat": ts, "exp": ts, "email_hash": ...}
# Clock skew:   30s past (exp), 60s future (iat)
#
# Tier semantics (E2 lane, 2026-05-22):
#   free     — local-only daemon, no cloud sync, no nucleus_ask recall
#   pro      — single-seat managed R2 sync + nucleus_ask (seat_count==1)
#   team     — multi-seat shared engrams (seat_count>=1, default 1)
#   founder  — lifetime Pro (first 30 customers; seat_count==1)
#
# Backwards-compat: ELT tokens issued before this lane did not carry `tier`
# field at the daemon layer (worker hard-coded "pro"). Tokens without an
# explicit `tier` claim default to "pro" on verify (LEGACY_DEFAULT_TIER).

import time as _time

ELT_HEADER = {"alg": "EdDSA", "typ": "ELT"}
ELT_HEADER_JSON = json.dumps(ELT_HEADER, separators=(",", ":"), sort_keys=True)
ELT_CLOCK_SKEW_PAST = 30   # seconds past exp still accepted
ELT_CLOCK_SKEW_FUTURE = 60  # seconds future iat still accepted

VALID_TIERS = ("free", "pro", "team", "founder")
LEGACY_DEFAULT_TIER = "pro"  # tokens without tier field default to pro


def _default_seat_count(tier: str) -> int:
    """Per-tier default seat count.

    free=0 (no managed surface), pro=1, founder=1, team=1 (caller can override).
    """
    if tier == "free":
        return 0
    return 1


def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 encode, no padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """URL-safe base64 decode, restore padding."""
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + ("=" * pad))


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 keypair as PEM bytes.

    Returns:
        (private_pem, public_pem) — both bytes.

    Use once, store private key in secrets manager (e.g. wrangler secret put
    LICENSE_PRIVATE_KEY), distribute public key in daemon binary.
    """
    from .identity.keygen import KeyManager
    km = KeyManager()
    kp = km.generate_keypair()
    return kp.private_key_pem.encode("utf-8"), kp.public_key_pem.encode("utf-8")


def sign_license(
    payload: dict,
    private_key_pem: bytes,
    *,
    ttl_seconds: int = 86400,
    tier: Optional[str] = None,
    seat_count: Optional[int] = None,
) -> str:
    """Sign a license payload, producing an ELT compact token.

    The supplied payload should contain at minimum: sub, email_hash.
    iat and exp are stamped automatically (caller-provided values are
    overridden — if you need custom iat/exp use _sign_license_raw).

    Tier + seat_count (E2 lane, 2026-05-22):
      - If `tier` arg supplied, overrides any tier in payload.
      - If `tier` not supplied and not in payload, defaults to "pro" (legacy
        behaviour preserved — pre-E2 callers issued pro-only tokens).
      - `seat_count` defaults per-tier: free=0, pro/founder/team=1. Team
        callers can override with explicit value.

    Args:
        payload: dict with sub, email_hash (and any extra fields; tier may
                 be in payload as fallback if tier arg is None)
        private_key_pem: Ed25519 private key bytes (PEM-encoded)
        ttl_seconds: token lifetime, default 24h
        tier: optional tier override ("free"|"pro"|"team"|"founder")
        seat_count: optional seat_count override (>=0)

    Returns:
        Compact ELT token: header.claims.signature (base64url segments)
    """
    if not isinstance(private_key_pem, (bytes, bytearray)):
        raise TypeError("private_key_pem must be bytes")
    now = int(_time.time())
    claims = dict(payload)

    # Resolve tier: arg > payload > legacy default
    resolved_tier = tier if tier is not None else claims.get("tier", LEGACY_DEFAULT_TIER)
    if resolved_tier not in VALID_TIERS:
        raise ValueError(
            f"invalid tier: {resolved_tier!r} (valid: {VALID_TIERS})"
        )
    claims["tier"] = resolved_tier

    # Resolve seat_count: arg > payload > per-tier default
    if seat_count is not None:
        if not isinstance(seat_count, int) or seat_count < 0:
            raise ValueError(f"seat_count must be non-negative int, got {seat_count!r}")
        claims["seat_count"] = seat_count
    elif "seat_count" not in claims:
        claims["seat_count"] = _default_seat_count(resolved_tier)

    claims["iat"] = now
    claims["exp"] = now + int(ttl_seconds)
    return _sign_license_raw(claims, private_key_pem)


def _sign_license_raw(claims: dict, private_key_pem: bytes) -> str:
    """Lower-level signing — caller controls iat/exp. Used by tests."""
    from .identity.keygen import KeyManager
    km = KeyManager()

    header_b64 = _b64url_encode(ELT_HEADER_JSON.encode("utf-8"))
    claims_json = json.dumps(claims, separators=(",", ":"), sort_keys=True)
    claims_b64 = _b64url_encode(claims_json.encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")
    signature = km.sign(private_key_pem.decode("utf-8"), signing_input)
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{claims_b64}.{sig_b64}"


def verify_license(token: str, public_key_pem: bytes) -> Optional[dict]:
    """Verify an ELT token. Return claims dict if valid, None otherwise.

    Performs (in order):
    1. Structural parsing — three base64url segments
    2. Header check — alg=EdDSA, typ=ELT (rejects JWT lookalikes)
    3. Ed25519 signature verification (constant-time via cryptography lib)
    4. Expiry check (now < exp + 30s skew)
    5. Issued-at sanity (iat < now + 60s skew)
    """
    if not isinstance(token, str) or not isinstance(public_key_pem, (bytes, bytearray)):
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, claims_b64, sig_b64 = parts

    # Decode header + validate alg/typ
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(header, dict):
        return None
    if header.get("alg") != "EdDSA" or header.get("typ") != "ELT":
        return None

    # Decode claims
    try:
        claims = json.loads(_b64url_decode(claims_b64).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(claims, dict):
        return None

    # Decode signature
    try:
        signature = _b64url_decode(sig_b64)
    except Exception:
        return None

    # Verify signature (constant-time via cryptography lib)
    from .identity.keygen import KeyManager
    km = KeyManager()
    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")
    if not km.verify(public_key_pem.decode("utf-8"), signature, signing_input):
        return None

    # Expiry checks (after signature verified, to avoid timing leak)
    now = int(_time.time())
    exp = claims.get("exp")
    iat = claims.get("iat")
    if not isinstance(exp, (int, float)) or not isinstance(iat, (int, float)):
        return None
    if now > exp + ELT_CLOCK_SKEW_PAST:
        return None
    if iat > now + ELT_CLOCK_SKEW_FUTURE:
        return None

    # E2 lane: backfill tier + seat_count for legacy tokens (issued before
    # the E2 tier-claim was added). Signature was verified against the
    # ORIGINAL claims dict, so this mutation happens AFTER verify so the
    # caller sees a tier-shaped claims dict regardless of token vintage.
    if "tier" not in claims:
        claims["tier"] = LEGACY_DEFAULT_TIER
    elif claims["tier"] not in VALID_TIERS:
        # Future-tier protection: unknown tier values surface as None so
        # the daemon gates everything off rather than fall-open.
        return None
    if "seat_count" not in claims:
        claims["seat_count"] = _default_seat_count(claims["tier"])
    elif not isinstance(claims["seat_count"], int) or claims["seat_count"] < 0:
        return None

    return claims
