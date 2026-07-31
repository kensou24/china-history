<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMeta } from '@/composables/useMeta'

const props = defineProps({
  dynasties: { type: Array, required: true },
  keyword: { type: String, default: '' },
})

const { chapterById } = useMeta()
const selected = ref(null)
const hover = ref(null)
const tooltip = ref({ x: 0, y: 0, visible: false, d: null })
const svgRef = ref(null)
const matchedDynasty = ref(null)

// ---- 时间映射：史前段压缩，其余线性 ----
const T_PRE_START = -3000
const T_PRE_END = -2070
const T_LIN_END = 1912
const PRE_FRAC = 0.08

// 全史 scale：年份 → 0..1
function scaleYear(y) {
  if (y <= T_PRE_END) {
    return ((y - T_PRE_START) / (T_PRE_END - T_PRE_START)) * PRE_FRAC
  }
  return PRE_FRAC + ((y - T_PRE_END) / (T_LIN_END - T_PRE_END)) * (1 - PRE_FRAC)
}

// 视图窗口（年份），默认全史
const view = ref({ start: T_PRE_START, end: T_LIN_END })

// 窗口内归一化 x
function xOf(y) {
  const { start, end } = view.value
  const denom = scaleYear(end) - scaleYear(start)
  if (denom <= 0) return 0
  return ((scaleYear(y) - scaleYear(start)) / denom) * 1000
}

const widthOf = (d) => Math.max(0, xOf(d.end) - xOf(d.start))

const VIEW_W = 1000
const VIEW_H = 96
const BAR_Y = 10
const BAR_H = 56

// 可见范围内的朝代
const visible = computed(() =>
  props.dynasties
    .map((d) => ({
      ...d,
      x: xOf(d.start),
      w: widthOf(d),
    }))
    .filter((d) => d.w > 0.4),
)

const yearLabel = (y) => (y < 0 ? `前${-y}` : `${y}`)

// ---- 缩放 ----
function zoom(factor, centerYear) {
  const cur = view.value
  const span = cur.end - cur.start
  const newSpan = span * factor
  if (newSpan < 60) return // 最小窗口 60 年
  if (newSpan > T_LIN_END - T_PRE_START) {
    view.value = { start: T_PRE_START, end: T_LIN_END }
    return
  }
  const c = centerYear ?? (cur.start + cur.end) / 2
  const half = newSpan / 2
  let s = c - half
  let e = c + half
  if (s < T_PRE_START) {
    e += T_PRE_START - s
    s = T_PRE_START
  }
  if (e > T_LIN_END) {
    s -= e - T_LIN_END
    e = T_LIN_END
  }
  view.value = { start: Math.max(T_PRE_START, s), end: Math.min(T_LIN_END, e) }
}

function zoomIn() {
  zoom(0.6)
}

function zoomOut() {
  zoom(1 / 0.6)
}

function resetView() {
  view.value = { start: T_PRE_START, end: T_LIN_END }
  selected.value = null
  matchedDynasty.value = null
}

// 滚轮缩放（以鼠标位置为锚点）
function onWheel(e) {
  e.preventDefault()
  const rect = svgRef.value.getBoundingClientRect()
  const ratio = (e.clientX - rect.left) / rect.width
  const yearAtCursor = view.value.start + (view.value.end - view.value.start) * ratio
  zoom(e.deltaY > 0 ? 1.25 : 0.8, yearAtCursor)
}

// ---- hover / tooltip ----
function onMove(d, e) {
  hover.value = d
  const rect = svgRef.value.getBoundingClientRect()
  tooltip.value = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
    visible: true,
    d,
  }
}

function onLeave() {
  hover.value = null
  tooltip.value.visible = false
}

function select(d) {
  selected.value = selected.value?.id === d.id ? null : d
}

// ---- 搜索联动 ----
watch(
  () => props.keyword,
  (kw) => {
    const q = kw.trim()
    if (!q) {
      matchedDynasty.value = null
      return
    }
    const hit = props.dynasties.find((d) => {
      if (d.name.includes(q)) return true
      if (d.alias.some((a) => a.includes(q))) return true
      return d.chapterIds.some((id) => chapterById(id)?.title.includes(q))
    })
    if (hit) {
      matchedDynasty.value = hit.id
      // 定位到该朝代
      const pad = Math.max(40, (hit.end - hit.start) * 0.3)
      view.value = {
        start: Math.max(T_PRE_START, hit.start - pad),
        end: Math.min(T_LIN_END, hit.end + pad),
      }
    } else {
      matchedDynasty.value = null
    }
  },
)

// 键盘 Esc 关闭
function onKey(e) {
  if (e.key === 'Escape') {
    selected.value = null
    matchedDynasty.value = null
    resetView()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  svgRef.value?.addEventListener('wheel', onWheel, { passive: false })
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  svgRef.value?.removeEventListener('wheel', onWheel)
})

const chaptersOf = (d) => d.chapterIds.map((id) => chapterById(id)).filter(Boolean)

// 缩放控制条
const controlsVisible = computed(
  () => view.value.start > T_PRE_START || view.value.end < T_LIN_END,
)
</script>

