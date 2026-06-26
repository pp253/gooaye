import type { Mention, Direction } from './core'

export type Freshness = 'fresh' | 'aging' | 'stale'

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

export interface MarkerInfo {
  ep?: number
  date: string
  daysAgo: number
  dir: Direction
  conf: number
  hasPos: boolean
  quote: string
  color: string
  price?: number
}
