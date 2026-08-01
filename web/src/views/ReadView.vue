<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMeta } from '@/composables/useMeta'
import { loadVolume } from '@/composables/useVolume'
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import { useToast } from '@/composables/useToast'
import Lightbox from '@/components/Lightbox.vue'
import AppLoading from '@/components/AppLoading.vue'
import BackToTop from '@/components/BackToTop.vue'

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()
const progress = useProgressStore()
const { toast } = useToast()
const { meta, loadMeta, chapterById, dynastyById, error: metaError } = useMeta()

const chapter = ref(null)
const volData = ref(null)
const loading = ref(true)
const error = ref(null)
const notFound = ref(false)
const lightbox = ref({ src: '', caption: '', visible: false })
const scrollEl = ref(null)
const scrollPct = ref(0)
const imageLoaded = ref({})

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
  error.value = null
  notFound.value = false
  imageLoaded.value = {}
  try {
    await loadMeta()
    if (metaError.value) throw new Error(metaError.value)
    const ch = chapterById(route.params.id)
    if (!ch) {
      notFound.value = true
      loading.value = false
      return
    }
    chapter.value = ch
    const volId = meta.value.volumes.findIndex((v) =>
      v.chapters.some((c) => c.id === ch.id),
    ) + 1
    volData.value = await loadVolume(volId)
    const vc = volData.value.chapters.find((c) => c.id === ch.id)
    chapter.value.blocks = vc.blocks
  } catch (e) {
    error.value = e.message || '章节加载失败'
  } finally {
    loading.value = false
  }
}

function retry() {
  loadChapter()
}

function restoreScroll() {
  const id = chapter.value?.id
  if (!id || !scrollEl.value) return
  const pct = progress.chapters[id]
  if (pct >= 2 && pct < 98) {
    nextTick(() => {
      const el = scrollEl.value
      const max = el.scrollHeight - el.clientHeight
      if (max > 0) {
        el.scrollTop = (pct / 100) * max
        toast(`已从上次阅读的 ${Math.round(pct)}% 处继续`)
      }
    })
  }
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
    scrollPct.value = pct
    progress.record(chapter.value.id, pct)
  }, 400)
}

watch(
  () => route.params.id,
  () => {
    loadChapter().then(() => {
      if (scrollEl.value) scrollEl.value.scrollTop = 0
      restoreScroll()
    })
  },
)

watch(loading, (v) => {
  if (!v && chapter.value) {
    scrollPct.value = progress.chapters[chapter.value.id] || 0
    restoreScroll()
  }
})

onMounted(() => {
  loadChapter().then(() => {
    if (scrollEl.value) {
      scrollEl.value.addEventListener('scroll', onScroll, { passive: true })
    }
  })
  window.addEventListener('keydown', onWindowKey)
})

onUnmounted(() => {
  if (scrollEl.value) {
    scrollEl.value.removeEventListener('scroll', onScroll)
  }
  window.removeEventListener('keydown', onWindowKey)
})

function onImageLoad(imgId) {
  imageLoaded.value[imgId] = true
}

function openLightbox(imgId, caption) {
  lightbox.value = {
    src: `/images_orig/${imgId}.jpeg`,
    imgId,
    caption,
    visible: true,
  }
}

function goPrev() {
  if (prevCh.value) router.push(`/read/${prevCh.value.id}`)
}

function goNext() {
  if (nextCh.value) router.push(`/read/${nextCh.value.id}`)
}

function scrollByPage(dir) {
  const el = scrollEl.value
  if (!el) return
  const amount = el.clientHeight * 0.85 * dir
  el.scrollBy({ top: amount, behavior: reducedMotion() ? 'auto' : 'smooth' })
}

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function onWindowKey(e) {
  if (lightbox.value.visible) return
  const tag = e.target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    goPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    goNext()
  } else if (e.key === 'PageDown' || e.key === ' ') {
    e.preventDefault()
    scrollByPage(1)
  } else if (e.key === 'PageUp') {
    e.preventDefault()
    scrollByPage(-1)
  } else if (e.key === 'Home') {
    e.preventDefault()
    if (scrollEl.value) scrollEl.value.scrollTop = 0
  } else if (e.key === 'End') {
    e.preventDefault()
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  }
}

