# UX 批次 1「阅读旅程核心」实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 依据 spec 实现批次 1 六项：章内小节 TOC、排版打磨（标点悬挂/主题自动档/深色白闪）、title 带章节名、章末反馈+时长、相邻卷空闲预取、小 bug 清扫。

**Architecture:** 纯静态 Vue 3 SPA（Vite + Vue Router hash + Pinia），无后端。批次 1 全部改动在 `web/` 前端，不动数据管线。唯一新组件是 `ChapterToc.vue`（≥1280px 右侧 sticky 栏），其余为既有文件的增量修改。

**Tech Stack:** Vue 3 `<script setup>`、Pinia、Vue Router 4 hash、Vite 8。

**Spec:** `docs/superpowers/specs/2026-08-01-ux-optimization-design.md`（批次 1 部分）

## Global Constraints

- **无测试框架**：每个任务的验证 = `cd web && npm run build` 通过 + `npm run dev`（:5173）手动走查该任务的走查项。不要引入测试框架。
- **提交规范**：中文 conventional commits，scope 用模块名（`feat(read)` / `fix(timeline)` / `feat(ui)`）。
- **动效约定**：reduced-motion 双保险（JS 判断 + CSS media query）；新 hover 样式必须包 `@media (hover: hover)`；固定视高用 `100dvh`（`100vh` 兜底写在前一行）。
- **静态资源/数据路径必须走 `utils/assetUrl()`**，禁止手写 `/` 开头的绝对路径（部署在 `/china-history/` 子路径）。
- **localStorage 键带 `zgts:` 前缀**；settings 新增/变更字段从 `saved` 读取时必须给默认值。
- **阅读页 `.reader-body` 是独立滚动容器**：scroll 不冒泡；IntersectionObserver 需显式传 `root`；其 DOM 随章节 keyed Transition 重建，滚动监听/观察器统一由 `watch(scrollEl, …, {flush:'post'})` 重挂，不在 onMounted 一次性绑定。
- **hash 路由是有意决策**，不改 history 模式。

---

### Task 1: progress store 返回"首次读完"标记

**Files:**
- Modify: `web/src/stores/progress.js`

**Interfaces:**
- Produces: `record(chId: string, percent: number) => boolean` —— 返回值语义变为"本次记录是否使该章**首次**达到 ≥98"（Task 4 依赖；现有唯一调用方 ReadView `flushRecord` 忽略返回值，向后兼容）

- [ ] **Step 1: 修改 record action**

`web/src/stores/progress.js` 的 `record` 改为：

```js
    record(chId, percent) {
      const prev = this.chapters[chId] || 0
      const next = Math.max(prev, Math.round(percent))
      this.chapters[chId] = next
      this.lastRead = chId
      this.persist()
      // 本次记录是否让该章首次达到"读完"（≥98）
      return prev < 98 && next >= 98
    },
```

- [ ] **Step 2: 构建验证**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

- [ ] **Step 3: Commit**

```bash
git add web/src/stores/progress.js
git commit -m "feat(read): 进度记录返回首次读完标记"
```

---

### Task 2: 章节头部细节 —— 时长估计 + 标签页标题 + 标点悬挂

**Files:**
- Modify: `web/src/views/ReadView.vue`

**Interfaces:**
- Consumes: 现有 `chapter` ref（含 `wordCount/title`）、`loadChapter()`
- Produces: `readMinutes` computed（模板内使用）；无跨任务接口

- [ ] **Step 1: 加 readMinutes computed**

`web/src/views/ReadView.vue` 在 `const dynasty = computed(...)` 之后加：

```js
// 阅读时长估计：按 400 字/分钟
const readMinutes = computed(() =>
  chapter.value ? Math.max(1, Math.ceil(chapter.value.wordCount / 400)) : 0,
)
```

- [ ] **Step 2: loadChapter 成功后设置标签页标题**

`loadChapter()` 中 `chapter.value = { ...ch, blocks: vc.blocks }` 之后加一行：

```js
    document.title = `${ch.title} · 中国通史学习`
```

（路由切换时 `router.afterEach` 会用路由 meta.title 覆盖，离开阅读页自动恢复，互不冲突。）

- [ ] **Step 3: 模板加时长 + sec 块不需要改动**

`.ch-meta` 块改为（在字数后加时长）：

