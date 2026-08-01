<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { yearLabel, reducedMotion } from '@/utils'

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

// scale(0..1) → 年份（全史范围反向映射，minimap 定位用）
function yearFromScale(t) {
  if (t <= PRE_FRAC) {
    return T_PRE_START + (t / PRE_FRAC) * (T_PRE_END - T_PRE_START)
  }
  return T_PRE_END + ((t - PRE_FRAC) / (1 - PRE_FRAC)) * (T_LIN_END - T_PRE_END)
}

// 把给定起点与跨度夹进全史边界
function clampWindow(s, span) {
  let e = s + span
  if (s < T_PRE_START) {
    e += T_PRE_START - s
    s = T_PRE_START
  }
  if (e > T_LIN_END) {
    s -= e - T_LIN_END
    e = T_LIN_END
  }
  return { start: Math.max(T_PRE_START, s), end: Math.min(T_LIN_END, e) }
}

// 视图窗口（年份），默认全史
const view = ref({ start: T_PRE_START, end: T_LIN_END })
const targetView = ref(null)
let animId = null
let flightTimer = null

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
  return ((scaleYear(y) - scaleYear(start)) / denom) * VIEW_W.value
}

const widthOf = (d) => Math.max(0, xOf(d.end) - xOf(d.start))

// 视图坐标宽度随容器收窄（420~1000）：窄屏下 1 单位≈1px，朝代名/年份标签保持可读字号
const containerW = ref(1000)
const VIEW_W = computed(() => Math.min(1000, Math.max(420, Math.round(containerW.value))))
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

// ---- 自适应年代刻度：按视野跨度选步长，保持屏上约 6~10 个刻度 ----
const TICK_STEPS = [10, 25, 50, 100, 200, 500, 1000]
const ticks = computed(() => {
  const span = view.value.end - view.value.start
  const step = TICK_STEPS.find((s) => span / s <= 10) || 1000
  const first = Math.ceil(view.value.start / step) * step
  const out = []
  for (let y = first; y <= view.value.end; y += step) out.push(y)
  return out
})

