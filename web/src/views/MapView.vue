<script setup>
import { computed, onMounted, ref } from 'vue'
import { useMapData } from '@/composables/useMapData'
import AppLoading from '@/components/AppLoading.vue'

const { data, error, loadMap, activeShapes } = useMapData()
const loading = ref(true)
const year = ref(-221) // 临时：Task 7 接入时间刷
const shapes = computed(() => activeShapes(year.value))

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

    <!-- 冒烟：底图 + 当前年活跃政权数（Task 6 替换为 AtlasMap） -->
    <svg v-else :viewBox="data.viewBox" class="smoke-map">
      <path :d="data.basemap.coast" fill="none" stroke="var(--text-soft)" stroke-width="1" />
      <path v-for="(r, i) in data.basemap.rivers" :key="i" :d="r"
            fill="none" stroke="var(--accent-soft)" stroke-width="1" />
      <text x="20" y="30" font-size="18" fill="var(--text)">
        前221年 · 活跃政权 {{ shapes.length }} 个 · 城市 {{ data.basemap.cities.length }} 个
      </text>
    </svg>
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

.smoke-map {
  width: 100%;
  height: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
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
