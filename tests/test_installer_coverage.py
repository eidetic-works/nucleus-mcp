"""Coverage tests for runtime/installer.py."""
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.runtime.installer import Installer
from mcp_server_nucleus.runtime.identity.manifest import AgentManifest


def _valid_manifest_obj():
    return AgentManifest(
        agent={
            "id": "nucleus.core.ops",
            "name": "Ops",
            "version": "1.0.0",
            "description": "d",
            "author": "me",
            "license": "MIT",
        },
        capabilities=[],
    )


def test_installer_init(tmp_path):
    inst = Installer(tmp_path)
    assert inst.brain_path == tmp_path
    assert inst.lifecycle is not None
    assert inst.team is not None
    assert inst.loader is not None


def test_install_from_file_success(tmp_path):
    inst = Installer(tmp_path)
    manifest = _valid_manifest_obj()

    inst.team.get_trusted_roots = MagicMock(return_value=["pubkey1"])
    inst.loader.load = MagicMock(return_value=manifest)
    inst.lifecycle.register_agent = MagicMock()

    nuke_path = tmp_path / "agent.nuke"
    result = inst.install_from_file(nuke_path)
    assert result is manifest
    inst.loader.load.assert_called_once()
    inst.lifecycle.register_agent.assert_called_once_with("nucleus.core.ops")


def test_install_from_file_loader_raises(tmp_path):
    inst = Installer(tmp_path)
    inst.team.get_trusted_roots = MagicMock(return_value=[])
    inst.loader.load = MagicMock(side_effect=PermissionError("bad sig"))

    with pytest.raises(PermissionError):
        inst.install_from_file(tmp_path / "x.nuke")


def test_install_from_file_trusted_map_construction(tmp_path):
    inst = Installer(tmp_path)
    manifest = _valid_manifest_obj()
    inst.team.get_trusted_roots = MagicMock(return_value=["k1", "k2"])
    inst.loader.load = MagicMock(return_value=manifest)
    inst.lifecycle.register_agent = MagicMock()

    inst.install_from_file(tmp_path / "x.nuke")
    # verify trusted_map built from list
    call_args = inst.loader.load.call_args
    trusted_map = call_args[0][1]
    assert trusted_map == {"trusted_0": "k1", "trusted_1": "k2"}
