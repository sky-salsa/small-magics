# System Inputs Config -- Ring + Mouse + ShareX Remapping

A single AutoHotkey v2 script that turns a cheap Bluetooth ring and a Logitech mouse into a keyboard-free control surface for voice dictation, desktop navigation, and app shortcuts on Windows 11.

## What It Does

Three input layers, one script:

1. **Bluetooth ring** (any 3-button ring that sends media keys in Music Mode) -- remapped to voice input toggle, Enter, and pane/window manager
2. **Mouse side buttons** (Logitech G305 or similar, mapped to F16/F17 via G Hub onboard profile) -- tap/double-tap/hold gestures for desktop switching, Enter, and voice push-to-talk
3. **ShareX hotkey relay** -- Win+Shift+W/A/D intercepted and relayed as F13/F14/F15 (Windows blocks these combos at the OS level)

## Button Map

### Ring (Music Mode)

| Button | Action |
|--------|--------|
| Center | Toggle voice input (double-tap Ctrl+Win to start, single to stop) |
| Up | Enter (submit prompts) |
| Down | Ctrl+Space (pane manager toggle with refocus) |

### Mouse Side Buttons (Normal)

| Button | Tap | Double-tap (200ms) | Hold (>300ms) |
|--------|-----|--------------------|---------------|
| Side 1 / F16 | Desktop left | Pane manager toggle | (available) |
| Side 2 / F17 | Desktop right | Enter | Voice push-to-talk |

### Mouse G-Shift Layer (hold DPI + side button)

| Button | Action |
|--------|--------|
| G-Shift + Side 1 / F18 | Pane manager toggle |
| G-Shift + Side 2 / F19 | Double-tap Alt |

### ShareX Relay

| Shortcut | Sends | ShareX Action |
|----------|-------|---------------|
| Win+Shift+W | F13 | Capture active window |
| Win+Shift+A | F14 | Capture region, copy file path |
| Win+Shift+D | F15 | Capture region, Save As |

## Prerequisites

- **Windows 11**
- **AutoHotkey v2**: `winget install AutoHotkey.AutoHotkey`
- **Bluetooth ring** paired and set to Music Mode (hold Up+Down until 3 purple LED flashes)
- **Logitech G Hub** (for initial mouse config only, not needed at runtime):
  - Side button 1 -> F16
  - Side button 2 -> F17
  - G-Shift + Side 1 -> F18
  - G-Shift + Side 2 -> F19
  - DPI button -> Middle click
  - Save to onboard profile

## Install

```powershell
# Clone and run the installer
git clone https://github.com/sky-salsa/small-magics.git
cd small-magics/system-inputs
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer creates startup and desktop shortcuts with Run as Administrator (needed for hotkeys to work in elevated windows). You'll get a UAC prompt on each login.

Or just run the script directly:

```
AutoHotkey.exe system-inputs-config.ahk
```

## Customization

The script is meant to be forked and customized. Key things you might change:

- **Voice input hotkey**: The script sends Ctrl+Win for Wispr Flow. Change the `SendInput` lines in the center button handler if your voice app uses a different hotkey.
- **Pane manager window title**: The refocus logic checks for `WinActive("Pane Management")`. Change this string to match your window manager.
- **F16 hold action**: Currently unmapped. Add your own action in the `f16Held` block.
- **Debug logging**: Set `DEBUG := false` at the top to disable logging.

## F-Key Allocation

| Range | Assignment |
|-------|-----------|
| F13-F15 | ShareX relay |
| F16-F17 | Mouse side buttons (normal) |
| F18-F19 | Mouse side buttons (G-Shift) |
| F20+ | Available |

## Known Limitations

- Ring drops rapid presses (<300ms apart) at the firmware level. This is a hardware limitation. AHK handlers are kept non-blocking to avoid compounding it.
- The voice input toggle (ring center) tracks state in a variable that can desync if a tap is missed. The mouse hold (push-to-talk) doesn't have this problem.
- G Hub must NOT auto-start. It's only needed to change onboard profiles. If someone launches it and changes the profile, the F16-F19 mappings break.
- AHK must run as admin to inject keys into elevated windows. This means a UAC prompt on every login.

## Files

| File | Purpose |
|------|---------|
| `system-inputs-config.ahk` | The script |
| `install.ps1` | Creates startup + desktop shortcuts |
| `README.md` | This file |
