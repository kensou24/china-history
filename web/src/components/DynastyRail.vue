<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useMeta } from '@/composables/useMeta'
import { useProgressStore } from '@/stores/progress'
import { useSettingsStore } from '@/stores/settings'

// 阅读页左侧竖向朝代导航轨：
// 等距行 + 竖脊线（比例轴下短朝代点不中，故不做比例尺），
// 当前章节所属朝代自动展开并滚动居中，点击朝代手风琴展开该朝章节
const props = defineProps({
  currentChapterId: { type: String, required: true },
})

const emit = defineEmits(['navigate'])

const { dynasties, chapterById } = useMeta()
const progress = useProgressStore()
const settings = useSettingsStore()

const railBodyRef = ref(null)
const hoverId = ref(null)
const expandedId = ref(null)

const rows = computed(() =>
  dynasties.value ? [...dynasties.value.dynasties].sort((a, b) => a.start - b.start) : [],
)

const currentChapter = computed(() => chapterById(props.currentChapterId))
const currentDynastyId = computed(() => currentChapter.value?.dynasty || null)
const currentDynasty = computed(() =>
  rows.value.find((d) => d.id === currentDynastyId.value) || null,
)

const yearLabel = (y) => (y < 0 ? `前${-y}` : `${y}`)
const chaptersOf = (d) => d.chapterIds.map((id) => chapterById(id)).filter(Boolean)

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

// hover 联动：时间重叠的并立政权一起点亮，其余压暗（与主时间轴聚光灯同一语言）
const litIds = computed(() => {
  if (!hoverId.value) return null
  const h = rows.value.find((d) => d.id === hoverId.value)
  if (!h) return null
  const set = new Set()
  for (const d of rows.value) {
    if (d.start < h.end && d.end > h.start) set.add(d.id)
  }
  return set
})

function toggle(d) {
  expandedId.value = expandedId.value === d.id ? null : d.id
}

// 当前朝代自动展开 + 滚动到 rail 可视区中部（手动 scrollTo，避免 scrollIntoView 连动页面）
async function focusCurrent(smooth) {
  const id = currentDynastyId.value
  if (!id) return
  expandedId.value = id
  await nextTick()
  const box = railBodyRef.value
  const el = box?.querySelector(`[data-dyn="${id}"]`)
  if (!box || !el) return
  const top = el.offsetTop - box.clientHeight / 2 + el.clientHeight / 2
  box.scrollTo({ top, behavior: smooth && !reducedMotion() ? 'smooth' : 'auto' })
}

watch(currentDynastyId, () => focusCurrent(true))
onMounted(() => focusCurrent(false))
</script>

<template>
  <nav class="dyn-rail" :class="{ collapsed: settings.railCollapsed }" aria-label="朝代导航">
    <template v-if="!settings.railCollapsed">
      <div class="rail-head">
        <span class="rail-title">朝代</span>
        <button
          class="rail-collapse"
          title="收起朝代导航"
          aria-label="收起朝代导航"
          @click="settings.toggleRailCollapsed()"
        >
          «
        </button>
      </div>

      <div ref="railBodyRef" class="rail-body">
        <div
          v-for="d in rows"
          :key="d.id"
          class="rail-row"
          :class="{
            dim: litIds && !litIds.has(d.id),
            linked: litIds && d.id !== hoverId && litIds.has(d.id),
          }"
        >
          <button
            class="dyn-btn"
            :class="{ current: d.id === currentDynastyId }"
            :style="d.id === currentDynastyId
              ? { background: d.color + '22', boxShadow: 'inset 3px 0 0 ' + d.color }
              : null"
            :data-dyn="d.id"
            :aria-expanded="expandedId === d.id"
            @click="toggle(d)"
            @mouseenter="hoverId = d.id"
            @mouseleave="hoverId = null"
          >
            <span class="dot" :style="{ background: d.color }" />
            <span class="dyn-name">{{ d.name }}</span>
            <span class="dyn-years">{{ yearLabel(d.start) }}—{{ yearLabel(d.end) }}</span>
            <span class="chev" :class="{ open: expandedId === d.id }">▸</span>
          </button>

          <div v-if="expandedId === d.id" class="chapter-sub">
            <router-link
              v-for="c in chaptersOf(d)"
              :key="c.id"
              :to="`/read/${c.id}`"
              class="sub-item"
              :class="{ active: c.id === currentChapterId }"
              @click="emit('navigate')"
            >
              <span class="sub-title">{{ c.title }}</span>
              <span v-if="progress.chapters[c.id] >= 98" class="sub-done">✓</span>
              <span v-else-if="c.id === currentChapterId" class="sub-cur">在读</span>
            </router-link>
          </div>
        </div>
      </div>

      <div v-if="currentDynasty" class="rail-foot">
        <span class="dot" :style="{ background: currentDynasty.color }" />
        当前：{{ currentDynasty.name }}
      </div>
    </template>

    <!-- 收起态：细条，点击展开 -->
    <button
      v-else
      class="rail-expand"
      title="展开朝代导航"
      aria-label="展开朝代导航"
      @click="settings.toggleRailCollapsed()"
    >
      <span class="vert-text">朝代</span>
      <span class="vert-chev">»</span>
    </button>
  </nav>
