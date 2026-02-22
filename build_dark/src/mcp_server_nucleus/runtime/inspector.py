"""
Inspector: The Lens.
Provides deep introspection into Agent Manifests for security review.

Role:
- Renders human-readable reports of what an agent can do.
- Highlights high-risk capabilities (Network, Shell, FS).
- Verifies Trust Chains (Future scope).
"""

from .identity.manifest import AgentManifest, CapabilityScope

class ManifestViewer:
    @staticmethod
    def render_report(manifest: AgentManifest) -> str:
        """
        Generates a formatted text report of the agent's identity and capabilities.
        """
        agent = manifest.agent
        lines = []
        
        # Header
        lines.append("╔═══════════════════════════════════════════════════════════╗")
        lines.append(f"║ IDENTITY: {agent.name:<47} ║")
        lines.append(f"║ ID:       {agent.id:<47} ║")
        lines.append(f"║ Version:  {agent.version:<47} ║")
        lines.append(f"║ License:  {agent.license:<47} ║")
        lines.append("╟───────────────────────────────────────────────────────────╢")
        
        # Description
        desc_preview = (agent.description[:50] + '..') if len(agent.description) > 50 else agent.description
        lines.append(f"║ {desc_preview:<57} ║")
        lines.append("╠═══════════════════════════════════════════════════════════╣")
        
        # Capabilities
        if not manifest.capabilities:
             lines.append("║ ✅ No Capabilities Requested (Safe)                       ║")
        else:
            lines.append("║ ⚠️  CAPABILITIES REQUESTED                                ║")
            lines.append("╟───────────────────────────────────────────────────────────╢")
            
            for cap in manifest.capabilities:
                scope = cap.scope.value.upper()
                icon = ManifestViewer._get_icon(cap.scope)
                
                lines.append(f"║ {icon} {scope:<53} ║")
                lines.append(f"║    Reason: {cap.reason[:44]:<44} ║")
                
                # Details
                if cap.scope == CapabilityScope.NETWORK and cap.domains:
                    lines.append(f"║    Domains: {', '.join(cap.domains)[:43]:<43} ║")
                    
                if cap.scope == CapabilityScope.FILESYSTEM and cap.paths:
                    mode = getattr(cap, 'mode', 'read')
                    lines.append(f"║    [{mode.upper()}] Paths: {', '.join(cap.paths)[:38]:<38} ║")
                
                lines.append("╟───────────────────────────────────────────────────────────╢")
                
        lines.append("╚═══════════════════════════════════════════════════════════╝")
        return "\n".join(lines)

    @staticmethod
    def _get_icon(scope: CapabilityScope) -> str:
        if scope == CapabilityScope.NETWORK:
            return "⚠️ "
        if scope == CapabilityScope.SHELL:
            return "🚨"
        if scope == CapabilityScope.FILESYSTEM:
            return "📁"
        if scope == CapabilityScope.MEMORY:
            return "🧠"
        if scope == CapabilityScope.BROWSER:
            return "🌐"
        return "🔧"