```html
      <div class="ch-meta">
        <span>{{ chapter.wordCount.toLocaleString() }} 字</span>
        <span>约 {{ readMinutes }} 分钟</span>
        <span>{{ chapter.imageCount }} 幅插图</span>
        <span v-if="progress.chapters[chapter.id] >= 98">✓ 已读完</span>
      </div>
```

- [ ] **Step 4: 标点悬挂**

`.block-p` 样式改为：

```css
.block-p {
  margin: 0 0 1em;
  text-indent: 2em;
  text-align: justify;
  hanging-punctuation: first allow-end; /* 中文标点悬挂，不支持则无害降级 */
}
```

- [ ] **Step 5: 构建 + 走查**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

走查（`npm run dev`）：打开任意章节 → ① 浏览器标签页标题显示章节名；② 头部显示"约 X 分钟"；③ 切换到目录/首页后标题恢复。

- [ ] **Step 6: Commit**

```bash
git add web/src/views/ReadView.vue
git commit -m "feat(read): 章节时长估计 + 标签页标题带章节名 + 中文标点悬挂"
```

---

### Task 3: 主题自动档（跟随系统）+ 消除主题白闪

**Files:**
- Modify: `web/src/stores/settings.js`
- Modify: `web/src/App.vue`
- Modify: `web/index.html`

**Interfaces:**
- Consumes: 现有 `settings.theme` / `settings.setTheme(t)`、`reducedMotion()`（@/utils）
- Produces: theme 取值域扩为 `'auto' | 'paper' | 'sepia' | 'dark'`；`body[data-theme]` 始终是解析后的具体主题（auto 永不写入 DOM）——Task 外代码无需感知 auto

- [ ] **Step 1: settings 默认值改 auto**

`web/src/stores/settings.js` state 中：

```js
      theme: saved.theme ?? 'auto', // auto | paper | sepia | dark（auto 跟随系统深浅色）
```

（老用户 localStorage 已存 paper/sepia/dark，不受影响。）

- [ ] **Step 2: App.vue 主题解析逻辑**

`web/src/App.vue` script 中，把 `const themes = [...]` 到 `setTheme(settings.theme)` 整段替换为：

```js
const themes = [
  { id: 'auto', label: '自' },
  { id: 'paper', label: '纸' },
  { id: 'sepia', label: '褐' },
  { id: 'dark', label: '夜' },
]

// auto 档跟随系统深浅色；body[data-theme] 只写解析后的具体主题
const systemDark = window.matchMedia('(prefers-color-scheme: dark)')

const resolveTheme = (t) =>
  t === 'auto' ? (systemDark.matches ? 'dark' : 'paper') : t

function applyTheme(t, animate = false) {
  // 切换瞬间挂过渡类，全站颜色 300ms 渐变；首次加载与 reduced-motion 不触发
  if (animate && !reducedMotion()) {
    document.body.classList.add('theme-anim')
    setTimeout(() => document.body.classList.remove('theme-anim'), 350)
  }
  document.body.dataset.theme = resolveTheme(t)
}

function setTheme(t, animate = false) {
  settings.setTheme(t)
  applyTheme(t, animate)
}

setTheme(settings.theme)

function onSystemThemeChange() {
  if (settings.theme === 'auto') applyTheme('auto')
}

systemDark.addEventListener('change', onSystemThemeChange)
```

`onUnmounted` 中追加移除：

```js
  systemDark.removeEventListener('change', onSystemThemeChange)
```

（模板中 `:class="{ active: settings.theme === t.id }"` 与 `@click="setTheme(t.id, true)"` 无需改动，auto 作为第四个按钮自然生效。）

- [ ] **Step 3: index.html 防白闪内联脚本**

`web/index.html` 的 `<head>` 中、`<title>` 之前插入：

```html
    <script>
      // 防主题白闪：JS bundle 加载前预置 html 背景（与 settings store 读取逻辑一致）
      try {
        var s = JSON.parse(localStorage.getItem('zgts:settings') || '{}')
        var t = s.theme || 'auto'
        var r =
          t === 'auto'
            ? matchMedia('(prefers-color-scheme: dark)').matches
              ? 'dark'
              : 'paper'
            : t
        var bg = { paper: '#f6f1e7', sepia: '#efe0c7', dark: '#1e1d1b' }
        document.documentElement.style.background = bg[r] || bg.paper
      } catch (e) {}
    </script>
```

- [ ] **Step 4: 构建 + 走查**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

