"""Migrate flat `dist/` SVG packs into note-folder layout under `icons/`."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from family_id import category_from_family_id, family_id_from_stem, tags_from_family_id, title_from_family_id

COLOR_PACKS = frozenset({"black", "gray", "white", "color"})
REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
ICONS_DIR = REPO_ROOT / "icons"


@dataclass
class VariantSource:
    """One source SVG discovered under `dist/`."""

    path: Path
    pack: str  # root | black | gray | white | color | note
    sha256: str = ""


@dataclass
class FamilyBucket:
    """Collected variants for one icon family."""

    variants: list[VariantSource] = field(default_factory=list)


def file_sha256(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_flat_svgs(dist_dir: Path) -> dict[str, FamilyBucket]:
    """Scan flat SVG packs (root + color folders) into family buckets."""
    families: dict[str, FamilyBucket] = defaultdict(FamilyBucket)

    for path in sorted(dist_dir.glob("*.svg")):
        fid = family_id_from_stem(path.stem)
        families[fid].variants.append(VariantSource(path=path, pack="root", sha256=file_sha256(path)))

    for pack in sorted(COLOR_PACKS):
        pack_dir = dist_dir / pack
        if not pack_dir.is_dir():
            continue
        for path in sorted(pack_dir.glob("*.svg")):
            fid = family_id_from_stem(path.stem)
            families[fid].variants.append(VariantSource(path=path, pack=pack, sha256=file_sha256(path)))

    return families


def discover_existing_notes(dist_dir: Path) -> dict[str, Path]:
    """Find already-migrated note folders under `dist/` (e.g. Marvin)."""
    notes: dict[str, Path] = {}
    for child in dist_dir.iterdir():
        if not child.is_dir() or child.name in COLOR_PACKS:
            continue
        md = child / f"{child.name}.md"
        img = child / "img"
        if md.is_file() and img.is_dir():
            notes[child.name] = child
    return notes


def pick_featured(variants: list[VariantSource]) -> VariantSource:
    """Prefer color/_01 variants without mono/line/improbable tokens."""

    def score(item: VariantSource) -> tuple[int, int, int, str]:
        name = item.path.stem
        pack_score = {"color": 0, "root": 1, "black": 2, "gray": 3, "white": 4, "note": 5}.get(item.pack, 9)
        has_01 = 0 if name.endswith("_01") else 1
        has_noise = 0
        for token in ("_black", "_gray", "_white", "_line-", "_improbable"):
            if token in name:
                has_noise += 1
        return (pack_score, has_noise, has_01, name)

    return sorted(variants, key=score)[0]


def write_note_md(family_id: str, note_dir: Path, *, existing_md: Path | None = None) -> None:
    """Write or preserve the family markdown note with YAML frontmatter."""
    target = note_dir / f"{family_id}.md"
    if existing_md is not None and existing_md.is_file():
        shutil.copy2(existing_md, target)
        return

    category = category_from_family_id(family_id)
    title = title_from_family_id(family_id)
    tags = tags_from_family_id(family_id)
    tags_yaml = ", ".join(tags)
    body = f"""---
categories: [{category}]
tags: [{tags_yaml}]
title: {title}
---

# {title}

![Featured image](featured-image.svg)

## Icons

