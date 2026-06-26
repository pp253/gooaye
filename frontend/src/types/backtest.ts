export interface TradeRow {
  ticker: string
  name_zh: string
  market: string
  ep_date: string
  entry_date: string
  exit_date: string
  ret: number
  bm_ret: number | null
  alpha: number | null
}

export interface Scope {
  scope: string
  n_trades: number
  win_rate?: number
  avg_return?: number
  avg_bm_return?: number | null
  avg_alpha?: number | null
  beat_bm_rate?: number | null
}

export interface DailyData {
  dates: string[]
  nav: number[]
  bm_nav?: number[] | null
}

export interface Strategy {
  id: string
  label: string
  desc?: string
  scopes?: Scope[]
  trades?: TradeRow[]
  daily?: Record<string, DailyData>
  recommendations?: Rec[]
  hit_rate?: HitRow[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  factor?: any
}

export interface Rec {
  stock_id: number
  ticker: string
  name_zh: string
  market: string
  asset_type: string
  ep_no: number | null
  signal_date: string
  confidence: number | null
  has_position: boolean | null
  quote: string | null
  entry_date: string
  entry_price: number
  current_date: string
  current_price: number
  ret: number | null
  days_held: number
  fresh: boolean
}

export interface HitRow {
  horizon: number
  n: number
  pct_positive?: number
  avg_return?: number
  avg_alpha?: number | null
  beat_bm_rate?: number | null
}

export interface NavSeries {
  id: string
  label: string
  color: string
  data: { date: string; value: number }[]
}
