# v4.0.0 — Douyin batch G（古风园林旗袍 / 老小区 / 夜景 / 雨夜 / 海边 / 仙侠影棚 / 汉服古建）

Local working copy only; nothing pushed. Base: v3.9.0 (533 photos).

Total photos: 533 → **606** (added **73**, rejected 18 of 91 downloaded). Taxonomy unchanged: **147** tags (imported with `--strict`). e2e: **111/111** passed (`tests/e2e.py . v40 screenshots`).

Real client 约拍 singles only; no AI / doll-skin / collage / text covers. Every frame viewed and tagged per photo (光线/体位/景别/机位/构图 etc.), unique Chinese title + 口令 + tips + 焦段. Perceptual-hash (dHash 256-bit) check vs all 533 existing thumbs and within batch: no near-duplicates in kept set. g07 slides were stored sideways → rotated 90° upright before import.

Sources (kept / downloaded):
- 吉喆 · 白旗袍古风园林 — 9/9 (`g01_jizhe_qipao`)
- 舒芙蕾 · 老小区街道 — 11/12 (`g02_shufulei_street`)
- 风无岸 · 夜景红裙 — 2/4 (`g03_fengwuan_night`)
- 猫爪 · 夜景天桥白裙 — 4/5 (`g04_maozhua_bridge`)
- 十一。 · 夜景街头 — 8/10 (`g05_shiyi_night`)
- 雾屿 · 雨夜透明伞 — 9/9 (`g06_wuyu_rain`)
- 李贰腿 · 海边 — 5/7 (`g07_lierti_beach`, rotated)
- 雾言Misty · 海边 — 0/9 (`g08_misty_beach`)
- 我要吃西瓜 · 海边日落 — 6/6 (`g09_xigua_sunset`)
- 豚豚爱拍照 · 古风仙侠影棚 — 12/13 (`g10_tuntun_xianxia`)
- 不用紧张我拍的不好 · 汉服古建筑窄巷 — 7/7 (`g11_hanfu_alley`)

Rejected (18):
- g08_01–09 (9): AI-looking / doll-skin (painted hair texture, plastic skin, uncanny eyes)
- g02_03: collage (2 photos stacked)
- g05_01, g05_10: collage (2 photos stacked)
- g10_01: 3-panel collage cover, low-res
- g03_01, g03_02: not tasteful (low crouch / leg-forward seated framing in short-slit dress)
- g04_02: near-duplicate of g04_01
- g07_02: face-only crop, no pose value
- g07_05: open shirt, not tasteful

## Files DELETED
None.

## Files CHANGED (overwrite)
- `data/imported.json` (+73 → 606)
- `sw.js` (cache v4.0.0)
- `app.js` (VERSION 4.0.0)
- `tests/e2e.py` (version strings, 1/606)
- `README.md`

## Files ADDED
- `CHANGES-v40.md`
- `screenshots/v40-*.png` (from e2e)
- 73 × `imported/<id>.jpg` and `imported/thumbs/<id>.jpg`
