<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { supabase } from '@/lib/supabase'
import type { PricePoint } from '@/lib/types'
import type { MentionWithTime } from '@/lib/signal'
import MentionTip from '@/components/MentionTip.vue'

const props = defineProps<{
  stockId: number
  mentions: MentionWithTime[]
  fromDate?: string | null
  axisStart?: string | null // 與演變圖共用的 x 軸起點
  axisEnd?: string | null // 與演變圖共用的 x 軸終點
}>()

const prices = ref<PricePoint[]>([])
const loading = ref(true)

// 套用時間範圍：只保留 fromDate（含）之後的股價與提及
const vis = computed(() =>
  props.fromDate ? prices.value.filter((p) => p.date >= props.fromDate!) : prices.value,
)
const visMentions = computed(() =>
  props.fromDate
    ? props.mentions.filter((m) => m.published_at >= props.fromDate!)
    : props.mentions,
)

const dirColor: Record<string, string> = { 看多: '#68d391', 看空: '#fc8181', 中性: '#90cdf4' }

const W = 680
const H = 220
const PAD = { top: 16, right: 16, bottom: 30, left: 52 }

async function load() {
  loading.value = true
  const { data } = await supabase
    .from('prices')
    .select('date, close')
    .eq('stock_id', props.stockId)
    .order('date')
  prices.value = (data ?? []) as PricePoint[]
  loading.value = false
}
onMounted(load)
watch(() => props.stockId, load)

const bounds = computed(() => {
  const ps = vis.value
  if (!ps.length) return null
  // x 軸範圍：優先用共用軸（與演變圖對齊），否則用資料範圍
  const tMin = props.axisStart ? Date.parse(props.axisStart) : Date.parse(ps[0].date)
  const tMaxRaw = props.axisEnd ? Date.parse(props.axisEnd) : Date.parse(ps[ps.length - 1].date)
  let pMin = Infinity, pMax = -Infinity
  for (const p of ps) { pMin = Math.min(pMin, p.close); pMax = Math.max(pMax, p.close) }
  const pad = (pMax - pMin) * 0.08 || 1
  return { tMin, tMax: tMaxRaw <= tMin ? tMin + 1 : tMaxRaw, pMin: pMin - pad, pMax: pMax + pad }
})

function sx(t: number): number {
  const b = bounds.value!
  return PAD.left + ((t - b.tMin) / (b.tMax - b.tMin)) * (W - PAD.left - PAD.right)
}
function sy(v: number): number {
  const b = bounds.value!
  return PAD.top + (1 - (v - b.pMin) / (b.pMax - b.pMin)) * (H - PAD.top - PAD.bottom)
}

