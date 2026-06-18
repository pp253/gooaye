import { supabase } from './supabase'
import type { Mention, Stock, StockPerformance } from './types'
import {
  computeSignal,
  daysBetween,
  freshness,
  type MentionWithTime,
  type StockSignal,
} from './signal'

export interface StockRow extends Stock {
  signal: StockSignal
  mentions: MentionWithTime[]
  performance: StockPerformance | null
  recent: number[] // 近約 30 天日收盤（舊→新），給迷你走勢圖用
}

/** 分頁撈出 cutoff 之後的所有股價（PostgREST 單次上限 1000，需分頁）。 */
async function fetchRecentPrices(cutoff: string): Promise<Map<number, number[]>> {
  const map = new Map<number, number[]>()
  const size = 1000
  for (let page = 0; ; page++) {
    const { data } = await supabase
      .from('prices')
      .select('stock_id, date, close')
      .gte('date', cutoff)
      .order('stock_id')
      .order('date')
      .range(page * size, page * size + size - 1)
    const rows = data ?? []
    for (const r of rows) {
      const arr = map.get(r.stock_id) ?? []
      arr.push(r.close as number)
      map.set(r.stock_id, arr)
    }
    if (rows.length < size) break
  }
  return map
}

/**
 * 一次撈出所有 stocks + mentions（含集數日期），在前端組裝出帶時間訊號的個股清單。
 * 回傳 referenceDate（資料集最新一集日期）供顯示。
 */
export async function loadStockSignals(): Promise<{
  stocks: StockRow[]
  referenceDate: string
}> {
  const [{ data: stockData }, { data: mentionData }, { data: perfData }] = await Promise.all([
    supabase.from('stocks').select('*'),
    supabase
      .from('mentions')
      .select('*, episodes(ep_no, title, published_at)')
      .not('stock_id', 'is', null),
    supabase.from('stock_performance').select('*'),
  ])

  const stocks = (stockData ?? []) as Stock[]
  const perfByStock = new Map<number, StockPerformance>(
    ((perfData ?? []) as StockPerformance[]).map((p) => [p.stock_id, p]),
  )

  // 近 ~45 天股價（約 30 個交易日）給迷你走勢圖
  const cutoff = new Date(Date.now() - 45 * 86_400_000).toISOString().slice(0, 10)
  const recentByStock = await fetchRecentPrices(cutoff)
  const rawMentions = (mentionData ?? []) as (Mention & {
    episodes: { ep_no: number; title: string; published_at: string | null }
  })[]

  // 衰減基準：資料集最新一集日期
  const referenceDate =
    rawMentions
      .map((m) => m.episodes?.published_at)
      .filter((d): d is string => !!d)
      .sort()
      .at(-1) ?? new Date().toISOString().slice(0, 10)

  // 依 stock_id 分組，補上時間欄位
  const byStock = new Map<number, MentionWithTime[]>()
  for (const m of rawMentions) {
    const published = m.episodes?.published_at
    if (!published || m.stock_id == null) continue
    const daysAgo = daysBetween(published, referenceDate)
    const withTime: MentionWithTime = {
      ...m,
      published_at: published,
      days_ago: daysAgo,
      freshness: freshness(daysAgo),
    }
    const arr = byStock.get(m.stock_id) ?? []
    arr.push(withTime)
    byStock.set(m.stock_id, arr)
  }

  const rows: StockRow[] = stocks
    .map((s) => {
      const mentions = byStock.get(s.id) ?? []
      if (mentions.length === 0) return null
      return {
        ...s,
        mentions,
        signal: computeSignal(mentions, referenceDate),
        performance: perfByStock.get(s.id) ?? null,
        recent: recentByStock.get(s.id) ?? [],
      }
    })
    .filter((r): r is StockRow => r !== null)

  return { stocks: rows, referenceDate }
}
