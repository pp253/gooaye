<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ScatterChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  DIRECTION_WEIGHT,
  DIRECTION_COLOR,
  relativeTime,
  filterMentionsByDate,
  buildMarkerInfo,
} from '@/lib/signal'
import type { MentionWithTime, MarkerInfo } from '@/types/signal'
import { ECHARTS_BASE_OPTIONS, makeTimeXAxis, makeValueYAxis } from '@/lib/chartTheme'

use([CanvasRenderer, ScatterChart, LineChart, GridComponent, TooltipComponent])

const props = defineProps<{
  mentions: MentionWithTime[]
  referenceDate: string
  fromDate?: string | null
  axisStart?: string | null // 與股價圖共用的 x 軸起點
  axisEnd?: string | null // 與股價圖共用的 x 軸終點
}>()

// 套用時間範圍後依日期排序（舊→新）
const sorted = computed(() => {
  const ms = filterMentionsByDate(props.mentions, props.fromDate)
  return [...ms].sort((a, b) => Date.parse(a.published_at) - Date.parse(b.published_at))
})

function tooltipHtml(m: MarkerInfo): string {
  const pos = m.hasPos
    ? `<span style="color:#fc8181;font-size:11px;margin-left:6px">🔴 有部位</span>`
    : ''
  return `
    <div style="max-width:260px;white-space:normal">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
        <b style="color:#63b3ed">EP${m.ep}</b>
        <b style="color:${m.color}">${m.dir}</b>${pos}
      </div>
      <div style="font-size:11px;color:#a0aec0;margin-bottom:4px">
        ${m.date} · ${relativeTime(m.daysAgo)} · 信心 ${Math.round(m.conf * 100)}%
      </div>
      <div style="font-size:12px;color:#cbd5e0;font-style:italic;line-height:1.5">「${m.quote}」</div>
    </div>`
}

const option = computed(() => {
  const pts = sorted.value.map((m) => {
    const info = buildMarkerInfo(m)
    return {
      value: [Date.parse(m.published_at), DIRECTION_WEIGHT[m.direction]],
      itemStyle: { color: info.color, borderColor: '#0f1117', borderWidth: 1 },
      _m: info,
    }
  })
  const ringPts = sorted.value
    .filter((m) => m.has_position)
    .map((m) => ({
      value: [Date.parse(m.published_at), DIRECTION_WEIGHT[m.direction]],
      symbolSize: 14 + m.confidence * 12,
    }))
  const linePts = sorted.value.map((m) => [
    Date.parse(m.published_at),
    DIRECTION_WEIGHT[m.direction],
  ])

  return {
    ...ECHARTS_BASE_OPTIONS,
    tooltip: {
      ...ECHARTS_BASE_OPTIONS.tooltip,
      trigger: 'item',
      formatter: (p: { data?: { _m?: MarkerInfo } }) =>
        p.data && p.data._m ? tooltipHtml(p.data._m) : '',
    },
    xAxis: makeTimeXAxis({
      min: props.axisStart ? Date.parse(props.axisStart) : undefined,
      max: props.axisEnd ? Date.parse(props.axisEnd) : Date.parse(props.referenceDate),
      splitLine: { show: true },
      axisLabel: {
        fontSize: 10,
        formatter: (v: number) => {
          const d = new Date(v)
          return `${d.getMonth() + 1}/${d.getDate()}`
        },
      },
    }),
    yAxis: makeValueYAxis({
      min: -1.2,
      max: 1.2,
      interval: 1,
      axisLabel: {
        fontWeight: 600,
        color: (v: number) =>
          v === 1
            ? DIRECTION_COLOR['看多']
            : v === 0
              ? DIRECTION_COLOR['中性']
              : v === -1
                ? DIRECTION_COLOR['看空']
                : '#718096',
        formatter: (v: number) => (v === 1 ? '看多' : v === 0 ? '中性' : v === -1 ? '看空' : ''),
      },
    }),
    series: [
      {
        type: 'line',
        data: linePts,
        showSymbol: false,
        silent: true,
        lineStyle: { color: '#4a5568', width: 1.5 },
        z: 1,
      },
      {
        type: 'scatter',
        data: ringPts,
        symbol: 'circle',
        itemStyle: { color: 'transparent', borderColor: '#f6ad55', borderWidth: 2 },
        silent: true,
        z: 2,
      },
      {
        type: 'scatter',
        data: pts,
        symbolSize: (_: unknown, p: { data: { _m: MarkerInfo } }) => 8 + p.data._m.conf * 12,
        z: 3,
      },
    ],
  }
})
</script>

<template>
  <p v-if="!sorted.length" class="traj-empty">此時間範圍內無提及紀錄</p>
  <VChart v-else class="traj" :option="option" autoresize />
</template>

<style scoped>
.traj {
  width: 100%;
  height: 200px;
  background: #161b27;
  border-radius: 8px;
}
.traj-empty {
  color: #718096;
  font-size: 0.85rem;
  padding: 1rem 0;
}
</style>
