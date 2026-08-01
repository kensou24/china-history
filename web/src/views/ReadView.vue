<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMeta } from '@/composables/useMeta'
import { loadVolume } from '@/composables/useVolume'
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import Lightbox from '@/components/Lightbox.vue'

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()
const progress = useProgressStore()
const { meta, loadMeta, chapterById, dynastyById } = useMeta()

const chapter = ref(null)
const volData = ref(null)
const loading = ref(true)
const lightbox = ref({ src: '', caption: '', visible: false })
const scrollEl = ref(null)

// 当前章节在全书中的位置（上一章 / 下一章）
const all = computed(() =>
  meta.value ? meta.value.volumes.flatMap((v) => v.chapters) : [],
)
const idx = computed(() => all.value.findIndex((c) => c.id === chapter.value?.id))
const prevCh = computed(() => (idx.value > 0 ? all.value[idx.value - 1] : null))
const nextCh = computed(() =>
  idx.value < all.value.length - 1 ? all.value[idx.value + 1] : null,
)
const dynasty = computed(() =>
  chapter.value ? dynastyById(chapter.value.dynasty) : null,
)

async function loadChapter() {
  loading.value = true
  await loadMeta()
  const ch = chapterById(route.params.id)
  if (!ch) {
    router.replace('/')
    return
  }
  chapter.value = ch
  const volId = meta.value.volumes.findIndex((v) =>
    v.chapters.some((c) => c.id === ch.id),
  ) + 1
  volData.value = await loadVolume(volId)
  const vc = volData.value.chapters.find((c) => c.id === ch.id)
  chapter.value.blocks = vc.blocks
  loading.value = false
}

// 滚动 → 进度记录（节流）
let scrollTimer = null
function onScroll() {
  if (scrollTimer) return
  scrollTimer = setTimeout(() => {
    scrollTimer = null
    const el = scrollEl.value
    if (!el || !chapter.value) return
    const max = el.scrollHeight - el.clientHeight
    const pct = max > 0 ? (el.scrollTop / max) * 100 : 100
    progress.record(chapter.value.id, pct)
  }, 400)
}

watch(
  () => route.params.id,
  () => {
    loadChapter()
    if (scrollEl.value) scrollEl.value.scrollTop = 0
  },
)

onMounted(() => {
  loadChapter()
  if (scrollEl.value) {
    scrollEl.value.addEventListener('scroll', onScroll, { passive: true })
  }
})

onUnmounted(() => {
  if (scrollEl.value) {
    scrollEl.value.removeEventListener('scroll', onScroll)
  }
})

function openLightbox(imgId, caption) {
  lightbox.value = {
    src: `/images_orig/${imgId}.jpeg`,
    imgId,
    caption,
    visible: true,
  }
}

const formatYear = (y) => (y < 0 ? `前${-y}` : `${y}`)
</script>

