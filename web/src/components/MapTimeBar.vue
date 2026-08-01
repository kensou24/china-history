<script setup>
import { computed, ref } from 'vue'
import { yearLabel } from '@/utils'

const props = defineProps({
  years: { type: Array, required: true }, // map.json changeYears（升序）
  year: { type: Number, required: true },
  playing: { type: Boolean, default: false },
})
const emit = defineEmits(['update:year', 'toggle-play'])

const trackRef = ref(null)
const dragging = ref(false)

const minY = computed(() => props.years[0])
const maxY = computed(() => props.years[props.years.length - 1])
const pctOf = (y) => ((y - minY.value) / (maxY.value - minY.value)) * 100

// 吸附到最近的变化年份（二分）
function snap(y) {
  const ys = props.years
  let lo = 0
  let hi = ys.length - 1
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (ys[mid] < y) lo = mid + 1
    else hi = mid
  }
  if (lo > 0 && y - ys[lo - 1] <= ys[lo] - y) return ys[lo - 1]
  return ys[lo]
}

function emitAt(clientX) {
  const rect = trackRef.value.getBoundingClientRect()
  const r = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
  emit('update:year', snap(Math.round(minY.value + r * (maxY.value - minY.value))))
}

function onPointerDown(e) {
  dragging.value = true
  trackRef.value.setPointerCapture(e.pointerId)
  emitAt(e.clientX)
}
function onPointerMove(e) {
  if (dragging.value) emitAt(e.clientX)
}
function onPointerUp(e) {
  dragging.value = false
  trackRef.value.releasePointerCapture(e.pointerId)
}

// 世纪刻度
const ticks = computed(() => {
  const out = []
  for (let y = Math.ceil(minY.value / 100) * 100; y <= maxY.value; y += 100) out.push(y)
  return out
})

// 变化点太密时只画刻度不画点，避免糊成一片
const showDots = computed(() => props.years.length <= 400)
</script>

<template>
  <div class="time-bar">
    <button class="play-btn" :aria-label="playing ? '暂停' : '播放'" @click="emit('toggle-play')">
      {{ playing ? '⏸' : '▶' }}
    </button>
    <div
      ref="trackRef"
      class="track"
      role="slider"
      aria-label="年份"
      :aria-valuenow="year"
      :aria-valuemin="minY"
      :aria-valuemax="maxY"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <span v-for="t in ticks" :key="'c' + t" class="tick" :style="{ left: pctOf(t) + '%' }" />
      <template v-if="showDots">
        <span v-for="y in years" :key="y" class="change-dot" :style="{ left: pctOf(y) + '%' }" />
      </template>
      <div class="handle" :style="{ left: pctOf(year) + '%' }">
        <span class="handle-label">{{ yearLabel(year) }}年</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.play-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  font-size: 14px;
  flex-shrink: 0;
}

.track {
  position: relative;
  flex: 1;
  height: 34px;
  cursor: pointer;
  touch-action: none;
}

.track::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 3px;
  transform: translateY(-50%);
  background: var(--border);
  border-radius: 2px;
}

.tick {
  position: absolute;
  top: 50%;
  width: 1px;
  height: 8px;
  transform: translateY(-50%);
  background: var(--text-soft);
  opacity: 0.5;
}

.change-dot {
  position: absolute;
  top: 50%;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: var(--text-soft);
}

.handle {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}

.handle::before {
  content: '';
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  border: 2px solid var(--surface);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.handle-label {
  position: absolute;
  bottom: 18px;
  white-space: nowrap;
  font-size: 12px;
  color: var(--accent);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
}
</style>
