<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MentionWithTime } from '@/lib/signal'
import { DIRECTION_WEIGHT } from '@/lib/signal'
import MentionTip from '@/components/MentionTip.vue'

const props = defineProps<{
  mentions: MentionWithTime[]
  referenceDate: string
  fromDate?: string | null
  axisStart?: string | null // 與股價圖共用的 x 軸起點
  axisEnd?: string | null // 與股價圖共用的 x 軸終點
}>()

const W = 680
const H = 160
const PAD = { top: 18, right: 16, bottom: 42, left: 52 }

const dirColor: Record<string, string> = {
  看多: '#68d391',
  看空: '#fc8181',
  中性: '#90cdf4',
}

// 套用時間範圍後依日期排序（舊→新）
const sorted = computed(() => {
  const ms = props.fromDate
    ? props.mentions.filter((m) => m.published_at >= props.fromDate!)
    : props.mentions
  return [...ms].sort((a, b) => Date.parse(a.published_at) - Date.parse(b.published_at))
})

const span = computed(() => {
  // 優先用共用軸（與股價圖對齊）
  if (props.axisStart && props.axisEnd) {
    const min = Date.parse(props.axisStart)
    const max = Date.parse(props.axisEnd)
    return { min, max: max <= min ? min + 1 : max }
  }
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
    daysAgo: m.days_ago,
    dir: m.direction,
    conf: m.confidence,
    quote: m.quote,
  })),
)

// hover 狀態（顯示日期／集數／方向等詳細資訊）
const hovered = ref<number | null>(null)

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
  <p v-if="!sorted.length" class="traj-empty">此時間範圍內無提及紀錄</p>
  <div v-else class="traj-wrap">
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
      <circle :cx="p.cx" :cy="p.cy" :r="p.r" :fill="p.color"
        :class="{ active: hovered === i }"
        @mouseenter="hovered = i" @mouseleave="hovered = null" />
      <!-- 透明大圈擴大 hover 命中範圍 -->
      <circle :cx="p.cx" :cy="p.cy" r="12" fill="transparent"
        @mouseenter="hovered = i" @mouseleave="hovered = null" />
      <text v-if="showEpLabels" :x="p.cx" :y="baseline + 15" class="ep-label">EP{{ p.ep }}</text>
    </g>
  </svg>

  <!-- hover 提示框 -->
  <MentionTip v-if="hovered !== null"
    :ep="points[hovered].ep" :dir="points[hovered].dir" :color="points[hovered].color"
    :date="points[hovered].date" :days-ago="points[hovered].daysAgo"
    :conf="points[hovered].conf" :has-pos="points[hovered].hasPos" :quote="points[hovered].quote"
    :left-pct="points[hovered].cx / W * 100" :top-pct="points[hovered].cy / H * 100"
    :place-below="points[hovered].cy < H / 2" />
  </div>
</template>

<style scoped>
.traj-wrap { position: relative; }
.traj { width: 100%; height: auto; background: #161b27; border-radius: 8px; display: block; }
.traj-empty { color: #718096; font-size: 0.85rem; padding: 1rem 0; }
.grid { stroke: #2d3748; stroke-width: 1; }
.grid.mid { stroke-dasharray: 3 3; }
.date-grid { stroke: #232b3a; stroke-width: 1; }
.axis-label { font-size: 10px; font-weight: 600; }
.traj-line { fill: none; stroke: #4a5568; stroke-width: 1.5; }
.ep-label { font-size: 9px; fill: #718096; text-anchor: middle; }
.date-label { font-size: 10px; fill: #a0aec0; text-anchor: middle; font-variant-numeric: tabular-nums; }
circle { cursor: pointer; }
circle.active { stroke: #fff; stroke-width: 1.5; }
</style>
