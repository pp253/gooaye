<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  createChart,
  LineSeries,
  createSeriesMarkers,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type Time,
} from 'lightweight-charts'
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

const dirColor: Record<string, string> = { 看多: '#68d391', 看空: '#fc8181', 中性: '#90cdf4' }

// 套用時間範圍：只保留 fromDate（含）之後的股價與提及
const vis = computed(() =>
  props.fromDate ? prices.value.filter((p) => p.date >= props.fromDate!) : prices.value,
)
const visMentions = computed(() =>
  props.fromDate
    ? props.mentions.filter((m) => m.published_at >= props.fromDate!)
    : props.mentions,
)

interface MarkerInfo {
  ep?: number
  date: string
  daysAgo: number
  dir: string
  conf: number
  hasPos: boolean
  quote: string
  color: string
  price: number
}

// 提及點：對齊到該日期(含)之後第一個有股價的點；key = 對齊後的股價日期
const markerByDate = computed<Record<string, MarkerInfo>>(() => {
  const map: Record<string, MarkerInfo> = {}
  for (const m of visMentions.value) {
    const idx = vis.value.findIndex((p) => p.date >= m.published_at)
    const p = idx >= 0 ? vis.value[idx] : vis.value[vis.value.length - 1]
    if (!p) continue
    map[p.date] = {
      ep: m.episodes?.ep_no,
      date: m.published_at,
      daysAgo: m.days_ago,
      dir: m.direction,
      conf: m.confidence,
      hasPos: m.has_position,
      quote: m.quote,
      color: dirColor[m.direction],
      price: p.close,
    }
  }
  return map
})

// ── 圖表生命週期 ─────────────────────────────────────────────
const container = ref<HTMLDivElement | null>(null)
let chart: IChartApi | null = null
let series: ISeriesApi<'Line'> | null = null
let markersApi: ISeriesMarkersPluginApi<Time> | null = null

const hovered = ref<MarkerInfo | null>(null)
const tipPos = ref({ leftPct: 0, topPct: 0, placeBelow: false })

function buildChart() {
  if (!container.value) return
  chart = createChart(container.value, {
    layout: {
      background: { type: ColorType.Solid, color: '#161b27' },
      textColor: '#a0aec0',
      fontSize: 10,
    },
    grid: {
      vertLines: { color: '#232b3a' },
      horzLines: { color: '#232b3a' },
    },
    rightPriceScale: { borderColor: '#2d3748' },
    timeScale: { borderColor: '#2d3748', timeVisible: false },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: '#4a5568', width: 1, style: 2, labelBackgroundColor: '#1a202c' },
      horzLine: { color: '#4a5568', width: 1, style: 2, labelBackgroundColor: '#1a202c' },
    },
    autoSize: true,
  })
  series = chart.addSeries(LineSeries, {
    color: '#63b3ed',
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
  })
  markersApi = createSeriesMarkers(series, [])

  chart.subscribeCrosshairMove((param) => {
    const t = param.time as string | undefined
    const info = t ? markerByDate.value[t] : undefined
    if (!info || !param.point || !container.value || !series) {
      hovered.value = null
      return
    }
    const y = series.priceToCoordinate(info.price)
    if (y == null) {
      hovered.value = null
      return
    }
    const w = container.value.clientWidth
    const h = container.value.clientHeight
    hovered.value = info
    tipPos.value = {
      leftPct: (param.point.x / w) * 100,
      topPct: (y / h) * 100,
      placeBelow: y < h / 2,
    }
  })
}

function applyData() {
  if (!chart || !series || !markersApi) return
  series.setData(vis.value.map((p) => ({ time: p.date as Time, value: p.close })))

  const markers = Object.entries(markerByDate.value)
    .map(([date, info]) => ({
      time: date as Time,
      position: 'inBar' as const,
      color: info.color,
      shape: (info.hasPos ? 'square' : 'circle') as 'square' | 'circle',
      size: 1.4,
    }))
    .sort((a, b) => (a.time < b.time ? -1 : 1))
  markersApi.setMarkers(markers)

  // 套用共用可視範圍（與演變圖大致對齊）；否則自適應
  if (props.axisStart && props.axisEnd) {
    chart.timeScale().setVisibleRange({
      from: props.axisStart as Time,
      to: props.axisEnd as Time,
    })
  } else {
    chart.timeScale().fitContent()
  }
}

async function load() {
  loading.value = true
  const { data } = await supabase
    .from('prices')
    .select('date, close')
    .eq('stock_id', props.stockId)
    .order('date')
  prices.value = (data ?? []) as PricePoint[]
  loading.value = false
  await nextTick()
  if (!chart && container.value) buildChart()
  applyData()
}

onMounted(load)
watch(() => props.stockId, load)
watch([() => props.fromDate, () => props.axisStart, () => props.axisEnd, () => props.mentions], () => {
  if (chart) applyData()
})

onUnmounted(() => {
  chart?.remove()
  chart = null
  series = null
  markersApi = null
})
</script>

<template>
  <div class="pc">
    <p v-if="loading" class="pc-msg">股價載入中 …</p>
    <p v-else-if="!prices.length" class="pc-msg">此標的無股價資料</p>
    <p v-else-if="!vis.length" class="pc-msg">此時間範圍內無股價資料</p>
    <div v-show="!loading && vis.length" class="pc-chart">
      <div ref="container" class="pc-canvas"></div>
      <MentionTip
        v-if="hovered"
        :ep="hovered.ep" :dir="hovered.dir" :color="hovered.color"
        :date="hovered.date" :days-ago="hovered.daysAgo"
        :conf="hovered.conf" :has-pos="hovered.hasPos" :quote="hovered.quote"
        :left-pct="tipPos.leftPct" :top-pct="tipPos.topPct"
        :place-below="tipPos.placeBelow" />
    </div>
    <div v-if="!loading && vis.length" class="legend">
      <span><i style="background:#68d391"></i>看多</span>
      <span><i style="background:#90cdf4"></i>中性</span>
      <span><i style="background:#fc8181"></i>看空</span>
      <span><i class="sq"></i>有部位</span>
    </div>
  </div>
</template>

<style scoped>
.pc-msg { color: #718096; font-size: 0.85rem; padding: 1rem 0; }
.pc-chart { position: relative; }
.pc-canvas { width: 100%; height: 240px; border-radius: 8px; overflow: hidden; }
.legend { display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.75rem; color: #a0aec0; }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 0.25rem; vertical-align: middle; }
.legend i.sq { border-radius: 2px; background: transparent; border: 2px solid #cbd5e0; }
</style>
