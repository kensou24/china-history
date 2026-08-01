// 全站通用小工具

// 年份显示：负数为公元前
export const yearLabel = (y) => (y < 0 ? `前${-y}` : `${y}`)

// 动效前判断用户是否偏好减少动态（与 CSS 侧 media query 双保险）
export function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

// 静态资源路径：拼接 Vite base（部署到子路径如 /china-history/ 时自动带前缀）
export const assetUrl = (p) => import.meta.env.BASE_URL + p.replace(/^\//, '')
