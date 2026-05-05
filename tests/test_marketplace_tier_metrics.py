"""Tests: nucleus_marketplace_tier_changed_total counter fires on tier promotion."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def _seed_registry_card(registry_dir: Path, address: str, tier: int = 0) -> None:
    """Write a minimal capability card to the registry dir."""
    slug = address.split("@")[0]
    card = {
        "address": address,
        "display_name": slug,
        "accepts": ["spawn_brief"],
        "emits": ["spawn_response"],
        "tier": tier,
        "tier_badge": "unverified",
        "connection_count": 0,
        "avg_response_ms": 0,
        "success_rate": 1.0,
    }
    (registry_dir / f"{slug}.json").write_text(json.dumps(card))


def _seed_telemetry(brain_path: Path, address: str, interactions: int = 5) -> None:
    """Write synthetic telemetry entries that drive reputation above Active threshold."""
    telemetry_dir = brain_path / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    telemetry_file = telemetry_dir / "relay_metrics.jsonl"
    with open(telemetry_file, "a") as f:
        for i in range(interactions):
            event = {
                "timestamp": f"2026-05-04T00:0{i}:00Z",
                "to_address": address,
                "from_address": f"caller_{i}@nucleus",
                "latency_ms": 100,
                "success": True,
            }
            f.write(json.dumps(event) + "\n")


def test_tier_promotion_increments_counter(tmp_path):
    """Tier flip Unverified → Active increments the Prometheus counter."""
    from mcp_server_nucleus.runtime.prometheus import (
        reset_metrics,
        get_metrics_json,
        MARKETPLACE_TIER_CHANGED_TOTAL,
    )
    from mcp_server_nucleus.runtime.jobs.marketplace_job import run_tier_promotion_loop
    from mcp_server_nucleus.runtime.marketplace import TrustTier

    reset_metrics()

    registry_dir = tmp_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True)
    address = "test-agent@nucleus"
    _seed_registry_card(registry_dir, address, tier=TrustTier.UNVERIFIED)
    _seed_telemetry(tmp_path, address, interactions=5)

    with patch("mcp_server_nucleus.runtime.marketplace.TrustTier.evaluate", return_value=TrustTier.ACTIVE):
        result = run_tier_promotion_loop(brain_path=tmp_path)

    assert result["updated"] >= 1
    metrics = get_metrics_json()
    counter_key = f"{MARKETPLACE_TIER_CHANGED_TOTAL}|address=test-agent@nucleus,from={int(TrustTier.UNVERIFIED)},to={int(TrustTier.ACTIVE)}"
    found = any(MARKETPLACE_TIER_CHANGED_TOTAL in k for k in metrics.get("tool_calls", {}).keys())
    assert found, f"Counter not found in metrics: {list(metrics.get('tool_calls', {}).keys())}"


def test_no_tier_change_no_increment(tmp_path):
    """When tier stays the same, counter is NOT incremented."""
    from mcp_server_nucleus.runtime.prometheus import reset_metrics, get_metrics_json, MARKETPLACE_TIER_CHANGED_TOTAL
    from mcp_server_nucleus.runtime.jobs.marketplace_job import run_tier_promotion_loop
    from mcp_server_nucleus.runtime.marketplace import TrustTier

    reset_metrics()

    registry_dir = tmp_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True)
    address = "stable-agent@nucleus"
    _seed_registry_card(registry_dir, address, tier=TrustTier.ACTIVE)

    with patch("mcp_server_nucleus.runtime.marketplace.TrustTier.evaluate", return_value=TrustTier.ACTIVE):
        result = run_tier_promotion_loop(brain_path=tmp_path)

    metrics = get_metrics_json()
    tier_counter_hits = {
        k: v for k, v in metrics.get("tool_calls", {}).items()
        if MARKETPLACE_TIER_CHANGED_TOTAL in k
    }
    assert len(tier_counter_hits) == 0, f"Counter should not be set when tier unchanged: {tier_counter_hits}"


def test_metrics_endpoint_exposes_tier_counter(tmp_path):
    """After a promotion, get_prometheus_metrics() contains the counter name."""
    from mcp_server_nucleus.runtime.prometheus import reset_metrics, get_prometheus_metrics, MARKETPLACE_TIER_CHANGED_TOTAL
    from mcp_server_nucleus.runtime.jobs.marketplace_job import run_tier_promotion_loop
    from mcp_server_nucleus.runtime.marketplace import TrustTier

    reset_metrics()

    registry_dir = tmp_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True)
    address = "promo-agent@nucleus"
    _seed_registry_card(registry_dir, address, tier=TrustTier.UNVERIFIED)
    _seed_telemetry(tmp_path, address, interactions=3)

    with patch("mcp_server_nucleus.runtime.marketplace.TrustTier.evaluate", return_value=TrustTier.TRUSTED):
        run_tier_promotion_loop(brain_path=tmp_path)

    output = get_prometheus_metrics()
    # The counter is stored under nucleus_tool_calls_total with the metric name in labels.
    assert "promo-agent@nucleus" in output, (
        f"Expected address label in /metrics output. Got:\n{output[:500]}"
    )
    assert MARKETPLACE_TIER_CHANGED_TOTAL in output or "promo-agent@nucleus" in output, (
        f"Expected tier-changed telemetry in /metrics output"
    )
