<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { pct } from '@/lib/format'
import { ECHARTS_BASE_OPTIONS, CHART_THEME, makeLegend, makeValueYAxis } from '@/lib/chartTheme'
import type { HitRow } from '@/types/backtest'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps<{
  hitRate: HitRow[]
}>()

const option = computed(() => {
  const horizons = props.hitRate.map((h) => `${h.horizon} 天`)
  const upRates = props.hitRate.map((h) => +((h.pct_positive ?? 0) * 100).toFixed(1))
  const beatRates = props.hitRate.map((h) => +((h.beat_bm_rate ?? 0) * 100).toFixed(1))

  return {
    ...ECHARTS_BASE_OPTIONS,
    grid: { ...ECHARTS_BASE_OPTIONS.grid, top: 32 },
    legend: makeLegend(),
    tooltip: {
      ...ECHARTS_BASE_OPTIONS.tooltip,
      trigger: 'axis',
      textStyle: { ...ECHARTS_BASE_OPTIONS.tooltip.textStyle, fontSize: 12 },
      formatter: (
        params: { seriesName: string; name: string; value: number; dataIndex: number }[],
      ) => {
        if (!params?.length) return ''
        const i = params[0].dataIndex
        const h = props.hitRate[i]
        const lines = params.map(
          (p) =>
            `<span style="color:${CHART_THEME.textColorNormal}">${p.seriesName}</span>: <b>${p.value}%</b>`,
        )
        return [
          `<div style="font-size:11px;color:${CHART_THEME.textColorMuted}">${params[0].name}（n=${h?.n ?? '—'}）</div>`,
          ...lines,
          h?.avg_alpha != null
            ? `<div style="color:${CHART_THEME.textColorMuted};font-size:11px;margin-top:3px">平均超額α: ${pct(h.avg_alpha)}</div>`
            : '',
        ].join('<br>')
      },
    },
    xAxis: {
      ...ECHARTS_BASE_OPTIONS.xAxis,
      type: 'category',
      data: horizons,
      axisLabel: {
        ...ECHARTS_BASE_OPTIONS.xAxis.axisLabel,
        fontSize: 11,
      },
    },
    yAxis: makeValueYAxis({
      min: 0,
      max: 100,
      axisLabel: {
        fontSize: 9,
        formatter: (v: number) => `${v}%`,
      },
    }),
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
