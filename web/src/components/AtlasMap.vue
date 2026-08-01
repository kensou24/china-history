<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { reducedMotion } from '@/utils'

const props = defineProps({
  basemap: { type: Object, required: true }, // { coast, rivers[], cities[] }
  full: { type: Object, required: true }, // 全景视图 { x, y, w, h }
  shapes: { type: Array, required: true }, // 当前年活跃 shape
  selectedId: { type: String, default: null }, // dynasty 模式选中的朝代 id
  focusKey: { type: Number, default: 0 }, // 变化时触发 flyTo(focusBbox)
  focusBbox: { type: Array, default: null }, // [x, y, w, h]
})
const emit = defineEmits(['select'])

const { dynastyById } = useMeta()
const svgRef = ref(null)
const hoverIdx = ref(-1)

// ---- 颜色：朝代色取自 dynasties.json；中立政权中性色 ----
function fillOf(s) {
  if (!s.dyn) return 'var(--border)'
  return dynastyById(s.dyn)?.color || 'var(--border)'
}
const dimmed = (s) => !!props.selectedId && s.dyn !== props.selectedId

// ---- 相机：view（当前）与 targetView（目标）分离，纵横比锁定 full ----
const view = ref({ ...props.full })
const targetView = ref(null)
let animId = null
let flightTimer = null

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

// 纵横比永远等于 full，避免 preserveAspectRatio 留边；平移夹进全景边界
function clampView(v) {
  const F = props.full
  const w = Math.min(Math.max(v.w, F.w * 0.04), F.w)
  const h = w * (F.h / F.w)
  if (w >= F.w) return { ...F }
  const x = Math.min(Math.max(v.x, F.x), F.x + F.w - w)
  const y = Math.min(Math.max(v.y, F.y), F.y + F.h - h)
  return { x, y, w, h }
}

function setView(v, animate = true, dur = 350) {
  clearTimeout(flightTimer)
  const target = clampView(v)
  targetView.value = target
  cancelAnimationFrame(animId)
  if (!animate || reducedMotion()) {
    view.value = target
    return
  }
  const from = { ...view.value }
  const t0 = performance.now()
  const step = (now) => {
    const p = Math.min(1, (now - t0) / dur)
    const e = easeInOutCubic(p)
    view.value = {
      x: from.x + (target.x - from.x) * e,
      y: from.y + (target.y - from.y) * e,
      w: from.w + (target.w - from.w) * e,
      h: from.h + (target.h - from.h) * e,
    }
    if (p < 1) animId = requestAnimationFrame(step)
  }
  animId = requestAnimationFrame(step)
}

const viewBoxStr = computed(
  () => `${view.value.x} ${view.value.y} ${view.value.w} ${view.value.h}`,
)

// fitBounds：外扩 12% 并锁纵横比
function fitBbox(b) {
  const F = props.full
  const pad = Math.max(b[2], b[3]) * 0.12
  let w = b[2] + pad * 2
  let h = b[3] + pad * 2
  const aspect = F.w / F.h
  if (w / h > aspect) h = w / aspect
  else w = h * aspect
  return clampView({
    x: b[0] + b[2] / 2 - w / 2,
    y: b[1] + b[3] / 2 - h / 2,
    w,
    h,
  })
}

// 镜头飞行：缩放比大时先拉远再推近（沿用时间轴两段式语言）
function flyTo(bbox, dur = 500) {
  if (!bbox) return
  const target = fitBbox(bbox)
  if (reducedMotion()) {
    setView(target, false)
    return
  }
  const from = targetView.value || view.value
  const ratio = Math.max(from.w / target.w, target.w / from.w)
  if (ratio > 2.2) {
    const midW = Math.sqrt(from.w * target.w)
    const mid = clampView({
      x: (from.x + from.w / 2 + target.x + target.w / 2) / 2 - midW / 2,
      y: (from.y + from.h / 2 + target.y + target.h / 2) / 2 - (midW * (props.full.h / props.full.w)) / 2,
      w: midW,
      h: midW * (props.full.h / props.full.w),
    })
    setView(mid, true, 260)
    flightTimer = setTimeout(() => setView(target, true, dur - 260), 250)
  } else {
    setView(target, true, dur)
  }
}

