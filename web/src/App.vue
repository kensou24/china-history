<script setup>
import { useSettingsStore } from '@/stores/settings'
import { useProgressStore } from '@/stores/progress'

const settings = useSettingsStore()
const progress = useProgressStore()

const themes = [
  { id: 'paper', label: '纸' },
  { id: 'sepia', label: '褐' },
  { id: 'dark', label: '夜' },
]

function setTheme(t) {
  settings.setTheme(t)
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
    <div class="theme-switch" title="阅读主题">
      <button
        v-for="t in themes"
        :key="t.id"
        :class="{ active: settings.theme === t.id }"
        @click="setTheme(t.id)"
      >
        {{ t.label }}
      </button>
    </div>
  </header>

  <main class="app-main">
    <router-view />
  </main>
</template>