<template>
  <div v-if="loading" class="loading">加载中…</div>

  <div v-else-if="chapter" class="reader">
    <!-- 顶部章节信息 -->
    <div class="reader-head">
      <div class="crumb">
        <router-link to="/catalog">全书目录</router-link>
        <span class="sep">/</span>
        <span>卷{{ (meta.volumes.findIndex((v) => v.chapters.some((c) => c.id === chapter.id)) + 1) }} ·
          {{ chapter.title }}</span>
      </div>
      <div class="ch-title-row">
        <h1 class="ch-title">{{ chapter.title }}</h1>
        <span v-if="dynasty" class="dynasty-tag" :style="{ background: dynasty.color + '22', color: dynasty.color }">
          {{ dynasty.name }} {{ formatYear(dynasty.start) }}—{{ formatYear(dynasty.end) }}
        </span>
      </div>
      <div class="ch-meta">
        <span>{{ chapter.wordCount.toLocaleString() }} 字</span>
        <span>{{ chapter.imageCount }} 幅插图</span>
        <span v-if="progress.chapters[chapter.id] >= 98">✓ 已读完</span>
      </div>

      <!-- 阅读设置 -->
      <div class="reader-tools">
        <button @click="settings.setFontSize(settings.fontSize - 1)" title="减小字号">A−</button>
        <span class="tool-val">{{ settings.fontSize }}px</span>
        <button @click="settings.setFontSize(settings.fontSize + 1)" title="增大字号">A+</button>
        <span class="tool-sep" />
        <button @click="settings.setLineHeight(settings.lineHeight - 0.2)" title="减小行距">行−</button>
        <span class="tool-val">{{ settings.lineHeight.toFixed(1) }}</span>
        <button @click="settings.setLineHeight(settings.lineHeight + 0.2)" title="增大行距">行+</button>
      </div>
    </div>

    <!-- 正文 -->
    <article
      ref="scrollEl"
      class="reader-body"
      :style="{ fontSize: settings.fontSize + 'px', lineHeight: settings.lineHeight }"
    >
      <template v-for="(b, i) in chapter.blocks" :key="i">
        <h3 v-if="b.t === 'sec'" class="block-sec">{{ b.title }}</h3>
        <p v-else-if="b.t === 'p'" class="block-p">{{ b.text }}</p>
        <figure v-else-if="b.t === 'fig'" class="block-fig">
          <img
            loading="lazy"
            :src="`/images/${b.img}.webp`"
            :alt="b.caption"
            @click="openLightbox(b.img, b.caption)"
          />
          <figcaption v-if="b.caption">{{ b.caption }}</figcaption>
        </figure>
        <p v-else-if="b.t === 'cap'" class="block-cap">{{ b.text }}</p>
      </template>

      <div class="chapter-end">— 本章完 —</div>
    </article>

    <!-- 上下章导航 -->
    <nav class="reader-nav">
      <router-link v-if="prevCh" :to="`/read/${prevCh.id}`" class="nav-item">
        <small>上一章</small>
        {{ prevCh.title }}
      </router-link>
      <span v-else class="nav-item empty">已是第一章</span>
      <router-link v-if="nextCh" :to="`/read/${nextCh.id}`" class="nav-item next">
        <small>下一章</small>
        {{ nextCh.title }}
      </router-link>
      <span v-else class="nav-item empty">已是最后一章</span>
    </nav>
  </div>

  <Lightbox
    :src="lightbox.src"
    :img-id="lightbox.imgId"
    :caption="lightbox.caption"
    :visible="lightbox.visible"
    @close="lightbox.visible = false"
  />
</template>

<style scoped>
.reader {
  max-width: 860px;
  margin: 0 auto;
}

.reader-head {
  margin-bottom: 20px;
}

.crumb {
  font-size: 13px;
  color: var(--text-soft);
  margin-bottom: 8px;
}

.crumb .sep {
  margin: 0 6px;
  color: var(--border);
}

.ch-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.ch-title {
  font-size: 30px;
  margin: 0;
  color: var(--accent);
  letter-spacing: 2px;
}

.ch-meta {
  font-size: 13px;
  color: var(--text-soft);
  display: flex;
  gap: 14px;
  margin: 6px 0 14px;
}

.reader-tools {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  width: fit-content;
}

.reader-tools button {
  padding: 2px 8px;
  font-size: 13px;
}

.tool-val {
  font-size: 12px;
  color: var(--text-soft);
  min-width: 34px;
  text-align: center;
}

.tool-sep {
  width: 1px;
  height: 18px;
  background: var(--border);
  margin: 0 6px;
}

.reader-body {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 40px 48px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  box-shadow: var(--shadow);
}

.block-p {
  margin: 0 0 1em;
  text-indent: 2em;
  text-align: justify;
}

.block-sec {
  font-size: 1.2em;
  margin: 1.4em 0 0.6em;
  color: var(--accent);
  border-left: 4px solid var(--accent-soft);
  padding-left: 10px;
}

.block-fig {
  margin: 24px auto;
  text-align: center;
}

.block-fig img {
  max-width: 100%;
  max-height: 460px;
  border-radius: 6px;
  cursor: zoom-in;
  border: 1px solid var(--border);
  background: var(--bg-soft);
}

.block-fig figcaption {
  font-size: 12.5px;
  color: var(--text-soft);
  margin-top: 8px;
  line-height: 1.6;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
  text-align: center;
}

.block-cap {
  font-size: 12.5px;
  color: var(--text-soft);
  text-align: center;
  margin: -12px 0 16px;
}

.chapter-end {
  text-align: center;
  color: var(--text-soft);
  font-size: 13px;
  padding: 24px 0 8px;
  letter-spacing: 4px;
}

.reader-nav {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 20px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 15px;
  max-width: 46%;
}

.nav-item small {
  color: var(--text-soft);
  font-size: 12px;
}

.nav-item.next {
  text-align: right;
}

.nav-item.empty {
  color: var(--text-soft);
  opacity: 0.6;
}

.loading {
  padding: 80px;
  text-align: center;
  color: var(--text-soft);
}
</style>
