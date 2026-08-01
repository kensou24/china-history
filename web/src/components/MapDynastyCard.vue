<script setup>
import { yearLabel } from '@/utils'

defineProps({
  dynasty: { type: Object, default: null }, // dynasties.json 条目
  chapters: { type: Array, default: () => [] },
  mapped: { type: Boolean, default: false }, // false = 疆域无数据降级态
  neutral: { type: Object, default: null }, // 点中的中立政权 shape
})
</script>

<template>
  <aside class="map-card" aria-live="polite">
    <!-- 中立政权通用卡 -->
    <template v-if="neutral">
      <h2>{{ neutral.n }}</h2>
      <p class="years">{{ yearLabel(neutral.from) }} — {{ yearLabel(neutral.to) }}</p>
      <p class="note">同时期并立政权 · 本书未设专章</p>
    </template>

    <!-- 朝代卡 -->
    <template v-else-if="dynasty">
      <h2>
        <span class="dot" :style="{ background: dynasty.color }" />{{ dynasty.name }}
      </h2>
      <p class="years">{{ yearLabel(dynasty.start) }} — {{ yearLabel(dynasty.end) }}</p>
      <p v-if="!mapped" class="note">该时期疆域尚无定论，以下为所属章节</p>
      <router-link class="timeline-link" :to="`/?d=${dynasty.id}`">在时间轴查看 →</router-link>
      <div class="ch-list">
        <router-link
          v-for="c in chapters"
          :key="c.id"
          :to="`/read/${c.id}`"
          class="ch-item"
        >
          {{ c.title }}
        </router-link>
      </div>
    </template>

    <!-- 空态 -->
    <template v-else>
      <p class="note">点击上方朝代或地图上的政权查看详情；拖动时间刷看疆域变迁</p>
    </template>
  </aside>
</template>

<style scoped>
.map-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 18px;
}

.map-card h2 {
  margin: 0 0 4px;
  font-size: 19px;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 8px}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.years {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--text-soft);
}

.note {
  font-size: 13px;
  color: var(--text-soft);
  line-height: 1.7;
}

.timeline-link {
  display: inline-block;
  font-size: 13px;
  margin-bottom: 10px;
}

.ch-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 50vh;
  overflow-y: auto;
}

.ch-item {
  font-size: 14px;
  padding: 6px 10px;
  border-radius: 6px;
  text-decoration: none;
  color: var(--text);
}

@media (hover: hover) {
  .ch-item:hover {
    background: var(--bg-soft);
    color: var(--accent);
  }
}
</style>
