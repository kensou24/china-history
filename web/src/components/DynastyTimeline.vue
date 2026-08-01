<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
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
const timelineRef = ref(null)
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
const targetView = ref(null)
let animId = null
let flightTimer = null

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function setView(v, animate = true, dur = 350) {
  clearTimeout(flightTimer)
  targetView.value = { ...v }
  cancelAnimationFrame(animId)
  if (!animate || reducedMotion()) {
    view.value = { ...v }
    return
  }
  const from = { ...view.value }
  const t0 = performance.now()
  function step(now) {
    const p = Math.min(1, (now - t0) / dur)
    const e = easeInOutCubic(p)
    view.value = {
      start: from.start + (targetView.value.start - from.start) * e,
      end: from.end + (targetView.value.end - from.end) * e,
    }
    if (p < 1) {
      animId = requestAnimationFrame(step)
    }
  }
  animId = requestAnimationFrame(step)
}

// 窗口内归一化 x
function xOf(y) {
  const { start, end } = view.value
  const denom = scaleYear(end) - scaleYear(start)
  if (denom <= 0) return 0
  return ((scaleYear(y) - scaleYear(start)) / denom) * 1000
}

const widthOf = (d) => Math.max(0, xOf(d.end) - xOf(d.start))

const VIEW_W = 1000
const ROW_H = 56
const ROW_GAP = 6

// 可见范围内的朝代（按时间排序）
const ordered = computed(() =>
  props.dynasties
    .map((d) => ({ ...d, x: xOf(d.start), w: widthOf(d) }))
    .filter((d) => d.w > 0.4)
    .sort((a, b) => a.start - b.start),
)

// 贪心分层：并立朝代（时间重叠，如宋辽西夏金元）自动分配到不同行
const layout = computed(() => {
  const rows = []
  for (const d of ordered.value) {
    let placed = false
    for (const row of rows) {
      const last = row[row.length - 1]
      if (last.end <= d.start) {
        row.push(d)
        placed = true
        break
      }
    }
    if (!placed) rows.push([d])
  }
  return rows
})

const visible = computed(() =>
  layout.value.flatMap((row, ri) => row.map((d) => ({ ...d, row: ri }))),
)

const viewH = computed(() => layout.value.length * (ROW_H + ROW_GAP) + 26)
const rowY = (row) => 6 + row * (ROW_H + ROW_GAP)

const yearLabel = (y) => (y < 0 ? `前${-y}` : `${y}`)

