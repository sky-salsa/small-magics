"""Barkeep v2 segment registry.

Each segment is a render function `(data, ctx) -> str | None`. Returning
None hides the segment for this render. The SEGMENTS dict maps names to
{render, desc, author, default_full, default_light}; declaration order
is canonical for `manage.py list` output.

DEFAULT_FULL_ORDER / DEFAULT_LIGHT_ORDER define the seed enable lists
the installer copies into barkeep-config.json on first install.
"""

import json
import os
import re
import subprocess
import time

# Bump on every release; keep in step with CHANGELOG.md's top entry.
# Reported by `manage.py --version`.
__version__ = "2.1.0"

# Family-name → short prefix used by render_model to compact display names.
# Match is case-insensitive and anchored at the start of the (post-"Claude ")
# display name. Order doesn't matter; longest-prefix-wins behavior would be
# nice but isn't needed since families are non-overlapping.
MODEL_SHORTHANDS = {
    "opus": "Op",
    "sonnet": "Snt",
    "haiku": "Hku",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECTIVES_FILE = os.path.join(SCRIPT_DIR, "objectives.json")
SESSION_FILE = os.path.join(SCRIPT_DIR, "current_session.txt")
DEBUG_DUMP_FILE = os.path.join(SCRIPT_DIR, "debug-payload.json")
PANE_SETTINGS = os.environ.get(
    "BARKEEP_PANE_SETTINGS",
    os.path.expanduser("~/.config/com.pane-management.app/settings.json")
)

MAX_OBJECTIVE_LEN = 80


# ─── Render context ─────────────────────────────────────────────────────────

def build_context(data):
    """Build the per-render context shared across segments. Holds colors and
    a few pre-extracted fields useful to multiple segments."""
    cwd = data.get("workspace", {}).get("current_dir", data.get("cwd", "?"))
    return {
        "data": data,
        "cwd": cwd,
        # 24-bit truecolor palette (skysalsa segments)
        "ORANGE": "\033[38;2;215;119;87m",       # Claude orange #D77757
        "GRAY": "\033[38;2;136;136;136m",
        "LIGHT_GRAY": "\033[38;2;180;180;180m",
        "WHITE": "\033[97m",
        "GREEN": "\033[38;2;120;200;120m",
        "RED": "\033[38;2;220;100;100m",
        # 256-color palette (jftuga segments — match his original look)
        "C141": "\033[38;5;141m",   # cyan-ish (model badge, effort)
        "C183": "\033[38;5;183m",   # bright magenta (model name)
        "C220": "\033[38;5;220m",   # bright yellow (cache bolt)
        "C179": "\033[38;5;179m",   # olive (cache count)
        "C108": "\033[38;5;108m",   # cyan (low-tier rate)
        "C222": "\033[38;5;222m",   # yellow (mid-tier rate)
        "C209": "\033[38;5;209m",   # orange (high-tier ctx)
        "C196": "\033[38;5;196m",   # red (crit-tier rate)
        "C245": "\033[38;5;245m",   # dim grey (reset symbol)
        # Palette pulled from the project_gradient stops — used for all
        # non-git, non-context-bar, non-project segments + the pipe separator.
        # Static (not rotating) so the bar feels anchored to the left-edge
        # gradient without animating elsewhere.
        "PAL_BLUE":       "\033[38;2;65;105;205m",   # gradient stop 0
        "PAL_LAVENDER":   "\033[38;2;170;120;190m",  # gradient stop 1
        "PAL_BURNT":      "\033[38;2;200;82;45m",    # gradient stop 2
        "PAL_PERIWINKLE": "\033[38;2;117;112;197m",  # midpoint stop0↔stop1
        "PAL_ROSE":       "\033[38;2;185;101;117m",  # midpoint stop1↔stop2
        "RESET": "\033[0m",
    }


# ─── Helpers (used by multiple segments) ────────────────────────────────────

def _save_session_id(session_id):
    """Write the active session ID so set-objective.py can scope writes."""
    if not session_id:
        return
    try:
        tmp = SESSION_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(session_id)
        os.replace(tmp, SESSION_FILE)
    except OSError:
        pass


def _read_objective(session_id):
    """Return (status, text). status ∈ {'set', 'clear', 'tbd'}."""
    if not session_id or not os.path.exists(OBJECTIVES_FILE):
        return ("tbd", None)
    try:
        with open(OBJECTIVES_FILE, "r", encoding="utf-8") as f:
            objectives = json.load(f)
        entries = objectives.get(session_id, [])
        if not entries:
            return ("tbd", None)
        last = entries[-1]
        if last.get("action") == "clear":
            return ("clear", None)
        text = last.get("objective", "")
        if not text:
            return ("tbd", None)
        if len(text) > MAX_OBJECTIVE_LEN:
            text = text[:MAX_OBJECTIVE_LEN - 1] + "…"
        return ("set", text)
    except (OSError, json.JSONDecodeError):
        return ("tbd", None)


def _git_status(cwd):
    """Branch + dirty counts. None if not a repo or git unavailable."""
    if cwd == "?":
        return None
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, capture_output=True, text=True, timeout=3,
        )
        if branch.returncode != 0:
            return None
        branch_name = branch.stdout.strip() or "HEAD"
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        staged = modified = deleted = untracked = 0
        for line in result.stdout.splitlines():
            if len(line) < 2:
                continue
            ix, wt = line[0], line[1]
            if line.startswith("??"):
                untracked += 1
                continue
            if ix in "MADR":
                staged += 1
            if wt in "MD":
                modified += 1
            if wt == "D":
                deleted += 1
        return {
            "branch": branch_name,
            "staged": staged,
            "modified": modified,
            "deleted": deleted,
            "untracked": untracked,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _tmux_pane_path():
    """Live path of the tmux pane this script is running in."""
    try:
        pane_id = os.environ.get("TMUX_PANE", "")
        cmd = ["tmux", "display-message", "-p", "#{pane_current_path}"]
        if pane_id:
            cmd = ["tmux", "display-message", "-t", pane_id, "-p",
                   "#{pane_current_path}"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _project_display_name():
    """Resolve project display name via tmux pane + pane-management settings."""
    pane_path = _tmux_pane_path()
    if not pane_path:
        return None
    encoded = pane_path.replace("/", "-").replace(" ", "-").replace("_", "-")
    if PANE_SETTINGS and os.path.exists(PANE_SETTINGS):
        try:
            with open(PANE_SETTINGS, "r", encoding="utf-8") as f:
                settings = json.load(f)
            meta = settings.get("project_meta", {}).get(encoded, {})
            display = meta.get("display_name")
            if display:
                return display
        except (OSError, json.JSONDecodeError):
            pass
    parts = [p for p in pane_path.split("/") if p]
    return parts[-1] if parts else None


def _format_tokens(n):
    """45200 -> '45.2k', 1_500_000 -> '1.5M'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _format_duration(seconds):
    """Seconds remaining -> 'XdYh' if ≥1d else 'XhYm'. Negative -> '0h0m'."""
    if seconds <= 0:
        return "0h0m"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days >= 1:
        return f"{days}d{hours}h"
    return f"{hours}h{minutes}m"


def _format_wallclock(ts):
    """Epoch -> local 'Wed 5am', or 'Wed 5:30am' when off the hour.

    Minutes are dropped on the hour to save bar width — resets have always
    landed on the hour so far, but don't assume it. Renders in the machine's
    local zone, which is the whole point:
    a wall-clock reset time is only useful in the reader's own timezone.
    """
    lt = time.localtime(ts)
    hour12 = lt.tm_hour % 12 or 12
    meridiem = "am" if lt.tm_hour < 12 else "pm"
    day = time.strftime("%a", lt)
    if lt.tm_min:
        return f"{day} {hour12}:{lt.tm_min:02d}{meridiem}"
    return f"{day} {hour12}{meridiem}"


# ─── Segment renderers (skysalsa) ───────────────────────────────────────────

def render_objective(data, ctx):
    session_id = data.get("session_id", "")
    _save_session_id(session_id)
    status, text = _read_objective(session_id)
    label = f"{ctx['WHITE']}\U0001fae7 Objective → {ctx['RESET']}"
    if status == "set":
        return f"{label}{ctx['ORANGE']}{text}{ctx['RESET']}"
    if status == "clear":
        return label
    return f"{label}{ctx['GRAY']}TBD{ctx['RESET']}"


def render_directory(data, ctx):
    cwd = ctx["cwd"]
    if cwd == "?":
        return None
    name = os.path.basename(cwd) or cwd
    return f"{ctx['LIGHT_GRAY']}{name}{ctx['RESET']}"


def render_project_gradient(data, ctx):
    project = _project_display_name()
    if not project:
        return None
    # Append the tmux pane id (e.g., "%7") inline if available — same gradient,
    # space-separated. Treated as part of the same visual unit, not a separate
    # piped segment, so adjacent chars share the gradient continuum.
    pane_id = os.environ.get("TMUX_PANE", "")
    text = f"{pane_id} {project}" if pane_id else project

    stops = [(65, 105, 205), (170, 120, 190), (200, 82, 45)]

    def lerp(t):
        t = t % 1.0
        seg_count = len(stops) - 1
        seg = min(int(t * seg_count), seg_count - 1)
        local_t = (t * seg_count) - seg
        r0, g0, b0 = stops[seg]
        r1, g1, b1 = stops[seg + 1]
        return (
            int(r0 + (r1 - r0) * local_t),
            int(g0 + (g1 - g0) * local_t),
            int(b0 + (b1 - b0) * local_t),
        )

    phase = (time.time() % 60) / 60.0
    chars = list(text)
    n = max(len(chars) - 1, 1)
    parts = []
    for i, ch in enumerate(chars):
        t = (i / n * 0.8 + phase) % 1.0
        r, g, b = lerp(t)
        parts.append(f"\033[38;2;{r};{g};{b}m{ch}")
    return f"\U0001fae7 {''.join(parts)}{ctx['RESET']}"


def render_context_bar(data, ctx):
    """skysalsa: simple 10-char Claude-orange bar."""
    pct = int(float(data.get("context_window", {}).get("used_percentage", 0) or 0))
    bar_width = 10
    filled = pct * bar_width // 100
    bar = "▓" * filled + "░" * (bar_width - filled)
    return f"{ctx['ORANGE']}{bar} {pct}%{ctx['RESET']}"


def render_ttu(data, ctx):
    cw = data.get("context_window", {})
    total = (cw.get("total_input_tokens", 0) or 0) + (cw.get("total_output_tokens", 0) or 0)
    return f"{ctx['LIGHT_GRAY']}TTU: {ctx['ORANGE']}{_format_tokens(total)}{ctx['RESET']}"


def render_git(data, ctx):
    info = _git_status(ctx["cwd"])
    if not info:
        return None
    b = info["branch"]
    s, m, d, u = info["staged"], info["modified"], info["deleted"], info["untracked"]
    dirty = s + m + d + u
    if dirty == 0:
        return f"{ctx['GREEN']}{b} ✔{ctx['RESET']}"
    parts = []
    if s: parts.append(f"{ctx['GREEN']}+{s}{ctx['RESET']}")
    if m: parts.append(f"{ctx['ORANGE']}~{m}{ctx['RESET']}")
    if d: parts.append(f"{ctx['RED']}-{d}{ctx['RESET']}")
    if u: parts.append(f"{ctx['GRAY']}?{u}{ctx['RESET']}")
    return f"{ctx['LIGHT_GRAY']}{b}{ctx['RESET']} ({' | '.join(parts)})"


def render_rate_reset_at(data, ctx):
    """Wall-clock day + time the weekly (7-day) rate limit rolls over.

    Sibling of jftuga's `rate_reset`, which shows the same event as a
    countdown ('2d17h') instead of a clock time ('Wed 5am'). Both are
    registered; enable whichever reads better — same coexistence pattern
    as context_bar / context_bar_tiered.
    """
    seven = data.get("rate_limits", {}).get("seven_day")
    if not seven:
        return None
    resets_at = seven.get("resets_at")
    if not resets_at:
        return None
    try:
        when = _format_wallclock(float(resets_at))
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    return f"{ctx['PAL_PERIWINKLE']}⟳ {ctx['PAL_LAVENDER']}{when}{ctx['RESET']}"


# ─── Segment renderers (jftuga ports) ───────────────────────────────────────
# Constants ported verbatim from jftuga/claude-statusline (Go) main.go.

def render_model(data, ctx):
    model = data.get("model", {})
    name = (model.get("display_name") or model.get("id") or "").strip()
    if name.lower().startswith("claude "):
        name = name[7:]
    if not name:
        return None
    # Compact: "Opus 4.7 (1M context)" -> "Op 4.7(1m)".
    short = name
    for full, abbrev in MODEL_SHORTHANDS.items():
        if short.lower().startswith(full):
            short = abbrev + short[len(full):]
            break
    short = re.sub(
        r"\s*\(([\d.]+)\s*M\s*context\)",
        lambda m: f"({m.group(1)}m)",
        short,
        flags=re.IGNORECASE,
    )
    return f"{ctx['PAL_BLUE']}◈ {ctx['PAL_LAVENDER']}{short}{ctx['RESET']}"


def render_effort(data, ctx):
    level = (data.get("effort", {}).get("level") or "").strip()
    if not level:
        return None
    return f"{ctx['PAL_PERIWINKLE']}({level}){ctx['RESET']}"


def render_cache(data, ctx):
    usage = data.get("context_window", {}).get("current_usage", {})
    cached = usage.get("cache_read_input_tokens", 0) or 0
    if cached <= 0:
        return None
    if cached >= 1000:
        count_str = f"{cached // 1000}k"
    else:
        count_str = str(cached)
    return f"{ctx['PAL_PERIWINKLE']}⦿ {count_str} cached{ctx['RESET']}"


def render_context_bar_tiered(data, ctx):
    """jftuga: 20-segment tiered-color context bar."""
    pct = int(float(data.get("context_window", {}).get("used_percentage", 0) or 0))
    bar_width = 20
    filled = pct * bar_width // 100
    if pct < 40:
        color = ctx["C108"]
    elif pct < 70:
        color = ctx["C222"]
    elif pct < 90:
        color = ctx["C209"]
    else:
        color = ctx["C196"]
    bar = "━" * filled + ("╌" * (bar_width - filled))
    return f"{color}{bar} {pct}%{ctx['RESET']}"


def render_rate_7d(data, ctx):
    """Show actual % used vs linear-pace target for the current week.

    Pace target = fraction of the 7-day window already elapsed × 100. If
    the reset is in 2d17h then ~61% of the week is gone, so 61% would be
    the "on-pace" usage line. Reading "36% / 61%" tells you whether
    you're ahead of (under) or behind (over) the pace.
    """
    seven = data.get("rate_limits", {}).get("seven_day")
    if not seven:
        return None
    pct = seven.get("used_percentage")
    if pct is None:
        return None
    pct_i = int(float(pct))

    pace_str = ""
    resets_at = seven.get("resets_at")
    if resets_at:
        try:
            seconds_until_reset = float(resets_at) - time.time()
            week_seconds = 7 * 24 * 3600
            elapsed = max(0.0, min(1.0, 1.0 - (seconds_until_reset / week_seconds)))
            pace_target = int(elapsed * 100)
            pace_str = f"/{pace_target}%"
        except (TypeError, ValueError):
            pass

    return f"{ctx['PAL_BLUE']}7d: {pct_i}%{pace_str}{ctx['RESET']}"


def render_rate_reset(data, ctx):
    seven = data.get("rate_limits", {}).get("seven_day")
    if not seven:
        return None
    resets_at = seven.get("resets_at")
    if not resets_at:
        return None
    try:
        delta = int(float(resets_at) - time.time())
    except (TypeError, ValueError):
        return None
    return f"{ctx['C245']}⟳ {ctx['LIGHT_GRAY']}{_format_duration(delta)}{ctx['RESET']}"


# ─── Dev segments ───────────────────────────────────────────────────────────

def render_dump_payload(data, ctx):
    """Dev tool: persist raw payload JSON for schema verification, render nothing."""
    try:
        with open(DEBUG_DUMP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except OSError:
        pass
    return None


# ─── Registry ────────────────────────────────────────────────────────────────
# Declaration order = canonical order for manage.py list output.

SEGMENTS = {
    # ── skysalsa originals ──
    "objective": {
        "render": render_objective,
        "desc": "Current session objective",
        "author": "skysalsa",
        "default_full": True,
        "default_light": False,
    },
    "directory": {
        "render": render_directory,
        "desc": "Working directory name",
        "author": "skysalsa",
        "default_full": True,
        "default_light": False,
    },
    "project_gradient": {
        "render": render_project_gradient,
        "desc": "Gradient-colored project name (tmux pane lookup)",
        "author": "skysalsa",
        "default_full": False,
        "default_light": True,
    },
    "context_bar": {
        "render": render_context_bar,
        "desc": "Context window % bar (Claude orange, 10-char)",
        "author": "skysalsa",
        "default_full": True,
        "default_light": True,
    },
    "ttu": {
        "render": render_ttu,
        "desc": "Total tokens used this session (input + output)",
        "author": "skysalsa",
        "default_full": True,
        "default_light": True,
    },
    "git": {
        "render": render_git,
        "desc": "Branch + dirty file counts",
        "author": "skysalsa",
        "default_full": True,
        "default_light": True,
    },
    "rate_reset_at": {
        "render": render_rate_reset_at,
        "desc": "Weekly rate limit reset as a clock time (e.g. 'Wed 5am')",
        "author": "skysalsa",
        "default_full": False,
        "default_light": False,
    },
    # ── jftuga ports ──
    "model": {
        "render": render_model,
        "desc": "Active model badge (Opus/Sonnet/Haiku)",
        "author": "jftuga",
        "default_full": False,
        "default_light": False,
    },
    "effort": {
        "render": render_effort,
        "desc": "Thinking effort level",
        "author": "jftuga",
        "default_full": False,
        "default_light": False,
    },
    "cache": {
        "render": render_cache,
        "desc": "Cache read tokens (hidden when 0)",
        "author": "jftuga",
        "default_full": False,
        "default_light": False,
    },
    "context_bar_tiered": {
        "render": render_context_bar_tiered,
        "desc": "Tiered-color 20-char context bar (green→yellow→orange→red)",
        "author": "jftuga",
        "default_full": False,
        "default_light": False,
    },
    "rate_7d": {
        "render": render_rate_7d,
        "desc": "7-day rate limit % usage",
        "author": "jftuga",
        "default_full": False,
        "default_light": False,
    },
    "rate_reset": {
        "render": render_rate_reset,
        "desc": "Countdown to 7-day rate limit reset",
        "author": "jftuga",
        "default_full": False,
        "default_light": False,
    },
    # ── dev ──
    "_dump_payload": {
        "render": render_dump_payload,
        "desc": "DEV: dump raw stdin payload to debug-payload.json (renders nothing)",
        "author": "skysalsa",
        "default_full": False,
        "default_light": False,
    },
}


DEFAULT_FULL_ORDER = [name for name, s in SEGMENTS.items() if s["default_full"]]
DEFAULT_LIGHT_ORDER = [name for name, s in SEGMENTS.items() if s["default_light"]]
