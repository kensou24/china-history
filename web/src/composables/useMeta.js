import { ref } from 'vue'

// meta.json / dynasties.json 全局只加载一次
const meta = ref(null)
const dynasties = ref(null)

export function useMeta() {
  async function loadMeta() {
    if (meta.value) return meta.value
    const [m, d] = await Promise.all([
      fetch('/data/meta.json').then((r) => r.json()),
      fetch('/data/dynasties.json').then((r) => r.json()),
    ])
    meta.value = m
    dynasties.value = d
    return m
  }

  const allChapters = () =>
    meta.value
      ? meta.value.volumes.flatMap((v) => v.chapters)
      : []

  const chapterById = (id) =>
    allChapters().find((c) => c.id === id) || null

  const dynastyById = (id) =>
    dynasties.value ? dynasties.value.dynasties.find((d) => d.id === id) || null : null

  return { meta, dynasties, loadMeta, allChapters, chapterById, dynastyById }
}
