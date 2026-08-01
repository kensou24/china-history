# 中国通史 · 交互式学习网站

基于《中国通史》五卷本（中国社会科学院撰稿，卜宪群主编，EPUB）构建的交互式 Web 学习应用。
全书 **5 卷 100 章 · 约 86.6 万字 · 979 幅插图**，以**朝代时间轴**为核心导航，配合分卷阅读。

## ✨ 功能

- **朝代时间轴**（首页）：横向 SVG 时间轴，史前→1912 年，并立政权（宋辽西夏金元）自动分层；
  滚轮缩放、hover 信息卡（起止年份 / 章节数）、点击朝代展开章节卡片
- **搜索联动**：输入人物 / 事件 / 朝代（如「汉武帝」「贞观之治」），时间轴自动定位并高亮对应朝代
- **智能阅读器**：正文渲染（段落 / 小节 / 插图 + 图注）、插图灯箱看原图、字号 / 行距 / 主题
  （纸 / 褐 / 夜）调节、阅读进度自动记忆（localStorage）、上下章导航
- **全书目录**：五卷章节卡片，按朝代标签 / 摘要搜索，已读标记

## 项目结构

```
.
├── 中国通史 五卷本….epub   # 原始数据（不入库）
├── scripts/                # Python 数据管线
│   ├── extract.py          # EPUB → meta.json + vol1..5.json（正文/小节/插图引用）
│   ├── images.py           # 插图提取 + WebP 缩略图压缩 + 原图归档
│   ├── dynasty.py          # 朝代序列表 + 100 章朝代标注 → dynasties.json（并回写 meta）
│   ├── validate.py         # 数据完整性校验
│   └── sync_web_assets.py  # data/ → web/public/ 同步
├── data/                   # 管线生成的结构化数据（不入库，可重新生成）
│   ├── meta.json           # 五卷 100 章元数据（标题/字数/摘要/朝代）
│   ├── vol1..5.json        # 分卷正文（blocks: p/sec/fig/cap）
│   ├── dynasties.json      # 25 朝代时间轴（起止年份/颜色/章节映射）
│   ├── images/             # WebP 缩略图（480px, 共 23MB）
│   └── images_orig/        # 原图归档（灯箱查看）
└── web/                    # 前端（Vite + Vue 3 + Vue Router + Pinia）
```

## 快速开始

```bash
# 1. 数据管线（Python 3，首次或数据变更后执行）
python3 scripts/extract.py           # 提取正文 → data/meta.json + vol1..5.json
python3 scripts/images.py            # 提取并压缩图片 → data/images (+ images_orig)
python3 scripts/dynasty.py           # 朝代标注 → data/dynasties.json + 回写 meta
python3 scripts/validate.py          # 校验（应 0 错误）
python3 scripts/sync_web_assets.py   # 同步到 web/public/

# 2. 前端（Node ≥ 18）
cd web
npm install
npm run dev        # 开发预览 http://localhost:5173
npm run build      # 生产构建 → web/dist
```

## 部署

纯静态站点，构建后将 `web/dist/` 部署到任意静态托管即可：

- **GitHub Pages**：`npm run build` 后推送 `dist/`（项目使用 hash 路由，无需服务端重写）
- **Nginx / Caddy**：`root /path/to/dist;`
- **本地**：`python3 -m http.server -d web/dist 8080`

注意：`dist/` 需包含 `data/`、`images/`、`images_orig/`（构建前先执行 `sync_web_assets.py`；
原图可跳过：`--skip-orig`，灯箱将回退显示缩略图）。

## 数据规格

`meta.json` 每章字段：`id / file / title / wordCount / summary / imageCount / dynasty`；
`volN.json` 章节 `blocks` 元素类型：`p`（正文段）、`sec`（小节标题）、`fig`（插图，`img` 为图片 id）、`cap`（独立图注）。
图片路径：`/images/{id}.webp`（缩略图）、`/images_orig/{id}.jpeg`（原图）。