// ---- 缩放 ----
function zoom(factor, centerYear, animate = true, dur = 350) {
  const cur = targetView.value || view.value
  const span = cur.end - cur.start
  const newSpan = span * factor
  if (newSpan < 60) return // 最小窗口 60 年
  if (newSpan > T_LIN_END - T_PRE_START) {
    setView({ start: T_PRE_START, end: T_LIN_END }, animate, dur)
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
  setView({ start: Math.max(T_PRE_START, s), end: Math.min(T_LIN_END, e) }, animate, dur)
}

function zoomIn() {
  zoom(0.6)
}

function zoomOut() {
  zoom(1 / 0.6)
}

// 搜索镜头飞行：先拉远到同时容纳当前与目标的视野，再推近到目标；
// 目标本就在视野附近时直接缓动，不做无谓的拉远
function flyTo(target) {
  if (reducedMotion()) {
    setView(target, false)
    return
  }
  const from = targetView.value || view.value
  const unionSpan = Math.max(from.end, target.end) - Math.min(from.start, target.start)
  const pad = Math.max(30, unionSpan * 0.08)
  const mid = {
    start: Math.max(T_PRE_START, Math.min(from.start, target.start) - pad),
    end: Math.min(T_LIN_END, Math.max(from.end, target.end) + pad),
  }
  if ((mid.end - mid.start) / (from.end - from.start) < 1.15) {
    setView(target, true, 450)
    return
  }
  setView(mid, true, 300)
  flightTimer = setTimeout(() => setView(target, true, 380), 290)
}

function resetView() {
  selected.value = null
  matchedDynasty.value = null
  setView({ start: T_PRE_START, end: T_LIN_END })
}

function yearAtClientX(cx) {
  const rect = svgRef.value.getBoundingClientRect()
  const ratio = (cx - rect.left) / rect.width
  const s = scaleYear(view.value.start)
  const e = scaleYear(view.value.end)
  const targetScale = s + (e - s) * ratio
  // 反向映射
  if (targetScale <= PRE_FRAC) {
    return T_PRE_START + (targetScale / PRE_FRAC) * (T_PRE_END - T_PRE_START)
  }
  return T_PRE_END + ((targetScale - PRE_FRAC) / (1 - PRE_FRAC)) * (T_LIN_END - T_PRE_END)
}

// 滚轮缩放（以鼠标位置为锚点，短时长缓动让连续滚动平滑追赶目标）
function onWheel(e) {
  e.preventDefault()
  stopMomentum()
  const c = yearAtClientX(e.clientX)
  zoom(e.deltaY > 0 ? 1.25 : 0.8, c, true, 180)
}

// ---- 拖拽惯性 ----
let vel = 0 // 拖拽速度（px/ms）
let lastMoveT = 0
let lastMoveX = 0
let momentumId = null

function stopMomentum() {
  cancelAnimationFrame(momentumId)
  momentumId = null
  vel = 0
}

// 按像素增量平移视图（带回弹边界），返回 false 表示撞到边缘
function panByPx(dxPx) {
  const rect = svgRef.value?.getBoundingClientRect()
  if (!rect) return false
  const span = view.value.end - view.value.start
  const yearDx = -(dxPx / rect.width) * span
  let s = view.value.start + yearDx
  let e = view.value.end + yearDx
  let clamped = false
  if (s < T_PRE_START) {
    e += T_PRE_START - s
    s = T_PRE_START
    clamped = true
  }
  if (e > T_LIN_END) {
    s -= e - T_LIN_END
    e = T_LIN_END
    clamped = true
  }
  view.value = { start: s, end: e }
  targetView.value = { start: s, end: e }
  return !clamped
}

// 松手后的惯性滑行：按初速度继续平移，指数衰减
function startMomentum() {
  if (reducedMotion() || Math.abs(vel) < 0.05) {
    vel = 0
    return
  }
  let prevT = performance.now()
  const step = (now) => {
    const dt = Math.min(50, now - prevT)
    prevT = now
    if (!panByPx(vel * dt)) {
      stopMomentum()
      return
    }
    vel *= Math.exp(-dt / 180)
    if (Math.abs(vel) < 0.02) {
      stopMomentum()
      return
    }
    momentumId = requestAnimationFrame(step)
  }
  momentumId = requestAnimationFrame(step)
}

// ---- 拖拽 / 触摸平移与缩放 ----
const pointers = new Map()
const dragStart = ref(null)
const suppressClick = ref(false)

function distance(p1, p2) {
  const dx = p1.x - p2.x
  const dy = p1.y - p2.y
  return Math.sqrt(dx * dx + dy * dy)
}

function midYear(p1, p2) {
  return yearAtClientX((p1.x + p2.x) / 2)
}

function onPointerDown(e) {
  if (!svgRef.value) return
  cancelAnimationFrame(animId)
  clearTimeout(flightTimer)
  stopMomentum()
  lastMoveT = 0
  lastMoveX = e.clientX
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  svgRef.value.setPointerCapture(e.pointerId)
  dragStart.value = { x: e.clientX, yearStart: view.value.start, yearEnd: view.value.end }
  suppressClick.value = false
}

// 命中检测：把视口坐标转成 SVG 用户坐标，找到包含该点的朝代块
function dynastyAtClient(cx, cy) {
  const svg = svgRef.value
  if (!svg) return null
  const ctm = svg.getScreenCTM()
  if (!ctm) return null
  const pt = svg.createSVGPoint()
  pt.x = cx
  pt.y = cy
  const p = pt.matrixTransform(ctm.inverse())
  return (
    visible.value.find((d) => {
      const y0 = rowY(d.row)
      return p.x >= d.x && p.x <= d.x + d.w && p.y >= y0 && p.y <= y0 + ROW_H
    }) || null
  )
}

function onPointerMove(ev) {
  if (!pointers.has(ev.pointerId)) {
    // 未按下（hover）：命中检测显示 tooltip
    const d = dynastyAtClient(ev.clientX, ev.clientY)
    if (d) {
      hover.value = d
      const rect = svgRef.value.getBoundingClientRect()
      tooltip.value = {
        x: ev.clientX - rect.left,
        y: ev.clientY - rect.top,
        visible: true,
        d,
      }
      clampTooltip()
    } else {
      hover.value = null
      tooltip.value.visible = false
    }
    return
  }
  const prev = pointers.get(ev.pointerId)
  pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })

  if (pointers.size === 2) {
    // pinch
    const pts = Array.from(pointers.values())
    const prevPts = [prev, { x: ev.clientX, y: ev.clientY }]
    // 简单处理：用当前两点距离与初始 pinch 距离比较
    if (dragStart.value && dragStart.value.pinchD0) {
      const d1 = distance(pts[0], pts[1])
      const c = midYear(pts[0], pts[1])
      zoom(dragStart.value.pinchD0 / d1, c, false)
    }
    return
  }

  if (pointers.size === 1 && dragStart.value) {
    // 追踪拖拽速度（平滑滤波），供松手后的惯性滑行使用
    const now = performance.now()
    if (lastMoveT && now > lastMoveT) {
      const v = (ev.clientX - lastMoveX) / (now - lastMoveT)
      vel = vel * 0.6 + v * 0.4
    }
    lastMoveT = now
    lastMoveX = ev.clientX
    const dx = ev.clientX - dragStart.value.x
    if (Math.abs(dx) > 4) suppressClick.value = true
    const rect = svgRef.value.getBoundingClientRect()
    const span = dragStart.value.yearEnd - dragStart.value.yearStart
    const yearDx = -(dx / rect.width) * span
    let s = dragStart.value.yearStart + yearDx
    let e = dragStart.value.yearEnd + yearDx
    const maxSpan = T_LIN_END - T_PRE_START
    if (e - s > maxSpan) {
      const mid = (s + e) / 2
      s = mid - maxSpan / 2
      e = mid + maxSpan / 2
    }
    if (s < T_PRE_START) {
      e += T_PRE_START - s
      s = T_PRE_START
    }
    if (e > T_LIN_END) {
      s -= e - T_LIN_END
      e = T_LIN_END
    }
    view.value = { start: s, end: e }
    targetView.value = { start: s, end: e }
  }
}

