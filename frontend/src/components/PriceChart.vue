<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { supabase } from '@/lib/supabase'
import type { PricePoint } from '@/lib/types'
import type { MentionWithTime } from '@/lib/signal'

const props = defineProps<{ stockId: number; mentions: MentionWithTime[] }>()

const prices = ref<PricePoint[]>([])
const loading = ref(true)

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
  const ps = prices.value
  if (!ps.length) return null
  const tMin = Date.parse(ps[0].date)
  const tMax = Date.parse(ps[ps.length - 1].date)
  let pMin = Infinity, pMax = -Infinity
  for (const p of ps) { pMin = Math.min(pMin, p.close); pMax = Math.max(pMax, p.close) }
  const pad = (pMax - pMin) * 0.08 || 1
  return { tMin, tMax: tMax === tMin ? tMin + 1 : tMax, pMin: pMin - pad, pMax: pMax + pad }
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
  return prices.value
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${sx(Date.parse(p.date)).toFixed(1)} ${sy(p.close).toFixed(1)}`)
    .join(' ')
})

// 提及點：對齊到該日期(含)之後第一個有股價的點
const markers = computed(() => {
  if (!bounds.value) return []
  return props.mentions.map((m) => {
    const idx = prices.value.findIndex((p) => p.date >= m.published_at)
    const p = idx >= 0 ? prices.value[idx] : prices.value[prices.value.length - 1]
    if (!p) return null
    return {
      cx: sx(Date.parse(p.date)), cy: sy(p.close),
      color: dirColor[m.direction], hasPos: m.has_position,
      ep: m.episodes?.ep_no, date: m.published_at, dir: m.direction, price: p.close,
    }
  }).filter((x): x is NonNullable<typeof x> => x !== null)
})

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
    <svg v-else :viewBox="`0 0 ${W} ${H}`" class="pc-svg">
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
        <circle :cx="mk.cx" :cy="mk.cy" r="4.5" :fill="mk.color" stroke="#0f1117" stroke-width="1">
          <title>EP{{ mk.ep }} · {{ mk.date }} · {{ mk.dir }} · 當時 {{ mk.price }}</title>
        </circle>
      </g>
    </svg>
    <div v-if="prices.length" class="legend">
      <span><i style="background:#68d391"></i>看多</span>
      <span><i style="background:#90cdf4"></i>中性</span>
      <span><i style="background:#fc8181"></i>看空</span>
      <span><i class="ring"></i>有部位</span>
    </div>
  </div>
</template>

<style scoped>
.pc-msg { color: #718096; font-size: 0.85rem; padding: 1rem 0; }
.pc-svg { width: 100%; height: auto; background: #161b27; border-radius: 8px; }
.grid { stroke: #232b3a; stroke-width: 1; }
.y-label { font-size: 9px; fill: #718096; text-anchor: end; font-variant-numeric: tabular-nums; }
.x-label { font-size: 10px; fill: #a0aec0; text-anchor: middle; font-variant-numeric: tabular-nums; }
.price-line { fill: none; stroke: #63b3ed; stroke-width: 1.5; }
.legend { display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.75rem; color: #a0aec0; }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 0.25rem; vertical-align: middle; }
.legend i.ring { background: transparent; border: 2px solid #f6ad55; }
</style>
