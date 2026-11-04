# Barkeep v2 installer (Windows).
# Runs in Windows PowerShell 5.1, the version built into Windows.
#
# From this folder:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# Installs to <your home>\.claude\extensions\barkeep-v2\ and merges the status
# line and objective hook into settings.json. Does NOT touch v1 at
# <your home>\.claude\extensions\barkeep\ -- coexistence by design.
#
# -ClaudeDir points the install at a different Claude config folder, which is
# handy for trying it somewhere harmless. It defaults to your real one.
#
# Keep this file ASCII. Windows PowerShell 5.1 misreads UTF-8 without a BOM, and
# the merge script below reaches Python through a pipe that is ASCII by default.

param(
    [string]$ClaudeDir
)

$ErrorActionPreference = "Stop"

function Stop-Install([string]$Message) {
    Write-Host ""
    Write-Host "  INSTALL FAILED: $Message" -ForegroundColor Red
    Write-Host ""
    # Pasted into a console there is no script to exit, and exit would close the
    # window before the message can be read.
    if ($PSCommandPath) { exit 1 }
    throw "Barkeep install failed."
}

trap {
    Stop-Install $_.Exception.Message
}

function Find-Python {
    # Run each candidate for real. Windows ships Store shortcuts named python and
    # python3 that Get-Command finds but that can't run anything.
    $ErrorActionPreference = "Continue"
    $probe = "import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 7) else 1)"
    $candidates = @(
        @{ Exe = "python";  Args = @() },
        @{ Exe = "python3"; Args = @() },
        @{ Exe = "py";      Args = @("-3") }
    )
    foreach ($candidate in $candidates) {
        $pyArgs = $candidate.Args
        try {
            $version = & $candidate.Exe @pyArgs -c $probe 2>$null
            if ($LASTEXITCODE -eq 0 -and $version) {
                return @{ Exe = $candidate.Exe; Args = $pyArgs; Version = "$version" }
            }
        } catch {
            # Not on PATH. Try the next one.
        }
    }
    return $null
}

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Barkeep v2 -- Modular Claude Code Status Bar  " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    Stop-Install "This installer has to run from a clone of the repo, not through 'irm | iex'. See barkeep/README.md."
}

if (-not $ClaudeDir) {
    # Claude Code reads its config from USERPROFILE on Windows.
    $userHome = $env:USERPROFILE
    if (-not $userHome) { $userHome = $HOME }
    $ClaudeDir = Join-Path $userHome ".claude"
}
$ClaudeDir    = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ClaudeDir)
$extensionDir = Join-Path $ClaudeDir "extensions"
$installDir   = Join-Path $extensionDir "barkeep-v2"
$v1Dir        = Join-Path $extensionDir "barkeep"
$settingsPath = Join-Path $ClaudeDir "settings.json"

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

# Everything that can be checked gets checked before anything is written.
$missing = @($codeFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $scriptDir $_)) })
if ($missing.Count -gt 0) {
    Stop-Install "These files are missing from ${scriptDir}: $($missing -join ', '). Nothing was changed. A fresh clone should fix it."
}

$python = Find-Python
if (-not $python) {
    Stop-Install "Barkeep needs Python 3.7 or newer, and no working python, python3, or py was found on PATH. The Windows Store shortcuts named python don't count. Install it from https://python.org or with 'winget install Python.Python.3.12', open a new window, and run this again. Nothing was changed."
}
$pyArgs    = $python.Args
$pyCommand = (@($python.Exe) + $pyArgs) -join " "
Write-Host "  Using Python $($python.Version) ($pyCommand)" -ForegroundColor Gray

