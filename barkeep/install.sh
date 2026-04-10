#!/usr/bin/env bash
set -e

echo ""
echo "  ================================================"
echo "   Barkeep -- Claude Code Status Bar"
echo "  ================================================"
echo ""

INSTALL_DIR="$HOME/.claude/extensions/barkeep"
SETTINGS="$HOME/.claude/settings.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check for python3
if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 is required but not found in PATH."
    echo "  Install Python 3 and try again."
    exit 1
fi

# Upgrade detection
if [ -f "$INSTALL_DIR/statusline.py" ]; then
    echo "  Found existing Barkeep install. Upgrading..."
    echo "  (objective history and session data will be preserved)"
else
    echo "  Fresh install."
fi

# Create target directory
mkdir -p "$INSTALL_DIR"

# Copy files
for f in statusline.py statusline-light.py objective-hook.py set-objective.py; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
        echo "  Installed $f"
    fi
done

echo ""

# Build commands (WSL uses python3, not python)
STATUSLINE_CMD="python3 \"$INSTALL_DIR/statusline-light.py\""
HOOK_CMD="python3 \"$INSTALL_DIR/objective-hook.py\" 2>/dev/null || true"

# Update settings.json
if [ -f "$SETTINGS" ]; then
    echo "  Updating existing settings.json..."
else
    mkdir -p "$(dirname "$SETTINGS")"
    echo '{}' > "$SETTINGS"
    echo "  Created new settings.json..."
fi

# Use python3 to safely merge into settings.json
python3 -c "
import json, sys

settings_path = '$SETTINGS'
with open(settings_path, 'r') as f:
    settings = json.load(f)

# Set statusLine
settings['statusLine'] = {
    'type': 'command',
    'command': '$STATUSLINE_CMD'
}

# Add UserPromptSubmit hook
hooks = settings.setdefault('hooks', {})
hooks['UserPromptSubmit'] = [{
    'hooks': [{
        'type': 'command',
        'command': '$HOOK_CMD'
    }]
}]

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
"

echo ""
echo "  Barkeep installed successfully!"
echo ""
echo "  Restart Claude Code to see your new status bar."
echo ""
echo "  Note: This installed the 'light' variant (statusline-light.py)."
echo "  For the full variant with objectives and directory display,"
echo "  edit ~/.claude/settings.json and change statusline-light.py"
echo "  to statusline.py (and use 'python' instead of 'python3' on"
echo "  native Windows)."
echo ""
