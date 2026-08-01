# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于《中国通史》五卷本 EPUB 的交互式学习网站：Python 离线数据管线 + 纯静态 Vue 3 SPA。
**没有也不引入后端**——所有内容经管线预生成为静态 JSON，用户状态仅存 localStorage，部署目标是任意静态托管。

## 常用命令

```bash
# 数据管线（仓库根目录，Python 3；首次或 EPUB/标注变更后按序执行）
python3 scripts/extract.py           # EPUB → data/meta.json + vol1..5.json
python3 scripts/images.py            # 插图 → data/images（WebP 缩略图）+ images_orig（原图）
python3 scripts/dynasty.py           # 朝代标注 → data/dynasties.json（并回写 meta.json 的 dynasty 字段）
python3 scripts/validate.py          # 数据完整性校验（应输出 0 错误）
python3 scripts/sync_web_assets.py   # data/ → web/public/（--skip-orig 跳过原图）

# 前端（Node ≥ 18，web/ 目录）
cd web
npm install
npm run dev        # 开发 http://localhost:5173
npm run build      # 产物 web/dist（部署前须先 sync_web_assets）
```

没有 lint / 单元测试配置；`validate.py` 是唯一的数据校验手段。改动数据管线后跑一遍它。

## 架构总览

### 单向数据流
`EPUB → scripts/ → data/（不入库，可再生）→ sync → web/public/ → 前端 fetch 静态 JSON`。
前端永不写数据；所有"动态"都是纯前端计算。

### 前端（Vite + Vue 3 `<script setup>` + Vue Router 4 hash 模式 + Pinia）
- **hash 路由是有意的**：静态托管无需服务端 rewrite，不要改成 history 模式。
- 三条路由：`/` 时间轴首页（HomeView + DynastyTimeline）、`/catalog` 目录、`/read/:id` 阅读器。
- **数据缓存模型**（`composables/`）：
  - `useMeta.js`：meta.json + dynasties.json，模块级单例，全站只加载一次；暴露 `meta / dynasties / chapterById / dynastyById`。
  - `useVolume.js`：volN.json 按卷懒加载 + Map 缓存。ReadView 用 `currentVol` 记住当前卷，**同卷翻章不再触发 loading**——跨卷才显示加载态。
- **用户状态**（localStorage，键名带 `zgts:` 前缀）：`stores/progress.js`（`zgts:progress`，每章 0-100 进度 + lastRead，≥98 判读完）、`stores/settings.js`（`zgts:settings`，字号/行距/主题/railCollapsed）。新增偏好字段时注意从 `saved` 读取要给默认值。
- 无 UI 组件库、无 TypeScript，全局样式在 `web/src/style.css`，主题用 CSS 变量 + `body[data-theme]` 切换。

### 内容数据规格
- 章节 blocks 只有四种类型：`p`（段落）/ `sec`（小节标题）/ `fig`（插图+图注）/ `cap`（独立图注）。
- `dynasties.json`：25 朝代，年份为整数（负数为公元前），含 `color / alias[] / chapterIds[]`。
- 图片路径：`/images/{id}.webp`（480px 缩略）、`/images_orig/{id}.jpeg`（灯箱原图，可能不存在→需回退缩略图）。

## 交互动效约定（本仓库的"游戏感"体系）

改交互时保持既有模式，不要另起炉灶：

- **reduced-motion 双保险**：JS 侧（动画前判 `matchMedia('(prefers-reduced-motion: reduce)')`，跳过观察器/改瞬时）+ CSS 侧（组件内 `@media (prefers-reduced-motion: reduce)` 强制终态可见）。只写一边会出 bug（如元素永远 opacity 0）。
- **滚动浮现**：IntersectionObserver + `.reveal/.revealed` 类，首批元素给 stagger delay，**揭示后必须清掉 transitionDelay**（否则拖累 hover 反馈）；transform+opacity，不做会引发布局位移的动画。
- **视图动画模型**（DynastyTimeline）：`view`（当前）与 `targetView`（目标）分离，`setView` 统一入口（含 `flightTimer` 清理）；任何手动接管（pointerdown/wheel/minimap 拖拽）必须先取消进行中的动画与惯性。
- **主题切换过渡**：不常驻全局 `*` 过渡，而是切换瞬间挂 `body.theme-anim` 类 350ms（App.vue setTheme）。

## 已知坑（踩过，别再踩）

- **`position: fixed` 在 transform 中的父元素内会失效**：所以阅读进度条必须放在章节滑动 Transition 容器之外。
- **`.reader-body` 是独立滚动容器**：其 scroll 事件不冒泡（App.vue 顶栏自动隐藏用 capture 阶段监听才能捕获）；IntersectionObserver 要显式传 `root`。
- **DynastyTimeline 用 svg 层手动命中检测**（`setPointerCapture` 会吞掉 rect 自身的 click/mousemove），新增可点元素走 `dynastyAtClient` 而非给 rect 加事件。
- **章节 keyed Transition out-in 下 DOM 会重建**：滚动监听/进度恢复/观察器统一由 `watch(scrollEl, …, {flush:'post'})` 重挂，不要在 onMounted 里一次性绑定。
- SVG 元素上 CSS transform 的原点与 HTML 不同；朝代块的高亮用 filter/opacity，不用 transform。

## 提交规范

中文 conventional commits，scope 用模块名：`feat(ui): …` / `fix(timeline): …` / `fix(read): …` / `feat(read): …`。
标题一行说清改动，body 列要点；EPUB 与 `data/` 不入库。
