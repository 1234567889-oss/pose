# v3.5.0 — import batchE (28 full single photos: 地铁站台 / 天台)

Local working copy only; nothing pushed. Base: v3.4.0 (323 photos).

Total photos: 323 → **351** (added 28, nothing removed). Taxonomy: 136 → 138 tags (new scene tags: 地铁, 天台; unused tags pruned — none were unused). e2e: 70/70 passed (`tests/e2e.py . v35 screenshots`; the offline-thumbnail-download check now waits up to 20 s for "已保存" instead of a fixed 1.5 s, which was flaky at 351 photos).

batchE: 33 candidates (e1–e3) → kept 28, dropped 5. Converted webp → lossless PNG before import (no cropping or rotation). Face-zoom AI check on e1/e2/e3 — all look like real photos. Duplicate check vs existing photos (dhash): none.
Dropped: e2/01 and e2/04 (tiny figure), e2/12 (arm covering most of the frame), e3/03 (near-duplicate of e3/04), e3/10 (tiny figure).
Kept by folder: e1 9 (地铁站台), e2 12 (天台), e3 7 (天台).

## Files DELETED
None.

## Files CHANGED (overwrite)
- `data/imported.json`
- `data/taxonomy.json`
- `sw.js` (cache v3.5.0)
- `tests/e2e.py` (version string; offline-download wait)
- `README.md`

## Files ADDED
- `CHANGES-v35.md`
- `screenshots/v35-1-home.png` … `v35-6-dark.png` (6 files)
- 28 × `imported/<id>.jpg` and `imported/thumbs/<id>.jpg` (originals named `eN_NN.png` in `original_name`)
