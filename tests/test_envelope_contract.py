"""Contract tests: verify envelope outputs conform to envelope.schema.json.

This is the load-bearing test that lets downstream consumers pin to the
schema artifact. Any drift between `tools/_envelope.py::wrap` output and
the schema at `schemas/envelope.schema.json` fails here.

Uses `jsonschema` if available (optional dep). If not installed, the
tests skip with a clear message — they're gating for release, not a
hard import.
"""

from __future__ import annotations

import json

import pytest

from mcp_server_nucleus import schemas as schemas_pkg
from mcp_server_nucleus.tools import _envelope as env

jsonschema = pytest.importorskip(
    "jsonschema",
    reason="jsonschema not installed; envelope contract tests skipped",
)


@pytest.fixture(autouse=True)
def _envelope_on(monkeypatch):
    """Contract tests always run with envelope ON — they validate wrap output."""
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "on")
    env.set_session_id(None)
    env.set_brain_id(None)
    yield
    env.set_session_id(None)
    env.set_brain_id(None)


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    return schemas_pkg.load_schema("envelope")


@pytest.fixture(scope="module")
def validator(envelope_schema):
    cls = jsonschema.validators.validator_for(envelope_schema)
    cls.check_schema(envelope_schema)
    return cls(envelope_schema)


def test_schema_is_loadable(envelope_schema):
    assert envelope_schema["$id"].endswith("envelope.schema.json")
    assert envelope_schema["type"] == "object"
    assert "schema_version" in envelope_schema["properties"]


def test_success_envelope_validates(validator):
    e = env.wrap({"hello": "world"}, brain_id="nucleus-primary", session_id="sess-1")
    validator.validate(e)


def test_success_envelope_with_warnings_validates(validator):
    e = env.wrap(
        {"x": 1},
        warnings=["action out of domain: advisory only"],
        brain_id="nucleus-primary",
        session_id="sess-1",
    )
    validator.validate(e)


def test_error_envelope_validates(validator):
    e = env.error_envelope(
        "transport_closed",
        recovery_hint="nucleus restart --force",
        last_healthy_at="2026-04-18T12:00:00Z",
        pid=4512,
        inflight_writes=["engram:abc123"],
    )
    # populate brain_id/session_id via wrap path which error_envelope uses
    assert e["ok"] is False
    validator.validate(e)


def test_error_envelope_minimal_validates(validator):
    e = env.error_envelope("handler_error", recovery_hint="check logs")
    validator.validate(e)


def test_envelope_missing_required_field_fails_validation(validator):
    bad = {
        "ok": True,
        "data": {},
        "brain_id": "x",
        "session_id": "y",
        "schema_version": "2",
        # missing warnings + error
    }
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)


def test_envelope_unknown_schema_version_fails(validator):
    bad = env.wrap({"x": 1})
    bad["schema_version"] = "99"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)


def test_envelope_additional_toplevel_property_fails(validator):
    bad = env.wrap({"x": 1})
    bad["injected"] = "no-such-field"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)


def test_error_block_accepts_extra_fields(validator):
    """error block has additionalProperties: true, so extras should pass."""
    e = env.error_envelope(
        "validation_error",
        recovery_hint="fix params",
        field="name",
        got_type="int",
    )
    validator.validate(e)


def test_schema_load_missing_name_raises():
    with pytest.raises(FileNotFoundError):
        schemas_pkg.load_schema("does-not-exist")


def test_schema_json_is_valid_json():
    """Guard: syntax-check the raw JSON file outside the loader."""
    from importlib import resources

    # use files() API for py3.10+
    path = schemas_pkg.SCHEMAS_DIR / "envelope.schema.json"
    with path.open("r") as f:
        data = json.load(f)
    assert data["$id"].endswith("envelope.schema.json")
