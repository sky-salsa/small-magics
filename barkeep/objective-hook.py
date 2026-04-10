#!/usr/bin/env python3
"""Claude Code hook -- captures 'objective:' prefixed messages and logs them.

Triggered on UserPromptSubmit. Reads prompt from stdin JSON.
If prompt starts with 'objective:', writes to objectives.json.
Otherwise exits immediately with no I/O.
"""

import json
import sys
import os
from datetime import datetime, timezone

OBJECTIVES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "objectives.json")

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    prompt = data.get("prompt", "").strip()
    session_id = data.get("session_id", "unknown")

    # Only act on "objective:" prefix (case-insensitive)
    if not prompt.lower().startswith("objective:"):
        return

    objective_text = prompt[len("objective:"):].strip()

    # Determine action
    if objective_text.lower() in ("clear", "none", ""):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "clear",
            "objective": None,
        }
    else:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "set",
            "objective": objective_text,
        }

    try:
        # Read existing data
        if os.path.exists(OBJECTIVES_FILE):
            with open(OBJECTIVES_FILE, "r", encoding="utf-8") as f:
                objectives = json.load(f)
        else:
            objectives = {}

        # Append entry under session ID
        if session_id not in objectives:
            objectives[session_id] = []
        objectives[session_id].append(entry)

        # Atomic write: write to .tmp, then replace
        tmp_file = OBJECTIVES_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(objectives, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, OBJECTIVES_FILE)

    except Exception as e:
        print(f"objective write failed: {e}", file=sys.stderr)
        return

    # Block the prompt from reaching Claude -- objective commands are
    # status-bar-only, not conversation messages.
    if entry["action"] == "clear":
        reason = "Objective cleared."
    else:
        reason = f"Objective set: {objective_text}"

    print(json.dumps({
        "decision": "block",
        "reason": reason,
    }))


if __name__ == "__main__":
    main()
