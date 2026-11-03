# v3.6.0 — import batchE2 (52 full single photos: 油菜花/花海 / 夜景·霓虹 / 地铁)

Local working copy only; nothing pushed. Base: v3.5.0 (351 photos).

Total photos: 351 → **403** (added 52, nothing removed). Taxonomy: 138 → 140 tags (new scene tags: 油菜花, 霓虹; 花海 already aliases to 花丛; no unused tags). e2e: 70/70 passed (`tests/e2e.py . v36 screenshots`).

batchE2: 108 candidates (e4–e15) → kept 52, dropped 56. Converted webp → lossless PNG before import (no cropping or rotation). Face-zoom AI check on the kept folders — all look like real photos. Duplicate check vs existing photos (dhash): none.
Dropped:
- e4/01–03: each is a 3-frame stacked collage; e4/04 (cropped, lying), e4/06, 09, 10 (tiny or back-view small figure)
- e5 (all 5): bare midriff crop top / short skirt sitting
- e6/04 (near-duplicate of e6/03), e6/06 (tiny landscape)
- e7 (all 9): AI-looking over-smooth faces and bodies, very short shorts
- e8 (all 9): black-skirt / thigh-high cosplay look, not clearly tasteful
- e9/04 (tiny landscape figure)
- e10/01 (near-dup of 04), 07 (near-dup of 06), 09 (near-dup of 03), 10 (tiny figure)
- e12/02 (tiny figure), e12/06 (near-dup of 07)
- e13 (all 10): short mini dress with sheer pantyhose
- e14/01, 10 (small figure), e14/03 (near-dup of 02), e14/07 (near-dup of 06)
- e15/01 (very short dress), e15/05 (tiny landscape), e15/07 (sheer stockings)
Kept by folder: e4 3 (油菜花), e6 6 (夜景霓虹), e9 5 (油菜花), e10 6 (油菜花, 背影), e11 6 (夜景霓虹), e12 16 (地铁), e14 6 (夜景), e15 4 (夜景).

## Files DELETED
None.

## Files CHANGED (overwrite)
- `data/imported.json`
- `data/taxonomy.json`
- `sw.js` (cache v3.6.0)
- `tests/e2e.py` (version string)
- `README.md`

## Files ADDED
- `CHANGES-v36.md`
- `screenshots/v36-1-home.png` … `v36-6-dark.png` (6 files)
- 52 × `imported/<id>.jpg` and `imported/thumbs/<id>.jpg` (originals named `eN_NN.png` in `original_name`)
