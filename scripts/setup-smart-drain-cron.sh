#!/bin/bash
# Setup Smart Drain Cron - Run every 12 hours

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SMART_DRAIN="$SCRIPT_DIR/smart-drain.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 SMART DRAIN CRON SETUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Remove old telemetry:drain cron if exists
if crontab -l 2>/dev/null | grep -q "telemetry:drain"; then
    echo "🗑️  Removing old telemetry:drain cron..."
    crontab -l 2>/dev/null | grep -v "telemetry:drain" | grep -v "# Nucleus Telemetry" | crontab -
fi

# Check if smart-drain cron already exists
if crontab -l 2>/dev/null | grep -q "smart-drain.sh"; then
    echo "⚠️  Smart drain cron already exists."
    echo ""
    echo "Current crontab:"
    crontab -l | grep -A1 -B1 "smart-drain"
    echo ""
    read -p "Replace existing job? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping cron setup."
        exit 0
    fi
    # Remove old job
    crontab -l | grep -v "smart-drain" | grep -v "# Nucleus Smart Drain" | crontab -
fi

# Add new cron job (every 12 hours at minute 0)
(crontab -l 2>/dev/null; echo ""; echo "# Nucleus Smart Drain (every 12 hours)"; echo "0 */12 * * * bash $SMART_DRAIN") | crontab -

echo "✅ Smart drain cron added successfully!"
echo ""
echo "Schedule: Every 12 hours (at 00:00 and 12:00)"
echo "Script: $SMART_DRAIN"
echo "Log: $PROJECT_ROOT/.telemetry/smart-drain.log"
echo ""
echo "What it does:"
echo "  • Starts telemetry containers if not running"
echo "  • Drains spans from Upstash → local collector"
echo "  • Checks for first external user (alerts if found)"
echo "  • Stops containers only if it started them"
echo ""
echo "To verify:"
echo "  crontab -l"
echo ""
echo "To test manually:"
echo "  bash $SMART_DRAIN"
echo ""
echo "To remove:"
echo "  crontab -e  # then delete the smart-drain line"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
