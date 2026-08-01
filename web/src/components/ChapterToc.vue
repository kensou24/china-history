<script setup>
// 章内小节导航：桌面宽屏（≥1280px）右侧 sticky 栏；点击跳转 + 滚动联动高亮
defineProps({
  items: { type: Array, required: true }, // [{ title, blockIndex }]
  active: { type: Number, default: -1 }, // 当前小节在 items 中的下标
})
const emit = defineEmits(['jump'])
</script>

<template>
  <nav class="chapter-toc" aria-label="本章小节">
    <div class="toc-title">本章小节</div>
    <button
      v-for="(s, i) in items"
      :key="s.blockIndex"
      class="toc-item"
      :class="{ active: i === active }"
      :aria-current="i === active ? 'true' : undefined"
      @click="emit('jump', s)"
    >
      {{ s.title }}
    </button>
  </nav>
</template>

<style scoped>
.chapter-toc {
  position: sticky;
  top: 76px;
  width: 200px;
  flex-shrink: 0;
  max-height: calc(100vh - 100px);
  max-height: calc(100dvh - 100px);
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 10px;
}

.toc-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 2px;
  padding: 0 8px 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 6px;
}

.toc-item {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--text-soft);
}

.toc-item.active {
  color: var(--accent);
  font-weight: 600;
  background: var(--bg-soft);
}

@media (hover: hover) {
  .toc-item:hover {
    background: var(--bg-soft);
    color: var(--accent);
  }
}
</style>
