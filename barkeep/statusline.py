#!/usr/bin/env python3
"""Claude Code statusline script -- persistent status bar.

Claude Code pipes session JSON to stdin after each assistant message.
This script reads it and prints a formatted status line to stdout.
"""

import json
import subprocess
import sys
import os
import io

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECTIVES_FILE = os.path.join(SCRIPT_DIR, "objectives.json")
SESSION_FILE = os.path.join(SCRIPT_DIR, "current_session.txt")
MAX_OBJECTIVE_LEN = 80


def get_objective(session_id):
    """Read the current objective for this session from objectives.json.

    Returns (status, text) where status is 'set', 'clear', or 'tbd'.
    """
    try:
        if not os.path.exists(OBJECTIVES_FILE) or not session_id:
            return ("tbd", None)

        with open(OBJECTIVES_FILE, "r", encoding="utf-8") as f:
            objectives = json.load(f)

        entries = objectives.get(session_id, [])
        if not entries:
            return ("tbd", None)

        last = entries[-1]
        if last.get("action") == "clear":
            return ("clear", None)

        objective = last.get("objective", "")
        if objective:
            if len(objective) > MAX_OBJECTIVE_LEN:
                objective = objective[:MAX_OBJECTIVE_LEN - 1] + "\u2026"
            return ("set", objective)

        return ("tbd", None)
    except Exception:
        return ("tbd", None)



def save_session_id(session_id):
    """Persist the current session ID so set-objective.py can read it."""
    if not session_id:
        return
    try:
        tmp = SESSION_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(session_id)
        os.replace(tmp, SESSION_FILE)
    except Exception:
        pass


def get_git_status(cwd):
    """Get git status summary for cwd. Returns None if not a git repo or git unavailable."""
    if cwd == "?":
        return None
    try:
        # Get branch name
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, capture_output=True, text=True, timeout=3
        )
        if branch.returncode != 0:
            return None
        branch_name = branch.stdout.strip() or "HEAD"

        # Get porcelain status
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
    # Force UTF-8 on Windows to handle block characters
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("[statusline: no data]")
        return

    # Extract fields with safe fallbacks
    cwd = data.get("workspace", {}).get("current_dir", data.get("cwd", "?"))
    dirname = os.path.basename(cwd) if cwd != "?" else "?"

    ctx = data.get("context_window", {})
    pct = ctx.get("used_percentage", 0) or 0
    pct = int(float(pct))


    # Colors
    ORANGE = "\033[38;2;215;119;87m"  # Claude orange (#D77757)
    GRAY = "\033[38;2;136;136;136m"
    LIGHT_GRAY = "\033[38;2;180;180;180m"
    WHITE = "\033[97m"
    RESET = "\033[0m"

    # Progress bar (10 chars wide)
    bar_width = 10
    filled = pct * bar_width // 100
    empty = bar_width - filled
    bar = "\u2593" * filled + "\u2591" * empty

    # Persist session ID so set-objective.py can write session-scoped objectives
    session_id = data.get("session_id", "")
    save_session_id(session_id)

    # Read current objective
    obj_status, obj_text = get_objective(session_id)

    # Build objective display with dynamic coloring
    # Label is always dim white; value color depends on state
    obj_label = f"{WHITE}\U0001fae7 Objective \u2192 {RESET}"
    if obj_status == "set":
        obj_display = f"{obj_label}{ORANGE}{obj_text}{RESET}"
    elif obj_status == "clear":
        obj_display = f"{obj_label}"
    else:
        obj_display = f"{obj_label}{GRAY}TBD{RESET}"

    # Pipe separator
    pipe = f" {GRAY}|{RESET} "

    # Total Token Usage (input + output, cumulative for session)
    total_in = ctx.get("total_input_tokens", 0) or 0
    total_out = ctx.get("total_output_tokens", 0) or 0
    ttu = total_in + total_out
    if ttu >= 1_000_000:
        ttu_str = f"{ttu / 1_000_000:.1f}M"
    elif ttu >= 1_000:
        ttu_str = f"{ttu / 1_000:.1f}k"
    else:
        ttu_str = str(ttu)

    # Git status (only shown when cwd is a repo with changes)
    GREEN = "\033[38;2;120;200;120m"
    RED = "\033[38;2;220;100;100m"
    git_segment = ""
    git_info = get_git_status(cwd)
    if git_info:
        parts = []
        b = git_info["branch"]
        s, m, d, u = git_info["staged"], git_info["modified"], git_info["deleted"], git_info["untracked"]
        total_dirty = s + m + d + u
        if total_dirty > 0:
            if s: parts.append(f"{GREEN}+{s}{RESET}")
            if m: parts.append(f"{ORANGE}~{m}{RESET}")
            if d: parts.append(f"{RED}-{d}{RESET}")
            if u: parts.append(f"{GRAY}?{u}{RESET}")
            git_segment = f"{pipe}{LIGHT_GRAY}\ue0a0 {b}{RESET} ({' | '.join(parts)})"
        else:
            git_segment = f"{pipe}{GREEN}\ue0a0 {b} \u2714{RESET}"

    # Assemble output: objective, directory, context bar, TTU, git
    line = (
        f"{obj_display}"
        f"{pipe}"
        f"{LIGHT_GRAY}{dirname}{RESET}"
        f"{pipe}"
        f"{ORANGE}{bar} {pct}% context{RESET}"
        f"{pipe}"
        f"{LIGHT_GRAY}TTU: {ORANGE}{ttu_str}{RESET}"
        f"{git_segment}"
    )

    print(line)


if __name__ == "__main__":
    main()
