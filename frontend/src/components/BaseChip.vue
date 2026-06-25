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
  line-height: 1.2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s, transform 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.chip:hover:not(:disabled) {
  background: #374151;
}
.chip.active {
  background: linear-gradient(135deg, rgba(99, 179, 237, 0.2), rgba(154, 230, 180, 0.1));
  color: #90cdf4;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(99, 179, 237, 0.35), 0 6px 16px -6px rgba(99, 179, 237, 0.25);
}
.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
