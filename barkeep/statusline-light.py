#!/usr/bin/env python3
"""Barkeep v2 — light/tmux statusline entry point.

Same architecture as statusline.py, different default segment list. Uses
a thinner pipe separator (│) since it typically lives in a tmux bar.
"""

import io
import json
import sys

from segments import SEGMENTS, build_context
from barkeep_config import get_enabled


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("[barkeep-light: no data]")
        return

    enabled = get_enabled("light")
    ctx = build_context(data)
    pipe = f" {ctx['PAL_PERIWINKLE']}│{ctx['RESET']} "

    parts = []
    for name in enabled:
        entry = SEGMENTS.get(name)
        if not entry:
            continue
        try:
            out = entry["render"](data, ctx)
        except Exception:
            out = f"{ctx['RED']}[{name}: error]{ctx['RESET']}"
        if out:
            parts.append(out)

    print(pipe.join(parts))


if __name__ == "__main__":
    main()
