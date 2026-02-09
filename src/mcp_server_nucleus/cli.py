"""
Nucleus MCP CLI - Smart initialization and configuration
"""

import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

def get_xdg_config_home() -> Path:
    """Get XDG config directory on Linux."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

def get_claude_config_path() -> Optional[Path]:
    system = platform.system()

    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return get_xdg_config_home() / "Claude" / "claude_desktop_config.json"

    return None



def get_cursor_config_path() -> Path:
    """Get the Cursor MCP config path."""
    system = platform.system()

    if system == "Windows":
        return (
            Path(os.environ.get("APPDATA", ""))
            / "Cursor"
            / "User"
            / "globalStorage"
            / "mcp.json"
        )
    elif system == "Linux":
        return get_xdg_config_home() / "cursor" / "mcp.json"

    return Path.home() / ".cursor" / "mcp.json"



def get_windsurf_config_path() -> Path:
    """Get the Windsurf MCP config path."""
    system = platform.system()

    if system == "Windows":
        return (
            Path(os.environ.get("APPDATA", ""))
            / "Codeium"
            / "windsurf"
            / "mcp_config.json"
        )
    elif system == "Linux":
        return get_xdg_config_home() / "codeium" / "windsurf" / "mcp_config.json"

    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"



def create_brain_structure(brain_path: Path) -> None:
    """Create the .brain directory structure."""
    dirs = [
        brain_path / "ledger",
        brain_path / "engrams",
        brain_path / "artifacts",
        brain_path / "sessions",
        brain_path / "agents",
        brain_path / "sync",
        brain_path / "config",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create initial state
    state_path = brain_path / "ledger" / "state.json"
    if not state_path.exists():
        state_path.write_text(json.dumps({
            "initialized": True,
            "version": "1.0.0",
            "created_at": __import__("datetime").datetime.now().isoformat()
        }, indent=2))

    # Create config
    config_path = brain_path / "config" / "nucleus.yaml"
    if not config_path.exists():
        config_path.write_text("""# Nucleus MCP Configuration
version: "1.0.0"

# Sync settings
sync:
  auto_sync: false
  sync_interval: 5  # seconds
  watched_files:
    - ledger/state.json
    - ledger/decisions.md

# Security settings
security:
  audit_enabled: true
  lock_critical_files: false
""")

    print(f"✅ Created .brain structure at: {brain_path}")


def get_nucleus_config_block(brain_path: Path) -> Dict[str, Any]:
    """Generate the Nucleus MCP server config block."""
    return {
        "command": "python3",
        "args": ["-m", "mcp_server_nucleus"],
        "env": {
            "NUCLEAR_BRAIN_PATH": str(brain_path.absolute())
        }
    }


def update_config_file(config_path: Path, brain_path: Path) -> bool:
    """Update or create an MCP config file with Nucleus."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except json.JSONDecodeError:
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["nucleus"] = get_nucleus_config_block(brain_path)

    config_path.write_text(json.dumps(config, indent=2))
    return True


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Nucleus MCP - The Universal Brain for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nucleus-init                    # Initialize in current directory
  nucleus-init --path /my/project # Initialize at specific path
  nucleus-init --claude-only      # Only configure Claude Desktop
        """
    )

    parser.add_argument(
        "--path", "-p",
        type=str,
        default=".",
        help="Path to create .brain folder (default: current directory)"
    )

    parser.add_argument(
        "--claude-only",
        action="store_true",
        help="Only configure Claude Desktop (skip Cursor/Windsurf)"
    )

    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Skip auto-configuration of MCP clients"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="nucleus-mcp 1.0.0"
    )

    args = parser.parse_args()

    print("""
🧠 Nucleus MCP - The Universal Brain for AI Agents
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    # Create brain structure
    brain_path = Path(args.path).absolute() / ".brain"
    create_brain_structure(brain_path)

    if args.skip_config:
        print("\n⏭️  Skipping MCP client configuration")
        print("\nManually add to your MCP config:")
        print(json.dumps({"nucleus": get_nucleus_config_block(brain_path)}, indent=2))
        return

    # Configure Claude Desktop
    claude_path = get_claude_config_path()
    if claude_path:
        try:
            update_config_file(claude_path, brain_path)
            print(f"✅ Configured Claude Desktop: {claude_path}")
        except Exception as e:
            print(f"⚠️  Could not configure Claude Desktop: {e}")

    if not args.claude_only:
        # Configure Cursor
        cursor_path = get_cursor_config_path()
        try:
            update_config_file(cursor_path, brain_path)
            print(f"✅ Configured Cursor: {cursor_path}")
        except Exception as e:
            print(f"⚠️  Could not configure Cursor: {e}")

        # Configure Windsurf
        windsurf_path = get_windsurf_config_path()
        try:
            update_config_file(windsurf_path, brain_path)
            print(f"✅ Configured Windsurf: {windsurf_path}")
        except Exception as e:
            print(f"⚠️  Could not configure Windsurf: {e}")

    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Nucleus initialized successfully!

Next steps:
1. Restart your AI tools (Claude Desktop, Cursor, etc.)
2. Ask: "What's my current sprint focus?"

Your brain is ready at: """ + str(brain_path) + """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


if __name__ == "__main__":
    main()
