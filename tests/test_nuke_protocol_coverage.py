"""Comprehensive coverage tests for runtime/nuke_protocol.py.

Tests NukePacker.pack and NukeLoader.load with a real Ed25519
round-trip (cryptography is available), plus all error paths:
missing tool file, missing manifest/signature in archive, invalid
manifest, signature verification failure, and re-install over an
existing agent directory. No real network.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.identity.keygen import KeyManager
from mcp_server_nucleus.runtime.identity.manifest import AgentManifest, AgentIdentity, Capability, CapabilityScope, LifecyclePolicy
from mcp_server_nucleus.runtime.nuke_protocol import NukeLoader, NukePacker


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
def _make_manifest() -> AgentManifest:
    return AgentManifest(
        manifest_version="1.0.0",
        agent=AgentIdentity(
            id="nucleus.test.ops",
            name="TestOps",
            version="1.0.0",
            description="A test agent",
            author="tester",
            license="MIT",
        ),
        capabilities=[
            Capability(scope=CapabilityScope.FILESYSTEM, reason="read tools", paths=["/tmp"], mode="read"),
        ],
        lifecycle=LifecyclePolicy(persistence="session", cleanup="strict"),
    )


@pytest.fixture
def keypair():
    km = KeyManager()
    return km.generate_keypair()


@pytest.fixture
def packer(tmp_path):
    return NukePacker(tmp_path / "staging")


@pytest.fixture
def loader(tmp_path):
    return NukeLoader(tmp_path / "install")


# ---------------------------------------------------------------------------
# NukePacker
# ---------------------------------------------------------------------------
class TestNukePackerInit:
    def test_creates_staging_root(self, tmp_path):
        staging = tmp_path / "staging"
        p = NukePacker(staging)
        assert staging.exists()
        # Check by class name rather than isinstance, since sys.modules
        # pollution from test_stripe_billing/test_license_elt can replace
        # the keygen module with a different class object
        assert type(p.key_manager).__name__ == "KeyManager"


class TestNukePackerPack:
    def test_pack_success(self, tmp_path, packer, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("def run(): pass\n")
        out = tmp_path / "agent.nuke"

        result = packer.pack(manifest, [tool], keypair.private_key_pem, out)

        assert result == out
        assert out.exists()
        # Verify archive contents
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "signature.sig" in names
            assert "tools/tool.py" in names
            # manifest is valid JSON with our agent id
            data = json.loads(zf.read("manifest.json"))
            assert data["agent"]["id"] == "nucleus.test.ops"

    def test_pack_multiple_tools(self, tmp_path, packer, keypair):
        manifest = _make_manifest()
        t1 = tmp_path / "a.py"
        t1.write_text("a")
        t2 = tmp_path / "b.py"
        t2.write_text("b")
        out = tmp_path / "agent.nuke"
        packer.pack(manifest, [t1, t2], keypair.private_key_pem, out)
        with zipfile.ZipFile(out) as zf:
            assert "tools/a.py" in zf.namelist()
            assert "tools/b.py" in zf.namelist()

    def test_pack_no_tools(self, tmp_path, packer, keypair):
        manifest = _make_manifest()
        out = tmp_path / "agent.nuke"
        packer.pack(manifest, [], keypair.private_key_pem, out)
        with zipfile.ZipFile(out) as zf:
            assert "manifest.json" in zf.namelist()
            assert "signature.sig" in zf.namelist()
            # tools dir exists but may be empty (no tool files in archive)
            assert not any(n.startswith("tools/") and n.endswith(".py") for n in zf.namelist())

    def test_pack_missing_tool_raises(self, tmp_path, packer, keypair):
        manifest = _make_manifest()
        out = tmp_path / "agent.nuke"
        with pytest.raises(FileNotFoundError, match="Tool not found"):
            packer.pack(manifest, [tmp_path / "nope.py"], keypair.private_key_pem, out)


# ---------------------------------------------------------------------------
# NukeLoader
# ---------------------------------------------------------------------------
class TestNukeLoaderInit:
    def test_creates_install_root(self, tmp_path):
        install = tmp_path / "install"
        l = NukeLoader(install)
        assert install.exists()
        assert (install / "tools" / "installed").exists()
        # Check by class name rather than isinstance (see TestNukePackerInit)
        assert type(l.key_manager).__name__ == "KeyManager"


class TestNukeLoaderLoad:
    def test_load_success_and_installs_tools(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("def run(): pass\n")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)

        trusted = {keypair.key_id: keypair.public_key_pem}
        result = loader.load(nuke, trusted)

        assert isinstance(result, AgentManifest)
        assert result.agent.id == "nucleus.test.ops"
        # tool installed
        installed = loader.installed_tools_dir / "nucleus.test.ops" / "tool.py"
        assert installed.exists()
        assert installed.read_text() == "def run(): pass\n"

    def test_load_missing_manifest_raises(self, tmp_path, loader):
        nuke = tmp_path / "bad.nuke"
        with zipfile.ZipFile(nuke, "w") as zf:
            zf.writestr("tools/x.py", "x")
        with pytest.raises(ValueError, match="Missing manifest or signature"):
            loader.load(nuke, {})

    def test_load_missing_signature_raises(self, tmp_path, loader):
        nuke = tmp_path / "bad.nuke"
        with zipfile.ZipFile(nuke, "w") as zf:
            zf.writestr("manifest.json", "{}")
        with pytest.raises(ValueError, match="Missing manifest or signature"):
            loader.load(nuke, {})

    def test_load_invalid_manifest_raises(self, tmp_path, loader):
        nuke = tmp_path / "bad.nuke"
        with zipfile.ZipFile(nuke, "w") as zf:
            zf.writestr("manifest.json", "not-json")
            zf.writestr("signature.sig", "00")
        with pytest.raises(ValueError, match="Invalid Manifest"):
            loader.load(nuke, {})

    def test_load_manifest_validation_failure(self, tmp_path, loader):
        nuke = tmp_path / "bad.nuke"
        # manifest dict missing required agent fields
        with zipfile.ZipFile(nuke, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"manifest_version": "1.0.0"}))
            zf.writestr("signature.sig", "00")
        with pytest.raises(ValueError, match="Invalid Manifest"):
            loader.load(nuke, {})

    def test_load_signature_verification_fails(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("x")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)
        # Use an unrelated public key
        other = KeyManager().generate_keypair()
        trusted = {"wrong-key": other.public_key_pem}
        with pytest.raises(PermissionError, match="SIGNATURE VERIFICATION FAILED"):
            loader.load(nuke, trusted)

    def test_load_no_trusted_keys_fails(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("x")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)
        with pytest.raises(PermissionError, match="SIGNATURE VERIFICATION FAILED"):
            loader.load(nuke, {})

    def test_load_verifies_with_one_of_many_keys(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("x")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)
        other = KeyManager().generate_keypair()
        trusted = {"other": other.public_key_pem, "real": keypair.public_key_pem}
        result = loader.load(nuke, trusted)
        assert result.agent.id == "nucleus.test.ops"

    def test_load_reinstall_overwrites_existing(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("v1")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)
        trusted = {keypair.key_id: keypair.public_key_pem}

        # First install
        loader.load(nuke, trusted)
        agent_dir = loader.installed_tools_dir / "nucleus.test.ops"
        assert (agent_dir / "tool.py").read_text() == "v1"

        # Add a stray file to ensure rmtree happened
        (agent_dir / "stray.py").write_text("stray")

        # Re-pack with different content
        tool.write_text("v2")
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)
        loader.load(nuke, trusted)
        assert (agent_dir / "tool.py").read_text() == "v2"
        assert not (agent_dir / "stray.py").exists()

    def test_load_installs_multiple_tools(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        t1 = tmp_path / "a.py"
        t1.write_text("a")
        t2 = tmp_path / "b.py"
        t2.write_text("b")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [t1, t2], keypair.private_key_pem, nuke)
        trusted = {keypair.key_id: keypair.public_key_pem}
        loader.load(nuke, trusted)
        agent_dir = loader.installed_tools_dir / "nucleus.test.ops"
        assert (agent_dir / "a.py").exists()
        assert (agent_dir / "b.py").exists()

    def test_load_ignores_non_py_files_in_tools(self, tmp_path, packer, loader, keypair):
        manifest = _make_manifest()
        tool = tmp_path / "tool.py"
        tool.write_text("x")
        nuke = tmp_path / "agent.nuke"
        packer.pack(manifest, [tool], keypair.private_key_pem, nuke)
        # Append a non-.py file into the archive manually
        with zipfile.ZipFile(nuke, "a") as zf:
            zf.writestr("tools/README.md", "docs")
        trusted = {keypair.key_id: keypair.public_key_pem}
        loader.load(nuke, trusted)
        agent_dir = loader.installed_tools_dir / "nucleus.test.ops"
        assert (agent_dir / "tool.py").exists()
        assert not (agent_dir / "README.md").exists()
