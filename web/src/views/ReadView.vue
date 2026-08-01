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
import DynastyRail from '@/components/DynastyRail.vue'
import ChapterToc from '@/components/ChapterToc.vue'
import { yearLabel, reducedMotion, assetUrl } from '@/utils'

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()
const progress = useProgressStore()
const { toast } = useToast()
const { meta, loadMeta, chapterById, dynastyById, error: metaError } = useMeta()

const chapter = ref(null)
const volData = ref(null)
const currentVol = ref(0)
const loading = ref(true)
const error = ref(null)
const notFound = ref(false)
const lightbox = ref({ src: '', caption: '', visible: false })
const scrollEl = ref(null)
const scrollPct = ref(0)
const imageLoaded = ref({})
const slideDir = ref('next')
const slideName = computed(() => 'slide-' + slideDir.value)

// ---- 窄屏朝代抽屉（<1100px 时左轨改为浮动按钮 + 抽屉） ----
const isNarrow = ref(window.matchMedia('(max-width: 1099px)').matches)
const drawerOpen = ref(false)
let narrowMq = null

function onNarrowChange(e) {
  isNarrow.value = e.matches
  if (!e.matches) drawerOpen.value = false
}

// ---- 宽屏章内小节 TOC（≥1280px 显示右侧栏） ----
const canToc = ref(window.matchMedia('(min-width: 1280px)').matches)
let wideMq = null

function onWideChange(e) {
  canToc.value = e.matches
}

watch(drawerOpen, (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
})

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

// 阅读时长估计：按 400 字/分钟
const readMinutes = computed(() =>
  chapter.value ? Math.max(1, Math.ceil(chapter.value.wordCount / 400)) : 0,
)

// ---- 章内小节 TOC ----
const tocItems = computed(() =>
  chapter.value
    ? chapter.value.blocks
        .map((b, i) => (b.t === 'sec' ? { title: b.title, blockIndex: i } : null))
        .filter(Boolean)
    : [],
)
const activeToc = ref(-1)

// scroll spy：高亮最后一个越过容器顶部（+80px 缓冲）的小节
function updateTocSpy() {
  const el = scrollEl.value
  if (!el || !tocItems.value.length) {
    activeToc.value = -1
    return
  }
  const secs = el.querySelectorAll('.block-sec')
  let cur = -1
  for (let i = 0; i < secs.length; i++) {
    if (secs[i].offsetTop <= el.scrollTop + 80) cur = i
    else break
  }
  activeToc.value = cur
}

function jumpToSection(s) {
  const el = scrollEl.value
  if (!el) return
  const target = el.querySelector(`[data-i="${s.blockIndex}"]`)
  if (!target) return
  el.scrollTo({
    top: target.offsetTop - 12,
    behavior: reducedMotion() ? 'auto' : 'smooth',
  })
}

// 加载序号：慢网络下跨卷快速翻章时，丢弃过期请求的结果，避免旧章覆盖新章
let loadSeq = 0

