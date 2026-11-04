# Barkeep v2 installer (Windows / PowerShell).
# Installs to $HOME\.claude\extensions\barkeep-v2\. Does NOT touch v1
# at $HOME\.claude\extensions\barkeep\ — coexistence by design.

$ErrorActionPreference = "Stop"

$installDir   = Join-Path $HOME ".claude" "extensions" "barkeep-v2"
$settingsPath = Join-Path $HOME ".claude" "settings.json"
$scriptDir    = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Barkeep v2 -- Modular Claude Code Status Bar  " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""

# Python check
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ERROR: Python 3 is required but not found in PATH." -ForegroundColor Red
    Write-Host "  Install Python from https://python.org and try again."
    exit 1
}

if (Test-Path (Join-Path $installDir "statusline.py")) {
    Write-Host "  Found existing Barkeep v2 install. Upgrading..." -ForegroundColor Yellow
    Write-Host "  (barkeep-config.json, objectives.json, current_session.txt preserved)" -ForegroundColor Gray
} else {
    Write-Host "  Fresh install." -ForegroundColor Green
}

if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}

$codeFiles = @(
    "statusline.py",
    "statusline-light.py",
    "segments.py",
    "barkeep_config.py",
    "manage.py",
    "objective-hook.py",
    "set-objective.py",
    "barkeep-config.default.json"
)

foreach ($f in $codeFiles) {
    $src = Join-Path $scriptDir $f
    $dst = Join-Path $installDir $f
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "  Installed $f" -ForegroundColor Gray
    } else {
        Write-Host "  WARNING: $f missing from source" -ForegroundColor Yellow
    }
}

# Seed barkeep-config.json from defaults only if missing (preserves user edits)
$userConfig    = Join-Path $installDir "barkeep-config.json"
$defaultConfig = Join-Path $installDir "barkeep-config.default.json"
if (-not (Test-Path $userConfig)) {
    Copy-Item $defaultConfig $userConfig -Force
    Write-Host "  Seeded barkeep-config.json from defaults" -ForegroundColor Gray
} else {
    Write-Host "  Preserved existing barkeep-config.json" -ForegroundColor Gray
}

Write-Host ""

# Default to the full variant on Windows (matches v1 convention)
$statuslineCmd = "python `"$($installDir -replace '\\','/')/statusline.py`""
$hookCmd       = "python `"$($installDir -replace '\\','/')/objective-hook.py`" 2>/dev/null || true"

if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    Write-Host "  Updating existing settings.json..." -ForegroundColor Gray
} else {
    $claudeDir = Join-Path $HOME ".claude"
    if (-not (Test-Path $claudeDir)) {
        New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
    }
    $settings = [PSCustomObject]@{}
    Write-Host "  Created new settings.json" -ForegroundColor Gray
}

# Use python for the merge — PowerShell's PSCustomObject array handling
# is brittle and easy to clobber neighboring hooks by accident. Pass values
# via environment variables so embedded quotes/backslashes can't break the
# Python source.
$env:BARKEEP_SETTINGS_PATH  = $settingsPath
$env:BARKEEP_STATUSLINE_CMD = $statuslineCmd
$env:BARKEEP_HOOK_CMD       = $hookCmd

$mergeScript = @'
import json, os
path = os.environ["BARKEEP_SETTINGS_PATH"]
new_status_cmd = os.environ["BARKEEP_STATUSLINE_CMD"]
new_hook_cmd   = os.environ["BARKEEP_HOOK_CMD"]
with open(path, "r", encoding="utf-8") as f:
    s = json.load(f)
s["statusLine"] = {"type": "command", "command": new_status_cmd}
hooks = s.setdefault("hooks", {})
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
with open(path, "w", encoding="utf-8") as f:
    json.dump(s, f, indent=2)
print("  [hooks] UserPromptSubmit: " + ("updated existing objective-hook entry" if replaced else "appended new objective-hook entry"))
'@
$mergeScript | python -

Remove-Item Env:BARKEEP_SETTINGS_PATH
Remove-Item Env:BARKEEP_STATUSLINE_CMD
Remove-Item Env:BARKEEP_HOOK_CMD

Write-Host ""
Write-Host "  Barkeep v2 installed at: $installDir" -ForegroundColor Green
Write-Host ""
Write-Host "  Restart Claude Code to see the new status bar." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Default variant: statusline.py (full)" -ForegroundColor Gray
Write-Host "  Manage segments:" -ForegroundColor Gray
Write-Host "    python `"$installDir\manage.py`" list" -ForegroundColor Gray
Write-Host "    python `"$installDir\manage.py`" enable <segment>" -ForegroundColor Gray
Write-Host ""
Write-Host "  Rollback to v1: re-run v1's install.ps1 (this installer leaves" -ForegroundColor Gray
Write-Host "  ~\.claude\extensions\barkeep\ untouched)." -ForegroundColor Gray
Write-Host ""
