# Web 用户体验优化 · 设计文档

日期：2026-08-01
状态：已获用户批准（方案 A + TOC 右侧 sticky 布局 + 批次 1 细节）

## 背景与目标

站点已上线（`https://kensou24.github.io/china-history/`），P0 bug 与首批体验项已修复。
本文档是剩余 UX 优化点的**全面清单**，按用户确认的约束组织：

- **受众场景**：深度阅读，桌面为主（移动端专项降级为长尾）
- **范围策略**：全面清单、分批实施；本轮实现批次 1

## 分批策略：按用户旅程（方案 A）

以深度阅读用户的完整旅程为主线：进得来（加载感知）→ 读得顺（章内导航/排版）→
读得完（章末反馈）→ 找得到（目录/搜索/定位）。每批交付后核心路径都有可感知提升。

---

## 批次 1 · 阅读旅程核心（本轮实现）

### 1. 章内小节 TOC（新组件 `ChapterToc.vue`）

- **布局**：阅读页 `app-main` 放宽至 1400px（App.vue 按 `route.name === 'read'` 加修饰类，
  其他页不变）；右侧 sticky 栏（约 200px，`top: 76px` 与 rail 对齐），
  **≥1280px 显示，窄屏不渲染**（窄屏保持 fab 抽屉模式，不冲突）
- **数据**：`chapter.blocks` 中 `t === 'sec'` 提取为 `tocItems`（`{ title, blockIndex }`）；
  sec 标题渲染时加 `data-i` 属性用于定位；无 sec 的章不渲染该栏
- **交互**：
  - 点击 → `reader-body.scrollTo({ top: secEl.offsetTop - 12 })`，reduced-motion 瞬时
  - scroll spy：复用 ReadView 现有 rAF 合帧的 `onScroll`，
    高亮最后一个 `offsetTop <= scrollTop + 阈值` 的小节
- **错误处理**：TOC 为空不渲染；章节切换（keyed Transition 重建 DOM）后
  由既有 `watch(scrollEl, flush: 'post')` 统一重挂，与滚动监听同一生命周期

### 2. 排版打磨

- `.block-p` 加 `hanging-punctuation: first allow-end`（不支持浏览器无害降级）
- **主题新增"自动"档**：主题切换组变 4 按钮（自/纸/褐/夜）；
  `settings.theme` 默认值改 `'auto'`（老用户 localStorage 已存值不受影响）；
  auto 时 App.vue 解析 `prefers-color-scheme` 并监听系统切换，
  `body[data-theme]` 始终写解析后的具体主题（paper/dark），sepia 不参与自动
- **深色白闪修复**：`index.html` `<head>` 内联 ~10 行脚本，JS bundle 加载前
  读 `localStorage['zgts:settings']` 的 theme（含 auto 解析），
  为 dark 时提前给 `html` 铺深色背景；App mount 后 body 背景接管，颜色一致

### 3. document.title 带章节名

- `loadChapter` 成功后 `document.title = `${chapter.title} · 中国通史学习``；
  路由切换时 `router.afterEach` 照旧覆盖，互不冲突

### 4. 章末反馈 + 时长估计

- 章节头部 meta 行加"约 X 分钟"（`Math.ceil(wordCount / 400)`）
- `progress.record` 返回值改为 `{ isNewFinish }`（首次跨 98 为 true）；
  ReadView `flushRecord` 中首次读完时 toast「✓ 已读完《章节名》」

### 5. 相邻卷空闲预取

- `loadChapter` 完成后：`requestIdleCallback`（Safari 降级 `setTimeout(2000)`）
  调 `loadVolume(volId + 1)`（≤5 时）；失败静默（loadVolume 已缓存 + in-flight 去重，
  翻章时自然重试）。跨卷翻章零 loading

### 6. 小 bug 清扫

| 问题 | 修法 |
|---|---|
| 时间轴缩放/拖拽后 tooltip 残留 | `watch(view)` 中 `tooltip.visible = false`、`hover = null` |
| Esc 复位后搜索框文字与匹配高亮不一致 | DynastyTimeline Esc 时 `emit('update:keyword', '')`，HomeView 绑定更新 |
| 进度恢复 toast 每章每次进入都弹 | ReadView 会话级 `Set` 记录已提示章节，每章只弹一次 |

### 错误处理与边界（批次 1 通用）

- 无 sec 章 → 无 TOC 栏；预取失败 → 静默；旧 theme 值（paper/sepia/dark）兼容
- reduced-motion：TOC 跳转瞬时完成；不引入新动画（遵循仓库双保险约定）
- a11y：TOC 用 `<nav aria-label="本章小节">`，当前小节 `aria-current="true"`

### 验证（无测试框架，手动走查）

1. `npm run build` 通过
2. dev server 走查清单：
   - TOC：点击跳转定位准确、滚动高亮跟随、无 sec 章不显示、<1280px 不显示
   - 主题：auto 跟随系统（切系统深浅色验证）、4 按钮切换、dark 下刷新无白闪
   - title 随章节变化；时长估计显示合理
   - 读完 toast 只弹一次（刷新后再读到底不弹）；翻章恢复 toast 同章不重复
   - 跨卷翻章无 loading（预取生效，DevTools Network 可见预取请求）
   - 时间轴：缩放后 tooltip 消失；Esc 后搜索框清空且高亮清除
3. 数据未变，无需跑 `validate.py`

---

## 批次 2 · 导航与定位（下一轮，仅列清单）

1. **目录页朝代筛选 chips**：25 朝代横排过滤，与搜索框并存
2. **阅读页 ↔ 时间轴联动**：阅读页加"在时间上定位"入口跳首页选中该朝代；
   时间轴选中状态同步 URL（刷新/分享保留）
3. **灯箱增强**：原图加载进度、双击/滚轮缩放、左右键切换同章插图
4. **全文搜索**（纯前端，不动管线）：空闲时后台加载 volN.json，
   跨章搜索正文段落 → 结果列表 → 跳转章节并定位段落

## 批次 3 · 长尾（有空再做，仅列清单）

1. PWA（manifest + Service Worker 离线缓存已加载内容）
2. a11y 收尾：时间轴 svg `role` 修正（img → group/application）、
   灯箱焦点陷阱、章节卡片区 aria-live
3. 移动端专项：reader-body 独立滚动容器改页面滚动的可行性评估、
   触控目标 ≥44px、时间轴初始视野引导
4. og:image / 社交分享卡片 meta

## 明确不做的（YAGNI）

- 不做历史路由模式（hash 路由是静态部署的有意决策）
- 不做账号体系/云端进度同步（违反"无后端"约束）
- 不做移动端专项进批次 1（受众为桌面深度阅读）
- 不为全文搜索改数据管线（纯前端空闲加载已够用）
