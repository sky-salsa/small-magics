# Changelog

All notable changes to Barkeep v2. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning started at 2.1.0. The 2.0.0 entry below is backfilled from git
history after the fact (commits `3f81b23`..`ffaea4c`) — it was never tagged
or released under that number at the time.

## [2.1.0] — 2026-07-26

### Added
- **`rate_reset_at` segment** (`-skysalsa`). Renders the weekly (7-day) rate
  limit reset as a local wall-clock day and time — `⟳ Wed 5am` — instead of a
  countdown. Minutes are dropped when the reset falls on the hour, so an
  off-hour reset shows as `⟳ Wed 5:30am`. Reads
  `rate_limits.seven_day.resets_at` (a Unix epoch) and formats in the
  machine's local timezone, which is the point: a wall-clock reset time is
  only useful in the reader's own zone.
- Registered as a **sibling** to jftuga's `rate_reset` countdown rather than
  replacing it, following the same coexistence pattern as
  `context_bar` / `context_bar_tiered`. Both remain available.
- `__version__` in `segments.py`, reported by `manage.py --version`.
- This changelog.

### Changed
- Live light-variant bar: `cache` swapped out for `rate_reset_at` in the same
  slot, giving `(xhigh) │ ⟳ Wed 5am │ 7d: 36%/61%`. This is a user-config
  change in the install dir's `barkeep-config.json`, not a default — `cache`
  stays registered and is one `manage.py enable cache` away.

## [2.0.0] — 2026-04-27

Initial modular rewrite. Replaces v1's monolithic Python statusline with a
registry-based architecture where every visible bar element is a
self-contained, swappable module.

### Added
- Segment registry in `segments.py`. A segment is `(data, ctx) -> str | None`;
  returning `None` hides it for that render. 13 segments at this version.
- Per-segment author attribution (`-skysalsa` for originals, `-jftuga` for
  ports) surfaced in `manage.py list`.
- Segments ported from [jftuga/claude-statusline](https://github.com/jftuga/claude-statusline):
  `model`, `effort`, `cache`, `context_bar_tiered`, `rate_7d`, `rate_reset`.
- `manage.py` CLI — `list` / `enable` / `disable` / `move` / `order` / `reset`,
  persisting to `barkeep-config.json`.
- Two entry points sharing one registry, each with its own enable list:
  `statusline.py` (full) and `statusline-light.py` (tmux/WSL).
- `install.sh` / `install.ps1`, deploying to `~/.claude/extensions/barkeep-v2/`
  and leaving the v1 install untouched for rollback.
- `_dump_payload` dev segment for capturing raw stdin to `debug-payload.json`.

### Changed
- Model badge compacted: `Opus 4.7 (1M context)` → `◈ Op 4.7(1m)`;
  symbol `◆` → `◈`.
- Cache indicator: yellow `⚡` → periwinkle `⦿`.
- `rate_7d` gained a linear-pace target — `7d: 36%/61%` reads as
  "used / fraction of the week elapsed", so you can see whether you're ahead
  of or behind pace. Tier coloring dropped in favor of a flat palette hue.
- `git` segment stripped its leading Powerline branch glyph (didn't render in
  Sky's terminal) and leading space; moved to the far right of the bar.
- All non-anchor segments recolored from the `project_gradient` palette as
  static hues; pipe separators are periwinkle.
- `context_bar` dropped its trailing "context" label.
- tmux pane id prepended to `project_gradient`, sharing the same drifting
  gradient as one visual unit.

### Fixed
- Installers merge surgically into `settings.json`'s `UserPromptSubmit` array
  instead of overwriting it, preserving unrelated sibling hooks.
