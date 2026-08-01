<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { useProgressStore } from '@/stores/progress'
import { useDebounce } from '@/composables/useDebounce'
import AppLoading from '@/components/AppLoading.vue'
import BackToTop from '@/components/BackToTop.vue'
import { reducedMotion } from '@/utils'

const { loadMeta, meta, dynastyById, error } = useMeta()
const progress = useProgressStore()
const loading = ref(true)
const search = ref('')
const debouncedSearch = useDebounce(search, 250)

const filteredVolumes = computed(() => {
  if (!meta.value) return []
  const q = debouncedSearch.value.trim()
  return meta.value.volumes.map((v) => ({
    ...v,
    chapters: v.chapters.filter(
      (c) =>
        !q ||
        c.title.includes(q) ||
        c.summary.includes(q) ||
        (dynastyById(c.dynasty)?.name || '').includes(q),
    ),
  }))
})

const matchedCount = computed(() =>
  filteredVolumes.value.reduce((sum, v) => sum + v.chapters.length, 0),
)

const totalProgress = computed(() => {
  if (!meta.value) return 0
  const total = meta.value.book.chapters
  return total > 0 ? (progress.finishedCount / total) * 100 : 0
})

async function init() {
  loading.value = true
  try {
    await loadMeta()
  } catch {
    /* error 已写入 store */
  } finally {
    loading.value = false
    setupCardReveal()
  }
}

onMounted(init)
onUnmounted(() => cardObserver?.disconnect())

function clearSearch() {
  search.value = ''
}

// ---- 卡片滚动浮现 ----
let cardObserver = null

// 进入视口的卡片按批次 35ms 级联浮现；筛选变化后重挂观察（只补未揭示的新卡）
function setupCardReveal() {
  cardObserver?.disconnect()
  cardObserver = null
  if (reducedMotion()) return
  nextTick(() => {
    cardObserver = new IntersectionObserver(
      (entries) => {
        const hits = entries.filter((e) => e.isIntersecting)
        hits.forEach((en, i) => {
          const el = en.target
          const delay = Math.min(i * 35, 280)
          el.style.transitionDelay = `${delay}ms`
          el.classList.add('card-shown')
          cardObserver.unobserve(el)
          // 揭示完成后清掉延迟，避免拖累 hover/active 的即时反馈
          setTimeout(() => (el.style.transitionDelay = ''), delay + 450)
        })
      },
      { rootMargin: '0px 0px -4% 0px', threshold: 0.05 },
    )
    document
      .querySelectorAll('.catalog .chapter-card:not(.card-shown)')
      .forEach((el) => cardObserver.observe(el))
  })
}

watch(filteredVolumes, setupCardReveal)
</script>