if (Test-Path -LiteralPath (Join-Path $installDir "statusline.py")) {
    Write-Host "  Found existing Barkeep v2 install. Upgrading..." -ForegroundColor Yellow
    Write-Host "  (barkeep-config.json, objectives.json, current_session.txt preserved)" -ForegroundColor Gray
} else {
    Write-Host "  Fresh install." -ForegroundColor Green
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null

foreach ($f in $codeFiles) {
    Copy-Item -LiteralPath (Join-Path $scriptDir $f) -Destination (Join-Path $installDir $f) -Force
    Write-Host "  Installed $f" -ForegroundColor Gray
}

# Seed barkeep-config.json from defaults only if missing (preserves user edits)
$userConfig    = Join-Path $installDir "barkeep-config.json"
$defaultConfig = Join-Path $installDir "barkeep-config.default.json"
if (-not (Test-Path -LiteralPath $userConfig)) {
    Copy-Item -LiteralPath $defaultConfig -Destination $userConfig -Force
    Write-Host "  Seeded barkeep-config.json from defaults" -ForegroundColor Gray
} else {
    Write-Host "  Preserved existing barkeep-config.json" -ForegroundColor Gray
}

Write-Host ""

# Default to the full variant on Windows (matches v1 convention)
$installDirForward = $installDir -replace '\\','/'
$statuslineCmd = "$pyCommand `"$installDirForward/statusline.py`""
$hookCmd       = "$pyCommand `"$installDirForward/objective-hook.py`" 2>/dev/null || true"

# Python does the merge. PowerShell's PSCustomObject array handling is brittle
# and easy to clobber neighboring hooks with. Values travel in environment
# variables so embedded quotes and backslashes can't break the Python source.
$env:BARKEEP_SETTINGS_PATH  = $settingsPath
$env:BARKEEP_STATUSLINE_CMD = $statuslineCmd
$env:BARKEEP_HOOK_CMD       = $hookCmd

$mergeScript = @'
import json, os, shutil, sys, time

path = os.environ["BARKEEP_SETTINGS_PATH"]
new_status_cmd = os.environ["BARKEEP_STATUSLINE_CMD"]
new_hook_cmd = os.environ["BARKEEP_HOOK_CMD"]


def fail(message):
    print("  ERROR: " + message)
    sys.exit(1)


exists = os.path.exists(path)
settings = {}
had_content = False
if exists:
    try:
        # utf-8-sig also reads the BOM that Windows PowerShell 5.1 likes to add.
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = f.read()
    except (OSError, ValueError) as e:
        fail("Could not read settings.json as UTF-8, so it was left as is: " + str(e))
    if raw.strip():
        had_content = True
        try:
            settings = json.loads(raw)
        except ValueError as e:
            fail("settings.json is not valid JSON, so it was left as is: " + str(e))
        if not isinstance(settings, dict):
            fail("settings.json does not hold a JSON object, so it was left as is.")

before = json.dumps(settings, sort_keys=True)

# statusLine: set the two fields we own, keep anything else in there (padding, say).
status = settings.get("statusLine")
previous_status = status.get("command") if isinstance(status, dict) else status
if not isinstance(status, dict):
    status = {}
    settings["statusLine"] = status
status["type"] = "command"
status["command"] = new_status_cmd

# UserPromptSubmit hooks: repoint an existing objective-hook entry, or append one.
# Every other hook and event stays exactly as it was.
hooks = settings.setdefault("hooks", {})
if not isinstance(hooks, dict):
    fail("'hooks' in settings.json is not an object, so the file was left as is.")
ups = hooks.setdefault("UserPromptSubmit", [])
if not isinstance(ups, list):
    fail("'hooks.UserPromptSubmit' in settings.json is not a list, so the file was left as is.")

found = False
for outer in ups:
    inner_hooks = outer.get("hooks") if isinstance(outer, dict) else None
    if not isinstance(inner_hooks, list):
        continue
    for inner in inner_hooks:
        if isinstance(inner, dict) and "objective-hook.py" in str(inner.get("command", "")):
            inner["command"] = new_hook_cmd
            found = True
if not found:
    ups.append({"hooks": [{"type": "command", "command": new_hook_cmd}]})

if had_content and json.dumps(settings, sort_keys=True) == before:
    print("  settings.json already set up. Left it unchanged.")
    sys.exit(0)

try:
    if exists:
        backup = path + ".barkeep-backup-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, backup)
        print("  Backed up settings.json to " + os.path.basename(backup))
    # Write beside the real file, then swap, so a failure can't leave half a file.
    tmp = path + ".barkeep-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    with open(path, "r", encoding="utf-8") as f:
        written = json.load(f)
except (OSError, ValueError) as e:
    fail("Could not write settings.json: " + str(e))

if written != settings:
    fail("settings.json did not read back as written.")

print("  " + ("Updated" if exists else "Created") + " settings.json")
print("  [hooks] UserPromptSubmit: " + ("updated existing objective-hook entry" if found else "appended new objective-hook entry"))
if previous_status and previous_status != new_status_cmd and "barkeep" not in str(previous_status):
    print("  Replaced your previous statusLine command. The backup has it if you want it back.")
'@

$mergeScript | & $python.Exe @pyArgs -
$mergeExit = $LASTEXITCODE

$env:BARKEEP_SETTINGS_PATH  = $null
$env:BARKEEP_STATUSLINE_CMD = $null
$env:BARKEEP_HOOK_CMD       = $null

if ($mergeExit -ne 0) {
    Stop-Install "The files are in $installDir, but $settingsPath was not updated, so Claude Code won't show the bar. See the error above, fix it, and run this again."
}

# Prove the configured status line runs before calling this a success.
$bar = '{}' | & $python.Exe @pyArgs (Join-Path $installDir "statusline.py")
if ($LASTEXITCODE -ne 0 -or -not $bar) {
    Stop-Install "The status line failed its test run, so the bar won't work yet. See any error above, fix it, and run this again."
}

Write-Host ""
Write-Host "  Barkeep v2 installed at: $installDir" -ForegroundColor Green
Write-Host ""
Write-Host "  Restart Claude Code to see the new status bar." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Default variant: statusline.py (full)" -ForegroundColor Gray
Write-Host "  Manage segments:" -ForegroundColor Gray
Write-Host "    $pyCommand `"$installDir\manage.py`" list" -ForegroundColor Gray
Write-Host "    $pyCommand `"$installDir\manage.py`" enable <segment>" -ForegroundColor Gray
if (Test-Path -LiteralPath $v1Dir) {
    Write-Host ""
    Write-Host "  Your v1 install at $v1Dir is untouched. To go back to it," -ForegroundColor Gray
    Write-Host "  point the statusLine and objective-hook.py entries in settings.json at that folder." -ForegroundColor Gray
}
Write-Host ""
