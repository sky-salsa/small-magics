# Small Magics

A collection of small quality-of-life tools, automations, and device tricks. Not big architecture projects. Just the little things that make daily workflows better.

Each module is independent and self-contained. Install only what you want.

## Modules

### [Barkeep](barkeep/) -- Claude Code Status Bar

A zero-token-overhead status bar for Claude Code showing objectives, context window usage, total token burn, and git status. Two variants: full (Windows) and light (WSL/tmux with gradient project name).

```powershell
# Windows
irm https://raw.githubusercontent.com/sky-salsa/small-magics/main/barkeep/install.ps1 | iex
```

```bash
# WSL / Linux
git clone https://github.com/sky-salsa/small-magics.git /tmp/small-magics
bash /tmp/small-magics/barkeep/install.sh
```

### [System Inputs](system-inputs/) -- Ring + Mouse + ShareX Remapping

AutoHotkey v2 script that turns a Bluetooth ring and mouse side buttons into a keyboard-free control surface for voice dictation, desktop navigation, and screenshot shortcuts on Windows 11.

```powershell
git clone https://github.com/sky-salsa/small-magics.git
cd small-magics/system-inputs
powershell -ExecutionPolicy Bypass -File install.ps1
```

## Requirements

- **Barkeep**: Python 3 (stdlib only)
- **System Inputs**: Windows 11, AutoHotkey v2, a Bluetooth ring, Logitech mouse with G Hub

## License

MIT
