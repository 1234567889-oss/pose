# v3.8.0 — Douyin batch F（onsetyang 公园/花园/稻田客片 + 米米汉服）

Local working copy only; nothing pushed. Base: v3.7.0 (430 photos).

Total photos: 430 → **533** (added **103**, rejected 17 of 120 downloaded). Taxonomy: **147** tags (new prop tag e.g. 枕头). e2e: **70/70** passed (`tests/e2e.py . v38 screenshots`).

Douyin 图文 batch F — real client 约拍 singles only; no AI / collage / pose-grid sheets. Visual pass dropped tight face-only crops and low pose-value frames (esp. in f05_off_shoulder, f08_white_corset, f10_straw_hat). Each kept frame got a unique title + 口令 + tips + 焦段 (import is content-hash idempotent).

Sources (12 notes, 103 kept / 120 downloaded):
- onsetyang · 公园格子裙 — 6 (`f01_park_gingham`)
- onsetyang · 三角梅墙 — 11 (`f02_bougainvillea`)
- onsetyang · 花园旗袍 — 9 (`f03_garden_qipao`)
- onsetyang · 秋日草帽花篮 — 11 (`f04_autumn_hat`)
- onsetyang · 草地露肩/牛仔靴 — 8 (`f05_off_shoulder`)
- onsetyang · 森林野餐 — 10 (`f06_forest_picnic`)
- onsetyang · 稻田番茄篮 — 12 (`f07_rice_field`)
- onsetyang · 白马甲牛仔短裤 — 8 (`f08_white_corset`)
- onsetyang · 碎花裙抱枕 — 9 (`f09_floral_dress`)
- onsetyang · 春日草帽特写组 — 6 (`f10_straw_hat`)
- onsetyang · 绿针织玫瑰 — 6 (`f11_green_knit`)
- 杭州摄影师米米 · 秋日汉服桥伞 — 7 (`f12_autumn_hanfu`)

Rejected (17): face-only / weak pose crops — f01_06; f02_08; f03_05; f04_12; f05_09–10; f06_07; f07_06/13; f08_03/06; f09_07; f10_01/07; f11_01/06; f12_06.

## Files DELETED
None (app). Rejected JPEGs removed from `xhs/douyin-batchF/incoming/` only.

## Files CHANGED (overwrite)
- `data/imported.json` (+103)
- `data/taxonomy.json` (new prop tags as needed)
- `sw.js` (cache v3.8.0)
- `tests/e2e.py` (version string)
- `README.md`

## Files ADDED
- `CHANGES-v38.md`
- `screenshots/v38-*.png` (from e2e)
- 103 × `imported/<id>.jpg` and `imported/thumbs/<id>.jpg` (originals named `f01_*` … `f12_*`)
