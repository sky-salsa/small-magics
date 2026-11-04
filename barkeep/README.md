# Barkeep v2 — Modular Claude Code Status Bar

Zero-token-overhead status bar for Claude Code. v2's headline change: every segment is a self-contained module you can swap in or out via a small CLI. New segments (model badge, effort, cache, 7-day rate limit, reset countdown, reset clock time) ship alongside the originals; both Sky's plain context bar and jftuga's tiered/colored bar coexist as separate options. If you have v1 installed, it stays untouched on disk.

## Install

### Windows (PowerShell 7)

```powershell
git clone https://github.com/sky-salsa/small-magics.git
cd small-magics\barkeep
pwsh -File install.ps1
```

Two things to know on Windows:

- **It needs PowerShell 7 (`pwsh`).** The installer does not run under Windows PowerShell 5.1, the version that ships with Windows. `winget install Microsoft.PowerShell` gets you PowerShell 7.
- **`~/.claude/settings.json` has to exist first.** If you don't have one yet, create it with `{}` as its only contents, then run the installer.

The `irm | iex` one-liner from v1 no longer works. The installer copies files from the folder it sits in, so it has to run from a clone.

### WSL / Linux / macOS

```bash
git clone https://github.com/sky-salsa/small-magics.git /tmp/small-magics
bash /tmp/small-magics/barkeep/install.sh
```

