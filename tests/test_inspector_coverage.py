"""Coverage tests for runtime/inspector.py."""
import pytest

from mcp_server_nucleus.runtime.identity.manifest import (
    AgentIdentity,
    AgentManifest,
    Capability,
    CapabilityScope,
    LifecyclePolicy,
)
from mcp_server_nucleus.runtime.inspector import ManifestViewer


def _agent(name="Ops", desc="d", license_="MIT"):
    return AgentIdentity(
        id="nucleus.core.ops",
        name=name,
        version="1.0.0",
        description=desc,
        author="me",
        license=license_,
    )


def test_render_report_no_capabilities():
    m = AgentManifest(agent=_agent())
    report = ManifestViewer.render_report(m)
    assert "No Capabilities Requested" in report
    assert "nucleus.core.ops" in report


def test_render_report_long_description_truncated():
    long_desc = "x" * 80
    m = AgentManifest(agent=_agent(desc=long_desc))
    report = ManifestViewer.render_report(m)
    assert ".." in report


def test_render_report_short_description():
    m = AgentManifest(agent=_agent(desc="short"))
    report = ManifestViewer.render_report(m)
    assert "short" in report


def test_render_report_with_network_capability():
    cap = Capability(scope=CapabilityScope.NETWORK, reason="need net", domains=["google.com"])
    m = AgentManifest(agent=_agent(), capabilities=[cap])
    report = ManifestViewer.render_report(m)
    assert "NETWORK" in report
    assert "google.com" in report


def test_render_report_with_filesystem_capability():
    cap = Capability(scope=CapabilityScope.FILESYSTEM, reason="need fs", paths=["/tmp"], mode="read")
    m = AgentManifest(agent=_agent(), capabilities=[cap])
    report = ManifestViewer.render_report(m)
    assert "FILESYSTEM" in report
    assert "/tmp" in report
    assert "READ" in report


def test_render_report_with_shell_capability():
    cap = Capability(scope=CapabilityScope.SHELL, reason="need shell")
    m = AgentManifest(agent=_agent(), capabilities=[cap])
    report = ManifestViewer.render_report(m)
    assert "SHELL" in report


def test_render_report_with_memory_capability():
    cap = Capability(scope=CapabilityScope.MEMORY, reason="need mem")
    m = AgentManifest(agent=_agent(), capabilities=[cap])
    report = ManifestViewer.render_report(m)
    assert "MEMORY" in report


def test_render_report_with_browser_capability():
    cap = Capability(scope=CapabilityScope.BROWSER, reason="need browser")
    m = AgentManifest(agent=_agent(), capabilities=[cap])
    report = ManifestViewer.render_report(m)
    assert "BROWSER" in report


def test_render_report_with_strategy_capability():
    cap = Capability(scope=CapabilityScope.STRATEGY, reason="need strat", paths=["/s"])
    m = AgentManifest(agent=_agent(), capabilities=[cap])
    report = ManifestViewer.render_report(m)
    assert "STRATEGY" in report


def test_get_icon_network():
    assert ManifestViewer._get_icon(CapabilityScope.NETWORK) == "⚠️ "


def test_get_icon_shell():
    assert ManifestViewer._get_icon(CapabilityScope.SHELL) == "🚨"


def test_get_icon_filesystem():
    assert ManifestViewer._get_icon(CapabilityScope.FILESYSTEM) == "📁"


def test_get_icon_memory():
    assert ManifestViewer._get_icon(CapabilityScope.MEMORY) == "🧠"


def test_get_icon_browser():
    assert ManifestViewer._get_icon(CapabilityScope.BROWSER) == "🌐"


def test_get_icon_default():
    assert ManifestViewer._get_icon(CapabilityScope.STRATEGY) == "🔧"
