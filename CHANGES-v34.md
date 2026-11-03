# v3.4.0 — import batchD (88 full single photos)

Local working copy only; nothing pushed. Base: v3.3.0 (235 photos).

Total photos: 235 → **323** (added 88, nothing removed). Taxonomy: 133 → 136 tags (new scene tags: 校园, 博物馆, 书店; unused tags pruned — none were unused). e2e: 70/70 passed (`tests/e2e.py . v34 screenshots`).

batchD: 122 candidates (d1–d16) → kept 88, dropped 34. Converted webp → lossless PNG before import (no cropping or rotation). Strict screen at full size; face-zoom checks on the film/retouched sets.
Dropped by folder: d1 1 (near-duplicate), d3 3 (tiny figure; two near-duplicate poses), d5 2 (stacked two-photo collage; tiny figure), d6 0, d7 1 (tiny figure), d8 3 (collage/odd crop/tiny), d9 4 (tiny figures, near-duplicate, face cut off), d10 2 (near-duplicate, tiny), d11 4 (three stacked two-photo collages + one small landscape), d13 6 (all: AI-looking, doll-like uniform faces), d14 5 (tiny figures / odd crop), d15 3 (all: watermark overlay "ZHAOCANPHOTOGRAPH").
Kept by folder: d1 9, d2 4, d3 8, d4 6, d5 4, d6 7, d7 4, d8 4, d9 7, d10 7, d11 5, d12 6, d14 5, d16 12.
Note: d16 model looks very young (school-uniform styling); age cannot be verified.

## Files DELETED
None.

## Files CHANGED (overwrite)
- `data/imported.json`
- `data/taxonomy.json`
- `sw.js` (cache v3.4.0)
- `tests/e2e.py` (version string)
- `README.md`

## Files ADDED
- `CHANGES-v34.md`
- `screenshots/v34-1-home.png` … `v34-6-dark.png` (6 files)
- 88 × `imported/<id>.jpg` and `imported/thumbs/<id>.jpg` (ids in `data/imported.json`; originals named `dN_NN.png` in `original_name`)
