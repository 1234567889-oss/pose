# v3.7.0 — Douyin trial import（王森·罗汉寺马面裙、筱雨·逆光黑裙、林鹏呀·影棚）

Local working copy only; nothing pushed. Base: v3.6.0 (403 photos).

Total photos: 403 → **430** (added 27, nothing removed). Taxonomy: 140 → **143** tags (new prop tags: 香, 扇, 念珠). e2e: `tests/e2e.py . v37 screenshots`.

Douyin 图文 trial batch — real client 约拍 photos only; no AI / collage / pose-grid sheets. Each frame got a unique title + 口令 + tips + 焦段 after visual check (import is content-hash idempotent; metadata merged on re-run).

Sources (3 notes, 27 singles):
- 王森 · 罗汉寺马面裙约拍 — 13 frames (`wangsen_01`–`13`, note 7694295423585881380). 古建筑 + 汉服/马面裙；香/念珠/扇/伞道具.
- 筱雨 · 逆光黑裙 — 9 frames (`xiaoyu_01`–`09`, note 7688406109955172520). 公园/湖边, 逆光黑裙, 走/坐/特写.
- 林鹏呀 · 影棚客片 — 5 frames (`linpeng_01`–`05`, note 7700798952749290186). 灰棚柔光, 卫衣/短裙站坐.

Strict quality: single full photos, real people, tasteful; rejected AI-looking / collage posts from the same trial session were not imported.

## Files DELETED
None.

## Files CHANGED (overwrite)
- `data/imported.json`
- `data/taxonomy.json` (+香/扇/念珠)
- `sw.js` (cache v3.7.0)
- `tests/e2e.py` (version string)
- `README.md`

## Files ADDED
- `CHANGES-v37.md`
- `screenshots/v37-*.png` (from e2e)
- 27 × `imported/<id>.jpg` and `imported/thumbs/<id>.jpg` (originals named `wangsen_*` / `xiaoyu_*` / `linpeng_*`)
