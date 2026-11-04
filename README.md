# Small Magics

A collection of small quality-of-life tools, automations, and device tricks. Not big architecture projects. Just the little things that make daily workflows better.

Each module is independent and self-contained. Install only what you want.

## Modules

### [Barkeep](barkeep/) -- Claude Code Status Bar

A zero-token-overhead status bar for Claude Code showing objectives, context window usage, total token burn, and git status, with optional segments for model, effort, cache, and weekly rate limits. Every segment can be switched on, off, or reordered with a small CLI. Two variants: full (Windows default) and light (WSL/Linux default, with a gradient project name in tmux).

```powershell
# Windows
git clone https://github.com/sky-salsa/small-magics.git
cd small-magics\barkeep
powershell -ExecutionPolicy Bypass -File install.ps1
```

```bash
# WSL / Linux
git clone https://github.com/sky-salsa/small-magics.git /tmp/small-magics
bash /tmp/small-magics/barkeep/install.sh
```

v2 installs alongside any v1 you already have. The [Barkeep README](barkeep/README.md) has the details.

### [Hand-Down, Hand-Up, and North Star](skills/) -- Claude Code Skills

Three Claude Code skills. `/hand-down` and `/hand-up` carry a project across `/clear`, `/compact`, or a brand new session. `/hand-down` saves where things stand: an index of the project's docs, a state file, a learning log, and a pointer in `CLAUDE.md`. `/hand-up` makes the next agent read all of it in full before it touches anything. `/north-star` holds the rest of the conversation to one principle: don't accept a belief or theory as true until it's abundantly verified.

```bash
# WSL / Linux (skip the clone if you already have one)
git clone https://github.com/sky-salsa/small-magics.git /tmp/small-magics
mkdir -p ~/.claude/skills
cp -r /tmp/small-magics/skills/hand-down /tmp/small-magics/skills/hand-up /tmp/small-magics/skills/north-star ~/.claude/skills/
```

```powershell
# Windows (skip the clone if you already have one)
git clone https://github.com/sky-salsa/small-magics.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse small-magics\skills\hand-down, small-magics\skills\hand-up, small-magics\skills\north-star "$HOME\.claude\skills\"
```

Start a new Claude Code session to pick them up, then use `/hand-down`, `/hand-up`, and `/north-star`.

A couple of things you'll notice inside: the skills were written for Sky, so they mention him by name. `service files/skill log/` in `hand-down` ships empty. It's where the skill keeps notes on its own issues as you use it.

### [System Inputs](system-inputs/) -- Ring + Mouse + ShareX Remapping

AutoHotkey v2 script that turns a Bluetooth ring and mouse side buttons into a keyboard-free control surface for voice dictation, desktop navigation, and screenshot shortcuts on Windows 11.

```powershell
git clone https://github.com/sky-salsa/small-magics.git
cd small-magics/system-inputs
powershell -ExecutionPolicy Bypass -File install.ps1
```

## Requirements

- **Barkeep**: Python 3.7 or newer (stdlib only)
- **Hand-Down, Hand-Up, and North Star**: Claude Code
- **System Inputs**: Windows 11, AutoHotkey v2, a Bluetooth ring, Logitech mouse with G Hub

## License

MIT. Barkeep includes segments ported from [jftuga/claude-statusline](https://github.com/jftuga/claude-statusline), also MIT. See [its notice](barkeep/THIRD_PARTY_NOTICES.md).
