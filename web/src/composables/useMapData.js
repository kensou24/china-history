import { ref } from 'vue'
import { assetUrl } from '@/utils'

// map.json 全局只加载一次（与 useMeta 同模式：模块级缓存 + 并发去重）
const data = ref(null)
const error = ref(null)
let inflight = null

let shapeByDynasty = null // Map<dynId, shape[]>
let dynastyYear = null // Map<dynId, number>

function buildIndex() {
  shapeByDynasty = new Map()
  dynastyYear = new Map()
  for (const s of data.value.shapes) {
    if (!s.dyn) continue
    if (!shapeByDynasty.has(s.dyn)) shapeByDynasty.set(s.dyn, [])
    shapeByDynasty.get(s.dyn).push(s)
  }
  for (const [id, m] of Object.entries(data.value.dynastyMap)) {
    dynastyYear.set(id, m.year)
  }
}

export function useMapData() {
  async function loadMap() {
    if (data.value) return data.value
    if (inflight) return inflight
    error.value = null
    inflight = fetch(assetUrl('/data/map.json'), { cache: 'no-cache' })
      .then((r) => {
        if (!r.ok) throw new Error(`map.json ${r.status}`)
        return r.json()
      })
      .then((d) => {
        data.value = d
        buildIndex()
        inflight = null
        return d
      })
      .catch((e) => {
        inflight = null
        error.value = e.message || '地图数据加载失败'
        throw e
      })
    return inflight
  }

  // 某年活跃政权：区间模型前端过滤（数百条，微秒级）
  const activeShapes = (year) =>
    data.value ? data.value.shapes.filter((s) => s.from <= year && year <= s.to) : []

  const shapesByDynasty = (id) => (shapeByDynasty && shapeByDynasty.get(id)) || []

  const yearOf = (id) => (dynastyYear && dynastyYear.get(id)) ?? null

  return { data, error, loadMap, activeShapes, shapesByDynasty, yearOf }
}
