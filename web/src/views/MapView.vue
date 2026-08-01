<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMapData } from '@/composables/useMapData'
import { useToast } from '@/composables/useToast'
import { reducedMotion } from '@/utils'
import AppLoading from '@/components/AppLoading.vue'
import AtlasMap from '@/components/AtlasMap.vue'
import MapTimeBar from '@/components/MapTimeBar.vue'

const { data, error, loadMap, activeShapes } = useMapData()
const { toast } = useToast()
const loading = ref(true)
const year = ref(-221) // 默认秦代表年（changeYears 含 -221）
const shapes = computed(() => activeShapes(year.value))
const full = computed(() => {
  const [x, y, w, h] = (data.value?.viewBox || '0 0 1000 800').split(' ').map(Number)
  return { x, y, w, h }
})

// 临时：Task 8 替换为双模式选择逻辑
function onSelect(s) {
  if (s) toast(s.dyn ? s.n : `${s.n}（中立政权）`)
}

const playing = ref(false)
let playTimer = null

// changeYears 中离 y 最近的下标
function nearestIdx(y) {
  const ys = data.value.changeYears
  let best = 0
  for (let i = 0; i < ys.length; i++) {
    if (Math.abs(ys[i] - y) < Math.abs(ys[best] - y)) best = i
  }
  return best
}

// 步进到上/下一个变化年；已在末尾返回 false（播放自动停）
function stepYear(d) {
  const ys = data.value.changeYears
  const i = Math.min(ys.length - 1, Math.max(0, nearestIdx(year.value) + d))
  onYearUpdate(ys[i])
  return i < ys.length - 1
}

function togglePlay() {
  if (reducedMotion()) {
    stepYear(1) // 减少动态：播放按钮变单步
    return
  }
  playing.value = !playing.value
}

watch(playing, (v) => {
  clearInterval(playTimer)
  playTimer = null
  if (v) {
    playTimer = setInterval(() => {
      if (!stepYear(1)) playing.value = false
    }, 1200)
  }
})

onUnmounted(() => clearInterval(playTimer))

// 临时版：Task 8 扩展为切换 year 模式 + 清选中
function onYearUpdate(y) {
  year.value = y
}

async function init() {
  loading.value = true
  try {
    await loadMap()
  } catch {
    /* error 已写入 composable */
  } finally {
    loading.value = false
  }
}

onMounted(init)
</script>

<template>
  <div class="map-page">
    <h1 class="page-title">疆域时空地图</h1>
    <p class="page-sub">拖动年份看疆域变迁 —— 底图为海岸线与大河，不代表现代国界</p>

    <AppLoading v-if="loading" />
    <div v-else-if="error" class="error-box">
      <p>地图数据加载失败：{{ error }}</p>
      <button @click="init">重新加载</button>
    </div>

    <template v-else>
      <AtlasMap
        :basemap="data.basemap"
        :full="full"
        :shapes="shapes"
        :selected-id="null"
        :focus-key="0"
        @select="onSelect"
      />
      <MapTimeBar
        :years="data.changeYears"
        :year="year"
        :playing="playing"
        @update:year="onYearUpdate"
        @toggle-play="togglePlay"
      />
    </template>
  </div>
</template>

<style scoped>
.page-title {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--accent);
}

.page-sub {
  margin: 0 0 14px;
  color: var(--text-soft);
  font-size: 14px;
}

.error-box {
  padding: 60px 24px;
  text-align: center;
  color: var(--text-soft);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
}
</style>
