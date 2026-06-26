import { daysBetween } from './signal'
import type { Strategy, Scope, TradeRow } from '@/types/backtest'

export function aggregate(trades: TradeRow[], scope: string): Scope {
  const sel = scope === 'ALL' ? trades : trades.filter((t) => t.market === scope)
  if (!sel.length) return { scope, n_trades: 0 }
  const rets = sel.map((t) => t.ret)
  const withBm = sel.filter((t) => t.bm_ret !== null && t.bm_ret !== undefined)
  const alphas = withBm.map((t) => t.ret - t.bm_ret!)
  const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length
  return {
    scope,
    n_trades: sel.length,
    win_rate: rets.filter((r) => r > 0).length / rets.length,
    avg_return: mean(rets),
    avg_bm_return: withBm.length ? mean(withBm.map((t) => t.bm_ret!)) : null,
    avg_alpha: alphas.length ? mean(alphas) : null,
    beat_bm_rate: alphas.length ? alphas.filter((a) => a > 0).length / alphas.length : null,
  }
}

export function slicedDaily(st: Strategy, scope: string, fromDate: string, toDate: string) {
  const d = st.daily?.[scope]
  if (!d || d.dates.length < 2) return { curve: [], bmCurve: [] }
  const idx: number[] = []
  for (let i = 0; i < d.dates.length; i++) {
    if (d.dates[i] >= fromDate && d.dates[i] <= toDate) idx.push(i)
  }
  if (idx.length < 2) return { curve: [], bmCurve: [] }
  const base = d.nav[idx[0]] || 1
  const bmBase = d.bm_nav ? d.bm_nav[idx[0]] || 1 : null
  const curve = idx.map((i) => ({ date: d.dates[i], value: +(d.nav[i] / base).toFixed(4) }))
  const bmCurve =
    d.bm_nav && bmBase
      ? idx.map((i) => ({ date: d.dates[i], value: +(d.bm_nav![i] / bmBase).toFixed(4) }))
      : []
  return { curve, bmCurve }
}

export function computeMdd(curve: { date: string; value: number }[]) {
  let peak = -Infinity
  let mdd = 0.0
  for (const p of curve) {
    if (p.value > peak) peak = p.value
    const dd = p.value / peak - 1.0
    if (dd < mdd) mdd = dd
  }
  return mdd
}

export function computeSharpe(curve: { date: string; value: number }[]) {
  if (curve.length < 3) return null
  const r: number[] = []
  for (let i = 1; i < curve.length; i++) {
    if (curve[i - 1].value > 0) r.push(curve[i].value / curve[i - 1].value - 1)
  }
  if (r.length < 2) return null
  const mean = r.reduce((a, b) => a + b, 0) / r.length
  const variance = r.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (r.length - 1)
  const sd = Math.sqrt(variance)
  if (sd === 0) return null
  const days = daysBetween(curve[0].date, curve[curve.length - 1].date)
  const years = days / 365.25
  const periodsPerYear = years > 0 ? r.length / years : 252
  return (mean / sd) * Math.sqrt(periodsPerYear)
}

export function computeCagr(curve: { date: string; value: number }[]) {
  if (curve.length < 2) return null
  const days = daysBetween(curve[0].date, curve[curve.length - 1].date)
  if (days <= 0 || curve[0].value <= 0) return null
  const years = days / 365.25
  return Math.pow(curve[curve.length - 1].value / curve[0].value, 1 / years) - 1
}

export function computeStreaks(trades: TradeRow[]) {
  const sorted = [...trades].sort((a, b) => a.exit_date.localeCompare(b.exit_date))
  let winStreak = 0
  let loseStreak = 0
  let maxWin = 0
  let maxLose = 0
  for (const t of sorted) {
    if (t.ret > 0) {
      winStreak++
      loseStreak = 0
      if (winStreak > maxWin) maxWin = winStreak
    } else if (t.ret < 0) {
      loseStreak++
      winStreak = 0
      if (loseStreak > maxLose) maxLose = loseStreak
    } else {
      winStreak = 0
      loseStreak = 0
    }
  }
  return { maxWin, maxLose }
}

export function getYearlyStats(trades: TradeRow[]) {
  const byYear: Record<string, TradeRow[]> = {}
  for (const t of trades) {
    if (!t.exit_date) continue
    const year = t.exit_date.split('-')[0]
    if (!byYear[year]) byYear[year] = []
    byYear[year].push(t)
  }
  return Object.keys(byYear)
    .sort()
    .map((year) => ({
      year,
      ...aggregate(byYear[year], 'ALL'),
    }))
}
