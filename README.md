# 中国通史 · 交互式学习网站

基于《中国通史》五卷本（中国社会科学院撰稿，卜宪群主编，EPUB）构建的交互式 Web 学习应用。
全书 100 章、约 93 万字、1054 幅插图，以「朝代时间轴」为核心导航，配合分卷阅读。

## 项目结构

```
.
├── 中国通史 五卷本….epub   # 原始数据（不入库）
├── scripts/                # Python 数据管线
│   ├── extract.py          # EPUB → meta.json + vol1..5.json（正文/小节/插图引用）
│   ├── images.py           # 图片提取 + WebP 缩略图压缩
│   └── dynasty.py          # 朝代序列表 + 章节朝代自动标注 → dynasties.json
├── data/                   # 管线生成的结构化数据（不入库，可重新生成）
└── web/                    # 前端（Vite + Vue 3 + Router + Pinia）
    └── public/
        ├── data/           # JSON 数据（构建时从 ../data 复制）
        └── images/         # WebP 缩略图
```

## 快速开始

```bash
# 1. 数据管线（Python 3）
python3 scripts/extract.py      # 提取正文与元数据 → data/
python3 scripts/images.py       # 提取并压缩图片 → data/images/
python3 scripts/dynasty.py      # 朝代标注 → data/dynasties.json

# 2. 前端（Node ≥ 18）
cd web
npm install
npm run dev        # 开发预览 http://localhost:5173
npm run build      # 生产构建 → web/dist
```

## 数据规格

- `data/meta.json`：五卷、100 章元数据（标题、字数、摘要、小节、图片清单、朝代归属）
- `data/vol1..5.json`：分卷正文（章节 → 段落 / 小节 / 插图引用）
- `data/dynasties.json`：朝代时间轴（起止年份、章节映射）

## 部署

纯静态站点：`npm run build` 后将 `web/dist/` 部署到任意静态托管（GitHub Pages / Nginx 等）即可。
