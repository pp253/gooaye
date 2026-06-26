import { supabase, fetchAllPaged } from './supabase'
import type { Mention, Stock, StockPerformance } from './types'
import {
  computeSignal,
  daysBetween,
  freshness,
  type MentionWithTime,
  type StockSignal,
} from './signal'
import { formatDateYmd } from './format'

export interface StockRow extends Stock {
  signal: StockSignal
  mentions: MentionWithTime[]
  performance: StockPerformance | null
  recent: number[] // 近約 30 天日收盤（舊→新），給迷你走勢圖用
}

type RawMention = Mention & {
  episodes: { ep_no: number; title: string; published_at: string | null }
}

export function toMentionWithTime(m: RawMention, referenceDate: string): MentionWithTime {
  const published = m.episodes?.published_at ?? formatDateYmd()
  const daysAgo = daysBetween(published, referenceDate)
  return {
    ...m,
    published_at: published,
    days_ago: daysAgo,
    freshness: freshness(daysAgo),
  }
}

/** 依 stock_id 分組 mentions，補上時間欄位（published_at/days_ago/freshness）。 */
function buildMentionsByStock(
  rawMentions: RawMention[],
  referenceDate: string,
): Map<number, MentionWithTime[]> {
  const byStock = new Map<number, MentionWithTime[]>()
  for (const m of rawMentions) {
    if (!m.episodes?.published_at || m.stock_id == null) continue
    const withTime = toMentionWithTime(m, referenceDate)
    const arr = byStock.get(m.stock_id) ?? []
    arr.push(withTime)
    byStock.set(m.stock_id, arr)
  }
  return byStock
}

/** 組裝 StockRow 清單，過濾掉沒有任何 mention 的股票。 */
function buildStockRows(
  stocks: Stock[],
  byStock: Map<number, MentionWithTime[]>,
  perfByStock: Map<number, StockPerformance>,
  referenceDate: string,
): StockRow[] {
  return stocks
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
}

/** 撈出 cutoff 之後的所有股價（PostgREST 單次上限 1000，需分頁）。 */
async function fetchRecentPrices(
  cutoff: string,
  stockIds?: number[],
): Promise<Map<number, number[]>> {
  const rows = await fetchAllPaged<{ stock_id: number; close: number }>((offset, limit) => {
    let query = supabase
      .from('prices')
      .select('stock_id, date, close')
      .gte('date', cutoff)
      .order('stock_id')
      .order('date')
      .range(offset, offset + limit - 1)

    if (stockIds && stockIds.length > 0) {
      query = query.in('stock_id', stockIds)
    }
    return query
  })
  const map = new Map<number, number[]>()
  for (const r of rows) {
    const arr = map.get(r.stock_id) ?? []
    arr.push(r.close)
    map.set(r.stock_id, arr)
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
  const [{ data: stockData }, { data: mentionData }, { data: perfData }, { data: refData }] =
    await Promise.all([
      supabase.from('stocks').select('*').eq('id', stockId).single(),
      supabase
        .from('mentions')
        .select('*, episodes(ep_no, title, published_at)')
        .eq('stock_id', stockId),
      supabase.from('stock_performance').select('*').eq('stock_id', stockId).single(),
      supabase
        .from('episodes')
        .select('published_at')
        .order('published_at', { ascending: false })
        .limit(1),
    ])

  if (!stockData) return null

  const referenceDate = (refData?.[0]?.published_at as string | undefined) ?? formatDateYmd()

  const rawMentions = (mentionData ?? []) as RawMention[]

  const mentions: MentionWithTime[] = rawMentions
    .filter((m) => m.episodes?.published_at)
    .map((m) => toMentionWithTime(m, referenceDate))

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

  const [{ data: stockData }, { data: mentionData }, { data: perfData }, { data: refData }] =
    await Promise.all([
      supabase.from('stocks').select('*'),
      supabase
        .from('mentions')
        .select('*, episodes(ep_no, title, published_at)')
        .not('stock_id', 'is', null),
      supabase.from('stock_performance').select('*'),
      supabase
        .from('episodes')
        .select('published_at')
        .order('published_at', { ascending: false })
        .limit(1),
    ])

  const stocks = (stockData ?? []) as Stock[]
  const perfByStock = new Map<number, StockPerformance>(
    ((perfData ?? []) as StockPerformance[]).map((p) => [p.stock_id, p]),
  )

  const rawMentions = (mentionData ?? []) as RawMention[]

  // 衰減基準：直接從 episodes 表取最新一集日期（避免 mentions 被 PostgREST 截斷導致日期不準）
  const referenceDate =
    (refData?.[0]?.published_at as string | undefined)?.slice(0, 10) ?? formatDateYmd()

  const byStock = buildMentionsByStock(rawMentions, referenceDate)
  const rows = buildStockRows(stocks, byStock, perfByStock, referenceDate)

  _cache = { stocks: rows, referenceDate }
  _cacheAt = Date.now()
  return _cache
}

/**
 * 第二階段：補充各股近 30 天收盤（給 Sparkline 用）。
 * 傳入 rows ref 直接 mutate，讓 UI 漸進更新。
 */
export async function loadSparklines(rows: StockRow[]): Promise<void> {
  if (rows.length === 0) return
  const cutoff = formatDateYmd(new Date(Date.now() - 45 * 86_400_000))
  const stockIds = rows.map((r) => r.id)
  const recentByStock = await fetchRecentPrices(cutoff, stockIds)
  for (const r of rows) {
    r.recent = recentByStock.get(r.id) ?? []
  }
  // 同時更新快取中的 recent 資料，避免覆蓋/損壞完整快取列表
  if (_cache) {
    for (const r of rows) {
      const cached = _cache.stocks.find((s) => s.id === r.id)
      if (cached) {
        cached.recent = r.recent
      }
    }
  }
}

export async function searchStockSignals(q: string): Promise<{
  stocks: StockRow[]
  referenceDate: string
}> {
  const trimmed = q.trim()
  if (!trimmed) {
    return loadStockSignals()
  }

  // Build query for matching stocks
  let stockQuery = supabase.from('stocks').select('*')

  // PostgREST OR query for ticker, name_zh, name_en, and array containment on aliases
  stockQuery = stockQuery.or(
    `ticker.ilike.%${trimmed}%,name_zh.ilike.%${trimmed}%,name_en.ilike.%${trimmed}%,aliases.cs.{"${trimmed}"}`,
  )

  const [{ data: stockData }, { data: refData }] = await Promise.all([
    stockQuery,
    supabase
      .from('episodes')
      .select('published_at')
      .order('published_at', { ascending: false })
      .limit(1),
  ])

  const referenceDate =
    (refData?.[0]?.published_at as string | undefined)?.slice(0, 10) ?? formatDateYmd()

  const stocks = (stockData ?? []) as Stock[]
  if (stocks.length === 0) {
    return { stocks: [], referenceDate }
  }

  const stockIds = stocks.map((s) => s.id)

  const [{ data: mentionData }, { data: perfData }] = await Promise.all([
    supabase
      .from('mentions')
      .select('*, episodes(ep_no, title, published_at)')
      .in('stock_id', stockIds),
    supabase.from('stock_performance').select('*').in('stock_id', stockIds),
  ])

  const perfByStock = new Map<number, StockPerformance>(
    ((perfData ?? []) as StockPerformance[]).map((p) => [p.stock_id, p]),
  )

  const rawMentions = (mentionData ?? []) as RawMention[]

  const byStock = buildMentionsByStock(rawMentions, referenceDate)
  const rows = buildStockRows(stocks, byStock, perfByStock, referenceDate)

  return { stocks: rows, referenceDate }
}
