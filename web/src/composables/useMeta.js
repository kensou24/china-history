import { ref } from 'vue'

// meta.json / dynasties.json 全局只加载一次
const meta = ref(null)
const dynasties = ref(null)
const error = ref(null)

export function useMeta() {
  async function loadMeta() {
    if (meta.value) return meta.value
    error.value = null
    try {
      const [m, d] = await Promise.all([
        fetch('/data/meta.json').then((r) => {
          if (!r.ok) throw new Error(`meta.json ${r.status}`)
          return r.json()
        }),
        fetch('/data/dynasties.json').then((r) => {
          if (!r.ok) throw new Error(`dynasties.json ${r.status}`)
          return r.json()
        }),
      ])
      meta.value = m
      dynasties.value = d
      return m
    } catch (e) {
      error.value = e.message || '数据加载失败'
      throw e
    }
  }

  const allChapters = () =>
    meta.value
      ? meta.value.volumes.flatMap((v) => v.chapters)
      : []

  const chapterById = (id) =>
    allChapters().find((c) => c.id === id) || null

  const dynastyById = (id) =>
    dynasties.value ? dynasties.value.dynasties.find((d) => d.id === id) || null : null

  return { meta, dynasties, error, loadMeta, allChapters, chapterById, dynastyById }
}
