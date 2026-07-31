<script setup>
import { onMounted, ref } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { useProgressStore } from '@/stores/progress'

const { loadMeta, meta, dynastyById } = useMeta()
const progress = useProgressStore()
const loading = ref(true)
const search = ref('')

onMounted(async () => {
  await loadMeta()
  loading.value = false
})

const allChapters = () => {
  if (!meta.value) return []
  const q = search.value.trim()
  return meta.value.volumes.flatMap((v) =>
    v.chapters.filter(
      (c) =>
        !q ||
        c.title.includes(q) ||
        c.summary.includes(q) ||
        (dynastyById(c.dynasty)?.name || '').includes(q),
    ),
  )
}

function volChapters(v) {
  const q = search.value.trim()
  return v.chapters.filter(
    (c) =>
      !q ||
      c.title.includes(q) ||
      c.summary.includes(q) ||
      (dynastyById(c.dynasty)?.name || '').includes(q),
  )
}
</script>

<template>
  <div class="catalog">
    <h1 class="page-title">全书目录</h1>
    <p class="page-sub">五卷 · 100 章 —— 按卷浏览，或搜索章节 / 人物 / 朝代</p>

    <input
      v-model="search"
      class="search-input"
      type="search"
      placeholder="搜索章节名、摘要或朝代…"
    />

    <div v-if="loading" class="loading">加载中…</div>

    <section v-for="v in meta?.volumes" v-else :key="v.id" class="volume">
      <h2 class="volume-title">
        <span class="vol-badge">卷{{ v.id }}</span>
        {{ v.title }}
        <small>{{ v.chapters.length }} 章</small>
      </h2>
      <div class="chapter-grid">
        <router-link
          v-for="c in volChapters(v)"
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
        </router-link>
      </div>
    </section>

    <p v-if="!loading && allChapters().length === 0" class="empty">
      没有匹配「{{ search }}」的章节
    </p>
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
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

.chapter-card .done {
  color: var(--accent);
  font-weight: 600;
}

.empty {
  color: var(--text-soft);
  padding: 40px;
  text-align: center;
}

.loading {
  padding: 60px;
  text-align: center;
  color: var(--text-soft);
}
</style>
