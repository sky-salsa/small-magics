# Barkeep Installer -- Claude Code Status Bar
# Usage: powershell -c "irm https://raw.githubusercontent.com/sky-salsa/small-magics/main/barkeep/install.ps1 | iex"

$ErrorActionPreference = "Stop"

$repo = "https://raw.githubusercontent.com/sky-salsa/small-magics/main/barkeep"
$installDir = Join-Path $HOME ".claude" "extensions" "barkeep"
$settingsPath = Join-Path $HOME ".claude" "settings.json"

$files = @("statusline.py", "objective-hook.py", "set-objective.py")

Write-Host ""
Write-Host "=== Barkeep -- Claude Code Status Bar ===" -ForegroundColor Cyan
Write-Host ""

# Detect old installations by scanning settings.json for previous statusline paths
$oldInstallDir = $null
if (Test-Path $settingsPath) {
    $existingSettings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($existingSettings.statusLine -and $existingSettings.statusLine.command) {
        $match = [regex]::Match($existingSettings.statusLine.command, 'python\s+"?(.+)[/\\]statusline\.py"?')
        if ($match.Success) {
            $candidate = $match.Groups[1].Value.Trim('"')
            if ($candidate -ne ($installDir -replace '\\','/') -and (Test-Path $candidate)) {
                $oldInstallDir = $candidate
            }
        }
    }
}

# Migrate objectives.json from old installation
if ($oldInstallDir) {
    Write-Host "Found previous installation at: $oldInstallDir" -ForegroundColor Yellow
    $oldObjectives = Join-Path $oldInstallDir "objectives.json"
    $newObjectives = Join-Path $installDir "objectives.json"
    if (Test-Path $oldObjectives) {
        if (-not (Test-Path $installDir)) {
            New-Item -ItemType Directory -Path $installDir -Force | Out-Null
        }
        if (Test-Path $newObjectives) {
            Write-Host "Merging objective history from old installation..." -ForegroundColor Gray
            $oldData = Get-Content $oldObjectives -Raw | ConvertFrom-Json -AsHashtable
            $newData = Get-Content $newObjectives -Raw | ConvertFrom-Json -AsHashtable
            foreach ($key in $oldData.Keys) {
                if (-not $newData.ContainsKey($key)) {
                    $newData[$key] = $oldData[$key]
                }
            }
            $newData | ConvertTo-Json -Depth 10 | Set-Content -Path $newObjectives -Encoding UTF8
        } else {
            Write-Host "Migrating objective history from old installation..." -ForegroundColor Gray
            Copy-Item $oldObjectives $newObjectives
        }
        Write-Host "Objective history preserved." -ForegroundColor Green
    }
    Write-Host ""
}

# Check for existing installation at target path (upgrade)
if (Test-Path (Join-Path $installDir "statusline.py")) {
    Write-Host "Upgrading existing Barkeep installation..." -ForegroundColor Yellow
    Write-Host "(objective history and session data will be preserved)" -ForegroundColor Gray
    Write-Host ""
}

# Check for Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python 3 is required but not found in PATH." -ForegroundColor Red
    Write-Host "Install Python from https://python.org and try again."
    exit 1
}

# Create install directory
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    Write-Host "Created $installDir" -ForegroundColor Green
}

# Download files
foreach ($file in $files) {
    $url = "$repo/$file"
    $dest = Join-Path $installDir $file
    Write-Host "Downloading $file..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    } catch {
        Write-Host "ERROR: Failed to download $file from $url" -ForegroundColor Red
        Write-Host $_.Exception.Message
        exit 1
    }
}

# Build the commands with proper paths
$statuslineCmd = "python `"$($installDir -replace '\\','/')/statusline.py`""
$hookCmd = "python `"$($installDir -replace '\\','/')/objective-hook.py`" 2>/dev/null || true"

# Read or create settings.json
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    Write-Host "Updating existing settings.json..." -ForegroundColor Gray
} else {
    $claudeDir = Join-Path $HOME ".claude"
    if (-not (Test-Path $claudeDir)) {
        New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
    }
    $settings = [PSCustomObject]@{}
    Write-Host "Creating new settings.json..." -ForegroundColor Gray
}

# Set statusLine
$settings | Add-Member -NotePropertyName "statusLine" -NotePropertyValue ([PSCustomObject]@{
    type = "command"
    command = $statuslineCmd
}) -Force

# Set hooks -- preserve existing hooks, add/update UserPromptSubmit
if (-not ($settings.PSObject.Properties.Name -contains "hooks")) {
    $settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue ([PSCustomObject]@{}) -Force
}

$barkeepHook = [PSCustomObject]@{
    hooks = @(
        [PSCustomObject]@{
            type = "command"
            command = $hookCmd
        }
    )
}

$settings.hooks | Add-Member -NotePropertyName "UserPromptSubmit" -NotePropertyValue @($barkeepHook) -Force

# Write settings back
$json = $settings | ConvertTo-Json -Depth 10
Set-Content -Path $settingsPath -Value $json -Encoding UTF8

Write-Host ""
Write-Host "Barkeep installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Restart Claude Code to see your new status bar." -ForegroundColor Cyan
Write-Host ""
