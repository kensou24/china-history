<script setup>
import { computed, onMounted, ref } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { useDebounce } from '@/composables/useDebounce'
import { useProgressStore } from '@/stores/progress'
import DynastyTimeline from '@/components/DynastyTimeline.vue'
import AppLoading from '@/components/AppLoading.vue'
import BackToTop from '@/components/BackToTop.vue'

const { loadMeta, meta, dynasties, error, chapterById } = useMeta()
const progress = useProgressStore()
const loading = ref(true)
const keyword = ref('')
const debouncedKeyword = useDebounce(keyword, 250)

const continueChapter = computed(() => {
  if (!progress.lastRead) return null
  return chapterById(progress.lastRead)
})

const continuePct = computed(() => progress.chapters[progress.lastRead] || 0)

async function init() {
  loading.value = true
  try {
    await loadMeta()
  } catch {
    /* error 已写入 store */
  } finally {
    loading.value = false
  }
}

onMounted(init)
</script>

<template>
  <div class="home">
    <h1 class="page-title">中国通史 · 朝代时间轴</h1>
    <p class="page-sub">
      <template v-if="meta">
        全书 {{ meta.book.chapters }} 章 · {{ (meta.book.totalChars / 10000).toFixed(1) }} 万字
        · {{ meta.book.totalImages }} 幅插图 —— 点击朝代查看所属章节
      </template>
      <template v-else>五卷本 · 以朝代时间轴为核心导航</template>
    </p>

    <input
      v-if="!loading && !error"
      v-model="keyword"
      class="search-input"
      type="search"
      placeholder="搜索人物 / 事件 / 朝代，如：汉武帝、贞观之治…"
      aria-label="搜索人物、事件或朝代"
    />

    <router-link
      v-if="!loading && !error && continueChapter && continuePct < 98"
      :to="`/read/${continueChapter.id}`"
      class="continue-card chapter-card"
    >
      <span class="continue-label">继续阅读</span>
      <h3>{{ continueChapter.title }}</h3>
      <div class="progress-bar">
        <div :style="{ width: continuePct + '%' }" />
      </div>
      <span class="continue-pct">已读 {{ Math.round(continuePct) }}%</span>
    </router-link>

    <AppLoading v-if="loading" />

    <div v-else-if="error" class="error-box">
      <p>数据加载失败：{{ error }}</p>
      <button @click="init">重新加载</button>
    </div>

    <DynastyTimeline
      v-else
      :dynasties="dynasties.dynasties"
      :keyword="debouncedKeyword"
      @update:keyword="keyword = $event"
    />

    <BackToTop />
  </div>
</template>

<style scoped>
.home .page-title {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--accent);
}

.home .page-sub {
  margin: 0 0 14px;
  color: var(--text-soft);
  font-size: 14px;
}

.search-input {
  width: 100%;
  max-width: 480px;
  padding: 10px 16px;
  font-size: 15px;
  font-family: inherit;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  margin-bottom: 18px;
}

.error-box {
  padding: 60px 24px;
  text-align: center;
  color: var(--text-soft);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.error-box p {
  margin: 0 0 16px;
}

.continue-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px 14px;
  align-items: center;
  max-width: 480px;
  margin-bottom: 18px;
  text-decoration: none;
}

.continue-card h3 {
  margin: 0;
  font-size: 16px;
  grid-column: 2 / 3;
}

.continue-label {
  font-size: 12px;
  color: var(--accent);
  border: 1px solid var(--accent-soft);
  border-radius: 4px;
  padding: 1px 8px;
  grid-column: 1 / 2;
}

.continue-card .progress-bar {
  grid-column: 2 / 3;
  height: 4px;
}

.continue-pct {
  font-size: 12px;
  color: var(--text-soft);
  grid-column: 3 / 4;
}

@media (max-width: 768px) {
  .home .page-title {
    font-size: 22px;
  }
}
</style>