function onPointerUp(e) {
  if (svgRef.value) svgRef.value.releasePointerCapture(e.pointerId)
  const wasPinch = !!(dragStart.value && dragStart.value.pinchD0)
  const wasDrag = suppressClick.value
  pointers.delete(e.pointerId)
  dragStart.value = null
  // 点击选择：单指抬起、未拖拽、未捏合时按命中检测选择朝代
  if (!wasDrag && !wasPinch && pointers.size === 0) {
    const d = dynastyAtClient(e.clientX, e.clientY)
    if (d) select(d)
  } else if (wasDrag && !wasPinch && pointers.size === 0) {
    startMomentum()
  }
}

function onPointerCancel(e) {
  pointers.delete(e.pointerId)
  dragStart.value = null
}

function onPointerDownPinch(e) {
  onPointerDown(e)
  if (pointers.size === 2) {
    const pts = Array.from(pointers.values())
    dragStart.value = {
      ...dragStart.value,
      pinchD0: distance(pts[0], pts[1]),
      pinchView: { ...view.value },
    }
  }
}

// ---- hover / tooltip ----
async function clampTooltip() {
  await nextTick()
  const tipEl = timelineRef.value?.querySelector('.tooltip')
  const svgEl = svgRef.value
  if (!tipEl || !svgEl) return
  const tRect = tipEl.getBoundingClientRect()
  const sRect = svgEl.getBoundingClientRect()
  let x = tooltip.value.x + 14
  let y = tooltip.value.y - 12
  if (x + tRect.width > sRect.width) x = tooltip.value.x - tRect.width - 14
  if (y + tRect.height > sRect.height) y = sRect.height - tRect.height - 8
  if (y < 0) y = 8
  tooltip.value = { ...tooltip.value, x, y }
}

function onLeave() {
  hover.value = null
  tooltip.value.visible = false
}

// hover 聚光灯：悬停朝代 + 时间重叠的并立政权保持点亮，其余压暗；
// 搜索命中的朝代始终不被压暗
const litIds = computed(() => {
  if (!hover.value) return null
  const h = hover.value
  const set = new Set([h.id])
  for (const d of visible.value) {
    if (d.start < h.end && d.end > h.start) set.add(d.id)
  }
  if (matchedDynasty.value) set.add(matchedDynasty.value)
  return set
})

function select(d) {
  if (suppressClick.value) return
  selected.value = selected.value?.id === d.id ? null : d
}

function onKey(e) {
  if (e.key === 'Escape') {
    selected.value = null
    matchedDynasty.value = null
    resetView()
  }
}

function onDynKey(e, d) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    select(d)
  }
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
      const pad = Math.max(40, (hit.end - hit.start) * 0.3)
      flyTo({
        start: Math.max(T_PRE_START, hit.start - pad),
        end: Math.min(T_LIN_END, hit.end + pad),
      })
    } else {
      matchedDynasty.value = null
    }
  },
)

// 搜索是否命中
const hasMatch = computed(() => {
  const q = props.keyword.trim()
  if (!q) return true
  return props.dynasties.some((d) => {
    if (d.name.includes(q)) return true
    if (d.alias.some((a) => a.includes(q))) return true
    return d.chapterIds.some((id) => chapterById(id)?.title.includes(q))
  })
})

const isTouch = ref(false)

onMounted(() => {
  window.addEventListener('keydown', onKey)
  isTouch.value = window.matchMedia('(hover: none)').matches
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  cancelAnimationFrame(animId)
  clearTimeout(flightTimer)
  stopMomentum()
})

