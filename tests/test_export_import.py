"""Tests for nucleus export/import CLI — the sovereignty guarantee.

Covers:
  - Export creates a valid .tar.gz with manifest.json
  - Manifest schema_version + file list + SHA-256 integrity
  - Secrets redaction by default (secrets/ dir + secret-bearing config)
  - --include-secrets includes secrets
  - relay/ excluded by default, included with --include-relay
  - Round-trip: export → import restores files correctly
  - Import merge mode (non-destructive, suffix-collide)
  - Import replace mode (destructive, requires --force)
  - Import dry-run (no writes)
  - Verify mode (SHA-256 integrity check)
  - Tenant-aware export (tenant_id in manifest)
  - Invalid archive rejection (missing manifest, bad schema)
"""
import json
import os
import tarfile
import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.export_import import (
    export_brain,
    import_brain,
    verify_export,
    EXPORT_SCHEMA_VERSION,
    _sha256_file,
    _resolve_tenant_id_from_brain_path,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_brain(tmp_path):
    """Create a sample brain directory with representative contents."""
    brain = tmp_path / "brain"
    brain.mkdir()

    # Standard subdirs
    for d in ["engrams", "ledger", "sessions", "config", "secrets", "relay", "logs"]:
        (brain / d).mkdir(exist_ok=True)

    # Engrams (user memory — should be exported)
    (brain / "engrams" / "history.jsonl").write_text(
        '{"ts":"2026-01-01T00:00:00Z","key":"test","value":"hello"}\n'
    )

    # Ledger
    (brain / "ledger" / "activity_summary.json").write_text('{"events": 42}')

    # Config — secret-bearing (should be redacted by default)
    (brain / "config" / "nucleus.yaml").write_text(
        "api_key: sk-secret-12345\nprovider: gemini\n"
    )

    # Secrets dir (should NEVER be exported without --include-secrets)
    (brain / "secrets" / "tokens.json").write_text(
        '{"telegram": "bot:supersecret"}'
    )

    # Relay (should be excluded by default)
    (brain / "relay" / "claude_code_peer").mkdir()
    (brain / "relay" / "claude_code_peer" / "msg1.json").write_text('{"from":"peer"}')

    # Logs (should ALWAYS be excluded)
    (brain / "logs" / "run.log").write_text("some log output\n")

    # A top-level markdown file
    (brain / "README.md").write_text("# My Brain\n\nUser notes.")

    return brain


@pytest.fixture
def tenant_brain(tmp_path, monkeypatch):
    """Create a tenant brain under ~/.nucleus/tenants/<id>/.brain structure."""
    brain_root = tmp_path / "tenants"
    tenant_id = "abc123def456"
    brain = brain_root / tenant_id / ".brain"
    brain.mkdir(parents=True)

    for d in ["engrams", "ledger", "config"]:
        (brain / d).mkdir(exist_ok=True)

    (brain / "engrams" / "memory.jsonl").write_text('{"key":"tenant_data"}\n')
    (brain / "ledger" / "state.json").write_text('{"tenant": "abc123"}')

    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(brain_root))
    return brain, tenant_id


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_creates_valid_archive(self, sample_brain, tmp_path):
        """Export produces a .tar.gz with manifest.json + brain/ contents."""
        output = tmp_path / "export.tar.gz"
        result = export_brain(sample_brain, output)

        assert result.exists()
        assert result.suffix == ".gz"

        with tarfile.open(result, "r:gz") as tar:
            names = tar.getnames()
            assert "manifest.json" in names
            assert "brain/engrams/history.jsonl" in names
            assert "brain/ledger/activity_summary.json" in names
            assert "brain/README.md" in names

    def test_export_manifest_structure(self, sample_brain, tmp_path):
        """Manifest has required fields + correct schema version."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output)

        with tarfile.open(output, "r:gz") as tar:
            manifest = json.loads(tar.extractfile("manifest.json").read())

        assert manifest["schema_version"] == EXPORT_SCHEMA_VERSION
        assert "exported_at" in manifest
        assert "file_count" in manifest
        assert "files" in manifest
        assert isinstance(manifest["files"], list)
        assert manifest["file_count"] == len(manifest["files"])

    def test_export_sha256_integrity(self, sample_brain, tmp_path):
        """Every file in manifest has a correct SHA-256."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output)

        with tarfile.open(output, "r:gz") as tar:
            manifest = json.loads(tar.extractfile("manifest.json").read())

        for f in manifest["files"]:
            if f.get("redacted"):
                continue
            src = sample_brain / f["relpath"]
            assert _sha256_file(src) == f["sha256"]

    def test_export_excludes_secrets_by_default(self, sample_brain, tmp_path):
        """secrets/ directory is excluded from export by default."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output)

        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()

        # secrets/ dir should NOT appear
        assert not any(n.startswith("brain/secrets/") for n in names)

    def test_export_includes_secrets_with_flag(self, sample_brain, tmp_path):
        """--include-secrets includes secrets/ directory."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output, include_secrets=True)

        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()

        assert "brain/secrets/tokens.json" in names

    def test_export_redacts_secret_bearing_config(self, sample_brain, tmp_path):
        """config/nucleus.yaml is redacted by default (placeholder, not real content)."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output)

        with tarfile.open(output, "r:gz") as tar:
            manifest = json.loads(tar.extractfile("manifest.json").read())
            config_member = tar.extractfile("brain/config/nucleus.yaml")
            config_content = config_member.read().decode("utf-8")

        # Should be a redaction placeholder, not the real api_key
        assert "sk-secret-12345" not in config_content
        assert "REDACTED" in config_content

        # Manifest should mark it as redacted
        config_entry = next(
            f for f in manifest["files"] if f["relpath"] == "config/nucleus.yaml"
        )
        assert config_entry["redacted"] is True

    def test_export_includes_secret_config_with_flag(self, sample_brain, tmp_path):
        """--include-secrets includes real config/nucleus.yaml content."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output, include_secrets=True)

        with tarfile.open(output, "r:gz") as tar:
            config_content = tar.extractfile("brain/config/nucleus.yaml").read().decode()

        assert "sk-secret-12345" in config_content

    def test_export_excludes_relay_by_default(self, sample_brain, tmp_path):
        """relay/ directory is excluded by default."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output)

        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()

        assert not any(n.startswith("brain/relay/") for n in names)

    def test_export_includes_relay_with_flag(self, sample_brain, tmp_path):
        """--include-relay includes relay/ directory."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output, include_relay=True)

        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()

        assert any(n.startswith("brain/relay/") for n in names)

    def test_export_always_excludes_logs(self, sample_brain, tmp_path):
        """logs/ is always excluded even with all flags."""
        output = tmp_path / "export.tar.gz"
        export_brain(sample_brain, output, include_secrets=True, include_relay=True)

        with tarfile.open(output, "r:gz") as tar:
            names = tar.getnames()

        assert not any(n.startswith("brain/logs/") for n in names)

    def test_export_tenant_id_in_manifest(self, tenant_brain, tmp_path):
        """Tenant brain export includes tenant_id in manifest."""
        brain, tenant_id = tenant_brain
        output = tmp_path / "export.tar.gz"
        export_brain(brain, output)

        with tarfile.open(output, "r:gz") as tar:
            manifest = json.loads(tar.extractfile("manifest.json").read())

        assert manifest["tenant_id"] == tenant_id

    def test_export_nonexistent_brain_raises(self, tmp_path):
        """Exporting a nonexistent brain raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            export_brain(tmp_path / "nonexistent", tmp_path / "out.tar.gz")


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------

class TestImport:
    def test_round_trip_export_import(self, sample_brain, tmp_path):
        """Export → import restores all non-redacted files correctly."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        target = tmp_path / "imported_brain"
        result = import_brain(archive, target)

        assert result["imported"] > 0
        assert len(result["errors"]) == 0

        # Verify content restored
        assert (target / "engrams" / "history.jsonl").exists()
        assert (target / "ledger" / "activity_summary.json").exists()
        assert (target / "README.md").exists()

        # Verify content matches
        original = (sample_brain / "engrams" / "history.jsonl").read_text()
        restored = (target / "engrams" / "history.jsonl").read_text()
        assert original == restored

    def test_import_skips_redacted_files(self, sample_brain, tmp_path):
        """Redacted config files are skipped during import (placeholder, not real data)."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        target = tmp_path / "imported_brain"
        result = import_brain(archive, target)

        # config/nucleus.yaml was redacted → should be skipped
        assert not (target / "config" / "nucleus.yaml").exists()
        assert result["skipped"] >= 1

    def test_import_merge_non_destructive(self, sample_brain, tmp_path):
        """Merge mode doesn't overwrite existing files — suffix-collides instead."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        target = tmp_path / "imported_brain"
        target.mkdir(parents=True)
        (target / "engrams").mkdir()
        (target / "engrams" / "history.jsonl").write_text("EXISTING CONTENT")

        result = import_brain(archive, target, merge=True)

        # Original file preserved
        assert (target / "engrams" / "history.jsonl").read_text() == "EXISTING CONTENT"
        # Imported file got suffixed (pattern: history.imported-<ts>.jsonl)
        imported_files = list((target / "engrams").glob("history.imported-*.jsonl"))
        assert len(imported_files) == 1

    def test_import_replace_overwrites(self, sample_brain, tmp_path):
        """Replace mode overwrites existing files."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        target = tmp_path / "imported_brain"
        target.mkdir(parents=True)
        (target / "engrams").mkdir()
        (target / "engrams" / "history.jsonl").write_text("OLD CONTENT")

        result = import_brain(archive, target, merge=False, replace=True)

        assert (target / "engrams" / "history.jsonl").read_text() != "OLD CONTENT"
        assert result["overwritten"] >= 1

    def test_import_replace_requires_confirmation(self, sample_brain, tmp_path):
        """merge + replace are mutually exclusive."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        target = tmp_path / "imported_brain"
        with pytest.raises(ValueError, match="mutually exclusive"):
            import_brain(archive, target, merge=True, replace=True)

    def test_import_dry_run_no_writes(self, sample_brain, tmp_path):
        """Dry run validates without writing anything."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        target = tmp_path / "imported_brain"
        result = import_brain(archive, target, dry_run=True)

        assert result["dry_run"] is True
        assert result["imported"] == 0
        assert not target.exists() or not any(target.iterdir())

    def test_import_invalid_archive_no_manifest(self, tmp_path):
        """Archive without manifest.json is rejected."""
        bad_archive = tmp_path / "bad.tar.gz"
        with tarfile.open(bad_archive, "w:gz") as tar:
            info = tarfile.TarInfo(name="random.txt")
            info.size = 5
            from io import BytesIO
            tar.addfile(info, BytesIO(b"hello"))

        target = tmp_path / "brain"
        with pytest.raises(ValueError, match="manifest"):
            import_brain(bad_archive, target)

    def test_import_invalid_archive_bad_schema(self, sample_brain, tmp_path):
        """Archive with future schema version is rejected."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        # Tamper with manifest to have a future schema version
        with tempfile.TemporaryDirectory() as td:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(td)

            manifest_path = Path(td) / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["schema_version"] = EXPORT_SCHEMA_VERSION + 999
            manifest_path.write_text(json.dumps(manifest))

            tampered = tmp_path / "tampered.tar.gz"
            with tarfile.open(tampered, "w:gz") as tar:
                # Add files at root level (not nested under ./)
                for fpath in Path(td).iterdir():
                    tar.add(str(fpath), arcname=fpath.name)

        target = tmp_path / "brain"
        with pytest.raises(ValueError, match="newer"):
            import_brain(tampered, target)