Both installers write to `~/.claude/extensions/barkeep-v2/` (NOT `~/.claude/extensions/barkeep/`, which is v1's home). They update `~/.claude/settings.json` to point Claude Code's `statusLine` and `UserPromptSubmit` hook at the v2 scripts, and leave your other hooks alone. **Restart Claude Code** after install.

The Windows installer sets up the full variant. The WSL / Linux / macOS installer sets up the light variant. To switch, change `statusline.py` to `statusline-light.py` (or the reverse) in `settings.json`.

## Segment catalog

Each segment is a discrete render function in `segments.py`. The author tag tracks origin so two competing variants of the same idea (e.g., context bars from different folks) can coexist.

| Segment | Author | Default (full / light) | What it shows |
|---|---|---|---|
| `objective` | -skysalsa | ✓ / – | `🫧 Objective → <text>` |
| `directory` | -skysalsa | ✓ / – | working directory basename |
| `project_gradient` | -skysalsa | – / ✓ | drifting-gradient project name (uses tmux pane path, hidden outside tmux) |
| `context_bar` | -skysalsa | ✓ / ✓ | `▓▓▓▓░░░░░░ 41%` (Claude orange, 10-char) |
| `context_bar_tiered` | -jftuga | – / – | 20-char bar, tier-colored (green/yellow/orange/red) |
| `ttu` | -skysalsa | ✓ / ✓ | `TTU: 45.2k` (input + output cumulative) |
| `model` | -jftuga | – / – | `◈ Op 4.7(1m)` (compacted model name, strips "Claude " prefix) |
| `effort` | -jftuga | – / – | `(high)` |
| `cache` | -jftuga | – / – | `⦿ 12k cached` (hidden when 0) |
| `rate_7d` | -jftuga | – / – | `7d: 36%/61%` (used / share of the week elapsed, so you can see if you're ahead of pace) |
| `rate_reset` | -jftuga | – / – | `⟳ 2d4h` countdown to 7-day reset |
| `rate_reset_at` | -skysalsa | – / – | `⟳ Wed 5am` clock time of the 7-day reset, local tz (drops `:00` on the hour) |
| `git` | -skysalsa | ✓ / ✓ | branch + dirty file counts |
| `_dump_payload` | -skysalsa | – / – | DEV: writes raw stdin to `debug-payload.json` |

`project_gradient` uses the tmux pane's folder name. It can also read display names from a settings file: set `BARKEEP_PANE_SETTINGS` to its path.

## Manage segments

Run these from the install dir, `~/.claude/extensions/barkeep-v2/`. On Linux / WSL use `python3` instead of `python`.

Commands act on the full variant unless you say otherwise. If you're on the light variant (the WSL / Linux / macOS default), add `--variant=light` or your changes won't show up.

```
python manage.py list                         # see what's enabled in the full variant
python manage.py list --variant=light         # same for the light variant
python manage.py list --show-dev              # include dev segments

python manage.py enable model effort cache    # add multiple at once (appends to end)
python manage.py disable git
python manage.py move model --before objective
python manage.py order model objective directory context_bar ttu git
python manage.py reset                        # restore variant defaults
python manage.py --version
```

Edits persist to `barkeep-config.json` next to the installed script. The installer preserves it on upgrade.

Sample `list` output:

```
Barkeep segments — variant: full

  Enabled (in display order):
  [x] objective           (-skysalsa)  Current session objective
  [x] directory           (-skysalsa)  Working directory name
  [x] context_bar         (-skysalsa)  Context window % bar (Claude orange, 10-char)
  [x] ttu                 (-skysalsa)  Total tokens used this session (input + output)
  [x] git                 (-skysalsa)  Branch + dirty file counts

  Available (disabled):
  [ ] project_gradient    (-skysalsa)  Gradient-colored project name (tmux pane lookup)
  [ ] rate_reset_at       (-skysalsa)  Weekly rate limit reset as a clock time (e.g. 'Wed 5am')
  [ ] model               (-jftuga)    Active model badge (Opus/Sonnet/Haiku)
  [ ] effort              (-jftuga)    Thinking effort level
  [ ] cache               (-jftuga)    Cache read tokens (hidden when 0)
  [ ] context_bar_tiered  (-jftuga)    Tiered-color 20-char context bar (green→yellow→orange→red)
  [ ] rate_7d             (-jftuga)    7-day rate limit % usage
  [ ] rate_reset          (-jftuga)    Countdown to 7-day rate limit reset

  Order: objective | directory | context_bar | ttu | git
```

## Setting objectives

Same as v1:

- Type `objective: fix the login redirect` in chat → sets the objective (message intercepted by hook, never reaches Claude).
- Type `objective: clear` → clears it.
- Or ask Claude to set it; Claude can call `python set-objective.py "..."` directly.

Objectives are session-scoped. Persisted in `objectives.json`. The `objective` segment is off by default in the light variant, so enable it there if you want to see them.

## Schema verification protocol

If Claude Code's stdin payload schema changes and a segment stops rendering correctly:

```
python manage.py enable _dump_payload
```

Send any message in Claude Code. The next render writes the raw stdin JSON to `debug-payload.json` in the install dir. Inspect it, compare to what the segment expects, fix the field path. Then:

```
python manage.py disable _dump_payload
```

## Authoring a new segment

1. Add a render function `render_xyz(data, ctx) -> str | None` to `segments.py`. Return `None` to hide the segment for this render.
2. Register it in the `SEGMENTS` dict with `render`, `desc`, `author`, `default_full`, `default_light`.
3. The segment appears immediately in `python manage.py list`. Enable to display.

`ctx` carries pre-extracted fields (`cwd`, `data`) and color codes for both the 24-bit truecolor palette (skysalsa-style) and the 256-color palette (jftuga-style). Mix freely — terminals handle both.

## How it works

Claude Code's `statusLine` config invokes `statusline.py` (or `statusline-light.py`) once per assistant message, piping session JSON to stdin. The script:

1. Loads `barkeep-config.json` to get the enabled segment list for this variant.
2. Iterates the list, calls each segment's render function, collects non-`None` outputs.
3. Joins with a pipe separator and prints to stdout.

No background process, no daemon, no pip packages. Python 3 stdlib only.

## Uninstall

Remove `~/.claude/extensions/barkeep-v2/`, then take the `statusLine` entry and the `objective-hook.py` hook entry out of `~/.claude/settings.json`.

## Files

| File | Purpose |
|---|---|
| `statusline.py` | Full variant entry point |
| `statusline-light.py` | Light variant (project gradient, no objective/dir) |
| `segments.py` | All render functions + the `SEGMENTS` registry |
| `barkeep_config.py` | Config load/save helpers |
| `manage.py` | CLI for toggling segments and reordering |
| `set-objective.py` | CLI Claude uses to set objectives |
| `objective-hook.py` | UserPromptSubmit hook that intercepts `objective:` messages |
| `barkeep-config.default.json` | Seed file copied to `barkeep-config.json` on first install |
| `install.ps1` / `install.sh` | Installers |
| `tests/sample-payload.json` | Canned stdin for offline rendering tests |
| `CHANGELOG.md` | Version history |
| `THIRD_PARTY_NOTICES.md` | License for the ported jftuga segments |

## Coexistence with v1

v2 lives at `~/.claude/extensions/barkeep-v2/`. v1 stays at `~/.claude/extensions/barkeep/`. The active statusline is whichever one `~/.claude/settings.json` points at. To go back to v1, point the `statusLine` and `objective-hook.py` entries in `settings.json` back at v1's folder.

## Out of scope (deferred)

- Continuous animation of `project_gradient`. The `statusLine` slot in Claude Code is one-shot per assistant message; smooth animation requires moving the bar to a tmux/WezTerm status line, which is a separate project.
- Cost segment, 5-hour rate limit, vim mode badge, agent name. All available in the stdin schema; trivial to add as new segments when needed.

## Credits

Segments tagged `-jftuga` are ported from [jftuga/claude-statusline](https://github.com/jftuga/claude-statusline) under the MIT License. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
