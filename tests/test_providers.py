"""
Tests for the provider registry — Slice #3 config-registry role_map (2026-04-22).

Covers: YAML loading (stdlib path), schema validation, env override, unknown-
prefix fallback, mtime-based cache invalidation, backward-compat with the
legacy `_coerce_legacy_to_tuple` signature, and primitive-gate provider-
neutrality sentinel.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime import providers as provider_reg
from mcp_server_nucleus.runtime.providers import (
    ProviderEntry,
    ProviderRegistry,
    RegistryLoadError,
    _clear_cache_for_tests,
    coerce_to_tuple,
    list_providers,
    load_registry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    """Cache is process-global; reset before & after each test."""
    _clear_cache_for_tests()
    yield
    _clear_cache_for_tests()


@pytest.fixture
def tmp_yaml(tmp_path: Path) -> Path:
    """Writable YAML override path (does not touch the shipped default)."""
    return tmp_path / "providers.yaml"


def _write_yaml(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Shipped-default registry
# ---------------------------------------------------------------------------


class TestShippedDefault:
    """The package ships a providers.yaml that must load cleanly."""

    def test_default_yaml_loads(self):
        reg = load_registry()
        assert reg.schema_version == 1
        assert len(reg.entries) >= 5, "expected at least 5 providers in shipped default"

    def test_default_contains_five_active_providers(self):
        """Slice #3 exit criterion 1: cowork + claude_code_main/peer + gemini + windsurf."""
        reg = load_registry()
        prefixes = {e.prefix for e in reg.entries}
        required = {
            "cowork",
            "claude_code_main",
            "claude_code_peer",
            "gemini",
            "windsurf",
        }
        missing = required - prefixes
        assert not missing, f"shipped providers.yaml missing required prefixes: {missing}"

    def test_default_preserves_legacy_tuple_values(self):
        """Parity with pre-refactor `_PROVIDER_PATTERNS` tuple."""
        reg = load_registry()
        by_prefix = {e.prefix: e for e in reg.entries}

        expected = {
            "claude_code_peer": ("anthropic_claude_code", "secondary"),
            "claude_code_main": ("anthropic_claude_code", "primary"),
            "claude_code":      ("anthropic_claude_code", "primary"),
            "cowork":           ("anthropic_cowork",      "coordinator"),
            "codex":            ("openai_codex",          "worker"),
            "gemini":           ("google_gemini",         "reviewer"),
            "cursor":           ("cursor",                "primary"),
            "windsurf":         ("windsurf",              "primary"),
        }
        for prefix, (prov, role) in expected.items():
            assert prefix in by_prefix, f"missing prefix {prefix}"
            entry = by_prefix[prefix]
            assert entry.provider == prov, f"{prefix}: provider"
            assert entry.default_role == role, f"{prefix}: role"


# ---------------------------------------------------------------------------
# Env override (primitive-gate axis: any-computer)
# ---------------------------------------------------------------------------


class TestEnvOverride:
    def test_nucleus_providers_yaml_env_overrides_default(
        self, tmp_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _write_yaml(tmp_yaml, "schema_version: 1\nproviders:\n  - prefix: myagent\n    provider: custom_provider\n    default_role: special\n")
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))

        reg = load_registry()
        assert len(reg.entries) == 1
        assert reg.entries[0].prefix == "myagent"
        assert reg.entries[0].provider == "custom_provider"

    def test_explicit_path_beats_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        env_yaml = tmp_path / "env.yaml"
        arg_yaml = tmp_path / "arg.yaml"
        _write_yaml(env_yaml, "schema_version: 1\nproviders:\n  - prefix: env_p\n    provider: env_prov\n    default_role: env_role\n")
        _write_yaml(arg_yaml, "schema_version: 1\nproviders:\n  - prefix: arg_p\n    provider: arg_prov\n    default_role: arg_role\n")
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(env_yaml))

        reg = load_registry(path=arg_yaml)
        assert reg.entries[0].prefix == "arg_p"


