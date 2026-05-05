"""Nucleus AI Marketplace — Foundation Primitives.

Implements the CapabilityRegistry for the two-sided AI tool marketplace.
Provides permanent addresses and capability discovery for tools connected
to the Nucleus relay bus.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .common import get_brain_path

logger = logging.getLogger("nucleus.marketplace")

# Strict format: alphanumerics and dashes only, ending in @nucleus
_ADDRESS_RE = re.compile(r"^[a-z0-9\-]+@nucleus$")


def _get_registry_dir(brain_path: Optional[Path] = None) -> Path:
    """Get the registry directory, creating it if needed."""
    brain = brain_path or get_brain_path()
    registry_dir = brain / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    return registry_dir


def _get_card_path(address: str, registry_dir: Path) -> Path:
    """Get the file path for a specific capability card."""
    # Strip @nucleus to form the filename
    slug = address.split("@")[0]
    return registry_dir / f"{slug}.json"


def register_tool(card_data: Dict[str, Any], brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Register a new tool or update an existing one in the capability registry.

    Args:
        card_data: A dict containing capability card fields. Must include at least:
            - address: The tool's unique address (e.g., 'pr-reviewer@nucleus')
            - display_name: Human readable name
            - accepts: List of supported input subjects/intents
            - emits: List of possible output subjects/intents
        brain_path: Override for .brain directory.

    Returns:
        The updated capability card with platform metadata attached.
    """
    address = card_data.get("address", "")
    if not isinstance(address, str) or not _ADDRESS_RE.match(address):
        raise ValueError(f"Invalid address format: {address}. Must match '{_ADDRESS_RE.pattern}'.")

    for required in ("display_name", "accepts", "emits"):
        if not card_data.get(required):
            raise ValueError(f"Capability card missing required field: {required}")

    registry_dir = _get_registry_dir(brain_path)
    card_path = _get_card_path(address, registry_dir)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Merge with existing card if it exists
    if card_path.exists():
        try:
            existing = json.loads(card_path.read_text())
            card = {**existing, **card_data}
            # Preserve original registration date
            card["registered_at"] = existing.get("registered_at", now)
        except Exception as e:
            logger.warning(f"Failed to read existing card for {address}, overwriting. Error: {e}")
            card = dict(card_data)
            card["registered_at"] = now
    else:
        card = dict(card_data)
        card["registered_at"] = now

        # Initialize reputation signals to default
        card.setdefault("status", "active")
        card.setdefault("last_seen_at", now)
        card.setdefault("connection_count", 0)
        card.setdefault("avg_response_ms", 0)
        card.setdefault("success_rate", 1.0)
        card.setdefault("tier", TrustTier.UNVERIFIED)
        card.setdefault("tier_badge", TrustTier.get_display_badge(TrustTier.UNVERIFIED))
        card.setdefault("tags", [])

    # Ensure list types
    if not isinstance(card["accepts"], list):
        card["accepts"] = [card["accepts"]]
    if not isinstance(card["emits"], list):
        card["emits"] = [card["emits"]]
    if not isinstance(card.get("tags", []), list):
        card["tags"] = [card.get("tags")]

    card_path.write_text(json.dumps(card, indent=2))
    return card


