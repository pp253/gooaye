<script setup lang="ts">
import { computed } from 'vue'
import type { MentionWithTime } from '@/lib/signal'
import { DIRECTION_WEIGHT } from '@/lib/signal'

const props = defineProps<{ mentions: MentionWithTime[]; referenceDate: string }>()

const W = 680
const H = 210
const PAD = { top: 24, right: 16, bottom: 48, left: 40 }

const dirColor: Record<string, string> = {
  看多: '#68d391',
  看空: '#fc8181',
  中性: '#90cdf4',
}

// 依日期排序（舊→新）
const sorted = computed(() =>
  [...props.mentions].sort((a, b) => Date.parse(a.published_at) - Date.parse(b.published_at)),
)

const span = computed(() => {
  const times = sorted.value.map((m) => Date.parse(m.published_at))
  const min = Math.min(...times)
  const max = Math.max(Date.parse(props.referenceDate), ...times)
  return { min, max: max === min ? min + 1 : max }
})

function x(published: string): number {
  const { min, max } = span.value
  const t = Date.parse(published)
  return PAD.left + ((t - min) / (max - min)) * (W - PAD.left - PAD.right)
}
// y: 看多上、看空下
function y(dir: string): number {
  const w = DIRECTION_WEIGHT[dir as keyof typeof DIRECTION_WEIGHT] // -1..1
  const mid = (H - PAD.top - PAD.bottom) / 2 + PAD.top
  return mid - w * (mid - PAD.top)
}

const baseline = H - PAD.bottom

// 點多時隱藏每點 EP 標籤，避免重疊（hover 仍可看完整資訊）
const showEpLabels = computed(() => sorted.value.length <= 14)

const points = computed(() =>
  sorted.value.map((m) => ({
    cx: x(m.published_at),
    cy: y(m.direction),
    r: 4 + m.confidence * 6,
    color: dirColor[m.direction],
    hasPos: m.has_position,
    ep: m.episodes?.ep_no,
    date: m.published_at,
    dir: m.direction,
    conf: m.confidence,
  })),
)

const linePath = computed(() =>
  points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.cx} ${p.cy}`).join(' '),
)

// 底部日期刻度：在時間軸上均勻取 5 個點，標出真實日期
const dateTicks = computed(() => {
  const { min, max } = span.value
  const n = 5
  const ticks: { x: number; label: string }[] = []
  let prevYear = 0
  for (let i = 0; i < n; i++) {
    const t = min + ((max - min) * i) / (n - 1)
    const d = new Date(t)
    const yr = d.getFullYear()
    const md = `${d.getMonth() + 1}/${d.getDate()}`
    // 第一個刻度、或跨年時，標出年份
    const label = i === 0 || yr !== prevYear ? `${yr}/${md}` : md
    prevYear = yr
    ticks.push({
      x: PAD.left + (i / (n - 1)) * (W - PAD.left - PAD.right),
      label,
    })
  }
  return ticks
})

const midY = (H - PAD.top - PAD.bottom) / 2 + PAD.top
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" class="traj">
    <!-- 方向區帶 -->
    <line :x1="PAD.left" :x2="W - PAD.right" :y1="PAD.top" :y2="PAD.top" class="grid" />
    <line :x1="PAD.left" :x2="W - PAD.right" :y1="midY" :y2="midY" class="grid mid" />
    <line :x1="PAD.left" :x2="W - PAD.right" :y1="baseline" :y2="baseline" class="grid" />
    <text :x="4" :y="PAD.top + 4" class="axis-label" fill="#68d391">看多</text>
    <text :x="4" :y="midY + 4" class="axis-label" fill="#90cdf4">中性</text>
    <text :x="4" :y="baseline + 4" class="axis-label" fill="#fc8181">看空</text>

    <!-- 日期刻度：淡色直格線 + 真實日期 -->
    <g v-for="(tk, i) in dateTicks" :key="`t${i}`">
      <line :x1="tk.x" :x2="tk.x" :y1="PAD.top" :y2="baseline" class="date-grid" />
      <text :x="tk.x" :y="baseline + 32" class="date-label">{{ tk.label }}</text>
    </g>

    <!-- 連線 -->
    <path :d="linePath" class="traj-line" />

    <!-- 點 -->
    <g v-for="(p, i) in points" :key="i">
      <circle v-if="p.hasPos" :cx="p.cx" :cy="p.cy" :r="p.r + 4" fill="none" stroke="#f6ad55" stroke-width="2" />
      <circle :cx="p.cx" :cy="p.cy" :r="p.r" :fill="p.color">
        <title>EP{{ p.ep }} · {{ p.date }} · {{ p.dir }} · 信心 {{ Math.round(p.conf * 100) }}%{{ p.hasPos ? ' · 有部位' : '' }}</title>
      </circle>
      <text v-if="showEpLabels" :x="p.cx" :y="baseline + 15" class="ep-label">EP{{ p.ep }}</text>
    </g>
  </svg>
</template>

<style scoped>
.traj { width: 100%; height: auto; background: #161b27; border-radius: 8px; }
.grid { stroke: #2d3748; stroke-width: 1; }
.grid.mid { stroke-dasharray: 3 3; }
.date-grid { stroke: #232b3a; stroke-width: 1; }
.axis-label { font-size: 10px; font-weight: 600; }
.traj-line { fill: none; stroke: #4a5568; stroke-width: 1.5; }
.ep-label { font-size: 9px; fill: #718096; text-anchor: middle; }
.date-label { font-size: 10px; fill: #a0aec0; text-anchor: middle; font-variant-numeric: tabular-nums; }
</style>