async function loadChapter() {
  const seq = ++loadSeq
  const id = route.params.id
  error.value = null
  notFound.value = false
  imageLoaded.value = {}
  try {
    await loadMeta()
    if (seq !== loadSeq) return
    if (metaError.value) throw new Error(metaError.value)
    const ch = chapterById(id)
    if (!ch) {
      notFound.value = true
      return
    }
    const volId = meta.value.volumes.findIndex((v) =>
      v.chapters.some((c) => c.id === ch.id),
    ) + 1
    // 同卷内翻章不闪 loading，章节内容直接带方向过渡切换
    if (currentVol.value !== volId) {
      loading.value = true
      const data = await loadVolume(volId)
      if (seq !== loadSeq) return // 竞态：已有更新的加载在进行
      volData.value = data
      currentVol.value = volId
    }
    const vc = volData.value.chapters.find((c) => c.id === ch.id)
    chapter.value = { ...ch, blocks: vc.blocks }
    document.title = `${ch.title} · 中国通史学习`
    // 空闲时预取下一卷，跨卷翻章零 loading；失败静默（翻章时会自然重试）
    const nextVol = volId + 1
    if (nextVol <= 5) {
      const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 2000))
      idle(() => loadVolume(nextVol).catch(() => {}))
    }
  } catch (e) {
    if (seq === loadSeq) error.value = e.message || '章节加载失败'
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function retry() {
  loadChapter()
}

// 进度恢复提示：本次会话内每章只提示一次
const restoreToasted = new Set()

function restoreScroll() {
  const id = chapter.value?.id
  if (!id || !scrollEl.value) return
  const pct = progress.chapters[id]
  if (pct >= 2 && pct < 98) {
    nextTick(() => {
      const el = scrollEl.value
      if (!el) return
      const max = el.scrollHeight - el.clientHeight
      if (max > 0) {
        el.scrollTop = (pct / 100) * max
        if (!restoreToasted.has(id)) {
          restoreToasted.add(id)
          toast(`已从上次阅读的 ${Math.round(pct)}% 处继续`)
        }
      }
    })
  }
}

// 滚动 → 进度条即时更新（rAF 合帧）；持久化延迟到停止滚动 400ms 后，
// 避免滚动期间高频写 localStorage，也让进度条跟手
let recordTimer = null
let rafId = null

function currentPct() {
  const el = scrollEl.value
  if (!el) return scrollPct.value
  const max = el.scrollHeight - el.clientHeight
  return max > 0 ? (el.scrollTop / max) * 100 : 100
}

function onScroll() {
  if (!rafId) {
    rafId = requestAnimationFrame(() => {
      rafId = null
      scrollPct.value = currentPct()
      updateTocSpy()
    })
  }
  clearTimeout(recordTimer)
  recordTimer = setTimeout(flushRecord, 400)
}

function flushRecord() {
  clearTimeout(recordTimer)
  recordTimer = null
  if (!chapter.value) return
  scrollPct.value = currentPct()
  const isNewFinish = progress.record(chapter.value.id, scrollPct.value)
  if (isNewFinish) toast(`✓ 已读完《${chapter.value.title}》`)
}

watch(
  () => route.params.id,
  (newId, oldId) => {
    // 比较新旧章节序号决定过渡方向：往后翻从右滑入，往前翻从左滑入
    const ni = all.value.findIndex((c) => c.id === newId)
    const oi = all.value.findIndex((c) => c.id === oldId)
    slideDir.value = oi === -1 || ni >= oi ? 'next' : 'prev'
    loadChapter()
  },
)

// 正文容器每次随过渡重建：统一在此重挂滚动监听、恢复进度、启动浮现观察
watch(
  scrollEl,
  (el, oldEl) => {
    if (oldEl) oldEl.removeEventListener('scroll', onScroll)
    if (!el) return
    el.addEventListener('scroll', onScroll, { passive: true })
    scrollPct.value = chapter.value ? progress.chapters[chapter.value.id] || 0 : 0
    restoreScroll()
    updateTocSpy()
    setupReveal()
  },
  { flush: 'post' },
)

// ---- 段落逐段浮现 ----
let revealObserver = null

function setupReveal() {
  revealObserver?.disconnect()
  revealObserver = null
  if (reducedMotion()) return
  const root = scrollEl.value
  if (!root) return
  revealObserver = new IntersectionObserver(
    (entries) => {
      for (const en of entries) {
        if (en.isIntersecting) {
          en.target.classList.add('revealed')
          revealObserver.unobserve(en.target)
        }
      }
    },
    { root, rootMargin: '0px 0px -6% 0px', threshold: 0.05 },
  )
  root.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el))
}

// 首屏几个块级联入场（stagger），后续滚动即时浮现
function revealStyle(i) {
  return i < 6 ? { transitionDelay: `${i * 45}ms` } : undefined
}

onMounted(() => {
  loadChapter()
  window.addEventListener('keydown', onWindowKey)
  narrowMq = window.matchMedia('(max-width: 1099px)')
  narrowMq.addEventListener('change', onNarrowChange)
  wideMq = window.matchMedia('(min-width: 1280px)')
  wideMq.addEventListener('change', onWideChange)
})

onUnmounted(() => {
  if (scrollEl.value) {
    scrollEl.value.removeEventListener('scroll', onScroll)
  }
  if (rafId) cancelAnimationFrame(rafId)
  flushRecord() // 滚动后 400ms 内离开页面也能保住进度
  revealObserver?.disconnect()
  window.removeEventListener('keydown', onWindowKey)
  narrowMq?.removeEventListener('change', onNarrowChange)
  wideMq?.removeEventListener('change', onWideChange)
  document.body.style.overflow = ''
})

function onImageLoad(imgId) {
  imageLoaded.value[imgId] = true
}

