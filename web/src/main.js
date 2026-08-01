import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { useToast } from '@/composables/useToast'

const app = createApp(App)
app.use(createPinia())
app.use(router)

app.config.errorHandler = (err) => {
  console.error(err)
  const { toast } = useToast()
  toast('页面出现异常，请刷新重试')
}

window.addEventListener('unhandledrejection', (e) => {
  console.error(e.reason)
  const { toast } = useToast()
  toast('请求失败，请检查网络后重试')
})

app.mount('#app')
