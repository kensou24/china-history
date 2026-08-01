<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import { useToast } from '@/composables/useToast'
import { reducedMotion } from '@/utils'

const route = useRoute()
const settings = useSettingsStore()
const progress = useProgressStore()
const { toasts } = useToast()

const themes = [
  { id: 'auto', label: '自' },
  { id: 'paper', label: '纸' },
  { id: 'sepia', label: '褐' },
  { id: 'dark', label: '夜' },
]

// auto 档跟随系统深浅色；body[data-theme] 只写解析后的具体主题
const systemDark = window.matchMedia('(prefers-color-scheme: dark)')

// 主题背景色映射（与 index.html 防闪脚本一致）
const THEME_BG = { paper: '#f6f1e7', sepia: '#efe0c7', dark: '#1e1d1b' }

const resolveTheme = (t) =>
  t === 'auto' ? (systemDark.matches ? 'dark' : 'paper') : t

function applyTheme(t, animate = false) {
  // 切换瞬间挂过渡类，全站颜色 300ms 渐变；首次加载与 reduced-motion 不触发
  if (animate && !reducedMotion()) {
    document.body.classList.add('theme-anim')
    setTimeout(() => document.body.classList.remove('theme-anim'), 350)
  }
  const r = resolveTheme(t)
  document.body.dataset.theme = r
  // 同步 html 背景与 --bg：首帧（CSS 未应用前）与过滚动区域都用对的主题色
  const c = THEME_BG[r] || THEME_BG.paper
  document.documentElement.style.background = c
  document.documentElement.style.setProperty('--bg', c)
}

function setTheme(t, animate = false) {
  settings.setTheme(t)
  applyTheme(t, animate)
}

setTheme(settings.theme)

function onSystemThemeChange() {
  if (settings.theme === 'auto') applyTheme('auto')
}

systemDark.addEventListener('change', onSystemThemeChange)

// ---- 顶栏自动隐藏：下滚隐藏、上滚浮现 ----
// capture 阶段监听，可同时捕获 reader-body 等内部滚动容器的 scroll 事件
const headerHidden = ref(false)
let lastScrollY = 0

function onScrollCapture(e) {
  const t = e.target
  const y =
    t === document || t === document.documentElement || t === document.body
      ? window.scrollY
      : (t.scrollTop ?? window.scrollY)
  if (y < 80) {
    headerHidden.value = false
    lastScrollY = y
    return
  }
  // 只有同方向累计超过 8px 才翻转，避免抖动
  if (y - lastScrollY > 8) {
    headerHidden.value = true
    lastScrollY = y
  } else if (lastScrollY - y > 8) {
    headerHidden.value = false
    lastScrollY = y
  }
}

onMounted(() => {
  window.addEventListener('scroll', onScrollCapture, { capture: true, passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScrollCapture, { capture: true })
  systemDark.removeEventListener('change', onSystemThemeChange)
})
</script>

<template>
  <header class="app-header" :class="{ hidden: headerHidden }">
    <router-link to="/" class="brand">
      中国通史<small>五卷本 · 交互式学习</small>
    </router-link>
    <nav class="app-nav">
      <router-link to="/">朝代时间轴</router-link>
      <router-link to="/catalog">全书目录</router-link>
      <router-link to="/map">疆域地图</router-link>
    </nav>
    <div class="spacer" />
    <div class="theme-switch" title="阅读主题" role="group" aria-label="阅读主题">
      <button
        v-for="t in themes"
        :key="t.id"
        :class="{ active: settings.theme === t.id }"
        :aria-pressed="settings.theme === t.id"
        @click="setTheme(t.id, true)"
      >
        {{ t.label }}
      </button>
    </div>
  </header>

  <main class="app-main" :class="{ 'read-wide': route.name === 'read' || route.name === 'map' }">
    <router-view v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </router-view>
  </main>

  <!-- Toast 容器 -->
  <div v-if="toasts.length" class="toast-container" aria-live="polite" aria-atomic="true">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast">{{ t.message }}</div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}
</style>
