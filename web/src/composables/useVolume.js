// 按卷懒加载正文（带缓存 + 并发去重）
import { assetUrl } from '@/utils'

const cache = new Map()
const inflight = new Map()

export function loadVolume(volId) {
  if (cache.has(volId)) return Promise.resolve(cache.get(volId))
  if (inflight.has(volId)) return inflight.get(volId)
  // cache: no-cache → 数据更新后强制重新校验（未变则 304，几乎无开销）
  const p = fetch(assetUrl(`/data/vol${volId}.json`), { cache: 'no-cache' })
    .then((res) => {
      if (!res.ok) throw new Error(`vol${volId}.json ${res.status}`)
      return res.json()
    })
    .then((data) => {
      cache.set(volId, data)
      inflight.delete(volId)
      return data
    })
    .catch((e) => {
      inflight.delete(volId)
      throw e
    })
  inflight.set(volId, p)
  return p
}
