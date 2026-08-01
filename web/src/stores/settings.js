import { defineStore } from 'pinia'

const KEY = 'zgts:settings'

// 阅读偏好：字号 / 行距 / 主题（localStorage 持久化）
export const useSettingsStore = defineStore('settings', {
  state: () => {
    let saved = {}
    try {
      saved = JSON.parse(localStorage.getItem(KEY) || '{}')
    } catch {
      /* ignore */
    }
    return {
      fontSize: saved.fontSize ?? 18, // px
      lineHeight: saved.lineHeight ?? 1.9,
      theme: saved.theme ?? 'paper', // paper | dark | sepia
      railCollapsed: saved.railCollapsed ?? false, // 阅读页朝代竖轨是否收起
    }
  },
  actions: {
    setFontSize(v) {
      this.fontSize = Math.min(28, Math.max(14, v))
      this.persist()
    },
    setLineHeight(v) {
      this.lineHeight = Math.min(2.6, Math.max(1.4, v))
      this.persist()
    },
    setTheme(t) {
      this.theme = t
      this.persist()
    },
    toggleRailCollapsed() {
      this.railCollapsed = !this.railCollapsed
      this.persist()
    },
    persist() {
      localStorage.setItem(KEY, JSON.stringify({
        fontSize: this.fontSize,
        lineHeight: this.lineHeight,
        theme: this.theme,
        railCollapsed: this.railCollapsed,
      }))
    },
  },
})
