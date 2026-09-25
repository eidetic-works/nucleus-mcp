"""Tests for v0.3.0 integration — sessions/discovery_context.

Per cc-peer 2026-06-09T10:45Z verdict batch (PR #506 piece (c)
discovery_context_fetcher).

Coverage:
- build_discovery_context happy path: pulls mcp_servers from
  get_mcp_bootstrap, threads system_prompt
- Best-effort: get_mcp_bootstrap DiscoveryError absorbed, partial
  context returned
- Empty mcp_servers omitted from result dict (Layer 5 sees absent key)
- Defensive bootstrap parsing: top-level list, mcp_servers key,
  servers key, nested data.mcp_servers, non-dict ignored
- Missing required args raise ValueError
- Pseudonymity: bearer never logged; org_uuid truncated in logs
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server_nucleus.sessions import discovery_context as dc
from mcp_server_nucleus.org.discovery import DiscoveryError


# ── Happy path ────────────────────────────────────────────────────────


def test_build_discovery_context_threads_mcp_servers():
    bootstrap_response = {
        "mcp_servers": [
            {"url": "https://nucleus.local", "type": "url"},
            {"url": "https://eidetic.local", "type": "url"},
        ],
    }
    with patch.object(dc, "get_mcp_bootstrap", return_value=bootstrap_response):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB-OAT", org_uuid="903554b9-org",
            system_prompt="You are cc-tb autonomous.",
        )
    assert ctx["system_prompt"] == "You are cc-tb autonomous."
    assert len(ctx["mcp_servers"]) == 2
    assert ctx["mcp_servers"][0]["url"] == "https://nucleus.local"


def test_system_prompt_omitted_when_empty():
    """Empty system_prompt → omitted from result dict (Layer 5 default)."""
    with patch.object(dc, "get_mcp_bootstrap",
                      return_value={"mcp_servers": [{"url": "x"}]}):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB-OAT", org_uuid="o",
            system_prompt="",
        )
    assert "system_prompt" not in ctx


# ── Best-effort Layer 2 failure absorption ─────────────────────────────


def test_get_mcp_bootstrap_fail_returns_partial_context():
    with patch.object(dc, "get_mcp_bootstrap",
                      side_effect=DiscoveryError("GET rejected status=401")):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB-OAT", org_uuid="o",
            system_prompt="You are cc-tb.",
        )
    # mcp_servers absent (Layer 2 failed)
    assert "mcp_servers" not in ctx
    # system_prompt threaded through
    assert ctx["system_prompt"] == "You are cc-tb."


def test_get_mcp_bootstrap_fail_with_empty_system_prompt_returns_empty_dict():
    with patch.object(dc, "get_mcp_bootstrap",
                      side_effect=DiscoveryError("transport")):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB-OAT", org_uuid="o",
        )
    assert ctx == {}


# ── Empty mcp_servers omitted ─────────────────────────────────────────


def test_empty_mcp_servers_list_omitted_from_result():
    """If bootstrap returns empty list → omit mcp_servers key entirely."""
    with patch.object(dc, "get_mcp_bootstrap",
                      return_value={"mcp_servers": []}):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB-OAT", org_uuid="o",
        )
    assert "mcp_servers" not in ctx


# ── Defensive parsing ─────────────────────────────────────────────────


def test_extract_mcp_servers_top_level_list():
    out = dc._extract_mcp_servers([{"url": "a"}, {"url": "b"}])
    assert len(out) == 2


def test_extract_mcp_servers_from_mcp_servers_key():
    out = dc._extract_mcp_servers({"mcp_servers": [{"url": "x"}]})
    assert out == [{"url": "x"}]


def test_extract_mcp_servers_from_servers_key():
    out = dc._extract_mcp_servers({"servers": [{"url": "y"}]})
    assert out == [{"url": "y"}]


def test_extract_mcp_servers_from_nested_data():
    out = dc._extract_mcp_servers({"data": {"mcp_servers": [{"url": "z"}]}})
    assert out == [{"url": "z"}]


def test_extract_mcp_servers_non_dict_returns_empty():
    assert dc._extract_mcp_servers(None) == []
    assert dc._extract_mcp_servers("not a dict") == []
    assert dc._extract_mcp_servers(42) == []


def test_extract_mcp_servers_no_known_key_returns_empty():
    assert dc._extract_mcp_servers({"unknown": []}) == []
    assert dc._extract_mcp_servers({}) == []


def test_extract_mcp_servers_first_match_wins():
    """When multiple recognized keys present, top-level mcp_servers wins."""
    response = {
        "mcp_servers": [{"url": "primary"}],
        "servers": [{"url": "secondary"}],
    }
    out = dc._extract_mcp_servers(response)
    assert out == [{"url": "primary"}]


# ── Missing args raise ValueError ─────────────────────────────────────


def test_raises_on_empty_role():
    with pytest.raises(ValueError):
        dc.build_discovery_context("", bearer="STUB", org_uuid="o")


def test_raises_on_empty_bearer():
    with pytest.raises(ValueError):
        dc.build_discovery_context("cc_tb", bearer="", org_uuid="o")


def test_raises_on_empty_org_uuid():
    with pytest.raises(ValueError):
        dc.build_discovery_context("cc_tb", bearer="STUB", org_uuid="")


# ── Pseudonymity ──────────────────────────────────────────────────────


def test_bearer_never_logged_on_success(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.discovery_context")
    SECRET_BEARER = "STUB-OAT-DISCOVERY-secret-do-not-leak-xyz"
    with patch.object(dc, "get_mcp_bootstrap",
                      return_value={"mcp_servers": []}):
        dc.build_discovery_context(
            "cc_tb", bearer=SECRET_BEARER, org_uuid="o",
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_bearer_never_logged_on_failure(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.discovery_context")
    SECRET_BEARER = "STUB-OAT-fail-leak-check-xyz"
    with patch.object(dc, "get_mcp_bootstrap",
                      side_effect=DiscoveryError("rejected")):
        dc.build_discovery_context(
            "cc_tb", bearer=SECRET_BEARER, org_uuid="o",
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_org_uuid_truncated_in_logs(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.discovery_context")
    long_org = "903554b9-AAAAAAAA-BBBBBBBB-CCCCCCCC-secret-rest"
    with patch.object(dc, "get_mcp_bootstrap",
                      return_value={"mcp_servers": [{"url": "x"}]}):
        dc.build_discovery_context(
            "cc_tb", bearer="STUB-OAT", org_uuid=long_org,
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert long_org[:12] in all_text
    assert long_org not in all_text


# ── Exports ───────────────────────────────────────────────────────────


def test_all_exported():
    assert set(dc.__all__) == {"build_discovery_context"}


# ── Task #63 wiring: bespoq_context loader called when account_uuid present ──


def test_bespoq_loader_called_when_account_uuid_and_session_id_present():
    """Wiring contract: account_uuid + session_id present → loader fires."""
    with patch.object(dc, "load_bespoq_session_context") as bespoq_mock, \
         patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": []}):
        bespoq_mock.return_value = {
            "system_prompt": "You are bespoq.",
            "mcp_servers": [{"url": "https://nucleus.local"}],
            "title": "bespoq title",
        }
        ctx = dc.build_discovery_context(
            "bespoq_cowork",
            bearer="STUB-OAT",
            org_uuid="org-1",
            account_uuid="acct-1",
            session_id="cse_match",
        )
    bespoq_mock.assert_called_once()
    args = bespoq_mock.call_args.kwargs
    assert args["account_uuid"] == "acct-1"
    assert args["org_uuid"] == "org-1"
    assert args["session_id"] == "cse_match"
    # bespoq fields threaded into context
    assert ctx["system_prompt"] == "You are bespoq."
    assert ctx["title"] == "bespoq title"
    assert any(s["url"] == "https://nucleus.local" for s in ctx["mcp_servers"])


def test_bespoq_loader_skipped_when_account_uuid_absent():
    """Backward compat: no account_uuid → no bespoq call."""
    with patch.object(dc, "load_bespoq_session_context") as bespoq_mock, \
         patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": [{"url": "x"}]}):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB", org_uuid="o",
        )
    bespoq_mock.assert_not_called()
    # Layer 2 mcp_servers still threaded
    assert ctx.get("mcp_servers") == [{"url": "x"}]


def test_bespoq_loader_skipped_when_session_id_absent():
    """Both account_uuid + session_id required for lookup."""
    with patch.object(dc, "load_bespoq_session_context") as bespoq_mock, \
         patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": []}):
        dc.build_discovery_context(
            "cc_tb", bearer="STUB", org_uuid="o", account_uuid="acct-1",
            # session_id missing
        )
    bespoq_mock.assert_not_called()


def test_bespoq_loader_none_falls_back_to_caller_system_prompt(caplog):
    """When loader returns None (file missing / mismatch) → caller's
    system_prompt arg used as fallback."""
    import logging
    caplog.set_level(logging.WARNING, logger="nucleus.discovery_context")
    with patch.object(dc, "load_bespoq_session_context", return_value=None), \
         patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": []}):
        ctx = dc.build_discovery_context(
            "cc_tb",
            bearer="STUB",
            org_uuid="o",
            system_prompt="fallback prompt",
            account_uuid="acct-1",
            session_id="cse_x",
        )
    assert ctx["system_prompt"] == "fallback prompt"
    assert any(
        "bespoq context unavailable" in r.getMessage() for r in caplog.records
    )


def test_bespoq_loader_BespoqContextError_absorbed():
    """Loader raises (e.g., missing required args) → absorbed, fall back."""
    with patch.object(
        dc, "load_bespoq_session_context",
        side_effect=dc.BespoqContextError("bad args"),
    ), patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": [{"url": "x"}]}):
        ctx = dc.build_discovery_context(
            "cc_tb",
            bearer="STUB",
            org_uuid="o",
            account_uuid="acct-1",
            session_id="cse_x",
        )
    # Wake still fires with Layer 2 fallback
    assert ctx.get("mcp_servers") == [{"url": "x"}]


def test_mcp_servers_merged_bespoq_then_layer2():
    """Merge: bespoq mcp_servers first, Layer 2 fills (de-dup by url)."""
    with patch.object(dc, "load_bespoq_session_context", return_value={
        "mcp_servers": [
            {"url": "https://bespoq-1.local"},
            {"url": "https://shared.local", "name": "from_bespoq"},
        ],
    }), patch.object(dc, "get_mcp_bootstrap", return_value={
        "mcp_servers": [
            {"url": "https://shared.local", "name": "from_layer2"},
            {"url": "https://layer2-only.local"},
        ],
    }):
        ctx = dc.build_discovery_context(
            "cc_tb",
            bearer="STUB",
            org_uuid="o",
            account_uuid="acct",
            session_id="cse_x",
        )
    urls = [s["url"] for s in ctx["mcp_servers"]]
    assert urls == [
        "https://bespoq-1.local",
        "https://shared.local",
        "https://layer2-only.local",
    ]
    # bespoq wins on duplicate
    shared = next(s for s in ctx["mcp_servers"] if s["url"] == "https://shared.local")
    assert shared.get("name") == "from_bespoq"


def test_bespoq_system_prompt_wins_over_caller_arg():
    """When bespoq supplies non-empty system_prompt, it OVERRIDES caller arg."""
    with patch.object(dc, "load_bespoq_session_context", return_value={
        "system_prompt": "BESPOQ identity",
        "mcp_servers": [],
    }), patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": []}):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB", org_uuid="o",
            system_prompt="generic caller prompt",
            account_uuid="acct", session_id="cse_x",
        )
    assert ctx["system_prompt"] == "BESPOQ identity"


def test_layer2_fail_does_not_block_bespoq_path():
    """Layer 2 DiscoveryError absorbed; bespoq mcp_servers still threaded."""
    with patch.object(dc, "load_bespoq_session_context", return_value={
        "mcp_servers": [{"url": "https://bespoq.local"}],
    }), patch.object(dc, "get_mcp_bootstrap",
                     side_effect=DiscoveryError("status=403")):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB", org_uuid="o",
            account_uuid="acct", session_id="cse_x",
        )
    assert ctx["mcp_servers"] == [{"url": "https://bespoq.local"}]


def test_merge_handles_servers_without_url_key():
    """Entries without 'url' key kept (no dedup possible)."""
    with patch.object(dc, "load_bespoq_session_context", return_value={
        "mcp_servers": [{"type": "stdio", "command": "x"}, {"url": "u1"}],
    }), patch.object(dc, "get_mcp_bootstrap", return_value={
        "mcp_servers": [{"type": "stdio", "command": "y"}],
    }):
        ctx = dc.build_discovery_context(
            "cc_tb", bearer="STUB", org_uuid="o",
            account_uuid="acct", session_id="cse_x",
        )
    # Both no-url entries kept + one url entry
    assert len(ctx["mcp_servers"]) == 3


def test_account_uuid_truncated_in_logs(caplog):
    """Pseudonymity: account_uuid truncated [:12] per PR #499."""
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.discovery_context")
    LONG_ACCT = "acct_AAAAAAAAAAAAAAAAAAAAAAAAA_secret"
    with patch.object(dc, "load_bespoq_session_context", return_value=None), \
         patch.object(dc, "get_mcp_bootstrap", return_value={"mcp_servers": []}):
        dc.build_discovery_context(
            "cc_tb", bearer="STUB", org_uuid="o",
            account_uuid=LONG_ACCT, session_id="cse_x",
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert LONG_ACCT not in all_text
    assert LONG_ACCT[:12] in all_text