</template>

<style scoped>
.dyn-rail {
  position: sticky;
  top: 76px;
  width: 236px;
  max-height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  overflow: hidden;
  flex-shrink: 0;
}

.dyn-rail.collapsed {
  width: 40px;
}

.rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--border);
}

.rail-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 2px;
}

.rail-collapse {
  padding: 0 6px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--text-soft);
}

.rail-body {
  position: relative;
  overflow-y: auto;
  flex: 1;
  padding: 8px 6px 8px 0;
}

/* 竖脊线 */
.rail-body::before {
  content: '';
  position: absolute;
  left: 16px;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background: var(--border);
  border-radius: 1px;
}

.rail-body::-webkit-scrollbar {
  width: 6px;
}

.rail-row {
  transition: opacity 0.2s ease;
}

.rail-row.dim {
  opacity: 0.35;
}

.dyn-btn {
  position: relative;
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 7px 8px 7px 6px;
  border: none;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  line-height: 1.3;
  transition: background 0.15s;
}

.dyn-btn:hover {
  background: var(--bg-soft);
}

.rail-row.linked .dyn-btn {
  background: var(--bg-soft);
}

.dyn-btn.current {
  /* 行内联样式提供朝代色底与色条 */
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-left: 5px;
  box-shadow: 0 0 0 2px var(--surface);
  z-index: 1;
}

.dyn-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
}

.dyn-years {
  font-size: 10.5px;
  color: var(--text-soft);
  margin-left: auto;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.chev {
  font-size: 10px;
  color: var(--text-soft);
  transition: transform 0.18s ease;
}

.chev.open {
  transform: rotate(90deg);
}

/* 手风琴章节子列表 */
.chapter-sub {
  padding: 2px 6px 6px 30px;
  animation: sub-in 0.18s ease;
}

@keyframes sub-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
}

.sub-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-soft);
  text-decoration: none;
  line-height: 1.35;
}

.sub-item:hover {
  background: var(--bg-soft);
  color: var(--accent);
  text-decoration: none;
}

.sub-item.active {
  color: var(--accent);
  font-weight: 600;
  background: var(--bg-soft);
}

.sub-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.sub-done {
  color: var(--accent);
  font-size: 12px;
}

.sub-cur {
  font-size: 10.5px;
  color: var(--accent);
  border: 1px solid var(--accent-soft);
  border-radius: 4px;
  padding: 0 4px;
  flex-shrink: 0;
}

.rail-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-soft);
}

.rail-foot .dot {
  margin-left: 0;
}

/* 收起态 */
.rail-expand {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 0;
  border: none;
  background: transparent;
  color: var(--text-soft);
}

.rail-expand:hover {
  color: var(--accent);
  background: var(--bg-soft);
}

.vert-text {
  writing-mode: vertical-rl;
  letter-spacing: 4px;
  font-size: 14px;
}

.vert-chev {
  font-size: 12px;
}

@media (prefers-reduced-motion: reduce) {
  .chapter-sub {
    animation: none;
  }

  .chev {
    transition: none;
  }
}
</style>
