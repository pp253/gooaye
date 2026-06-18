import { supabase } from './supabase'
import type { Mention, Stock } from './types'
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
}

/**
 * 一次撈出所有 stocks + mentions（含集數日期），在前端組裝出帶時間訊號的個股清單。
 * 回傳 referenceDate（資料集最新一集日期）供顯示。
 */
export async function loadStockSignals(): Promise<{
  stocks: StockRow[]
  referenceDate: string
}> {
  const [{ data: stockData }, { data: mentionData }] = await Promise.all([
    supabase.from('stocks').select('*'),
    supabase
      .from('mentions')
      .select('*, episodes(ep_no, title, published_at)')
      .not('stock_id', 'is', null),
  ])

  const stocks = (stockData ?? []) as Stock[]
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
      return { ...s, mentions, signal: computeSignal(mentions, referenceDate) }
    })
    .filter((r): r is StockRow => r !== null)

  return { stocks: rows, referenceDate }
}
