// 按卷懒加载正文（带缓存）
const cache = new Map()

export async function loadVolume(volId) {
  if (cache.has(volId)) return cache.get(volId)
  const data = await fetch(`/data/vol${volId}.json`).then((r) => r.json())
  cache.set(volId, data)
  return data
}
