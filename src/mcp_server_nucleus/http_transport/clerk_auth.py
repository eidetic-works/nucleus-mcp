"""Clerk JWT verification for OAuth email-verified identity.

Clerk (https://clerk.com) handles user authentication — magic links,
Google/GitHub OAuth, MFA — and issues a session JWT that Nucleus verifies
to extract a *verified* email claim.  Nucleus then derives its own
tenant_id from that email and mints its own opaque access token.

The sovereignty line: Clerk verifies identity; Nucleus owns everything
downstream (tenant isolation, brain storage, token format, TTL, revocation).
If Clerk disappears, existing Nucleus tokens still work until they expire;
only new-user verification breaks — a recoverable failure, not a
catastrophic one.

Env contract:
  NUCLEUS_CLERK_ENABLED           "true" to enable Clerk integration
  NUCLEUS_CLERK_ISSUER            Clerk JWT issuer (your Clerk frontend API URL,
                                  e.g. https://your-app.clerk.accounts.dev)
  NUCLEUS_CLERK_JWKS_URL          Optional override for JWKS endpoint
                                  (default: {issuer}/.well-known/jwks.json)
  NUCLEUS_CLERK_JWKS_CACHE_TTL    JWKS cache TTL in seconds (default: 300)

Pseudonymity: emails are never logged; only the derived tenant_id (a
SHA-256 hash) appears in logs.  The JWT itself is verified and discarded.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("nucleus.clerk_auth")

# ── Configuration ────────────────────────────────────────────────────────

_JWKS_CACHE: Optional[Dict[str, Any]] = None  # {"keys": [...], "fetched_at": ts}
_JWKS_CACHE_TTL_DEFAULT = 300  # 5 minutes


def _clerk_enabled() -> bool:
    return os.environ.get("NUCLEUS_CLERK_ENABLED", "false").lower() == "true"


def _clerk_issuer() -> str:
    return os.environ.get("NUCLEUS_CLERK_ISSUER", "").rstrip("/")


def _clerk_jwks_url() -> str:
    override = os.environ.get("NUCLEUS_CLERK_JWKS_URL", "").strip()
    if override:
        return override
    issuer = _clerk_issuer()
    if not issuer:
        raise ValueError("NUCLEUS_CLERK_ISSUER not configured")
    return f"{issuer}/.well-known/jwks.json"


def _jwks_cache_ttl() -> int:
    return int(os.environ.get("NUCLEUS_CLERK_JWKS_CACHE_TTL", _JWKS_CACHE_TTL_DEFAULT))


# ── JWKS fetching with caching ───────────────────────────────────────────

def _fetch_jwks() -> Dict[str, Any]:
    """Fetch Clerk's JWKS with in-memory caching.

    Returns a dict with a "keys" list per RFC 7517.
    """
    global _JWKS_CACHE
    now = time.time()
    if _JWKS_CACHE and (now - _JWKS_CACHE["fetched_at"]) < _jwks_cache_ttl():
        return _JWKS_CACHE

    url = _clerk_jwks_url()
    logger.debug("Fetching Clerk JWKS from %s", url)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "keys" not in data:
            raise ValueError("JWKS response missing 'keys' field")
        _JWKS_CACHE = {"keys": data["keys"], "fetched_at": now}
        logger.info("Clerk JWKS fetched: %d keys", len(data["keys"]))
        return _JWKS_CACHE
    except Exception as e:
        logger.warning("Clerk JWKS fetch failed: %s", e)
        # Return stale cache if available (better than nothing)
        if _JWKS_CACHE:
            logger.info("Using stale Clerk JWKS cache")
            return _JWKS_CACHE
        raise


def _clear_jwks_cache() -> None:
    """Clear the JWKS cache (for testing)."""
    global _JWKS_CACHE
    _JWKS_CACHE = None


# ── JWT verification ─────────────────────────────────────────────────────

def verify_clerk_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Clerk session JWT and return its claims.

    Verifies:
      - RS256 signature against Clerk's JWKS
      - issuer matches NUCLEUS_CLERK_ISSUER
      - token is not expired (exp claim)
      - token is not used before valid (nbf claim, if present)

    Returns the claims dict on success, None on failure.
    The email claim is extracted by the caller — this function only
    verifies cryptographic integrity.
    """
    if not _clerk_enabled():
        logger.debug("Clerk not enabled — skipping JWT verification")
        return None

    try:
        import jwt as pyjwt
        from jwt.algorithms import RSAAlgorithm
    except ImportError:
        logger.error("PyJWT not installed — cannot verify Clerk JWT")
        return None

    issuer = _clerk_issuer()
    if not issuer:
        logger.error("NUCLEUS_CLERK_ISSUER not configured")
        return None

    try:
        # Decode without verification first to get the kid
        unverified_header = pyjwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            logger.warning("Clerk JWT missing 'kid' header")
            return None

        # Fetch JWKS and find matching key
        jwks = _fetch_jwks()
        matching_key = None
        for key in jwks["keys"]:
            if key.get("kid") == kid:
                matching_key = key
                break

        if not matching_key:
            logger.warning("No JWKS key matching kid=%s — refreshing cache", kid[:8])
            _clear_jwks_cache()
            jwks = _fetch_jwks()
            for key in jwks["keys"]:
                if key.get("kid") == kid:
                    matching_key = key
                    break
            if not matching_key:
                logger.warning("Clerk JWT kid=%s not found in JWKS", kid[:8])
                return None

        # Construct the public key from JWK
        public_key = RSAAlgorithm.from_jwk(json.dumps(matching_key))

        # Verify the JWT
        claims = pyjwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_exp": True,
                "verify_nbf": True,
                "verify_aud": False,  # Clerk session JWTs don't always set aud
            },
        )
        logger.debug("Clerk JWT verified: sub=%s", claims.get("sub", "")[:8])
        return claims

    except Exception as e:
        logger.warning("Clerk JWT verification failed: %s", e)
        return None


def extract_email(claims: Dict[str, Any]) -> Optional[str]:
    """Extract a verified email from Clerk JWT claims.

    Clerk includes email in the JWT payload when the user has a verified
    email address.  The claim location varies by Clerk version:
      - Top-level "email" (most common)
      - "email_address" (older Clerk versions)

    Only returns the email if Clerk has marked it as verified.
    """
    email = claims.get("email") or claims.get("email_address")
    if not email:
        return None

    # Clerk sets email_verified=true in the JWT when the email is verified
    # via magic link or OAuth provider.  If the claim is missing, be
    # conservative and treat as unverified.
    verified = claims.get("email_verified", claims.get("emailVerified", False))
    if not verified:
        logger.warning("Clerk JWT email not verified — rejecting")
        return None

    return email.strip().lower()
