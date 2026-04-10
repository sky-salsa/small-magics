# System Inputs Config Installer
# Creates startup and desktop shortcuts for the AHK remapping script.
#
# Prerequisites:
#   - AutoHotkey v2 installed (winget install AutoHotkey.AutoHotkey)
#   - Bluetooth ring paired and in Music Mode
#   - G Hub onboard profile configured (F16/F17 side buttons, F18/F19 G-Shift)
#
# Usage: Run from the directory containing system-inputs-config.ahk

$ErrorActionPreference = "Stop"

$scriptName = "system-inputs-config.ahk"
$scriptPath = Join-Path $PSScriptRoot $scriptName

if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: $scriptName not found in $PSScriptRoot" -ForegroundColor Red
    exit 1
}

# Check for AutoHotkey
$ahk = Get-Command "AutoHotkey64.exe", "AutoHotkey32.exe", "AutoHotkey.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $ahk) {
    Write-Host "AutoHotkey not found. Install it first:" -ForegroundColor Red
    Write-Host "  winget install AutoHotkey.AutoHotkey"
    exit 1
}

$ahkPath = $ahk.Source
Write-Host ""
Write-Host "=== System Inputs Config -- Shortcut Creator ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "AHK: $ahkPath" -ForegroundColor Gray
Write-Host "Script: $scriptPath" -ForegroundColor Gray
Write-Host ""

$shell = New-Object -ComObject WScript.Shell

# --- Startup shortcut (Run as Administrator) ---
$startupDir = [Environment]::GetFolderPath("Startup")
$startupLnk = Join-Path $startupDir "System Inputs Config.lnk"

$lnk = $shell.CreateShortcut($startupLnk)
$lnk.TargetPath = $ahkPath
$lnk.Arguments = "`"$scriptPath`""
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Description = "System Inputs Config -- ring + mouse + ShareX remapping"
$lnk.Save()

# Set "Run as administrator" flag (byte 0x15 = 0x20)
$bytes = [System.IO.File]::ReadAllBytes($startupLnk)
$bytes[0x15] = $bytes[0x15] -bor 0x20
[System.IO.File]::WriteAllBytes($startupLnk, $bytes)

Write-Host "Created startup shortcut (Run as Administrator):" -ForegroundColor Green
Write-Host "  $startupLnk"

# --- Desktop shortcut ---
$desktopDir = [Environment]::GetFolderPath("Desktop")
$desktopLnk = Join-Path $desktopDir "System Inputs Config.lnk"

$lnk = $shell.CreateShortcut($desktopLnk)
$lnk.TargetPath = $ahkPath
$lnk.Arguments = "`"$scriptPath`""
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Description = "System Inputs Config -- ring + mouse + ShareX remapping"
$lnk.Save()

# Also set Run as Administrator on desktop shortcut
$bytes = [System.IO.File]::ReadAllBytes($desktopLnk)
$bytes[0x15] = $bytes[0x15] -bor 0x20
[System.IO.File]::WriteAllBytes($desktopLnk, $bytes)

Write-Host "Created desktop shortcut (Run as Administrator):" -ForegroundColor Green
Write-Host "  $desktopLnk"

Write-Host ""
Write-Host "Done! The script will auto-start on login (UAC prompt expected)." -ForegroundColor Cyan
Write-Host "Double-click the desktop shortcut to start it now." -ForegroundColor Cyan
Write-Host ""
