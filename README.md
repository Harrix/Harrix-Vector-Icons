# Harrix-Vector-Icons

<https://github.com/Harrix/Harrix-Vector-Icons-ai> repo with source AI files.

## Layout

- `dist/` — legacy flat SVG packs (`black/`, `gray/`, `white/`, `color/`, root picks). Kept for rollback.
- `icons/` — **source of truth**: one note-folder per icon family.
- `catalog.json` — generated search index for apps (do not edit by hand).
- `tools/` — migration and catalog scripts.

### Note-folder format

```text
icons/building__house/
  building__house.md
  featured-image.svg
  img/
    building__house_01.svg
    building__house_black.svg
    …
```

YAML frontmatter example:

```yaml
---
categories: [building]
tags: [house, дом]
title: House
---
```

## Rebuild

From the repository root (Python 3.11+):

```text
python tools/migrate_dist_to_icons.py --clean
python tools/build_catalog.py
```

`migrate_dist_to_icons.py` groups SVGs by family id (strips `_black` / `_gray` / `_white`, `_line-8|16|32`, `_improbable`, `_NN`). `build_catalog.py` writes `catalog.json` with paths and content hashes.