// 父级经 focusKey 通知飞行（immediate 覆盖"带 ?d= 进页面"的首帧）
watch(
  () => props.focusKey,
  () => {
    if (props.focusBbox) flyTo(props.focusBbox)
  },
  { immediate: true },
)

// ---- 坐标换算：视口 px → SVG 用户坐标 ----
function svgPoint(cx, cy) {
  const ctm = svgRef.value?.getScreenCTM()
  if (!ctm) return null
  return new DOMPoint(cx, cy).matrixTransform(ctm.inverse())
}

// ---- 滚轮缩放（指针锚定，短缓动让连续滚动平滑追赶） ----
function onWheel(e) {
  e.preventDefault()
  stopMomentum()
  const p = svgPoint(e.clientX, e.clientY)
  if (!p) return
  const cur = targetView.value || view.value
  const f = e.deltaY > 0 ? 1.25 : 0.8
  if (f < 1 && cur.w * f < props.full.w * 0.04) return
  if (f > 1 && cur.w >= props.full.w) return
  const w = cur.w * f
  setView(
    { x: p.x - (p.x - cur.x) * f, y: p.y - (p.y - cur.y) * f, w, h: w * (cur.h / cur.w) },
    true,
    180,
  )
}

// ---- 拖拽 / 惯性 / pinch ----
const pointers = new Map()
let dragStart = null // { view, downX, downY, pinchD0, pinchView, pinchAnchor }
let velX = 0
let velY = 0
let lastMoveT = 0
let lastMoveX = 0
let lastMoveY = 0
let momentumId = null
const moved = ref(false)

function stopMomentum() {
  cancelAnimationFrame(momentumId)
  momentumId = null
  velX = 0
  velY = 0
}

function panByPx(dxPx, dyPx) {
  const rect = svgRef.value?.getBoundingClientRect()
  if (!rect) return false
  const dx = (-dxPx / rect.width) * view.value.w
  const dy = (-dyPx / rect.height) * view.value.h
  const next = clampView({ ...view.value, x: view.value.x + dx, y: view.value.y + dy })
  const hitEdge = next.x === view.value.x && next.y === view.value.y
  view.value = next
  targetView.value = next
  return !hitEdge
}

function startMomentum() {
  if (reducedMotion() || Math.hypot(velX, velY) < 0.05) {
    stopMomentum()
    return
  }
  let prevT = performance.now()
  const step = (now) => {
    const dt = Math.min(50, now - prevT)
    prevT = now
    if (!panByPx(velX * dt, velY * dt)) {
      stopMomentum()
      return
    }
    const decay = Math.exp(-dt / 180)
    velX *= decay
    velY *= decay
    if (Math.hypot(velX, velY) < 0.02) {
      stopMomentum()
      return
    }
    momentumId = requestAnimationFrame(step)
  }
  momentumId = requestAnimationFrame(step)
}

function onPointerDown(e) {
  if (!svgRef.value) return
  cancelAnimationFrame(animId)
  clearTimeout(flightTimer)
  stopMomentum()
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  svgRef.value.setPointerCapture(e.pointerId)
  lastMoveT = 0
  lastMoveX = e.clientX
  lastMoveY = e.clientY
  moved.value = false
  dragStart = { view: { ...view.value }, downX: e.clientX, downY: e.clientY }
  if (pointers.size === 2) {
    const pts = [...pointers.values()]
    const d0 = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
    // pinch 基准：起点视图 + 双指中点下的用户坐标（全程不变，防指数发散）
    const midCx = (pts[0].x + pts[1].x) / 2
    const midCy = (pts[0].y + pts[1].y) / 2
    dragStart.pinchD0 = Math.max(24, d0)
    dragStart.pinchView = { ...view.value }
    dragStart.pinchAnchor = svgPoint(midCx, midCy)
  }
}

