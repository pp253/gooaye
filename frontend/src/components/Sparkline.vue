<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ values: number[]; width?: number; height?: number }>(), {
  width: 96,
  height: 28,
})

const PAD = 2

const path = computed(() => {
  const vs = props.values
  if (vs.length < 2) return ''
  const min = Math.min(...vs)
  const max = Math.max(...vs)
  const range = max - min || 1
  const w = props.width - PAD * 2
  const h = props.height - PAD * 2
  return vs
    .map((v, i) => {
      const x = PAD + (i / (vs.length - 1)) * w
      const y = PAD + (1 - (v - min) / range) * h
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
})

// 期間漲跌決定顏色（近端 vs 遠端）
const up = computed(() => {
  const vs = props.values
  return vs.length >= 2 && vs[vs.length - 1] >= vs[0]
})
const color = computed(() => (up.value ? '#68d391' : '#fc8181'))
</script>

<template>
  <svg
    v-if="path"
    :viewBox="`0 0 ${width} ${height}`"
    :width="width"
    :height="height"
    class="spark"
  >
    <path
      :d="path"
      :stroke="color"
      fill="none"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
  <span v-else class="spark-empty">—</span>
</template>

<style scoped>
.spark {
  display: block;
}
.spark-empty {
  color: #4a5568;
  font-size: 0.8rem;
}
</style>
