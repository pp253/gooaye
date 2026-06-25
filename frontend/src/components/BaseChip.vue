<script setup lang="ts">
defineProps<{
  active?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <button
    :class="['chip', { active }]"
    :disabled="disabled"
    type="button"
  >
    <slot />
  </button>
</template>

<style scoped>
.chip {
  background: #2d3748;
  color: #a0aec0;
  border: none;
  border-radius: 6px;
  padding: 0.3rem 0.7rem;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.15s, color 0.15s, transform 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.chip:hover:not(:disabled) {
  background: #374151;
}
.chip.active {
  background: linear-gradient(135deg, #63b3ed, #4299e1);
  color: #1a1f2e;
  font-weight: 600;
  box-shadow: 0 4px 12px -4px rgba(99, 179, 237, 0.5);
}
.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
