// 全站通用小工具

// 年份显示：负数为公元前
export const yearLabel = (y) => (y < 0 ? `前${-y}` : `${y}`)

// 动效前判断用户是否偏好减少动态（与 CSS 侧 media query 双保险）
export function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
