#!/bin/bash
# First External User Alert - Detect and notify when first real user telemetry arrives

set -euo pipefail

PROJECT="/Users/lokeshgarg/ai-mvp-backend/mcp-server-nucleus"
ALERT_FILE="$PROJECT/.telemetry/first-user-detected"
TRACES_FILE="$PROJECT/.telemetry/traces.jsonl"

# Your known Python versions (to filter out your own telemetry)
YOUR_PYTHON_VERSIONS=("3.9.6" "3.11.14" "3.14.2")
YOUR_PLATFORM="darwin"

# If we already alerted, skip
if [ -f "$ALERT_FILE" ]; then
    exit 0
fi

# Check if traces file exists
if [ ! -f "$TRACES_FILE" ]; then
    exit 0
fi

# Scan traces for external users (non-your Python version or non-darwin platform)
EXTERNAL_USER_FOUND=0

while IFS= read -r line; do
    # Extract Python version and platform from JSON
    PYTHON_VER=$(echo "$line" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    attrs = d['resourceSpans'][0]['resource']['attributes']
    for a in attrs:
        if a['key'] == 'python.version':
            print(a['value']['stringValue'])
            break
except:
    pass
" 2>/dev/null || echo "")
    
    PLATFORM=$(echo "$line" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    attrs = d['resourceSpans'][0]['resource']['attributes']
    for a in attrs:
        if a['key'] == 'os.platform':
            print(a['value']['stringValue'])
            break
except:
    pass
" 2>/dev/null || echo "")
    
    # Check if this is NOT your telemetry
    IS_YOURS=0
    for ver in "${YOUR_PYTHON_VERSIONS[@]}"; do
        if [ "$PYTHON_VER" = "$ver" ] && [ "$PLATFORM" = "$YOUR_PLATFORM" ]; then
            IS_YOURS=1
            break
        fi
    done
    
    # If not yours and has valid data, it's an external user
    if [ "$IS_YOURS" -eq 0 ] && [ -n "$PYTHON_VER" ] && [ -n "$PLATFORM" ]; then
        EXTERNAL_USER_FOUND=1
        FIRST_USER_PYTHON="$PYTHON_VER"
        FIRST_USER_PLATFORM="$PLATFORM"
        
        # Extract command name
        FIRST_USER_COMMAND=$(echo "$line" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    spans = d['resourceSpans'][0]['scopeSpans'][0]['spans']
    print(spans[0].get('name', 'unknown'))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")
        
        break
    fi
done < "$TRACES_FILE"

# If external user found, create alert
if [ "$EXTERNAL_USER_FOUND" -eq 1 ]; then
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create alert file
    cat > "$ALERT_FILE" << EOF
🎉 FIRST EXTERNAL USER DETECTED!

Timestamp: $TIMESTAMP
Python Version: $FIRST_USER_PYTHON
Platform: $FIRST_USER_PLATFORM
Command: $FIRST_USER_COMMAND

This is NOT your telemetry (you use Python ${YOUR_PYTHON_VERSIONS[*]} on darwin).

Check traces.jsonl for more details:
  cat $TRACES_FILE | grep -v "3.9.6\|3.11.14\|3.14.2"

Congratulations! 🚀
EOF
    
    # Display alert
    cat "$ALERT_FILE"
    
    # macOS notification (if available)
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"Python $FIRST_USER_PYTHON on $FIRST_USER_PLATFORM\" with title \"🎉 First Nucleus User!\" sound name \"Glass\""
    fi
    
    # Log to smart-drain log
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🎉 FIRST EXTERNAL USER DETECTED: Python $FIRST_USER_PYTHON on $FIRST_USER_PLATFORM" >> "$PROJECT/.telemetry/smart-drain.log"
fi
