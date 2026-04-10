# Barkeep -- Claude Code Status Bar

A zero-token-overhead status bar for Claude Code that displays your current objective, working directory, context window usage, and total token usage.

## Install

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/sky-salsa/small-magics/main/barkeep/install.ps1 | iex
```

### WSL / Linux (bash)

```bash
git clone https://github.com/sky-salsa/small-magics.git /tmp/small-magics
bash /tmp/small-magics/barkeep/install.sh
```

Restart Claude Code after installing.

## What You Get

Two variants included:

### `statusline.py` (Windows, full)

```
Objective -> fix the login redirect | my-project | ░░░░░░░░░░ 41% context | TTU: 45.2k |  main +2 ~1
```

| Segment | What It Shows |
|---------|--------------|
| Objective | What you're working on (set it yourself or ask Claude) |
| Directory | Current working directory name |
| Context % | How much of the context window you've used |
| TTU | Total tokens used this session (input + output) |
| Git | Branch name + dirty file counts |

### `statusline-light.py` (WSL/tmux, minimal)

```
project-name | ░░░░░░░░░░ 41% | TTU 45.2k |  main +2 ~1
```

Strips the objective and directory segments. Adds a drifting gradient on the project name. If you use [pane-management](https://github.com/sky-salsa/pane-management), it picks up project display names automatically.

Set the `BARKEEP_PANE_SETTINGS` environment variable to point to your pane-management settings file, or it defaults to `~/.config/com.pane-management.app/settings.json`.

## Setting Objectives

**Type it yourself:**
- `objective: fix the login redirect` -- sets the objective (message doesn't reach Claude)
- `objective: clear` -- clears it

**Ask Claude:**
- "Hey, set the objective to fix the login redirect"
- Claude updates the status bar directly via `set-objective.py`

Objectives are session-scoped. They don't leak across sessions.

## How It Works

Claude Code's `statusLine` config runs a command after each assistant message, piping session JSON to stdin. Barkeep reads context window stats, git status, and objective state, then prints a formatted line to stdout.

The objective system uses a `UserPromptSubmit` hook to intercept `objective:` prefixed messages before they reach Claude, blocking them from the conversation.

No pip packages. Python 3 stdlib only.

## Uninstall

Delete `~/.claude/extensions/barkeep/` and remove the `statusLine` and `UserPromptSubmit` hook entries from `~/.claude/settings.json`.

## Files

| File | Purpose |
|------|---------|
| `statusline.py` | Full status bar (Windows) |
| `statusline-light.py` | Minimal status bar (WSL/tmux) |
| `objective-hook.py` | Captures `objective:` messages from prompts |
| `set-objective.py` | CLI for Claude to set objectives programmatically |
| `install.ps1` | Windows installer |
| `install.sh` | WSL/Linux installer |
