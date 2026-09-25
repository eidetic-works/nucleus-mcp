"""Coverage tests for runtime/publisher.py."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.publisher import Publisher
from mcp_server_nucleus.runtime.identity.keygen import KeyPair


def _valid_manifest():
    return {
        "agent": {
            "id": "nucleus.core.ops",
            "name": "Ops",
            "version": "1.0.0",
            "description": "d",
            "author": "me",
            "license": "MIT",
        },
        "capabilities": [],
    }


def test_publisher_init(tmp_path):
    km = MagicMock()
    pub = Publisher(tmp_path, key_manager=km)
    assert pub.brain_path == tmp_path
    assert pub.key_manager is km
    assert pub.packer is not None
    assert pub.validator is not None


def test_publish_missing_manifest_raises(tmp_path):
    km = MagicMock()
    pub = Publisher(tmp_path, key_manager=km)
    src = tmp_path / "src"
    src.mkdir()
    with pytest.raises(FileNotFoundError):
        pub.publish(src, tmp_path / "out", "key1")


def test_publish_invalid_manifest_raises(tmp_path):
    km = MagicMock()
    pub = Publisher(tmp_path, key_manager=km)
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps({"agent": {"id": "bad"}}))
    with pytest.raises((ValueError, Exception)):
        pub.publish(src, tmp_path / "out", "key1")


def test_publish_key_not_found_raises(tmp_path):
    km = MagicMock()
    km.get_key_pair.return_value = None
    pub = Publisher(tmp_path, key_manager=km)
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps(_valid_manifest()))
    with pytest.raises(ValueError, match="not found"):
        pub.publish(src, tmp_path / "out", "missingkey")


def test_publish_success(tmp_path):
    km = MagicMock()
    kp = KeyPair(key_id="k1", private_key_pem="priv", public_key_pem="pub")
    km.get_key_pair.return_value = kp
    pub = Publisher(tmp_path, key_manager=km)
    pub.packer.pack = MagicMock(return_value=tmp_path / "out" / "x.nuke")
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps(_valid_manifest()))
    (src / "tool.py").write_text("# tool")
    out = tmp_path / "out"
    result = pub.publish(src, out, "k1")
    assert result == tmp_path / "out" / "nucleus.core.ops-1.0.0.nuke"
    pub.packer.pack.assert_called_once()
    # verify output dir created
    assert out.exists()


def test_publish_packer_raises_propagates(tmp_path):
    km = MagicMock()
    kp = KeyPair(key_id="k1", private_key_pem="priv", public_key_pem="pub")
    km.get_key_pair.return_value = kp
    pub = Publisher(tmp_path, key_manager=km)
    pub.packer.pack = MagicMock(side_effect=RuntimeError("pack fail"))
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps(_valid_manifest()))
    with pytest.raises(RuntimeError, match="pack fail"):
        pub.publish(src, tmp_path / "out", "k1")


def test_publish_private_flag_accepted(tmp_path):
    km = MagicMock()
    kp = KeyPair(key_id="k1", private_key_pem="priv", public_key_pem="pub")
    km.get_key_pair.return_value = kp
    pub = Publisher(tmp_path, key_manager=km)
    pub.packer.pack = MagicMock(return_value=tmp_path / "out" / "x.nuke")
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps(_valid_manifest()))
    result = pub.publish(src, tmp_path / "out", "k1", private=True)
    assert result is not None
