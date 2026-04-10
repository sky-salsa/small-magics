#!/usr/bin/env python3
"""Set the status bar objective from the command line (used by Claude).

Reads the current session ID from current_session.txt (written by
statusline.py on every response) and writes to objectives.json under
that session -- same format as the hook, fully session-scoped.

Usage:
    python set-objective.py "my objective text"
    python set-objective.py clear
"""

import json
import sys
import os
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECTIVES_FILE = os.path.join(SCRIPT_DIR, "objectives.json")
SESSION_FILE = os.path.join(SCRIPT_DIR, "current_session.txt")


def get_session_id():
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python set-objective.py \"objective text\" | clear")
        sys.exit(1)

    session_id = get_session_id()
    if not session_id:
        print("Error: No active session found (current_session.txt missing).")
        print("This is normal on the very first message -- the statusline")
        print("needs one response cycle to record the session ID.")
        sys.exit(1)

    text = " ".join(sys.argv[1:]).strip()

    if text.lower() in ("clear", "none", ""):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "clear",
            "objective": None,
        }
    else:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "set",
            "objective": text,
        }

    try:
        if os.path.exists(OBJECTIVES_FILE):
            with open(OBJECTIVES_FILE, "r", encoding="utf-8") as f:
                objectives = json.load(f)
        else:
            objectives = {}

        if session_id not in objectives:
            objectives[session_id] = []
        objectives[session_id].append(entry)

        # Atomic write
        tmp = OBJECTIVES_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(objectives, f, indent=2, ensure_ascii=False)
        os.replace(tmp, OBJECTIVES_FILE)

    except Exception as e:
        print(f"Error writing objective: {e}", file=sys.stderr)
        sys.exit(1)

    if entry["action"] == "clear":
        print("Objective cleared.")
    else:
        print(f"Objective set: {text}")


if __name__ == "__main__":
    main()
