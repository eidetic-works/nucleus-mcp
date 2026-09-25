"""Coverage tests for runtime/auth.py.

Note: runtime/auth.py is shadowed by the runtime/auth/ package directory,
so we load the module directly from its file path via importlib.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_AUTH_PY = Path(__file__).resolve().parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "auth.py"


def _load_auth_module():
    spec = importlib.util.spec_from_file_location("_nucleus_auth_mod", _AUTH_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_nucleus_auth_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


auth_mod = _load_auth_module()
AuthManager = auth_mod.AuthManager
Credentials = auth_mod.Credentials
PrivateSource = auth_mod.PrivateSource


def _brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir()
    return brain


def test_private_source_defaults():
    s = PrivateSource(domain="github.com", token_env="GH_TOKEN")
    assert s.username == "oauth2"
    assert s.org is None


def test_private_source_required():
    with pytest.raises(Exception):
        PrivateSource(domain="github.com")  # missing token_env


def test_credentials_model():
    c = Credentials(username="u", token="t")
    assert c.username == "u"
    assert c.token == "t"


def test_authmanager_init_no_config(tmp_path):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    assert am.sources == []


def test_authmanager_load_config(tmp_path):
    brain = _brain(tmp_path)
    cfg = brain / "config"
    cfg.mkdir()
    (cfg / "auth.json").write_text(json.dumps({
        "sources": [
            {"domain": "github.com", "org": "myorg", "token_env": "GH_TOKEN"},
            {"domain": "gitlab.com", "token_env": "GL_TOKEN"},
        ]
    }))
    am = AuthManager(brain)
    assert len(am.sources) == 2
    assert am.sources[0].org == "myorg"


def test_authmanager_load_config_corrupt(tmp_path):
    brain = _brain(tmp_path)
    cfg = brain / "config"
    cfg.mkdir()
    (cfg / "auth.json").write_text("not json")
    am = AuthManager(brain)
    assert am.sources == []


def test_get_credentials_no_match(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    assert am.get_credentials("https://example.com/org/repo") is None


def test_get_credentials_domain_only_match(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    am.sources = [PrivateSource(domain="github.com", token_env="GH_TOKEN")]
    monkeypatch.setenv("GH_TOKEN", "tok123")
    creds = am.get_credentials("https://github.com/owner/repo")
    assert creds is not None
    assert creds.token == "tok123"
    assert creds.username == "oauth2"


def test_get_credentials_org_match_preferred(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    am.sources = [
        PrivateSource(domain="github.com", token_env="GEN_TOKEN"),
        PrivateSource(domain="github.com", org="myorg", token_env="ORG_TOKEN"),
    ]
    monkeypatch.setenv("GEN_TOKEN", "gen")
    monkeypatch.setenv("ORG_TOKEN", "org")
    creds = am.get_credentials("https://github.com/myorg/repo")
    assert creds.token == "org"


def test_get_credentials_org_mismatch_falls_back_to_domain(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    am.sources = [
        PrivateSource(domain="github.com", org="myorg", token_env="ORG_TOKEN"),
        PrivateSource(domain="github.com", token_env="GEN_TOKEN"),
    ]
    monkeypatch.setenv("ORG_TOKEN", "org")
    monkeypatch.setenv("GEN_TOKEN", "gen")
    creds = am.get_credentials("https://github.com/otherorg/repo")
    assert creds.token == "gen"


def test_resolve_env_missing_token(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    monkeypatch.delenv("MISSING_TOKEN", raising=False)
    src = PrivateSource(domain="github.com", token_env="MISSING_TOKEN")
    assert am._resolve_env(src) is None


def test_inject_credentials_no_creds(tmp_path):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    url = "https://example.com/o/r"
    assert am.inject_credentials(url) == url


def test_inject_credentials_with_creds(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    am.sources = [PrivateSource(domain="github.com", token_env="GH_TOKEN")]
    monkeypatch.setenv("GH_TOKEN", "tok123")
    out = am.inject_credentials("https://github.com/o/r")
    assert "oauth2:tok123@github.com" in out


def test_inject_credentials_with_port(tmp_path, monkeypatch):
    brain = _brain(tmp_path)
    am = AuthManager(brain)
    # get_credentials matches on netloc which includes port; mock to return
    # creds so the port-handling branch in inject_credentials is exercised.
    monkeypatch.setattr(am, "get_credentials", lambda url: Credentials(username="oauth2", token="tok"))
    out = am.inject_credentials("https://gitlab.example.com:8443/o/r")
    assert "oauth2:tok@gitlab.example.com:8443" in out
