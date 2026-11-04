#!/usr/bin/env python3
"""Barkeep v2 segment manager.

Toggle which segments appear in the statusline, reorder them, or reset
to defaults. Edits barkeep-config.json next to this script.

Usage:
  python manage.py list [--variant=full|light] [--show-dev]
  python manage.py enable <name> [<name>...] [--variant=full|light]
  python manage.py disable <name> [<name>...] [--variant=full|light]
  python manage.py move <name> (--before <other> | --after <other>) [--variant=...]
  python manage.py order <name> [<name>...] [--variant=full|light]
  python manage.py reset [--variant=full|light]
  python manage.py --version
"""

import argparse
import sys

from segments import SEGMENTS, DEFAULT_FULL_ORDER, DEFAULT_LIGHT_ORDER, __version__
from barkeep_config import get_enabled, set_enabled


def _variant_default(variant):
    return DEFAULT_LIGHT_ORDER if variant == "light" else DEFAULT_FULL_ORDER


def _validate_segment(name):
    if name not in SEGMENTS:
        sys.stderr.write(f"error: unknown segment '{name}'\n")
        sys.stderr.write("       run 'python manage.py list --show-dev' to see available\n")
        sys.exit(2)


def cmd_list(args):
    variant = args.variant
    enabled = get_enabled(variant)
    enabled_set = set(enabled)

    print()
    print(f"Barkeep segments — variant: {variant}")
    print()

    # Compute column widths for alignment
    visible = [
        (name, meta) for name, meta in SEGMENTS.items()
        if args.show_dev or not name.startswith("_")
    ]
    name_w = max((len(n) for n, _ in visible), default=4)
    author_w = max((len(f"-{m['author']}") for _, m in visible), default=8)

    def fmt_row(checked, name, meta):
        mark = "[x]" if checked else "[ ]"
        author = f"(-{meta['author']})"
        return f"  {mark} {name:<{name_w}}  {author:<{author_w + 2}}  {meta['desc']}"

    # Section: enabled, in display order
    print("  Enabled (in display order):")
    if not enabled:
        print("    (none)")
    for name in enabled:
        meta = SEGMENTS.get(name)
        if not meta:
            print(f"  [?] {name:<{name_w}}  (-unknown)  segment not in registry")
            continue
        print(fmt_row(True, name, meta))

    print()
    print("  Available (disabled):")
    available_any = False
    for name, meta in SEGMENTS.items():
        if name in enabled_set:
            continue
        if name.startswith("_") and not args.show_dev:
            continue
        print(fmt_row(False, name, meta))
        available_any = True
    if not available_any:
        print("    (none)")

    print()
    print(f"  Order: {' | '.join(enabled) if enabled else '(empty)'}")
    print()


def cmd_enable(args):
    variant = args.variant
    enabled = list(get_enabled(variant))
    changed = False
    for name in args.names:
        _validate_segment(name)
        if name in enabled:
            print(f"already enabled: {name}")
            continue
        enabled.append(name)
        changed = True
        print(f"enabled: {name} (added at end)")
    if changed:
        set_enabled(variant, enabled)


def cmd_disable(args):
    variant = args.variant
    enabled = list(get_enabled(variant))
    changed = False
    for name in args.names:
        _validate_segment(name)
        if name not in enabled:
            print(f"already disabled: {name}")
            continue
        enabled.remove(name)
        changed = True
        print(f"disabled: {name}")
    if changed:
        set_enabled(variant, enabled)


def cmd_move(args):
    variant = args.variant
    _validate_segment(args.name)
    target = args.before or args.after
    if not target:
        sys.stderr.write("error: --before or --after is required\n")
        sys.exit(2)
    _validate_segment(target)
    enabled = list(get_enabled(variant))
    if args.name not in enabled:
        sys.stderr.write(f"error: '{args.name}' is not currently enabled\n")
        sys.exit(2)
    if target not in enabled:
        sys.stderr.write(f"error: '{target}' is not currently enabled\n")
        sys.exit(2)
    enabled.remove(args.name)
    idx = enabled.index(target)
    if args.after:
        idx += 1
    enabled.insert(idx, args.name)
    set_enabled(variant, enabled)
    relation = "after" if args.after else "before"
    print(f"moved: {args.name} {relation} {target}")
    print(f"order: {' | '.join(enabled)}")


def cmd_order(args):
    variant = args.variant
    for name in args.names:
        _validate_segment(name)
    if len(args.names) != len(set(args.names)):
        sys.stderr.write("error: duplicate segment names not allowed\n")
        sys.exit(2)
    set_enabled(variant, args.names)
    print(f"order set: {' | '.join(args.names)}")


def cmd_reset(args):
    variant = args.variant
    defaults = _variant_default(variant)
    set_enabled(variant, list(defaults))
    print(f"reset {variant} to defaults: {' | '.join(defaults)}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Barkeep statusline segments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version",
                        version=f"barkeep {__version__}")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    def add_variant(p):
        p.add_argument("--variant", choices=["full", "light"], default="full",
                       help="which statusline variant to operate on (default: full)")

    p_list = subparsers.add_parser("list", help="list segments")
    add_variant(p_list)
    p_list.add_argument("--show-dev", action="store_true",
                        help="include dev segments (those prefixed with _)")
    p_list.set_defaults(func=cmd_list)

    p_enable = subparsers.add_parser("enable", help="enable one or more segments")
    add_variant(p_enable)
    p_enable.add_argument("names", nargs="+")
    p_enable.set_defaults(func=cmd_enable)

    p_disable = subparsers.add_parser("disable", help="disable one or more segments")
    add_variant(p_disable)
    p_disable.add_argument("names", nargs="+")
    p_disable.set_defaults(func=cmd_disable)

    p_move = subparsers.add_parser("move", help="move a segment relative to another")
    add_variant(p_move)
    p_move.add_argument("name")
    grp = p_move.add_mutually_exclusive_group(required=True)
    grp.add_argument("--before", metavar="OTHER")
    grp.add_argument("--after", metavar="OTHER")
    p_move.set_defaults(func=cmd_move)

    p_order = subparsers.add_parser("order", help="set the full enable list explicitly")
    add_variant(p_order)
    p_order.add_argument("names", nargs="+")
    p_order.set_defaults(func=cmd_order)

    p_reset = subparsers.add_parser("reset", help="reset variant to its defaults")
    add_variant(p_reset)
    p_reset.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
