import { ref } from 'vue'

// meta.json / dynasties.json 全局只加载一次
const meta = ref(null)
const dynasties = ref(null)
const error = ref(null)
let inflight = null

// 章节/朝代索引：加载完成后构建一次，chapterById/dynastyById 走 O(1) 查找
let chapterIndex = null
let dynastyIndex = null
let allCache = null

function buildIndex() {
  chapterIndex = new Map()
  dynastyIndex = new Map()
  allCache = []
  for (const v of meta.value.volumes) {
    for (const c of v.chapters) {
      chapterIndex.set(c.id, c)
      allCache.push(c)
    }
  }
  for (const d of dynasties.value.dynasties) dynastyIndex.set(d.id, d)
}

export function useMeta() {
  async function loadMeta() {
    if (meta.value) return meta.value
    if (inflight) return inflight
    error.value = null
    // cache: no-cache → 每次加载都向服务器重新校验（ETag 未变返回 304），
    // 解决静态 JSON 文件名固定、部署更新后拿到旧缓存的问题
    inflight = Promise.all([
      fetch('/data/meta.json', { cache: 'no-cache' }).then((r) => {
        if (!r.ok) throw new Error(`meta.json ${r.status}`)
        return r.json()
      }),
      fetch('/data/dynasties.json', { cache: 'no-cache' }).then((r) => {
        if (!r.ok) throw new Error(`dynasties.json ${r.status}`)
        return r.json()
      }),
    ])
      .then(([m, d]) => {
        meta.value = m
        dynasties.value = d
        buildIndex()
        inflight = null
        return m
      })
      .catch((e) => {
        inflight = null
        error.value = e.message || '数据加载失败'
        throw e
      })
    return inflight
  }

  const allChapters = () => allCache || []

  const chapterById = (id) => (chapterIndex ? chapterIndex.get(id) || null : null)

  const dynastyById = (id) => (dynastyIndex ? dynastyIndex.get(id) || null : null)

  return { meta, dynasties, error, loadMeta, allChapters, chapterById, dynastyById }
}