// HUD：当前视野年代读数（拖拽/缩放时实时跳动）
const viewRangeLabel = computed(() => {
  const s = Math.round(view.value.start)
  const e = Math.round(view.value.end)
  return `${yearLabel(s)} — ${yearLabel(e)} · ${e - s} 年`
})

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
  setView(clampWindow(c - newSpan / 2, newSpan), animate, dur)
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
  return yearFromScale(s + (e - s) * ratio)
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
  pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })

  if (pointers.size === 2) {
    // pinch：始终以捏合起点时的视图（pinchView）为基准按比例缩放。
    // 不能逐帧把总比例乘在当前视图上，否则会指数发散、缩放失控
    if (dragStart.value && dragStart.value.pinchD0) {
      const pts = Array.from(pointers.values())
      const d1 = Math.max(24, distance(pts[0], pts[1]))
      const v0 = dragStart.value.pinchView
      const span0 = v0.end - v0.start
      let newSpan = span0 * (dragStart.value.pinchD0 / d1)
      newSpan = Math.min(T_LIN_END - T_PRE_START, Math.max(60, newSpan))
      // 锚点：双指中点下的年份保持在原位
      const c = midYear(pts[0], pts[1])
      const w = clampWindow(c - newSpan / 2, newSpan)
      view.value = w
      targetView.value = { ...w }
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
  // 捏合后先抬起一指：以剩余手指的当前位置重新锚定拖拽起点，
  // 否则 pinch → 单指平移切换瞬间视图会跳变
  if (wasPinch && pointers.size === 1) {
    const [p] = pointers.values()
    dragStart.value = { x: p.x, yearStart: view.value.start, yearEnd: view.value.end }
    lastMoveT = 0
    lastMoveX = p.x
    vel = 0
    suppressClick.value = true
    return
  }
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
  if (selected.value?.id === d.id) {
    selected.value = null
    return
  }
  selected.value = d
  // 选中即运镜居中：小朝代推近到其跨度 2 倍（至少 160 年），但不主动拉远
  const span = view.value.end - view.value.start
  const targetSpan = Math.min(Math.max((d.end - d.start) * 2, 160), span)
  const mid = (d.start + d.end) / 2
  setView(clampWindow(mid - targetSpan / 2, targetSpan), true, 420)
}

// 双击空白处快速放大（点在朝代上不抢点击/聚光灯）
function onDblClick(e) {
  if (dynastyAtClient(e.clientX, e.clientY)) return
  zoom(0.5, yearAtClientX(e.clientX), true, 300)
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

// ---- 迷你地图：全史缩略 + 当前视野框，点击跳转、拖拽平移 ----
const MINI_ROW = 9
const MINI_GAP = 2
const miniSvgRef = ref(null)

const miniRows = computed(() => {
  const rows = []
  const sorted = [...props.dynasties].sort((a, b) => a.start - b.start)
  for (const d of sorted) {
    let placed = false
    for (const row of rows) {
      if (row[row.length - 1].end <= d.start) {
        row.push(d)
        placed = true
        break
      }
    }
    if (!placed) rows.push([d])
  }
  return rows
})

const miniH = computed(() => miniRows.value.length * (MINI_ROW + MINI_GAP) + 6)
const miniX = (y) => scaleYear(y) * VIEW_W.value
const miniW = (d) => Math.max(2, miniX(d.end) - miniX(d.start))

const miniViewRect = computed(() => ({
  x: scaleYear(view.value.start) * VIEW_W.value,
  w: Math.max(6, (scaleYear(view.value.end) - scaleYear(view.value.start)) * VIEW_W.value),
}))

// 抓取点相对视野中心的年偏移：抓住视野框内部拖不跳变，点框外则以点击处为中心
let miniDrag = null

function miniYear(e) {
  const rect = miniSvgRef.value.getBoundingClientRect()
  const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
  return yearFromScale(ratio)
}

function miniApply(e) {
  const span = view.value.end - view.value.start
  const center = miniYear(e) - (miniDrag?.offset || 0)
  const w = clampWindow(center - span / 2, span)
  cancelAnimationFrame(animId)
  clearTimeout(flightTimer)
  stopMomentum()
  view.value = w
  targetView.value = { ...w }
}

function onMiniDown(e) {
  if (!miniSvgRef.value) return
  e.preventDefault()
  miniSvgRef.value.setPointerCapture(e.pointerId)
  const y = miniYear(e)
  const inside = y >= view.value.start && y <= view.value.end
  miniDrag = { offset: inside ? y - (view.value.start + view.value.end) / 2 : 0 }
  miniApply(e)
}

function onMiniMove(e) {
  if (miniDrag) miniApply(e)
}

function onMiniUp(e) {
  miniSvgRef.value?.releasePointerCapture(e.pointerId)
  miniDrag = null
}

const isTouch = ref(false)
let resizeObs = null

onMounted(() => {
  window.addEventListener('keydown', onKey)
  isTouch.value = window.matchMedia('(hover: none)').matches
  // 跟踪容器宽度驱动响应式 VIEW_W（桌面 ≥1000px 时与旧行为一致）
  resizeObs = new ResizeObserver((entries) => {
    const w = entries[0]?.contentRect.width
    if (w > 0) containerW.value = w
  })
  if (timelineRef.value) resizeObs.observe(timelineRef.value)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  cancelAnimationFrame(animId)
  clearTimeout(flightTimer)
  stopMomentum()
  resizeObs?.disconnect()
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
      @dblclick="onDblClick"
      @pointerdown="onPointerDownPinch"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
      @pointerleave="onLeave"
    >
      <!-- 年份刻度 -->
      <line :x1="xOf(view.start)" y1="0" :x2="xOf(view.end)" y2="0" class="axis-line" />

      <!-- 自适应网格线（朝代块之下） -->
      <line
        v-for="y in ticks"
        :key="y"
        class="grid-line"
        :x1="xOf(y)"
        y1="0"
        :x2="xOf(y)"
        :y2="viewH - 16"
      />

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

      <!-- 底部自适应刻度标签（夹边防止溢出） -->
      <text
        v-for="y in ticks"
        :key="'l' + y"
        :x="Math.min(VIEW_W - 16, Math.max(16, xOf(y)))"
        :y="viewH - 3"
        text-anchor="middle"
        class="tick-label"
      >
        {{ yearLabel(y) }}
      </text>
    </svg>

    <!-- 迷你地图：全史缩略，点击跳转、拖拽平移 -->
    <svg
      ref="miniSvgRef"
      :viewBox="`0 0 ${VIEW_W} ${miniH}`"
      class="mini-map"
      role="img"
      aria-label="全史缩略导航"
      @pointerdown="onMiniDown"
      @pointermove="onMiniMove"
      @pointerup="onMiniUp"
      @pointercancel="onMiniUp"
    >
      <g v-for="(row, ri) in miniRows" :key="ri">
        <rect
          v-for="d in row"
          :key="d.id"
          :x="miniX(d.start)"
          :y="3 + ri * (MINI_ROW + MINI_GAP)"
          :width="miniW(d)"
          :height="MINI_ROW"
          :fill="d.color"
          rx="1.5"
          class="mini-dyn"
          :class="{ 'mini-active': selected?.id === d.id }"
        />
      </g>
      <rect
        class="mini-view"
        :x="miniViewRect.x"
        y="1"
        :width="miniViewRect.w"
        :height="miniH - 2"
        rx="3"
      />
    </svg>

    <div class="axis-footer">
      <span class="axis-hint">
        {{ isTouch ? '拖动平移 · 双指缩放 · 点按查看章节 · 缩略图可拖' : '滚轮缩放 · 双击放大 · 点击朝代查看章节 · Esc 复位' }}
      </span>
      <span class="view-hud" aria-hidden="true">{{ viewRangeLabel }}</span>
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

/* hover 高亮只在有悬停能力的设备上生效，避免触屏点按后高亮粘住 */
@media (hover: hover) {
  .dyn-rect:hover,
  .dyn-rect.hovered {
    filter: brightness(1.18) drop-shadow(0 0 7px rgba(0, 0, 0, 0.35));
  }
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

.grid-line {
  stroke: var(--border);
  stroke-width: 1;
  opacity: 0.35;
  pointer-events: none;
}

.tick-label {
  font-size: 9.5px;
  fill: var(--text-soft);
  pointer-events: none;
}

/* 迷你地图 */
.mini-map {
  width: 100%;
  height: auto;
  display: block;
  margin-top: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: crosshair;
  touch-action: none;
  user-select: none;
}

.mini-dyn {
  opacity: 0.75;
}

.mini-dyn.mini-active {
  opacity: 1;
  stroke: var(--text);
  stroke-width: 1;
}

.mini-view {
  fill: rgba(127, 127, 127, 0.12);
  stroke: var(--text-soft);
  stroke-width: 1.5;
  cursor: grab;
}

.axis-footer {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-top: 4px;
}

.axis-footer .axis-hint {
  margin-top: 0;
}

.view-hud {
  font-size: 12px;
  color: var(--text-soft);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
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
  animation: tip-in 0.15s ease;
}

@keyframes tip-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
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
