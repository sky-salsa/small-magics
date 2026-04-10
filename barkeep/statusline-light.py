#!/usr/bin/env python3
"""Barkeep Light -- minimal Claude Code statusline for tmux/WSL.

Shows context window usage, total token burn, and git branch/status.
No objectives, no directory segment. Just the metrics.

Project name is resolved from the tmux pane's working directory. If you
use pane-management (https://github.com/sky-salsa/pane-management), it
will pick up display_name overrides from the pane-management settings.
"""

import json
import subprocess
import sys
import os
import io
import time

# Optional: pane-management settings path for display_name overrides.
# On Windows (via WSL /mnt/c/), this is typically:
#   /mnt/c/Users/<YOU>/AppData/Roaming/com.pane-management.app/settings.json
# On native Linux/macOS:
#   ~/.config/com.pane-management.app/settings.json
# Set to None to skip display_name lookups entirely.
PANE_SETTINGS = os.environ.get(
    "BARKEEP_PANE_SETTINGS",
    os.path.expanduser("~/.config/com.pane-management.app/settings.json")
)


def get_project_name():
    """Look up project display name using tmux's live pane path."""
    try:
        # Get live working directory from THIS pane (not the active one)
        pane_id = os.environ.get("TMUX_PANE", "")
        cmd = ["tmux", "display-message", "-p", "#{pane_current_path}"]
        if pane_id:
            cmd = ["tmux", "display-message", "-t", pane_id, "-p", "#{pane_current_path}"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=2
        )
        if result.returncode != 0:
            return None
        pane_path = result.stdout.strip()
        if not pane_path:
            return None

        # Convert path to encoded name (replace / with -, drop leading slash)
        encoded = pane_path.replace("/", "-").replace(" ", "-").replace("_", "-")

        # Check project_meta for a display_name
        if PANE_SETTINGS:
            try:
                with open(PANE_SETTINGS, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                meta = settings.get("project_meta", {}).get(encoded, {})
                display = meta.get("display_name")
                if display:
                    return display
            except Exception:
                pass

        # Fall back to last meaningful path segment(s)
        parts = [p for p in pane_path.split("/") if p]
        return parts[-1] if parts else None
    except Exception:
        return None


def get_git_status(cwd):
    """Get git branch and dirty counts. Returns None if not a repo."""
    if cwd == "?":
        return None
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, capture_output=True, text=True, timeout=3
        )
        if branch.returncode != 0:
            return None
        branch_name = branch.stdout.strip() or "HEAD"

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, timeout=5
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
            else:
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


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("[barkeep-light: no data]")
        return

    # --- Context window ---
    ctx = data.get("context_window", {})
    pct = int(float(ctx.get("used_percentage", 0) or 0))

    # --- Token burn ---
    total_in = ctx.get("total_input_tokens", 0) or 0
    total_out = ctx.get("total_output_tokens", 0) or 0
    ttu = total_in + total_out
    if ttu >= 1_000_000:
        ttu_str = f"{ttu / 1_000_000:.1f}M"
    elif ttu >= 1_000:
        ttu_str = f"{ttu / 1_000:.1f}k"
    else:
        ttu_str = str(ttu)

    # --- Git ---
    cwd = data.get("workspace", {}).get("current_dir", data.get("cwd", "?"))
    git_info = get_git_status(cwd)

    # --- Colors ---
    ORANGE = "\033[38;2;215;119;87m"
    GRAY = "\033[38;2;136;136;136m"
    LIGHT = "\033[38;2;180;180;180m"
    GREEN = "\033[38;2;120;200;120m"
    RED = "\033[38;2;220;100;100m"
    RESET = "\033[0m"

    # Context bar (10 wide)
    bar_width = 10
    filled = pct * bar_width // 100
    bar = "\u2593" * filled + "\u2591" * (bar_width - filled)

    pipe = f" {GRAY}\u2502{RESET} "

    # Git segment
    git_seg = ""
    if git_info:
        b = git_info["branch"]
        s, m, d, u = git_info["staged"], git_info["modified"], git_info["deleted"], git_info["untracked"]
        dirty = s + m + d + u
        if dirty > 0:
            parts = []
            if s: parts.append(f"{GREEN}+{s}{RESET}")
            if m: parts.append(f"{ORANGE}~{m}{RESET}")
            if d: parts.append(f"{RED}-{d}{RESET}")
            if u: parts.append(f"{GRAY}?{u}{RESET}")
            git_seg = f"{LIGHT}\uf126 {b}{RESET} ({' '.join(parts)})"
        else:
            git_seg = f"{GREEN}\uf126 {b} \u2714{RESET}"

    # Project name with drifting gradient (shifts each refresh)
    project = get_project_name()
    project_seg = ""
    if project:
        # Gradient stops: deep blue -> lavender -> burnt sunset orange
        stops = [
            ( 65, 105, 205),
            (170, 120, 190),
            (200,  82,  45),
        ]

        def lerp_color(stops, t):
            """Interpolate through color stops at position t (0.0-1.0)."""
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

        # Time-based offset: full cycle every 60 seconds
        phase = (time.time() % 60) / 60.0

        chars = list(project)
        n = max(len(chars) - 1, 1)
        gradient_parts = []
        for i, ch in enumerate(chars):
            t = (i / n * 0.8 + phase) % 1.0
            r, g, b = lerp_color(stops, t)
            gradient_parts.append(f"\033[38;2;{r};{g};{b}m{ch}")
        project_seg = f"\U0001fae7 {''.join(gradient_parts)}{RESET}{pipe}"

    # Assemble: project | context | TTU | git
    line = (
        f"{project_seg}"
        f"{ORANGE}{bar} {pct}%{RESET}"
        f"{pipe}"
        f"{LIGHT}TTU {ORANGE}{ttu_str}{RESET}"
    )
    if git_seg:
        line += f"{pipe}{git_seg}"

    print(line)


if __name__ == "__main__":
    main()