<template>
  <div class="catalog">
    <h1 class="page-title">全书目录</h1>
    <p class="page-sub">五卷 · 100 章 —— 按卷浏览，或搜索章节 / 人物 / 朝代</p>

    <div v-if="!loading && !error" class="total-progress">
      <span>全书进度</span>
      <div class="progress-bar">
        <div :style="{ width: totalProgress + '%' }" />
      </div>
      <span>{{ progress.finishedCount }}/{{ meta?.book.chapters }} 章</span>
    </div>

    <input
      v-if="!loading && !error"
      v-model="search"
      class="search-input"
      type="search"
      placeholder="搜索章节名、摘要或朝代…"
      aria-label="搜索章节名、摘要或朝代"
    />

    <AppLoading v-if="loading" />

    <div v-else-if="error" class="error-box">
      <p>数据加载失败：{{ error }}</p>
      <button @click="init">重新加载</button>
    </div>

    <template v-else>
      <p v-if="debouncedSearch.trim()" class="match-hint">
        匹配 {{ matchedCount }} 章
      </p>

      <section v-for="v in filteredVolumes" :key="v.id" class="volume">
        <h2 class="volume-title">
          <span class="vol-badge">卷{{ v.id }}</span>
          {{ v.title }}
          <small>{{ v.chapters.length }} 章</small>
        </h2>
        <TransitionGroup name="cards" tag="div" class="chapter-grid">
          <router-link
            v-for="c in v.chapters"
            :key="c.id"
            :to="`/read/${c.id}`"
            class="chapter-card"
          >
            <h3>{{ c.title }}</h3>
            <p class="summary">{{ c.summary }}</p>
            <div class="meta">
              <span class="dynasty-tag">{{ dynastyById(c.dynasty)?.name || '—' }}</span>
              <span>{{ c.wordCount.toLocaleString() }} 字</span>
              <span>{{ c.imageCount }} 图</span>
              <span v-if="progress.chapters[c.id] >= 98" class="done">✓ 已读</span>
            </div>
            <div v-if="progress.chapters[c.id]" class="progress-bar">
              <div :style="{ width: Math.min(100, progress.chapters[c.id]) + '%' }" />
            </div>
          </router-link>
        </TransitionGroup>
      </section>

      <div v-if="matchedCount === 0" class="empty">
        <p>没有匹配「{{ debouncedSearch }}」的章节</p>
        <button @click="clearSearch">清除搜索</button>
      </div>
    </template>

    <BackToTop />
  </div>
</template>

<style scoped>
.page-title {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--accent);
}

.page-sub {
  margin: 0 0 16px;
  color: var(--text-soft);
  font-size: 14px;
}

.search-input {
  width: 100%;
  max-width: 420px;
  padding: 8px 14px;
  font-size: 15px;
  font-family: inherit;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  margin-bottom: 24px;
}

.volume {
  margin-bottom: 30px;
}

.volume-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 19px;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.volume-title small {
  color: var(--text-soft);
  font-weight: 400;
  font-size: 13px;
}

.vol-badge {
  background: var(--accent);
  color: var(--surface);
  border-radius: 6px;
  padding: 2px 10px;
  font-size: 14px;
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

/* 卡片浮现：初始隐藏，JS 观察进入视口后加 card-shown */
.chapter-card {
  opacity: 0;
  transform: translateY(16px);
  transition:
    opacity 0.4s ease,
    transform 0.4s ease,
    box-shadow 0.15s ease,
    background 0.25s,
    border-color 0.25s;
}

.chapter-card.card-shown {
  opacity: 1;
  transform: none;
}

@media (hover: hover) {
  .chapter-card.card-shown:hover {
    transform: translateY(-2px);
  }
}

.chapter-card.card-shown:active {
  transform: translateY(-1px) scale(0.98);
}

/* 未揭示卡片的进度条压到 0，揭示时随卡片一同涨起 */
.chapter-card .progress-bar > div {
  transition: width 0.5s ease 0.15s;
}

.chapter-card:not(.card-shown) .progress-bar > div {
  width: 0 !important;
}

/* 筛选 FLIP：幸存卡片滑向新位置，离场卡片快速淡出 */
.cards-move {
  transition: transform 0.35s ease;
}

.cards-leave-active {
  position: absolute;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.cards-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

.chapter-card .done {
  color: var(--accent);
  font-weight: 600;
}

.match-hint {
  font-size: 13px;
  color: var(--text-soft);
  margin: -8px 0 16px;
}

.total-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 420px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-soft);
}

.total-progress .progress-bar {
  flex: 1;
  height: 6px;
}

.chapter-card .progress-bar {
  margin-top: 10px;
  height: 4px;
}

.empty {
  color: var(--text-soft);
  padding: 40px;
  text-align: center;
  background: var(--surface);
  border: 1px dashed var(--border);
  border-radius: 12px;
}

.empty p {
  margin: 0 0 14px;
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

@media (max-width: 768px) {
  .page-title {
    font-size: 22px;
  }

  .volume-title {
    font-size: 17px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chapter-card {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
