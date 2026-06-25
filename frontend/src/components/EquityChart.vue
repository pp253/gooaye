<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { ECHARTS_BASE_OPTIONS, CHART_THEME } from '@/lib/chartTheme'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, MarkLineComponent])

const props = withDefaults(
  defineProps<{
    curve: { date: string; value: number }[]
    width?: number
    height?: number
  }>(),
  { width: 600, height: 120 },
)

const color = computed(() => {
  const last = props.curve[props.curve.length - 1]?.value ?? 0
  return last >= 0 ? '#68d391' : '#fc8181'
})

const option = computed(() => ({
  ...ECHARTS_BASE_OPTIONS,
  grid: { ...ECHARTS_BASE_OPTIONS.grid, top: 8, right: 12, bottom: 22 },
  tooltip: {
    ...ECHARTS_BASE_OPTIONS.tooltip,
    trigger: 'axis',
    textStyle: { ...ECHARTS_BASE_OPTIONS.tooltip.textStyle, fontSize: 12 },
    formatter: (params: { axisValueLabel?: string; data?: [string, number] }[]) => {
      const p = params[0]
      if (!p?.data) return ''
      return `${p.data[0]} · ${(p.data[1] * 100).toFixed(1)}%`
    },
  },
  xAxis: {
    ...ECHARTS_BASE_OPTIONS.xAxis,
    type: 'time',
    axisLabel: {
      ...ECHARTS_BASE_OPTIONS.xAxis.axisLabel,
      color: CHART_THEME.textColorMuted,
      fontSize: 9,
      formatter: (v: number) => {
        const d = new Date(v)
        return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}`
      },
    },
    splitLine: { show: false },
  },
  yAxis: {
    ...ECHARTS_BASE_OPTIONS.yAxis,
    type: 'value',
    axisLabel: { 
      ...ECHARTS_BASE_OPTIONS.yAxis.axisLabel,
      color: CHART_THEME.textColorMuted, 
      fontSize: 9, 
      formatter: (v: number) => `${(v * 100).toFixed(0)}%` 
    },
  },
  series: [
    {
      type: 'line',
      data: props.curve.map((p) => [Date.parse(p.date), p.value]),
      showSymbol: false,
      smooth: false,
      lineStyle: { color: color.value, width: 1.8 },
      areaStyle: { color: color.value, opacity: 0.08 },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: CHART_THEME.crosshairColor, width: 1 },
        label: { show: false },
        data: [{ yAxis: 0 }],
      },
    },
  ],
}))
</script>

<template>
  <VChart
    v-if="curve.length >= 2"
    class="eq"
    :style="{ height: height + 'px' }"
    :option="option"
    autoresize
  />
  <span v-else class="eq-empty">—</span>
</template>

<style scoped>
.eq {
  width: 100%;
}
.eq-empty {
  color: #4a5568;
  font-size: 0.8rem;
}
</style>
