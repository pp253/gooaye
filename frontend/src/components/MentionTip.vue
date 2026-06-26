<script setup lang="ts">
import { relativeTime } from '@/lib/signal'

defineProps<{
  ep?: number
  dir: string
  color: string
  date: string
  daysAgo: number
  conf: number
  hasPos: boolean
  quote: string
  leftPct: number
  topPct: number
  placeBelow: boolean
}>()
</script>

<template>
  <div
    class="tip"
    :style="{
      left: leftPct + '%',
      top: topPct + '%',
      transform: placeBelow ? 'translate(-50%, 16px)' : 'translate(-50%, calc(-100% - 16px))',
    }"
  >
    <div class="tip-head">
      <span class="tip-ep">EP{{ ep }}</span>
      <span class="tip-dir" :style="{ color }">{{ dir }}</span>
      <span v-if="hasPos" class="tip-pos">🔴 有部位</span>
    </div>
    <div class="tip-meta">
      {{ date }} · {{ relativeTime(daysAgo) }} · 信心 {{ Math.round(conf * 100) }}%
    </div>
    <div class="tip-quote">「{{ quote }}」</div>
  </div>
</template>

<style scoped>
.tip {
  position: absolute;
  background: #0b0e16;
  border: 1px solid #2d3748;
  border-radius: 8px;
  padding: 0.5rem 0.7rem;
  width: 260px;
  pointer-events: none;
  z-index: 5;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
}
.tip-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}
.tip-ep {
  font-weight: 700;
  color: #63b3ed;
  font-size: 0.85rem;
}
.tip-dir {
  font-weight: 700;
  font-size: 0.85rem;
}
.tip-pos {
  font-size: 0.72rem;
  color: #fc8181;
}
.tip-meta {
  font-size: 0.72rem;
  color: #a0aec0;
  margin-bottom: 0.35rem;
  font-variant-numeric: tabular-nums;
}
.tip-quote {
  font-size: 0.78rem;
  color: #cbd5e0;
  line-height: 1.5;
  font-style: italic;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
