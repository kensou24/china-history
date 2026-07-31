import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import CatalogView from '@/views/CatalogView.vue'
import ReadView from '@/views/ReadView.vue'

// hash 模式：纯静态部署（GitHub Pages 等）无需服务器重写
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { title: '朝代时间轴' } },
    { path: '/catalog', name: 'catalog', component: CatalogView, meta: { title: '全书目录' } },
    { path: '/read/:id', name: 'read', component: ReadView, meta: { title: '阅读' } },
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
