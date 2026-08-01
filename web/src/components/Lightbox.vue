<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  imgId: { type: String, default: '' },
  caption: { type: String, default: '' },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])
const currentSrc = ref(props.src)

// 原图加载失败 → 回退缩略图
function onImgError() {
  if (props.imgId) currentSrc.value = `/images/${props.imgId}.webp`
}

watch(
  () => props.src,
  (s) => {
    currentSrc.value = s
  },
)

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="lightbox" @click.self="emit('close')" @keydown="onKey">
        <button class="close-btn" @click="emit('close')">✕</button>
        <img :src="currentSrc" :alt="caption" @error="onImgError" />
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
}

.lightbox img {
  max-width: 92vw;
  max-height: 82vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
}

.lightbox .caption {
  color: #e8e2d4;
  margin-top: 16px;
  font-size: 15px;
}

.lightbox .close-btn {
  position: absolute;
  top: 20px;
  right: 24px;
  font-size: 20px;
  background: transparent;
  border: none;
  color: #e8e2d4;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
