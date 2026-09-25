"""Coverage tests for runtime/registry.py."""
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.registry import RegistryClient, RegistryEntry


def _entry_dict(id_="a1", name="Agent One", tags=None, description="desc"):
    return {
        "id": id_,
        "name": name,
        "description": description,
        "latest_version": "1.0.0",
        "repo_url": "https://example.com/r",
        "tags": tags or [],
    }


def test_registry_entry_model():
    e = RegistryEntry(**_entry_dict())
    assert e.id == "a1"
    assert e.tags == []


def test_registry_entry_required_fields():
    with pytest.raises(Exception):
        RegistryEntry(id="x")


def test_init_defaults():
    rc = RegistryClient()
    assert rc.registry_url == "https://registry.nucleus.dev/index.json"
    assert rc._cache == []


def test_init_custom_url():
    rc = RegistryClient("https://custom.example/index.json")
    assert rc.registry_url == "https://custom.example/index.json"


def test_fetch_index_success():
    rc = RegistryClient("https://x.example/index.json")
    payload = json.dumps({"agents": [_entry_dict("a1"), _entry_dict("a2", "Agent Two")]}).encode()
    fake_resp = BytesIO(payload)
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda self, *a: None
    with patch("mcp_server_nucleus.runtime.registry.urllib.request.urlopen", return_value=fake_resp):
        entries = rc.fetch_index()
    assert len(entries) == 2
    assert entries[0].id == "a1"
    assert rc._cache == entries


def test_fetch_index_failure_raises():
    rc = RegistryClient("https://x.example/index.json")
    with patch("mcp_server_nucleus.runtime.registry.urllib.request.urlopen", side_effect=Exception("net err")):
        with pytest.raises(Exception, match="net err"):
            rc.fetch_index()


def test_search_with_cache():
    rc = RegistryClient()
    rc._cache = [
        RegistryEntry(**_entry_dict("alpha", "Alpha Agent", tags=["cool"])),
        RegistryEntry(**_entry_dict("beta", "Beta Agent", tags=["hot"])),
    ]
    results = rc.search("alpha")
    assert len(results) == 1
    assert results[0].id == "alpha"


def test_search_by_tag():
    rc = RegistryClient()
    rc._cache = [RegistryEntry(**_entry_dict("a1", "X", tags=["machine-learning"]))]
    results = rc.search("machine")
    assert len(results) == 1


def test_search_by_description():
    rc = RegistryClient()
    rc._cache = [RegistryEntry(**_entry_dict("a1", "X", description="special keyword here"))]
    results = rc.search("keyword")
    assert len(results) == 1


def test_search_no_match():
    rc = RegistryClient()
    rc._cache = [RegistryEntry(**_entry_dict("a1", "X"))]
    results = rc.search("zzz")
    assert results == []


def test_search_auto_fetch_on_empty_cache():
    rc = RegistryClient()
    payload = json.dumps({"agents": [_entry_dict("a1")]}).encode()
    fake_resp = BytesIO(payload)
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda self, *a: None
    with patch("mcp_server_nucleus.runtime.registry.urllib.request.urlopen", return_value=fake_resp):
        results = rc.search("agent")
    assert len(results) == 1


def test_search_auto_fetch_failure_returns_empty():
    rc = RegistryClient()
    with patch("mcp_server_nucleus.runtime.registry.urllib.request.urlopen", side_effect=Exception("net")):
        results = rc.search("anything")
    assert results == []


def test_get_entry_found():
    rc = RegistryClient()
    rc._cache = [RegistryEntry(**_entry_dict("a1")), RegistryEntry(**_entry_dict("a2"))]
    e = rc.get_entry("a2")
    assert e is not None
    assert e.id == "a2"


def test_get_entry_not_found():
    rc = RegistryClient()
    rc._cache = [RegistryEntry(**_entry_dict("a1"))]
    assert rc.get_entry("nope") is None


def test_get_entry_auto_fetch():
    rc = RegistryClient()
    payload = json.dumps({"agents": [_entry_dict("a1")]}).encode()
    fake_resp = BytesIO(payload)
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda self, *a: None
    with patch("mcp_server_nucleus.runtime.registry.urllib.request.urlopen", return_value=fake_resp):
        e = rc.get_entry("a1")
    assert e is not None
    assert e.id == "a1"
