<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

export interface NavSeries {
  id: string
  label: string
  color: string
  data: { date: string; value: number }[]
}

const props = withDefaults(
  defineProps<{
    series: NavSeries[]
    height?: number
  }>(),
  { height: 200 },
)

const option = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 28, right: 16, bottom: 28, left: 52 },
  legend: {
    top: 4,
    right: 0,
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
    formatter: (params: { seriesName: string; data: [number, number]; marker: string }[]) => {
      if (!params?.length) return ''
      const date = new Date(params[0].data[0]).toISOString().slice(0, 10)
      // 用 echarts 內建 marker（顏色即系列實際顏色），確保與線、legend 一致
      const lines = params.map(
        (p) => `${p.marker}${p.seriesName}: $${p.data[1].toFixed(3)}`,
      )
      return `<div style="font-size:11px;color:#718096">${date}</div>${lines.join('<br>')}`
    },
  },
  xAxis: {
    type: 'time',
    axisLine: { lineStyle: { color: '#2d3748' } },
    axisLabel: {
      color: '#718096',
      fontSize: 9,
      formatter: (v: number) => {
        const d = new Date(v)
        return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}`
      },
    },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: '#718096',
      fontSize: 9,
      formatter: (v: number) => `$${v.toFixed(2)}`,
    },
    splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } },
  },
  series: props.series.map((s) => ({
    name: s.label,
    type: 'line',
    // color 同時驅動線、legend 圖示與 tooltip marker，避免三者不一致
    color: s.color,
    data: s.data.map((p) => [Date.parse(p.date), p.value]),
    showSymbol: false,
    smooth: false,
    itemStyle: { color: s.color },
    lineStyle: { color: s.color, width: 2 },
    areaStyle: { color: s.color, opacity: 0.04 },
    markLine:
      s.id === props.series[0]?.id
        ? {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#4a5568', width: 1, type: 'dashed' },
            label: { show: true, formatter: '$1.00', color: '#4a5568', fontSize: 9 },
            data: [{ yAxis: 1.0 }],
          }
        : undefined,
  })),
}))
</script>

<template>
  <VChart
    v-if="series.some((s) => s.data.length >= 2)"
    class="chart"
    :style="{ height: height + 'px' }"
    :option="option"
    autoresize
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
