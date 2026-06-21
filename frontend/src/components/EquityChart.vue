<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import VChart from 'vue-echarts'

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
  backgroundColor: 'transparent',
  grid: { top: 8, right: 12, bottom: 22, left: 48 },
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#0b0e16',
    borderColor: '#2d3748',
    textStyle: { color: '#e2e8f0', fontSize: 12 },
    formatter: (params: { axisValueLabel?: string; data?: [string, number] }[]) => {
      const p = params[0]
      if (!p?.data) return ''
      return `${p.data[0]} · ${(p.data[1] * 100).toFixed(1)}%`
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
    axisLabel: { color: '#718096', fontSize: 9, formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
    splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } },
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
        lineStyle: { color: '#4a5568', width: 1 },
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
