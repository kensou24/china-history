import { defineStore } from 'pinia'

const KEY = 'zgts:progress'

// 阅读进度：每章记录阅读百分比（localStorage 持久化）
export const useProgressStore = defineStore('progress', {
  state: () => {
    let saved = {}
    try {
      saved = JSON.parse(localStorage.getItem(KEY) || '{}')
    } catch {
      /* ignore */
    }
    return {
      chapters: saved.chapters || {}, // { chId: 0-100 }
      lastRead: saved.lastRead || null, // 最近阅读章节 id
    }
  },
  getters: {
    finishedCount: (s) => Object.values(s.chapters).filter((v) => v >= 98).length,
  },
  actions: {
    record(chId, percent) {
      const prev = this.chapters[chId] || 0
      const next = Math.max(prev, Math.round(percent))
      this.chapters[chId] = next
      this.lastRead = chId
      this.persist()
      // 本次记录是否让该章首次达到"读完"（≥98）
      return prev < 98 && next >= 98
    },
    persist() {
      localStorage.setItem(KEY, JSON.stringify({
        chapters: this.chapters,
        lastRead: this.lastRead,
      }))
    },
  },
})