const linePath = computed(() => {
  if (!bounds.value) return ''
  return vis.value
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${sx(Date.parse(p.date)).toFixed(1)} ${sy(p.close).toFixed(1)}`)
    .join(' ')
})

// 提及點：對齊到該日期(含)之後第一個有股價的點
const markers = computed(() => {
  if (!bounds.value) return []
  return visMentions.value.map((m) => {
    const idx = vis.value.findIndex((p) => p.date >= m.published_at)
    const p = idx >= 0 ? vis.value[idx] : vis.value[vis.value.length - 1]
    if (!p) return null
    return {
      cx: sx(Date.parse(p.date)), cy: sy(p.close),
      color: dirColor[m.direction], hasPos: m.has_position,
      ep: m.episodes?.ep_no, date: m.published_at, daysAgo: m.days_ago,
      dir: m.direction, conf: m.confidence, quote: m.quote, price: p.close,
    }
  }).filter((x): x is NonNullable<typeof x> => x !== null)
})

// hover 狀態
const hovered = ref<number | null>(null)

const yTicks = computed(() => {
  if (!bounds.value) return []
  const { pMin, pMax } = bounds.value
  return [0, 0.5, 1].map((f) => {
    const v = pMin + (pMax - pMin) * f
    return { y: sy(v), label: v >= 1000 ? v.toFixed(0) : v.toFixed(2) }
  })
})

const xTicks = computed(() => {
  if (!bounds.value) return []
  const { tMin, tMax } = bounds.value
  return [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const t = tMin + (tMax - tMin) * f
    const d = new Date(t)
    return { x: sx(t), label: `${d.getMonth() + 1}/${d.getDate()}` }
  })
})
</script>

<template>
  <div class="pc">
    <p v-if="loading" class="pc-msg">股價載入中 …</p>
    <p v-else-if="!prices.length" class="pc-msg">此標的無股價資料</p>
    <p v-else-if="!vis.length" class="pc-msg">此時間範圍內無股價資料</p>
    <div v-else class="pc-chart">
    <svg :viewBox="`0 0 ${W} ${H}`" class="pc-svg">
      <!-- y 軸格線 + 價格 -->
      <g v-for="(tk, i) in yTicks" :key="`y${i}`">
        <line :x1="PAD.left" :x2="W - PAD.right" :y1="tk.y" :y2="tk.y" class="grid" />
        <text :x="PAD.left - 6" :y="tk.y + 3" class="y-label">{{ tk.label }}</text>
      </g>
      <!-- x 軸日期 -->
      <text v-for="(tk, i) in xTicks" :key="`x${i}`" :x="tk.x" :y="H - 10" class="x-label">{{ tk.label }}</text>

      <!-- 價格線 -->
      <path :d="linePath" class="price-line" />

      <!-- 提及點 -->
      <g v-for="(mk, i) in markers" :key="i">
        <circle v-if="mk.hasPos" :cx="mk.cx" :cy="mk.cy" r="7" fill="none" stroke="#f6ad55" stroke-width="2" />
        <circle :cx="mk.cx" :cy="mk.cy" r="4.5" :fill="mk.color" stroke="#0f1117" stroke-width="1"
          :class="{ active: hovered === i }"
          @mouseenter="hovered = i" @mouseleave="hovered = null" />
        <circle :cx="mk.cx" :cy="mk.cy" r="11" fill="transparent"
          @mouseenter="hovered = i" @mouseleave="hovered = null" />
      </g>
    </svg>
    <MentionTip v-if="hovered !== null && markers[hovered]"
      :ep="markers[hovered].ep" :dir="markers[hovered].dir" :color="markers[hovered].color"
      :date="markers[hovered].date" :days-ago="markers[hovered].daysAgo"
      :conf="markers[hovered].conf" :has-pos="markers[hovered].hasPos" :quote="markers[hovered].quote"
      :left-pct="markers[hovered].cx / W * 100" :top-pct="markers[hovered].cy / H * 100"
      :place-below="markers[hovered].cy < H / 2" />
    </div>
    <div v-if="vis.length" class="legend">
      <span><i style="background:#68d391"></i>看多</span>
      <span><i style="background:#90cdf4"></i>中性</span>
      <span><i style="background:#fc8181"></i>看空</span>
      <span><i class="ring"></i>有部位</span>
    </div>
  </div>
</template>

<style scoped>
.pc-msg { color: #718096; font-size: 0.85rem; padding: 1rem 0; }
.pc-chart { position: relative; }
.pc-svg { width: 100%; height: auto; background: #161b27; border-radius: 8px; display: block; }
.pc-svg circle { cursor: pointer; }
.pc-svg circle.active { stroke: #fff; stroke-width: 1.5; }
.grid { stroke: #232b3a; stroke-width: 1; }
.y-label { font-size: 9px; fill: #718096; text-anchor: end; font-variant-numeric: tabular-nums; }
.x-label { font-size: 10px; fill: #a0aec0; text-anchor: middle; font-variant-numeric: tabular-nums; }
.price-line { fill: none; stroke: #63b3ed; stroke-width: 1.5; }
.legend { display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.75rem; color: #a0aec0; }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 0.25rem; vertical-align: middle; }
.legend i.ring { background: transparent; border: 2px solid #f6ad55; }
</style>
