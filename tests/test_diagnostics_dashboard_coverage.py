"""Coverage tests for mcp_server_nucleus.diagnostics.dashboard."""
import sys
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.diagnostics import dashboard as dash


def test_hud_root_env_override(monkeypatch):
    monkeypatch.setenv("NUCLEUS_HUD_ROOT", "/custom/hud")
    result = dash._hud_root()
    assert result == Path("/custom/hud")


def test_hud_root_default(monkeypatch, tmp_path):
    monkeypatch.delenv("NUCLEUS_HUD_ROOT", raising=False)
    with mock.patch.object(dash, "nucleus_root", return_value=tmp_path):
        result = dash._hud_root()
    assert result == tmp_path / "tools" / "nucleus-hud"


def test_verify_files_exist_all_present(tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    pages = hud / "app" / "marketplace"
    comp.mkdir(parents=True)
    pages.mkdir(parents=True)
    (comp / "AgentCard.tsx").write_text("x")
    (comp / "MarketplaceGrid.tsx").write_text("x")
    (pages / "page.tsx").write_text("x")
    assert dash.verify_files_exist(hud) is True


def test_verify_files_exist_missing(tmp_path):
    hud = tmp_path / "hud"
    assert dash.verify_files_exist(hud) is False


def test_verify_files_exist_partial(tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    comp.mkdir(parents=True)
    (comp / "AgentCard.tsx").write_text("x")
    # Missing other files
    assert dash.verify_files_exist(hud) is False


def test_verify_content_valid(tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    comp.mkdir(parents=True)
    card = comp / "AgentCard.tsx"
    card.write_text("interface Agent {}\nexport default function AgentCard() {}\n")
    assert dash.verify_content(hud) is True


def test_verify_content_missing_interface(tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    comp.mkdir(parents=True)
    card = comp / "AgentCard.tsx"
    card.write_text("export default function AgentCard() {}\n")
    assert dash.verify_content(hud) is False


def test_verify_content_missing_export(tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    comp.mkdir(parents=True)
    card = comp / "AgentCard.tsx"
    card.write_text("interface Agent {}\n")
    assert dash.verify_content(hud) is False


def test_verify_content_no_card_file(tmp_path):
    hud = tmp_path / "hud"
    # No AgentCard.tsx exists — content cannot be verified, so this fails.
    assert dash.verify_content(hud) is False


def test_main_hud_root_not_found(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_HUD_ROOT", str(tmp_path / "nonexistent"))
    assert dash.main() == 1


def test_main_files_missing(monkeypatch, tmp_path):
    hud = tmp_path / "hud"
    hud.mkdir()
    monkeypatch.setenv("NUCLEUS_HUD_ROOT", str(hud))
    assert dash.main() == 1


def test_main_all_pass(monkeypatch, tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    pages = hud / "app" / "marketplace"
    comp.mkdir(parents=True)
    pages.mkdir(parents=True)
    (comp / "AgentCard.tsx").write_text("interface Agent {}\nexport default function AgentCard() {}\n")
    (comp / "MarketplaceGrid.tsx").write_text("x")
    (pages / "page.tsx").write_text("x")
    monkeypatch.setenv("NUCLEUS_HUD_ROOT", str(hud))
    assert dash.main() == 0


def test_main_content_fail(monkeypatch, tmp_path):
    hud = tmp_path / "hud"
    comp = hud / "app" / "components" / "marketplace"
    pages = hud / "app" / "marketplace"
    comp.mkdir(parents=True)
    pages.mkdir(parents=True)
    (comp / "AgentCard.tsx").write_text("no interface here")
    (comp / "MarketplaceGrid.tsx").write_text("x")
    (pages / "page.tsx").write_text("x")
    monkeypatch.setenv("NUCLEUS_HUD_ROOT", str(hud))
    assert dash.main() == 1
