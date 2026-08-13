"""Build `catalog.json` from `icons/` note-folders for the HSK Icons app."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from family_id import category_from_family_id, title_from_family_id

REPO_ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = REPO_ROOT / "icons"
CATALOG_PATH = REPO_ROOT / "catalog.json"

_SKIP_DIR_NAMES = frozenset({".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv"})
_NOTE_ASSET_DIR_NAMES = frozenset({"img", "files"})
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_LIST_RE = re.compile(r"^\[\s*(.*?)\s*\]$")


def file_sha256(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_yaml_list(raw: str) -> list[str]:
    """Parse a simple YAML inline list like `[a, b]` or `["a", "b"]`."""
    match = _LIST_RE.match(raw.strip())
    if not match:
        return [raw.strip().strip("\"'")] if raw.strip() else []
    inner = match.group(1).strip()
    if not inner:
        return []
    items: list[str] = []
    for part in inner.split(","):
        item = part.strip().strip("\"'")
        if item:
            items.append(item)
    return items


def is_icon_note_dir(path: Path) -> bool:
    """Return whether `path` is an icon family note-folder."""
    if not path.is_dir():
        return False
    return (
        (path / "featured-image.svg").is_file()
        or (path / f"{path.name}.md").is_file()
        or (path / "img").is_dir()
    )


def iter_icon_note_dirs(icons_dir: Path) -> list[Path]:
    """Collect icon note-folders under `icons/`, including category subfolders."""
    result: list[Path] = []
    stack = [icons_dir]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir():
                continue
            name = entry.name.casefold()
            if name in _SKIP_DIR_NAMES or name in _NOTE_ASSET_DIR_NAMES:
                continue
            if is_icon_note_dir(entry):
                result.append(entry)
            else:
                stack.append(entry)
    result.sort(key=lambda item: item.as_posix().casefold())
    return result


def first_h1(text: str) -> str:
    """Return the first ATX H1 heading after optional YAML frontmatter."""
    body = text
    match = _FRONTMATTER_RE.match(text)
    if match:
        body = text[match.end() :]
    for line in body.splitlines():
        heading = _H1_RE.match(line)
        if heading:
            return heading.group(1).strip()
    return ""


def parse_frontmatter(md_path: Path) -> dict[str, Any]:
    """Parse a minimal YAML frontmatter block (categories, tags, date)."""
    text = md_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"categories", "tags"}:
            result[key] = _parse_yaml_list(value)
        elif key == "date":
            result[key] = value.strip("\"'")
        elif key == "title":
            result["title"] = value.strip("\"'")
    yaml_title = str(result.get("title") or "").strip()
    result["title"] = yaml_title or first_h1(text)
    return result


def build_catalog(icons_dir: Path) -> dict[str, Any]:
    """Scan note-folders and return catalog structure."""
    repo_root = icons_dir.resolve().parent
    icons: list[dict[str, Any]] = []
    for note_dir in iter_icon_note_dirs(icons_dir):
        family_id = note_dir.name
        md_path = note_dir / f"{family_id}.md"
        meta = parse_frontmatter(md_path) if md_path.is_file() else {}

        categories = list(meta.get("categories") or [])
        if not categories:
            categories = [category_from_family_id(family_id)]

        title = str(meta.get("title") or title_from_family_id(family_id))
        tags = list(meta.get("tags") or [])
        icon_date = str(meta.get("date") or "").strip()

        featured = note_dir / "featured-image.svg"
        featured_rel = "featured-image.svg" if featured.is_file() else ""
        featured_hash = file_sha256(featured) if featured.is_file() else ""

        variants: list[dict[str, str]] = []
        img_dir = note_dir / "img"
        if img_dir.is_dir():
            for svg in sorted(img_dir.glob("*.svg")):
                variants.append(
                    {
                        "file": f"img/{svg.name}",
                        "name": svg.stem,
                        "hash": file_sha256(svg),
                    },
                )

        icons.append(
            {
                "id": family_id,
                "title": title,
                "date": icon_date,
                "categories": categories,
                "tags": tags,
                "folder": note_dir.resolve().relative_to(repo_root).as_posix(),
                "featured": featured_rel,
                "featured_hash": featured_hash,
                "variants": variants,
            },
        )

    return {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "icons": icons,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icons", type=Path, default=ICONS_DIR, help="icons/ folder")
    parser.add_argument("--output", type=Path, default=CATALOG_PATH, help="catalog.json path")
    args = parser.parse_args(argv)
    if not args.icons.is_dir():
        print(f"icons not found: {args.icons}", file=sys.stderr)
        return 1
    catalog = build_catalog(args.icons)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog['icons'])} icons -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