"""
    img_dir = note_dir / "img"
    lines = []
    for svg in sorted(img_dir.glob("*.svg")):
        lines.append(f"- ![{svg.stem}](img/{svg.name})")
    target.write_text(body + "\n".join(lines) + "\n", encoding="utf-8")


def copy_variants_into_note(family_id: str, bucket: FamilyBucket, icons_dir: Path) -> int:
    """Copy unique-by-hash variants into `icons/{id}/img/`. Return file count."""
    note_dir = icons_dir / family_id
    img_dir = note_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    seen_hashes: dict[str, str] = {}
    written = 0
    for variant in bucket.variants:
        existing_name = seen_hashes.get(variant.sha256)
        if existing_name is not None:
            continue
        dest_name = variant.path.name
        dest = img_dir / dest_name
        if dest.exists() and file_sha256(dest) != variant.sha256:
            dest = img_dir / f"{variant.path.stem}__{variant.pack}{variant.path.suffix}"
        shutil.copy2(variant.path, dest)
        seen_hashes[variant.sha256] = dest.name
        written += 1

    featured_src = pick_featured(bucket.variants)
    featured_dest = note_dir / "featured-image.svg"
    # Prefer already-copied unique file with same hash
    featured_name = seen_hashes.get(featured_src.sha256)
    if featured_name:
        shutil.copy2(img_dir / featured_name, featured_dest)
    else:
        shutil.copy2(featured_src.path, featured_dest)

    write_note_md(family_id, note_dir)
    return written


def copy_existing_note(family_id: str, source_note: Path, icons_dir: Path) -> int:
    """Copy a pre-existing note-folder (Marvin-style) into `icons/`."""
    dest = icons_dir / family_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source_note, dest)
    # Ensure featured-image exists
    featured = dest / "featured-image.svg"
    if not featured.is_file():
        img = dest / "img"
        svgs = sorted(img.glob("*.svg")) if img.is_dir() else []
        if svgs:
            shutil.copy2(svgs[0], featured)
    md = dest / f"{family_id}.md"
    if not md.is_file():
        write_note_md(family_id, dest)
    return len(list((dest / "img").glob("*.svg"))) if (dest / "img").is_dir() else 0


def migrate(*, dist_dir: Path, icons_dir: Path, clean: bool) -> None:
    """Run full migration from `dist/` into `icons/`."""
    if clean and icons_dir.exists():
        shutil.rmtree(icons_dir)
    icons_dir.mkdir(parents=True, exist_ok=True)

    existing_notes = discover_existing_notes(dist_dir)
    families = discover_flat_svgs(dist_dir)

    # Merge note-folder SVGs into buckets when family also has flat files
    for note_id, note_path in existing_notes.items():
        img_dir = note_path / "img"
        for path in sorted(img_dir.glob("*.svg")):
            families[note_id].variants.append(
                VariantSource(path=path, pack="note", sha256=file_sha256(path)),
            )

    total_files = 0
    for family_id in sorted(families):
        if family_id in existing_notes and not any(v.pack != "note" for v in families[family_id].variants):
            # Pure note-only family (should not happen often)
            total_files += copy_existing_note(family_id, existing_notes[family_id], icons_dir)
            continue
        if family_id in existing_notes:
            # Prefer preserving existing markdown when present
            note_dir = icons_dir / family_id
            img_dir = note_dir / "img"
            img_dir.mkdir(parents=True, exist_ok=True)
            written = 0
            seen_hashes: dict[str, str] = {}
            for variant in families[family_id].variants:
                if variant.sha256 in seen_hashes:
                    continue
                dest = img_dir / variant.path.name
                if dest.exists() and file_sha256(dest) != variant.sha256:
                    dest = img_dir / f"{variant.path.stem}__{variant.pack}{variant.path.suffix}"
                shutil.copy2(variant.path, dest)
                seen_hashes[variant.sha256] = dest.name
                written += 1
            featured_src = pick_featured(families[family_id].variants)
            featured_name = seen_hashes.get(featured_src.sha256)
            featured_dest = note_dir / "featured-image.svg"
            if featured_name:
                shutil.copy2(img_dir / featured_name, featured_dest)
            else:
                shutil.copy2(featured_src.path, featured_dest)
            existing_md = existing_notes[family_id] / f"{family_id}.md"
            write_note_md(family_id, note_dir, existing_md=existing_md if existing_md.is_file() else None)
            total_files += written
            continue
        total_files += copy_variants_into_note(family_id, families[family_id], icons_dir)

    print(f"Families: {len(families)}")
    print(f"SVG files written (unique by hash per family): {total_files}")
    print(f"Output: {icons_dir}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist",
        type=Path,
        default=DIST_DIR,
        help="Path to dist folder (default: repo dist/)",
    )
    parser.add_argument(
        "--icons",
        type=Path,
        default=ICONS_DIR,
        help="Output icons folder (default: repo icons/)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing icons/ before migration",
    )
    args = parser.parse_args(argv)
    if not args.dist.is_dir():
        print(f"dist not found: {args.dist}", file=sys.stderr)
        return 1
    migrate(dist_dir=args.dist, icons_dir=args.icons, clean=args.clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
