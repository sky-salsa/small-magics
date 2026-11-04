#!/usr/bin/env bash
# Barkeep v2 installer (WSL/Linux/macOS).
# Installs to ~/.claude/extensions/barkeep-v2/. Does NOT touch v1
# at ~/.claude/extensions/barkeep/ — coexistence by design.

set -e

echo ""
echo "  ================================================"
echo "   Barkeep v2 -- Modular Claude Code Status Bar"
echo "  ================================================"
echo ""

INSTALL_DIR="$HOME/.claude/extensions/barkeep-v2"
SETTINGS="$HOME/.claude/settings.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 is required but not found in PATH."
    exit 1
fi

if [ -f "$INSTALL_DIR/statusline.py" ]; then
    echo "  Found existing Barkeep v2 install. Upgrading..."
    echo "  (barkeep-config.json, objectives.json, current_session.txt preserved)"
else
    echo "  Fresh install."
fi

mkdir -p "$INSTALL_DIR"

# Code files — always overwrite on upgrade
CODE_FILES=(
    statusline.py
    statusline-light.py
    segments.py
    barkeep_config.py
    manage.py
    objective-hook.py
    set-objective.py
    barkeep-config.default.json
)
for f in "${CODE_FILES[@]}"; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
        echo "  Installed $f"
    else
        echo "  WARNING: $f missing from source"
    fi
done

# Seed barkeep-config.json from defaults only if it doesn't exist (preserves user edits)
if [ ! -f "$INSTALL_DIR/barkeep-config.json" ]; then
    cp "$INSTALL_DIR/barkeep-config.default.json" "$INSTALL_DIR/barkeep-config.json"
    echo "  Seeded barkeep-config.json from defaults"
else
    echo "  Preserved existing barkeep-config.json"
fi

echo ""

# Default to the light variant on Linux/WSL (matches v1 convention)
STATUSLINE_CMD="python3 \"$INSTALL_DIR/statusline-light.py\""
HOOK_CMD="python3 \"$INSTALL_DIR/objective-hook.py\" 2>/dev/null || true"

if [ -f "$SETTINGS" ]; then
    echo "  Updating existing settings.json..."
else
    mkdir -p "$(dirname "$SETTINGS")"
    echo '{}' > "$SETTINGS"
    echo "  Created new settings.json"
fi

BARKEEP_SETTINGS_PATH="$SETTINGS" \
BARKEEP_STATUSLINE_CMD="$STATUSLINE_CMD" \
BARKEEP_HOOK_CMD="$HOOK_CMD" \
python3 <<'PYEOF'
import json
import os

settings_path = os.environ["BARKEEP_SETTINGS_PATH"]
new_status_cmd = os.environ["BARKEEP_STATUSLINE_CMD"]
new_hook_cmd = os.environ["BARKEEP_HOOK_CMD"]

with open(settings_path, "r", encoding="utf-8") as f:
    settings = json.load(f)

# statusLine: outright replace (single value, no merge needed)
settings["statusLine"] = {"type": "command", "command": new_status_cmd}

# UserPromptSubmit hooks: surgical merge.
# Find any inner hook whose command contains "objective-hook.py" and replace
# its command with v2's path. Leave all other hooks (and other event types)
# untouched. If no objective-hook entry exists, append a new top-level entry
# with just our hook.
hooks = settings.setdefault("hooks", {})
ups = hooks.get("UserPromptSubmit", [])
replaced = False

for outer in ups:
    for inner in outer.get("hooks", []):
        if "objective-hook.py" in inner.get("command", ""):
            inner["command"] = new_hook_cmd
            replaced = True

if not replaced:
    ups.append({"hooks": [{"type": "command", "command": new_hook_cmd}]})

hooks["UserPromptSubmit"] = ups

with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=2)

print("  [hooks] UserPromptSubmit: " + ("updated existing objective-hook entry" if replaced else "appended new objective-hook entry"))
PYEOF

echo ""
echo "  Barkeep v2 installed at: $INSTALL_DIR"
echo ""
echo "  Restart Claude Code to see the new status bar."
echo ""
echo "  Default variant: statusline-light.py (tmux/WSL friendly)"
echo "  To use the full variant instead, edit ~/.claude/settings.json"
echo "  and change 'statusline-light.py' to 'statusline.py'."
echo ""
echo "  Manage segments:"
echo "    python3 \"$INSTALL_DIR/manage.py\" list"
echo "    python3 \"$INSTALL_DIR/manage.py\" enable <segment>"
echo ""
echo "  Rollback to v1: re-run v1's install.sh (this installer leaves"
echo "  ~/.claude/extensions/barkeep/ untouched)."
echo ""