# ---------------------------------------------------------------------------
# Verify tests
# ---------------------------------------------------------------------------

class TestVerify:
    def test_verify_valid_archive(self, sample_brain, tmp_path):
        """Verify returns valid=True for a clean export."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        result = verify_export(archive)

        assert result["valid"] is True
        assert result["verified"] > 0
        assert len(result["mismatches"]) == 0
        assert len(result["missing"]) == 0

    def test_verify_detects_tampering(self, sample_brain, tmp_path):
        """Verify detects SHA-256 mismatch after tampering."""
        archive = tmp_path / "export.tar.gz"
        export_brain(sample_brain, archive)

        # Tamper: replace a file's content in the archive
        with tempfile.TemporaryDirectory() as td:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(td)

            # Tamper with a brain file
            target_file = Path(td) / "brain" / "engrams" / "history.jsonl"
            target_file.write_text("TAMPERED CONTENT")

            tampered = tmp_path / "tampered.tar.gz"
            with tarfile.open(tampered, "w:gz") as tar:
                # Re-add at root level to preserve archive structure
                for fpath in Path(td).iterdir():
                    tar.add(str(fpath), arcname=fpath.name)

            result = verify_export(tampered)

        assert result["valid"] is False
        assert len(result["mismatches"]) >= 1


# ---------------------------------------------------------------------------
# Tenant resolution helper tests
# ---------------------------------------------------------------------------

class TestTenantResolution:
    def test_resolve_tenant_id_from_brain_path(self, tenant_brain):
        """Tenant ID is correctly resolved from brain path structure."""
        brain, expected_id = tenant_brain
        result = _resolve_tenant_id_from_brain_path(brain)
        assert result == expected_id

    def test_resolve_tenant_id_standalone_brain(self, tmp_path):
        """Standalone .brain (not under tenants/) returns None."""
        brain = tmp_path / ".brain"
        brain.mkdir()
        assert _resolve_tenant_id_from_brain_path(brain) is None

    def test_resolve_tenant_id_non_brain_path(self, tmp_path):
        """Non-.brain path returns None."""
        assert _resolve_tenant_id_from_brain_path(tmp_path / "data") is None


# ---------------------------------------------------------------------------
# Tenant isolation test
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    def test_export_import_tenant_isolation(self, tmp_path, monkeypatch):
        """Two tenants export + import without cross-contamination."""
        brain_root = tmp_path / "tenants"
        tenant_a = "tenant_a_001"
        tenant_b = "tenant_b_002"

        brain_a = brain_root / tenant_a / ".brain"
        brain_b = brain_root / tenant_b / ".brain"
        brain_a.mkdir(parents=True)
        brain_b.mkdir(parents=True)

        (brain_a / "engrams").mkdir()
        (brain_b / "engrams").mkdir()

        (brain_a / "engrams" / "memory.jsonl").write_text('{"tenant": "A"}')
        (brain_b / "engrams" / "memory.jsonl").write_text('{"tenant": "B"}')

        monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(brain_root))

        # Export both
        archive_a = tmp_path / "a.tar.gz"
        archive_b = tmp_path / "b.tar.gz"
        export_brain(brain_a, archive_a)
        export_brain(brain_b, archive_b)

        # Verify manifests have correct tenant_ids
        with tarfile.open(archive_a, "r:gz") as tar:
            manifest_a = json.loads(tar.extractfile("manifest.json").read())
        with tarfile.open(archive_b, "r:gz") as tar:
            manifest_b = json.loads(tar.extractfile("manifest.json").read())

        assert manifest_a["tenant_id"] == tenant_a
        assert manifest_b["tenant_id"] == tenant_b
        assert manifest_a["tenant_id"] != manifest_b["tenant_id"]

        # Import A into a fresh target — should only contain A's data
        target = tmp_path / "restored_a"
        import_brain(archive_a, target)

        restored = (target / "engrams" / "memory.jsonl").read_text()
        assert '"tenant": "A"' in restored
        assert '"tenant": "B"' not in restored
