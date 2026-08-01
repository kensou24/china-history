// 按卷懒加载正文（带缓存）
const cache = new Map()

export async function loadVolume(volId) {
  if (cache.has(volId)) return cache.get(volId)
  const res = await fetch(`/data/vol${volId}.json`)
  if (!res.ok) throw new Error(`vol${volId}.json ${res.status}`)
  const data = await res.json()
  cache.set(volId, data)
  return data
}
