<script setup>
import { computed, onMounted, ref } from 'vue'
import { useMapData } from '@/composables/useMapData'
import { useToast } from '@/composables/useToast'
import AppLoading from '@/components/AppLoading.vue'
import AtlasMap from '@/components/AtlasMap.vue'

const { data, error, loadMap, activeShapes } = useMapData()
const { toast } = useToast()
const loading = ref(true)
const year = ref(-221) // 临时：Task 7 接入时间刷
const shapes = computed(() => activeShapes(year.value))
const full = computed(() => {
  const [x, y, w, h] = (data.value?.viewBox || '0 0 1000 800').split(' ').map(Number)
  return { x, y, w, h }
})

// 临时：Task 8 替换为双模式选择逻辑
function onSelect(s) {
  if (s) toast(s.dyn ? s.n : `${s.n}（中立政权）`)
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

    <AtlasMap
      v-else
      :basemap="data.basemap"
      :full="full"
      :shapes="shapes"
      :selected-id="null"
      :focus-key="0"
      @select="onSelect"
    />
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
