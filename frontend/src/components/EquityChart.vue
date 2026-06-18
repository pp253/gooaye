<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    curve: { date: string; value: number }[]
    width?: number
    height?: number
  }>(),
  { width: 600, height: 120 },
)

const PAD = { top: 8, right: 8, bottom: 20, left: 44 }

const hovered = ref<{ x: number; y: number; date: string; value: number } | null>(null)

const chartW = computed(() => props.width - PAD.left - PAD.right)
const chartH = computed(() => props.height - PAD.top - PAD.bottom)

const minV = computed(() => Math.min(0, ...props.curve.map(p => p.value)))
const maxV = computed(() => Math.max(0, ...props.curve.map(p => p.value)))
const range = computed(() => maxV.value - minV.value || 0.01)

function xPos(i: number) {
  return PAD.left + (i / Math.max(props.curve.length - 1, 1)) * chartW.value
}
function yPos(v: number) {
  return PAD.top + (1 - (v - minV.value) / range.value) * chartH.value
}

const linePath = computed(() => {
  if (props.curve.length < 2) return ''
  return props.curve
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xPos(i).toFixed(1)} ${yPos(p.value).toFixed(1)}`)
    .join(' ')
})

const zeroY = computed(() => yPos(0))

const color = computed(() => {
  const last = props.curve[props.curve.length - 1]?.value ?? 0
  return last >= 0 ? '#68d391' : '#fc8181'
})

// 簡易 Y 軸刻度（3 格）
const yTicks = computed(() => {
  const ticks = [minV.value, minV.value + range.value / 2, maxV.value]
  return ticks.map(v => ({ v, y: yPos(v) }))
})

// 首尾兩個 X 軸日期標籤
const xLabels = computed(() => {
  const c = props.curve
  if (c.length === 0) return []
  return [
    { label: c[0].date.slice(0, 7), x: xPos(0) },
    { label: c[c.length - 1].date.slice(0, 7), x: xPos(c.length - 1) },
  ]
})

function onMouseMove(e: MouseEvent) {
  const svg = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
  const mx = e.clientX - svg.left - PAD.left
  const idx = Math.round((mx / chartW.value) * (props.curve.length - 1))
  const clamped = Math.max(0, Math.min(props.curve.length - 1, idx))
  const pt = props.curve[clamped]
  if (pt) {
    hovered.value = { x: xPos(clamped), y: yPos(pt.value), date: pt.date, value: pt.value }
  }
}
</script>

<template>
  <div class="eq-wrap" v-if="curve.length >= 2">
    <svg
      :viewBox="`0 0 ${width} ${height}`"
      :width="width" :height="height"
      class="eq-svg"
      @mousemove="onMouseMove"
      @mouseleave="hovered = null"
    >
      <!-- Y 軸刻度線 & 標籤 -->
      <g v-for="t in yTicks" :key="t.v">
        <line
          :x1="PAD.left" :x2="PAD.left + chartW"
          :y1="t.y" :y2="t.y"
          stroke="#2d3748" stroke-width="1" stroke-dasharray="3,3"
        />
        <text :x="PAD.left - 4" :y="t.y + 3.5" text-anchor="end" class="tick-label">
          {{ (t.v * 100).toFixed(0) }}%
        </text>
      </g>

      <!-- 0% 基準線 -->
      <line
        :x1="PAD.left" :x2="PAD.left + chartW"
        :y1="zeroY" :y2="zeroY"
        stroke="#4a5568" stroke-width="1"
      />

      <!-- 資金曲線 -->
      <path :d="linePath" :stroke="color" fill="none" stroke-width="1.8"
            stroke-linecap="round" stroke-linejoin="round" />

      <!-- X 軸日期標籤 -->
      <text v-for="xl in xLabels" :key="xl.x" :x="xl.x" :y="height - 4"
            text-anchor="middle" class="tick-label">{{ xl.label }}</text>

      <!-- Hover crosshair -->
      <template v-if="hovered">
        <line :x1="hovered.x" :x2="hovered.x"
              :y1="PAD.top" :y2="PAD.top + chartH"
              stroke="#718096" stroke-width="1" stroke-dasharray="3,3" />
        <circle :cx="hovered.x" :cy="hovered.y" r="3" :fill="color" />
        <!-- Tooltip -->
        <rect
          :x="Math.min(hovered.x + 6, PAD.left + chartW - 90)"
          :y="Math.max(hovered.y - 28, PAD.top)"
          width="84" height="22" rx="4"
          fill="#1a202c" opacity="0.92"
        />
        <text
          :x="Math.min(hovered.x + 48, PAD.left + chartW - 48)"
          :y="Math.max(hovered.y - 13, PAD.top + 14)"
          text-anchor="middle" class="tooltip-text"
        >
          {{ hovered.date }} {{ (hovered.value * 100).toFixed(1) }}%
        </text>
      </template>
    </svg>
  </div>
  <span v-else class="eq-empty">—</span>
</template>

<style scoped>
.eq-wrap { width: 100%; overflow-x: auto; }
.eq-svg { display: block; width: 100%; height: auto; }
.tick-label { font-size: 9px; fill: #718096; font-family: monospace; }
.tooltip-text { font-size: 9px; fill: #e2e8f0; font-family: monospace; }
.eq-empty { color: #4a5568; font-size: 0.8rem; }
</style>
