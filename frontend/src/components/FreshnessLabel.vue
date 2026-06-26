<script setup lang="ts">
import { computed } from 'vue'
import { freshness, relativeTime, FRESHNESS_META } from '@/lib/signal'

const props = defineProps<{
  daysAgo: number
  ep?: number // 傳入則顯示集數，不傳則隱藏
}>()

const meta = computed(() => FRESHNESS_META[freshness(props.daysAgo)])
</script>

<template>
  <span class="fl-wrap">
    <span class="fl-fresh" :style="{ color: meta.color }">
      {{ meta.dot }} {{ relativeTime(daysAgo) }}
    </span>
    <span v-if="ep != null" class="fl-ep">EP{{ ep }}</span>
  </span>
</template>

<style scoped>
.fl-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.fl-fresh {
  font-size: 0.84rem;
  font-weight: 500;
  white-space: nowrap;
}
.fl-ep {
  font-size: 0.76rem;
  color: #4a5568;
  white-space: nowrap;
}
</style>