const chaptersOf = (d) => d.chapterIds.map((id) => chapterById(id)).filter(Boolean)

// 缩放控制条
const controlsVisible = computed(
  () => view.value.start > T_PRE_START || view.value.end < T_LIN_END,
)
</script>

<template>
  <div ref="timelineRef" class="timeline">
    <!-- 缩放控制 -->
    <div class="zoom-controls">
      <button @click="zoomIn" title="放大" aria-label="放大时间轴">＋</button>
      <button @click="zoomOut" title="缩小" aria-label="缩小时间轴">－</button>
      <button v-if="controlsVisible" @click="resetView" title="回到全史" aria-label="回到全史">全史</button>
    </div>

    <!-- SVG 时间轴 -->
    <svg
      ref="svgRef"
      :viewBox="`0 0 ${VIEW_W} ${viewH}`"
      class="axis-svg"
      role="img"
      aria-label="朝代时间轴"
      @wheel.prevent="onWheel"
      @pointerdown="onPointerDownPinch"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
      @pointerleave="onLeave"
    >
      <!-- 年份刻度 -->
      <line :x1="xOf(view.start)" y1="0" :x2="xOf(view.end)" y2="0" class="axis-line" />

      <!-- 朝代区块 -->
      <g
        v-for="d in visible"
        :key="d.id"
        class="dyn-g"
        :class="{
          dim: litIds && !litIds.has(d.id),
          linked: litIds && hover?.id !== d.id && litIds.has(d.id),
        }"
      >
        <rect
          :x="d.x"
          :y="rowY(d.row)"
          :width="d.w"
          :height="ROW_H"
          rx="4"
          :fill="d.color"
          :class="{
            'dyn-rect': true,
            active: selected?.id === d.id,
            matched: matchedDynasty === d.id,
            hovered: hover?.id === d.id,
          }"
          tabindex="0"
          role="button"
          :aria-label="`${d.name} ${yearLabel(d.start)}—${yearLabel(d.end)}`"
          :aria-pressed="selected?.id === d.id"
          @keydown="onDynKey($event, d)"
        >
          <title>{{ d.name }} {{ yearLabel(d.start) }}—{{ yearLabel(d.end) }}</title>
        </rect>

        <!-- 朝代名（宽度足够时显示） -->
        <text
          v-if="d.w > 52"
          :x="d.x + d.w / 2"
          :y="rowY(d.row) + ROW_H / 2 - 4"
          text-anchor="middle"
          class="dyn-label"
        >
          {{ d.name }}
        </text>
        <text
          v-if="d.w > 76"
          :x="d.x + d.w / 2"
          :y="rowY(d.row) + ROW_H / 2 + 13"
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
          :y1="ROW_H + ROW_GAP"
          :x2="xOf(y)"
          :y2="ROW_H + ROW_GAP + 5"
          class="tick"
        />
        <text
          v-if="xOf(y) > 0 && xOf(y) < VIEW_W"
          :x="xOf(y)"
          :y="viewH - 2"
          text-anchor="middle"
          class="tick-label"
        >
          {{ yearLabel(y) }}
        </text>
      </g>
    </svg>
    <div class="axis-hint">
      {{ isTouch ? '拖动平移 · 双指缩放 · 点按查看章节' : '滚轮缩放 · 点击朝代查看章节 · Esc 复位' }}
    </div>

    <!-- hover 信息卡 -->
    <div
      v-if="tooltip.visible && tooltip.d && !isTouch"
      class="tooltip"
      aria-hidden="true"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
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

    <p v-else-if="!hasMatch" class="hint no-match">
      未找到与「{{ keyword }}」相关的朝代或章节
    </p>
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
  touch-action: none;
  user-select: none;
}

.axis-svg:active {
  cursor: grabbing;
}

.axis-line {
  stroke: var(--border);
  stroke-width: 1;
}

.dyn-g {
  transition: opacity 0.22s ease;
}

.dyn-g.dim {
  opacity: 0.3;
}

.dyn-g.linked .dyn-rect {
  filter: brightness(1.12);
}

.dyn-rect {
  cursor: pointer;
  transition: filter 0.2s, opacity 0.2s;
  outline: none;
}

.dyn-rect:hover,
.dyn-rect.hovered {
  filter: brightness(1.18) drop-shadow(0 0 7px rgba(0, 0, 0, 0.35));
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

.dyn-rect:focus-visible {
  stroke: var(--accent);
  stroke-width: 3;
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

.hint.no-match {
  color: var(--accent-soft);
}

@media (max-width: 768px) {
  .chapter-grid {
    grid-template-columns: 1fr;
  }

  .dyn-chapters h2 {
    font-size: 18px;
  }
}
</style>
