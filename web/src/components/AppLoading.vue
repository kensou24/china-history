<template>
  <div class="app-loading" :class="{ inline }">
    <span class="spinner" aria-hidden="true" />
    <span class="text">{{ text || '加载中…' }}</span>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
  inline: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 60px 24px;
  color: var(--text-soft);
  font-size: 14px;
}

.app-loading.inline {
  flex-direction: row;
  padding: 12px 0;
  gap: 10px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

.app-loading.inline .spinner {
  width: 18px;
  height: 18px;
  border-width: 2px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
    border-top-color: var(--border);
    background: conic-gradient(from 0deg, var(--accent), var(--border));
  }
}
</style>
