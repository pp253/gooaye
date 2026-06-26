<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ score: number }>()

const color = computed(() => (props.score >= 0 ? '#68d391' : '#fc8181'))
const barPct = computed(() => Math.min(100, Math.abs(props.score) * 40) + '%')
const label = computed(() => (props.score >= 0 ? '+' : '') + props.score.toFixed(2))
</script>

<template>
  <div class="score-cell">
    <div class="score-bar-track">
      <div class="score-bar" :style="{ width: barPct, background: color }" />
    </div>
    <span class="score-num" :style="{ color }">{{ label }}</span>
  </div>
</template>

<style scoped>
.score-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.score-bar-track {
  width: 70px;
  height: 6px;
  background: #2d3748;
  border-radius: 3px;
  overflow: hidden;
}
.score-bar {
  height: 100%;
  border-radius: 3px;
}
.score-num {
  font-variant-numeric: tabular-nums;
  font-size: 0.82rem;
  font-weight: 600;
  min-width: 3rem;
}
</style>