走查：① 主题按钮变 4 个，默认"自"；② DevTools → Rendering → Emulate `prefers-color-scheme: dark/light` 切换，auto 档整站跟随；③ 选"夜"后刷新页面无白闪（首帧即深色）；④ 选"纸"/"褐"刷新首帧即对应底色。

- [ ] **Step 5: Commit**

```bash
git add web/src/stores/settings.js web/src/App.vue web/index.html
git commit -m "feat(ui): 主题新增自动档（跟随系统）+ 消除主题白闪"
```

---

### Task 4: 读完一次提示 + 恢复进度提示去重

**Files:**
- Modify: `web/src/views/ReadView.vue`

**Interfaces:**
- Consumes: Task 1 的 `record(chId, percent) => boolean`；现有 `useToast()` 的 `toast(msg)`、`restoreScroll()`、`flushRecord()`
- Produces: 无跨任务接口

- [ ] **Step 1: flushRecord 首次读完 toast**

`web/src/views/ReadView.vue` 的 `flushRecord` 改为：

```js
function flushRecord() {
  clearTimeout(recordTimer)
  recordTimer = null
  if (!chapter.value) return
  scrollPct.value = currentPct()
  const isNewFinish = progress.record(chapter.value.id, scrollPct.value)
  if (isNewFinish) toast(`✓ 已读完《${chapter.value.title}》`)
}
```

- [ ] **Step 2: 恢复进度 toast 会话级去重**

`restoreScroll` 前加模块级 Set，函数改为：

```js
// 进度恢复提示：本次会话内每章只提示一次
const restoreToasted = new Set()

function restoreScroll() {
  const id = chapter.value?.id
  if (!id || !scrollEl.value) return
  const pct = progress.chapters[id]
  if (pct >= 2 && pct < 98) {
    nextTick(() => {
      const el = scrollEl.value
      if (!el) return
      const max = el.scrollHeight - el.clientHeight
      if (max > 0) {
        el.scrollTop = (pct / 100) * max
        if (!restoreToasted.has(id)) {
          restoreToasted.add(id)
          toast(`已从上次阅读的 ${Math.round(pct)}% 处继续`)
        }
      }
    })
  }
}
```

- [ ] **Step 3: 构建 + 走查**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

走查：① 把某章读到底 → toast「✓ 已读完《…》」只弹一次，再次滚动到底不弹；② 中途退出重进 → 恢复 toast 弹一次，同章再次进入不再弹；③ 换一章仍有各自的一次提示。

- [ ] **Step 4: Commit**

```bash
git add web/src/views/ReadView.vue
git commit -m "feat(read): 读完一次提示 + 恢复进度提示每章去重"
```

---

### Task 5: 相邻卷空闲预取

**Files:**
- Modify: `web/src/views/ReadView.vue`

**Interfaces:**
- Consumes: `loadVolume(volId)`（@/composables/useVolume，自带缓存 + in-flight 去重）
- Produces: 无跨任务接口

- [ ] **Step 1: loadChapter 末尾加预取**

`loadChapter()` 中 `document.title = ...`（Task 2 所加）之后加：

```js
    // 空闲时预取下一卷，跨卷翻章零 loading；失败静默（翻章时会自然重试）
    const nextVol = volId + 1
    if (nextVol <= 5) {
      const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 2000))
      idle(() => loadVolume(nextVol).catch(() => {}))
    }
```

- [ ] **Step 2: 构建 + 走查**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

走查：DevTools Network 面板打开任意章节 → 空闲后可见下一卷 `volN.json` 请求；翻到跨卷边界章（如卷 1 末章 → 卷 2 首章）→ 无 AppLoading 出现。

- [ ] **Step 3: Commit**

```bash
git add web/src/views/ReadView.vue
git commit -m "feat(read): 空闲预取下一卷，跨卷翻章零加载"
```

---

### Task 6: 章内小节 TOC（≥1280px 右侧 sticky 栏）

**Files:**
- Create: `web/src/components/ChapterToc.vue`
- Modify: `web/src/views/ReadView.vue`
- Modify: `web/src/App.vue`
- Modify: `web/src/style.css`

**Interfaces:**
- Consumes: 现有 `chapter.blocks`（`t==='sec'` 含 `title`）、`scrollEl`、`reducedMotion()`、Task 2 的 onScroll rAF 结构
- Produces: `ChapterToc` 组件 props `{ items: Array<{title: string, blockIndex: number}>, active: number }`，emit `jump(item)`；ReadView 内部 `tocItems / activeToc / jumpToSection`（无其他任务依赖）

