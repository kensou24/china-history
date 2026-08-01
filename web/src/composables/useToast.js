import { ref } from 'vue'

const toasts = ref([])
let id = 0

export function useToast() {
  function toast(message, duration = 2500) {
    const item = { id: ++id, message }
    toasts.value.push(item)
    setTimeout(() => {
      toasts.value = toasts.value.filter((t) => t.id !== item.id)
    }, duration)
  }

  return { toasts, toast }
}
