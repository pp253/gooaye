import { ColorType, type ChartOptions, type DeepPartial } from 'lightweight-charts'

/**
 * Shared styling options for charts (ECharts & Lightweight-Charts)
 * to maintain visual consistency across the application.
 */

export const CHART_THEME = {
  // Base colors matching the dark theme
  bgMain: '#161b27',
  bgTooltip: '#0b0e16',
  borderColor: '#2d3748',
  gridLineColor: '#232b3a',
  textColorMuted: '#718096',
  textColorNormal: '#a0aec0',
  textColorBright: '#e2e8f0',
  crosshairColor: '#4a5568',

  // Directions (matching @/lib/signal colors)
  colorBull: '#68d391',
  colorNeutral: '#90cdf4',
  colorBear: '#fc8181',
  colorWarning: '#f6ad55',
}

// ── Shared ECharts Configurations ───────────────────

export const ECHARTS_BASE_OPTIONS = {
  backgroundColor: 'transparent',
  grid: {
    top: 24,
    right: 20,
    bottom: 28,
    left: 48,
  },
  tooltip: {
    backgroundColor: CHART_THEME.bgTooltip,
    borderColor: CHART_THEME.borderColor,
    borderWidth: 1,
    textStyle: {
      color: CHART_THEME.textColorBright,
      fontSize: 12,
    },
  },
  xAxis: {
    axisLine: {
      lineStyle: { color: CHART_THEME.borderColor },
    },
    axisLabel: {
      color: CHART_THEME.textColorNormal,
      fontSize: 10,
    },
    splitLine: {
      show: true,
      lineStyle: { color: CHART_THEME.gridLineColor },
    },
  },
  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: CHART_THEME.textColorNormal,
      fontSize: 10,
    },
    splitLine: {
      show: true,
      lineStyle: { color: CHART_THEME.borderColor },
    },
  },
}

// ── Shared Lightweight-Charts Configurations ───────────

export const LIGHTWEIGHT_CHARTS_BASE_OPTIONS: DeepPartial<ChartOptions> = {
  layout: {
    background: { type: ColorType.Solid, color: CHART_THEME.bgMain },
    textColor: CHART_THEME.textColorNormal,
    fontSize: 10,
  },
  grid: {
    vertLines: { color: CHART_THEME.gridLineColor },
    horzLines: { color: CHART_THEME.gridLineColor },
  },
  rightPriceScale: {
    borderColor: CHART_THEME.borderColor,
  },
  timeScale: {
    borderColor: CHART_THEME.borderColor,
    timeVisible: false,
  },
  crosshair: {
    vertLine: {
      color: CHART_THEME.crosshairColor,
      width: 1,
      style: 2,
      labelBackgroundColor: '#1a202c',
    },
    horzLine: {
      color: CHART_THEME.crosshairColor,
      width: 1,
      style: 2,
      labelBackgroundColor: '#1a202c',
    },
  },
  autoSize: true,
}