# ---------------------------------------------------------------------------
# Coerce legacy signature (backward-compat)
# ---------------------------------------------------------------------------


class TestCoerceBackwardCompat:
    def test_known_prefix_maps_to_tuple(self):
        out = coerce_to_tuple("gemini-flash-7")
        assert out == {
            "role": "reviewer",
            "provider": "google_gemini",
            "session_id": "gemini-flash-7",
        }

    def test_explicit_role_overrides_default(self):
        out = coerce_to_tuple("gemini-abc", role="primary")
        assert out["role"] == "primary"
        assert out["provider"] == "google_gemini"

    def test_unknown_prefix_falls_back(self):
        out = coerce_to_tuple("mystery-agent-42")
        assert out == {
            "role": "worker",
            "provider": "unknown",
            "session_id": "mystery-agent-42",
        }

    def test_empty_agent_id(self):
        out = coerce_to_tuple("")
        assert out == {"role": "worker", "provider": "unknown", "session_id": ""}

    def test_sync_ops_delegate_still_works(self):
        """Regression: the public `_coerce_legacy_to_tuple` surface still returns correct data."""
        from mcp_server_nucleus.runtime.sync_ops import _coerce_legacy_to_tuple

        out = _coerce_legacy_to_tuple("windsurf-ide")
        assert out["provider"] == "windsurf"
        assert out["role"] == "primary"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_missing_schema_version_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(tmp_yaml, "providers:\n  - prefix: p\n    provider: q\n    default_role: r\n")
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="schema_version"):
            load_registry()

    def test_wrong_schema_version_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(tmp_yaml, "schema_version: 2\nproviders:\n  - prefix: p\n    provider: q\n    default_role: r\n")
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="schema_version"):
            load_registry()

    def test_empty_providers_list_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(tmp_yaml, "schema_version: 1\nproviders: []\n")
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="providers"):
            load_registry()

    def test_missing_providers_key_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(tmp_yaml, "schema_version: 1\n")
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="providers"):
            load_registry()

    def test_entry_missing_required_field_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n  - prefix: p\n    provider: q\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="missing required keys"):
            load_registry()

    def test_unknown_entry_key_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n  - prefix: p\n    provider: q\n    default_role: r\n    extra: nope\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="unknown keys"):
            load_registry()

    def test_duplicate_prefix_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n"
            "  - prefix: p\n    provider: q1\n    default_role: r1\n"
            "  - prefix: p\n    provider: q2\n    default_role: r2\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="duplicate prefix"):
            load_registry()

    def test_empty_field_rejected(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            'schema_version: 1\nproviders:\n  - prefix: ""\n    provider: q\n    default_role: r\n',
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))
        with pytest.raises(RegistryLoadError, match="empty required field"):
            load_registry()


# ---------------------------------------------------------------------------
# mtime-based cache invalidation
# ---------------------------------------------------------------------------


class TestCacheBehavior:
    def test_repeat_load_returns_cached_instance(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n  - prefix: a\n    provider: prov1\n    default_role: worker\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))

        reg1 = load_registry()
        reg2 = load_registry()
        assert reg1 is reg2

    def test_mtime_change_invalidates_cache(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n  - prefix: a\n    provider: prov1\n    default_role: worker\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))

        reg1 = load_registry()

        # Bump mtime by rewriting with different content.
        import time

        time.sleep(0.01)
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n  - prefix: b\n    provider: prov2\n    default_role: worker\n",
        )
        os.utime(tmp_yaml, None)  # force mtime bump even on fast fs

        reg2 = load_registry()
        assert reg2.entries[0].prefix == "b"

    def test_use_cache_false_bypasses_cache(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n  - prefix: a\n    provider: prov1\n    default_role: worker\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))

        reg1 = load_registry(use_cache=False)
        reg2 = load_registry(use_cache=False)
        assert reg1 is not reg2
        assert reg1.entries[0].prefix == reg2.entries[0].prefix


