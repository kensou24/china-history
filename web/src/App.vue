<script setup>
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'
import { useToast } from '@/composables/useToast'
import BackToTop from '@/components/BackToTop.vue'

const settings = useSettingsStore()
const progress = useProgressStore()
const { toasts } = useToast()

const themes = [
  { id: 'paper', label: '纸' },
  { id: 'sepia', label: '褐' },
  { id: 'dark', label: '夜' },
]

function setTheme(t, animate = false) {
  settings.setTheme(t)
  // 切换瞬间挂过渡类，全站颜色 300ms 渐变；首次加载与 reduced-motion 不触发
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (animate && !reduce) {
    document.body.classList.add('theme-anim')
    setTimeout(() => document.body.classList.remove('theme-anim'), 350)
  }
  document.body.dataset.theme = t
}

setTheme(settings.theme)
</script>

<template>
  <header class="app-header">
    <router-link to="/" class="brand">
      中国通史<small>五卷本 · 交互式学习</small>
    </router-link>
    <nav class="app-nav">
      <router-link to="/">朝代时间轴</router-link>
      <router-link to="/catalog">全书目录</router-link>
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

  <main class="app-main">
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

  <BackToTop />
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