function openLightbox(imgId, caption) {
  lightbox.value = {
    src: assetUrl(`/images_orig/${imgId}.jpeg`),
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

function onWindowKey(e) {
  if (lightbox.value.visible) return
  if (e.key === 'Escape' && drawerOpen.value) {
    drawerOpen.value = false
    return
  }
  // 表单控件与按钮放行：空格在按钮上是激活，不能抢成滚屏
  const tag = e.target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'SELECT') return
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

  <template v-else>
    <!-- 阅读进度条（放在过渡容器外，避免 transform 使 fixed 定位失效） -->
    <div v-if="chapter" class="read-progress" aria-label="本章阅读进度" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round(scrollPct)">
      <div :style="{ width: scrollPct + '%' }" />
    </div>

    <div class="read-layout">
      <DynastyRail v-if="chapter && !isNarrow" :current-chapter-id="chapter.id" />

      <div class="reader-col">
    <Transition :name="slideName" mode="out-in">
    <div v-if="chapter" :key="chapter.id" class="reader">
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
          {{ dynasty.name }} {{ yearLabel(dynasty.start) }}—{{ yearLabel(dynasty.end) }}
        </span>
      </div>
      <div class="ch-meta">
        <span>{{ chapter.wordCount.toLocaleString() }} 字</span>
        <span>约 {{ readMinutes }} 分钟</span>
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
        <h3 v-if="b.t === 'sec'" class="block-sec reveal" :data-i="i" :style="revealStyle(i)">{{ b.title }}</h3>
        <p v-else-if="b.t === 'p'" class="block-p reveal" :style="revealStyle(i)">{{ b.text }}</p>
        <figure v-else-if="b.t === 'fig'" class="block-fig reveal" :style="revealStyle(i)">
          <img
            loading="lazy"
            :src="assetUrl(`/images/${b.img}.webp`)"
            :alt="b.caption"
            :class="{ loaded: imageLoaded[b.img] }"
            @click="openLightbox(b.img, b.caption)"
            @load="onImageLoad(b.img)"
          />
          <figcaption v-if="b.caption">{{ b.caption }}</figcaption>
        </figure>
        <p v-else-if="b.t === 'cap'" class="block-cap reveal" :style="revealStyle(i)">{{ b.text }}</p>
      </template>

      <div class="chapter-end reveal">— 本章完 —</div>
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
    </Transition>
      </div>

      <ChapterToc
        v-if="chapter && canToc && tocItems.length"
        :items="tocItems"
        :active="activeToc"
        @jump="jumpToSection"
      />
    </div>

    <!-- 窄屏：浮动朝代按钮 + 抽屉式导航 -->
    <button
      v-if="chapter && isNarrow && !drawerOpen"
      class="rail-fab"
      :style="dynasty ? { background: dynasty.color } : null"
      aria-label="打开朝代导航"
      @click="drawerOpen = true"
    >
      {{ dynasty?.name || '朝代' }}
    </button>

    <Transition name="drawer">
      <div v-if="drawerOpen && chapter" class="rail-drawer">
        <div class="drawer-backdrop" @click="drawerOpen = false" />
        <DynastyRail
          :current-chapter-id="chapter.id"
          class="drawer-rail"
          @navigate="drawerOpen = false"
        />
      </div>
    </Transition>
  </template>

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

/* 左轨 + 正文双栏布局 */
.read-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.reader-col {
  flex: 1;
  min-width: 0;
}

/* 窄屏浮动朝代按钮 */
.rail-fab {
  position: fixed;
  left: 16px;
  bottom: 20px;
  z-index: 40;
  border: none;
  border-radius: 999px;
  padding: 8px 16px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}

/* 窄屏抽屉 */
.rail-drawer {
  position: fixed;
  inset: 0;
  z-index: 90;
}

.drawer-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(10, 8, 4, 0.45);
}

.rail-drawer .drawer-rail {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 280px;
  max-height: none;
  border-radius: 0;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.22s ease;
}

.drawer-enter-active .drawer-rail,
.drawer-leave-active .drawer-rail {
  transition: transform 0.25s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer-rail,
.drawer-leave-to .drawer-rail {
  transform: translateX(-100%);
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
  max-height: calc(100dvh - 260px); /* dvh：移动端地址栏伸缩时高度不跳 */
  overflow-y: auto;
  box-shadow: var(--shadow);
  transition: font-size 0.2s, line-height 0.2s, background 0.25s, border-color 0.25s;
}

.block-p {
  margin: 0 0 1em;
  text-indent: 2em;
  text-align: justify;
  hanging-punctuation: first allow-end; /* 中文标点悬挂，不支持则无害降级 */
}

/* 段落滚动浮现：占位不变（transform + opacity），滚动时无重排 */
.reveal {
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 0.45s ease, transform 0.45s ease;
}

.reveal.revealed {
  opacity: 1;
  transform: none;
}

/* 章节方向过渡：下一章从右入/向左出，上一章反向 */
.slide-next-enter-active,
.slide-next-leave-active,
.slide-prev-enter-active,
.slide-prev-leave-active {
  transition: opacity 0.26s ease, transform 0.26s ease;
}

.slide-next-enter-from {
  opacity: 0;
  transform: translateX(56px);
}

.slide-next-leave-to {
  opacity: 0;
  transform: translateX(-56px);
}

.slide-prev-enter-from {
  opacity: 0;
  transform: translateX(-56px);
}

.slide-prev-leave-to {
  opacity: 0;
  transform: translateX(56px);
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
  filter: blur(10px);
  transform: scale(1.02);
  transition: opacity 0.4s ease, filter 0.4s ease, transform 0.4s ease;
}

.block-fig img.loaded {
  opacity: 1;
  filter: blur(0);
  transform: none;
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
    max-height: calc(100dvh - 240px);
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
    filter: none;
    transform: none;
  }

  /* 减少动态时段落直接显示（JS 侧也不会启动观察器） */
  .reveal {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .slide-next-enter-active,
  .slide-next-leave-active,
  .slide-prev-enter-active,
  .slide-prev-leave-active {
    transition: none;
  }

  .drawer-enter-active,
  .drawer-leave-active,
  .drawer-enter-active .drawer-rail,
  .drawer-leave-active .drawer-rail {
    transition: none;
  }
}
</style>
