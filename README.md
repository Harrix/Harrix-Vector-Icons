# Harrix-Vector-Icons

<https://github.com/Harrix/Harrix-Vector-Icons-ai> repo with source AI files.

## Layout

- `icons/` — **source of truth**: one note-folder per icon family.
- `catalog.json` — generated search index for apps (do not edit by hand).
- `tools/` — catalog and optional migration scripts.

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

## Rebuild catalog

From the repository root (Python 3.11+):

```text
python tools/build_catalog.py
```

`build_catalog.py` writes `catalog.json` with paths and content hashes for each family under `icons/`.

Optional one-time migration from a legacy flat `dist/` tree (if you restore it from backup):

```text
python tools/migrate_dist_to_icons.py --clean
python tools/build_catalog.py
```
