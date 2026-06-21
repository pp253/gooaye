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
 * 個股詳情頁專用：只撈單一股票的資料，避免載入全部個股。
 * 並行抓：股票基本資料、該股提及、該股績效、全域 referenceDate。
 */
export async function loadSingleStockDetail(stockId: number): Promise<{
  stock: StockRow
  referenceDate: string
} | null> {
  const [
    { data: stockData },
    { data: mentionData },
    { data: perfData },
    { data: refData },
  ] = await Promise.all([
    supabase.from('stocks').select('*').eq('id', stockId).single(),
    supabase
      .from('mentions')
      .select('*, episodes(ep_no, title, published_at)')
      .eq('stock_id', stockId),
    supabase.from('stock_performance').select('*').eq('stock_id', stockId).single(),
    supabase.from('episodes').select('published_at').order('published_at', { ascending: false }).limit(1),
  ])

  if (!stockData) return null

  const referenceDate =
    (refData?.[0]?.published_at as string | undefined) ??
    new Date().toISOString().slice(0, 10)

  const rawMentions = (mentionData ?? []) as (Mention & {
    episodes: { ep_no: number; title: string; published_at: string | null }
  })[]

  const mentions: MentionWithTime[] = rawMentions
    .filter((m) => m.episodes?.published_at)
    .map((m) => {
      const published = m.episodes.published_at as string
      const daysAgo = daysBetween(published, referenceDate)
      return { ...m, published_at: published, days_ago: daysAgo, freshness: freshness(daysAgo) }
    })

  if (mentions.length === 0) return null

  const stock = stockData as Stock
  return {
    stock: {
      ...stock,
      mentions,
      signal: computeSignal(mentions, referenceDate),
      performance: (perfData as StockPerformance | null) ?? null,
      recent: [],
    },
    referenceDate,
  }
}


// ── 模組層快取（5 分鐘 TTL，頁面間切換時避免重新抓取） ─────────────
let _cache: { stocks: StockRow[]; referenceDate: string } | null = null
let _cacheAt = 0
const CACHE_TTL_MS = 5 * 60 * 1000

/** 清除快取（資料更新後可強制重刷） */
export function invalidateStockCache() {
  _cache = null
  _cacheAt = 0
}

export async function loadStockSignals(): Promise<{
  stocks: StockRow[]
  referenceDate: string
}> {
  if (_cache && Date.now() - _cacheAt < CACHE_TTL_MS) return _cache

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
        recent: [] as number[], // sparkline 由 loadSparklines() 非同步補入
      }
    })
    .filter((r): r is StockRow => r !== null)

  _cache = { stocks: rows, referenceDate }
  _cacheAt = Date.now()
  return _cache
}

/**
 * 第二階段：補充各股近 30 天收盤（給 Sparkline 用）。
 * 傳入 rows ref 直接 mutate，讓 UI 漸進更新。
 */
export async function loadSparklines(rows: StockRow[]): Promise<void> {
  const cutoff = new Date(Date.now() - 45 * 86_400_000).toISOString().slice(0, 10)
  const recentByStock = await fetchRecentPrices(cutoff)
  for (const r of rows) {
    r.recent = recentByStock.get(r.id) ?? []
  }
  // 同時更新快取
  if (_cache) _cache.stocks = rows
}