- [ ] **Step 1: 创建 ChapterToc.vue**

完整内容：

```vue
<script setup>
// 章内小节导航：桌面宽屏（≥1280px）右侧 sticky 栏；点击跳转 + 滚动联动高亮
defineProps({
  items: { type: Array, required: true }, // [{ title, blockIndex }]
  active: { type: Number, default: -1 }, // 当前小节在 items 中的下标
})
const emit = defineEmits(['jump'])
</script>

<template>
  <nav class="chapter-toc" aria-label="本章小节">
    <div class="toc-title">本章小节</div>
    <button
      v-for="(s, i) in items"
      :key="s.blockIndex"
      class="toc-item"
      :class="{ active: i === active }"
      :aria-current="i === active ? 'true' : undefined"
      @click="emit('jump', s)"
    >
      {{ s.title }}
    </button>
  </nav>
</template>

<style scoped>
.chapter-toc {
  position: sticky;
  top: 76px;
  width: 200px;
  flex-shrink: 0;
  max-height: calc(100vh - 100px);
  max-height: calc(100dvh - 100px);
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 10px;
}

.toc-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 2px;
  padding: 0 8px 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
}

.toc-item {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--text-soft);
}

.toc-item.active {
  color: var(--accent);
  font-weight: 600;
  background: var(--bg-soft);
}

@media (hover: hover) {
  .toc-item:hover {
    background: var(--bg-soft);
    color: var(--accent);
  }
}
</style>
```

- [ ] **Step 2: ReadView 数据与交互**

`web/src/views/ReadView.vue`：

① import 区加：

```js
import ChapterToc from '@/components/ChapterToc.vue'
```

② 窄屏 mq 代码附近加宽屏 mq（与 narrowMq 同生命周期）：

```js
// ---- 宽屏章内小节 TOC（≥1280px 显示右侧栏） ----
const canToc = ref(window.matchMedia('(min-width: 1280px)').matches)
let wideMq = null

function onWideChange(e) {
  canToc.value = e.matches
}
```

`onMounted` 中加：

```js
  wideMq = window.matchMedia('(min-width: 1280px)')
  wideMq.addEventListener('change', onWideChange)
```

`onUnmounted` 中加：

```js
  wideMq?.removeEventListener('change', onWideChange)
```

③ `readMinutes` computed 后加：

```js
// ---- 章内小节 TOC ----
const tocItems = computed(() =>
  chapter.value
    ? chapter.value.blocks
        .map((b, i) => (b.t === 'sec' ? { title: b.title, blockIndex: i } : null))
        .filter(Boolean)
    : [],
)
const activeToc = ref(-1)

// scroll spy：高亮最后一个越过容器顶部（+80px 缓冲）的小节
function updateTocSpy() {
  const el = scrollEl.value
  if (!el || !tocItems.value.length) {
    activeToc.value = -1
    return
  }
  const secs = el.querySelectorAll('.block-sec')
  let cur = -1
  for (let i = 0; i < secs.length; i++) {
    if (secs[i].offsetTop <= el.scrollTop + 80) cur = i
    else break
  }
  activeToc.value = cur
}

function jumpToSection(s) {
  const el = scrollEl.value
  if (!el) return
  const target = el.querySelector(`[data-i="${s.blockIndex}"]`)
  if (!target) return
  el.scrollTo({
    top: target.offsetTop - 12,
    behavior: reducedMotion() ? 'auto' : 'smooth',
  })
}
```

④ `onScroll` 的 rAF 回调中、`scrollPct.value = currentPct()` 之后加一行：

```js
      updateTocSpy()
```

⑤ 章节切换后重置高亮 + 初始 spy：`watch(scrollEl, …)` 回调中 `restoreScroll()` 之后加：

```js
    updateTocSpy()
```

- [ ] **Step 3: ReadView 模板接入**

① sec 块加定位属性（`v-for` 内 `i` 即 blockIndex）：

```html
        <h3 v-if="b.t === 'sec'" class="block-sec reveal" :data-i="i" :style="revealStyle(i)">{{ b.title }}</h3>
```

② `.read-layout` 中、`.reader-col` 结束之后加：

