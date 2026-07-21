"""nucleus-relay-sdk — minimal Python SDK for the relay envelope protocol.

Implements the envelope format defined in ``docs/spec/relay_envelope_spec.md``
§2 and the three core operations (post / read / ack) from spec §3.

Install (separate from ``nucleus-mcp``)::

    pip install nucleus-relay-sdk

Usage::

    from nucleus_relay_sdk import RelayClient

    client = RelayClient(sender="my_agent")
    client.post(to="claude_code_main", subject="[DONE] task", body="shipped")
    msgs = client.read(bucket="claude_code_main")
    client.ack(msgs[0]["id"])
"""

from .client import RelayClient
from .envelope import (
    EnvelopeError,
    build_envelope,
    validate_envelope,
    mint_message_id,
    REQUIRED_FIELDS,
    VALID_PRIORITIES,
)

__version__ = "0.1.0"

__all__ = [
    "RelayClient",
    "EnvelopeError",
    "build_envelope",
    "validate_envelope",
    "mint_message_id",
    "REQUIRED_FIELDS",
    "VALID_PRIORITIES",
    "__version__",
]
