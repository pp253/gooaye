<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'

withDefaults(defineProps<{ label?: string; width?: number }>(), { width: 280 })

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function toggle() {
  open.value = !open.value
  if (open.value) {
    // 下一個 tick 後掛上外部點擊監聽，避免本次點擊立即關閉
    setTimeout(() => document.addEventListener('click', onOutside), 0)
  }
}
function onOutside(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) close()
}
function close() {
  open.value = false
  document.removeEventListener('click', onOutside)
}
onBeforeUnmount(() => document.removeEventListener('click', onOutside))
</script>

<template>
  <span ref="root" class="info-tip">
    <button
      type="button"
      class="info-btn"
      :class="{ active: open }"
      :aria-label="label || '說明'"
      :aria-expanded="open"
      @click.stop="toggle"
    >
      ⓘ
    </button>
    <div v-if="open" class="info-pop" :style="{ width: width + 'px' }" @click.stop>
      <div v-if="label" class="info-pop-title">{{ label }}</div>
      <div class="info-pop-body"><slot /></div>
    </div>
  </span>
</template>

<style scoped>
.info-tip { position: relative; display: inline-flex; vertical-align: middle; }
.info-btn {
  background: none; border: none; cursor: pointer; padding: 0 0.15rem;
  color: #718096; font-size: 0.9rem; line-height: 1;
  transition: color 0.15s;
}
.info-btn:hover, .info-btn.active { color: #63b3ed; }
.info-pop {
  position: absolute; top: calc(100% + 6px); left: 0; z-index: 20;
  background: #0b0e16; border: 1px solid #2d3748; border-radius: 8px;
  padding: 0.6rem 0.75rem; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  text-align: left; white-space: normal; cursor: default;
}
.info-pop-title { font-weight: 700; color: #63b3ed; font-size: 0.82rem; margin-bottom: 0.35rem; }
.info-pop-body { font-size: 0.78rem; color: #cbd5e0; line-height: 1.6; font-weight: 400; }
:slotted(b), :slotted(strong) { color: #e2e8f0; }
:slotted(code) {
  background: #1a202c; padding: 0.05rem 0.3rem; border-radius: 4px;
  font-size: 0.74rem; color: #90cdf4;
}
</style>