<template>
  <div class="timeline">
    <!-- 缩放控制 -->
    <div class="zoom-controls">
      <button @click="zoomIn" title="放大">＋</button>
      <button @click="zoomOut" title="缩小">－</button>
      <button v-if="controlsVisible" @click="resetView" title="回到全史">全史</button>
    </div>

    <!-- SVG 时间轴 -->
    <svg
      ref="svgRef"
      :viewBox="`0 0 ${VIEW_W} ${VIEW_H}`"
      class="axis-svg"
      @wheel.prevent="onWheel"
    >
      <!-- 年份刻度 -->
      <line :x1="xOf(view.start)" y1="0" :x2="xOf(view.end)" y2="0" class="axis-line" />

      <!-- 朝代区块 -->
      <g v-for="d in visible" :key="d.id">
        <rect
          :x="d.x"
          :y="BAR_Y"
          :width="d.w"
          :height="BAR_H"
          rx="4"
          :fill="d.color"
          :class="{
            'dyn-rect': true,
            active: selected?.id === d.id,
            matched: matchedDynasty === d.id,
            hovered: hover?.id === d.id,
          }"
          @mousemove="onMove(d, $event)"
          @mouseleave="onLeave"
          @click="select(d)"
        >
          <title>{{ d.name }} {{ yearLabel(d.start) }}—{{ yearLabel(d.end) }}</title>
        </rect>

        <!-- 朝代名（宽度足够时显示） -->
        <text
          v-if="d.w > 52"
          :x="d.x + d.w / 2"
          :y="BAR_Y + BAR_H / 2 - 4"
          text-anchor="middle"
          class="dyn-label"
        >
          {{ d.name }}
        </text>
        <text
          v-if="d.w > 76"
          :x="d.x + d.w / 2"
          :y="BAR_Y + BAR_H / 2 + 13"
          text-anchor="middle"
          class="dyn-years-label"
        >
          {{ yearLabel(d.start) }}—{{ yearLabel(d.end) }}
        </text>
      </g>

      <!-- 底部年份刻度线 -->
      <g v-for="y in [-2070, -221, 0, 220, 618, 960, 1271, 1644, 1912]" :key="y">
        <line
          v-if="xOf(y) > 0 && xOf(y) < VIEW_W"
          :x1="xOf(y)"
          y1="BAR_Y + BAR_H"
          :x2="xOf(y)"
          y2="BAR_Y + BAR_H + 5"
          class="tick"
        />
        <text
          v-if="xOf(y) > 0 && xOf(y) < VIEW_W"
          :x="xOf(y)"
          :y="VIEW_H - 2"
          text-anchor="middle"
          class="tick-label"
        >
          {{ yearLabel(y) }}
        </text>
      </g>
    </svg>
    <div class="axis-hint">滚轮缩放 · 点击朝代查看章节 · Esc 复位</div>

    <!-- hover 信息卡 -->
    <div
      v-if="tooltip.visible && tooltip.d"
      class="tooltip"
      :style="{ left: tooltip.x + 14 + 'px', top: tooltip.y - 12 + 'px' }"
    >
      <strong>{{ tooltip.d.name }}</strong>
      <span>{{ yearLabel(tooltip.d.start) }} — {{ yearLabel(tooltip.d.end) }}</span>
      <span>所属章节 {{ tooltip.d.chapterIds.length }} 章</span>
    </div>

    <!-- 选中朝代 → 章节卡片 -->
    <section v-if="selected" class="dyn-chapters">
      <h2>
        {{ selected.name }}（{{ yearLabel(selected.start) }}—{{ yearLabel(selected.end) }}）
        · {{ selected.chapterIds.length }} 章
      </h2>
      <div class="chapter-grid">
        <router-link
          v-for="c in chaptersOf(selected)"
          :key="c.id"
          :to="`/read/${c.id}`"
          class="chapter-card"
        >
          <h3>{{ c.title }}</h3>
          <p class="summary">{{ c.summary }}</p>
          <div class="meta">
            <span>{{ c.wordCount.toLocaleString() }} 字</span>
            <span>{{ c.imageCount }} 图</span>
          </div>
        </router-link>
      </div>
    </section>

    <p v-else class="hint">点击朝代区块，查看该朝代对应的全部章节 →</p>
  </div>
</template>

<style scoped>
.timeline {
  position: relative;
}

.zoom-controls {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.zoom-controls button {
  min-width: 30px;
  font-size: 14px;
}

.axis-svg {
  width: 100%;
  height: auto;
  display: block;
  cursor: grab;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 0 0;
}

.axis-line {
  stroke: var(--border);
  stroke-width: 1;
}

.dyn-rect {
  cursor: pointer;
  transition: filter 0.15s, opacity 0.15s;
}

.dyn-rect:hover,
.dyn-rect.hovered {
  filter: brightness(1.15);
}

.dyn-rect.active {
  stroke: var(--text);
  stroke-width: 3;
}

.dyn-rect.matched {
  stroke: var(--text);
  stroke-width: 2.5;
  stroke-dasharray: 5 3;
  filter: brightness(1.25);
}

.dyn-label {
  font-size: 13px;
  font-weight: 700;
  fill: #fff;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}

.dyn-years-label {
  font-size: 10px;
  fill: #fff;
  pointer-events: none;
  opacity: 0.92;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}

.tick {
  stroke: var(--text-soft);
  stroke-width: 1;
}

.tick-label {
  font-size: 9.5px;
  fill: var(--text-soft);
}

.axis-hint {
  font-size: 12px;
  color: var(--text-soft);
  margin-top: 4px;
}

.tooltip {
  position: absolute;
  z-index: 20;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 8px 12px;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  pointer-events: none;
  white-space: nowrap;
}

.dyn-chapters {
  margin-top: 24px;
}

.dyn-chapters h2 {
  font-size: 20px;
  color: var(--accent);
  margin: 0 0 14px;
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.hint {
  color: var(--text-soft);
  font-size: 13px;
  margin-top: 14px;
}
</style>
