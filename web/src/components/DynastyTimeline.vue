<script setup>
import { computed, ref } from 'vue'
import { useMeta } from '@/composables/useMeta'

const props = defineProps({
  dynasties: { type: Array, required: true },
})

const { meta, chapterById } = useMeta()
const selected = ref(null)
const hover = ref(null)

// 时间范围：史前段压缩展示（-3000 起），其余线性
const T0 = -3000
const T1 = 1912

const widthOf = (d) => {
  const span = d.end - d.start
  if (d.start <= -2070) {
    // 史前：固定给 6% 宽度
    return 6
  }
  return (span / (T1 - T0)) * 94
}

const chaptersOf = (d) =>
  d.chapterIds.map((id) => chapterById(id)).filter(Boolean)

const formatYear = (y) => (y < 0 ? `前${-y}` : `${y}`)
</script>

<template>
  <div class="timeline">
    <div class="axis">
      <div
        v-for="d in dynasties"
        :key="d.id"
        class="dyn-block"
        :style="{
          width: widthOf(d) + '%',
          background: d.color,
        }"
        :class="{ active: selected?.id === d.id }"
        @mouseenter="hover = d"
        @mouseleave="hover = null"
        @click="selected = selected?.id === d.id ? null : d"
      >
        <span class="dyn-name">{{ d.name }}</span>
        <span class="dyn-years">{{ formatYear(d.start) }}—{{ formatYear(d.end) }}</span>
      </div>
    </div>
    <div class="axis-scale">
      <span>前3000</span><span>前2070</span><span>前221</span><span>618</span><span>1912</span>
    </div>

    <!-- hover 信息卡 -->
    <div v-if="hover" class="hover-card">
      <strong>{{ hover.name }}</strong>
      <span>{{ formatYear(hover.start) }} — {{ formatYear(hover.end) }}</span>
      <span>{{ hover.chapterIds.length }} 章</span>
    </div>

    <!-- 选中朝代 → 章节卡片 -->
    <section v-if="selected" class="dyn-chapters">
      <h2>
        {{ selected.name }}（{{ formatYear(selected.start) }}—{{ formatYear(selected.end) }}）
        · {{ selected.chapterIds.length }} 章
      </h2>
      <div class="chapter-grid">
        <router-link
          v-for="c in chaptersOf(selected)"
          :key="c.id"
          :to="`/read/${c.id}`"
          class="chapter-card"
        >
          <h3>{{ c.title }}</h3>
          <p class="summary">{{ c.summary }}</p>
          <div class="meta">
            <span>{{ c.wordCount.toLocaleString() }} 字</span>
            <span>{{ c.imageCount }} 图</span>
          </div>
        </router-link>
      </div>
    </section>

    <p v-else class="hint">点击朝代区块，查看该朝代对应的全部章节 →</p>
  </div>
</template>

<style scoped>
.timeline {
  position: relative;
}

.axis {
  display: flex;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
  cursor: pointer;
}

.dyn-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 0;
  color: #fff;
  transition: filter 0.15s, transform 0.15s;
  position: relative;
}

.dyn-block:hover {
  filter: brightness(1.12);
  z-index: 2;
}

.dyn-block.active {
  outline: 3px solid var(--text);
  outline-offset: -3px;
  filter: brightness(1.15);
}

.dyn-name {
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.dyn-years {
  font-size: 10.5px;
  white-space: nowrap;
  opacity: 0.9;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.axis-scale {
  display: flex;
  justify-content: space-between;
  color: var(--text-soft);
  font-size: 11px;
  padding: 4px 2px 0;
}

.hover-card {
  position: absolute;
  top: -10px;
  right: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 8px 12px;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 5;
}

.dyn-chapters {
  margin-top: 28px;
}

.dyn-chapters h2 {
  font-size: 20px;
  color: var(--accent);
  margin: 0 0 14px;
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.hint {
  color: var(--text-soft);
  font-size: 13px;
  margin-top: 14px;
}
</style>
