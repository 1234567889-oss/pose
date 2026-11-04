# v4.1.0 — Douyin batch H（窗边阅读 / 雪景 / 雪夜车内 / 卧室 / 花海 / 法式窗帘 / 阶梯教室）

Local working copy only; nothing pushed. Base: v4.0.0 (606 photos).

Total photos: 606 → **682** (added **76**, rejected 14 of 90 downloaded). Taxonomy unchanged: **147** tags (`--strict`). e2e: **111/111** passed (`tests/e2e.py . v41 screenshots`).

Every frame viewed and tagged per photo; dHash (256-bit) dedupe vs all 606 existing thumbs + within batch. Lying/prone poses tagged where real: 躺 h01_03, h03_03, h06_06; 趴 h05_05, h06_08. h04 already landscape (2844×1440), kept as 横构图. h03 snow scenes have no 场景 tag (taxonomy has no 雪景 value; left blank under --strict).

Sources (kept / downloaded):
- 墨鱼女孩 · 窗边阅读/木地板 — 9/9 (`h01_moyu_window`)
- 牛油果不牛 · 复古书店 JK — 0/11 (`h02_hiuyo_bookstore`)
- HammKumo摄影 · 雪景木屋 — 9/9 (`h03_snow_hammkumo`)
- 空气切片师 · 雪夜打伞/车内 — 7/8 (`h04_snownight_car`)
- 欢欢小同学 · 卧室白裙 — 6/6 (`h05_bedroom_whitedress`)
- 呦呦小马甲 · 橙色花海 — 8/8 (`h06_flowers_cosmos`)
- 林间拾花者 · 花海绿裙 — 9/9 (`h07_flowers_cosmos_green`)
- 奶兔 · 月见草花海蝴蝶风筝 — 6/6 (`h08_flowers_kite`)
- 木子RAW · 法式白纱帘窗边 — 11/12 (`h09_window_french_muzi`)
- 小良月 · 阶梯教室 — 11/12 (`h10_campus_classroom`)

Rejected (14):
- h02_01–14 (all 11 slides): every slide carries the visible "HIUYO RAW/FOSHAN" logo watermark (mid-frame on most); h02_08 is also a collage
- h04_06: near-duplicate of h04_02 (dHash distance 29/256)
- h09_08: head cropped out at top, weak pose value
- h10_02: low-res (960×1280, longest side < 1200) and tight face crop

## Files CHANGED (overwrite)
- `data/imported.json` (+76 → 682), `sw.js` (cache v4.1.0), `app.js` (VERSION 4.1.0), `tests/e2e.py` (version, 1/682), `README.md`

## Files ADDED
- `CHANGES-v41.md`, `screenshots/v41-*.png`, 76 × `imported/<id>.jpg` + `imported/thumbs/<id>.jpg`
