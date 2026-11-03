# v3.0.0 — remove built-in 示意图 (SVG diagram poses)

Local working copy only; nothing pushed, no zip built. Backup of the pre-change tree: `/tmp/pose-app-v2-backup` (box, not persistent guarantee).

## Files DELETED (delete these in the GitHub repo too)
- `assets/builtin/` — whole directory, 126 files (`b001.svg` … `b126.svg`)
- `tools/gen_builtin.py`
- `tools/pose_lib.py`
- `tools/pose_render.py`
- `tools/poses_lie.py`
- `tools/poses_sit.py`
- `tools/poses_squat_lie.py`
- `tools/poses_stand.py`
- `tools/poses_walk.py`
- `tools/preview.py`
- `tools/sequences_src.py`
- `data/poses.json`
- `data/sequences.json`
- `screenshots/shipped-1-home.png`
- `screenshots/shipped-2-filter-sheet.png`
- `screenshots/shipped-3-card.png`
- `screenshots/shipped-4-sequence-step.png`
- `screenshots/shipped-5-checklist.png`
- `screenshots/shipped-6-dark.png`

## Files CHANGED
- `app.js` — no poses.json / sequences.json loading; no 示意图/照片/全部 switch (`renderColl`, `S.coll`, `isPhoto`, builtin branches removed); stale favourites / checklist / own sequences (ids that no longer exist, e.g. b001…b126) are dropped silently and the cleaned values written back to localStorage; legacy `ps_coll` key removed; "about" line no longer counts 示意图.
- `index.html` — removed `#coll` segmented switch; empty-state banner text no longer mentions diagrams.
- `style.css` — removed `.seg.wide`, `.pc .badge`, `.pc.svg` rules.
- `sw.js` — VERSION `v2.2.0` → `v3.0.0`; precache list is now `./, index.html, style.css, app.js, manifest.webmanifest, assets/icon*.{svg,png}, data/taxonomy.json, data/imported.json`; removed the poses.json-driven SVG precache and the `/assets/builtin/` route. Old `ps-shell-v2.2.0` cache is deleted on activate.
- `data/taxonomy.json` — all 10 dimensions kept; tags no photo uses were removed (147 → 120 tags). Aliases untouched.
- `tools/import.py` — alias hits on a pruned tag now re-add that tag to the taxonomy (so later imports don't lose it).
- `tests/e2e.py` — rewritten for photo-only state (70 checks, incl. v2→v3 localStorage migration, `#pose=b001` deep link, no builtin requests, taxonomy has no unused tags, own-sequence flow). `tests/shots.py` unchanged.
- `README.md` — updated.
- `screenshots/` — added `v3-1-home … v3-6-dark`, `v3-a … v3-e` (photo shots). `xhs-*` / `pearl-*` kept as historical v2-UI shots.

## Files UNCHANGED but relevant
- `data/imported.json` (209 photos), `data/sequences_user.json` (`[]`, still loaded as optional), `imported/`, `assets/icon*`, `manifest.webmanifest`, `serve.sh`.

## Notes / decisions to confirm
- All 14 built-in 连拍 (`data/sequences.json`) consisted only of diagram poses (0 photo ids), so they were removed too. The 连拍 tab now lists only the user's own sequences (saved from the checklist) and shows "还没有连拍组合" when empty. Option: later generate photo-based sequences into `data/sequences_user.json`.
- The 我的 → 新建动作 tag picker lists taxonomy tags only; pruned ones (e.g. 室内窗边, 咖啡馆) are no longer offered there but can be typed into 其他标签. They come back automatically once an import uses them.
- Test result: `python tests/e2e.py . v3 screenshots` → 70/70 passed.