# ---------------------------------------------------------------------------
# File-not-found + introspection
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_yaml_raises_clear_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_path / "does-not-exist.yaml"))
        with pytest.raises(RegistryLoadError, match="not found"):
            load_registry()

    def test_list_providers_exposes_entries(self):
        items = list_providers()
        assert isinstance(items, list)
        assert all({"prefix", "provider", "default_role"} <= set(e.keys()) for e in items)

    def test_first_match_wins_ordering(self, tmp_yaml: Path, monkeypatch):
        _write_yaml(
            tmp_yaml,
            "schema_version: 1\nproviders:\n"
            "  - prefix: claude_code_main\n    provider: anthropic_claude_code\n    default_role: primary\n"
            "  - prefix: claude_code\n    provider: anthropic_claude_code\n    default_role: other\n",
        )
        monkeypatch.setenv("NUCLEUS_PROVIDERS_YAML", str(tmp_yaml))

        out = coerce_to_tuple("claude_code_main_xyz")
        assert out["role"] == "primary"


# ---------------------------------------------------------------------------
# Primitive-gate sentinel (grep-based)
# ---------------------------------------------------------------------------


class TestPrimitiveGate:
    """Enforce invariant: provider strings are data, not code."""

    def test_sync_ops_has_no_hardcoded_providers(self):
        """grep sentinel — Slice #3 exit criterion 2."""
        import re

        sync_ops_path = (
            Path(__file__).parent.parent
            / "src"
            / "mcp_server_nucleus"
            / "runtime"
            / "sync_ops.py"
        )
        text = sync_ops_path.read_text(encoding="utf-8")

        # Strip comments + docstrings to avoid false positives from commentary.
        # Remove triple-quoted docstrings.
        text = re.sub(r'"""[\s\S]*?"""', "", text)
        # Remove # comments.
        text = re.sub(r"#.*", "", text)

        forbidden = [
            "claude_code_peer",
            "claude_code_main",
            "anthropic_claude_code",
            "google_gemini",
            "openai_codex",
            "anthropic_cowork",
        ]
        hits = [tok for tok in forbidden if tok in text]
        assert not hits, (
            f"sync_ops.py still hardcodes provider tokens: {hits} — "
            "all provider data must live in runtime/providers.yaml per Slice #3."
        )


# ── Perplexity provider entry (relay_20260427_101151_8bbea329) ──────────
# Item (1) of Perplexity full-setup directive: substrate primitive
# registration for the cross-vendor relay loop. Defends against
# sender-coercion drift when Perplexity calls relay_post without explicit
# sender (the antigravity incident pattern, R6.1-v2 hardened).

def test_perplexity_entry_resolves_to_correct_provider_tuple(tmp_path):
    """coerce_to_tuple(perplexity_*) → provider=perplexity, role=primary."""
    _clear_cache_for_tests()
    reg = provider_reg.load_registry()
    out = reg.coerce("perplexity_mac_app_session_xyz")
    assert out["provider"] == "perplexity"
    assert out["role"] == "primary"
    assert out["session_id"] == "perplexity_mac_app_session_xyz"


def test_perplexity_bare_prefix_works():
    """A bare `perplexity` agent_id (no suffix) maps to the same tuple."""
    _clear_cache_for_tests()
    reg = provider_reg.load_registry()
    out = reg.coerce("perplexity")
    assert out["provider"] == "perplexity"
    assert out["role"] == "primary"


def test_perplexity_listed_in_provider_enumeration():
    _clear_cache_for_tests()
    reg = provider_reg.load_registry()
    providers_listed = [e.provider for e in reg.entries]
    prefixes_listed = [e.prefix for e in reg.entries]
    assert "perplexity" in providers_listed
    assert "perplexity" in prefixes_listed
