<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = withDefaults(
  defineProps<{
    to?: string | object
    hoverable?: boolean
  }>(),
  { hoverable: true, to: undefined },
)

const isLink = computed(() => !!props.to)
const componentType = computed(() => (isLink.value ? RouterLink : 'div'))
</script>

<template>
  <component :is="componentType" :to="to" :class="['app-card', { hoverable }]">
    <slot />
  </component>
</template>

<style scoped>
.app-card {
  background: #1a1f2e;
  border: 1px solid #2d3748;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  transition:
    border-color 0.15s,
    background 0.15s,
    transform 0.15s,
    box-shadow 0.15s;
}
.app-card.hoverable:hover {
  border-color: #63b3ed;
  background: #1e2535;
  transform: translateY(-2px);
  box-shadow: 0 10px 24px -12px rgba(99, 179, 237, 0.3);
  cursor: pointer;
}
</style>