const formatYear = (y) => (y < 0 ? `前${-y}` : `${y}`)
</script>

<template>
  <div class="read-page">
    <AppLoading v-if="loading" />

  <div v-else-if="error" class="error-box">
    <p>{{ error }}</p>
    <button @click="retry">重新加载</button>
  </div>

  <div v-else-if="notFound" class="error-box">
    <p>未找到该章节</p>
    <router-link to="/catalog">返回全书目录</router-link>
  </div>

  <div v-else-if="chapter" class="reader">
    <!-- 阅读进度条 -->
    <div class="read-progress" aria-label="本章阅读进度" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round(scrollPct)">
      <div :style="{ width: scrollPct + '%' }" />
    </div>

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
        <span class="tool-val" :key="settings.fontSize">{{ settings.fontSize }}px</span>
        <button @click="settings.setFontSize(settings.fontSize + 1)" title="增大字号">A+</button>
        <span class="tool-sep" />
        <button @click="settings.setLineHeight(settings.lineHeight - 0.2)" title="减小行距">行−</button>
        <span class="tool-val" :key="settings.lineHeight">{{ settings.lineHeight.toFixed(1) }}</span>
        <button @click="settings.setLineHeight(settings.lineHeight + 0.2)" title="增大行距">行+</button>
      </div>
      <div class="key-hint">← → 翻章 · 空格 / PageDown 滚屏 · Home/End 跳转</div>
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
            :class="{ loaded: imageLoaded[b.img] }"
            @click="openLightbox(b.img, b.caption)"
            @load="onImageLoad(b.img)"
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

  <BackToTop :target="scrollEl" :threshold="600" />
  </div>
</template>

<style scoped>
.reader {
  max-width: 860px;
  margin: 0 auto;
}

.read-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  z-index: 60;
  background: transparent;
}

.read-progress > div {
  height: 100%;
  background: var(--accent);
  transition: width 0.2s;
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
  flex-wrap: wrap;
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
  animation: valuePulse 0.3s ease;
}

@keyframes valuePulse {
  0% {
    color: var(--accent);
  }
  100% {
    color: var(--text-soft);
  }
}

.tool-sep {
  width: 1px;
  height: 18px;
  background: var(--border);
  margin: 0 6px;
}

.key-hint {
  font-size: 12px;
  color: var(--text-soft);
  margin-top: 8px;
}

.reader-body {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 40px 48px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  box-shadow: var(--shadow);
  transition: font-size 0.2s, line-height 0.2s, background 0.25s, border-color 0.25s;
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
  min-height: 180px;
  background: var(--bg-soft);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.block-fig img {
  max-width: 100%;
  max-height: 460px;
  border-radius: 6px;
  cursor: zoom-in;
  border: 1px solid var(--border);
  background: var(--bg-soft);
  opacity: 0;
  transition: opacity 0.3s;
}

.block-fig img.loaded {
  opacity: 1;
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

.error-box {
  padding: 80px 24px;
  text-align: center;
  color: var(--text-soft);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  max-width: 560px;
  margin: 0 auto;
}

.error-box p {
  margin: 0 0 16px;
}

@media (max-width: 768px) {
  .reader-body {
    padding: 20px 18px;
    max-height: calc(100vh - 240px);
  }

  .ch-title {
    font-size: 24px;
  }

  .reader-tools {
    width: 100%;
    justify-content: center;
  }

  .key-hint {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tool-val {
    animation: none;
  }

  .block-fig img {
    transition: none;
    opacity: 1;
  }
}
</style>
