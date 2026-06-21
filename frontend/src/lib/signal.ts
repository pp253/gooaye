import type { Mention, Direction } from './types'

/** 方向權重：看多 +1、中性 0、看空 -1 */
export const DIRECTION_WEIGHT: Record<Direction, number> = {
  看多: 1,
  中性: 0,
  看空: -1,
}

/** 訊號衰減半衰期（天）。30 天前的觀點權重剩一半。 */
export const HALF_LIFE_DAYS = 30

const MS_PER_DAY = 86_400_000

export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(to) - Date.parse(from)) / MS_PER_DAY)
}

/** 指數衰減係數，0~1。越久遠越接近 0。 */
export function decay(daysAgo: number, halfLife = HALF_LIFE_DAYS): number {
  const h = halfLife > 0 ? halfLife : HALF_LIFE_DAYS
  return Math.pow(0.5, Math.max(0, daysAgo) / h)
}

export type Freshness = 'fresh' | 'aging' | 'stale'

/** 依距今天數分級。 */
export function freshness(daysAgo: number): Freshness {
  if (daysAgo <= 14) return 'fresh'
  if (daysAgo <= 60) return 'aging'
  return 'stale'
}

export const FRESHNESS_META: Record<Freshness, { label: string; color: string; dot: string }> = {
  fresh: { label: '近期', color: '#68d391', dot: '🟢' },
  aging: { label: '漸舊', color: '#f6ad55', dot: '🟡' },
  stale: { label: '過期', color: '#fc8181', dot: '🔴' },
}

/** 相對時間中文描述，例如「3 天前」「2 週前」「2 個月前」。 */
export function relativeTime(daysAgo: number): string {
  if (daysAgo <= 0) return '今天'
  if (daysAgo === 1) return '昨天'
  if (daysAgo < 14) return `${daysAgo} 天前`
  if (daysAgo < 60) return `${Math.round(daysAgo / 7)} 週前`
  if (daysAgo < 365) return `${Math.round(daysAgo / 30)} 個月前`
  return `${(daysAgo / 365).toFixed(1)} 年前`
}

export interface MentionWithTime extends Mention {
  published_at: string
  days_ago: number
  freshness: Freshness
}

export interface StockSignal {
  /** 時間衰減後的綜合分數，正=偏多、負=偏空 */
  score: number
  /** 最近一次提及的方向（=他目前的立場） */
  latest_direction: Direction
  latest_days_ago: number
  latest_ep: number
  latest_freshness: Freshness
  mention_count: number
  has_position_ever: boolean
  /** 最近連續看多次數 */
  bull_streak: number
  /** 首次提及日期（YYYY-MM-DD） */
  first_mention_date: string
  /** 首次提及距基準日天數 */
  first_mention_days_ago: number
}

/**
 * 計算一檔股票的時間加權訊號。
 * @param mentions 該股所有提及（需含 published_at），會在內部依日期排序。
 * @param referenceDate 衰減基準日（通常 = 資料集最新一集日期）
 */
export function computeSignal(
  mentions: MentionWithTime[],
  referenceDate: string,
): StockSignal {
  const sorted = [...mentions].sort(
    (a, b) => Date.parse(b.published_at) - Date.parse(a.published_at),
  )
  const latest = sorted[0]

  let score = 0
  for (const m of sorted) {
    const d = daysBetween(m.published_at, referenceDate)
    score += DIRECTION_WEIGHT[m.direction] * m.confidence * decay(d)
  }

  // 最近連續看多（從最新往回數）
  let bullStreak = 0
  for (const m of sorted) {
    if (m.direction === '看多') bullStreak++
    else break
  }

  const first = sorted[sorted.length - 1]
  const firstDaysAgo = daysBetween(first.published_at, referenceDate)

  return {
    score,
    latest_direction: latest.direction,
    latest_days_ago: latest.days_ago,
    latest_ep: latest.episodes?.ep_no ?? 0,
    latest_freshness: latest.freshness,
    mention_count: sorted.length,
    has_position_ever: sorted.some((m) => m.has_position),
    bull_streak: bullStreak,
    first_mention_date: first.published_at,
    first_mention_days_ago: firstDaysAgo,
  }
}
