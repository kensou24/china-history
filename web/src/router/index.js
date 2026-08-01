import { createRouter, createWebHashHistory } from 'vue-router'

// hash 模式：纯静态部署（GitHub Pages 等）无需服务器重写
// 视图动态导入：按路由分包，首屏只下载当前页的代码
const HomeView = () => import('@/views/HomeView.vue')
const CatalogView = () => import('@/views/CatalogView.vue')
const ReadView = () => import('@/views/ReadView.vue')
const MapView = () => import('@/views/MapView.vue')
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { title: '朝代时间轴' } },
    { path: '/catalog', name: 'catalog', component: CatalogView, meta: { title: '全书目录' } },
    { path: '/read/:id', name: 'read', component: ReadView, meta: { title: '阅读' } },
    { path: '/map', name: 'map', component: MapView, meta: { title: '疆域地图' } },
  ],
  scrollBehavior(to, from, saved) {
    return saved || { top: 0 }
  },
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · 中国通史学习`
    : '中国通史 · 交互式学习'
})

export default router
