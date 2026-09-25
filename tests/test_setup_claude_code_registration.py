"""Tests for Claude Code `.claude.json` MCP registration.

Covers `_patch_claude_code_config` (reached via `_patch_mcp_config` when the
config path basename is `.claude.json`) — the hardened patcher that
atomically injects the `nucleus` entry into the `mcpServers` block.
"""
import json

from mcp_server_nucleus.cli import _patch_mcp_config


class TestClaudeCodeRegistration:
    def test_unrelated_keys_survive_and_nucleus_patched_in(self, tmp_path, capsys):
        """A realistic `.claude.json` carrying an unrelated MCP server and
        unrelated top-level keys is patched in-place: nucleus lands in
        `mcpServers`, every pre-existing key survives unchanged, and the
        success message is emitted."""
        # A realistic ~/.claude.json: top-level Claude Code settings plus an
        # unrelated MCP server already registered.
        original = {
            "numStartups": 42,
            "theme": "dark",
            "hasCompletedOnboarding": True,
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                },
            },
            "projectOnboardingSeenCount": 3,
        }
        cfg_path = tmp_path / ".claude.json"
        cfg_path.write_text(json.dumps(original, indent=2), encoding="utf-8")

        nucleus_config = {
            "command": "nucleus-mcp",
            "env": {"NUCLEUS_BRAIN_PATH": str(tmp_path)},
        }

        result = _patch_mcp_config(cfg_path, "Claude Code", nucleus_config)

        # Success reported honestly.
        assert result is True
        captured = capsys.readouterr()
        assert "Auto-configured" in captured.out
        assert "nucleus" in captured.out

        # Parsed-JSON compare — not a raw-string substring check.
        patched = json.loads(cfg_path.read_text(encoding="utf-8"))

        # nucleus was injected.
        assert "nucleus" in patched["mcpServers"]
        assert patched["mcpServers"]["nucleus"] == nucleus_config

        # The unrelated server survives intact.
        assert patched["mcpServers"]["filesystem"] == original["mcpServers"]["filesystem"]

        # Every unrelated top-level key survives with its original value.
        for key, value in original.items():
            if key == "mcpServers":
                continue
            assert key in patched, f"top-level key '{key}' was dropped"
            assert patched[key] == value, f"top-level key '{key}' value changed"

    def test_no_claude_json_no_file_created_no_success(self, tmp_path, capsys):
        """When `.claude.json` does not exist, the patcher refuses to invent
        one: it returns False, creates no file, and emits no success message
        for Claude Code."""
        cfg_path = tmp_path / ".claude.json"
        assert not cfg_path.exists()

        nucleus_config = {
            "command": "nucleus-mcp",
            "env": {"NUCLEUS_BRAIN_PATH": str(tmp_path)},
        }

        result = _patch_mcp_config(cfg_path, "Claude Code", nucleus_config)

        # Refused — no success claimed.
        assert result is False

        # No file was invented.
        assert not cfg_path.exists()

        # No success message for Claude Code.
        captured = capsys.readouterr()
        assert "Auto-configured" not in captured.out
        assert "nucleus" not in captured.out.lower() or "not found" in captured.out.lower()

    def test_existing_nucleus_entry_no_force_preserved_already_registered(self, tmp_path, capsys):
        """An existing `nucleus` entry is preserved (not overwritten) when
        `force` is not passed, and the already-registered message is emitted
        instead of the Auto-configured success message."""
        existing_nucleus_config = {
            "command": "/old/path/nucleus-mcp",
            "env": {"NUCLEUS_BRAIN_PATH": "/old/brain"},
        }
        original = {
            "mcpServers": {
                "nucleus": existing_nucleus_config,
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                },
            },
        }
        cfg_path = tmp_path / ".claude.json"
        cfg_path.write_text(json.dumps(original, indent=2), encoding="utf-8")
        pre_bytes = cfg_path.read_bytes()

        new_nucleus_config = {
            "command": "nucleus-mcp",
            "env": {"NUCLEUS_BRAIN_PATH": str(tmp_path)},
        }

        result = _patch_mcp_config(cfg_path, "Claude Code", new_nucleus_config)

        # Already-registered is still a success (rc True), but no write happened.
        assert result is True

        # Entry preserved — bytes unchanged, parsed entry is the old one.
        assert cfg_path.read_bytes() == pre_bytes
        patched = json.loads(cfg_path.read_text(encoding="utf-8"))
        assert patched["mcpServers"]["nucleus"] == existing_nucleus_config

        # Sibling survives too.
        assert patched["mcpServers"]["filesystem"] == original["mcpServers"]["filesystem"]

        # Already-registered message emitted; no Auto-configured success claim.
        captured = capsys.readouterr()
        assert "already configured" in captured.out
        assert "--force" in captured.out
        assert "Auto-configured" not in captured.out

    def test_malformed_claude_json_left_byte_identical_error_emitted(self, tmp_path, capsys):
        """A `.claude.json` containing malformed (unparseable) JSON is left
        byte-identical on disk: the patcher reads the raw bytes, detects the
        parse failure, writes the original bytes back unchanged, emits a
        malformed-JSON warning, and returns False. No truncation, no blanking,
        no partial overwrite, and no success message is claimed."""
        # Malformed JSON: valid prefix, then garbage that breaks parsing.
        malformed = b'{\n  "numStartups": 42,\n  "mcpServers": { not valid json ][,\n'
        cfg_path = tmp_path / ".claude.json"
        cfg_path.write_bytes(malformed)
        pre_bytes = cfg_path.read_bytes()
        assert pre_bytes == malformed

        nucleus_config = {
            "command": "nucleus-mcp",
            "env": {"NUCLEUS_BRAIN_PATH": str(tmp_path)},
        }

        result = _patch_mcp_config(cfg_path, "Claude Code", nucleus_config)

        # Refused — no success claimed.
        assert result is False

        # Byte-identity: the file is unchanged down to the last byte.
        # This is the core guarantee — no truncation, no blanking, no partial
        # overwrite, no re-serialization that could drop the malformed tail.
        post_bytes = cfg_path.read_bytes()
        assert post_bytes == pre_bytes, (
            "malformed .claude.json was modified on disk — byte-identity violated"
        )

        # Error message emitted naming the file and the malformed-JSON cause.
        captured = capsys.readouterr()
        assert "malformed JSON" in captured.out
        assert str(cfg_path) in captured.out
        assert "left unchanged" in captured.out

        # No success message — nothing was auto-configured.
        assert "Auto-configured" not in captured.out
        assert "already configured" not in captured.out
