"""Nucleus Runtime — OpenTelemetry Export Layer.

Additive OTel export for Nucleus events, decisions, and metrics.
Maps existing Nucleus primitives to OTel spans/metrics without
touching events.jsonl or any existing audit infrastructure.

Config (env vars):
    NUCLEUS_OTEL_ENABLED      — "true" to activate (default: "false")
    NUCLEUS_OTEL_ENDPOINT     — OTLP gRPC endpoint (default: "https://telemetry.googleapis.com")
    NUCLEUS_OTEL_SERVICE_NAME — service name in traces (default: "nucleus-agent-os")

Usage:
    from mcp_server_nucleus.runtime.otel_export import (
        record_dispatch_span,
        record_semantic_event,
        inc_engram_write,
        inc_engram_read,
    )
"""

import logging
import os
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("nucleus.otel_export")

# ── Configuration ────────────────────────────────────────────
_OTEL_ENABLED = os.environ.get("NUCLEUS_OTEL_ENABLED", "false").lower() == "true"
_OTEL_ENDPOINT = os.environ.get("NUCLEUS_OTEL_ENDPOINT", "https://telemetry.googleapis.com")
_OTEL_SERVICE_NAME = os.environ.get("NUCLEUS_OTEL_SERVICE_NAME", "nucleus-agent-os")

# ── Lazy-init singletons ────────────────────────────────────
_init_lock = threading.Lock()
_initialized = False
_tracer = None
_meter = None

# Instruments (created on init)
_engram_write_counter = None
_engram_read_counter = None
_dispatch_duration_histogram = None
_workflow_cost_histogram = None


def otel_enabled() -> bool:
    """Check if OTel export is active."""
    return _OTEL_ENABLED


def _ensure_initialized():
    """Lazy-initialize OTel providers on first use. Thread-safe."""
    global _initialized, _tracer, _meter
    global _engram_write_counter, _engram_read_counter
    global _dispatch_duration_histogram, _workflow_cost_histogram

    if _initialized or not _OTEL_ENABLED:
        return

    with _init_lock:
        if _initialized:
            return

        try:
            from opentelemetry import metrics as otel_metrics
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create({"service.name": _OTEL_SERVICE_NAME})

            # Trace provider
            span_exporter = OTLPSpanExporter(endpoint=_OTEL_ENDPOINT)
            tracer_provider = TracerProvider(resource=resource)
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
            trace.set_tracer_provider(tracer_provider)
            _tracer = trace.get_tracer("nucleus-agent-os", "1.0.0")

            # Metrics provider
            metric_exporter = OTLPMetricExporter(endpoint=_OTEL_ENDPOINT)
            metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60000)
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            otel_metrics.set_meter_provider(meter_provider)
            _meter = otel_metrics.get_meter("nucleus-agent-os", "1.0.0")

            # Create instruments
            _engram_write_counter = _meter.create_counter(
                name="nucleus.engram.writes",
                description="Number of engram write operations",
                unit="1",
            )
            _engram_read_counter = _meter.create_counter(
                name="nucleus.engram.reads",
                description="Number of engram read (query/search) operations",
                unit="1",
            )
            _dispatch_duration_histogram = _meter.create_histogram(
                name="nucleus.dispatch.duration_ms",
                description="Facade action dispatch latency in milliseconds",
                unit="ms",
            )
            _workflow_cost_histogram = _meter.create_histogram(
                name="nucleus.workflow.cost",
                description="Cost units per dispatch action",
                unit="1",
            )

            _initialized = True
            logger.info(
                f"OTel initialized: endpoint={_OTEL_ENDPOINT}, service={_OTEL_SERVICE_NAME}"
            )
        except Exception as e:
            logger.warning(f"OTel initialization failed (will no-op): {e}")
            _initialized = True  # Don't retry on every call


def get_tracer():
    """Get the OTel tracer. Returns None if disabled."""
    if not _OTEL_ENABLED:
        return None
    _ensure_initialized()
    return _tracer


def get_meter():
    """Get the OTel meter. Returns None if disabled."""
    if not _OTEL_ENABLED:
        return None
    _ensure_initialized()
    return _meter


# ── Public API: Dispatch Spans ───────────────────────────────

