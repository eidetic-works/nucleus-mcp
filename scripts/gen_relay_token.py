#!/usr/bin/env python3
"""Generate a relay webhook token for a sender.

Usage:
    python scripts/gen_relay_token.py <sender>
    python scripts/gen_relay_token.py perplexity claude_code_main windsurf

Prints a JSON line suitable for NUCLEUS_RELAY_TOKEN_MAP in deploy/oci/.env.
"""
from __future__ import annotations

import json
import secrets
import sys


def make_token() -> str:
    return secrets.token_hex(32)


def main(senders: list[str]) -> int:
    if not senders:
        print(__doc__, file=sys.stderr)
        return 2

    mapping = {make_token(): s for s in senders}
    print("# Paste this line into deploy/oci/.env (single line, no whitespace inside JSON):")
    print(f"NUCLEUS_RELAY_TOKEN_MAP={json.dumps(mapping, separators=(',', ':'))}")
    print()
    print("# Per-sender tokens — share each token only with its declared sender:")
    for tok, sender in mapping.items():
        print(f"  {sender:<24} {tok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
