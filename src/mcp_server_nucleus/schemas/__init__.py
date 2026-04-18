"""Shipped JSON Schema artifacts for Nucleus public contracts.

Consumers of the facade tools can pin to these schemas and
regression-test responses against them. Any change to a schema file
constitutes a public contract change and requires a minor-version bump
at minimum.
"""

from pathlib import Path

SCHEMAS_DIR = Path(__file__).parent


def load_schema(name: str) -> dict:
    """Load a schema by filename stem (e.g. 'envelope' -> envelope.schema.json)."""
    import json

    path = SCHEMAS_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    with path.open("r") as f:
        return json.load(f)
