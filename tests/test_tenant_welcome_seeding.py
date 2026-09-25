"""Tests for welcome-engram seeding on first brain creation and
per-tenant isolation (the load-bearing privacy gate for the ChatGPT
connector production flow per CHATGPT_FIRST_RUN_ONBOARDING.md).

Covers:
  - Welcome engram is seeded on first brain creation
  - Welcome engram is NOT re-seeded on subsequent calls
  - Welcome engram is queryable via search_engrams
  - Per-tenant isolation: two tenants get different brains, zero cross-read
  - Per-tenant isolation: engrams written by tenant A are invisible to tenant B
"""
import json
import os
import pytest
from pathlib import Path


@pytest.fixture
def isolated_brain_root(tmp_path, monkeypatch):
    """Point NUCLEUS_BRAIN_ROOT at a temp dir so tests don't touch real brains."""
    root = tmp_path / "tenants"
    root.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_ROOT", str(root))
    yield root


class TestWelcomeEngramSeeding:
    """Mitigation 2 from CHATGPT_FIRST_RUN_ONBOARDING.md."""

    def test_welcome_engram_seeded_on_first_creation(self, isolated_brain_root):
        """A freshly-created brain gets a welcome engram in its ledger."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant

        brain = brain_path_for_tenant("alice_test")

        ledger = brain / "engrams" / "ledger.jsonl"
        assert ledger.exists(), "ledger.jsonl should exist after brain creation"

        lines = [l for l in ledger.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1, "welcome engram should be seeded"

        engram = json.loads(lines[0])
        assert engram["key"] == "onboarding_welcome"
        assert "sovereign memory" in engram["value"].lower()
        assert engram["deleted"] is False
        assert engram["version"] == 1

    def test_welcome_engram_not_reseeded_on_subsequent_calls(self, isolated_brain_root):
        """Calling brain_path_for_tenant again does not duplicate the welcome engram."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant

        brain_path_for_tenant("bob_test")
        brain_path_for_tenant("bob_test")  # second call
        brain_path_for_tenant("bob_test")  # third call

        brain = isolated_brain_root / "bob_test" / ".brain"
        ledger = brain / "engrams" / "ledger.jsonl"
        lines = [l for l in ledger.read_text().splitlines() if l.strip()]
        assert len(lines) == 1, "welcome engram should not be re-seeded"

    def test_welcome_engram_is_searchable(self, isolated_brain_root):
        """The seeded welcome engram is findable via search_engrams."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl

        brain = brain_path_for_tenant("carol_test")
        # Set BOTH env vars — the tenant middleware sets both in production;
        # tests that bypass the middleware must mirror that or get_brain_path()
        # falls back to the dev's ~/.brain (the original cross-tenant leak).
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)

        result = _brain_search_engrams_impl("welcome", limit=10)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        eng = result_data["data"]["engrams"]
        assert len(eng) >= 1
        assert any(e["key"] == "onboarding_welcome" for e in eng)


class TestPerTenantIsolation:
    """The load-bearing privacy gate: two tenants never see each other's data."""

    def test_two_tenants_get_different_brain_directories(self, isolated_brain_root):
        """Different tenant_ids resolve to different brain paths."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant

        brain_a = brain_path_for_tenant("tenant_alpha")
        brain_b = brain_path_for_tenant("tenant_beta")

        assert brain_a != brain_b
        assert brain_a.exists()
        assert brain_b.exists()

    def test_engrams_written_by_tenant_a_invisible_to_tenant_b(self, isolated_brain_root):
        """An engram written under tenant A's brain does not appear in tenant B's search."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant
        from mcp_server_nucleus.runtime.engram_ops import (
            _brain_write_engram_impl,
            _brain_search_engrams_impl,
        )

        # Tenant A writes a private engram
        brain_a = brain_path_for_tenant("tenant_private_a")
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain_a)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(brain_a)
        _brain_write_engram_impl(
            key="secret_project_alpha",
            value="The launch date for Project Alpha is October 15",
            context="Strategy",
            intensity=9,
        )

        # Tenant B searches for it
        brain_b = brain_path_for_tenant("tenant_private_b")
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain_b)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(brain_b)
        result = _brain_search_engrams_impl("Project Alpha", limit=50)
        result_data = json.loads(result)
        eng = result_data["data"]["engrams"]

        # Tenant B must NOT see tenant A's secret engram
        keys = [e["key"] for e in eng]
        assert "secret_project_alpha" not in keys, (
            "CROSS-TENANT LEAK: tenant B can see tenant A's private engram"
        )

    def test_welcome_engram_does_not_leak_across_tenants(self, isolated_brain_root):
        """Each tenant gets their own welcome engram; no cross-contamination."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant

        brain_a = brain_path_for_tenant("welcome_isolation_a")
        brain_b = brain_path_for_tenant("welcome_isolation_b")

        ledger_a = brain_a / "engrams" / "ledger.jsonl"
        ledger_b = brain_b / "engrams" / "ledger.jsonl"

        engram_a = json.loads(ledger_a.read_text().strip())
        engram_b = json.loads(ledger_b.read_text().strip())

        # Same key (it's a template) but different brain files
        assert engram_a["key"] == "onboarding_welcome"
        assert engram_b["key"] == "onboarding_welcome"
        # The brain paths are different (already tested above, but reinforce)
        assert ledger_a != ledger_b

    def test_oauth_per_user_routing_produces_isolated_brains(self, isolated_brain_root, monkeypatch):
        """End-to-end: OAuth tokens for different users route to isolated brains
        with seeded welcome engrams. This is the production ChatGPT connector flow."""
        from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant
        from mcp_server_nucleus.http_transport.oauth_server import (
            _get_store,
            _derive_tenant_id_from_email,
        )

        monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
        monkeypatch.setenv("NUCLEUS_OAUTH_ISSUER", "https://test.nucleusos.dev")
        monkeypatch.setenv("NUCLEUS_OAUTH_STORE_PATH", "")
        import mcp_server_nucleus.http_transport.oauth_server as mod
        mod._store = None

        store = _get_store()
        client = store.register_client(client_name="chatgpt-connector-test")

        # Two different users grant OAuth
        alice_tenant = _derive_tenant_id_from_email("alice@chatgpt-user.com")
        bob_tenant = _derive_tenant_id_from_email("bob@chatgpt-user.com")

        alice_access, _, _ = store.issue_token(
            client["client_id"], "mcp:tools", tenant_id=alice_tenant
        )
        bob_access, _, _ = store.issue_token(
            client["client_id"], "mcp:tools", tenant_id=bob_tenant
        )

        # Simulate first request for each → brain created + welcome engram seeded
        brain_a = brain_path_for_tenant(alice_tenant)
        brain_b = brain_path_for_tenant(bob_tenant)

        assert brain_a != brain_b
        assert (brain_a / "engrams" / "ledger.jsonl").exists()
        assert (brain_b / "engrams" / "ledger.jsonl").exists()

        # Both have welcome engrams
        a_engs = [l for l in (brain_a / "engrams" / "ledger.jsonl").read_text().splitlines() if l.strip()]
        b_engs = [l for l in (brain_b / "engrams" / "ledger.jsonl").read_text().splitlines() if l.strip()]
        assert len(a_engs) >= 1
        assert len(b_engs) >= 1

        mod._store = None
