"""Tests for runtime.manifest."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
import yaml

from mcp_server_nucleus.runtime import manifest
from mcp_server_nucleus.tools import _envelope


@pytest.fixture
def brain(tmp_path) -> Path:
    root = tmp_path / ".brain"
    root.mkdir()
    return root


@pytest.fixture(autouse=True)
def _reset_envelope():
    _envelope.set_brain_id(None)
    yield
    _envelope.set_brain_id(None)


def test_load_bootstraps_missing(brain):
    result = manifest.load(brain)
    assert result["schema_version"] == 2
    assert "brain_id" in result
    assert manifest.manifest_path(brain).exists()


def test_load_no_auto_create_raises(brain):
    with pytest.raises(FileNotFoundError):
        manifest.load(brain, auto_create=False)


def test_round_trip(brain):
    manifest.save(brain, {"brain_id": "primary", "tracks_projects": ["a/b"]})
    out = manifest.load(brain)
    assert out["brain_id"] == "primary"
    assert out["tracks_projects"] == ["a/b"]


def test_v1_upgrades_on_read(brain):
    manifest.manifest_path(brain).write_text(
        yaml.safe_dump({"brain_id": "legacy", "schema_version": 1})
    )
    out = manifest.load(brain)
    assert out["schema_version"] == 2
    assert out["tracks_projects"] == []


def test_add_project_idempotent(brain):
    manifest.save(brain, {"brain_id": "x"})
    manifest.add_project(brain, "a/b")
    m = manifest.add_project(brain, "a/b")
    assert m["tracks_projects"] == ["a/b"]


def test_remove_project(brain):
    manifest.save(brain, {"brain_id": "x", "tracks_projects": ["a/b", "c/d"]})
    m = manifest.remove_project(brain, "a/b")
    assert m["tracks_projects"] == ["c/d"]


def test_resolve_brain_id_env_first(monkeypatch, brain):
    monkeypatch.setenv("NUCLEUS_BRAIN_ID", "env-brain")
    manifest.save(brain, {"brain_id": "manifest-brain"})
    assert manifest.resolve_brain_id(brain) == "env-brain"


def test_resolve_brain_id_from_manifest(monkeypatch, brain):
    monkeypatch.delenv("NUCLEUS_BRAIN_ID", raising=False)
    manifest.save(brain, {"brain_id": "manifest-brain"})
    assert manifest.resolve_brain_id(brain) == "manifest-brain"


def test_resolve_brain_id_unknown_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("NUCLEUS_BRAIN_ID", raising=False)
    bad = tmp_path / "nonexistent" / "brain"
    assert manifest.resolve_brain_id(bad) in ("unknown", manifest.resolve_brain_id(bad))


def test_load_primes_envelope(monkeypatch, brain):
    monkeypatch.setenv("NUCLEUS_ENVELOPE", "on")
    manifest.save(brain, {"brain_id": "primed-id"})
    manifest.load(brain)
    e = _envelope.wrap({"x": 1})
    assert e["brain_id"] == "primed-id"


def test_atomic_write_no_partial_file_under_race(brain):
    """Multiple writers race — file is never observed partial/corrupt."""
    manifest.save(brain, {"brain_id": "init"})
    stop = threading.Event()
    observed_corrupt = []

    def reader():
        while not stop.is_set():
            try:
                text = manifest.manifest_path(brain).read_text()
                if text:
                    data = yaml.safe_load(text)
                    if not isinstance(data, dict) or "brain_id" not in data:
                        observed_corrupt.append(data)
            except Exception as e:
                observed_corrupt.append(str(e))

    def writer(tag: str, n: int):
        for i in range(n):
            manifest.save(brain, {"brain_id": f"{tag}-{i}", "tracks_projects": [tag]})

    r = threading.Thread(target=reader, daemon=True)
    r.start()
    writers = [threading.Thread(target=writer, args=(f"w{i}", 20)) for i in range(4)]
    for w in writers:
        w.start()
    for w in writers:
        w.join()
    stop.set()
    r.join(timeout=1.0)
    assert observed_corrupt == []


def test_tmp_file_cleaned_after_save(brain):
    manifest.save(brain, {"brain_id": "x"})
    tmp = manifest.manifest_path(brain).with_suffix(".yaml.tmp")
    assert not tmp.exists()


def test_parse_owner_from_git_url():
    m = manifest._parse_owner_from_url
    assert m("git@github.com:eidetic-works/mcp-server-nucleus.git") == "eidetic-works/mcp-server-nucleus"
    assert m("https://github.com/eidetic-works/mcp-server-nucleus.git") == "eidetic-works/mcp-server-nucleus"
    assert m("https://github.com/eidetic-works/mcp-server-nucleus") == "eidetic-works/mcp-server-nucleus"
    assert m("") is None
    assert m("not-a-url") is None


def test_slugify():
    assert manifest._slugify("Hello World") == "hello-world"
    assert manifest._slugify("foo_bar-BAZ") == "foo-bar-baz"
    assert manifest._slugify("a") == "a"
