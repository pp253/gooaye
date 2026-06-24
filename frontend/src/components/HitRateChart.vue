<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { pct } from '@/lib/format'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

export interface HitRow {
  horizon: number
  n: number
  pct_positive?: number
  avg_return?: number
  avg_alpha?: number | null
  beat_bm_rate?: number | null
}

const props = defineProps<{
  hitRate: HitRow[]
}>()

const option = computed(() => {
  const horizons = props.hitRate.map((h) => `${h.horizon} 天`)
  const upRates = props.hitRate.map((h) => +(((h.pct_positive ?? 0) * 100).toFixed(1)))
  const beatRates = props.hitRate.map((h) => +(((h.beat_bm_rate ?? 0) * 100).toFixed(1)))

  return {
    backgroundColor: 'transparent',
    grid: { top: 32, right: 20, bottom: 28, left: 48 },
    legend: {
      top: 4,
      textStyle: { color: '#a0aec0', fontSize: 11 },
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0b0e16',
      borderColor: '#2d3748',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      formatter: (params: { seriesName: string; name: string; value: number; dataIndex: number }[]) => {
        if (!params?.length) return ''
        const i = params[0].dataIndex
        const h = props.hitRate[i]
        const lines = params.map(
          (p) => `<span style="color:#a0aec0">${p.seriesName}</span>: <b>${p.value}%</b>`,
        )
        return [
          `<div style="font-size:11px;color:#718096">${params[0].name}（n=${h?.n ?? '—'}）</div>`,
          ...lines,
          h?.avg_alpha != null
            ? `<div style="color:#718096;font-size:11px;margin-top:3px">平均超額α: ${pct(h.avg_alpha)}</div>`
            : '',
        ].join('<br>')
      },
    },
    xAxis: {
      type: 'category',
      data: horizons,
      axisLine: { lineStyle: { color: '#2d3748' } },
      axisLabel: { color: '#718096', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#718096',
        fontSize: 9,
        formatter: (v: number) => `${v}%`,
      },
      splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } },
    },
    series: [
      {
        name: '上漲比例',
        type: 'bar',
        data: upRates,
        barMaxWidth: 32,
        itemStyle: { color: '#63b3ed', borderRadius: [3, 3, 0, 0] },
        label: {
          show: true,
          position: 'top',
          color: '#63b3ed',
          fontSize: 10,
          formatter: (p: { value: number }) => `${p.value}%`,
        },
      },
      {
        name: '贏基準比例',
        type: 'bar',
        data: beatRates,
        barMaxWidth: 32,
        itemStyle: { color: '#f6ad55', borderRadius: [3, 3, 0, 0] },
        label: {
          show: true,
          position: 'top',
          color: '#f6ad55',
          fontSize: 10,
          formatter: (p: { value: number }) => `${p.value}%`,
        },
      },
    ],
  }
})
</script>

<template>
  <VChart
    v-if="hitRate.some((h) => h.n > 0)"
    class="chart"
    :option="option"
    autoresize
    style="height: 180px"
  />
  <span v-else class="empty">暫無資料</span>
</template>

<style scoped>
.chart {
  width: 100%;
}
.empty {
  color: #4a5568;
  font-size: 0.8rem;
}
</style>