function onPointerMove(e) {
  if (!pointers.has(e.pointerId)) {
    throttledHover(e.clientX, e.clientY)
    return
  }
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })

  if (pointers.size === 2 && dragStart?.pinchD0 && dragStart.pinchAnchor) {
    const pts = [...pointers.values()]
    const d1 = Math.max(24, Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y))
    const w = dragStart.pinchView.w * (dragStart.pinchD0 / d1)
    const h = w * (props.full.h / props.full.w)
    const rect = svgRef.value.getBoundingClientRect()
    const fx = ((pts[0].x + pts[1].x) / 2 - rect.left) / rect.width
    const fy = ((pts[0].y + pts[1].y) / 2 - rect.top) / rect.height
    view.value = clampView({
      x: dragStart.pinchAnchor.x - fx * w,
      y: dragStart.pinchAnchor.y - fy * h,
      w,
      h,
    })
    targetView.value = { ...view.value }
    moved.value = true
    return
  }

  if (pointers.size === 1 && dragStart) {
    const now = performance.now()
    if (lastMoveT && now > lastMoveT) {
      velX = velX * 0.6 + ((e.clientX - lastMoveX) / (now - lastMoveT)) * 0.4
      velY = velY * 0.6 + ((e.clientY - lastMoveY) / (now - lastMoveT)) * 0.4
    }
    const dx = e.clientX - lastMoveX
    const dy = e.clientY - lastMoveY
    lastMoveT = now
    lastMoveX = e.clientX
    lastMoveY = e.clientY
    if (
      dragStart.downX !== undefined &&
      Math.hypot(e.clientX - dragStart.downX, e.clientY - dragStart.downY) >= 5
    ) {
      moved.value = true
    }
    panByPx(dx, dy)
  }
}

function onPointerUp(e) {
  svgRef.value?.releasePointerCapture(e.pointerId)
  const wasPinch = !!dragStart?.pinchD0
  const wasMoved = moved.value
  pointers.delete(e.pointerId)
  if (wasPinch && pointers.size === 1) {
    // 捏合后先抬一指：以剩余手指当前位置重新锚定，防跳变
    const [p] = pointers.values()
    dragStart = { view: { ...view.value }, downX: p.x, downY: p.y }
    lastMoveT = 0
    lastMoveX = p.x
    lastMoveY = p.y
    stopMomentum()
    moved.value = true
    return
  }
  dragStart = null
  if (pointers.size === 0) {
    if (!wasMoved && !wasPinch) {
      // 点击：位移 <5px 视为选择（命中检测走 elementFromPoint，
      // 不受 setPointerCapture 重定向影响——时间轴踩坑后的方案）
      emit('select', shapeAtClient(e.clientX, e.clientY))
    } else if (wasMoved && !wasPinch) {
      startMomentum()
    }
  }
}

function onPointerCancel(e) {
  pointers.delete(e.pointerId)
  dragStart = null
}

// 双击复位全景
function onDblClick() {
  setView({ ...props.full }, true, 400)
}

// ---- 命中检测：elementFromPoint 读 path 的 data-i ----
function shapeAtClient(cx, cy) {
  const el = document.elementFromPoint(cx, cy)
  if (!el?.dataset || el.dataset.i === undefined) return null
  return props.shapes[+el.dataset.i] || null
}

// hover：rAF 合帧，只在未按下时（触屏拖动不触发，天然无粘滞）
let hoverRaf = null

function throttledHover(cx, cy) {
  if (hoverRaf) return
  hoverRaf = requestAnimationFrame(() => {
    hoverRaf = null
    const el = document.elementFromPoint(cx, cy)
    hoverIdx.value = el?.dataset?.i !== undefined ? +el.dataset.i : -1
  })
}

