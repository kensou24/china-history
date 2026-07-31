<script setup>
import { onMounted, ref } from 'vue'
import { useMeta } from '@/composables/useMeta'
import DynastyTimeline from '@/components/DynastyTimeline.vue'

const { loadMeta, meta, dynasties } = useMeta()
const loading = ref(true)

onMounted(async () => {
  await loadMeta()
  loading.value = false
})
</script>

<template>
  <div class="home">
    <h1 class="page-title">中国通史 · 朝代时间轴</h1>
    <p class="page-sub">
      全书 {{ meta?.book.chapters }} 章 · {{ (meta?.book.totalChars / 10000).toFixed(1) }} 万字
      · {{ meta?.book.totalImages }} 幅插图 —— 点击朝代查看所属章节
    </p>

    <div v-if="loading" class="loading">加载中…</div>
    <DynastyTimeline v-else :dynasties="dynasties.dynasties" />
  </div>
</template>

<style scoped>
.home .page-title {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--accent);
}

.home .page-sub {
  margin: 0 0 20px;
  color: var(--text-soft);
  font-size: 14px;
}

.loading {
  padding: 60px;
  text-align: center;
  color: var(--text-soft);
}
</style>
