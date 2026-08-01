<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { useMapData } from '@/composables/useMapData'
import { reducedMotion } from '@/utils'
import AppLoading from '@/components/AppLoading.vue'
import AtlasMap from '@/components/AtlasMap.vue'
import MapTimeBar from '@/components/MapTimeBar.vue'
import MapDynastyCard from '@/components/MapDynastyCard.vue'
import { useRoute, useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress'

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()

const { loadMeta, dynasties, dynastyById, chapterById } = useMeta()
const { data, error, loadMap, activeShapes, shapesByDynasty, yearOf } = useMapData()

const loading = ref(true)
const year = ref(-221)
const mode = ref('year') // 'dynasty' | 'year'
const selectedDynasty = ref(null)
const neutralShape = ref(null)
const playing = ref(false)
const focusKey = ref(0)

const shapes = computed(() => activeShapes(year.value))
const full = computed(() => {
  const [x, y, w, h] = (data.value?.viewBox || '0 0 1000 800').split(' ').map(Number)
  return { x, y, w, h }
})
const dynastyList = computed(() => dynasties.value?.dynasties || [])
const mappedIds = computed(() => new Set(Object.keys(data.value?.dynastyMap || {})))

const selectedDynastyObj = computed(() =>
  selectedDynasty.value ? dynastyById(selectedDynasty.value) : null,
)
const selectedChapters = computed(() =>
  selectedDynastyObj.value
    ? selectedDynastyObj.value.chapterIds.map((id) => chapterById(id)).filter(Boolean)
    : [],
)

// 选中朝代的飞行目标：其全部 shape 的 bbox 并集（时期朝代多政权一起框入）
const focusBbox = computed(() => {
  if (!selectedDynasty.value) return null
  const ss = shapesByDynasty(selectedDynasty.value)
  if (!ss.length) return null
  const x0 = Math.min(...ss.map((s) => s.bbox[0]))
  const y0 = Math.min(...ss.map((s) => s.bbox[1]))
  const x1 = Math.max(...ss.map((s) => s.bbox[0] + s.bbox[2]))
  const y1 = Math.max(...ss.map((s) => s.bbox[1] + s.bbox[3]))
  return [x0, y0, x1 - x0, y1 - y0]
})

async function init() {
  loading.value = true
  try {
    await Promise.all([loadMeta(), loadMap()])
    initState()
  } catch {
    /* error 已写入 composable */
  } finally {
    loading.value = false
    urlReady = true
  }
}

// 初始状态：URL query > 最近阅读朝代 > 默认（year 模式，前 221 年）
function initState() {
  const qd = typeof route.query.d === 'string' ? route.query.d : null
  const qy = Number(route.query.y)
  if (qd && dynastyById(qd)) {
    selectDynasty(qd)
    return
  }
  const ys = data.value.changeYears
  if (Number.isFinite(qy) && ys.length && qy >= ys[0] && qy <= ys[ys.length - 1]) {
    mode.value = 'year'
    year.value = qy
    return
  }
  const lastDyn = progress.lastRead ? chapterById(progress.lastRead)?.dynasty : null
  if (lastDyn && dynastyById(lastDyn) && mappedIds.value.has(lastDyn)) {
    selectDynasty(lastDyn)
    return
  }
  // 否则保持默认：year 模式，秦朝代表年（Cliopatria 秦首个几何快照为 -218，
  // -221 仅见战国末年；用 dynastyMap.qin.year 落地即见秦朝疆域）
  year.value = yearOf('qin') ?? -221
}

// ---- URL 状态同步（router.replace，不污染历史）----
let urlReady = false
watch([mode, year, selectedDynasty], () => {
  if (!urlReady) return
  const query =
    mode.value === 'dynasty' && selectedDynasty.value
      ? { d: selectedDynasty.value }
      : { y: String(year.value) }
  router.replace({ query })
})

// 选朝代（chips / 地图点击）→ dynasty 模式：跳代表年、飞镜头、右侧信息卡
function selectDynasty(id) {
  if (!dynastyById(id)) return
  mode.value = 'dynasty'
  selectedDynasty.value = id
  neutralShape.value = null
  const y = yearOf(id)
  if (y != null) year.value = y
  if (mappedIds.value.has(id)) focusKey.value++
}

// 地图点击：有朝代 → dynasty 模式（镜头不动）；中立政权 → 通用卡
function onAtlasSelect(s) {
  if (!s) return
  if (s.dyn) {
    selectedDynasty.value = s.dyn
    mode.value = 'dynasty'
    neutralShape.value = null
  } else {
    neutralShape.value = s
    selectedDynasty.value = null
  }
}

// 拖时间刷 / 播放 → year 模式：清选中，政权平权显示
function onYearUpdate(y) {
  mode.value = 'year'
  year.value = y
  selectedDynasty.value = null
  neutralShape.value = null
}

// ---- 播放 ----
let playTimer = null

function nearestIdx(y) {
  const ys = data.value.changeYears
  let best = 0
  for (let i = 0; i < ys.length; i++) {
    if (Math.abs(ys[i] - y) < Math.abs(ys[best] - y)) best = i
  }
  return best
}

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

onMounted(init)
onUnmounted(() => clearInterval(playTimer))
</script>

<template>
  <div class="map-page">
    <h1 class="page-title">疆域时空地图</h1>
    <p class="page-sub">点击朝代或拖动时间刷看疆域变迁 —— 底图为海岸线与大河，不代表现代国界</p>

    <AppLoading v-if="loading" />
    <div v-else-if="error" class="error-box">
      <p>地图数据加载失败：{{ error }}</p>
      <button @click="init">重新加载</button>
    </div>

    <template v-else>
      <div class="dynasty-chips" role="group" aria-label="选择朝代">
        <button
          v-for="d in dynastyList"
          :key="d.id"
          class="chip"
          :class="{ active: selectedDynasty === d.id, nomap: !mappedIds.has(d.id) }"
          :title="mappedIds.has(d.id) ? d.name : `${d.name}（疆域数据暂缺）`"
          @click="selectDynasty(d.id)"
        >
          <span class="dot" :style="{ background: d.color }" />{{ d.name }}
        </button>
      </div>

      <div class="map-layout">
        <div class="map-col">
          <AtlasMap
            :basemap="data.basemap"
            :full="full"
            :shapes="shapes"
            :selected-id="selectedDynasty"
            :focus-key="focusKey"
            :focus-bbox="focusBbox"
            @select="onAtlasSelect"
          />
          <MapTimeBar
            :years="data.changeYears"
            :year="year"
            :playing="playing"
            @update:year="onYearUpdate"
            @toggle-play="togglePlay"
          />
          <p v-if="!shapes.length" class="map-empty">该年暂无疆域数据</p>
        </div>
        <MapDynastyCard
          class="side-card"
          :dynasty="selectedDynastyObj"
          :chapters="selectedChapters"
          :mapped="selectedDynasty ? mappedIds.has(selectedDynasty) : false"
          :neutral="neutralShape"
        />
      </div>

      <p class="attribution">
        疆域数据 © <a href="https://github.com/Seshat-Global-History-Databank/cliopatria" target="_blank" rel="noopener">Cliopatria</a>（CC BY 4.0）·
        底图 <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener">Natural Earth</a>（公有领域）·
        疆域为学术数据集近似示意，不代表现代国界
      </p>
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

.dynasty-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 8px;
  margin-bottom: 12px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: 13px;
  white-space: nowrap;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}

.chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.chip.nomap {
  opacity: 0.55;
}

.chip.active {
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}

@media (hover: hover) {
  .chip:hover {
    border-color: var(--accent);
  }
}

.map-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.map-col {
  flex: 1;
  min-width: 0;
}

.side-card {
  width: 280px;
  flex-shrink: 0;
  position: sticky;
  top: 76px;
}

.error-box {
  padding: 60px 24px;
  text-align: center;
  color: var(--text-soft);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.map-empty {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--text-soft);
  text-align: center;
}

.attribution {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--text-soft);
}

@media (max-width: 1099px) {
  .map-layout {
    flex-direction: column;
  }

  .side-card {
    width: 100%;
    position: static;
  }
}
</style>