function onLeave() {
  hoverIdx.value = -1
}

// 标签只在疆域块足够大时显示（随缩放自适应密度）
const labelShapes = computed(() =>
  props.shapes.filter((s) => s.bbox[2] > view.value.w * 0.055),
)

onUnmounted(() => {
  cancelAnimationFrame(animId)
  cancelAnimationFrame(momentumId)
  cancelAnimationFrame(hoverRaf)
  clearTimeout(flightTimer)
})
</script>

<template>
  <svg
    ref="svgRef"
    class="atlas"
    :viewBox="viewBoxStr"
    role="application"
    aria-label="疆域地图：滚轮缩放，拖拽平移，点击政权查看"
    @wheel.prevent="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerCancel"
    @pointerleave="onLeave"
    @dblclick="onDblClick"
  >
    <!-- 底图：海岸线 + 河流 + 城市参考点（不可点） -->
    <path class="coast" :d="basemap.coast" />
    <path v-for="(r, i) in basemap.rivers" :key="'r' + i" class="river" :d="r" />
    <g v-for="c in basemap.cities" :key="c.n" class="city">
      <circle :cx="c.x" :cy="c.y" :r="view.w * 0.0022" />
      <text :x="c.x + view.w * 0.004" :y="c.y" :font-size="view.w * 0.011">{{ c.n }}</text>
    </g>

    <!-- 政权疆域（可点；key = 名称+起始年，跨年切换 200ms 淡入淡出） -->
    <TransitionGroup name="polity" tag="g">
      <path
        v-for="(s, i) in shapes"
        :key="s.n + '-' + s.from"
        class="polity"
        :class="{ dim: dimmed(s), hov: hoverIdx === i }"
        :d="s.d"
        :fill="fillOf(s)"
        :data-i="i"
      />
    </TransitionGroup>

    <!-- 政权名标签（不可点，不挡命中） -->
    <text
      v-for="s in labelShapes"
      :key="'t' + s.n + '-' + s.from"
      class="polity-label"
      :x="s.label[0]"
      :y="s.label[1]"
      :font-size="view.w * 0.016"
      text-anchor="middle"
    >
      {{ s.n }}
    </text>
  </svg>
</template>

<style scoped>
.atlas {
  width: 100%;
  height: auto;
  display: block;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: 12px;
  touch-action: none; /* 触控手势由组件接管（拖拽/pinch） */
  user-select: none;
}

.coast {
  fill: none;
  stroke: var(--text-soft);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
  opacity: 0.7;
  pointer-events: none;
}

.river {
  fill: none;
  stroke: var(--accent-soft);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
  opacity: 0.8;
  pointer-events: none;
}

.city {
  pointer-events: none;
}

.city circle {
  fill: var(--text-soft);
}

.city text {
  fill: var(--text-soft);
  font-size: inherit;
}

.polity {
  stroke: var(--surface);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
  opacity: 0.78;
  transition: opacity 0.2s ease;
}

@media (hover: hover) {
  .polity {
    cursor: pointer;
  }

  .polity.hov {
    opacity: 1;
    stroke: var(--accent);
  }
}

/* dynasty 模式：非选中朝代降为中性色淡显（CSS 优先级高于 :fill 表现属性） */
.polity.dim {
  fill: var(--border);
  opacity: 0.25;
}

.polity-label {
  fill: var(--text);
  paint-order: stroke;
  stroke: var(--bg-soft);
  stroke-width: 3;
  pointer-events: none;
  font-weight: 600;
}

.polity-enter-active,
.polity-leave-active {
  transition: opacity 0.2s ease;
}

.polity-enter-from,
.polity-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .polity,
  .polity-enter-active,
  .polity-leave-active {
    transition: none;
  }
}
</style>
