export type Direction = '看多' | '看空' | '中性'
export type Market = 'TW' | 'US' | 'OTHER' | 'UNKNOWN'
export type AssetType = '個股' | 'ETF' | '題材' | '指數' | '商品'

/** 可交易（可直接買賣）的資產類型 */
export const TRADEABLE_TYPES: AssetType[] = ['個股', 'ETF']

export interface Episode {
  id: number
  ep_no: number
  title: string
  source_url: string
  published_at: string | null
  summary: string[]
  topics: string[]
  created_at: string
}

export interface Stock {
  id: number
  ticker: string
  market: Market
  name_zh: string
  name_en: string | null
  aliases: string[]
  asset_type: AssetType
}

export interface Mention {
  id: number
  episode_id: number
  stock_id: number | null
  name_raw: string
  ticker_guess: string | null
  market: Market
  direction: Direction
  confidence: number
  has_position: boolean
  quote: string
  note: string | null
  // joined
  episodes?: Pick<Episode, 'ep_no' | 'title'>
  stocks?: Pick<Stock, 'ticker' | 'name_zh' | 'market'> | null
}
