<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  target: { type: [Object, String], default: 'window' },
  threshold: { type: Number, default: 400 },
})

const visible = ref(false)
let el = null

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function check() {
  if (!el) return
  const top = props.target === 'window' ? window.scrollY : el.scrollTop
  visible.value = top > props.threshold
}

function bindTarget() {
  unbindTarget()
  if (props.target === 'window') {
    window.addEventListener('scroll', check, { passive: true })
  } else if (typeof props.target === 'string') {
    el = document.querySelector(props.target)
    el?.addEventListener('scroll', check, { passive: true })
  } else if (props.target?.$el || props.target instanceof Element) {
    el = props.target.$el || props.target
    el?.addEventListener('scroll', check, { passive: true })
  }
  check()
}

function unbindTarget() {
  if (props.target === 'window') {
    window.removeEventListener('scroll', check)
  } else if (el) {
    el.removeEventListener('scroll', check)
    el = null
  }
}

function scrollToTop() {
  if (props.target === 'window') {
    window.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' })
  } else if (el) {
    el.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' })
  }
}

onMounted(bindTarget)
onUnmounted(unbindTarget)

watch(() => props.target, bindTarget, { flush: 'post' })
</script>

<template>
  <Transition name="back-fade">
    <button
      v-show="visible"
      class="back-to-top"
      aria-label="回到顶部"
      title="回到顶部"
      @click="scrollToTop"
    >
      ↑
    </button>
  </Transition>
</template>

<style scoped>
.back-to-top {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 40;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  padding: 0;
  box-shadow: var(--shadow);
}

.back-fade-enter-active,
.back-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.back-fade-enter-from,
.back-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (max-width: 768px) {
  .back-to-top {
    right: 12px;
    bottom: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .back-fade-enter-active,
  .back-fade-leave-active {
    transition: none;
  }
}
</style>
