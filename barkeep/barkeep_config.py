"""Barkeep v2 user-config plumbing.

barkeep-config.json lives next to this script (the install dir). It's
seeded from barkeep-config.default.json on first read if missing.
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "barkeep-config.json")
DEFAULT_CONFIG_FILE = os.path.join(SCRIPT_DIR, "barkeep-config.default.json")


def load_default_config():
    """Read the shipped defaults. Returns {} on any failure."""
    try:
        with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def load_config():
    """Load user config; auto-seed from defaults if missing.

    Returns a dict with keys 'statusline' and 'statusline-light' each
    holding an ordered list of segment names.
    """
    if not os.path.exists(CONFIG_FILE):
        defaults = load_default_config()
        save_config(defaults)
        return defaults
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return load_default_config()


def save_config(config):
    """Atomic write to barkeep-config.json."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG_FILE)
        return True
    except OSError:
        return False


def get_enabled(variant):
    """Return ordered list of enabled segments for variant ('full' | 'light').

    Falls back to DEFAULT_*_ORDER from segments.py if the config key is missing.
    """
    from segments import DEFAULT_FULL_ORDER, DEFAULT_LIGHT_ORDER
    cfg = load_config()
    key = "statusline-light" if variant == "light" else "statusline"
    fallback = DEFAULT_LIGHT_ORDER if variant == "light" else DEFAULT_FULL_ORDER
    return cfg.get(key, fallback)


def set_enabled(variant, segment_list):
    """Replace the enable list for variant. Persists immediately."""
    cfg = load_config()
    key = "statusline-light" if variant == "light" else "statusline"
    cfg[key] = segment_list
    return save_config(cfg)