def record_dispatch_span(
    facade: str,
    action: str,
    duration_ms: float,
    error: Optional[str] = None,
) -> None:
    """Record an OTel span for a facade action dispatch.

    Called from tools/_dispatch.py after every handler execution.
    """
    if not _OTEL_ENABLED:
        return

    _ensure_initialized()

    tracer = _tracer
    if tracer is None:
        return

    try:
        from opentelemetry.trace import StatusCode

        span_name = f"{facade}.{action}"
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("nucleus.facade", facade)
            span.set_attribute("nucleus.action", action)
            span.set_attribute("nucleus.duration_ms", duration_ms)

            if error:
                span.set_status(StatusCode.ERROR, error[:200])
                span.set_attribute("nucleus.error", error[:500])
            else:
                span.set_status(StatusCode.OK)

        # Also record in histogram
        if _dispatch_duration_histogram:
            _dispatch_duration_histogram.record(
                duration_ms,
                attributes={"nucleus.facade": facade, "nucleus.action": action},
            )
    except Exception as e:
        logger.debug(f"OTel dispatch span failed: {e}")


# ── Public API: Semantic Events ──────────────────────────────

def record_semantic_event(
    event_type: str,
    emitter: str,
    data: Dict[str, Any],
) -> None:
    """Record an OTel event for a Nucleus semantic event.

    Called from runtime/event_ops.py after every event emission.
    Maps event types to appropriate OTel span events.
    """
    if not _OTEL_ENABLED:
        return

    _ensure_initialized()

    tracer = _tracer
    if tracer is None:
        return

    try:
        # Create a span for the semantic event
        with tracer.start_as_current_span(f"nucleus.event.{event_type}") as span:
            span.set_attribute("nucleus.event_type", event_type)
            span.set_attribute("nucleus.emitter", emitter)

            if event_type == "DecisionMade":
                span.add_event("agent.decision", attributes={
                    "decision_id": str(data.get("decision_id", "")),
                    "reasoning": str(data.get("reasoning", ""))[:200],
                    "confidence": float(data.get("confidence", 0.0)),
                    "context_hash": str(data.get("context_hash", "")),
                })
            elif event_type in ("HITLApproval", "HITLRejection", "ConsentResponse"):
                span.add_event("hitl.gate", attributes={
                    "gate_type": event_type,
                    "emitter": emitter,
                    "description": str(data.get("description", ""))[:200],
                })
            elif event_type == "engram_written":
                span.add_event("engram.write", attributes={
                    "key": str(data.get("key", "")),
                    "context": str(data.get("context", "")),
                    "intensity": int(data.get("intensity", 0)),
                })
            else:
                # Generic event
                span.add_event(f"nucleus.{event_type}", attributes={
                    "emitter": emitter,
                })
    except Exception as e:
        logger.debug(f"OTel semantic event failed: {e}")


# ── Public API: Engram Counters ──────────────────────────────

def inc_engram_write(context: str = "", intensity: int = 0) -> None:
    """Increment the engram writes counter."""
    if not _OTEL_ENABLED:
        return

    _ensure_initialized()

    try:
        if _engram_write_counter:
            attrs = {}
            if context:
                attrs["nucleus.engram.context"] = context
            if intensity:
                attrs["nucleus.engram.intensity"] = intensity
            _engram_write_counter.add(1, attributes=attrs)
    except Exception as e:
        logger.debug(f"OTel engram write counter failed: {e}")


def inc_engram_read() -> None:
    """Increment the engram reads counter."""
    if not _OTEL_ENABLED:
        return

    _ensure_initialized()

    try:
        if _engram_read_counter:
            _engram_read_counter.add(1)
    except Exception as e:
        logger.debug(f"OTel engram read counter failed: {e}")


# ── Public API: Workflow Cost ────────────────────────────────

def record_workflow_cost(
    facade: str,
    action: str,
    cost_units: float,
    tier: int = 1,
) -> None:
    """Record workflow cost in the OTel histogram."""
    if not _OTEL_ENABLED:
        return

    _ensure_initialized()

    try:
        if _workflow_cost_histogram:
            _workflow_cost_histogram.record(
                cost_units,
                attributes={
                    "nucleus.facade": facade,
                    "nucleus.action": action,
                    "nucleus.tier": tier,
                },
            )
    except Exception as e:
        logger.debug(f"OTel workflow cost failed: {e}")


# ── Testing Utilities ────────────────────────────────────────

def reset_otel_state():
    """Reset OTel state for testing. NOT for production use."""
    global _initialized, _tracer, _meter
    global _engram_write_counter, _engram_read_counter
    global _dispatch_duration_histogram, _workflow_cost_histogram

    with _init_lock:
        _initialized = False
        _tracer = None
        _meter = None
        _engram_write_counter = None
        _engram_read_counter = None
        _dispatch_duration_histogram = None
        _workflow_cost_histogram = None