def lookup_by_address(address: str, brain_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Look up a capability card by its permanent address."""
    if not isinstance(address, str) or not _ADDRESS_RE.match(address):
        return None

    registry_dir = _get_registry_dir(brain_path)
    card_path = _get_card_path(address, registry_dir)

    if not card_path.is_file():
        return None

    try:
        return json.loads(card_path.read_text())
    except Exception as e:
        logger.error(f"Failed to parse card for {address}: {e}")
        return None


def search_by_tags(tags: List[str], brain_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Search for tools that match ANY of the provided tags.
    
    If tags is empty, returns all registered tools.
    """
    registry_dir = _get_registry_dir(brain_path)
    
    if not registry_dir.exists():
        return []

    query_tags = set(t.lower() for t in tags)
    results = []

    for card_path in registry_dir.glob("*.json"):
        if not card_path.is_file():
            continue
            
        try:
            card = json.loads(card_path.read_text())
        except Exception:
            continue
            
        if not query_tags:
            results.append(card)
            continue
            
        card_tags: Set[str] = set()
        for t in card.get("tags", []):
            if isinstance(t, str):
                card_tags.add(t.lower())
                
        if query_tags & card_tags:
            results.append(card)

    # Sort deterministically by registration date (newest first)
    results.sort(key=lambda c: c.get("registered_at", ""), reverse=True)
    return results


class CapabilityRegistry:
    """Static helpers for the capability registry — prune, audit, and bookkeeping."""

    @staticmethod
    def mark_stale(
        threshold_days: int = 90,
        brain_path: Optional[Path] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Mark registry entries with no interactions in > threshold_days as inactive.

        Idempotent — already-inactive entries are left unchanged. Active addresses
        are never touched. Preserves full audit trail (no deletion).

        Args:
            threshold_days: Entries older than this with no interactions are marked.
            brain_path: Override for .brain directory.
            now: Reference "current time" (injectable for tests).

        Returns:
            Summary dict: {"marked": [addresses], "skipped": int, "total": int}
        """
        registry_dir = _get_registry_dir(brain_path)
        telemetry_file = ReputationSignals._get_telemetry_file(brain_path)
        current_time = now or datetime.now(timezone.utc)

        # Build last_interaction_at index from telemetry
        last_seen_index: Dict[str, str] = {}
        if telemetry_file.exists():
            try:
                with open(telemetry_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                            addr = event.get("to_address", "")
                            ts = event.get("timestamp", "")
                            if addr and ts:
                                if addr not in last_seen_index or ts > last_seen_index[addr]:
                                    last_seen_index[addr] = ts
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"mark_stale: failed reading telemetry: {e}")

        marked = []
        skipped = 0
        total = 0

        for card_path in registry_dir.glob("*.json"):
            if not card_path.is_file():
                continue
            total += 1
            try:
                card = json.loads(card_path.read_text())
            except Exception:
                skipped += 1
                continue

            address = card.get("address", "")

            # Determine last activity: telemetry index > card last_seen_at > registered_at
            last_activity_str = (
                last_seen_index.get(address)
                or card.get("last_seen_at")
                or card.get("registered_at")
            )

            if not last_activity_str:
                skipped += 1
                continue

            try:
                dt_str = last_activity_str.replace("Z", "+00:00")
                last_activity_dt = datetime.fromisoformat(dt_str)
                days_since = (current_time - last_activity_dt).days
            except Exception as e:
                logger.warning(f"mark_stale: could not parse date for {address}: {e}")
                skipped += 1
                continue

            if days_since > threshold_days:
                card["inactive"] = True
                card["inactive_since"] = current_time.isoformat().replace("+00:00", "Z")
                card["inactive_reason"] = f"no_interaction_{days_since}d"
                try:
                    card_path.write_text(json.dumps(card, indent=2))
                    marked.append(address)
                except Exception as e:
                    logger.error(f"mark_stale: failed writing card for {address}: {e}")
                    skipped += 1

        return {"marked": marked, "skipped": skipped, "total": total}


class ReputationSignals:
    """Computes and tracks trust signals from relay telemetry."""
    
    @staticmethod
    def _get_telemetry_file(brain_path: Optional[Path] = None) -> Path:
        brain = brain_path or get_brain_path()
        telemetry_dir = brain / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        return telemetry_dir / "relay_metrics.jsonl"

    @staticmethod
    def record_interaction(to_address: str, from_address: str, latency_ms: int, success: bool, brain_path: Optional[Path] = None) -> None:
        """Record a relay interaction for reputation scoring.
        
        Args:
            to_address: The target tool's permanent address
            from_address: The sender's identity/session
            latency_ms: Round-trip time
            success: Whether the message was successfully processed
            brain_path: Override for .brain directory
        """
        telemetry_file = ReputationSignals._get_telemetry_file(brain_path)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        event = {
            "timestamp": now,
            "to_address": to_address,
            "from_address": from_address,
            "latency_ms": latency_ms,
            "success": success
        }
        
        try:
            with open(telemetry_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write reputation telemetry: {e}")

    @staticmethod
    def apply_decay(metrics: Dict[str, Any], now: Optional[datetime] = None, half_life_days: int = 30) -> Dict[str, Any]:
        """Apply a half-life decay to reputation metrics based on inactivity."""
        last_seen = metrics.get("last_seen_at")
        if not last_seen:
            return metrics

        try:
            dt_str = last_seen.replace("Z", "+00:00")
            last_seen_dt = datetime.fromisoformat(dt_str)
            current_time = now or datetime.now(timezone.utc)
            days_stale = max(0.0, (current_time - last_seen_dt).total_seconds() / 86400.0)

            decay_factor = (0.5) ** (days_stale / half_life_days)
            
            decayed = dict(metrics)
            # Connection count determines tier, decaying it effectively decays reputation
            decayed["connection_count"] = max(0, round(metrics["connection_count"] * decay_factor))
            return decayed
        except Exception as e:
            logger.error(f"Failed to apply reputation decay: {e}")
            return metrics

    @staticmethod
    def compute_signals(address: str, brain_path: Optional[Path] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Compute reputation metrics from telemetry history."""
        telemetry_file = ReputationSignals._get_telemetry_file(brain_path)
        
        default_metrics = {
            "connection_count": 0,
            "avg_response_ms": 0,
            "success_rate": 1.0,
            "last_seen_at": None
        }
        
        if not telemetry_file.exists():
            return default_metrics
            
        unique_connections = set()
        latencies = []
        total_deliveries = 0
        successful_deliveries = 0
        last_seen = None
        
        try:
            with open(telemetry_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("to_address") == address:
                            unique_connections.add(event.get("from_address"))
                            latencies.append(event.get("latency_ms", 0))
                            total_deliveries += 1
                            if event.get("success"):
                                successful_deliveries += 1
                            
                            ev_time = event.get("timestamp")
                            if ev_time and (not last_seen or ev_time > last_seen):
                                last_seen = ev_time
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Failed to read reputation telemetry: {e}")
            return default_metrics
            
        success_rate = 1.0
        if total_deliveries > 0:
            success_rate = successful_deliveries / total_deliveries
            
        avg_latency = 0
        if latencies:
            latencies.sort()
            avg_latency = latencies[len(latencies) // 2]  # median
            
        metrics = {
            "connection_count": len(unique_connections),
            "avg_response_ms": avg_latency,
            "success_rate": round(success_rate, 4),
            "last_seen_at": last_seen
        }
        
        return ReputationSignals.apply_decay(metrics, now=now)


class TrustTier(IntEnum):
    UNVERIFIED = 0
    ACTIVE = 1
    TRUSTED = 2
    VERIFIED = 3

    @classmethod
    def evaluate(cls, card: Dict[str, Any], metrics: Dict[str, Any]) -> "TrustTier":
        """Evaluate a tool's trust tier based on capability card and reputation signals."""
        
        # Verified is a manual override state, typically via platform admin
        if card.get("verified_override", False):
            return cls.VERIFIED
            
        conns = metrics.get("connection_count", 0)
        success_rate = metrics.get("success_rate", 1.0)
        
        # Calculate age in days
        registered_at_str = card.get("registered_at")
        age_days = 0
        if registered_at_str:
            try:
                dt_str = registered_at_str.replace("Z", "+00:00")
                registered_dt = datetime.fromisoformat(dt_str)
                now = datetime.now(timezone.utc)
                age_days = (now - registered_dt).days
            except Exception:
                pass
                
        if conns >= 50 and success_rate >= 0.95 and age_days >= 30:
            return cls.TRUSTED
            
        if conns >= 5 and success_rate >= 0.90:
            return cls.ACTIVE
            
        return cls.UNVERIFIED

    @classmethod
    def get_display_badge(cls, tier: "TrustTier") -> str:
        if tier == cls.VERIFIED:
            return "Verified"
        if tier == cls.TRUSTED:
            return "Trusted"
        if tier == cls.ACTIVE:
            return "Active"
        return "New"


class MessageGuard:
    @staticmethod
    def detect_injection(payload: str) -> Optional[str]:
        """Detect injection risks using relay_route pattern scanning."""
        from mcp_server_nucleus.http_transport.relay_route import scan_injection_patterns
        is_injection, pattern = scan_injection_patterns(payload)
        return pattern if is_injection else None
        
    @staticmethod
    def quarantine(payload: str, reason: str, address: Optional[str] = None, brain_path: Optional[Path] = None) -> None:
        """Quarantine a message payload for an address."""
        telemetry_dir = (brain_path or get_brain_path()) / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        q_file = telemetry_dir / "quarantine.jsonl"
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "reason": reason,
            "address": address
        }
        with open(q_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


class ListingEligibility:
    @staticmethod
    def check_pre_listing(card: Dict[str, Any], brain_path: Optional[Path] = None) -> Tuple[bool, str]:
        """Verify if a tool card is eligible for marketplace listing."""
        address = card.get("address")
        if not address:
            return False, "Missing address"
            
        if not card.get("display_name"):
            return False, "Missing display_name"
        if not card.get("accepts") or not card.get("emits"):
            return False, "Missing accepts or emits signature"
            
        telemetry_dir = (brain_path or get_brain_path()) / "telemetry"
        q_file = telemetry_dir / "quarantine.jsonl"
        if q_file.exists():
            try:
                count = 0
                with open(q_file, "r") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            data = json.loads(line)
                            if data.get("address") == address:
                                count += 1
                        except Exception:
                            pass
                if count > 5:
                    return False, "Failed quarantine threshold"
            except Exception:
                pass
                
        return True, "Eligible"
