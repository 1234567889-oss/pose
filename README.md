# 拍照摆姿 — 人像摆姿参考 PWA

手机优先的离线 PWA：拍人像时翻照片找姿势、念口令、按连拍组合一步步拍。
内容以**真实照片**（你的小红书收藏）为主；内置的 126 个 SVG 示意姿势只是"还没导入照片时"的备用。

## 运行
    ./serve.sh 8080          # 然后打开 http://localhost:8080 （安装为 App 需要 HTTPS 或 localhost）
纯静态站点，无构建步骤，任何静态托管（GitHub Pages / Netlify / Cloudflare Pages 等）都能直接部署整个文件夹。

## 功能
- **图鉴**：两列瀑布流照片卡；集合切换 照片 / 示意图 / 全部；搜索（标题/口令/标签）；多维度标签筛选（同维度多选=或，跨维度=且，数字为当前可选数量）；仅看收藏；🎲 随机（遵守当前筛选）。
- **详情**：大图（先缩略图后原图渐进加载）、大字**口令**（点击放大，可朗读/复制）、全部标签（点击标签=筛选）、动作要点、拍摄建议、原帖链接；左右滑动/按钮/键盘切换；收藏、加入清单、标记已拍；`#pose=<id>` 深链接。
- **连拍**：14 组连拍组合（5-8 个动作），逐步模式（大字口令、进度点、可选自动翻页/自动朗读）；清单可"存为连拍"。
- **清单**：拍摄前挑选，拍摄时打勾，按清单逐个拍。
- **我的**：自建动作（上传照片 → IndexedDB，仅存本机，含名称/标签/口令）、主题（自动/浅/深）、离线保存全部缩略图、安装到主屏幕。
- 离线：Service Worker 预缓存外壳与数据，`/imported/` 照片按需缓存（最多 800 张）。

## 数据与标签体系
- `data/taxonomy.json`：标签体系，10 个维度 / 147 个标签（光线 14、场景 33、风格 20、情绪 12、体位 10、景别 5、机位 6、构图 10、道具 20、服装 17）。格式 `{dimensions:[{key,label,tags[],aliases{别名:标准标签}}]}`。**直接编辑即可增加标签/维度**；导入脚本遇到新值也会自动追加。筛选面板只显示当前集合里实际出现的标签。
- `data/poses.json`（126 个内置示意姿势，由 `tools/gen_builtin.py` 生成）、`data/sequences.json`（14 组连拍）、`data/imported.json`（照片姿势，**只由导入脚本写入**）、`imported/`（照片与 `thumbs/` 缩略图）、`data/sequences_user.json`（可选，自定义连拍）。
- 姿势对象：`{id,type:"builtin|image|custom",title,image/thumb 或 svg,w,h,source_url,kouling,tags:{光线..},extra:[],tips:[],shot:{},note,difficulty}`。

## 批量导入小红书收藏
1. 把图片放进一个文件夹（如 `incoming/`）。
2. `python3 tools/import.py --template incoming/meta.csv` 生成空白表格，按需填写（只有 `file` 必填）。
3. `python3 tools/import.py --images incoming --meta incoming/meta.csv`（先加 `--dry-run` 预览；需要 Pillow：`pip install pillow`）。

表格列：`file, title, source_url, kouling, tips(用 ; 分隔), note, difficulty(1-3), 焦段, tags` 以及各维度列
`光线 场景 风格 情绪 体位 景别 机位 构图 道具 服装`（列名可用中文、英文 key 或别名；一格多个值用 , ， ; 、 | 空格 分隔）。
`tags` 自由词会按标签/别名自动归入对应维度，认不出的进入"其他"。维度列里出现的新值会追加进 taxonomy（`--strict` 则丢弃并警告）。
照片复制为 ≤1600px JPEG + 480px 缩略图；id 是内容哈希，重复运行安全（跳过重复，已有条目补充非空新元数据）；写入是原子的。
其他参数：`--list-tags` 查看标签、`--data/--taxonomy/--dest` 指定路径。没有元数据的照片标为"未分类"，之后可以补表格再跑一遍。
也可以不用脚本：直接按上面的姿势对象格式编辑 `data/imported.json`。

## 测试
    python3 -m venv /tmp/v && /tmp/v/bin/pip install playwright pillow cairosvg && /tmp/v/bin/playwright install chromium
    /tmp/v/bin/python tests/e2e.py . shipped screenshots     # 约 57 项检查 @390x844：渲染、筛选、详情、滑动、收藏、清单、连拍、自建动作(IndexedDB)、深色、SW、可安装性、离线、零控制台错误
    /tmp/v/bin/python tests/shots.py <含照片的副本> <输出目录> <标签>   # 额外的照片版截图
`screenshots/` 中 `shipped-*` 是出厂状态（0 张照片，使用示意图）；`xhs-*` 是导入 8 篇小红书收藏后（135 张单人姿势照片）的截图；`pearl-*` 是再导入 12 篇广州珠江夜景人像笔记后（共 209 张）的截图。

## 灵感与许可
界面思路参考 [RuiC-PoseAtlas](https://hruiccc.github.io/RuiC-PoseAtlas/)（作者 hruiccc / RuiC，代码许可 MIT）：照片卡片 + 多维标签筛选 + 详情页 + 随机/收藏等。
**本项目没有复制其代码、图片或元数据**，全部为独立实现；其 README 说明图片与元数据版权归原作者/来源所有，因此这里未使用。
你从小红书保存的图片版权属于原作者，仅供个人学习参考，请勿公开再发布。

## 限制
内置姿势是火柴人式示意图；语音朗读取决于设备的 zh-CN 语音；自建动作只存在本机浏览器里；照片很多时首次"离线保存"会占用较多空间。
