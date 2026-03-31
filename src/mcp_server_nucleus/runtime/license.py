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
