"""Move `icons/{family_id}` note-folders into `icons/{category}/{family_id}`."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from build_catalog import ICONS_DIR, is_icon_note_dir
from family_id import note_dir_for_family_id


def nest_icons(icons_dir: Path) -> int:
    """Nest top-level note-folders by category prefix. Return how many moved."""
    moved = 0
    for child in sorted(path for path in icons_dir.iterdir() if path.is_dir()):
        if not is_icon_note_dir(child):
            continue
        dest = note_dir_for_family_id(icons_dir, child.name)
        if child.resolve() == dest.resolve():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            msg = f"Destination already exists: {dest}"
            raise FileExistsError(msg)
        try:
            child.rename(dest)
        except OSError:
            shutil.move(str(child), str(dest))
        moved += 1
    return moved


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icons", type=Path, default=ICONS_DIR, help="icons/ folder")
    args = parser.parse_args(argv)
    if not args.icons.is_dir():
        print(f"icons not found: {args.icons}", file=sys.stderr)
        return 1
    moved = nest_icons(args.icons)
    print(f"Moved {moved} note-folders under category directories in {args.icons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
