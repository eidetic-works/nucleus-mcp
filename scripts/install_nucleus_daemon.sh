#!/usr/bin/env bash

# =============================================================================
# Nucleus Sovereign Controller - Privilege System Installer
# =============================================================================
# This script installs mcp-server-nucleus as a privileged root daemon using 
# systemd (Linux) or launchd (macOS). This implements Level 5 of the Nucleus 
# Trust Matrix (Strict Privilege Separation) preventing the AI Agent from 
# terminating the Watchdog.
# =============================================================================

set -e

# Require root
if [ "$EUID" -ne 0 ]; then
  echo "🚨 ERROR: This script must be run as root (sudo)."
  echo "Usage: sudo ./install_nucleus_daemon.sh"
  exit 1
fi

echo "🛡️  Nucleus Sovereign Controller Installer"
echo "----------------------------------------"

# Detect OS
OS_UNAME=$(uname -s)
SERVICE_NAME="nucleus-hypervisor"

# Determine path to the python executable running this env, defaulting to global python3 if not known
PYTHON_EXEC=$(which python3)

if [[ -f "/usr/bin/python3" ]]; then
    PYTHON_EXEC="/usr/bin/python3"
fi

echo "🔍 Detected OS: $OS_UNAME"
echo "🐍 Python Executable: $PYTHON_EXEC"

if [[ "$OS_UNAME" == "Linux" ]]; then
    echo "⚙️  Configuring Systemd Service (Linux)..."
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Nucleus MCP Sovereign Hypervisor
After=network.target

[Service]
Type=simple
User=root
# Execute module directly to avoid external binary dependencies
ExecStart=$PYTHON_EXEC -m mcp_server_nucleus
Restart=always
RestartSec=5
# Output to syslog
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=nucleus-hypervisor

[Install]
WantedBy=multi-user.target
EOF

    echo "✅ Created $SERVICE_FILE"
    echo "🔄 Reloading systemd modules..."
    systemctl daemon-reload
    echo "⚡ Starting and enabling service..."
    systemctl enable --now ${SERVICE_NAME}
    echo "🎉 Nucleus Hypervisor is now running as root via systemd."
    echo "   Verify status with: sudo systemctl status $SERVICE_NAME"
    echo "   View logs with:   sudo journalctl -u $SERVICE_NAME -f"

elif [[ "$OS_UNAME" == "Darwin" ]]; then
    echo "⚙️  Configuring launchd Daemon (macOS)..."
    PLIST_FILE="/Library/LaunchDaemons/com.eidetic.nucleus.plist"
    
    cat <<EOF > "$PLIST_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.eidetic.nucleus</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_EXEC</string>
        <string>-m</string>
        <string>mcp_server_nucleus</string>
    </array>
    <key>UserName</key>
    <string>root</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/var/log/nucleus-hypervisor.error.log</string>
    <key>StandardOutPath</key>
    <string>/var/log/nucleus-hypervisor.out.log</string>
</dict>
</plist>
EOF

    echo "✅ Created $PLIST_FILE"
    echo "🔄 Adjusting permissions..."
    chmod 644 "$PLIST_FILE"
    chown root:wheel "$PLIST_FILE"
    
    echo "⚡ Loading and starting daemon..."
    # Always try to unload first in case it already exists
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load -w "$PLIST_FILE"
    
    echo "🎉 Nucleus Hypervisor is now running as root via launchd."
    echo "   Verify status with: sudo launchctl list | grep nucleus"
    echo "   View logs with:   tail -f /var/log/nucleus-hypervisor.error.log"

else
    echo "❌ ERROR: Unsupported OS '$OS_UNAME'. This script currently supports Linux (systemd) and macOS (launchd)."
    exit 1
fi

echo "----------------------------------------"
echo "🔒 Level 5 Assurance: The Host is now Sovereign."
