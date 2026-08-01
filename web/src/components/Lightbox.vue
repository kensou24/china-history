<script setup>
import { nextTick, ref, watch } from 'vue'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  src: { type: String, required: true },
  imgId: { type: String, default: '' },
  caption: { type: String, default: '' },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])
const { toast } = useToast()
const currentSrc = ref(props.src)
const loaded = ref(false)
const overlayRef = ref(null)
let lastFocused = null

// 原图加载失败 → 回退缩略图
function onImgError() {
  if (props.imgId) {
    currentSrc.value = `/images/${props.imgId}.webp`
    toast('原图加载失败，已显示缩略图')
  }
}

watch(
  () => props.src,
  (s) => {
    currentSrc.value = s
    loaded.value = false
  },
)

function close() {
  emit('close')
}

function onKey(e) {
  if (e.key === 'Escape') close()
}

watch(
  () => props.visible,
  (v) => {
    if (v) {
      lastFocused = document.activeElement
      document.body.style.overflow = 'hidden'
      nextTick(() => {
        overlayRef.value?.focus()
      })
      window.addEventListener('keydown', onKey)
    } else {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
      loaded.value = false
      if (lastFocused && typeof lastFocused.focus === 'function') {
        nextTick(() => lastFocused.focus())
      }
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        ref="overlayRef"
        class="lightbox"
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        aria-label="图片预览"
        @click.self="close"
      >
        <button class="close-btn" @click="close" aria-label="关闭预览">✕</button>
        <div class="img-wrap">
          <div v-if="!loaded" class="img-spinner" aria-hidden="true" />
          <img
            :src="currentSrc"
            :alt="caption"
            :class="{ loaded }"
            @error="onImgError"
            @load="loaded = true"
          />
        </div>
        <p v-if="caption" class="caption">{{ caption }}</p>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(10, 8, 4, 0.92);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  cursor: zoom-out;
  outline: none;
}

.lightbox .close-btn {
  position: absolute;
  top: 20px;
  right: 24px;
  font-size: 20px;
  background: transparent;
  border: none;
  color: #e8e2d4;
  cursor: pointer;
}

@media (hover: hover) {
  .lightbox .close-btn:hover {
    color: #fff;
  }
}

.img-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 120px;
  min-height: 120px;
}

.img-spinner {
  position: absolute;
  width: 32px;
  height: 32px;
  border: 3px solid rgba(232, 226, 212, 0.2);
  border-top-color: #e8e2d4;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

.lightbox img {
  max-width: 92vw;
  max-height: 82vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  opacity: 0;
  transform: scale(0.94);
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.lightbox img.loaded {
  opacity: 1;
  transform: scale(1);
}

.lightbox .caption {
  color: #e8e2d4;
  margin-top: 16px;
  font-size: 15px;
  text-align: center;
  max-width: 92vw;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .img-spinner {
    animation: none;
  }

  .lightbox img {
    transition: none;
    opacity: 1;
    transform: none;
  }

  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
