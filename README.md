# Harrix-Vector-Icons

<https://github.com/Harrix/Harrix-Vector-Icons-ai> repo with source AI files.

## Layout

- `icons/` — **source of truth**: one note-folder per icon family, grouped by category.
- `catalog.json` — generated local search index (gitignored; Vector Icons rebuilds it on open if missing).
- `tools/` — catalog and optional migration scripts.

### Note-folder format

```text
icons/building/building__house/
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
date: 2020-07-19
categories: [building]
tags: [house, дом]
---

# House
```

## Rebuild catalog

Vector Icons writes `catalog.json` when you open the repo without one, or when you rebuild the catalog in the app.

From the repository root (Python 3.11+):

```text
python tools/build_catalog.py
```

Optional one-time migration from a legacy flat `dist/` tree (if you restore it from backup):

```text
python tools/migrate_dist_to_icons.py --clean
```