```html
      <ChapterToc
        v-if="chapter && canToc && tocItems.length"
        :items="tocItems"
        :active="activeToc"
        @jump="jumpToSection"
      />
```

- [ ] **Step 4: 阅读页容器加宽**

`web/src/App.vue`：script 顶部 import 加 `import { useRoute } from 'vue-router'`，setup 中加 `const route = useRoute()`；模板 `<main>` 改为：

```html
  <main class="app-main" :class="{ 'read-wide': route.name === 'read' }">
```

`web/src/style.css` `.app-main` 规则后加：

```css
/* 阅读页加宽：容纳右侧小节 TOC 栏 */
.app-main.read-wide {
  max-width: 1400px;
}
```

- [ ] **Step 5: 构建 + 走查**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

走查：① 桌面 ≥1280px 打开有小节的章 → 右侧"本章小节"栏，点击跳转定位准确（smooth）；② 滚动正文高亮跟随；③ 无 sec 的章不显示该栏；④ 窗口缩到 <1280px 栏消失且布局不破；⑤ 首页/目录页宽度仍 1280 不变；⑥ 减少动态模式下 TOC 跳转瞬时。

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ChapterToc.vue web/src/views/ReadView.vue web/src/App.vue web/src/style.css
git commit -m "feat(read): 章内小节 TOC（≥1280px 右侧 sticky 栏，点击跳转 + 滚动高亮）"
```

---

### Task 7: 时间轴小 bug —— tooltip 过期 + Esc 搜索框不一致

**Files:**
- Modify: `web/src/components/DynastyTimeline.vue`
- Modify: `web/src/views/HomeView.vue`

**Interfaces:**
- Produces: DynastyTimeline 新增 emit `update:keyword`（HomeView 消费，清空输入框 v-model）

- [ ] **Step 1: 视图变化隐藏过期 tooltip**

`web/src/components/DynastyTimeline.vue` 关键词 watch 附近加：

```js
// 视图变化（拖拽/缩放/运镜）后 tooltip 位置与内容已过期，隐藏待下次 hover
watch(view, () => {
  tooltip.value.visible = false
})
```

- [ ] **Step 2: Esc 同步清空搜索框**

`defineProps` 之后加：

```js
const emit = defineEmits(['update:keyword'])
```

`onKey` 改为：

```js
function onKey(e) {
  if (e.key === 'Escape') {
    selected.value = null
    matchedDynasty.value = null
    emit('update:keyword', '') // 搜索框与匹配高亮一并复位
    resetView()
  }
}
```

- [ ] **Step 3: HomeView 绑定**

`web/src/views/HomeView.vue` 的 DynastyTimeline 用法改为：

```html
    <DynastyTimeline
      v-else
      :dynasties="dynasties.dynasties"
      :keyword="debouncedKeyword"
      @update:keyword="keyword = $event"
    />
```

（`keyword` 是输入框 v-model 的源 ref，清空后经 250ms 防抖同步给时间轴。）

- [ ] **Step 4: 构建 + 走查**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错

走查：① hover 朝代出 tooltip 后滚轮缩放 → tooltip 立即消失，无残留错位；② 搜索命中后按 Esc → 搜索框清空、高亮清除、视图复位全史。

- [ ] **Step 5: Commit**

```bash
git add web/src/components/DynastyTimeline.vue web/src/views/HomeView.vue
git commit -m "fix(timeline): 视图变化隐藏过期 tooltip + Esc 同步清空搜索框"
```

---

### Task 8: 全量走查与推送

**Files:** 无（仅验证）

- [ ] **Step 1: 最终构建**

Run: `cd web && npm run build`
Expected: `✓ built in` 无报错；dist 正常分包

- [ ] **Step 2: spec 走查清单全量过一遍**

按 spec「验证」节执行（`npm run dev`）：
- TOC：跳转/高亮/无 sec 不显示/<1280px 不显示
- 主题：auto 跟随系统、4 按钮、dark 刷新无白闪
- title 随章节变化；时长估计显示
- 读完 toast 一次；恢复 toast 同章不重复
- 跨卷翻章无 loading（Network 可见预取）
- 时间轴：缩放后 tooltip 消失；Esc 清空搜索框且高亮清除

- [ ] **Step 3: 推送**

```bash
git push
```

（push 触发 GitHub Actions 自动部署；线上验证 `https://kensou24.github.io/china-history/` 同走查清单抽查。）
